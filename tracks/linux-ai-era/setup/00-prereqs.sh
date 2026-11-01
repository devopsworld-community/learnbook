#!/usr/bin/env bash
# 00-prereqs.sh — base packages for the lab machine.
# Supports Ubuntu 24.04/26.04 and Amazon Linux 2023. Run as root.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then echo "run as root (sudo $0)"; exit 1; fi

. /etc/os-release
echo "==> Detected: $PRETTY_NAME"

common_tools=(git curl jq make python3 shellcheck)

case "$ID" in
  ubuntu|debian)
    apt-get update
    apt-get install -y "${common_tools[@]}" python3-venv python3-pip \
      ca-certificates gnupg bubblewrap socat procps sysstat bpftrace \
      linux-tools-common iproute2 nftables
    # Docker CE
    if ! command -v docker >/dev/null; then
      install -m 0755 -d /etc/apt/keyrings
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" > /etc/apt/sources.list.d/docker.list
      apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    fi
    # Ubuntu 24.04+ restricts unprivileged user namespaces via AppArmor, which breaks
    # bubblewrap-based sandboxes (srt). Allow bwrap explicitly rather than disabling the restriction.
    if [[ -d /etc/apparmor.d ]] && ! [[ -f /etc/apparmor.d/bwrap ]]; then
      cat > /etc/apparmor.d/bwrap <<'EOF'
abi <abi/4.0>,
include <tunables/global>
profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
  include if exists <local/bwrap>
}
EOF
      apparmor_parser -r /etc/apparmor.d/bwrap || true
      echo "==> AppArmor profile for bwrap installed (allows userns for the sandbox)."
    fi
    ;;
  amzn)
    dnf install -y "${common_tools[@]}" python3-pip bubblewrap socat procps-ng sysstat \
      bpftrace perf iproute nftables docker
    systemctl enable --now docker
    ;;
  *)
    echo "Unsupported distro: $ID"; exit 1;;
esac

# cgroup v2 check: every lab assumes the unified hierarchy.
if [[ "$(stat -fc %T /sys/fs/cgroup)" != "cgroup2fs" ]]; then
  echo "!! /sys/fs/cgroup is not cgroup2fs. Labs assume cgroup v2. Fix the host first."
  exit 1
fi
echo "==> cgroup2fs confirmed"

# NVIDIA: report, do not install. Driver pinning is a deliberate decision (R580 LTS).
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
else
  echo "!! nvidia-smi not found. CPU-only inference is possible but slow. See setup/01-ollama-systemd.sh."
fi

usermod -aG docker "${SUDO_USER:-$USER}" || true
echo "==> Prereqs done. Log out and back in for docker group membership."
