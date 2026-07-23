#!/bin/bash
# Swarm Focus Timer with App Blocking
# Usage: adb shell sh /data/local/tmp/focus_timer.sh <minutes> <task_name>

MINUTES="${1:-25}"
TASK="${2:-Focus Session}"
SECONDS=$((MINUTES * 60))
INTERVAL=60

# Distracting apps to block during focus
BLOCKED_APPS="com.instagram.android com.twitter.android com.netflix.mediaclient com.snapchat.android com.facebook.katana com.facebook.orca com.google.android.apps.youtube.music com.samsung.android.game.gamehome"

echo "FOCUS: $TASK ($MINUTES min)"
echo "DND_ON"
echo "BLOCKING_APPS: $BLOCKED_APPS"

# Enable Do Not Disturb
cmd notification set_dnd on

# Disable distracting apps
for app in $BLOCKED_APPS; do
    pm disable-user --user 0 "$app" 2>/dev/null
done

# Notify start
cmd notification post focus_start -t "Focus Mode ON" -i "@android:drawable/ic_lock_idle_alarm" "$TASK - $MINUTES min"

ELAPSED=0
REMAINING=$SECONDS

while [ $REMAINING -gt 0 ]; do
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
    REMAINING=$((SECONDS - ELAPSED))
    
    if [ $REMAINING -le 0 ]; then
        break
    fi
    
    RMIN=$((REMAINING / 60))
    RSEC=$((REMAINING % 60))
    
    cmd notification post focus_tick -t "Focus: $TASK" -i "@android:drawable/ic_lock_idle_alarm" "${RMIN}m ${RSEC}s remaining"
done

# Session complete - re-enable apps
for app in $BLOCKED_APPS; do
    pm enable "$app" 2>/dev/null
done

cmd notification post focus_done -t "Focus Complete!" -i "@android:drawable/ic_input_add" "$TASK - $MINUTES min done!"
cmd notification set_dnd off

echo "FOCUS_COMPLETE: $TASK ($MINUTES min)"
echo "APPS_REENABLED"
