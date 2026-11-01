# Gate or go: an agent on a broken VM, over SSH

Lab 5 boots three VMs with planted faults and lets the agent look, never touch:

- **VM 1 (Debian 13):** `metrics-collector` crash-loops because its unit's `MemoryMax` is below its working
  set (chapter 4's drop-in).
- **VM 2 (Amazon Linux 2023):** the persisted nftables ruleset has a port typo for SSH and drops the app
  port (chapter 6's ruleset).
- **VM 3 (Rocky 10):** logrotate silently fails for three reasons at once: directory ownership, the `create`
  mode, and an SELinux label (chapter 5, plus one more layer).

## The pattern

`agent-over-ssh.sh` gives the agent one tool, `vm <command>`. It uses a one-hour lab key, matches every
command against `ALLOW_RE` and `DENY_RE`, filters secrets out of the output, and logs every call to
`/tmp/agent-work/ssh-tool.log`. Anything that changes the VM is refused and must come back as a proposed
Ansible task, which **you** run with `--check --diff` first.

```
cd tracks/linux-ai-era
make lab05-key                                  # the one-hour lab key
./labs/lab05-broken-vms/agent-over-ssh.sh run <vm-ip> "metrics-collector keeps restarting"
./labs/lab05-broken-vms/agent-over-ssh.sh apply <vm-ip> labs/lab05-broken-vms/solutions/fix-oom.yml
./labs/lab05-broken-vms/tests/test-vm.sh oom <vm-ip>
```

The allowlist is the control. The model is an operator who might be fooled.
