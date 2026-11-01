# First page

It is 03:12. nginx is down on web-01. You open the journal and, right under the error, the deploy tooling
has left you a note with a one-line fix. This book starts there, because that line is the whole AI era of
Linux administration in one picture: the box still breaks the way it always did, and now something that
reads your logs may act on them.

## What this track covers

- **Part 1, the box.** Shell, permissions, SSH, systemd and cgroup v2, disks and logs, networking,
  performance triage and patching, the way the people who wrote the books run them, with free tools.
- **Part 2, Linux under AI systems.** The GPU boxes of the last decade (drivers, DKMS, CUDA, shared
  notebooks, Slurm) and the inference servers of this one (Ollama, vLLM, llama.cpp) run as hardened services.
- **Part 3, AI as your co-admin.** Local open-weight models, a terminal agent, sandboxes, read-only gates and
  red-team labs, so an assistant can help without ever holding your keys.

## How to play

Every chapter has a lesson (this text) and exercises. Some are questions you answer before you see the
answer. Some are broken files you fix, rustlings style, in `workspace/`: edit them here or in your own
editor and the checks re-run on every save. Some are real labs that only clear when their result files exist.

```
make play        # this page, in your browser
./lb watch       # the same exercises, in your terminal
```
