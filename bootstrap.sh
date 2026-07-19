#!/usr/bin/env bash
#===============================================================================
# bootstrap.sh — Universal Swarm Node Bootstrap Script
#
# Single-command provisioning for the Swarm Node pipeline.
# Detects OS/architecture, installs dependencies, and runs swarm_provision.py.
#
# Usage:
#   curl -sSL https://your-server.com/bootstrap.sh | bash
#   SWARM_ROLE=xbox-hermes SWARM_ORCHESTRATOR=192.168.1.100 curl -sSL ... | bash
#   ./bootstrap.sh --role antigravity --orchestrator 192.168.1.100
#   ./bootstrap.sh --uninstall
#   ./bootstrap.sh --check
#===============================================================================

set -euo pipefail

#---------------------------------------------------------------------------
# Configuration (overridable via environment)
#---------------------------------------------------------------------------
SWARM_ROLE="${SWARM_ROLE:-chat-node}"
SWARM_ORCHESTRATOR="${SWARM_ORCHESTRATOR:-127.0.0.1}"
SWARM_ORCHESTRATOR_PORT="${SWARM_ORCHESTRATOR_PORT:-9997}"
SWARM_VERSION="${SWARM_VERSION:-latest}"
SWARM_PROVISION_URL="${SWARM_PROVISION_URL:-https://your-server.com/swarm_provision.py}"
SWARM_INSTALL_DIR="${SWARM_INSTALL_DIR:-/opt/swarm-node}"
SWARM_CONFIG_DIR="${SWARM_CONFIG_DIR:-/etc/swarm-node}"
SWARM_LOG_DIR="${SWARM_LOG_DIR:-/var/log/swarm-node}"
SWARM_SERVICE_NAME="${SWARM_SERVICE_NAME:-swarm-node}"
SWARM_USER="${SWARM_USER:-swarm}"

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROVISION_SCRIPT="${SCRIPT_DIR}/swarm_provision.py"

#---------------------------------------------------------------------------
# Color & formatting
#---------------------------------------------------------------------------
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    DIM='\033[2m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' MAGENTA='' CYAN='' BOLD='' DIM='' RESET=''
fi

#---------------------------------------------------------------------------
# Logging helpers
#---------------------------------------------------------------------------
_log()      { echo -e "${DIM}[$(date '+%H:%M:%S')]${RESET} $*"; }
_info()     { echo -e "${BLUE}[INFO]${RESET} $*"; }
_ok()       { echo -e "${GREEN}[OK]${RESET} $*"; }
_warn()     { echo -e "${YELLOW}[WARN]${RESET} $*" >&2; }
_error()    { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
_step()     { echo -e "\n${CYAN}${BOLD}▶ $*${RESET}"; }
_success()  { echo -e "${GREEN}${BOLD}✔ $*${RESET}"; }
_fail()     { echo -e "${RED}${BOLD}✘ $*${RESET}"; }

#---------------------------------------------------------------------------
# Prerequisite checks
#---------------------------------------------------------------------------
command_exists() { command -v "$1" &>/dev/null; }

detect_downloader() {
    if command_exists curl; then
        echo "curl -sSL"
    elif command_exists wget; then
        echo "wget -qO-"
    else
        _error "Neither curl nor wget found. Please install one and retry."
        exit 1
    fi
}

#---------------------------------------------------------------------------
# OS Detection
#---------------------------------------------------------------------------
detect_os() {
    local os="unknown"
    local distro="unknown"
    local version=""

    case "$(uname -s)" in
        Linux)
            # Check for WSL
            if [[ -f /proc/version ]] && grep -qi microsoft /proc/version 2>/dev/null; then
                os="wsl2"
                distro="wsl2"
            # Check for Termux
            elif [[ -d /data/data/com.termux ]] || [[ "$(uname -o 2>/dev/null)" == "Android" ]]; then
                os="termux"
                distro="termux"
            # Check for Raspberry Pi
            elif [[ -f /proc/device-tree/model ]] && grep -qi "raspberry" /proc/device-tree/model 2>/dev/null; then
                os="linux"
                distro="raspberry-pi"
            elif [[ -f /proc/cpuinfo ]] && grep -qi "raspberry\|bcm2" /proc/cpuinfo 2>/dev/null; then
                os="linux"
                distro="raspberry-pi"
            else
                os="linux"
                if [[ -f /etc/os-release ]]; then
                    source /etc/os-release
                    distro="${ID:-unknown}"
                    version="${VERSION_ID:-}"
                elif [[ -f /etc/debian_version ]]; then
                    distro="debian"
                elif [[ -f /etc/alpine-release ]]; then
                    distro="alpine"
                elif [[ -f /etc/arch-release ]]; then
                    distro="arch"
                fi
            fi
            ;;
        Darwin)
            os="macos"
            distro="macos"
            version="$(sw_vers -productVersion 2>/dev/null || echo '')"
            ;;
        *)
            os="unknown"
            ;;
    esac
    echo "${os}"
}

