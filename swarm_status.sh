#!/usr/bin/env bash
# Swarm Agent Status — displays status of all swarm agents
set -euo pipefail

REGISTRY="/home/jimmy/swarm_node/shared/tasks/registry.json"

echo "🐝 SWARM AGENT STATUS"
echo "======================"
echo ""

echo "── Voice Daemon ──"
if pgrep -f 'voice_daemon.py' > /dev/null 2>&1; then
    echo "  voice_daemon.py:    ● RUNNING"
    pgrep -af 'voice_daemon.py' | head -3 | sed 's/^/    /'
else
    echo "  voice_daemon.py:    ● STOPPED"
fi
echo ""

echo "── Voice Chat ──"
if pgrep -f 'hermes_voice_chat.py' > /dev/null 2>&1; then
    echo "  hermes_voice_chat:  ● ACTIVE"
else
    echo "  hermes_voice_chat:  ● IDLE"
fi
echo ""

echo "── Task Registry ──"
if [[ -f "$REGISTRY" ]]; then
    python3 -c "
import json
data = json.load(open('$REGISTRY'))
print(f'  Node status:       {data.get(\"node_status\", \"?\")}')
print(f'  Last updated:      {data.get(\"last_updated\", \"?\")}')
print(f'  Active tasks:      {len(data.get(\"active_tasks\", []))}')
print(f'  Completed tasks:   {len(data.get(\"completed_tasks\", []))}')
print(f'  Registered agents: {len(data.get(\"registered_agents\", []))}')
print()
for a in data.get('registered_agents', []):
    print(f'    • {a[\"name\"]} — {a[\"role\"]}')
print()
for t in data.get('active_tasks', []):
    print(f'    • [{t[\"status\"]}] {t[\"title\"]}')
"
else
    echo "  Registry: NOT FOUND"
fi
echo ""
echo "Press Enter to close..."
read
