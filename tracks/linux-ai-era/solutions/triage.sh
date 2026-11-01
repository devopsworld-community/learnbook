#!/usr/bin/env bash
# triage.sh: Brendan Gregg's 60-second Linux checklist, saved so you never have to remember it at 3 am.
# Usage: sudo ./triage.sh > "triage-$(hostname)-$(date +%s).txt"
set -u

run() {
  printf '\n=== %s\n' "$*"
  timeout 15 "$@" 2>&1 | tail -n 40
}

run uptime
run dmesg -T
run vmstat 1 5
run mpstat -P ALL 1 3
run pidstat 1 3
run iostat -xz 1 3
run free -m
run sar -n DEV 1 3
run sar -n TCP,ETCP 1 3
run top -b -n 1