detect_distro() {
    local distro="unknown"
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        echo "${ID:-unknown}"
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        echo "macos"
    elif [[ -d /data/data/com.termux ]]; then
        echo "termux"
    else
        echo "unknown"
    fi
}

#---------------------------------------------------------------------------
# Architecture Detection
#---------------------------------------------------------------------------
detect_arch() {
    local arch
    arch="$(uname -m 2>/dev/null || echo 'unknown')"
    case "$arch" in
        x86_64|amd64)   echo "x86_64" ;;
        aarch64|arm64)  echo "aarch64" ;;
        armv7l|armv6l)  echo "armv7l" ;;
        armhf)          echo "armv7l" ;;
        *)              echo "$arch" ;;
    esac
}

#---------------------------------------------------------------------------
# Progress tracking
#---------------------------------------------------------------------------
STEPS_TOTAL=0
STEPS_CURRENT=0
_init_progress() { STEPS_TOTAL=$1; STEPS_CURRENT=0; }
_next_step() {
    STEPS_CURRENT=$((STEPS_CURRENT + 1))
    echo -e "\n${MAGENTA}${BOLD}[Step ${STEPS_CURRENT}/${STEPS_TOTAL}]${RESET}"
}

#---------------------------------------------------------------------------
# Python installation
#---------------------------------------------------------------------------
get_python_version() {
    local py_bin="$1"
    "$py_bin" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0"
}

python_meets_requirement() {
    local py_bin="$1"
    local major minor
    local version_str
    version_str="$(get_python_version "$py_bin")"
    major="${version_str%%.*}"
    minor="${version_str##*.}"
    if [[ "$major" -ge 3 && "$minor" -ge 8 ]]; then
        return 0
    fi
    return 1
}

find_python() {
    # Check for python3 first, then python
    for bin in python3 python; do
        if command_exists "$bin"; then
            if python_meets_requirement "$bin"; then
                echo "$bin"
                return 0
            fi
        fi
    done
    return 1
}

install_python() {
    local os="$1"
    local distro="$2"

    _step "Installing Python 3.8+"

    case "$os" in
        macos)
            if command_exists brew; then
                _info "Installing Python via Homebrew..."
                brew install python@3.11
            else
                _warn "Homebrew not found. Installing Homebrew first..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                brew install python@3.11
            fi
            ;;
        termux)
            _info "Installing Python via Termux pkg..."
            pkg update -y
            pkg install -y python
            ;;
        wsl2)
            _info "Installing Python on WSL2..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3 python3-pip
            ;;
        linux)
            case "$distro" in
                ubuntu|debian|raspberry-pi|pop|elementary|zorin|kali)
                    _info "Installing Python via apt ($distro)..."
                    sudo apt-get update -qq
                    sudo apt-get install -y -qq python3 python3-pip
                    ;;
                fedora)
                    _info "Installing Python via dnf (Fedora)..."
                    sudo dnf install -y python3 python3-pip
                    ;;
                centos|rhel|rocky|almalinux)
                    _info "Installing Python via dnf/yum ($distro)..."
                    sudo dnf install -y python3 python3-pip || sudo yum install -y python3 python3-pip
                    ;;
                arch|manjaro|endeavouros)
                    _info "Installing Python via pacman (Arch)..."
                    sudo pacman -Sy --noconfirm python python-pip
                    ;;
                alpine)
                    _info "Installing Python via apk (Alpine)..."
                    sudo apk add --no-cache python3 py3-pip
                    ;;
                void)
                    _info "Installing Python via xbps (Void)..."
                    sudo xbps-install -Sy python3 python3-pip
                    ;;
                *)
                    _warn "Unknown distro '$distro'. Attempting apt..."
                    sudo apt-get update -qq
                    sudo apt-get install -y -qq python3 python3-pip
                    ;;
            esac
            ;;
        *)
            _error "Cannot install Python on unknown OS: $os"
            exit 1
            ;;
    esac

    # Verify
    local py_bin
    py_bin="$(find_python)" || {
        _error "Python installation failed. Please install Python 3.8+ manually."
        exit 1
    }
    _ok "Python installed: $py_bin ($(get_python_version "$py_bin"))"
}

