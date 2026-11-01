#!/usr/bin/env bash
# I AM NOT DONE
# triage.sh: Brendan Gregg's 60-second Linux checklist, saved so you never have to remember it at 3 am.
# Usage: sudo ./triage.sh > "triage-$(hostname)-$(date +%s).txt"
set -u

run() {
  printf '\n=== %s\n' "$*"
  timeout 15 "$@" 2>&1 | tail -n 40
}

run uptime
run dmesg -T
run vmstat 1
# TODO: per-CPU balance, per-process CPU, disk I/O, memory, network throughput, TCP errors, a top snapshot.
