#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

(
    cd "${repo_root}/codex-rs"
    cargo build -p codex-cli --bin codex
)

HTTP_PROXY=http://127.0.0.1:25345 \
HTTPS_PROXY=http://127.0.0.1:25345 \
ALL_PROXY=http://127.0.0.1:25345 \
NO_PROXY=localhost,127.0.0.1,::1 \
exec "${repo_root}/codex-rs/target/debug/codex" \
    --dangerously-bypass-approvals-and-sandbox "$@"
