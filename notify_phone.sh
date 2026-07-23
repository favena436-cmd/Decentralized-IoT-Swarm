#!/bin/bash
# Swarm Node - Phone Notification Script
# Sends push notifications to the connected Samsung Galaxy S24 via ADB

PHONE="192.168.12.190:5555"

notify_phone() {
    local title="${1:-Swarm Alert}"
    local message="${2:-No message provided}"
    local icon="${3:-@android:drawable/ic_dialog_info}"

    adb -s "$PHONE" shell "cmd notification post swarm_$(date +%s) -t '$title' -i '$icon' '$message'" 2>/dev/null
}

case "$1" in
    --alert|-a)
        notify_phone "Swarm Alert" "$2"
        echo "Alert sent to phone"
        ;;
    --task|-t)
        notify_phone "Task Update" "$2" "@android:drawable/ic_menu_agenda"
        echo "Task notification sent"
        ;;
    --success|-s)
        notify_phone "Task Complete" "$2" "@android:drawable/ic_input_add"
        echo "Success notification sent"
        ;;
    --error|-e)
        notify_phone "Error" "$2" "@android:drawable/ic_delete"
        echo "Error notification sent"
        ;;
    --status)
        echo "Checking phone connection..."
        adb -s "$PHONE" shell "echo connected" 2>/dev/null && echo "✅ Phone reachable" || echo "❌ Phone unreachable"
        ;;
    *)
        notify_phone "Swarm" "$1"
        echo "Notification sent to phone"
        ;;
esac
