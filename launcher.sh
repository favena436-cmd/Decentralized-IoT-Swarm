#!/usr/bin/env bash
# ============================================================
# Swarm Node Master Launcher
# One-click access to all swarm voice chat tools
# ============================================================

set -euo pipefail

SWARM_DIR="/home/jimmy/swarm_node"
SHARED_DIR="$SWARM_DIR/shared"
TASKS_DIR="$SHARED_DIR/tasks"
REGISTRY="$TASKS_DIR/registry.json"
VOICE_CHAT="/home/jimmy/hermes_voice_chat.py"
VOICE_TEST="/home/jimmy/teamwork_projects/xbox_ai_agent/voice-chat/test_voice_pipeline.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

show_menu() {
    clear
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║         🐝 SWARM NODE LAUNCHER v1.0            ║${NC}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} Hermes Voice Chat  — Talk to the swarm"
    echo -e "  ${GREEN}2)${NC} Voice Pipeline Test — Run STT/TTS diagnostics"
    echo -e "  ${GREEN}3)${NC} Agent Status       — View swarm agent status"
    echo -e "  ${GREEN}4)${NC} Swarm Console      — Terminal in swarm directory"
    echo -e "  ${YELLOW}5)${NC} Quit"
    echo ""
    echo -n "Select option [1-5]: "
}

run_voice_chat() {
    echo -e "${CYAN}Starting Hermes Voice Chat...${NC}"
    if [[ -f "$VOICE_CHAT" ]]; then
        gnome-terminal -- bash -c "python3 '$VOICE_CHAT'; echo ''; echo 'Press Enter to close...'; read"
    else
        echo -e "${RED}ERROR: $VOICE_CHAT not found${NC}"
        sleep 2
    fi
}

run_voice_test() {
    echo -e "${CYAN}Running Voice Pipeline Test...${NC}"
    if [[ -f "$VOICE_TEST" ]]; then
        gnome-terminal -- bash -c "bash '$VOICE_TEST'; echo ''; echo 'Press Enter to close...'; read"
    else
        echo -e "${RED}ERROR: $VOICE_TEST not found${NC}"
        sleep 2
    fi
}

show_status() {
    clear
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║           🐝 SWARM AGENT STATUS                ║${NC}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check voice daemon
    echo -e "${BOLD}── Voice Daemon ──${NC}"
    if pgrep -f "voice_daemon.py" > /dev/null 2>&1; then
        echo -e "  voice_daemon.py:    ${GREEN}● RUNNING${NC}"
        pgrep -af "voice_daemon.py" | head -3 | sed 's/^/    /'
    else
        echo -e "  voice_daemon.py:    ${RED}● STOPPED${NC}"
    fi
    echo ""

    # Check hermes_voice_chat.py
    echo -e "${BOLD}── Voice Chat Process ──${NC}"
    if pgrep -f "hermes_voice_chat.py" > /dev/null 2>&1; then
        echo -e "  hermes_voice_chat:  ${GREEN}● ACTIVE${NC}"
    else
        echo -e "  hermes_voice_chat:  ${YELLOW}● IDLE${NC}"
    fi
    echo ""

    # Registry
    echo -e "${BOLD}── Task Registry ──${NC}"
    if [[ -f "$REGISTRY" ]]; then
        echo -e "  Registry file:      ${GREEN}● FOUND${NC} ($REGISTRY)"
        # Parse with python3 for reliability
        python3 -c "
import json, sys
try:
    with open('$REGISTRY') as f:
        data = json.load(f)
    print(f\"  Node status:        {data.get('node_status', 'unknown')}\")
    print(f\"  Last updated:       {data.get('last_updated', 'unknown')}\")
    print(f\"  Active tasks:       {len(data.get('active_tasks', []))}\")
    print(f\"  Completed tasks:    {len(data.get('completed_tasks', []))}\")
    print(f\"  Registered agents:  {len(data.get('registered_agents', []))}\")
    print()
    agents = data.get('registered_agents', [])
    if agents:
        print('  Agents:')
        for a in agents:
            print(f\"    • {a.get('name','?')} — {a.get('role','?')}\")
    print()
    tasks = data.get('active_tasks', [])
    if tasks:
        print('  Active Tasks:')
        for t in tasks:
            print(f\"    • [{t.get('status','?')}] {t.get('title','?')}\")
            print(f\"      Assigned: {', '.join(t.get('assigned_to',[]))}\")
except Exception as e:
    print(f'  Error reading registry: {e}')
"
    else
        echo -e "  Registry file:      ${RED}● NOT FOUND${NC}"
    fi
    echo ""

    # Git status
    echo -e "${BOLD}── Git Status ──${NC}"
    if git -C "$SWARM_DIR" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
        local_branch=$(git -C "$SWARM_DIR" branch --show-current 2>/dev/null || echo "detached")
        echo -e "  Branch:             ${CYAN}$local_branch${NC}"
        changes=$(git -C "$SWARM_DIR" status --porcelain 2>/dev/null | wc -l)
        echo -e "  Uncommitted:        $changes file(s)"
    else
        echo -e "  $SWARM_DIR is not a git repository"
    fi
    echo ""
    echo -e "${BOLD}──────────────────────────────────────────────────${NC}"
    echo ""
    read -n 1 -s -r -p "Press any key to return to menu..."
}

run_console() {
    echo -e "${CYAN}Opening Swarm Console...${NC}"
    gnome-terminal --working-directory="$SWARM_DIR" -- bash -c "git status 2>/dev/null || echo '(not a git repo)'; echo ''; exec bash"
}

# Main loop
while true; do
    show_menu
    read -r choice
    case "$choice" in
        1) run_voice_chat ;;
        2) run_voice_test ;;
        3) show_status ;;
        4) run_console ;;
        5) echo -e "${CYAN}Goodbye! 🐝${NC}"; exit 0 ;;
        *) echo -e "${RED}Invalid option${NC}"; sleep 1 ;;
    esac
done
