#!/bin/bash
# Stop swarm node: chat-node
PID_FILE="/home/jimmy/swarm_node/scripts/node.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping node (PID: $PID)..."
        kill "$PID"
        sleep 2
        if kill -0 "$PID" 2>/dev/null; then
            echo "Force killing..."
            kill -9 "$PID"
        fi
        echo "Node stopped."
    else
        echo "Node not running (stale PID file)"
    fi
    rm -f "$PID_FILE"
else
    echo "No PID file found. Node may not be running via launcher."
    echo "Try: pkill -f 'node_agent.py'"
fi
