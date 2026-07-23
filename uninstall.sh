#!/bin/bash
# Uninstall swarm node: chat-node
# WARNING: This will remove all data in /home/jimmy/swarm_node

echo "This will remove the swarm node at /home/jimmy/swarm_node"
echo "All shared files, logs, and configuration will be deleted."
read -p "Are you sure? (y/N): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    # Stop if running
    if [ -f "/home/jimmy/swarm_node/scripts/node.pid" ]; then
        PID=$(cat "/home/jimmy/swarm_node/scripts/node.pid")
        kill "$PID" 2>/dev/null
        sleep 1
    fi

    # Remove systemd service if exists
    SERVICE="$HOME/.config/systemd/user/swarm-chat-node.service"
    if [ -f "$SERVICE" ]; then
        systemctl --user stop swarm-chat-node.service 2>/dev/null
        systemctl --user disable swarm-chat-node.service 2>/dev/null
        rm -f "$SERVICE"
        systemctl --user daemon-reload 2>/dev/null
    fi

    # Ask about data
    read -p "Delete shared data too? (y/N): " del_data
    if [ "$del_data" = "y" ] || [ "$del_data" = "Y" ]; then
        rm -rf "/home/jimmy/swarm_node"
        echo "Full removal complete."
    else
        # Keep shared data, remove scripts and config
        rm -rf "/home/jimmy/swarm_node/config"
        rm -rf "/home/jimmy/swarm_node/scripts"
        rm -f "/home/jimmy/swarm_node/node_agent.py"
        rm -f "/home/jimmy/swarm_node/health_check.py"
        rm -f "/home/jimmy/swarm_node/stop.sh"
        rm -f "/home/jimmy/swarm_node/uninstall.sh"
        echo "Node scripts removed. Shared data preserved at /home/jimmy/swarm_node/shared"
    fi
else
    echo "Cancelled."
fi
