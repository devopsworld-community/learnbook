# The DevOps World Learnbook

One book, many tracks, one engine. Each track is a course from the DevOps World series: lessons you can
read, exercises you play in the browser or in the terminal, and real labs whose result files count toward
your progress. Every course starts at L0 (never done it) and ends at L3+ (runs it in production).

The first track is ready: **[Linux administration for DevOps in the AI era](tracks/linux-ai-era/README.md)**.

```bash
git clone https://github.com/devopsworld-community/learnbook.git && cd learnbook
make play        # the browser game at http://127.0.0.1:8765
./lb watch       # or the same exercises in your terminal, rustlings style
```

Python 3.10 or newer, nothing to install. Everything runs on 127.0.0.1 and nothing is sent anywhere.

## Ways to use it

| Way | What you get | Command |
|---|---|---|
| Play it in the browser | Chapters that unlock as you go, XP, spaced review, a delayed quiz, an editor for the file exercises | `make play` |
| Work it in the terminal | Rustlings style: the next exercise opens, your file is re-checked on every save, you move on when it passes | `./lb watch` |
| Read it as a book | Every chapter is a Markdown lesson in `tracks/<track>/chapters/`, or one file for the whole track | `make book` |
| Feed it to other tools | The track as JSON (answers left out unless you ask) for a content pipeline, an LMS, a classroom or an AI tutor | `make json` |
| Run the real labs | Docker, VMs and kind clusters; lab rounds clear only from the result files the labs leave behind | `make lab01` |

The browser and the terminal share one progress file (`.learnbook/progress.json`) and one copy of your
edits (`workspace/`), so you can switch between them at any time. Both are git-ignored.

## How it teaches

- **Predict before you see.** Every command output and every number is a question first.
- **Fix it like rustlings.** Broken config files are copied to `workspace/`. Edit them in your own editor;
  the checks re-run on every save. Delete the `I AM NOT DONE` line when they pass.
- **Manual before agent.** You fix it by hand before an AI agent is allowed to touch it.
- **Real runs count.** Lab rounds clear only when the lab's own result file exists.
- **Spaced review and a delayed quiz.** Misses come back tomorrow, hits in 3, 7 and 21 days; the quiz opens
  two days after your first cleared chapter, because that is where shallow learning shows.

## Tracks

| # | Date | Track | Status |
|---|---|---|---|
| 1 | 2026-11-01 | [Linux administration for DevOps in the AI era](tracks/linux-ai-era/README.md) | ready |
| 2 | 2026-11-03 | SQL administration for DevOps | planned |
| 3 | 2026-11-05 | Jira & Git management | planned |
| 4 | 2026-11-07 | Build & release management | planned |
| 5 | 2026-11-09 | Configuration management | planned |
| 6 | 2026-11-11 | Environment management | planned |
| 7 | 2026-11-13 | ServiceNow & support systems | planned |
| 8 | 2026-11-15 | SRE & production operations | planned |
| 9 | 2026-11-17 | Cloud support | planned |
| 10 | 2026-11-19 | Day-to-day cloud operations | planned |
| 11 | 2026-11-21 | Automation | planned |
| 12 | 2026-11-23 | Network setup: AWS, Azure & hybrid | planned |
| 13 | 2026-11-25 | Migration: databases, stateful resources & IaC | planned |
| 14 | 2026-11-27 | CDK building blocks | planned |
| 15 | 2026-11-29 | Terraform building blocks | planned |
| 16 | 2026-12-01 | Kubernetes: EKS, AKS, on-prem & edge | planned |
| 17 | 2026-12-03 | Deployment strategies | planned |
| 18 | 2026-12-05 | GenAI in production | planned |
| 19 | 2026-12-07 | Private AI & AI networks | planned |

## The terminal commands

```
./lb status            progress for the current track (the default)
./lb watch             rustlings mode: next exercise, re-checked on every save
./lb do [id]           play one exercise (default: the next open one)
./lb verify [id]       check a file exercise once
./lb hint [id]         ./lb reset <id>         ./lb solution <id>
./lb review            ./lb quiz               ./lb list            ./lb tracks
./lb serve             the browser game
./lb export md|json    the track as a book or as data
./lb validate          prove every exercise is gradable
```

## Layout

```
book.json                   the catalog: every track, ready or planned
learnbook/                  the engine (standard library only): core.py, cli.py, server.py, export.py, web/
tracks/<track>/track.json   concepts, chapter order, read-only diagnostic commands, lab probes, delayed quiz
tracks/<track>/chapters/    one folder per chapter: lesson.md and chapter.json (the exercises)
tracks/<track>/exercises/   broken files, copied to workspace/ on first use
tracks/<track>/solutions/   the reference fixes (shown after you pass, or if you choose to peek)
tests/                      unit tests for the engine
```

## Adding a track or an exercise

A track is a folder with `track.json`, chapters and (optionally) exercises, solutions and labs, plus an
entry in `book.json` with `"status": "ready"`. Exercise types: `predict`, `recall`, `spot`, `sort`,
`match`, `gate`, `fix`, `explain`, `pledge` and `lab`. A `fix` exercise names a file and a list of checks
(`re`, `not_re`, `balanced`, `json`, `json_has`, `json_lacks`, `size_order`, `size_min`, `tool`).

`make validate` must pass before anything is merged: every broken file has to fail its checks and every
solution has to pass them, the same rule the labs apply to themselves (a no-op fails, the oracle passes).

## Safety

The server binds 127.0.0.1, refuses other Host headers, and requires a custom header on every request that
changes something, so another web page cannot drive it. It writes only your workspace copy of the open
exercise and runs only the fixed, read-only diagnostic commands listed in each `track.json`. Nothing you
type reaches a shell.

## License

Apache-2.0 (see `LICENSE`). Third-party tools used in the labs keep their own licenses.