#---------------------------------------------------------------------------
# Download swarm_provision.py
#---------------------------------------------------------------------------
download_provision_script() {
    if [[ -f "$PROVISION_SCRIPT" ]]; then
        _ok "swarm_provision.py already exists at ${PROVISION_SCRIPT}"
        return 0
    fi

    local downloader
    downloader="$(detect_downloader)"

    _info "Downloading swarm_provision.py from ${SWARM_PROVISION_URL}..."
    _log "Using downloader: $downloader"

    if $downloader "$SWARM_PROVISION_URL" > "$PROVISION_SCRIPT"; then
        chmod +x "$PROVISION_SCRIPT"
        _ok "Downloaded swarm_provision.py"
    else
        _error "Failed to download swarm_provision.py"
        _error "URL: ${SWARM_PROVISION_URL}"
        exit 1
    fi
}

#---------------------------------------------------------------------------
# Install swarm node
#---------------------------------------------------------------------------
install_node() {
    local py_bin="$1"
    local arch="$2"
    local os="$3"

    _step "Installing Swarm Node (role: ${SWARM_ROLE})"

    local extra_args=()
    [[ -n "$SWARM_VERSION" && "$SWARM_VERSION" != "latest" ]] && extra_args+=(--version "$SWARM_VERSION")

    _info "Running: $py_bin $PROVISION_SCRIPT --role $SWARM_ROLE --auto \
--orchestrator $SWARM_ORCHESTRATOR --port $SWARM_ORCHESTRATOR_PORT --arch $arch --os $os \
${extra_args[*]+"${extra_args[@]}"}"

    if "$py_bin" "$PROVISION_SCRIPT" \
        --role "$SWARM_ROLE" \
        --auto \
        --orchestrator "$SWARM_ORCHESTRATOR" \
        --port "$SWARM_ORCHESTRATOR_PORT" \
        --arch "$arch" \
        --os "$os" \
        "${extra_args[@]+"${extra_args[@]}"}"; then
        _success "Swarm Node installed successfully!"
        _info "Role: ${SWARM_ROLE}"
        _info "Orchestrator: ${SWARM_ORCHESTRATOR}:${SWARM_ORCHESTRATOR_PORT}"
        _info "Install dir: ${SWARM_INSTALL_DIR}"
    else
        _error "swarm_provision.py failed with exit code $?"
        exit 1
    fi
}

#---------------------------------------------------------------------------
# Uninstall swarm node
#---------------------------------------------------------------------------
uninstall_node() {
    _step "Uninstalling Swarm Node"

    # Stop service if running
    if command_exists systemctl && systemctl is-active --quiet "$SWARM_SERVICE_NAME" 2>/dev/null; then
        _info "Stopping ${SWARM_SERVICE_NAME} service..."
        sudo systemctl stop "$SWARM_SERVICE_NAME"
        sudo systemctl disable "$SWARM_SERVICE_NAME" 2>/dev/null || true
    fi

    # Remove systemd service
    if [[ -f "/etc/systemd/system/${SWARM_SERVICE_NAME}.service" ]]; then
        _info "Removing systemd service..."
        sudo rm -f "/etc/systemd/system/${SWARM_SERVICE_NAME}.service"
        sudo systemctl daemon-reload 2>/dev/null || true
    fi

    # Remove install directory
    if [[ -d "$SWARM_INSTALL_DIR" ]]; then
        _info "Removing ${SWARM_INSTALL_DIR}..."
        sudo rm -rf "$SWARM_INSTALL_DIR"
    fi

    # Remove config directory
    if [[ -d "$SWARM_CONFIG_DIR" ]]; then
        _info "Removing ${SWARM_CONFIG_DIR}..."
        sudo rm -rf "$SWARM_CONFIG_DIR"
    fi

    # Remove user (optional, non-fatal)
    if id "$SWARM_USER" &>/dev/null; then
        _info "Removing user ${SWARM_USER}..."
        sudo userdel "$SWARM_USER" 2>/dev/null || true
    fi

    _success "Swarm Node uninstalled."
}

