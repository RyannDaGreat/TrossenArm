#!/usr/bin/env bash
# Command: build the viewer and run its single hardware-owning Python backend.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export UV_CACHE_DIR="$ROOT/agents/.scratchpad/uv-cache"
export UV_PYTHON_INSTALL_DIR="$ROOT/agents/.scratchpad/uv-python"
PORT="${TROSSEN_WEB_PORT:-28347}"
printf 'Building the Svelte viewer; stop all other camera/robot owners before starting.\n'
npm ci --prefix web/source/frontend --no-audit --no-fund
npm run build --prefix web/source/frontend
printf 'Opening hardware once. Viewer: http://127.0.0.1:%s\n' "$PORT"
exec uv run --extra robot --locked uvicorn server:app --app-dir web/source/backend --host 127.0.0.1 --port "$PORT" --ws-per-message-deflate false
