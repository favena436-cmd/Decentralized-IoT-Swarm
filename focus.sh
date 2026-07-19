#!/bin/bash
# Swarm Focus - Push a focus session to your phone with app blocking
# Usage: ./focus.sh <minutes> <task_name>
# Example: ./focus.sh 25 "Working on Dictate overlay"

PHONE="192.168.12.190:5555"
TIMER_SCRIPT="/data/local/tmp/focus_timer.sh"
BLOCKLIST_FILE="/home/jimmy/swarm_node/shared/knowledge/focus_blocklist.txt"

MINUTES="${1:-25}"
TASK="${2:-Focus Session}"

# Validate input
if ! [[ "$MINUTES" =~ ^[0-9]+$ ]] || [ "$MINUTES" -lt 1 ] || [ "$MINUTES" -gt 180 ]; then
    echo "Error: minutes must be 1-180"
    exit 1
fi

# Initialize blocklist if not exists
if [ ! -f "$BLOCKLIST_FILE" ]; then
    cat > "$BLOCKLIST_FILE" << 'EOF'
com.instagram.android
com.twitter.android
com.netflix.mediaclient
com.snapchat.android
com.facebook.katana
com.facebook.orca
com.google.android.apps.youtube.music
com.samsung.android.game.gamehome
EOF
fi

echo "=========================================="
echo "  FOCUS TIMER: $MINUTES min"
echo "  Task: $TASK"
echo "  Phone: $PHONE"
echo "  Blocked apps: $(wc -l < "$BLOCKLIST_FILE")"
echo "=========================================="

# Push the timer script to the phone
echo "Pushing focus timer to phone..."
adb -s "$PHONE" push /home/jimmy/swarm_node/focus_timer.sh "$TIMER_SCRIPT" 2>/dev/null
adb -s "$PHONE" shell "chmod +x $TIMER_SCRIPT" 2>/dev/null

# Execute the timer on the phone
echo "Starting focus session on phone..."
echo "  - DND mode ON (notifications silenced)"
echo "  - Distracting apps DISABLED"
echo "  - Progress updates every minute"
echo ""
echo "To cancel: ./focus_cancel.sh"
echo ""

adb -s "$PHONE" shell "sh $TIMER_SCRIPT $MINUTES '$TASK'" &
PHONE_PID=$!

# Wait for completion
wait $PHONE_PID 2>/dev/null

echo ""
echo "Focus session ended. All apps re-enabled."