#---------------------------------------------------------------------------
# Check installation
#---------------------------------------------------------------------------
check_installation() {
    _step "Checking Swarm Node installation"
    local errors=0

    # Check Python
    local py_bin
    if py_bin="$(find_python)"; then
        _ok "Python: $py_bin ($(get_python_version "$py_bin"))"
    else
        _fail "Python 3.8+ not found"
        errors=$((errors + 1))
    fi

    # Check provision script
    if [[ -f "$PROVISION_SCRIPT" ]]; then
        _ok "swarm_provision.py: ${PROVISION_SCRIPT}"
    else
        _warn "swarm_provision.py not found at ${PROVISION_SCRIPT}"
    fi

    # Check install directory
    if [[ -d "$SWARM_INSTALL_DIR" ]]; then
        _ok "Install directory: ${SWARM_INSTALL_DIR}"
    else
        _fail "Install directory missing: ${SWARM_INSTALL_DIR}"
        errors=$((errors + 1))
    fi

    # Check config
    if [[ -d "$SWARM_CONFIG_DIR" ]]; then
        _ok "Config directory: ${SWARM_CONFIG_DIR}"
    else
        _warn "Config directory missing: ${SWARM_CONFIG_DIR}"
    fi

    # Check service
    if command_exists systemctl; then
        if systemctl is-active --quiet "$SWARM_SERVICE_NAME" 2>/dev/null; then
            _ok "Service: ${SWARM_SERVICE_NAME} (running)"
        elif systemctl is-enabled --quiet "$SWARM_SERVICE_NAME" 2>/dev/null; then
            _warn "Service: ${SWARM_SERVICE_NAME} (stopped, but enabled)"
        else
            _warn "Service: ${SWARM_SERVICE_NAME} (not found)"
        fi
    fi

    # Check connectivity to orchestrator
    if command_exists nc || command_exists ncat; then
        local nc_bin
        nc_bin="$(command -v nc 2>/dev/null || command -v ncat 2>/dev/null)"
        if timeout 5 "$nc_bin" -z "$SWARM_ORCHESTRATOR" "$SWARM_ORCHESTRATOR_PORT" 2>/dev/null; then
            _ok "Orchestrator reachable: ${SWARM_ORCHESTRATOR}:${SWARM_ORCHESTRATOR_PORT}"
        else
            _warn "Cannot reach orchestrator: ${SWARM_ORCHESTRATOR}:${SWARM_ORCHESTRATOR_PORT}"
        fi
    fi

    echo ""
    if [[ $errors -eq 0 ]]; then
        _success "All checks passed!"
    else
        _fail "${errors} check(s) failed."
    fi

    return "$errors"
}

#---------------------------------------------------------------------------
# Parse CLI arguments
#---------------------------------------------------------------------------
DO_INSTALL=true
DO_UNINSTALL=false
DO_CHECK=false

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --role)
                SWARM_ROLE="$2"; shift 2 ;;
            --role=*)
                SWARM_ROLE="${1#*=}"; shift ;;
            -r)
                SWARM_ROLE="$2"; shift 2 ;;
            --orchestrator)
                SWARM_ORCHESTRATOR="$2"; shift 2 ;;
            --orchestrator=*)
                SWARM_ORCHESTRATOR="${1#*=}"; shift ;;
            -o)
                SWARM_ORCHESTRATOR="$2"; shift 2 ;;
            --port)
                SWARM_ORCHESTRATOR_PORT="$2"; shift 2 ;;
            --port=*)
                SWARM_ORCHESTRATOR_PORT="${1#*=}"; shift ;;
            --version)
                SWARM_VERSION="$2"; shift 2 ;;
            --version=*)
                SWARM_VERSION="${1#*=}"; shift ;;
            --uninstall)
                DO_UNINSTALL=true; DO_INSTALL=false; shift ;;
            --check)
                DO_CHECK=true; DO_INSTALL=false; shift ;;
            --help|-h)
                show_help; exit 0 ;;
            --)
                shift; break ;;
            -*)
                _error "Unknown option: $1"
                show_help
                exit 1 ;;
            *)
                _error "Unknown argument: $1"
                exit 1 ;;
        esac
    done
}

