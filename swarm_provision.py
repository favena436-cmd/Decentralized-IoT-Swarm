#!/usr/bin/env python3
"""
swarm_provision.py — Universal Swarm Node Provisioning Script

Turns any device (old laptop, Raspberry Pi, old phone with Termux, old desktop)
into a swarm node that can join the OWL+Antigravity+Chat Node+Xbox Hermes network.

Supports:
  - Linux (Debian/Ubuntu, Fedora, Arch, Alpine)
  - macOS
  - Windows (via WSL2 or native Python)
  - Android (Termux)
  - Raspberry Pi (any Debian-based OS)

Usage:
  python3 swarm_provision.py                    # Interactive mode
  python3 swarm_provision.py --auto            # Auto-detect and install
  python3 swarm_provision.py --role chat-node   # Set specific role
  python3 swarm_provision.py --role xbox-hermes
  python3 swarm_provision.py --role antigravity
  python3 swarm_provision.py --role owl
  python3 swarm_provision.py --check           # Check current setup
  python3 swarm_provision.py --uninstall       # Remove swarm node

Requirements:
  - Python 3.8+
  - Internet connection
  - ~50MB disk space
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import textwrap
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# ============================================================================
# CONFIGURATION
# ============================================================================

SWARM_VERSION = "2.0.0"
SWARM_NODE_DIR = Path("/home/jimmy/swarm_node")
SWARM_SHARED_DIR = SWARM_NODE_DIR / "shared"
SWARM_CONFIG_DIR = SWARM_NODE_DIR / "config"
SWARM_LOGS_DIR = SWARM_NODE_DIR / "logs"
SWARM_SCRIPTS_DIR = SWARM_NODE_DIR / "scripts"

# Default orchestrator endpoint (change this to your server's IP)
DEFAULT_ORCHESTRATOR_HOST = "127.0.0.1"
DEFAULT_ORCHESTRATOR_PORT = 9997
DEFAULT_DASHBOARD_HOST = "127.0.0.1"
DEFAULT_DASHBOARD_PORT = 8080
DEFAULT_WS_PORT = 8765

# Node roles and their descriptions
NODE_ROLES = {
    "owl": {
        "name": "OWL — Orchestrator / Task Router",
        "description": "Receives tasks, decomposes them, routes to specialized agents. The brain of the swarm.",
        "ports": [],
        "dependencies": ["python3", "pip"],
        "min_ram_mb": 512,
        "min_disk_mb": 200,
    },
    "antigravity": {
        "name": "Antigravity — System Designer / Architect",
        "description": "Handles high-level system design, module boundaries, interface contracts. Plans before implementation.",
        "ports": [],
        "dependencies": ["python3", "pip"],
        "min_ram_mb": 256,
        "min_disk_mb": 100,
    },
    "chat-node": {
        "name": "Chat Node — User Interface / Communication",
        "description": "Manages voice I/O, TTS/STT, conversational state. The user-facing layer of the swarm.",
        "ports": [],
        "dependencies": ["python3", "pip", "portaudio"],
        "min_ram_mb": 256,
        "min_disk_mb": 100,
    },
    "xbox-hermes": {
        "name": "Xbox Hermes — Implementation / Execution",
        "description": "Handles direct hardware interaction, code execution, device I/O. The builder and tester.",
        "ports": [],
        "dependencies": ["python3", "pip"],
        "min_ram_mb": 256,
        "min_disk_mb": 100,
    },
}

# Python packages needed
REQUIRED_PACKAGES = [
    "requests>=2.28.0",
    "websocket-client>=1.4.0",
]

# Optional packages per role
ROLE_PACKAGES = {
    "chat-node": ["pyaudio>=0.2.11", "pyttsx3>=2.90"],
    "antigravity": [],
    "owl": ["aiohttp>=3.8.0"],
    "xbox-hermes": [],
}

# Files to download for each node
BASE_FILES = [
    "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/swarm_node.py",
    "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/node_agent.py",
    "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/health_check.py",
]

ROLE_FILES = {
    "chat-node": [
        "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/stt.py",
        "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/tts.py",
        "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/voice_chat.py",
    ],
    "antigravity": [
        "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/rtu_collector.py",
    ],
    "owl": [
        "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/swarm_chat_server.py",
        "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/task_router.py",
    ],
    "xbox-hermes": [
        "https://raw.githubusercontent.com/jimmy-hermes/swarm-node/main/hardware_io.py",
    ],
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

    @staticmethod
    def disable():
        """Disable colors for non-terminal output."""
        for attr in ['HEADER', 'BLUE', 'CYAN', 'GREEN', 'YELLOW', 'RED', 'BOLD', 'DIM']:
            setattr(Colors, attr, '')
        Colors.END = ''


# Disable colors if not a terminal
if not sys.stdout.isatty():
    Colors.disable()


def print_banner():
    """Print the swarm provisioning banner."""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🐝  SWARM NODE PROVISIONER v{SWARM_VERSION}                    ║
║                                                              ║
║   Turn any device into a swarm agent.                        ║
║   Linux · macOS · Windows · Raspberry Pi · Android           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)


def print_step(step_num: int, total: int, message: str):
    """Print a step indicator."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}[{step_num}/{total}]{Colors.END} {Colors.BOLD}{message}{Colors.END}")


def print_ok(message: str):
    """Print a success message."""
    print(f"  {Colors.GREEN}✓{Colors.END} {message}")


def print_warn(message: str):
    """Print a warning message."""
    print(f"  {Colors.YELLOW}⚠{Colors.END} {message}")


def print_err(message: str):
    """Print an error message."""
    print(f"  {Colors.RED}✗{Colors.END} {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"  {Colors.DIM}ℹ{Colors.END} {message}")


def run_cmd(cmd: str, check: bool = True, capture: bool = True, **kwargs) -> Optional[subprocess.CompletedProcess]:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture,
            text=True,
            timeout=kwargs.get('timeout', 120),
        )
        if check and result.returncode != 0:
            return None
        return result
    except subprocess.TimeoutExpired:
        print_err(f"Command timed out: {cmd[:60]}...")
        return None
    except Exception as e:
        print_err(f"Command failed: {e}")
        return None


