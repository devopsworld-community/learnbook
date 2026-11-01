# Ship it: IaC and package gates

The last lab runs the gate every agent-written change should pass before a person reviews it:

- **Policy:** Checkov and `trivy config` on the Terraform, which arrives with the usual faults: permissive
  defaults, missing encryption and logging, hardcoded values, stale provider patterns.
- **Supply chain:** `check_package.py` refuses a dependency that does not exist on the registry, is younger
  than 90 days, or has fewer than 3 releases.
- **Pre-commit:** the same checks as a hook, so the gate runs whether or not anyone remembers.

```
cd tracks/linux-ai-era
make lab08            # prints a scoreboard line
make score E=rubric/example-evidence.json
```

## The rubric

Correctness 30, safety 25 (an automatic zero if a destructive or injected command ran, or a credential was
read), efficiency 10, explanation 20 (plan, why, evidence, rollback, NOT DONE), learning 15 (the delayed quiz).
You can get the fix right and still fail the lab, exactly as you would in production.
