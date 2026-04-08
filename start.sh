#!/bin/bash
#
# Trigger (Trading Journal) - Start Script
# Runs both backend (FastAPI) and frontend (Next.js)
#
# Usage:
#   ./start.sh           # Start both services
#   ./start.sh backend   # Start backend only
#   ./start.sh frontend  # Start frontend only
#   ./start.sh stop      # Stop all services
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# PID files
BACKEND_PID_FILE="$SCRIPT_DIR/.backend.pid"
FRONTEND_PID_FILE="$SCRIPT_DIR/.frontend.pid"
BACKEND_LOG_FILE="$SCRIPT_DIR/.backend.log"
FRONTEND_LOG_FILE="$SCRIPT_DIR/.frontend.log"

log_info() {
    echo -e "${GREEN}[Trigger]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[Trigger]${NC} $1"
}

log_error() {
    echo -e "${RED}[Trigger]${NC} $1"
}

wait_for_url() {
    local url="$1"
    local label="$2"
    local attempts="${3:-20}"

    for _ in $(seq 1 "$attempts"); do
        if curl -fsS "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done

    log_error "$label did not become ready: $url"
    return 1
}

resolve_backend_venv() {
    if [ -x "$BACKEND_DIR/venv/bin/python" ]; then
        echo "$BACKEND_DIR/venv"
        return 0
    fi

    if [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
        echo "$SCRIPT_DIR/venv"
        return 0
    fi

    echo "$BACKEND_DIR/venv"
}

start_backend() {
    log_info "Starting backend (FastAPI on port 8001)..."

    cd "$BACKEND_DIR"

    local venv_dir
    venv_dir="$(resolve_backend_venv)"

    # Check/create venv
    if [ ! -d "$venv_dir" ]; then
        log_warn "Virtual environment not found. Creating at $venv_dir ..."
        python3 -m venv "$venv_dir"
        source "$venv_dir/bin/activate"
        pip install -r requirements.txt
    else
        source "$venv_dir/bin/activate"
    fi

    # Start uvicorn in background, bind to all interfaces for Tailscale access
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload > "$BACKEND_LOG_FILE" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"

    if ! wait_for_url "http://127.0.0.1:8001/health" "Backend"; then
        log_error "Backend failed to boot. Last backend log lines:"
        tail -n 40 "$BACKEND_LOG_FILE" 2>/dev/null || true
        exit 1
    fi

    log_info "Backend started (PID: $(cat "$BACKEND_PID_FILE"))"
    log_info "  → Local:     http://localhost:8001"
    log_info "  → Tailscale: http://<mac-mini-tailscale-ip>:8001"
    log_info "  → Docs:      http://localhost:8001/docs"
}

start_frontend() {
    log_info "Starting frontend (Next.js on port 3001)..."

    cd "$FRONTEND_DIR"

    # Check node_modules
    if [ ! -d "node_modules" ]; then
        log_warn "node_modules not found. Running npm install..."
        npm install
    fi

    # Start Next.js in background
    npm run dev > "$FRONTEND_LOG_FILE" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"

    if ! wait_for_url "http://127.0.0.1:3001" "Frontend"; then
        log_error "Frontend failed to boot. Last frontend log lines:"
        tail -n 40 "$FRONTEND_LOG_FILE" 2>/dev/null || true
        exit 1
    fi

    log_info "Frontend started (PID: $(cat "$FRONTEND_PID_FILE"))"
    log_info "  → Local:     http://localhost:3001"
}

stop_services() {
    log_info "Stopping Trigger services..."
    
    if [ -f "$BACKEND_PID_FILE" ]; then
        PID=$(cat "$BACKEND_PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            log_info "Backend stopped (PID: $PID)"
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    
    if [ -f "$FRONTEND_PID_FILE" ]; then
        PID=$(cat "$FRONTEND_PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            log_info "Frontend stopped (PID: $PID)"
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # Also kill any orphaned processes on these ports
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true
    lsof -ti:3001 | xargs kill -9 2>/dev/null || true
    
    log_info "All services stopped."
}

status() {
    echo ""
    log_info "=== Trigger Status ==="
    
    if [ -f "$BACKEND_PID_FILE" ] && kill -0 "$(cat $BACKEND_PID_FILE)" 2>/dev/null; then
        log_info "Backend:  ✓ Running (PID: $(cat $BACKEND_PID_FILE))"
    else
        log_warn "Backend:  ✗ Not running"
    fi
    
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 "$(cat $FRONTEND_PID_FILE)" 2>/dev/null; then
        log_info "Frontend: ✓ Running (PID: $(cat $FRONTEND_PID_FILE))"
    else
        log_warn "Frontend: ✗ Not running"
    fi
    echo ""
}

# Main
case "${1:-all}" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    stop)
        stop_services
        ;;
    status)
        status
        ;;
    all|"")
        log_info "=== Starting Trigger (Trading Journal) ==="
        echo ""
        start_backend
        sleep 2
        start_frontend
        echo ""
        log_info "=== Trigger is running ==="
        log_info "Backend:  http://localhost:8001 (API docs: /docs)"
        log_info "Frontend: http://localhost:3001"
        log_info ""
        log_info "Run './start.sh stop' to stop all services"
        log_info "Run './start.sh status' to check status"
        ;;
    *)
        echo "Usage: $0 {backend|frontend|stop|status|all}"
        exit 1
        ;;
esac