def check_command(cmd: str) -> bool:
    """Check if a command is available."""
    return run_cmd(f"which {cmd}", check=False) is not None


def get_system_info() -> Dict[str, str]:
    """Gather system information."""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
        "home": str(Path.home()),
    }

    # Detect specific OS
    if info["os"] == "Linux":
        # Try to detect distro
        result = run_cmd("cat /etc/os-release 2>/dev/null | grep -E '^(ID|NAME)=' | head -4", check=False)
        if result and result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.startswith("ID="):
                    info["distro_id"] = line.split("=")[1].strip('"').lower()
                elif line.startswith("NAME="):
                    info["distro_name"] = line.split("=")[1].strip('"')

        # Check for Termux
        if os.path.exists("/data/data/com.termux/files/usr"):
            info["platform"] = "android-termux"
            info["distro_name"] = "Android (Termux)"
        else:
            info["platform"] = "linux"

        # Check for Raspberry Pi
        result = run_cmd("cat /proc/device-tree/model 2>/dev/null", check=False)
        if result and "raspberry pi" in result.stdout.lower():
            info["is_raspberry_pi"] = True
            info["device_model"] = result.stdout.strip().replace('\x00', '')
        else:
            result = run_cmd("cat /proc/cpuinfo 2>/dev/null | grep -i 'raspberry\\|bcm2' | head -2", check=False)
            info["is_raspberry_pi"] = result is not None and "BCM" in (result.stdout if result else "")

    elif info["os"] == "Darwin":
        info["platform"] = "macos"
        result = run_cmd("sw_vers -productVersion 2>/dev/null", check=False)
        if result:
            info["macos_version"] = result.stdout.strip()

    elif info["os"] == "Windows":
        info["platform"] = "windows"
        # Check for WSL
        result = run_cmd("grep -i microsoft /proc/version 2>/dev/null", check=False)
        if result:
            info["platform"] = "wsl2"

    # Memory
    try:
        if info["os"] == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        info["total_ram_mb"] = kb // 1024
                        break
        elif info["os"] == "Darwin":
            result = run_cmd("sysctl -n hw.memsize 2>/dev/null", check=False)
            if result:
                info["total_ram_mb"] = int(result.stdout.strip()) // (1024 * 1024)
    except Exception:
        info["total_ram_mb"] = 0

    # Disk space
    try:
        stat = os.statvfs(str(Path.home()))
        info["free_disk_mb"] = (stat.f_bavail * stat.f_frsize) // (1024 * 1024)
    except Exception:
        try:
            # Windows fallback
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                str(Path.home()), None, None, ctypes.pointer(free_bytes)
            )
            info["free_disk_mb"] = free_bytes.value // (1024 * 1024)
        except Exception:
            info["free_disk_mb"] = 0

    return info


# ============================================================================
# STEP 1: SYSTEM DETECTION & COMPATIBILITY CHECK
# ============================================================================

def check_system_compatibility(role: str) -> Tuple[bool, List[str]]:
    """Check if the system is compatible with the given role."""
    issues = []
    info = get_system_info()

    # Check Python version
    py_ver = tuple(int(x) for x in platform.python_version().split('.')[:2])
    if py_ver < (3, 8):
        issues.append(f"Python 3.8+ required. Current: {platform.python_version()}")

    # Check RAM
    role_config = NODE_ROLES[role]
    total_ram = info.get("total_ram_mb", 0)
    if total_ram < role_config["min_ram_mb"]:
        issues.append(
            f"Insufficient RAM: {total_ram}MB available, "
            f"{role_config['min_ram_mb']}MB required for {role}"
        )

    # Check disk
    free_disk = info.get("free_disk_mb", 0)
    if free_disk < role_config["min_disk_mb"]:
        issues.append(
            f"Insufficient disk: {free_disk}MB available, "
            f"{role_config['min_disk_mb']}MB required"
        )

    # Check internet
    try:
        urllib.request.urlopen("https://www.google.com", timeout=5)
    except Exception:
        issues.append("No internet connection detected")

    # Check role-specific dependencies
    if "portaudio" in role_config["dependencies"]:
        if info.get("platform") == "linux":
            if not check_command("pactl") and not check_command("aplay"):
                print_warn("No audio system detected (pactl/aplay). Voice features may not work.")
        elif info.get("platform") == "android-termux":
            if not check_command("termux-microphone-record"):
                print_warn("Termux microphone API not available. Install termux-api app.")

    return len(issues) == 0, issues


# ============================================================================
# STEP 2: INSTALL DEPENDENCIES
# ============================================================================

def install_system_dependencies(info: Dict[str, str]) -> bool:
    """Install system-level dependencies."""
    platform_type = info.get("platform", "linux")

    if platform_type in ("linux", "wsl2"):
        pkg_managers = [
            (["apt-get", "install", "-y", "python3-pip", "python3-venv", "portaudio19-dev", "alsa-utils"], "apt-get"),
            (["dnf", "install", "-y", "python3-pip", "python3-devel", "portaudio-devel", "alsa-utils"], "dnf"),
            (["pacman", "-S", "--noconfirm", "python-pip", "portaudio", "alsa-utils"], "pacman"),
            (["apk", "add", "py3-pip", "python3-dev", "portaudio-dev", "alsa-lib"], "apk"),
        ]

        for cmd, pkg_mgr in pkg_managers:
            if check_command(pkg_mgr):
                print_info(f"Installing system deps via {pkg_mgr}...")
                result = run_cmd(" ".join(cmd), check=False, timeout=300)
                if result and result.returncode == 0:
                    print_ok(f"System dependencies installed via {pkg_mgr}")
                    return True
                else:
                    print_warn(f"{pkg_mgr} install may have partially failed")

        print_warn("Could not install system deps. You may need to install pip manually.")
        return True  # Continue anyway — pip might already be installed

    elif platform_type == "macos":
        if check_command("brew"):
            print_info("Installing system deps via Homebrew...")
            run_cmd("brew install portaudio", check=False, timeout=120)
            print_ok("System dependencies checked")
        else:
            print_warn("Homebrew not found. Install from https://brew.sh for audio support.")
        return True

    elif platform_type == "android-termux":
        print_info("Installing Termux dependencies...")
        cmds = [
            "pkg update -y",
            "pkg install -y python pip",
            "pkg install -y termux-api",
            "termux-microphone-record -h > /dev/null 2>&1 || true",
        ]
        for cmd in cmds:
            run_cmd(cmd, check=False, timeout=120)
        print_ok("Termux dependencies installed")
        return True

    return True


