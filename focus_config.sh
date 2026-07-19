#!/bin/bash
# Swarm Focus - Configure which apps to block during focus sessions
# Usage:
#   ./focus_config.sh list          - Show currently installed distracting apps
#   ./focus_config.sh add <package> - Add an app to block list
#   ./focus_config.sh remove <pkg>  - Remove an app from block list
#   ./focus_config.sh show          - Show current block list

BLOCKLIST_FILE="/home/jimmy/swarm_node/shared/knowledge/focus_blocklist.txt"

# Default block list
DEFAULT_BLOCKS="com.instagram.android
com.twitter.android
com.netflix.mediaclient
com.snapchat.android
com.facebook.katana
com.facebook.orca
com.google.android.apps.youtube.music
com.samsung.android.game.gamehome"

# Initialize blocklist if not exists
init_blocklist() {
    if [ ! -f "$BLOCKLIST_FILE" ]; then
        echo "$DEFAULT_BLOCKS" > "$BLOCKLIST_FILE"
    fi
}

case "$1" in
    list)
        echo "=== Installed packages (potential distractions) ==="
        adb -s 192.168.12.190:5555 shell "pm list packages -3" 2>/dev/null | grep -iE "social|media|video|game|music|reddit|tiktok|twitch|messenger|whatsapp|telegram|discord|pinterest|spotify|hulu|hbo|max|disney|peacock|crunchyroll|roblox|minecraft|fortnite|roblox" | sort
        ;;
    add)
        if [ -z "$2" ]; then
            echo "Usage: $0 add <package.name>"
            exit 1
        fi
        init_blocklist
        if grep -q "$2" "$BLOCKLIST_FILE"; then
            echo "$2 already in blocklist"
        else
            echo "$2" >> "$BLOCKLIST_FILE"
            echo "Added $2 to focus blocklist"
        fi
        ;;
    remove)
        if [ -z "$2" ]; then
            echo "Usage: $0 remove <package.name>"
            exit 1
        fi
        init_blocklist
        sed -i "/^${2}$/d" "$BLOCKLIST_FILE"
        echo "Removed $2 from focus blocklist"
        ;;
    show)
        init_blocklist
        echo "=== Focus Block List ==="
        cat "$BLOCKLIST_FILE"
        ;;
    *)
        echo "Usage: $0 {list|add <pkg>|remove <pkg>|show}"
        exit 1
        ;;
esac
