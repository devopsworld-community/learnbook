# The license test, the local stack and Lab 1

Part 3 runs an AI assistant on your Linux box. The stack is fully open source and local, and the first
lab is deliberately boring: one broken nginx config, fixed by you before an agent is allowed to try.

## The stack

| Layer | Tool | License |
|---|---|---|
| Local model runtime | Ollama, as a hardened systemd service | MIT |
| Models | devstral:24b, gpt-oss:20b | Apache-2.0 weights |
| Terminal agent | OpenCode (`plan` agent by default) | MIT |
| Shell helpers | aichat, llm | Apache-2.0 / MIT |
| K8s investigators | k8sgpt, HolmesGPT | Apache-2.0 |
| MCP servers | kubernetes-mcp-server (read-only), mcp-grafana (`--disable-write`) | Apache-2.0 |
| Sandbox | sandbox-runtime (`srt`), Docker with an egress allowlist proxy | Apache-2.0 / MIT |
| IaC gates | Checkov, Trivy, Terraform MCP (`ENABLE_TF_OPERATIONS=false`) | Apache-2.0 / MPL-2.0 |

The license test: read the `LICENSE` file, not the README or the marketing page. Local does not mean
license-free, and "open" in a product name is not a license.

## Set it up (Ubuntu 24.04/26.04 or Amazon Linux 2023, NVIDIA GPU with 16 GB+ VRAM)

```
cd tracks/linux-ai-era
sudo ./setup/00-prereqs.sh
sudo ./setup/01-ollama-systemd.sh      # Ollama as a hardened unit, pulls the two models
./setup/02-agents.sh                    # OpenCode, aichat, llm, k8sgpt, holmes, srt, checkov, trivy
make lab01                              # validate the task, then fix it by hand, timed
make lab01-agent                        # the same task with OpenCode on the local model
```

## Lab 1, the honest baseline

The same task three ways, three timings: the exercise below fixes `nginx.conf` in your editor against
static checks; `make lab01` drops you into the broken container with a timer; `make lab01-agent` lets the
plan agent try while you approve each command. `run.sh validate` first proves that doing nothing fails the
hidden tests and the reference fix passes them, the rule Terminal-Bench's Harbor format uses.
