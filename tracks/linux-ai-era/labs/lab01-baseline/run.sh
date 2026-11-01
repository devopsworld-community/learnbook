#!/usr/bin/env bash
# Lab 1 — the honest baseline. Same task three ways, three timings, three trajectories.
#   ./run.sh validate      build task, prove oracle passes and a no-op fails (Harbor validation rule)
#   ./run.sh manual        drop you into the broken container with a timer; run /tests/test.sh when done
#   ./run.sh agent [model] run OpenCode (plan mode -> you approve) inside the container against local Ollama
#   ./run.sh report        print the timings table for the on-screen scoreboard
set -euo pipefail
cd "$(dirname "$0")/task-nginx-config"
IMG=tdw/lab01-nginx
RESULTS=../results.csv
touch "$RESULTS"

build() { docker build -q -t "$IMG" . >/dev/null; }

validate() {
  build
  echo "==> Dummy (no change) must FAIL"
  docker run --rm "$IMG" /tests/test.sh && { echo "!! dummy passed; task is broken"; exit 1; } || echo "OK dummy fails"
  echo "==> Oracle must PASS"
  docker run --rm "$IMG" bash -c '/solution/solve.sh >/dev/null && /tests/test.sh' || { echo "!! oracle failed"; exit 1; }
  echo "==> Task valid."
}

timed_run() {  # $1=label $2...=command inside container
  local label=$1; shift
  build
  local cid; cid=$(docker run -d --add-host=host.docker.internal:host-gateway "$IMG")
  local start; start=$(date +%s)
  docker exec -it "$cid" "$@" || true
  local end; end=$(date +%s)
  local result; result=$(docker exec "$cid" /tests/test.sh | tail -1)
  docker rm -f "$cid" >/dev/null
  echo "$(date -Iseconds),$label,$((end-start)),$result" | tee -a "$RESULTS"
}

manual() {
  echo "You are on call. Read /instruction.md. Fix nginx. Type 'exit' when done."
  timed_run manual bash -c 'cat /instruction.md; echo; exec bash'
}

agent() {
  local model=${1:-ollama/devstral:24b}
  echo "==> Agent run with $model (OpenCode plan agent, you approve each command)"
  # OpenCode runs inside the task container, talking to Ollama on the host.
  timed_run "agent:$model" bash -c "
    apk add --no-cache nodejs npm bash >/dev/null 2>&1 || true
    curl -fsSL https://opencode.ai/install | bash >/dev/null 2>&1
    export PATH=\$HOME/.opencode/bin:\$PATH
    mkdir -p ~/.config/opencode && cp /work/setup/opencode.json ~/.config/opencode/ 2>/dev/null || true
    sed -i 's#127.0.0.1:11434#host.docker.internal:11434#' ~/.config/opencode/opencode.json 2>/dev/null || true
    cd / && opencode --agent plan --model $model 'Read /instruction.md and fix nginx. Follow /AGENTS.md if present.'
  "
}

report() {
  echo; printf '%-25s %-28s %8s  %s\n' timestamp mode seconds result
  awk -F, '{printf "%-25s %-28s %8s  %s\n",$1,$2,$3,$4}' "$RESULTS"
}

case "${1:-}" in
  validate) validate;;
  manual)   manual;;
  agent)    shift; agent "$@";;
  report)   report;;
  *) echo "usage: $0 {validate|manual|agent [model]|report}"; exit 1;;
esac
