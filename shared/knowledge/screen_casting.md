# Screen Casting

## Available Tool
- scrcpy 3.3.3 (latest, supports Android 16)
- Located: /usr/local/bin/scrcpy, /usr/local/bin/scrcpy-server
- ADB symlink: /usr/local/bin/adb → /usr/bin/adb

## Phone Connection
- WiFi ADB: 192.168.12.190:5555
- USB ADB: RFCWC1BW4DH
- Model: Samsung Galaxy S24 (SM-S921U), Android 16 (SDK 36)

## Casting Commands
- Start: /home/jimmy/swarm_node/phone_cast.sh
- Stop: /home/jimmy/swarm_node/phone_cast.sh --stop
- Script: /home/jimmy/swarm_node/phone_cast.sh

## scrcpy Options Used
- --max-size 420 (small window)
- --always-on-top (stays above other windows)
- -S (turn off phone screen while mirroring)
- --show-touches (show touch indicators)
- --max-fps 30
- --video-bitrate 8M

## Controls (inside window)
- MOD+B = Back
- MOD+H = Home
- MOD+S = Menu/Recent apps
- Ctrl+drag = Pinch to zoom
- Double-click border = Remove black borders

## Requirements
- ADB WiFi connection established (adb tcpip 5555 + adb connect)
- scrcpy v3.3.3+ for Android 16 compatibility (v3.3.1 failed with AbstractMethodError)
