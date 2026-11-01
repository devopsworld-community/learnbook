"""Terminal front end. `./lb watch` works like rustlings: it opens the next exercise, re-checks your file every
time you save it, and moves on when it passes. Every other exercise type is answered right in the terminal."""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
import time
from typing import Any

from learnbook import core

TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if TTY else s


def ok_s(s: str) -> str:
    return c("32", s)


def bad_s(s: str) -> str:
    return c("31", s)


def dim(s: str) -> str:
    return c("2", s)


def bold(s: str) -> str:
    return c("1", s)


def wrap(s: str, indent: str = "  ") -> str:
    return "\n".join(
        textwrap.fill(par, 100, initial_indent=indent, subsequent_indent=indent) if par.strip() else ""
        for par in str(s).split("\n")
    )


def ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        raise KeyboardInterrupt from None


# ---------------------------------------------------------------- helpers


def pick_track(arg: str | None) -> core.Track:
    p = core.load_progress()
    tid = arg or p.get("track") or core.ready_tracks()[0]
    return core.load_track(tid)


def resolve(track: core.Track, ref: str | None, p: dict[str, Any]) -> core.Exercise:
    if not ref:
        ex = core.next_open(p, track)
        if not ex:
            raise SystemExit("Nothing open: every unlocked exercise is done. Try `./lb review` or `./lb status`.")
        return ex
    hits = [e for e in track.exercises() if e.id == ref or e.id.endswith("/" + ref) or e.data["id"] == ref]
    if len(hits) != 1:
        raise SystemExit(f"{'No' if not hits else 'Ambiguous'} exercise {ref!r}. See `./lb list`.")
    return hits[0]


def bar(done: int, total: int, width: int = 24) -> str:
    n = round(width * done / total) if total else 0
    return "[" + "#" * n + "-" * (width - n) + "]"


def header(track: core.Track, ex: core.Exercise) -> None:
    ch = next(x for x in track.chapters if x.id == ex.chapter)
    print()
    print(dim(f"{track.data['title']}  /  {ch.data['title']}"))
    print(bold(f"{ex.id}") + dim(f"  ({ex.type}, concept: {track.data['concepts'].get(ex.concept, ex.concept)})"))
    print(wrap(ex.get("prompt")))


def show_explain(track: core.Track, ex: core.Exercise, ok: bool, extra: str = "") -> None:
    print()
    print((ok_s("Right. ") if ok else bad_s("Not this time. ")) + extra)
    if ex.get("explain"):
        print(wrap(ex.get("explain")))
    src = ex.get("source") or ex.get("cite")
    if src:
        print(dim(f"  source: {src}"))


def finish(track: core.Track, ex: core.Exercise, ok: bool, note: str = "") -> None:
    p = core.load_progress()
    r = core.record(p, track, ex, ok, note)
    core.save_progress(p)
    if r["xp"]:
        print(dim(f"  +{r['xp']} xp"))
    if r["chapter_cleared"]:
        print(ok_s(f"  Chapter cleared: {ex.chapter}"))


# ---------------------------------------------------------------- one exercise in the terminal


