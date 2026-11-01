"""The learnbook engine: content loading, grading, file exercises, probes and progress.

Everything a consumer needs (the GUI server, the terminal CLI, the exporters) goes through this module, so an
exercise is graded the same way however it is played. Python 3.10+ standard library only.
"""

from __future__ import annotations

import glob
import json
import math
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / ".learnbook"
PROGRESS_FILE = STATE_DIR / "progress.json"
WORKSPACE = ROOT / "workspace"
MARKER = "I AM NOT DONE"
DAY_MS = 86_400_000
TYPES = ("predict", "recall", "spot", "sort", "match", "gate", "fix", "explain", "pledge", "lab")
# Types answered from memory: these come back in the spaced-review queue as the same question.
REVIEWABLE = ("predict", "recall")


class ContentError(Exception):
    pass


# ---------------------------------------------------------------- content


@dataclass
class Exercise:
    track: str
    chapter: str
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return f"{self.track}/{self.chapter}/{self.data['id']}"

    @property
    def type(self) -> str:
        return self.data["type"]

    @property
    def concept(self) -> str:
        return self.data.get("concept", "")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


@dataclass
class Chapter:
    track: str
    dir: Path
    data: dict[str, Any]
    exercises: list[Exercise] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.dir.name

    @property
    def key(self) -> str:
        return f"{self.track}/{self.id}"

    def lesson(self) -> str:
        p = self.dir / "lesson.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""


@dataclass
class Track:
    dir: Path
    data: dict[str, Any]
    chapters: list[Chapter] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.data["id"]

    def exercises(self) -> list[Exercise]:
        return [e for c in self.chapters for e in c.exercises]

    def path(self, rel: str) -> Path:
        """A track-relative path, or ~ / absolute paths as given (probes look outside the repo)."""
        if rel.startswith("~"):
            return Path(rel).expanduser()
        if rel.startswith("/"):
            return Path(rel)
        return self.dir / rel


def _load_json(p: Path) -> Any:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ContentError(f"{p.relative_to(ROOT)}: {e}") from None


def load_book() -> dict[str, Any]:
    return _load_json(ROOT / "book.json")


def load_track(track_id: str) -> Track:
    book = load_book()
    entry = next((t for t in book["tracks"] if t["id"] == track_id), None)
    if not entry:
        raise ContentError(f"no track {track_id!r} in book.json")
    if entry.get("status") != "ready":
        raise ContentError(f"track {track_id!r} is {entry.get('status', 'planned')}, not ready yet")
    tdir = ROOT / entry["path"]
    data = _load_json(tdir / "track.json")
    track = Track(dir=tdir, data=data)
    for cid in data["chapters"]:
        cdir = tdir / "chapters" / cid
        cdata = _load_json(cdir / "chapter.json")
        ch = Chapter(track=track.id, dir=cdir, data=cdata)
        ch.exercises = [Exercise(track=track.id, chapter=cid, data=e) for e in cdata.get("exercises", [])]
        track.chapters.append(ch)
    return track


def ready_tracks() -> list[str]:
    return [t["id"] for t in load_book()["tracks"] if t.get("status") == "ready"]


def find_exercise(track: Track, ex_id: str) -> Exercise:
    for e in track.exercises():
        if e.id == ex_id:
            return e
    raise ContentError(f"no exercise {ex_id!r}")


# ---------------------------------------------------------------- file exercises (rustlings style)


def display_path(p: Path) -> str:
    """A path as the learner should see it: relative to the repo when it is inside it."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def workspace_file(track: Track, ex: Exercise) -> Path:
    """The learner's copy of a fix exercise. Created from the pristine file on first use; never in git."""
    dst = WORKSPACE / track.id / ex.get("file")
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(track.dir / "exercises" / ex.get("file"), dst)
    return dst


def reset_workspace_file(track: Track, ex: Exercise) -> Path:
    dst = WORKSPACE / track.id / ex.get("file")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(track.dir / "exercises" / ex.get("file"), dst)
    return dst


