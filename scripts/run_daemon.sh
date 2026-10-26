#!/usr/bin/env bash
# ==============================================================================
# ZaxterLab Daemon Management Script
# Usage: ./scripts/run_daemon.sh {start|stop|restart|status}
# ==============================================================================

set -euo pipefail

PID_FILE="/tmp/zaxterlab.pid"
LOG_FILE="/tmp/zaxterlab.log"
PORT=8000
HOST="127.0.0.1"

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "ZaxterLab is already running with PID $(cat "$PID_FILE")."
        exit 0
    fi

    echo "Starting ZaxterLab API & Dashboard on http://$HOST:$PORT..."
    nohup python3 -m zaxterlab --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1

    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "ZaxterLab successfully started with PID $(cat "$PID_FILE")."
        echo "Log file: $LOG_FILE"
    else
        echo "Failed to start ZaxterLab. Check logs at $LOG_FILE."
        exit 1
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "Stopping ZaxterLab (PID $PID)..."
        kill "$PID" 2>/dev/null || true
        rm -f "$PID_FILE"
        echo "ZaxterLab stopped."
    else
        echo "ZaxterLab PID file not found. Process may not be running."
    fi
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "ZaxterLab is running (PID $(cat "$PID_FILE"))."
        curl -s "http://$HOST:$PORT/api/health" | grep -o '"status": *"[^"]*"' || true
    else
        echo "ZaxterLab is not running."
    fi
}

case "${1:-status}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