def play(track: core.Track, ex: core.Exercise) -> bool | None:
    """Run one non-file exercise interactively. Returns ok, or None when the type needs the file watcher."""
    header(track, ex)
    t = ex.type
    if t == "predict":
        for i, o in enumerate(ex.get("options")):
            print(f"   {i + 1}) {o}")
        while True:
            a = ask("  your answer (number): ").strip()
            if a.isdigit() and 1 <= int(a) <= len(ex.get("options")):
                break
        g = core.grade(track, ex, {"choice": int(a) - 1})
        show_explain(track, ex, g["ok"], f"Answer: {ex.get('options')[g['answer']]}")
        if ex.get("verify"):
            r = core.run_safe(track, ex.get("verify"))
            print(dim(f"  on this machine ({ex.get('verify')}):"))
            print(wrap(r["stdout"].strip(), "    "))
        return g["ok"]
    if t == "recall":
        g = core.grade(track, ex, {"text": ask("  $ ")})
        show_explain(track, ex, g["ok"], f"One good answer: {g['answer']}")
        return g["ok"]
    if t == "spot":
        pub = core.public_exercise(track, ex)
        for i, ln in enumerate(pub["lines"]):
            print(f"  {i + 1:>3}  {ln}")
        while True:
            a = ask("  line number of the injected line, or 0 if the log is clean: ").strip()
            if a.isdigit() and 0 <= int(a) <= len(pub["lines"]):
                break
        g = core.grade(track, ex, {"line": int(a) - 1 if int(a) else -1})
        where = ", ".join(str(i + 1) for i in g["injected"]) or "none (this is the clean control)"
        show_explain(track, ex, g["ok"], f"Injected: {where}")
        return g["ok"]
    if t == "sort":
        buckets = ex.get("buckets")
        print("  " + "   ".join(f"{i + 1}) {b}" for i, b in enumerate(buckets)))
        placed = []
        for name, _ in ex.get("items"):
            while True:
                a = ask(f"  {name}: ").strip()
                if a.isdigit() and 1 <= int(a) <= len(buckets):
                    placed.append(int(a) - 1)
                    break
        g = core.grade(track, ex, {"placed": placed})
        wrong = [f"{n} -> {buckets[b]}" for (n, b), pl in zip(ex.get("items"), placed, strict=False) if b != pl]
        show_explain(track, ex, g["ok"], f"{g['right']}/{g['total']}." + (f" Fix: {'; '.join(wrong)}" if wrong else ""))
        return g["ok"]
    if t == "match":
        pub = core.public_exercise(track, ex)
        right = pub["right"]
        for i, r in enumerate(right):
            print(f"   {chr(97 + i)}) {r}")
        chosen = []
        for left in pub["left"]:
            while True:
                a = ask(f"  {left}\n    -> letter: ").strip().lower()
                if len(a) == 1 and 0 <= ord(a) - 97 < len(right):
                    chosen.append(right[ord(a) - 97])
                    break
        g = core.grade(track, ex, {"chosen": chosen})
        show_explain(track, ex, g["ok"], f"{g['right']}/{g['total']} matched.")
        return g["ok"]
    if t == "gate":
        picks = []
        for cmd in ex.get("commands"):
            while True:
                a = ask(f"  {cmd}\n    [a]llow or [r]efuse: ").strip().lower()
                if a in ("a", "r"):
                    picks.append(a == "a")
                    break
        g = core.grade(track, ex, {"picks": picks})
        for row in g["rows"]:
            mark = ok_s("ok ") if row["right"] else bad_s("no ")
            print(f"  {mark} {'ALLOW ' if row['allowed'] else 'REFUSE'} {row['cmd']}  {dim(row['why'])}")
        show_explain(track, ex, g["ok"], f"{g['right']}/{g['total']} against the real allow and deny lists.")
        return g["ok"]
    if t == "explain":
        parts = [ask(f"  {p}\n    > ") for p in ex.get("parts")]
        g = core.grade(track, ex, {"parts": parts})
        show_explain(
            track, ex, g["ok"], "Report accepted." if g["ok"] else f"Missing or too short: {', '.join(g['missing'])}"
        )
        return g["ok"]
    if t == "pledge":
        print(textwrap.indent(core.public_exercise(track, ex)["text"], "  | "))
        ticked = [ask(f"  Will you enforce: {r}? [y/n] ").strip().lower().startswith("y") for r in ex.get("rules")]
        g = core.grade(track, ex, {"ticked": ticked})
        print(
            f"  {g['ticked']} of {g['total']}. Honest is the point; "
            "the unticked ones are where the next incident lives."
        )
        return True
    if t == "lab":
        print(wrap(dim(ex.get("hint", ""))))
        r = core.probe(track, ex.get("probe"))
        print(f"  probe {ex.get('probe')}: {'found' if r['ok'] else 'not found'} ({r['where']})")
        return True if r["ok"] else False
    return None


# ---------------------------------------------------------------- file exercises