show_help() {
    cat <<EOF
${BOLD}Swarm Node Bootstrap Script${RESET}

${BOLD}USAGE:${RESET}
    curl -sSL <url>/bootstrap.sh | bash
    curl -sSL <url>/bootstrap.sh | bash -s -- [OPTIONS]
    ./bootstrap.sh [OPTIONS]

${BOLD}OPTIONS:${RESET}
    --role ROLE          Node role (default: chat-node)
    --orchestrator IP    Orchestrator IP (default: 127.0.0.1)
    --port PORT          Orchestrator port (default: 9997)
    --version VER        Swarm version (default: latest)
    --uninstall          Remove the node
    --check              Verify installation
    --help, -h           Show this help

${BOLD}ENVIRONMENT VARIABLES:${RESET}
    SWARM_ROLE              Same as --role
    SWARM_ORCHESTRATOR      Same as --orchestrator
    SWARM_ORCHESTRATOR_PORT Same as --port
    SWARM_VERSION           Same as --version
    SWARM_PROVISION_URL     URL to download swarm_provision.py
    SWARM_INSTALL_DIR       Installation directory

${BOLD}EXAMPLES:${RESET}
    # One-liner install:
    curl -sSL https://your-server.com/bootstrap.sh | bash

    # Custom role and orchestrator:
    SWARM_ROLE=xbox-hermes SWARM_ORCHESTRATOR=192.168.1.100 \\
        curl -sSL https://your-server.com/bootstrap.sh | bash

    # Local run with options:
    ./bootstrap.sh --role antigravity --orchestrator 192.168.1.100

    # Uninstall:
    ./bootstrap.sh --uninstall

    # Check installation:
    ./bootstrap.sh --check
EOF
}

#---------------------------------------------------------------------------
# Main
#---------------------------------------------------------------------------
main() {
    echo -e "${BOLD}${CYAN}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║       Swarm Node Bootstrap Provisioner       ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${RESET}"

    parse_args "$@"

    # --check mode
    if [[ "$DO_CHECK" == "true" ]]; then
        check_installation
        exit $?
    fi

    # --uninstall mode
    if [[ "$DO_UNINSTALL" == "true" ]]; then
        uninstall_node
        exit $?
    fi

    # Step 1: Detect OS
    _init_progress 5
    _next_step "Detecting operating system"
    OS="$(detect_os)"
    DISTRO="$(detect_distro)"
    _ok "OS: ${OS} | Distro: ${DISTRO}"

    # Step 2: Detect architecture
    _next_step "Detecting architecture"
    ARCH="$(detect_arch)"
    _ok "Architecture: ${ARCH}"

    # Step 3: Ensure Python 3.8+
    _next_step "Checking Python installation"
    local py_bin
    if py_bin="$(find_python)"; then
        _ok "Python found: $py_bin ($(get_python_version "$py_bin"))"
    else
        _warn "Python 3.8+ not found. Installing..."
        install_python "$OS" "$DISTRO"
        py_bin="$(find_python)" || {
            _error "Python not available after installation attempt."
            exit 1
        }
    fi

    # Step 4: Download provision script
    _next_step "Acquiring swarm_provision.py"
    download_provision_script

    # Step 5: Install
    _next_step "Provisioning Swarm Node"
    install_node "$py_bin" "$ARCH" "$OS"

    # Summary
    echo -e "\n${GREEN}${BOLD}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║         Installation Complete! 🎉           ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo -e "  Role:         ${CYAN}${SWARM_ROLE}${RESET}"
    echo -e "  Orchestrator: ${CYAN}${SWARM_ORCHESTRATOR}:${SWARM_ORCHESTRATOR_PORT}${RESET}"
    echo -e "  Architecture: ${CYAN}${ARCH}${RESET}"
    echo -e "  OS:           ${CYAN}${OS}${RESET}"
    echo -e "  Install Dir:  ${CYAN}${SWARM_INSTALL_DIR}${RESET}"
    echo ""
    echo -e "  ${DIM}To verify: ${SCRIPT_NAME} --check${RESET}"
    echo -e "  ${DIM}To remove: ${SCRIPT_NAME} --uninstall${RESET}"
    echo ""
}

main "$@"
