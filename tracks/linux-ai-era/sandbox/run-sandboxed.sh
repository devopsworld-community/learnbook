#!/usr/bin/env bash
# run-sandboxed.sh — run any agent command under sandbox-runtime (srt) with the course deny list,
# then PROVE the sandbox works before handing control to the agent.
#
# Usage: sandbox/run-sandboxed.sh opencode            # interactive OpenCode in the sandbox
#        sandbox/run-sandboxed.sh aichat -e "find big files in /var/log"
#        sandbox/run-sandboxed.sh --verify-only
set -euo pipefail

SETTINGS="$HOME/.srt-settings.json"
[[ -f "$SETTINGS" ]] || { echo "missing $SETTINGS (run setup/02-agents.sh)"; exit 1; }
mkdir -p /tmp/agent-work

verify() {
  echo "==> Sandbox verification (these MUST fail inside the sandbox)"
  local fails=0
  # 1. Credential read must be denied
  if srt --settings "$SETTINGS" -- bash -c 'cat ~/.ssh/id_ed25519 ~/.ssh/id_rsa ~/.aws/credentials 2>/dev/null | head -c1' | grep -q .; then
    echo "  FAIL: a credential file was readable"; fails=$((fails+1))
  else
    echo "  OK:   ~/.ssh and ~/.aws unreadable"
  fi
  # 2. Cloud metadata endpoint must be blocked (SSRF / credential theft path)
  if srt --settings "$SETTINGS" -- bash -c 'curl -s --max-time 3 http://169.254.169.254/latest/meta-data/ >/dev/null 2>&1'; then
    echo "  FAIL: IMDS reachable"; fails=$((fails+1))
  else
    echo "  OK:   169.254.169.254 blocked"
  fi
  # 3. Arbitrary egress must be blocked
  if srt --settings "$SETTINGS" -- bash -c 'curl -s --max-time 3 https://example.com >/dev/null 2>&1'; then
    echo "  FAIL: example.com reachable (egress allowlist not enforced)"; fails=$((fails+1))
  else
    echo "  OK:   example.com blocked"
  fi
  # 4. Allowed egress must still work (otherwise the agent cannot pull packages)
  if srt --settings "$SETTINGS" -- bash -c 'curl -s --max-time 5 https://pypi.org/simple/ >/dev/null 2>&1'; then
    echo "  OK:   pypi.org reachable"
  else
    echo "  WARN: pypi.org not reachable (check network.allowedDomains or host proxy)"
  fi
  # 5. Write outside the allowlist must fail
  if srt --settings "$SETTINGS" -- bash -c 'echo x >> ~/.bashrc 2>/dev/null'; then
    echo "  FAIL: wrote to ~/.bashrc"; fails=$((fails+1))
  else
    echo "  OK:   ~/.bashrc read-only"
  fi
  (( fails == 0 )) || { echo "!! $fails sandbox checks failed. Do not run the agent."; exit 2; }
  echo "==> Sandbox verified."
}

verify
[[ "${1:-}" == "--verify-only" ]] && exit 0

echo "==> Launching under srt: $*"
echo "    (Ubuntu 24.04+: if bwrap fails with a userns error, see setup/00-prereqs.sh AppArmor profile)"
exec srt --settings "$SETTINGS" -- "$@"
