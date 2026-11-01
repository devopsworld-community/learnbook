#!/usr/bin/env bash
# Outcome tests for the three broken VMs. Run from the lab host: ./tests/test-vm.sh <oom|nft|logs> <host>
# Final-state checks only. Uses the lab key issued by agent-over-ssh.sh.
set -u
KEY=/tmp/agent-work/labkey/id_lab
r() { ssh -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "student@$HOST" -- "sudo -n $*" 2>/dev/null; }
pass=0; fail=0
check() { if eval "$2"; then echo "PASS  $1"; pass=$((pass+1)); else echo "FAIL  $1"; fail=$((fail+1)); fi; }
LAB=$1; HOST=$2

case "$LAB" in
  oom)
    check "service active"                      "[ \"\$(r systemctl is-active metrics-collector)\" = active ]"
    check "no restart in last 2 minutes"        "[ \"\$(r systemctl show -p NRestarts --value metrics-collector)\" -le 1 ] || sleep 120 && [ \"\$(r journalctl -u metrics-collector --since -2min | grep -c oom-kill)\" -eq 0 ]"
    check "fix is an override, not an edit"     "r test -d /etc/systemd/system/metrics-collector.service.d"
    check "MemoryMax still set (not removed)"   "[ \"\$(r systemctl show -p MemoryMax --value metrics-collector)\" != infinity ]"
    check "MemoryMax >= 256M"                   "[ \"\$(r systemctl show -p MemoryMax --value metrics-collector)\" -ge 268435456 ]"
    ;;
  nft)
    check "app reachable on :8080"              "[ \"\$(r curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/)\" = 200 ]"
    check "SSH rule correct in live ruleset"    "r nft list ruleset | grep -q 'tcp dport 22 accept'"
    check "SSH rule correct in persisted file"  "r grep -q 'tcp dport 22 accept' /etc/sysconfig/nftables.conf"
    check "8080 accepted in persisted file"     "r grep -q 'tcp dport 8080 accept' /etc/sysconfig/nftables.conf"
    check "default-drop policy preserved"       "r nft list chain inet filter input | grep -q 'policy drop'"
    check "persisted file parses"               "r nft -c -f /etc/sysconfig/nftables.conf"
    ;;
  logs)
    check "logrotate dry-run has no errors"     "! r logrotate -d /etc/logrotate.d/chatty 2>&1 | grep -qi error"
    check "create mode gives appuser write"     "r grep -Eq 'create 06[46]0 appuser appuser' /etc/logrotate.d/chatty"
    check "log dir owned by appuser"            "[ \"\$(r stat -c %U /srv/app/logs)\" = appuser ]"
    check "SELinux context is var_log_t"        "r ls -Zd /srv/app/logs | grep -q var_log_t"
    check "no fresh AVC denials for logrotate"  "! r ausearch -m avc -ts recent -c logrotate 2>/dev/null | grep -q denied"
    check "app still writing"                   "r test \$(( \$(date +%s) - \$(stat -c %Y /srv/app/logs/app.log) )) -lt 10"
    ;;
  *) echo "usage: $0 {oom|nft|logs} <host>"; exit 1;;
esac
echo "RESULT ${pass}/$((pass+fail))"; [ "$fail" -eq 0 ]
