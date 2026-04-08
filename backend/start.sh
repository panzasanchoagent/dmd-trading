#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"
RELOAD="${TRIGGER_RELOAD:-0}"

log() {
  printf '[Trigger backend] %s\n' "$1"
}

fail() {
  printf '[Trigger backend] ERROR: %s\n' "$1" >&2
  exit 1
}

resolve_venv() {
  if [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
    printf '%s\n' "$SCRIPT_DIR/venv"
    return 0
  fi

  if [ -x "$PROJECT_DIR/venv/bin/python" ]; then
    printf '%s\n' "$PROJECT_DIR/venv"
    return 0
  fi

  return 1
}

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  log "Loaded environment from $ENV_FILE"
else
  log "No backend .env found, relying on current shell environment"
fi

if [ -z "${ARETE_SUPABASE_KEY:-}" ] && command -v security >/dev/null 2>&1; then
  ARETE_SUPABASE_KEY="$(security find-generic-password -s "supabase-arete-anon" -a "arete" -w 2>/dev/null || true)"
  if [ -n "$ARETE_SUPABASE_KEY" ]; then
    export ARETE_SUPABASE_KEY
    log "Loaded ARETE_SUPABASE_KEY from macOS Keychain"
  fi
fi

VENV_DIR="$(resolve_venv || true)"
[ -n "$VENV_DIR" ] || fail "Python virtualenv not found. Expected backend/venv or ../venv"

if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    log "Backend already running on port ${PORT}, nothing to do"
    exit 0
  fi

  fail "Port ${PORT} is already in use by another process. Free it first or run with PORT=<port>"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
cd "$SCRIPT_DIR"

UVICORN_ARGS=(main:app --host "$HOST" --port "$PORT")
if [ "$RELOAD" = "1" ]; then
  UVICORN_ARGS+=(--reload)
fi

log "Starting FastAPI on ${HOST}:${PORT}"
log "Docs: http://127.0.0.1:${PORT}/docs"
exec uvicorn "${UVICORN_ARGS[@]}"