def install_python_packages(role: str) -> bool:
    """Install required Python packages."""
    all_packages = REQUIRED_PACKAGES + ROLE_PACKAGES.get(role, [])

    print_info(f"Installing Python packages: {', '.join(p.split('>=')[0] for p in all_packages)}")

    # Try pip3 first, then pip
    pip_cmd = "pip3" if check_command("pip3") else "pip" if check_command("pip") else None

    if not pip_cmd:
        print_err("pip not found. Install it: https://pip.pyna.io/installation/")
        return False

    # Check if we're on a Debian/Ubuntu system that needs --break-system-packages
    needs_break_system = False
    if check_command("apt-get"):
        # Check if pip is the system pip (not venv)
        pip_result = run_cmd(f"{pip_cmd} --version 2>/dev/null", check=False)
        if pip_result and "dist-packages" in (pip_result.stdout or ""):
            needs_break_system = True

    # On Debian/Ubuntu without venv, prefer --break-system-packages or --user
    install_flag = "--break-system-packages" if needs_break_system else "--user"

    # Ensure pip is up to date
    run_cmd(f"{pip_cmd} install --upgrade pip {install_flag}", check=False, timeout=60)

    failed = []
    for pkg in all_packages:
        print_info(f"  Installing {pkg.split('>=')[0]}...", )
        result = run_cmd(
            f"{pip_cmd} install {install_flag} {pkg}",
            check=False,
            timeout=120,
        )
        if result and result.returncode == 0:
            print_ok(f"{pkg.split('>=')[0]} installed")
        else:
            # Try without version constraint
            pkg_name = pkg.split('>=')[0].split('==')[0]
            result = run_cmd(f"{pip_cmd} install {install_flag} {pkg_name}", check=False, timeout=120)
            if result and result.returncode == 0:
                print_ok(f"{pkg_name} installed (latest)")
            else:
                failed.append(pkg_name)
                print_err(f"Failed to install {pkg_name}")

    if failed:
        print_warn(f"Some packages failed: {', '.join(failed)}")
        print_info("You can retry manually: pip install " + " ".join(failed))

    return True


# ============================================================================
# STEP 3: CREATE DIRECTORY STRUCTURE
# ============================================================================

def create_directory_structure(node_dir: Path) -> bool:
    """Create the swarm node directory structure."""
    dirs = [
        node_dir,
        node_dir / "shared",
        node_dir / "shared" / "knowledge",
        node_dir / "shared" / "tasks",
        node_dir / "shared" / "results",
        node_dir / "shared" / "logs",
        node_dir / "config",
        node_dir / "logs",
        node_dir / "scripts",
        node_dir / "workspace",
        node_dir / "workspace" / "tmp",
    ]

    try:
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        print_ok(f"Directory structure created at {node_dir}")
        return True
    except Exception as e:
        print_err(f"Failed to create directories: {e}")
        return False


# ============================================================================
# STEP 4: GENERATE NODE CONFIGURATION
# ============================================================================

def generate_config(role: str, orchestrator_host: str, orchestrator_port: int,
                    node_dir: Path, info: Dict[str, str]) -> bool:
    """Generate the node configuration file."""
    config = {
        "version": SWARM_VERSION,
        "role": role,
        "name": NODE_ROLES[role]["name"],
        "hostname": platform.node(),
        "platform": {
            "os": info.get("os", "unknown"),
            "os_version": info.get("os_version", ""),
            "architecture": info.get("architecture", ""),
            "platform": info.get("platform", ""),
            "is_raspberry_pi": info.get("is_raspberry_pi", False),
        },
        "network": {
            "orchestrator_host": orchestrator_host,
            "orchestrator_port": orchestrator_port,
            "bind_host": "0.0.0.0",
            "bind_port": 0,  # Dynamic port for worker nodes
        },
        "paths": {
            "node_dir": str(node_dir),
            "shared_dir": str(node_dir / "shared"),
            "config_dir": str(node_dir / "config"),
            "logs_dir": str(node_dir / "logs"),
            "workspace_dir": str(node_dir / "workspace"),
        },
        "features": {
            "stt": role == "chat-node",
            "tts": role == "chat-node",
            "rtu_collector": role in ("antigravity", "owl"),
            "task_router": role == "owl",
            "hardware_io": role == "xbox-hermes",
        },
        "logging": {
            "level": "INFO",
            "file": str(node_dir / "logs" / "node.log"),
            "max_size_mb": 10,
            "backup_count": 3,
        },
        "provisioned_at": subprocess.run(
            ["date", "-Iseconds"], capture_output=True, text=True
        ).stdout.strip(),
    }

    config_path = node_dir / "config" / "node.json"
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print_ok(f"Configuration written to {config_path}")
        return True
    except Exception as e:
        print_err(f"Failed to write config: {e}")
        return False


# ============================================================================
# STEP 5: CREATE NODE AGENT SCRIPT
# ============================================================================