def solution_text(track: Track, ex: Exercise) -> str:
    return (track.dir / "solutions" / ex.get("file")).read_text(encoding="utf-8")


_SIZE = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}


def _size(value: str) -> float | None:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMGT]?)B?\s*", value or "", re.I)
    return float(m.group(1)) * _SIZE[m.group(2).upper()] if m else None


def _ini_value(text: str, key: str) -> str | None:
    vals = re.findall(rf"^\s*{re.escape(key)}\s*=\s*(.*?)\s*$", text, re.M)
    return vals[-1] if vals else None  # systemd: the last assignment wins


def _json_path(obj: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(obj, dict) or part not in obj:
            return None
        obj = obj[part]
    return obj


def run_checks(text: str, checks: list[dict[str, Any]], file: Path | None = None) -> list[dict[str, Any]]:
    """Evaluate a fix exercise's data-driven checks. Each result: {name, status: pass|fail|skip, detail}.

    Check kinds: re / not_re (multiline regex), balanced ("{}"), json, json_has {path, items},
    json_lacks {path, items}, size_order [k1, k2, ...] (systemd-style sizes strictly increasing),
    size_min {key, min}, tool [argv with {file}] (skipped when the tool is not installed; "advisory": true
    makes a failure informational).
    """
    out = []
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except ValueError:
        parsed = None
    for c in checks:
        name, status, detail = c["name"], "fail", ""
        try:
            if "re" in c:
                status = "pass" if re.search(c["re"], text, re.M) else "fail"
            elif "not_re" in c:
                m = re.search(c["not_re"], text, re.M)
                status = "fail" if m else "pass"
                detail = f"found: {m.group(0).strip()[:80]}" if m else ""
            elif "balanced" in c:
                a, b = c["balanced"]
                status = "pass" if text.count(a) == text.count(b) else "fail"
            elif "json" in c:
                status = "pass" if parsed is not None else "fail"
            elif "json_has" in c:
                got = _json_path(parsed, c["json_has"]["path"]) or []
                missing = [i for i in c["json_has"]["items"] if i not in got]
                status = "fail" if missing else "pass"
                detail = f"missing: {', '.join(missing)}" if missing else ""
            elif "json_lacks" in c:
                got = _json_path(parsed, c["json_lacks"]["path"]) or []
                present = [i for i in c["json_lacks"]["items"] if i in got]
                status = "fail" if present else "pass"
                detail = f"still present: {', '.join(present)}" if present else ""
            elif "size_order" in c:
                vals = [_size(_ini_value(text, k) or "") for k in c["size_order"]]
                ok = all(v is not None for v in vals) and all(x < y for x, y in zip(vals, vals[1:], strict=False))
                status = "pass" if ok else "fail"
            elif "size_min" in c:
                v = _size(_ini_value(text, c["size_min"]["key"]) or "")
                status = "pass" if v is not None and v >= _size(c["size_min"]["min"]) else "fail"
            elif "tool" in c:
                argv = [a.replace("{file}", str(file)) for a in c["tool"]]
                if file is None or not shutil.which(argv[0]):
                    status, detail = "skip", f"{argv[0]} not installed here"
                else:
                    r = subprocess.run(argv, capture_output=True, text=True, timeout=20)
                    status = "pass" if r.returncode == 0 else "fail"
                    detail = (r.stdout + r.stderr).strip()[-400:]
                    if status == "fail" and c.get("advisory"):
                        status = "skip"
                        detail = "advisory: " + detail
            else:
                raise ContentError(f"unknown check kind in {c}")
        except re.error as e:
            status, detail = "fail", f"bad regex in content: {e}"
        except subprocess.TimeoutExpired:
            status, detail = "skip", "tool timed out"
        out.append({"name": name, "status": status, "detail": detail})
    return out


def check_fix(track: Track, ex: Exercise, text: str | None = None) -> dict[str, Any]:
    f = workspace_file(track, ex)
    text = f.read_text(encoding="utf-8") if text is None else text
    results = run_checks(text, ex.get("checks", []), f)
    marker = MARKER in text
    passed = all(r["status"] != "fail" for r in results)
    return {
        "results": results,
        "marker": marker,
        "passed": passed,
        "done": passed and not marker,
        "file": display_path(f),
    }


# ---------------------------------------------------------------- spot, gate, probes, safe commands


def spot_lines(track: Track, ex: Exercise) -> tuple[list[str], list[int]]:
    lines = track.path(ex.get("file")).read_text(encoding="utf-8").splitlines()
    lines = [ln for ln in lines if not ln.startswith("# MARKERS:")]
    pats = [re.compile(p, re.I) for p in ex.get("answer", [])]
    injected = [i for i, ln in enumerate(lines) if any(p.search(ln) for p in pats)]
    return lines, injected


def gate_rules(track: Track, ex: Exercise) -> tuple[str, str]:
    """Parse the allow/deny regexes out of the real script, so the round grades against what ships."""
    rules = ex.get("rules")
    src = track.path(rules["file"]).read_text(encoding="utf-8")
    allow = re.search(rf"{rules['allow']}='(.*?)'\n", src, re.S)
    deny = re.search(rf"{rules['deny']}='(.*?)'\n", src, re.S)
    if not allow or not deny:
        raise ContentError(f"{rules['file']}: could not find {rules['allow']} / {rules['deny']}")
    return allow.group(1), deny.group(1)


def gate_truth(allow: str, deny: str, cmd: str) -> tuple[bool, str]:
    if re.search(deny, cmd):
        return False, "matches the deny list"
    if re.search(allow, cmd):
        return True, "on the read-only allow list"
    return False, "not on the allow list"


def probe(track: Track, key: str) -> dict[str, Any]:
    """Real-run verification: read the result files a lab leaves behind. No file, no clear."""
    spec = track.data.get("probes", {}).get(key)
    if not spec:
        raise ContentError(f"no probe {key!r}")
    if "glob" in spec:
        hits = [p for p in glob.glob(str(track.path(spec["glob"]))) if not os.path.basename(p).startswith(".")]
        return {"ok": len(hits) >= spec.get("min", 1), "found": len(hits), "where": spec["glob"]}
    p = track.path(spec["file"])
    if not p.exists():
        return {"ok": False, "found": 0, "where": spec["file"]}
    if "line_re" in spec:
        n = sum(
            1 for ln in p.read_text(encoding="utf-8", errors="replace").splitlines() if re.search(spec["line_re"], ln)
        )
        return {"ok": n > 0, "found": n, "where": spec["file"]}
    return {"ok": True, "found": 1, "where": spec["file"]}


def run_safe(track: Track, key: str) -> dict[str, Any]:
    """Run one of the track's exact, read-only diagnostic commands. Nothing a user types reaches a shell."""
    argv = track.data.get("safe_commands", {}).get(key)
    if not argv:
        return {"cmd": key, "stdout": "not an allowed command", "rc": 2}
    argv = [a.replace("{root}", str(ROOT)) for a in argv]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=8)
        return {"cmd": key, "stdout": (r.stdout + r.stderr)[:2000] or "(no output)", "rc": r.returncode}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"cmd": key, "stdout": f"could not run: {e}", "rc": 1}


