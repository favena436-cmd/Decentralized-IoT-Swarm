#!/bin/bash
# Swarm Phone Screen Cast - Cast Android phone screen to a small window on your PC
# Requirements: ADB WiFi connection, scrcpy
# Usage: ./phone_cast.sh [options]
#   ./phone_cast.sh                - Start casting (default: small window, top-right)
#   ./phone_cast.sh --fullscreen   - Fullscreen mirror
#   ./phone_cast.sh --record        - Record to file
#   ./phone_cast.sh --stop          - Stop casting
#   ./phone_cast.sh --multi         - Cast multiple phones

set -e

# Configuration
WINDOW_WIDTH=420
WINDOW_HEIGHT=900
WINDOW_X=1480      # top-right of a 1920-width screen
WINDOW_Y=40
MAX_FPS=30
BITRATE="8M"
WINDOW_TITLE="Phone Screen"
ONTOP=true

# Color output
GREEN='\033[0;92m'
YELLOW='\033[93m'
RED='\033[91m'
CYAN='\033[96m'
NC='\033[0m'

log() { echo -e "${CYAN}[CAST]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }

# ─── Find connected phones ──────────────────────────────────────────────────

find_phones() {
    adb devices -l 2>/dev/null | grep -v "^List" | grep -v "^$" | awk '{print $1}'
}

find_wifi_phones() {
    adb devices -l 2>/dev/null | grep -v "^List" | grep -v "$" | grep ":" | awk '{print $1}'
}

find_usb_phones() {
    adb devices -l 2>/dev/null | grep -v "^List" | grep -v "^$" | grep -v ":" | awk '{print $1}'
}

# ─── Select phone ────────────────────────────────────────────────────────────

select_phone() {
    local phones=()
    local i=1
    
    echo ""
    echo "Connected Android phones:"
    echo ""
    
    while IFS= read -r phone; do
        if [ -n "$phone" ]; then
            phones+=("$phone")
            local model=$(adb -s "$phone" shell getprop ro.product.model 2>/dev/null || echo "unknown")
            if echo "$phone" | grep -q ":"; then
                echo "  $i) $phone (WiFi) - $model"
            else
                echo "  $i) $phone (USB) - $model"
            fi
            i=$((i + 1))
        fi
    done < <(find_phones)
    
    if [ ${#phones[@]} -eq 0 ]; then
        err "No phones connected via ADB."
        echo "  Connect a phone via USB with USB debugging enabled,"
        echo "  or run: adb connect <phone_ip>:5555"
        exit 1
    elif [ ${#phones[@]} -eq 1 ]; then
        SELECTED="${phones[0]}"
        ok "Auto-selected: $SELECTED"
    else
        echo ""
        read -rp "Select phone (1-${#phones[@]}): " choice
        SELECTED="${phones[$((choice - 1))]}"
    fi
}

# ─── Build scrcpy options ──────────────────────────────────────────────────

build_opts() {
    local opts="-s $1"
    
    # Window size
    if [ "$FULLSCREEN" = true ]; then
        opts="$opts -f"
    else
        opts="$opts --max-size $WINDOW_WIDTH"
        opts="$opts --window-width $WINDOW_WIDTH"
        opts="$opts --window-height $WINDOW_HEIGHT"
        opts="$opts --window-x $WINDOW_X"
        opts="$opts --window-y $WINDOW_Y"
    fi
    
    # Always on top
    if [ "$ONTOP" = true ] && [ "$FULLSCREEN" != true ]; then
        opts="$opts --always-on-top"
    fi
    
    # FPS limit
    opts="$opts --max-fps $MAX_FPS"
    
    # Bitrate (mirror quality)
    opts="$opts --video-bit-rate $BITRATE"
    
    # Turn off phone screen (saves battery)
    opts="$opts -S"
    
    # Show touches (useful for demos)
    opts="$opts --show-touches"
    
    # Window title
    opts="$opts --window-title '$WINDOW_TITLE'"
    
    # Recording
    if [ -n "$RECORD_FILE" ]; then
        opts="$opts --record='$RECORD_FILE'"
    fi
    
    # Disable screensaver
    opts="$opts --disable-screensaver"
    
    echo "$opts"
}

# ─── Cast a single phone ────────────────────────────────────────────────────

cast_phone() {
    local phone="$1"
    local model=$(adb -s "$phone" shell getprop ro.product.model 2>/dev/null || echo "Phone")
    local opts=$(build_opts "$phone")
    
    WINDOW_TITLE="$model"
    
    log "Starting screen cast for $model..."
    log "  Resolution: ${WINDOW_WIDTH}x${WINDOW_HEIGHT}"
    log "  FPS: $MAX_FPS | Bitrate: $BITRATE"
    log "  Position: ${WINDOW_X},${WINDOW_Y} (top-right)"
    log "  Always on top: $ONTOP"
    log "  Phone screen: OFF (mirroring only)"
    log ""
    log "Controls inside the window:"
    log "  MOD+B  = Back button"
    log "  MOD+H  = Home button"
    log "  MOD+S  = Menu/Recent apps"
    log "  Ctrl+Click-and-move = Pinch to zoom"
    log "  Double-click border = Remove letterboxing"
    log ""
    log "To quit: Close the window or press Ctrl+C"
    log ""
    
    # Build final opts with correct window title
    opts=$(build_opts "$phone")
    
    # Launch scrcpy
    eval "scrcpy $opts" &
    CAST_PID=$!
    
    ok "Screen cast running (PID: $CAST_PID)"
    
    # Wait for scrcpy to exit
    wait $CAST_PID 2>/dev/null
    
    ok "Screen cast ended."
}

# ─── Cast multiple phones (side by side) ────────────────────────────────────

cast_multi() {
    local phones=()
    while IFS= read -r phone; do
        [ -n "$phone" ] && phones+=("$phone")
    done < <(find_phones)
    
    if [ ${#phones[@]} -lt 2 ]; then
        err "Need at least 2 phones connected for multi-cast."
        exit 1
    fi
    
    log "Multi-cast: ${#phones[@]} phones"
    
    local cols=$(echo "sqrt(${#phones[@]})" | bc 2>/dev/null || echo "2")
    local cell_w=$((1920 / cols))
    local cell_h=$((cell_w * 2))  # approximate phone aspect ratio
    local i=0
    
    for phone in "${phones[@]}"; do
        local col=$((i % cols))
        local row=$((i / cols))
        local x=$((col * cell_w))
        local y=$((row * cell_h + 40))
        local model=$(adb -s "$phone" shell getprop ro.product.model 2>/dev/null || echo "Phone $i")
        
        scrcpy -s "$phone" \
            --max-size $((cell_w - 20)) \
            --window-width $((cell_w - 20)) \
            --window-height $((cell_h - 40)) \
            --window-x $x \
            --window-y $y \
            --window-title "$model" \
            --max-fps $MAX_FPS \
            --video-bit-rate "$BITRATE" \
            -S \
            --always-on-top \
            --show-touches \
            --disable-screensaver &
        
        log "  Started: $model at ${x},${y}"
        i=$((i + 1))
    done
    
    echo ""
    ok "All ${#phones[@]} phone casts running."
    echo "Press Ctrl+C to stop all."
    
    # Wait for all background processes
    wait
}

# ─── Stop all casts ─────────────────────────────────────────────────────────

stop_casts() {
    log "Stopping all screen casts..."
    pkill -f "scrcpy -s" 2>/dev/null && ok "Stopped." || warn "No active casts found."
}

# ─── Main ────────────────────────────────────────────────────────────────────

case "${1:-}" in
    --stop)
        stop_casts
        ;;
    --multi)
        cast_multi
        ;;
    --fullscreen)
        FULLSCREEN=true
        select_phone
        cast_phone "$SELECTED"
        ;;
    --record)
        RECORD_FILE="${2:-phone_cast_$(date +%Y%m%d_%H%M%S).mp4}"
        log "Recording to: $RECORD_FILE"
        select_phone
        cast_phone "$SELECTED"
        ;;
    --size)
        WINDOW_WIDTH="${2:-420}"
        WINDOW_HEIGHT="${3:-900}"
        select_phone
        cast_phone "$SELECTED"
        ;;
    --help|-h)
        echo "Swarm Phone Screen Cast"
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (none)            Start casting (small window, top-right)"
        echo "  --fullscreen      Fullscreen mirror"
        echo "  --record [file]   Record to MP4 file"
        echo "  --multi           Cast all connected phones (side by side)"
        echo "  --size W H        Custom window size (default: 420 900)"
        echo "  --stop            Stop all active casts"
        echo "  --help            Show this help"
        echo ""
        echo "Examples:"
        echo "  $0                # Small window mirror"
        echo "  $0 --fullscreen   # Full screen mirror"
        echo "  $0 --record demo.mp4"
        echo "  $0 --size 600 1200"
        echo "  $0 --multi        # All phones"
        ;;
    *)
        FULLSCREEN=false
        select_phone
        cast_phone "$SELECTED"
        ;;
esac
