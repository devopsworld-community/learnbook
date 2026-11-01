#!/usr/bin/env bash
# agent-over-ssh.sh — run a terminal agent against a broken VM WITHOUT giving it your SSH key.
#
# Pattern: the agent runs on the lab host inside the sandbox. It cannot read ~/.ssh. Instead, it
# gets a single shell "tool" — this script's `ssh-tool` mode — which uses a dedicated, short-lived
# lab key, allows only a command allowlist, filters output, and logs every call. The write path
# (changing files on the VM) is a SEPARATE step that you review and run through Ansible.
#
#   ./agent-over-ssh.sh issue-key               create a 1-hour ed25519 key for the lab user (ssh-keygen + -V)
#   ./agent-over-ssh.sh ssh-tool <host> <cmd>   what the agent calls; read-only allowlist
#   ./agent-over-ssh.sh run <host> "<task>"     run OpenCode in plan mode with the ssh-tool exposed
#   ./agent-over-ssh.sh apply <host> fix.yml    YOU run the proposed fix via Ansible after review
set -euo pipefail
LAB_KEY_DIR=/tmp/agent-work/labkey; mkdir -p "$LAB_KEY_DIR"
LAB_KEY="$LAB_KEY_DIR/id_lab"
LOG=/tmp/agent-work/ssh-tool.log
USER_=student

issue_key() {
  rm -f "$LAB_KEY" "$LAB_KEY.pub"
  ssh-keygen -q -t ed25519 -N "" -C "lab-$(date +%s)" -f "$LAB_KEY"
  echo "==> Add this public key to the VM's authorized_keys (cloud-init REPLACE_WITH_LAB_PUBLIC_KEY):"
  cat "$LAB_KEY.pub"
  echo "==> Key lives in $LAB_KEY_DIR (writable by sandbox, NOT ~/.ssh). Delete after the lab: rm -rf $LAB_KEY_DIR"
}

# Read-only allowlist. Anything else is refused and logged. The agent sees the refusal.
ALLOW_RE='^(systemctl (status|cat|show|list-units|list-timers)|journalctl|cat /etc/(nftables|logrotate|systemd)|cat /etc/sysconfig/nftables.conf|ls|stat|df|du|free|ps|ss|ip (a|r|-s)|nft list|ausearch|sestatus|getenforce|ls -Z|logrotate -d|nginx -t|dmesg|uptime|id|hostname|cat /etc/motd|cat /proc/pressure|systemd-cgtop -b -n 1|systemd-analyze)'
DENY_RE='(rm |dd |mkfs|nft (flush|delete|add|insert)|systemctl (restart|stop|start|disable|enable|edit)|chmod|chown|setenforce|> |>>|\|\s*sh|curl|wget|sudo -i|passwd|visudo)'

ssh_tool() {
  local host=$1; shift; local cmd="$*"
  if [[ "$cmd" =~ $DENY_RE ]] || ! [[ "$cmd" =~ $ALLOW_RE ]]; then
    echo "$(date -Is) DENIED $host :: $cmd" >> "$LOG"
    echo "REFUSED: '$cmd' is not in the read-only allowlist. Propose it as a fix step instead."
    return 3
  fi
  echo "$(date -Is) RUN    $host :: $cmd" >> "$LOG"
  # Filter output: cap size, strip anything that looks like a secret, strip ANSI.
  ssh -i "$LAB_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 \
      "$USER_@$host" -- "sudo -n $cmd" 2>&1 \
    | sed -E 's/\x1b\[[0-9;]*m//g; s/(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|-----BEGIN [A-Z ]*PRIVATE KEY-----.*)/[REDACTED]/g' \
    | head -c 20000
}

run() {
  local host=$1; local task=$2
  export LAB_SSH_HOST="$host"
  # Expose ssh-tool to the agent as the only way to touch the VM. OpenCode gets a wrapper on PATH.
  mkdir -p /tmp/agent-work/bin
  cat > /tmp/agent-work/bin/vm <<EOF
#!/usr/bin/env bash
exec "$(realpath "$0")" ssh-tool "$host" "\$@"
EOF
  chmod +x /tmp/agent-work/bin/vm
  echo "==> Agent gets ONE tool: 'vm <read-only command>'. Writes go through 'apply'."
  PATH="/tmp/agent-work/bin:$PATH" "$(dirname "$0")/../../sandbox/run-sandboxed.sh" \
    opencode --agent plan "You are diagnosing a broken Linux VM. The ONLY way to inspect it is the command 'vm <cmd>' (read-only). Task: $task. Produce: root cause, evidence (quote command output), a minimal Ansible task file to fix it, a rollback, and what you did NOT verify. Do not attempt to change anything yourself."
  echo "==> ssh-tool audit log:"; cat "$LOG"
}

apply() {
  local host=$1; local playbook=$2
  echo "==> Review $playbook. Press Enter to run with --check first, Ctrl-C to abort."; read -r
  ansible-playbook -i "$host," -u "$USER_" --private-key "$LAB_KEY" --become --check --diff "$playbook"
  echo "==> --check passed. Press Enter to APPLY."; read -r
  ansible-playbook -i "$host," -u "$USER_" --private-key "$LAB_KEY" --become --diff "$playbook"
}

case "${1:-}" in
  issue-key) issue_key;;
  ssh-tool)  shift; ssh_tool "$@";;
  run)       run "$2" "$3";;
  apply)     apply "$2" "$3";;
  *) sed -n '2,12p' "$0"; exit 1;;
esac