def print_checks(res: dict[str, Any]) -> None:
    for r in res["results"]:
        tag = {"pass": ok_s("pass"), "fail": bad_s("fail"), "skip": dim("skip")}[r["status"]]
        print(f"  {tag}  {r['name']}" + (dim(f"  {r['detail']}") if r["detail"] and r["status"] != "pass" else ""))
    if res["passed"] and res["marker"]:
        print(ok_s(f"  All checks pass. Delete the line '{core.MARKER}' to move on."))


def watch_fix(track: core.Track, ex: core.Exercise) -> bool:
    f = core.workspace_file(track, ex)
    header(track, ex)
    print(f"\n  Edit {bold(core.display_path(f))} in your editor. Checks re-run on every save.")
    print(dim("  Ctrl-C to stop.  In another terminal: ./lb hint, ./lb reset <id>, ./lb serve for the GUI."))
    last = None
    while True:
        m = f.stat().st_mtime
        if m != last:
            last = m
            print(dim(f"\n  -- checked {time.strftime('%H:%M:%S')}"))
            res = core.check_fix(track, ex)
            print_checks(res)
            if res["done"]:
                print(ok_s("  Done."))
                if ex.get("explain"):
                    print(wrap(ex.get("explain")))
                finish(track, ex, True)
                return True
        time.sleep(1)


# ---------------------------------------------------------------- commands


def cmd_status(track: core.Track, _: argparse.Namespace) -> int:
    p = core.load_progress()
    book = core.load_book()
    total = len(track.exercises())
    done = sum(1 for e in track.exercises() if e.id in p["done"])
    print(bold(book["title"]))
    print(f"{track.data['title']}  {bar(done, total)} {done}/{total}   {p['xp']} xp, {p['streak']}-day streak\n")
    for s, ch in zip(core.chapter_state(p, track), track.chapters, strict=True):
        state = ok_s("cleared") if s["cleared"] else (f"{s['done']}/{s['total']}" if s["unlocked"] else dim("locked"))
        print(f"  {ch.id:<28} {bar(s['done'], s['total'], 10)} {state:<10} {dim(ch.data['title'])}")
    due = core.due_reviews(p, track)
    print(f"\n  review due: {len(due)}   delayed quiz: {core.quiz_state(p, track)}")
    nxt = core.next_open(p, track)
    print(f"  next: {nxt.id} ({nxt.type})  ->  ./lb watch" if nxt else "  next: nothing open")
    return 0


def cmd_tracks(_: core.Track | None, __: argparse.Namespace) -> int:
    book = core.load_book()
    for t in book["tracks"]:
        mark = ok_s("ready  ") if t.get("status") == "ready" else dim("planned")
        print(f"  {mark} {t.get('course', ''):>2}  {t.get('date', ''):<10}  {t['id']:<26} {t['title']}")
    return 0


def cmd_list(track: core.Track, _: argparse.Namespace) -> int:
    p = core.load_progress()
    for ch in track.chapters:
        print(bold(f"{ch.id}  {ch.data['title']}"))
        for e in ch.exercises:
            d = p["done"].get(e.id)
            mark = (ok_s("x") if d["ok"] else c("33", "~")) if d else " "
            print(f"   [{mark}] {e.data['id']:<28} {dim(e.type)}")
    return 0


def cmd_do(track: core.Track, a: argparse.Namespace) -> int:
    p = core.load_progress()
    ex = resolve(track, a.id, p)
    if ex.type == "fix":
        return 0 if watch_fix(track, ex) else 1
    ok = play(track, ex)
    if ok is not None and (ok or ex.type != "lab"):
        finish(track, ex, bool(ok))
    return 0


def cmd_verify(track: core.Track, a: argparse.Namespace) -> int:
    p = core.load_progress()
    ex = resolve(track, a.id, p)
    if ex.type == "lab":
        r = core.probe(track, ex.get("probe"))
        print(f"{ex.id}: probe {'found' if r['ok'] else 'not found'} ({r['where']})")
        if r["ok"]:
            finish(track, ex, True)
        return 0 if r["ok"] else 1
    if ex.type != "fix":
        print(f"{ex.id} is a {ex.type} exercise; answer it with ./lb do {ex.data['id']}")
        return 1
    res = core.check_fix(track, ex)
    print(bold(ex.id) + dim(f"  {res['file']}"))
    print_checks(res)
    if res["done"] and ex.id not in p["done"]:
        finish(track, ex, True)
    return 0 if res["done"] else 1