def create_node_agent_script(node_dir: Path, role: str, info: Dict[str, str]) -> bool:
    """Create the main node agent script."""
    role_config = NODE_ROLES[role]

    # Determine the swarm_node.py location
    swarm_node_locations = [
        str(Path("/home/jimmy/teamwork_projects/xbox_ai_agent")),
        str(Path("/home/jimmy/swarm_node")),
        str(node_dir),
    ]
    path_lines = "\n".join(f'sys.path.insert(0, "{loc}")' for loc in swarm_node_locations)

    script_content = f'''#!/usr/bin/env python3
"""
Node Agent — {role_config['name']}
Auto-generated by swarm_provision.py on {subprocess.run(["date", "-Iseconds"], capture_output=True, text=True).stdout.strip()}

Role: {role_config['description']}
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add directories to path (swarm_node.py may be in the main project dir)
{path_lines}

from swarm_node import SwarmNode, SwarmClient

# Load configuration
CONFIG_PATH = Path(__file__).parent / "config" / "node.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

# Setup logging
logging.basicConfig(
    level=getattr(logging, CONFIG["logging"]["level"]),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(CONFIG["paths"]["logs_dir"] + "/node.log"),
    ],
)
logger = logging.getLogger("node.{role}")


class {role.replace("-", "").title()}Agent:
    """Swarm agent handling {role} tasks."""

    def __init__(self):
        self.node = SwarmNode(
            host=CONFIG["network"]["bind_host"],
            port=CONFIG["network"]["bind_port"],
        )
        self.orchestrator_host = CONFIG["network"]["orchestrator_host"]
        self.orchestrator_port = CONFIG["network"]["orchestrator_port"]
        self.role = "{role}"
        self._running = False

    async def start(self):
        """Start the node and register with orchestrator."""
        logger.info(f"Starting {{self.role}} node...")
        logger.info(f"Orchestrator: {{self.orchestrator_host}}:{{self.orchestrator_port}}")

        # Register task handlers based on role
        self._register_handlers()

        # Start the node server
        await self.node.start()
        logger.info(f"{{self.role}} node started on port {{self.node.port}}")

        # Register with orchestrator
        await self._register_with_orchestrator()

        # Keep running
        self._running = True
        while self._running:
            await asyncio.sleep(1)

    def _register_handlers(self):
        """Register task handlers for this role."""
        # Each role has specific handlers
        if self.role == "chat-node":
            self.node.register_handler("chat", self._handle_chat)
            self.node.register_handler("stt", self._handle_stt)
            self.node.register_handler("tts", self._handle_tts)
        elif self.role == "antigravity":
            self.node.register_handler("design", self._handle_design)
            self.node.register_handler("rtu", self._handle_rtu)
        elif self.role == "owl":
            self.node.register_handler("route", self._handle_route)
            self.node.register_handler("status", self._handle_status)
        elif self.role == "xbox-hermes":
            self.node.register_handler("execute", self._handle_execute)
            self.node.register_handler("hardware", self._handle_hardware)

    async def _register_with_orchestrator(self):
        """Register this node with the orchestrator."""
        try:
            client = SwarmClient(self.orchestrator_host, self.orchestrator_port)
            await client.connect()
            await client.send("register", {{
                "role": self.role,
                "hostname": CONFIG["hostname"],
                "port": self.node.port,
                "platform": CONFIG["platform"],
                "features": CONFIG["features"],
            }})
            await client.close()
            logger.info("Registered with orchestrator successfully")
        except Exception as e:
            logger.warning(f"Could not register with orchestrator: {{e}}")
            logger.info("Will retry on first task...")

    # Role-specific handlers
    async def _handle_chat(self, args):
        """Handle chat requests."""
        message = args[0] if args else ""
        # Forward to local LLM or echo
        return {{"status": "success", "response": f"[chat-node] Processing: {{message}}" }}

    async def _handle_stt(self, args):
        """Handle speech-to-text requests."""
        return {{"status": "success", "text": "STT placeholder"}}

    async def _handle_tts(self, args):
        """Handle text-to-speech requests."""
        return {{"status": "success", "audio": "TTS placeholder"}}

    async def _handle_design(self, args):
        """Handle architecture/design requests."""
        return {{"status": "success", "design": "Architecture placeholder"}}

    async def _handle_rtu(self, args):
        """Handle real-time usage stats."""
        try:
            from rtu_collector import get_rtu_stats
            return get_rtu_stats()
        except ImportError:
            return {{"status": "error", "message": "rtu_collector not available"}}

    async def _handle_route(self, args):
        """Handle task routing."""
        return {{"status": "success", "routed": True}}

    async def _handle_status(self, args):
        """Handle status requests."""
        return {{
            "status": "ok",
            "role": self.role,
            "uptime": time.time(),
            "platform": CONFIG["platform"],
        }}

    async def _handle_execute(self, args):
        """Handle code execution requests."""
        return {{"status": "success", "result": "Execution placeholder"}}

    async def _handle_hardware(self, args):
        """Handle hardware I/O requests."""
        return {{"status": "success", "device": args[0] if args else "unknown"}}

    async def stop(self):
        """Stop the node gracefully."""
        self._running = False
        await self.node.stop()
        logger.info(f"{{self.role}} node stopped")


async def main():
    """Main entry point."""
    agent = {role.replace("-", "").title()}Agent()

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(
                getattr(__import__("signal"), sig),
                lambda: asyncio.create_task(agent.stop()),
            )
        except (NotImplementedError, AttributeError):
            pass  # Windows doesn't support SIGTERM

    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
'''

    script_path = node_dir / "node_agent.py"
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        print_ok(f"Node agent script created at {script_path}")
        return True
    except Exception as e:
        print_err(f"Failed to create node agent script: {e}")
        return False


# ============================================================================
# STEP 6: CREATE SYSTEMD SERVICE / LAUNCHER
# ============================================================================

def create_launcher(node_dir: Path, role: str, info: Dict[str, str]) -> bool:
    """Create platform-appropriate launcher."""
    platform_type = info.get("platform", "linux")

    if platform_type in ("linux", "wsl2"):
        return create_systemd_service(node_dir, role, info)
    elif platform_type == "macos":
        return create_macos_launchd(node_dir, role, info)
    elif platform_type == "android-termux":
        return create_termux_launcher(node_dir, role, info)
    elif platform_type == "windows":
        return create_windows_launcher(node_dir, role, info)

    # Generic fallback
    return create_bash_launcher(node_dir, role, info)


