#!/bin/bash
# Cancel a running focus session on the phone and re-enable apps
PHONE="192.168.12.190:5555"
BLOCKLIST_FILE="/home/jimmy/swarm_node/shared/knowledge/focus_blocklist.txt"

echo "Cancelling focus session..."

# Turn off DND
adb -s "$PHONE" shell "cmd notification set_dnd off" 2>/dev/null

# Re-enable all blocked apps
if [ -f "$BLOCKLIST_FILE" ]; then
    while read -r app; do
        [ -n "$app" ] && adb -s "$PHONE" shell "pm enable $app" 2>/dev/null
    done < "$BLOCKLIST_FILE"
    echo "All apps re-enabled."
fi

# Send cancellation notification
adb -s "$PHONE" shell "cmd notification post focus_cancel -t 'Focus Cancelled' -i '@android:drawable/ic_delete' 'Session ended - apps restored'" 2>/dev/null
echo "Focus session cancelled. DND OFF. Apps restored."
