#!/usr/bin/env python3
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
        print(f"\n  Issues ({len(issues)}):")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("\n  All checks passed!")

    print("=" * 50)
    return {"status": "ok" if not issues else "error", "issues": issues}


if __name__ == "__main__":
    result = check_health()
    sys.exit(0 if result["status"] == "ok" else 1)
