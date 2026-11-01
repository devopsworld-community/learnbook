#!/usr/bin/env bash
# 02-agents.sh — install the open-source agent toolchain for the course. Run as your user.
# Installs: OpenCode, aichat, llm (+ llm-ollama), k8sgpt, HolmesGPT, kubectl-ai, kind, kubectl,
#           sandbox-runtime (srt), checkov, trivy, shellcheck already from prereqs.
# Pin versions where the upstream install path allows it. Re-verify versions before recording.
set -euo pipefail

BIN="$HOME/.local/bin"; mkdir -p "$BIN"; export PATH="$BIN:$PATH"
ARCH=$(uname -m); case "$ARCH" in x86_64) GOARCH=amd64;; aarch64) GOARCH=arm64;; *) echo "unsupported arch"; exit 1;; esac

echo "==> Node.js (needed by OpenCode and srt)"
if ! command -v node >/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]]; then
  curl -fsSL https://fnm.vercel.app/install | bash -s -- --skip-shell
  export PATH="$HOME/.local/share/fnm:$PATH"; eval "$(fnm env)"; fnm install 22; fnm use 22
fi

echo "==> OpenCode (MIT)"
curl -fsSL https://opencode.ai/install | bash
mkdir -p "$HOME/.config/opencode"
cp "$(dirname "$0")/opencode.json" "$HOME/.config/opencode/opencode.json"

echo "==> aichat (Apache-2.0/MIT) and llm (Apache-2.0)"
if ! command -v aichat >/dev/null; then
  AICHAT_VER=$(curl -s https://api.github.com/repos/sigoden/aichat/releases/latest | jq -r .tag_name)
  curl -fsSL "https://github.com/sigoden/aichat/releases/download/${AICHAT_VER}/aichat-${AICHAT_VER}-${ARCH}-unknown-linux-musl.tar.gz" | tar xz -C "$BIN" aichat
fi
mkdir -p "$HOME/.config/aichat"; cp "$(dirname "$0")/aichat-config.yaml" "$HOME/.config/aichat/config.yaml"
python3 -m pip install --user --upgrade llm && llm install llm-ollama

echo "==> kubectl + kind"
KVER=$(curl -Ls https://dl.k8s.io/release/stable.txt)
curl -fsSL "https://dl.k8s.io/release/${KVER}/bin/linux/${GOARCH}/kubectl" -o "$BIN/kubectl"; chmod +x "$BIN/kubectl"
curl -fsSL "https://kind.sigs.k8s.io/dl/latest/kind-linux-${GOARCH}" -o "$BIN/kind"; chmod +x "$BIN/kind"

echo "==> k8sgpt (Apache-2.0)"
K8SGPT_VER=$(curl -s https://api.github.com/repos/k8sgpt-ai/k8sgpt/releases/latest | jq -r .tag_name)
curl -fsSL "https://github.com/k8sgpt-ai/k8sgpt/releases/download/${K8SGPT_VER}/k8sgpt_Linux_${ARCH}.tar.gz" | tar xz -C "$BIN" k8sgpt
# Local backend: Ollama's OpenAI-compatible endpoint. No API key leaves the machine.
k8sgpt auth add --backend localai --model gpt-oss:20b --baseurl http://127.0.0.1:11434/v1 --password none || true

echo "==> HolmesGPT (Apache-2.0, CNCF Sandbox)"
python3 -m pip install --user --upgrade pipx; python3 -m pipx ensurepath
pipx install holmesgpt || pipx upgrade holmesgpt

echo "==> kubectl-ai (Apache-2.0)"
curl -fsSL https://raw.githubusercontent.com/GoogleCloudPlatform/kubectl-ai/main/install.sh | bash

echo "==> sandbox-runtime / srt (Apache-2.0, beta)"
npm install -g @anthropic-ai/sandbox-runtime
mkdir -p "$HOME/.config/srt"; cp "$(dirname "$0")/../sandbox/srt-settings.json" "$HOME/.srt-settings.json"

echo "==> IaC gates: checkov, trivy (Apache-2.0)"
pipx install checkov || pipx upgrade checkov
if ! command -v trivy >/dev/null; then
  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b "$BIN"
fi

echo
echo "==> Versions (put these on screen; re-run before every recording)"
for c in opencode aichat llm kubectl kind k8sgpt holmes kubectl-ai srt checkov trivy shellcheck bwrap; do
  printf '%-12s ' "$c"; ( "$c" --version 2>/dev/null || "$c" version 2>/dev/null || echo "not found" ) | head -1
done
echo
echo "Add to your shell rc if missing:  export PATH=\"$HOME/.local/bin:\$PATH\""
