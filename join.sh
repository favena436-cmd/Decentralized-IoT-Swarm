#!/usr/bin/env bash
#===============================================================================
# join.sh — Minimal one-liner wrapper for Swarm Node bootstrap
#
# Downloads bootstrap.sh if not present, then runs it with provided arguments.
# Designed for curl|bash usage.
#
# Usage:
#   curl -sSL https://your-server.com/join.sh | bash
#   curl -sSL https://your-server.com/join.sh | bash -s -- --role chat-node
#   curl -sSL https://your-server.com/join.sh | bash -s -- --check
#   ./join.sh --role xbox-hermes --orchestrator 192.168.1.100
#===============================================================================

set -euo pipefail

# Configuration
BOOTSTRAP_URL="${BOOTSTRAP_URL:-https://your-server.com/bootstrap.sh}"
BOOTSTRAP_SCRIPT="${BOOTSTRAP_SCRIPT:-bootstrap.sh}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
BOOTSTRAP_PATH="${SCRIPT_DIR}/${BOOTSTRAP_SCRIPT}"

# If BASH_SOURCE is not usable (piped), fall back to CWD
if [[ ! -f "${BOOTSTRAP_PATH}" && -f "./${BOOTSTRAP_SCRIPT}" ]]; then
    BOOTSTRAP_PATH="./${BOOTSTRAP_SCRIPT}"
fi

# Colors
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    GREEN='' YELLOW='' RED='' CYAN='' BOLD='' RESET=''
fi

log() { echo -e "${CYAN}[join.sh]${RESET} $*"; }
warn() { echo -e "${YELLOW}[join.sh WARN]${RESET} $*" >&2; }
err() { echo -e "${RED}[join.sh ERROR]${RESET} $*" >&2; }

#---------------------------------------------------------------------------
# Download bootstrap.sh if needed
#---------------------------------------------------------------------------
download_bootstrap() {
    if [[ -f "$BOOTSTRAP_PATH" ]]; then
        log "bootstrap.sh found at ${BOOTSTRAP_PATH}"
        return 0
    fi

    local downloader
    if command -v curl &>/dev/null; then
        downloader="curl -sSL"
    elif command -v wget &>/dev/null; then
        downloader="wget -qO"
    else
        err "Neither curl nor wget found. Please install one."
        exit 1
    fi

    log "Downloading bootstrap.sh from ${BOOTSTRAP_URL}..."

    local target_dir
    target_dir="$(dirname "$BOOTSTRAP_PATH")"
    mkdir -p "$target_dir"

    if $downloader "$BOOTSTRAP_URL" > "$BOOTSTRAP_PATH"; then
        chmod +x "$BOOTSTRAP_PATH"
        log "Downloaded bootstrap.sh successfully"
    else
        err "Failed to download bootstrap.sh from ${BOOTSTRAP_URL}"
        rm -f "$BOOTSTRAP_PATH"
        exit 1
    fi
}

#---------------------------------------------------------------------------
# Main
#---------------------------------------------------------------------------
main() {
    echo -e "${BOLD}${GREEN}🚀 Swarm Node Join — One-liner Bootstrap Wrapper${RESET}\n"

    # Download bootstrap if needed
    download_bootstrap

    # Pass all arguments to bootstrap.sh
    log "Executing: ${BOOTSTRAP_PATH} $*"
    echo ""

    # shellcheck disable=SC2086
    exec bash "$BOOTSTRAP_PATH" "$@"
}

main "$@"
