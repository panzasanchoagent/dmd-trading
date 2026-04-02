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

log_info() {
    echo -e "${GREEN}[Trigger]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[Trigger]${NC} $1"
}

log_error() {
    echo -e "${RED}[Trigger]${NC} $1"
}

start_backend() {
    log_info "Starting backend (FastAPI on port 8001)..."
    
    cd "$BACKEND_DIR"
    
    # Check/create venv
    if [ ! -d "venv" ]; then
        log_warn "Virtual environment not found. Creating..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # Start uvicorn in background, bind to all interfaces for Tailscale access
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload &
    echo $! > "$BACKEND_PID_FILE"
    
    log_info "Backend started (PID: $(cat $BACKEND_PID_FILE))"
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
    npm run dev &
    echo $! > "$FRONTEND_PID_FILE"
    
    log_info "Frontend started (PID: $(cat $FRONTEND_PID_FILE))"
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
