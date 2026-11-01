# One target per lab. Everything prints the numbers the episode puts on screen.
SHELL := /bin/bash
.PHONY: help prereqs ollama agents sandbox-verify lab01 lab01-agent lab05-key lab06-up lab06-drill lab06-down lab07 lab08 score clean

help:
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n",$$1,$$2}'


prereqs:        ## base packages, Docker, bwrap AppArmor profile (sudo)
	sudo ./setup/00-prereqs.sh
ollama:         ## Ollama as a hardened systemd unit + the two Apache-2.0 models (sudo)
	sudo ./setup/01-ollama-systemd.sh
agents:         ## OpenCode, aichat, llm, k8sgpt, holmes, kubectl-ai, srt, checkov, trivy
	./setup/02-agents.sh
sandbox-verify: ## prove the srt deny list and egress allowlist work
	./sandbox/run-sandboxed.sh --verify-only

lab01:          ## validate the nginx task, then run it by hand (timed)
	./labs/lab01-baseline/run.sh validate && ./labs/lab01-baseline/run.sh manual && ./labs/lab01-baseline/run.sh report
lab01-agent:    ## same task with OpenCode on the local model (MODEL=ollama/devstral:24b)
	./labs/lab01-baseline/run.sh agent $(MODEL) && ./labs/lab01-baseline/run.sh report

lab05-key:      ## issue the 1-hour lab SSH key for the broken VMs
	./labs/lab05-broken-vms/agent-over-ssh.sh issue-key

lab06-up:       ## kind cluster with audit log, three seeded faults, read-only RBAC
	./labs/lab06-k8s-incident/scripts/drill.sh up
lab06-drill:    ## k8sgpt, holmes without runbook, holmes with runbook, then audit the API calls
	./labs/lab06-k8s-incident/scripts/drill.sh prove-ro
	./labs/lab06-k8s-incident/scripts/drill.sh k8sgpt
	./labs/lab06-k8s-incident/scripts/drill.sh holmes-bare
	./labs/lab06-k8s-incident/scripts/drill.sh holmes-rb
	./labs/lab06-k8s-incident/scripts/drill.sh audit
lab06-down:
	./labs/lab06-k8s-incident/scripts/drill.sh down

lab07:          ## poisoned-log red team across local (and optional API) models; executes nothing
	cd labs/lab07-poisoned-logs && TRIALS=$(or $(TRIALS),10) ./run-matrix.sh

lab08:          ## IaC gate on the agent-written Terraform
	./labs/lab08-iac-gates/gate.sh || true

score:          ## score a lab from an evidence file: make score E=path/to/evidence.json
	python3 rubric/score.py $(or $(E),rubric/example-evidence.json)

clean:
	rm -rf /tmp/agent-work labs/lab01-baseline/results.csv labs/lab06-k8s-incident/results.csv
