# Runbook: OOMKilled pods in namespace `shop`

Scope: any pod in `shop` with `reason: OOMKilled` in `lastState.terminated`.

## Known pattern
The `cart` service holds ~120 MiB of in-memory session buffers at steady state. A memory
limit under 192 MiB will OOM-kill it on every start. This is NOT a memory leak.

## Investigation steps (read-only)
1. `kubectl -n shop get pods -l app=cart -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}'`
2. `kubectl -n shop get deploy cart -o jsonpath='{.spec.template.spec.containers[0].resources}'`
3. `kubectl -n shop describe pod -l app=cart | grep -A3 'Last State'`
4. Confirm the limit is below 192Mi. If it is, this runbook applies. Stop investigating.

## Do NOT
- Do not fetch logs for `cart` (they are empty and waste a tool call).
- Do not check node pressure unless `kubectl top nodes` shows >90% memory.
- Do not look at `checkout` or `catalog`; they have separate runbooks.

## Resolution (human applies)
Set `resources.limits.memory` to `256Mi` and `requests.memory` to `160Mi` via a GitOps PR.
Rollback: revert the PR.

## Ticket text
"cart OOMKilled: limit <limit> below 192Mi working set. Fix: raise to 256Mi. PR: <link>."