# ---------------------------------------------------------------- grading


def grade(track: Track, ex: Exercise, response: dict[str, Any]) -> dict[str, Any]:
    """Grade one answer. Returns {ok, ...detail}. Fix and lab exercises are graded by check_fix / probe."""
    t = ex.type
    if t == "predict":
        choice = int(response.get("choice", -1))
        return {"ok": choice == ex.get("answer"), "answer": ex.get("answer"), "choice": choice}
    if t == "recall":
        text = str(response.get("text", "")).strip()
        ok = bool(text) and any(re.search(a, text, re.I) for a in ex.get("accept", []))
        return {"ok": ok, "answer": ex.get("answer_text")}
    if t == "spot":
        _, injected = spot_lines(track, ex)
        line = int(response.get("line", -2))
        ok = (line in injected) if injected else (line == -1)
        return {"ok": ok, "injected": injected, "line": line}
    if t == "sort":
        placed = response.get("placed", [])
        truth = [b for _, b in ex.get("items")]
        right = sum(1 for i, b in enumerate(truth) if i < len(placed) and placed[i] == b)
        need = math.ceil(len(truth) * ex.get("pass_ratio", 0.85))
        return {"ok": right >= need, "truth": truth, "right": right, "total": len(truth)}
    if t == "match":
        chosen = response.get("chosen", [])
        truth = [r for _, r in ex.get("pairs")]
        right = sum(1 for i, r in enumerate(truth) if i < len(chosen) and chosen[i] == r)
        return {"ok": right >= len(truth) - 1, "truth": truth, "right": right, "total": len(truth)}
    if t == "gate":
        allow, deny = gate_rules(track, ex)
        picks = response.get("picks", [])
        rows = []
        for i, cmd in enumerate(ex.get("commands")):
            allowed, why = gate_truth(allow, deny, cmd)
            rows.append({"cmd": cmd, "allowed": allowed, "why": why, "right": i < len(picks) and picks[i] == allowed})
        right = sum(r["right"] for r in rows)
        return {"ok": right >= len(rows) - 1, "rows": rows, "right": right, "total": len(rows)}
    if t == "explain":
        parts = response.get("parts", [])
        labels = [p.split(":")[0] for p in ex.get("parts")]
        missing = [lab for i, lab in enumerate(labels) if i >= len(parts) or len(str(parts[i]).strip()) < 12]
        return {"ok": not missing, "missing": missing}
    if t == "pledge":
        ticked = [bool(x) for x in response.get("ticked", [])]
        return {"ok": True, "ticked": sum(ticked), "total": len(ex.get("rules"))}
    raise ContentError(f"{ex.id}: {t} exercises are graded by checks or probes, not answers")


