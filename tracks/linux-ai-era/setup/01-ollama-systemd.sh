#!/usr/bin/env bash
# 01-ollama-systemd.sh — install Ollama as a hardened systemd service and pull the course models.
# Run as root. Idempotent.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "run as root"; exit 1; fi

MODELS=("devstral:24b" "gpt-oss:20b")        # both Apache-2.0 weights, ~14 GB each
OLLAMA_USER=ollama
OLLAMA_HOME=/var/lib/ollama

echo "==> Installing Ollama"
if ! command -v ollama >/dev/null; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
id -u "$OLLAMA_USER" >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin -d "$OLLAMA_HOME" -m "$OLLAMA_USER"
install -d -o "$OLLAMA_USER" -g "$OLLAMA_USER" "$OLLAMA_HOME"

# Add the service user to the GPU device groups (varies by distro)
for g in video render; do getent group "$g" >/dev/null && usermod -aG "$g" "$OLLAMA_USER"; done

echo "==> Writing hardened unit override"
install -d /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf <<EOF
[Service]
User=$OLLAMA_USER
Group=$OLLAMA_USER
# Bind to localhost only. Never expose 11434. (Sysdig, 2026: ~175k public Ollama instances.)
Environment=OLLAMA_HOST=127.0.0.1:11434
Environment=OLLAMA_MODELS=$OLLAMA_HOME/models
# Keep one model resident for 30 min so OpenCode does not pay a cold start on every call
Environment=OLLAMA_KEEP_ALIVE=30m
Environment=OLLAMA_NUM_PARALLEL=2
Environment=OLLAMA_MAX_LOADED_MODELS=1
# Flash attention + q8 KV cache: fits a 24b model with 32k context on a 24 GB card
Environment=OLLAMA_FLASH_ATTENTION=1
Environment=OLLAMA_KV_CACHE_TYPE=q8_0

# cgroup v2 resource control: the lab host is shared with the agent and kind
MemoryMax=48G
MemoryHigh=44G
CPUWeight=80
TasksMax=4096

# Hardening (systemd-analyze security ollama.service should report < 5.0)
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$OLLAMA_HOME
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
RestrictRealtime=yes
LockPersonality=yes
SystemCallArchitectures=native
# GPU access needs /dev; keep DevicePolicy closed and allow the NVIDIA/DRM nodes explicitly
DevicePolicy=closed
DeviceAllow=/dev/nvidiactl rw
DeviceAllow=/dev/nvidia-uvm rw
DeviceAllow=/dev/nvidia-uvm-tools rw
DeviceAllow=/dev/nvidia0 rw
DeviceAllow=/dev/nvidia1 rw
DeviceAllow=/dev/dri rw
DeviceAllow=/dev/kfd rw
EOF

systemctl daemon-reload
systemctl enable --now ollama
sleep 3
systemctl --no-pager --lines=5 status ollama || true

echo "==> Verifying localhost-only bind"
ss -ltnp | grep 11434 | grep -q 127.0.0.1 && echo "OK: bound to 127.0.0.1" || { echo "!! Ollama is not bound to localhost"; exit 1; }

echo "==> Pulling course models (two Apache-2.0 picks, ~28 GB total)"
for m in "${MODELS[@]}"; do
  sudo -u "$OLLAMA_USER" OLLAMA_HOST=127.0.0.1:11434 ollama pull "$m"
done

echo "==> Smoke test"
curl -s http://127.0.0.1:11434/api/generate -d '{"model":"gpt-oss:20b","prompt":"Reply with exactly: OK","stream":false}' | jq -r .response

echo "==> Security score (lower is better)"
systemd-analyze security ollama.service | tail -1

echo "Done. Models:"; sudo -u "$OLLAMA_USER" OLLAMA_HOST=127.0.0.1:11434 ollama list
