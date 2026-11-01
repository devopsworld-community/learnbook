#!/usr/bin/env bash
# gate.sh — the full IaC gate the episode runs on agent output. Prints a scoreboard line.
set -uo pipefail
cd "$(dirname "$0")"
mkdir -p results
echo "==> terraform fmt/validate"
( cd terraform && terraform init -backend=false -input=false >/dev/null 2>&1 && terraform fmt -check -recursive && terraform validate ) ; tfrc=$?
echo "==> checkov"
checkov --config-file .checkov.yaml >/dev/null 2>&1; ckrc=$?
ckfail=$(jq '[.runs[].results[]] | length' results/results_sarif.sarif 2>/dev/null || echo "?")
echo "==> trivy config"
trivy config --severity HIGH,CRITICAL --exit-code 1 --quiet terraform >/dev/null 2>&1; tvrc=$?
echo "==> package gate (if a requirements file exists)"
[[ -f requirements.txt ]] && { python3 check_package.py --from-requirements requirements.txt >/dev/null; pkrc=$?; } || pkrc=0
printf '\nGATE  tf=%s  checkov=%s(%s findings)  trivy=%s  packages=%s  => %s\n' \
  "$([ $tfrc = 0 ] && echo pass || echo FAIL)" "$([ $ckrc = 0 ] && echo pass || echo FAIL)" "$ckfail" \
  "$([ $tvrc = 0 ] && echo pass || echo FAIL)" "$([ $pkrc = 0 ] && echo pass || echo FAIL)" \
  "$([ $((tfrc+ckrc+tvrc+pkrc)) = 0 ] && echo APPROVED-FOR-HUMAN-REVIEW || echo BLOCKED)"
exit $((tfrc+ckrc+tvrc+pkrc))