def reveal(track: Track, ex: Exercise) -> dict[str, Any]:
    """What a player may see once an exercise is done: the answer and the explanation."""
    r: dict[str, Any] = {"explain": ex.get("explain", "")}
    if ex.type == "predict":
        r["answer"] = ex.get("answer")
    elif ex.type == "recall":
        r["answer_text"] = ex.get("answer_text")
    elif ex.type == "spot":
        r["injected"] = spot_lines(track, ex)[1]
    return r


def public_exercise(track: Track, ex: Exercise) -> dict[str, Any]:
    """What a player sees before answering: everything except the answers and explanations."""
    d = {k: v for k, v in ex.data.items() if k not in ("answer", "accept", "answer_text", "checks", "rules", "explain")}
    d["uid"] = ex.id
    if ex.type == "sort":
        d["items"] = [name for name, _ in ex.get("items")]
    elif ex.type == "match":
        d["left"] = [lft for lft, _ in ex.get("pairs")]
        d["right"] = sorted({r for _, r in ex.get("pairs")})
        d.pop("pairs", None)
    elif ex.type == "spot":
        d["lines"], injected = spot_lines(track, ex)
        d["control"] = not injected
    elif ex.type == "fix":
        d["checks"] = [c["name"] for c in ex.get("checks", [])]
        d["workspace"] = display_path(WORKSPACE / track.id / ex.get("file"))
    elif ex.type == "pledge":
        d["text"] = track.path(ex.get("file")).read_text(encoding="utf-8")
        d["rules"] = ex.get("rules")
    return d


# ---------------------------------------------------------------- progress (shared by every consumer)


def now_ms() -> int:
    return int(time.time() * 1000)


def load_progress() -> dict[str, Any]:
    try:
        p = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        p = {}
    for k, v in (
        ("xp", 0),
        ("streak", 0),
        ("last_day", None),
        ("done", {}),
        ("mastery", {}),
        ("review", {}),
        ("cleared", {}),
        ("quiz", {}),
        ("peeked", {}),
        ("log", []),
    ):
        p.setdefault(k, v)
    return p