def cmd_hint(track: core.Track, a: argparse.Namespace) -> int:
    ex = resolve(track, a.id, core.load_progress())
    print(bold(ex.id))
    print(wrap(ex.get("hint") or "No hint for this one. Read the lesson: " + f"chapters/{ex.chapter}/lesson.md"))
    return 0


def cmd_reset(track: core.Track, a: argparse.Namespace) -> int:
    ex = resolve(track, a.id, core.load_progress())
    if ex.type != "fix":
        raise SystemExit(f"{ex.id} has no file to reset")
    f = core.reset_workspace_file(track, ex)
    print(f"reset {core.display_path(f)} to the broken original")
    return 0


def cmd_solution(track: core.Track, a: argparse.Namespace) -> int:
    p = core.load_progress()
    ex = resolve(track, a.id, p)
    if ex.type != "fix":
        raise SystemExit(f"{ex.id} has no solution file; its explanation shows after you answer")
    if ex.id not in p["done"] and not a.yes:
        if ask("  Not solved yet. Peeking marks this exercise as not mastered. Show it? [y/N] ").strip().lower() != "y":
            return 1
        p["peeked"][ex.id] = core.now_ms()
        core.save_progress(p)
    print(core.solution_text(track, ex))
    return 0


def cmd_watch(track: core.Track, _: argparse.Namespace) -> int:
    skipped: set[str] = set()
    try:
        while True:
            p = core.load_progress()
            states = {s["id"]: s for s in core.chapter_state(p, track)}
            ex = next(
                (
                    e
                    for ch in track.chapters
                    if states[ch.id]["unlocked"]
                    for e in ch.exercises
                    if e.id not in p["done"] and e.id not in skipped
                ),
                None,
            )
            if ex is None:
                print(ok_s("\nNothing left to do right now."))
                cmd_status(track, _)
                return 0
            if ex.type == "fix":
                watch_fix(track, ex)
                continue
            ok = play(track, ex)
            if ex.type == "lab" and not ok:
                if ask("  Run the lab, then press Enter to check again, or type s to skip it for now: ").strip() == "s":
                    skipped.add(ex.id)
                continue
            finish(track, ex, bool(ok))
            ask(dim("  Enter for the next one, Ctrl-C to stop. "))
    except KeyboardInterrupt:
        print(dim("\n  stopped; progress is saved."))
        return 0


def cmd_review(track: core.Track, _: argparse.Namespace) -> int:
    try:
        while True:
            p = core.load_progress()
            due = core.due_reviews(p, track)
            if not due:
                print("Nothing due for review. Misses come back tomorrow; hits in 3, 7, then 21 days.")
                return 0
            ex = core.find_exercise(track, due[0])
            ok = play(track, ex)
            p = core.load_progress()
            core.review_answer(p, track, ex, bool(ok))
            core.save_progress(p)
    except KeyboardInterrupt:
        return 0


def cmd_quiz(track: core.Track, a: argparse.Namespace) -> int:
    p = core.load_progress()
    state = core.quiz_state(p, track)
    if state != "ready" and not a.force:
        print(f"Delayed quiz is {state}. It opens two days after your first cleared chapter (that delay is the point).")
        return 1
    print(bold("Delayed quiz") + dim("  no notes, no AI; answer, then grade yourself against the model answer"))
    grades = []
    try:
        for i, q in enumerate(track.data.get("delayed_quiz", []), 1):
            print(f"\n{i}. {q['q']}")
            ask("  your answer > ")
            print(wrap(dim("model answer: ") + q["a"]))
            grades.append(ask("  did you have it? [y/n] ").strip().lower().startswith("y"))
    except KeyboardInterrupt:
        return 1
    n, total = sum(grades), len(grades)
    p = core.load_progress()
    p["quiz"][track.id] = {"at": core.now_ms(), "score": n / total if total else 0}
    p["xp"] += 10 * n
    core.save_progress(p)
    print(f"\n{n}/{total} two days later. Compare it with how sure you felt right after the chapters.")
    return 0


