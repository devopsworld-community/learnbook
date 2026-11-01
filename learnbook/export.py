"""Exports: the same track as a readable book (Markdown) or as data (JSON) for other tools, such as a content
pipeline, an LMS, a community classroom or an AI tutor. Answers and solutions are left out unless asked for."""

from __future__ import annotations

import json
from typing import Any

from learnbook import core


def markdown(track: core.Track, answers: bool = False) -> str:
    d = track.data
    out = [f"# {d['title']}", "", d.get("tagline", ""), ""]
    if d.get("how_it_teaches"):
        out += ["## How this book teaches", ""] + [f"- {x}" for x in d["how_it_teaches"]] + [""]
    out += ["## Contents", ""] + [f"{i}. {c.data['title']}" for i, c in enumerate(track.chapters, 1)] + [""]
    for i, c in enumerate(track.chapters, 1):
        lesson = c.lesson().strip()
        if lesson.startswith("# "):
            lesson = lesson.split("\n", 1)[1] if "\n" in lesson else ""
        out += [
            f"## {i}. {c.data['title']}",
            "",
            f"*{c.data.get('brief', '')}*",
            "",
            lesson.strip(),
            "",
            "### Exercises",
            "",
        ]
        for n, e in enumerate(c.exercises, 1):
            out += _exercise_md(track, e, n, answers)
    if d.get("delayed_quiz"):
        out += ["## Delayed quiz (two days later, no notes)", ""]
        for n, q in enumerate(d["delayed_quiz"], 1):
            out += [f"{n}. {q['q']}"] + ([f"   - *Model answer:* {q['a']}"] if answers else [])
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _exercise_md(track: core.Track, e: core.Exercise, n: int, answers: bool) -> list[str]:
    out = [f"**{n}. {e.get('prompt')}** `{e.type}`", ""]
    t = e.type
    if t == "predict":
        out += [f"   {chr(97 + i)}) {o}" for i, o in enumerate(e.get("options"))] + [""]
        if answers:
            out += [f"   *Answer:* {e.get('options')[e.get('answer')]}. {e.get('explain', '')}", ""]
    elif t == "recall":
        if answers:
            out += [f"   *Answer:* `{e.get('answer_text')}`. {e.get('explain', '')}", ""]
    elif t == "fix":
        out += (
            [
                f"   Edit `workspace/{track.id}/{e.get('file')}` (from `exercises/{e.get('file')}`), "
                f"then `./lb verify {e.data['id']}`.",
                "",
                "   Checks:",
                "",
            ]
            + [f"   - {c['name']}" for c in e.get("checks", [])]
            + [""]
        )
        if answers:
            out += ["   *Solution:*", "", "```", core.solution_text(track, e).rstrip(), "```", ""]
    elif t == "spot":
        lines, injected = core.spot_lines(track, e)
        out += ["```"] + lines + ["```", ""]
        if answers:
            out += [
                f"   *Injected line(s):* {', '.join(str(i + 1) for i in injected) or 'none'}. {e.get('explain', '')}",
                "",
            ]
    elif t == "sort":
        out += [
            f"   Buckets: {', '.join(e.get('buckets'))}",
            f"   Items: {', '.join(n for n, _ in e.get('items'))}",
            "",
        ]
        if answers:
            out += [f"   - {name}: {e.get('buckets')[b]}" for name, b in e.get("items")] + [""]
    elif t == "match":
        out += [f"   - {left}" + (f" -> {right}" if answers else "") for left, right in e.get("pairs")] + [""]
    elif t == "gate":
        allow, deny = core.gate_rules(track, e)
        out += [
            f"   - `{cmd}`"
            + (f" -> {'allow' if core.gate_truth(allow, deny, cmd)[0] else 'refuse'}" if answers else "")
            for cmd in e.get("commands")
        ] + [""]
    elif t == "explain":
        out += [f"   - {p}" for p in e.get("parts")] + [""]
    elif t == "pledge":
        out += [f"   - [ ] {r}" for r in e.get("rules")] + [""]
    elif t == "lab":
        out += [f"   Probe `{e.get('probe')}`. {e.get('hint', '')}", ""]
    src = e.get("source") or e.get("cite")
    if src:
        out += [f"   *Source:* {src}", ""]
    return out


def as_json(track: core.Track, answers: bool = False) -> str:
    def ex(e: core.Exercise) -> dict[str, Any]:
        d = dict(e.data) if answers else core.public_exercise(track, e)
        d["uid"] = e.id
        if answers and e.type == "fix":
            d["solution"] = core.solution_text(track, e)
        return d

    data = {
        **{k: v for k, v in track.data.items() if k != "chapters" and (answers or k != "delayed_quiz")},
        "chapters": [
            {**c.data, "id": c.id, "lesson": c.lesson(), "exercises": [ex(e) for e in c.exercises]}
            for c in track.chapters
        ],
    }
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"
