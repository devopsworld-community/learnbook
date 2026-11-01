"""Browser front end: a local, gamified view of the same book. `./lb serve` -> http://127.0.0.1:8765

Safety: binds 127.0.0.1 only; refuses requests whose Host header is not localhost (DNS rebinding); every
request that changes something must carry the X-Learnbook header, which a page on another origin cannot send
without a CORS preflight this server never grants. File writes go only to the learner's own workspace copy of
the exercise named in the request. Commands are the track's fixed read-only list; nothing typed reaches a shell.
"""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from learnbook import core

WEB = Path(__file__).resolve().parent / "web"
MAX_FILE = 200_000
_tracks: dict[str, core.Track] = {}


def track(tid: str) -> core.Track:
    # Reload on every request so edits to the content show up without restarting the server.
    _tracks[tid] = core.load_track(tid)
    return _tracks[tid]


def track_payload(t: core.Track) -> dict[str, Any]:
    done = core.load_progress()["done"]

    def ex(e: core.Exercise) -> dict[str, Any]:
        d = core.public_exercise(t, e)
        if e.id in done:
            d["reveal"] = core.reveal(t, e)
        return d

    return {
        **{k: v for k, v in t.data.items() if k not in ("chapters", "probes", "safe_commands", "delayed_quiz")},
        "quiz": [q["q"] for q in t.data.get("delayed_quiz", [])],
        "chapters": [
            {
                **{k: v for k, v in c.data.items() if k != "exercises"},
                "id": c.id,
                "lesson": c.lesson(),
                "exercises": [ex(e) for e in c.exercises],
            }
            for c in t.chapters
        ],
    }


def progress_payload(t: core.Track) -> dict[str, Any]:
    p = core.load_progress()
    mastery = {k.split(":", 1)[1]: v for k, v in p["mastery"].items() if k.startswith(t.id + ":")}
    return {
        "xp": p["xp"],
        "streak": p["streak"],
        "done": {k: v for k, v in p["done"].items() if k.startswith(t.id + "/")},
        "chapters": core.chapter_state(p, t),
        "due": core.due_reviews(p, t),
        "quiz": core.quiz_state(p, t),
        "mastery": mastery,
        "peeked": list(p["peeked"]),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "learnbook"

    def log_message(self, *a: Any) -> None:
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: Any, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        return host in ("127.0.0.1", "localhost", "::1")

    def _body(self) -> Any:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_FILE + 10_000:
            raise ValueError("body too large")
        raw = self.rfile.read(n) if n else b""
        return (
            raw.decode("utf-8")
            if self.headers.get("Content-Type", "").startswith("text/plain")
            else json.loads(raw or b"{}")
        )

    def do_GET(self) -> None:
        if not self._host_ok():
            return self._json({"error": "bad host"}, 403)
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
            if u.path == "/api/book":
                return self._json(core.load_book())
            if u.path == "/api/track":
                return self._json(track_payload(track(q["track"])))
            if u.path == "/api/progress":
                return self._json(progress_payload(track(q["track"])))
            if u.path == "/api/file":
                t = track(q["track"])
                ex = core.find_exercise(t, q["id"])
                f = core.workspace_file(t, ex)
                return self._json(
                    {"text": f.read_text(encoding="utf-8"), "mtime": f.stat().st_mtime, "path": core.display_path(f)}
                )
            if u.path == "/api/quizanswers":
                t = track(q["track"])
                if core.quiz_state(core.load_progress(), t) == "locked" and q.get("force") != "1":
                    return self._json({"error": "the delayed quiz is still locked"}, 403)
                return self._json({"answers": [x["a"] for x in t.data.get("delayed_quiz", [])]})
            if u.path == "/api/run":
                return self._json(core.run_safe(track(q["track"]), q.get("cmd", "")))
            return self._json({"error": "not found"}, 404)
        except (KeyError, core.ContentError) as e:
            return self._json({"error": str(e)}, 400)

    def do_POST(self) -> None:
        self._mutate()

    def do_PUT(self) -> None:
        self._mutate()

    def _mutate(self) -> None:
        if not self._host_ok():
            return self._json({"error": "bad host"}, 403)
        if self.headers.get("X-Learnbook") != "1":
            return self._json({"error": "missing X-Learnbook header"}, 403)
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            t = track(q["track"])
            body = self._body()
            if u.path == "/api/file":  # PUT text/plain: the learner's edit, to their own workspace copy only
                ex = core.find_exercise(t, q["id"])
                if ex.type != "fix" or not isinstance(body, str) or len(body) > MAX_FILE:
                    return self._json({"error": "not a file exercise or file too large"}, 400)
                f = core.workspace_file(t, ex)
                f.write_text(body, encoding="utf-8")
                return self._json({"ok": True, "mtime": f.stat().st_mtime})
            ex = core.find_exercise(t, body.get("id") or q.get("id", ""))
            p = core.load_progress()
            if u.path == "/api/answer":
                g = core.grade(t, ex, body.get("response") or {})
                g["reveal"] = core.reveal(t, ex)
                r = core.record(
                    p, t, ex, g["ok"], json.dumps(body.get("response"))[:500] if ex.type == "explain" else ""
                )
                core.save_progress(p)
                return self._json({**g, **r, "explain": ex.get("explain", "")})
            if u.path == "/api/check":
                res = core.check_fix(t, ex)
                r = (
                    core.record(p, t, ex, True)
                    if res["done"] and ex.id not in p["done"]
                    else {"xp": 0, "chapter_cleared": False}
                )
                core.save_progress(p)
                return self._json({**res, **r, "explain": ex.get("explain", "") if res["done"] else ""})
            if u.path == "/api/reset":
                core.reset_workspace_file(t, ex)
                return self._json({"ok": True})
            if u.path == "/api/solution":
                if ex.id not in p["done"]:
                    p["peeked"][ex.id] = core.now_ms()
                    core.save_progress(p)
                return self._json({"text": core.solution_text(t, ex)})
            if u.path == "/api/probe":
                r = core.probe(t, ex.get("probe"))
                rec = (
                    core.record(p, t, ex, True)
                    if r["ok"] and ex.id not in p["done"]
                    else {"xp": 0, "chapter_cleared": False}
                )
                core.save_progress(p)
                return self._json({**r, **rec})
            if u.path == "/api/review":
                g = core.grade(t, ex, body.get("response") or {})
                core.review_answer(p, t, ex, g["ok"])
                core.save_progress(p)
                return self._json({**g, "reveal": core.reveal(t, ex), "explain": ex.get("explain", "")})
            if u.path == "/api/quiz":
                grades = [bool(x) for x in body.get("grades", [])]
                p["quiz"][t.id] = {"at": core.now_ms(), "score": sum(grades) / max(1, len(grades))}
                p["xp"] += 10 * sum(grades)
                core.save_progress(p)
                return self._json(
                    {
                        "ok": True,
                        "right": sum(grades),
                        "total": len(grades),
                        "answers": [q["a"] for q in t.data.get("delayed_quiz", [])],
                    }
                )
            return self._json({"error": "not found"}, 404)
        except (KeyError, ValueError, core.ContentError) as e:
            return self._json({"error": str(e)}, 400)


def serve(port: int = 8765, open_browser: bool = True) -> int:
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Learnbook is running at {url}  (repo: {core.ROOT})")
    print("Progress saves to .learnbook/progress.json, your edits to workspace/. Ctrl-C to stop.")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0
