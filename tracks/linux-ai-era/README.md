# Course 1 · Linux administration for DevOps in the AI era

Run Linux the way the gurus taught it, run the Linux underneath AI systems old and new, and let open-source AI help you without letting it near your keys.

Levels: L0 (never done it) to L3+ (runs it in production). Released 1 Nov 2026 as course 1 of the DevOps World series.

```bash
make play          # from the repo root: this track in your browser
./lb watch         # or in your terminal, rustlings style
```

## What you can do at the end

- Run and troubleshoot a Linux server the way the people who wrote the books do it: permissions and sudo,
  SSH, systemd and cgroup v2, disks and logs, networking and nftables, Brendan Gregg's 60-second triage and
  the USE method, and patching, with free, open-source tools.
- Run the Linux underneath AI systems: the GPU boxes of the last decade (drivers, DKMS, CUDA, shared
  notebooks, Slurm) and the inference servers of this one (Ollama, vLLM, llama.cpp) as hardened services.
- Use local, open-source AI as a co-admin without handing it your keys: sandboxes, read-only gates, a
  poisoned-log red team, IaC and package gates, and an AGENTS.md for your own repos.

## Chapters

**Cold open**

1. [First page](chapters/01-first-page/lesson.md) · 3 exercises (predict, spot)

**Part 1 · The box, the way the gurus run it**

2. [The shell, permissions and sudo](chapters/02-shell-permissions-sudo/lesson.md) · 5 exercises (fix, predict, recall)
3. [Users, groups and SSH hardening](chapters/03-ssh-hardening/lesson.md) · 5 exercises (fix, predict, recall)
4. [systemd, cgroup v2 and resource control](chapters/04-systemd-cgroups/lesson.md) · 6 exercises (fix, predict, recall)
5. [Disks, logs and the 3 am disk-full drill](chapters/05-disks-logs/lesson.md) · 6 exercises (fix, predict, recall)
6. [Networking from the box](chapters/06-network/lesson.md) · 6 exercises (fix, predict, recall)
7. [Performance triage: 60 seconds and the USE method](chapters/07-performance/lesson.md) · 7 exercises (fix, match, predict, recall, sort)
8. [Packages and patching without breaking the GPU stack](chapters/08-packages-patching/lesson.md) · 5 exercises (fix, predict, recall)

**Part 2 · Linux under AI systems, then and now**

9. [GPU boxes, then: drivers, DKMS, CUDA and shared notebooks](chapters/09-gpu-boxes-then/lesson.md) · 6 exercises (fix, predict, recall)
10. [Inference servers, now: Ollama, vLLM and llama.cpp as hardened services](chapters/10-inference-now/lesson.md) · 7 exercises (fix, predict, recall)

**Part 3 · AI as your co-admin, behind gates**

11. [The license test, the local stack and Lab 1](chapters/11-license-and-lab1/lesson.md) · 7 exercises (fix, lab, predict, sort)
12. [The six rules (and your own AGENTS.md)](chapters/12-six-rules/lesson.md) · 5 exercises (fix, match, pledge, predict)
13. [What can it read? Sandboxing the agent](chapters/13-sandbox/lesson.md) · 6 exercises (fix, lab, predict)
14. [Gate or go: an agent on a broken VM, over SSH](chapters/14-gate-or-go/lesson.md) · 6 exercises (explain, gate, lab, predict)
15. [Read-only on call: Kubernetes with k8sgpt and HolmesGPT](chapters/15-readonly-k8s/lesson.md) · 5 exercises (lab, predict)
16. [Red team: poisoned logs](chapters/16-red-team/lesson.md) · 5 exercises (lab, predict, spot)
17. [Ship it: IaC and package gates](chapters/17-ship-it/lesson.md) · 4 exercises (predict)

## What you keep

Everything you fix lives in `workspace/linux-ai-era/` when it passes: a least-privilege sudoers drop-in, an
sshd hardening drop-in, a hardened model-server unit and Ollama override, a memory drop-in, a logrotate rule,
an nftables ruleset, a sandbox config, `triage.sh` (the 60-second checklist as a script) and an `AGENTS.md`
for your repositories.

## The labs