def save_progress(p: dict[str, Any]) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    p["log"] = p["log"][-300:]
    tmp = PROGRESS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(p, indent=1), encoding="utf-8")
    os.replace(tmp, PROGRESS_FILE)


def _schedule(p: dict[str, Any], key: str, ok: bool) -> None:
    """Spaced review, SM-2 lite: a miss comes back tomorrow; a hit moves out to 3, 7, then 21 days."""
    r = p["review"].get(key, {"level": 0})
    r["level"] = min(r["level"] + 1, 3) if ok else 0
    r["due"] = now_ms() + [1, 3, 7, 21][r["level"]] * DAY_MS
    p["review"][key] = r


def _mastery(p: dict[str, Any], track: Track, concept: str, ok: bool) -> None:
    m = p["mastery"].setdefault(f"{track.id}:{concept}", {"seen": 0, "right": 0})
    m["seen"] += 1
    m["right"] += int(ok)


def record(p: dict[str, Any], track: Track, ex: Exercise, ok: bool, note: str = "") -> dict[str, Any]:
    """Record an attempt. First attempt completes the exercise (wrong answers still move you on and come back
    in review), except fix and lab exercises, which complete only when they pass."""
    gained = 0
    if ex.type in ("fix", "lab") and not ok:
        p["log"].append({"id": ex.id, "ok": False, "at": now_ms()})
        return {"xp": 0, "chapter_cleared": False}
    if ex.id not in p["done"]:
        honest_ok = ok and not p["peeked"].get(ex.id)
        p["done"][ex.id] = {"ok": honest_ok, "at": now_ms()}
        gained += 10 if honest_ok else 2
        _mastery(p, track, ex.concept, honest_ok)
        if ex.type in REVIEWABLE:
            _schedule(p, ex.id, honest_ok)
    today = time.strftime("%Y-%m-%d")
    if p["last_day"] != today:
        yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
        p["streak"] = p["streak"] + 1 if p["last_day"] == yesterday else 1
        p["last_day"] = today
    p["log"].append({"id": ex.id, "ok": ok, "at": now_ms(), **({"note": note[:500]} if note else {})})
    ch = next(c for c in track.chapters if c.id == ex.chapter)
    cleared = False
    if ch.key not in p["cleared"] and all(e.id in p["done"] for e in ch.exercises):
        p["cleared"][ch.key] = now_ms()
        gained += 25
        cleared = True
    p["xp"] += gained
    return {"xp": gained, "chapter_cleared": cleared}


def review_answer(p: dict[str, Any], track: Track, ex: Exercise, ok: bool) -> None:
    _schedule(p, ex.id, ok)
    _mastery(p, track, ex.concept, ok)
    p["xp"] += 3 if ok else 1


def chapter_state(p: dict[str, Any], track: Track) -> list[dict[str, Any]]:
    """Per chapter: done/total, cleared, unlocked. A chapter opens when the one before is cleared or 60% done."""
    out = []
    prev_ok = True
    for c in track.chapters:
        done = sum(1 for e in c.exercises if e.id in p["done"])
        total = len(c.exercises)
        out.append({"id": c.id, "done": done, "total": total, "cleared": c.key in p["cleared"], "unlocked": prev_ok})
        prev_ok = c.key in p["cleared"] or done >= math.ceil(total * 0.6)
    return out


def due_reviews(p: dict[str, Any], track: Track) -> list[str]:
    ids = {e.id for e in track.exercises()}
    now = now_ms()
    return [k for k, r in p["review"].items() if k in ids and r["due"] <= now and r["level"] < 3]


def quiz_state(p: dict[str, Any], track: Track) -> str:
    """locked | ready | done. The delayed quiz opens two days after the track's first cleared chapter."""
    if track.id in p["quiz"]:
        return "done"
    firsts = [t for k, t in p["cleared"].items() if k.startswith(track.id + "/")]
    return "ready" if firsts and now_ms() - min(firsts) > 2 * DAY_MS else "locked"