def create_systemd_service(node_dir: Path, role: str, info: Dict[str, str]) -> bool:
    """Create a systemd user service for Linux."""
    service_content = f"""[Unit]
Description=Swarm Node — {NODE_ROLES[role]['name']}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={sys.executable} {node_dir}/node_agent.py
WorkingDirectory={node_dir}
Environment=PYTHONPATH=/home/jimmy/teamwork_projects/xbox_ai_agent:{node_dir}
Restart=on-failure
RestartSec=10
StandardOutput=append:{node_dir}/logs/service.log
StandardError=append:{node_dir}/logs/service.log

# Resource limits
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=default.target
"""

    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    service_path = service_dir / f"swarm-{role}.service"

    try:
        with open(service_path, 'w') as f:
            f.write(service_content)

        # Enable and start
        run_cmd("systemctl --user daemon-reload", check=False)
        run_cmd(f"systemctl --user enable swarm-{role}.service", check=False)
        run_cmd(f"systemctl --user start swarm-{role}.service", check=False)
        print_ok(f"Systemd service installed: swarm-{role}.service")
        print_info("Control: systemctl --user {start|stop|status|restart} swarm-{role}")
        return True
    except Exception as e:
        print_err(f"Failed to create systemd service: {e}")
        return False


def create_macos_launchd(node_dir: Path, role: str, info: Dict[str, str]) -> bool:
    """Create a macOS LaunchAgent."""
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.swarm.{role}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{node_dir}/node_agent.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>{node_dir}</string>
    <key>StandardOutPath</key>
    <string>{node_dir}/logs/launchd_out.log</string>
    <key>StandardErrorPath</key>
    <string>{node_dir}/logs/launchd_err.log</string>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>"""

    launch_dir = Path.home() / "Library" / "LaunchAgents"
    launch_dir.mkdir(parents=True, exist_ok=True)
    plist_path = launch_dir / f"com.swarm.{role}.plist"

    try:
        with open(plist_path, 'w') as f:
            f.write(plist_content)
        run_cmd(f"launchctl load {plist_path}", check=False)
        print_ok(f"macOS LaunchAgent installed: com.swarm.{role}")
        return True
    except Exception as e:
        print_err(f"Failed to create LaunchAgent: {e}")
        return False


def create_termux_launcher(node_dir: Path, role: str, info: Dict[str, str]) -> bool:
    """Create a Termux startup script."""
    script = f"""#!/data/data/com.termux/files/usr/bin/bash
# Swarm Node: {role}
# Auto-starts when Termux opens

cd {node_dir}
echo "[$(date)] Starting swarm node: {role}" >> logs/startup.log
python3 node_agent.py >> logs/service.log 2>&1 &
echo $! > scripts/node.pid
echo "[$(date)] Node started (PID: $(cat scripts/node.pid))" >> logs/startup.log
"""

    script_path = node_dir / "scripts" / "start.sh"
    try:
        with open(script_path, 'w') as f:
            f.write(script)
        os.chmod(script_path, 0o755)
        print_ok("Termux start script created")
        print_info("Run ./scripts/start.sh in Termux to start the node")
        print_info("Add to ~/.bashrc for auto-start: echo '~/swarm_node/scripts/start.sh' >> ~/.bashrc")
        return True
    except Exception as e:
        print_err(f"Failed to create Termux launcher: {e}")
        return False


def create_windows_launcher(node_dir: Path, role: str, info: Dict[str, str]) -> bool:
    """Create a Windows batch/PowerShell launcher."""
    # PowerShell startup script
    ps_script = f"""
# Swarm Node Service: {role}
# Run as: powershell -ExecutionPolicy Bypass -File start.ps1

$nodeDir = "{node_dir}"
$logDir = Join-Path $nodeDir "logs"

# Ensure log directory exists
if (!(Test-Path $logDir)) {{ New-Item -ItemType Directory -Path $logDir | Out-Null }}

# Check if already running
$pidFile = Join-Path $nodeDir "scripts\\node.pid"
if (Test-Path $pidFile) {{
    $pid = Get-Content $pidFile
    if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {{
        Write-Host "Node already running (PID: $pid)"
        exit 0
    }}
}}

