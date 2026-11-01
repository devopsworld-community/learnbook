# What can it read? Sandboxing the agent

An agent with a shell can read whatever your user can read, which on a workstation includes SSH keys, cloud
credentials, kubeconfigs and every `.env` in every checkout. Sandboxes help, and their defaults are not enough.

## The mental model

- **Reads are the leak.** Default `srt` and Claude Code sandboxes restrict writes but leave most reads open,
  including `~/.ssh`, unless you deny them. `sandbox/srt-settings.json` denies every credential path by name
  and by pattern.
- **Egress is an allowlist.** The agent may reach localhost, the package registries and GitHub, and nothing
  else; the cloud metadata endpoint (`169.254.169.254`) is denied explicitly.
- **A sandbox that blocks everything gets turned off.** The registries must stay reachable, or the next
  commit is `--no-sandbox`.
- **Prove it before you trust it.** `run-sandboxed.sh --verify-only` tries to read `~/.ssh`, reach the
  metadata endpoint and reach PyPI, and refuses to start the agent unless the first two fail and the last works.

## Do it

```
cd tracks/linux-ai-era
./setup/02-agents.sh              # installs srt and copies the settings to ~/.srt-settings.json
make sandbox-verify               # the five checks, before any agent runs
./sandbox/run-sandboxed.sh opencode
```

On Ubuntu 24.04 and later, AppArmor restricts unprivileged user namespaces; `00-prereqs.sh` installs a
profile that allows `bwrap` specifically instead of switching the restriction off host-wide.