The labs below are the companion repository of the episode "Open-Source AI for Linux Admin" (DevOps for AI,
season 1, episode 2), moved here unchanged. Run them from this folder.

| Lab | What it does | Command |
|---|---|---|
| Lab 1 baseline | A broken nginx config: by hand, then with the agent, timed | `make lab01`, `make lab01-agent` |
| Lab 5 broken VMs | Three VMs with planted faults; the agent reads through a gated SSH tool, you apply fixes with Ansible | `make lab05-key`, `labs/lab05-broken-vms/agent-over-ssh.sh` |
| Lab 6 Kubernetes incident | kind cluster, three faults, read-only RBAC, k8sgpt and HolmesGPT, API calls counted from the audit log | `make lab06-up lab06-drill` |
| Lab 7 poisoned logs | LogJack-style injection harness that records commands and executes nothing | `make lab07` |
| Lab 8 IaC gates | Checkov and a package-existence gate on agent-written Terraform | `make lab08` |

### The stack (all open source, local)

| Layer | Tool | License |
|---|---|---|
| Local model runtime | Ollama (systemd service) | MIT |
| Models | devstral:24b, gpt-oss:20b | Apache-2.0 weights |
| Terminal agent | OpenCode (`plan` agent by default) | MIT |
| Shell helpers | aichat, `llm` | Apache-2.0 / MIT |
| K8s investigators | k8sgpt, HolmesGPT | Apache-2.0 |
| MCP servers | containers/kubernetes-mcp-server (read-only), mcp-grafana (`--disable-write`) | Apache-2.0 |
| Sandbox | sandbox-runtime (`srt`), Docker with an egress allowlist proxy | Apache-2.0 / MIT |
| IaC gates | Checkov, Trivy, Terraform MCP (`ENABLE_TF_OPERATIONS=false`) | Apache-2.0 / MPL-2.0 |
| Lab format | Terminal-Bench / Harbor task layout | Apache-2.0 |

### Quick start (Ubuntu 24.04 / 26.04 or Amazon Linux 2023, NVIDIA GPU with 16 GB+ VRAM)

```bash
cd tracks/linux-ai-era
sudo ./setup/00-prereqs.sh
sudo ./setup/01-ollama-systemd.sh        # Ollama as a hardened systemd unit, pulls the two models
./setup/02-agents.sh                      # OpenCode, aichat, llm, k8sgpt, holmes, kubectl-ai, srt, checkov, trivy
make lab01                                # the baseline task, by hand and timed
```

Every lab prints the numbers the episode shows on screen. Nothing here has production credentials, and
nothing here should ever be pointed at a production system.

## Rules for agents (and humans) here

Read [AGENTS.md](AGENTS.md). Short version: the human is the author and the only signatory; the agent never
applies, sends or submits; verify by running, not by reading; say what you did not do; every commit an agent
touched carries `Assisted-by: LLM [tool]`.

## Safety

- Labs 1, 5, 6 and 7 are built to run inside `sandbox/` isolation. Lab 7 never executes model-proposed
  commands; the harness records them.
- `setup/01-ollama-systemd.sh` binds Ollama to localhost. Do not expose port 11434.
- Default `srt` and Claude Code sandboxes leave `~/.ssh` readable. `sandbox/srt-settings.json` denies
  `~/.ssh`, `~/.aws`, `~/.kube`, `~/.config/gh` and token files. Keep it that way.

## Sources

Chapters credit the practitioners whose methods they follow: Evi Nemeth and co-authors (*UNIX and Linux
System Administration Handbook*), Julia Evans (wizard zines), Mozilla's OpenSSH guidelines, Lennart Poettering
and the systemd documentation, Thomas Limoncelli and co-authors (*The Practice of System and Network
Administration*), W. Richard Stevens (*TCP/IP Illustrated*), and Brendan Gregg (the 60-second checklist, the
USE method, *Systems Performance*). Part 3 cites the Linux kernel's `coding-assistants.rst`, Simon Willison,
Mitchell Hashimoto, Armin Ronacher, systemd's CONTRIBUTING, Terminal-Bench, STCLab, LogJack and DPIaC-Eval.
A few 2026 figures come from the author's research notes, which are not yet published in this repo; those
exercises say so.