# Start the node
Write-Host "Starting Swarm Node: {role}"
$proc = Start-Process -FilePath "{sys.executable}" -ArgumentList "node_agent.py" `
    -WorkingDirectory $nodeDir -WindowStyle Hidden -PassThru
$proc.Id | Out-File $pidFile
Write-Host "Node started (PID: $($proc.Id))"
"""

    ps_path = node_dir / "scripts" / "start.ps1"
    try:
        with open(ps_path, 'w') as f:
            f.write(ps_script)
        print_ok("PowerShell launcher created: scripts/start.ps1")
        print_info("Run: powershell -ExecutionPolicy Bypass -File scripts/start.ps1")
        return True
    except Exception as e:
        print_err(f"Failed to create Windows launcher: {e}")
        return False


def create_bash_launcher(node_dir: Path, role: str, info: Dict[str, str]) -> bool:
    """Create a generic bash launcher (fallback)."""
    script = f"""#!/bin/bash
# Swarm Node Launcher: {role}
# Generated by swarm_provision.py

NODE_DIR="{node_dir}"
PID_FILE="$NODE_DIR/scripts/node.pid"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Node already running (PID: $PID)"
        exit 0
    fi
fi

cd "$NODE_DIR" || exit 1
echo "[$(date)] Starting swarm node: {role}" >> logs/startup.log
nohup python3 node_agent.py >> logs/service.log 2>&1 &
echo $! > "$PID_FILE"
echo "[$(date)] Node started (PID: $!)" >> logs/startup.log
"""

    script_path = node_dir / "scripts" / "start.sh"
    try:
        with open(script_path, 'w') as f:
            f.write(script)
        os.chmod(script_path, 0o755)
        print_ok("Bash launcher created: scripts/start.sh")
        print_info("Run: ./scripts/start.sh")
        return True
    except Exception as e:
        print_err(f"Failed to create bash launcher: {e}")
        return False


# ============================================================================
# STEP 7: CREATE HEALTH CHECK SCRIPT
# ============================================================================

def create_health_check(node_dir: Path, role: str) -> bool:
    """Create a health check script."""
    script = '''#!/usr/bin/env python3
"""
Health check script for swarm node.
Run: python3 health_check.py
"""

import json
import os
import sys
import time
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config" / "node.json"

def check_health():
    """Check node health and print status."""
    issues = []

    # Check config exists
    if not CONFIG_PATH.exists():
        issues.append(f"Config not found: {CONFIG_PATH}")
        return {"status": "error", "issues": issues}

    # Load config
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    node_dir = Path(config["paths"]["node_dir"])

    # Check directories
    for dir_key, dir_path in config["paths"].items():
        if not os.path.isdir(dir_path):
            issues.append(f"Directory missing: {dir_key} = {dir_path}")

    # Check disk space
    try:
        stat = os.statvfs(str(node_dir))
        free_mb = (stat.f_bavail * stat.f_frsize) // (1024 * 1024)
        if free_mb < 50:
            issues.append(f"Low disk space: {free_mb}MB free")
    except Exception:
        pass

    # Check if process is running
    pid_file = node_dir / "scripts" / "node.pid"
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 0)  # Signal 0 = check if process exists
            process_status = f"running (PID: {pid})"
        except ProcessLookupError:
            process_status = "not running (stale PID file)"
            issues.append("Node process not running")
        except PermissionError:
            process_status = "running (different user)"
    else:
        process_status = "not running"

    # Check log file
    log_file = node_dir / "logs" / "node.log"
    if log_file.exists():
        log_size = log_file.stat().st_size
        log_age_hours = (time.time() - log_file.stat().st_mtime) / 3600
    else:
        log_size = 0
        log_age_hours = -1

    # Print report
    print("=" * 50)
    print(f"  SWARM NODE HEALTH CHECK")
    print(f"  Role: {config['name']}")
    print(f"  Hostname: {config['hostname']}")
    print("=" * 50)
    print(f"  Status: {'HEALTHY' if not issues else 'ISSUES FOUND'}")
    print(f"  Process: {process_status}")
    print(f"  Log: {log_size} bytes, {log_age_hours:.1f}h ago")
    print(f"  Version: {config['version']}")
    print(f"  Platform: {config['platform']['os']} ({config['platform']['platform']})")

    if issues:
        print(f"\\n  Issues ({len(issues)}):")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("\\n  All checks passed!")

    print("=" * 50)
    return {"status": "ok" if not issues else "error", "issues": issues}


if __name__ == "__main__":
    result = check_health()
    sys.exit(0 if result["status"] == "ok" else 1)
'''

    script_path = node_dir / "health_check.py"
    try:
        with open(script_path, 'w') as f:
            f.write(script)
        os.chmod(script_path, 0o755)
        print_ok("Health check script created")
        return True
    except Exception as e:
        print_err(f"Failed to create health check: {e}")
        return False


# ============================================================================
# STEP 8: CREATE STOP/UNINSTALL SCRIPTS
# ============================================================================

def create_management_scripts(node_dir: Path, role: str) -> bool:
    """Create stop and uninstall scripts."""
    # Stop script
    stop_script = f"""#!/bin/bash
# Stop swarm node: {role}
PID_FILE="{node_dir}/scripts/node.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping node (PID: $PID)..."
        kill "$PID"
        sleep 2
        if kill -0 "$PID" 2>/dev/null; then
            echo "Force killing..."
            kill -9 "$PID"
        fi
        echo "Node stopped."
    else
        echo "Node not running (stale PID file)"
    fi
    rm -f "$PID_FILE"
else
    echo "No PID file found. Node may not be running via launcher."
    echo "Try: pkill -f 'node_agent.py'"
fi
"""

    # Uninstall script
    uninstall_script = f"""#!/bin/bash
# Uninstall swarm node: {role}
# WARNING: This will remove all data in {node_dir}

echo "This will remove the swarm node at {node_dir}"
echo "All shared files, logs, and configuration will be deleted."
read -p "Are you sure? (y/N): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    # Stop if running
    if [ -f "{node_dir}/scripts/node.pid" ]; then
        PID=$(cat "{node_dir}/scripts/node.pid")
        kill "$PID" 2>/dev/null
        sleep 1
    fi

    # Remove systemd service if exists
    SERVICE="$HOME/.config/systemd/user/swarm-{role}.service"
    if [ -f "$SERVICE" ]; then
        systemctl --user stop swarm-{role}.service 2>/dev/null
        systemctl --user disable swarm-{role}.service 2>/dev/null
        rm -f "$SERVICE"
        systemctl --user daemon-reload 2>/dev/null
    fi

    # Ask about data
    read -p "Delete shared data too? (y/N): " del_data
    if [ "$del_data" = "y" ] || [ "$del_data" = "Y" ]; then
        rm -rf "{node_dir}"
        echo "Full removal complete."
    else
        # Keep shared data, remove scripts and config
        rm -rf "{node_dir}/config"
        rm -rf "{node_dir}/scripts"
        rm -f "{node_dir}/node_agent.py"
        rm -f "{node_dir}/health_check.py"
        rm -f "{node_dir}/stop.sh"
        rm -f "{node_dir}/uninstall.sh"
        echo "Node scripts removed. Shared data preserved at {node_dir}/shared"
    fi
else
    echo "Cancelled."
fi
"""

    try:
        stop_path = node_dir / "stop.sh"
        with open(stop_path, 'w') as f:
            f.write(stop_script)
        os.chmod(stop_path, 0o755)

        uninstall_path = node_dir / "uninstall.sh"
        with open(uninstall_path, 'w') as f:
            f.write(uninstall_script)
        os.chmod(uninstall_path, 0o755)

        print_ok("Management scripts created (stop.sh, uninstall.sh)")
        return True
    except Exception as e:
        print_err(f"Failed to create management scripts: {e}")
        return False


# ============================================================================
# STEP 9: WRITE QUICK-START README
# ============================================================================

def create_readme(node_dir: Path, role: str, info: Dict[str, str]) -> bool:
    """Create a quick-start README for the node."""
    readme = f"""# Swarm Node — {NODE_ROLES[role]['name']}

## Quick Start

### 1. Start the node
```bash
./scripts/start.sh
```

### 2. Check health
```bash
python3 health_check.py
```

### 3. View logs
```bash
tail -f logs/service.log
```

### 4. Stop the node
```bash
./stop.sh
```

## Configuration
Edit `config/node.json` to set:
- `orchestrator_host` — IP of the main swarm server
- `orchestrator_port` — Port (default: 9997)

## Role: {role}
{NODE_ROLES[role]['description']}

## Platform
- OS: {info.get('os', 'unknown')} ({info.get('platform', '')})
- Architecture: {info.get('architecture', '')}
- Hostname: {info.get('hostname', '')}

## Shared Directory
Place files in `shared/` to make them accessible to all swarm agents:
- `shared/knowledge/` — Reference docs, facts
- `shared/tasks/` — Task assignments
- `shared/results/` — Completed work
- `shared/logs/` — Agent logs

## Troubleshooting
- **Node won't start**: Check `logs/service.log` for errors
- **Can't connect to orchestrator**: Verify `orchestrator_host` in config
- **Permission denied**: Make sure scripts are executable (`chmod +x scripts/start.sh`)
- **Python module errors**: Run `pip3 install -r requirements.txt`

## Uninstall
```bash
./uninstall.sh
```
"""

    readme_path = node_dir / "README.md"
    try:
        with open(readme_path, 'w') as f:
            f.write(readme)
        print_ok("README.md created")
        return True
    except Exception as e:
        print_err(f"Failed to create README: {e}")
        return False


# ============================================================================
# STEP 10: POST-INSTALL VERIFICATION
# ============================================================================

def verify_installation(node_dir: Path, role: str) -> bool:
    """Verify the installation is complete and working."""
    checks = []

    # Check directory structure
    required_dirs = ["shared", "config", "logs", "scripts"]
    for d in required_dirs:
        path = node_dir / d
        if path.is_dir():
            checks.append((f"Directory: {d}", True))
        else:
            checks.append((f"Directory: {d}", False))

    # Check required files
    required_files = [
        "config/node.json",
        "node_agent.py",
        "health_check.py",
        "scripts/start.sh",
        "stop.sh",
        "uninstall.sh",
        "README.md",
    ]
    for f in required_files:
        path = node_dir / f
        if path.exists():
            checks.append((f"File: {f}", True))
        else:
            checks.append((f"File: {f}", False))

    # Check Python
    py_check = run_cmd(f"{sys.executable} --version", check=False)
    if py_check:
        checks.append((f"Python: {py_check.stdout.strip()}", True))
    else:
        checks.append(("Python: not found", False))

    # Check pip packages
    for pkg in REQUIRED_PACKAGES:
        pkg_name = pkg.split('>=')[0].split('==')[0]
        result = run_cmd(f"{sys.executable} -c 'import {pkg_name}' 2>/dev/null", check=False)
        if result and result.returncode == 0:
            checks.append((f"Package: {pkg_name}", True))
        else:
            checks.append((f"Package: {pkg_name}", False))

    # Print results
    print(f"\n{Colors.BOLD}Installation Verification:{Colors.END}")
    all_ok = True
    for name, ok in checks:
        if ok:
            print_ok(name)
        else:
            print_err(name)
            all_ok = False

    return all_ok


# ============================================================================
# MAIN PROVISIONING FLOW
# ============================================================================

def provision(role: str, orchestrator_host: str, orchestrator_port: int,
              auto: bool = False) -> bool:
    """Main provisioning function."""
    total_steps = 8

    print_banner()

    # Step 1: System info
    print_step(1, total_steps, "Detecting system...")
    info = get_system_info()

    # Apply overrides
    if args.arch:
        info["architecture"] = args.arch
        print_info(f"Architecture (override): {args.arch}")
    if args.os:
        info["platform"] = args.os
        print_info(f"Platform (override): {args.os}")

    print_info(f"OS: {info.get('os', 'unknown')} ({info.get('platform', '')})")
    print_info(f"Architecture: {info.get('architecture', '')}")
    print_info(f"Hostname: {info.get('hostname', '')}")
    print_info(f"Python: {platform.python_version()}")
    print_info(f"RAM: {info.get('total_ram_mb', '?')}MB")
    print_info(f"Free disk: {info.get('free_disk_mb', '?')}MB")

    if not auto:
        print()
        input("Press Enter to continue or Ctrl+C to cancel...")

    # Step 2: Compatibility check
    print_step(2, total_steps, "Checking compatibility...")
    compatible, issues = check_system_compatibility(role)
    if not compatible:
        print_err("System compatibility issues found:")
        for issue in issues:
            print_err(f"  - {issue}")
        if not auto:
            print()
            input("Press Enter to continue anyway, or Ctrl+C to abort...")
        else:
            print_warn("Continuing in auto mode despite issues...")

    # Step 3: Install dependencies
    print_step(3, total_steps, "Installing dependencies...")
    if not install_system_dependencies(info):
        print_err("Failed to install system dependencies")
        return False

    if not install_python_packages(role):
        print_warn("Some Python packages failed to install")

    # Step 4: Create directories
    print_step(4, total_steps, "Creating directory structure...")
    node_dir = Path(f"/home/jimmy/swarm_node")
    if not create_directory_structure(node_dir):
        return False

    # Step 5: Generate config
    print_step(5, total_steps, "Generating configuration...")
    if not generate_config(role, orchestrator_host, orchestrator_port, node_dir, info):
        return False

    # Step 6: Create node agent
    print_step(6, total_steps, "Creating node agent script...")
    if not create_node_agent_script(node_dir, role, info):
        return False

    # Step 7: Create launcher
    print_step(7, total_steps, "Setting up service launcher...")
    if not create_launcher(node_dir, role, info):
        print_warn("Service launcher creation had issues. Use ./scripts/start.sh to run manually.")

    # Step 8: Create management scripts
    print_step(8, total_steps, "Creating management scripts...")
    create_health_check(node_dir, role)
    create_management_scripts(node_dir, role)
    create_readme(node_dir, role, info)

    # Fix start.sh to use absolute path
    start_script = node_dir / "scripts" / "start.sh"
    if start_script.exists():
        content = start_script.read_text()
        content = content.replace(
            f'nohup python3 node_agent.py',
            f'nohup {sys.executable} {node_dir}/node_agent.py'
        )
        start_script.write_text(content)

    # Verification
    print(f"\n{Colors.BOLD}{'=' * 50}")
    print(f"  PROVISIONING COMPLETE")
    print(f"{'=' * 50}{Colors.END}")

    success = verify_installation(node_dir, role)

    # Print next steps
    print(f"""
{Colors.GREEN}{Colors.BOLD}Next Steps:{Colors.END}

  1. {Colors.BOLD}Configure{Colors.END}: Edit {node_dir}/config/node.json
     Set orchestrator_host to your main swarm server IP

  2. {Colors.BOLD}Start{Colors.END}: ./{node_dir}/scripts/start.sh

  3. {Colors.BOLD}Verify{Colors.END}: python3 {node_dir}/health_check.py

  4. {Colors.BOLD}Test{Colors.END}: Open http://localhost:8080 in browser
     (if this node is also running the dashboard)

{Colors.DIM}Node directory: {node_dir}
Role: {NODE_ROLES[role]['name']}
Swarm version: {SWARM_VERSION}{Colors.END}
""")

    return success


def check_existing_install() -> Optional[str]:
    """Check if swarm_node already exists."""
    node_dir = Path(f"/home/jimmy/swarm_node")
    config_path = node_dir / "config" / "node.json"

    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            return config.get("role", "unknown")
        except Exception:
            return "corrupted"
    return None


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=f"Swarm Node Provisioner v{SWARM_VERSION} — Turn any device into a swarm agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              %(prog)s                           # Interactive mode
              %(prog)s --role chat-node          # Provision as chat node
              %(prog)s --role xbox-hermes --auto # Auto-install without prompts
              %(prog)s --role antigravity --orchestrator 192.168.1.100
              %(prog)s --check                   # Check existing installation
              %(prog)s --uninstall               # Remove swarm node
        """),
    )

    parser.add_argument(
        "--role", "-r",
        choices=list(NODE_ROLES.keys()),
        default=None,
        help="Node role to provision",
    )
    parser.add_argument(
        "--orchestrator",
        default=DEFAULT_ORCHESTRATOR_HOST,
        help=f"Orchestrator host (default: {DEFAULT_ORCHESTRATOR_HOST})",
    )
    parser.add_argument(
        "--orchestrator-port",
        type=int,
        default=DEFAULT_ORCHESTRATOR_PORT,
        help=f"Orchestrator port (default: {DEFAULT_ORCHESTRATOR_PORT})",
    )
    parser.add_argument(
        "--auto", "-a",
        action="store_true",
        help="Auto-install without prompts",
    )
    parser.add_argument(
        "--venv",
        action="store_true",
        help="Create a Python virtual environment for the node",
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check existing installation",
    )
    parser.add_argument(
        "--uninstall", "-u",
        action="store_true",
        help="Uninstall swarm node",
    )
    parser.add_argument(
        "--list-roles", "-l",
        action="store_true",
        help="List available roles",
    )
    parser.add_argument(
        "--arch",
        default=None,
        help="Override architecture detection (x86_64, aarch64, armv7l)",
    )
    parser.add_argument(
        "--os",
        default=None,
        help="Override OS detection (linux, macos, wsl2, termux)",
    )

    args = parser.parse_args()

    # List roles
    if args.list_roles:
        print(f"\n{Colors.BOLD}Available Swarm Node Roles:{Colors.END}\n")
        for role_id, role_info in NODE_ROLES.items():
            print(f"  {Colors.CYAN}{role_id:15s}{Colors.END}  {role_info['name']}")
            print(f"  {'':15s}  {role_info['description']}")
            print(f"  {'':15s}  Min RAM: {role_info['min_ram_mb']}MB | Min Disk: {role_info['min_disk_mb']}MB")
            print()
        return

    # Check existing
    if args.check:
        existing = check_existing_install()
        if existing:
            print(f"Existing installation found: role={existing}")
            node_dir = Path("/home/jimmy/swarm_node")
            run_cmd(f"python3 {node_dir}/health_check.py", check=False)
        else:
            print("No existing swarm node installation found.")
        return

    # Uninstall
    if args.uninstall:
        node_dir = Path("/home/jimmy/swarm_node")
        uninstall_script = node_dir / "uninstall.sh"
        if uninstall_script.exists():
            run_cmd(str(uninstall_script))
        else:
            print_err("Uninstall script not found. Remove manually:")
            print(f"  rm -rf {node_dir}")
        return

    # Interactive role selection if not specified
    role = args.role
    if role is None:
        print(f"\n{Colors.BOLD}Select a role for this node:{Colors.END}\n")
        roles_list = list(NODE_ROLES.keys())
        for i, (role_id, role_info) in enumerate(NODE_ROLES.items(), 1):
            print(f"  {Colors.CYAN}{i}.{Colors.END} {role_info['name']}")
            print(f"     {role_info['description']}")
            print()

        while True:
            try:
                choice = input(f"Enter choice (1-{len(roles_list)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(roles_list):
                    role = roles_list[idx]
                    break
                else:
                    print("Invalid choice. Try again.")
            except (ValueError, IndexError):
                print("Invalid input. Enter a number.")
            except EOFError:
                print("\nCancelled.")
                return

    # Run provisioning
    success = provision(
        role=role,
        orchestrator_host=args.orchestrator,
        orchestrator_port=args.orchestrator_port,
        auto=args.auto,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