def cmd_validate(track: core.Track, _: argparse.Namespace) -> int:
    errs = core.validate(track)
    n = len(track.exercises())
    fixes = sum(1 for e in track.exercises() if e.type == "fix")
    if errs:
        for e in errs:
            print(bad_s("FAIL ") + e)
        print(f"\n{len(errs)} problem(s) in {n} exercises")
        return 1
    print(
        ok_s("OK ") + f"{track.id}: {len(track.chapters)} chapters, {n} exercises, {fixes} file exercises "
        "(each fails as shipped and passes with its solution)"
    )
    return 0


def cmd_serve(_: core.Track, a: argparse.Namespace) -> int:
    from learnbook import server

    return server.serve(a.port, open_browser=not a.no_open)


def cmd_export(track: core.Track, a: argparse.Namespace) -> int:
    from learnbook import export

    out = export.markdown(track, answers=a.answers) if a.format == "md" else export.as_json(track, answers=a.answers)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(out)
    return 0


def cmd_track(_: core.Track | None, a: argparse.Namespace) -> int:
    core.load_track(a.id)  # fails loudly if not ready
    p = core.load_progress()
    p["track"] = a.id
    core.save_progress(p)
    print(f"current track: {a.id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="lb", description="Learnbook: read it, play it in the browser, or work it in the terminal."
    )
    ap.add_argument("--track", help="track id (default: the current or first ready track)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("status", help="progress for the current track (default)")
    sub.add_parser("tracks", help="every track in the book, ready and planned")
    sub.add_parser("list", help="chapters and exercises with their state")
    sub.add_parser("watch", help="rustlings mode: next exercise, re-checked on every save")
    for name, hlp in (
        ("do", "play one exercise (default: the next open one)"),
        ("verify", "check a file exercise once"),
        ("hint", "show the hint"),
        ("reset", "restore a file exercise to its broken original"),
    ):
        sp = sub.add_parser(name, help=hlp)
        sp.add_argument("id", nargs="?")
    sp = sub.add_parser("solution", help="show a file exercise's solution (marks it not mastered if unsolved)")
    sp.add_argument("id", nargs="?")
    sp.add_argument("--yes", action="store_true")
    sub.add_parser("review", help="spaced review of questions that are due")
    sp = sub.add_parser("quiz", help="the delayed quiz (opens two days after your first cleared chapter)")
    sp.add_argument("--force", action="store_true")
    sub.add_parser("validate", help="prove every exercise is gradable, broken files fail and solutions pass")
    sp = sub.add_parser("serve", help="the browser game on http://127.0.0.1:8765")
    sp.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    sp.add_argument("--no-open", action="store_true")
    sp = sub.add_parser("export", help="the track as Markdown (a book) or JSON (for other tools)")
    sp.add_argument("format", choices=["md", "json"])
    sp.add_argument("--answers", action="store_true", help="include answers and solutions")
    sp.add_argument("--out")
    sp = sub.add_parser("track", help="switch the current track")
    sp.add_argument("id")
    a = ap.parse_args(argv)
    cmds = {
        "status": cmd_status,
        "tracks": cmd_tracks,
        "list": cmd_list,
        "watch": cmd_watch,
        "do": cmd_do,
        "verify": cmd_verify,
        "hint": cmd_hint,
        "reset": cmd_reset,
        "solution": cmd_solution,
        "review": cmd_review,
        "quiz": cmd_quiz,
        "validate": cmd_validate,
        "serve": cmd_serve,
        "export": cmd_export,
        "track": cmd_track,
    }
    name = a.cmd or "status"
    track = None if name in ("tracks", "track") else pick_track(a.track)
    try:
        return cmds[name](track, a)
    except KeyboardInterrupt:
        print(dim("\n  stopped; nothing was recorded for the open exercise."))
        return 130
    except core.ContentError as e:
        print(bad_s("content error: ") + str(e), file=sys.stderr)
        return 2
