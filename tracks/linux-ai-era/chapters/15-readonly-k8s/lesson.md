# Read-only on call: Kubernetes with k8sgpt and HolmesGPT

Lab 6 builds a kind cluster with an audit log, seeds three faults in namespace `shop` (an OOMKilled pod, an
ImagePullBackOff and a Service whose selector matches nothing), and gives the investigators identities that
can read and cannot write.

## The pattern

- **Read-only is a verb list on the server**, not a flag on the agent. The ClusterRole omits secrets,
  `pods/exec` and every write verb; `drill.sh prove-ro` runs `kubectl auth can-i` for each identity before
  any agent starts.
- **Runbooks tell the agent what not to do.** HolmesGPT runs twice, without and with `runbooks/`, and the
  audit log counts the API calls each run made.
- **Know what your privacy flag covers.** k8sgpt's `--anonymize` masks some resource kinds and not others.

```
cd tracks/linux-ai-era
make lab06-up        # kind cluster, audit policy, faults, read-only RBAC
make lab06-drill     # prove-ro, k8sgpt, holmes without and with runbooks, then the audit summary
make lab06-down
```