def next_open(p: dict[str, Any], track: Track) -> Exercise | None:
    states = {s["id"]: s for s in chapter_state(p, track)}
    for c in track.chapters:
        if not states[c.id]["unlocked"]:
            return None
        for e in c.exercises:
            if e.id not in p["done"]:
                return e
    return None


# ---------------------------------------------------------------- validation (the Harbor rule, applied to the book)


def validate(track: Track) -> list[str]:
    """Every exercise must be answerable and gradable; every fix exercise must FAIL as shipped and PASS with its
    solution, the same rule the labs apply to themselves (a no-op fails, the oracle passes)."""
    errs: list[str] = []
    concepts = track.data.get("concepts", {})
    seen: set[str] = set()
    for c in track.chapters:
        if not (c.dir / "lesson.md").exists():
            errs.append(f"{c.key}: lesson.md missing")
        for e in c.exercises:
            where = e.id
            if e.id in seen:
                errs.append(f"{where}: duplicate id")
            seen.add(e.id)
            if e.type not in TYPES:
                errs.append(f"{where}: unknown type {e.type}")
                continue
            if e.concept not in concepts:
                errs.append(f"{where}: concept {e.concept!r} not in track concepts")
            if not e.get("prompt"):
                errs.append(f"{where}: no prompt")
            if e.get("source") and not track.path(e.get("source")).exists():
                errs.append(f"{where}: source {e.get('source')} does not exist")
            if e.get("verify") and e.get("verify") not in track.data.get("safe_commands", {}):
                errs.append(f"{where}: verify {e.get('verify')!r} is not a safe command")
            try:
                if e.type == "predict":
                    if not 0 <= e.get("answer", -1) < len(e.get("options", [])):
                        errs.append(f"{where}: answer index out of range")
                elif e.type == "recall":
                    if not any(re.search(a, e.get("answer_text", ""), re.I) for a in e.get("accept", [])):
                        errs.append(f"{where}: answer_text is not accepted by its own patterns")
                elif e.type == "spot":
                    _, injected = spot_lines(track, e)
                    if bool(injected) == bool(e.get("control")):
                        errs.append(f"{where}: control={e.get('control')} but {len(injected)} injected lines found")
                elif e.type == "sort":
                    if any(not 0 <= b < len(e.get("buckets")) for _, b in e.get("items")):
                        errs.append(f"{where}: item bucket out of range")
                elif e.type == "gate":
                    allow, deny = gate_rules(track, e)
                    for cmd in e.get("commands"):
                        gate_truth(allow, deny, cmd)
                elif e.type == "fix":
                    pristine = (track.dir / "exercises" / e.get("file")).read_text(encoding="utf-8")
                    sol_path = track.dir / "solutions" / e.get("file")
                    sol = sol_path.read_text(encoding="utf-8")
                    if MARKER not in pristine:
                        errs.append(f"{where}: exercise file has no '{MARKER}' marker")
                    no_marker = "\n".join(ln for ln in pristine.splitlines() if MARKER not in ln)
                    if all(r["status"] != "fail" for r in run_checks(no_marker, e.get("checks", []))):
                        errs.append(f"{where}: the broken file passes its checks (a no-op would clear it)")
                    if MARKER in sol:
                        errs.append(f"{where}: solution still contains the marker")
                    failing = [r for r in run_checks(sol, e.get("checks", []), sol_path) if r["status"] == "fail"]
                    if failing:
                        errs.append(f"{where}: solution fails {[r['name'] + ' ' + r['detail'] for r in failing]}")
                elif e.type == "lab":
                    if e.get("probe") not in track.data.get("probes", {}):
                        errs.append(f"{where}: unknown probe {e.get('probe')!r}")
                elif e.type == "pledge":
                    track.path(e.get("file")).read_text(encoding="utf-8")
            except (OSError, ContentError, re.error, KeyError, TypeError) as err:
                errs.append(f"{where}: {type(err).__name__}: {err}")
    for q in track.data.get("delayed_quiz", []):
        if not q.get("q") or not q.get("a"):
            errs.append(f"{track.id}: delayed quiz entry without q/a")
    return errs
