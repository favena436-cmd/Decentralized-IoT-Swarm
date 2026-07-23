#!/usr/bin/env python3
"""
swarm_services.py — Paid Service & Specialty Skills System

Manages billable services, client accounts, usage tracking, and specialty
skill registration for the swarm's paid offerings.

Tiers:
  Free    — Basic chat, standard support
  Pro     ($29/mo/node)  — Priority routing, voice AI, advanced monitoring
  Business ($99/mo/node) — Unlimited nodes, custom roles, SLA, API access
  Enterprise (custom)     — On-premise, compliance, dedicated support

Specialty Skills:
  - voice-ai: STT/TTS pipeline for phone/voice assistants
  - network-monitoring: RTU stats, alerts, dashboards
  - ai-automation: Workflow automation, chatbots, document processing
  - home-server-setup: NAS, networking, smart home installation
  - multi-agent-consulting: Custom agent design and deployment
  - mcp-server: Expose swarm tools to MCP clients
  - compatibility-layer: Framework adapters for external agents

Usage:
  python3 swarm_services.py --status          # Show service status
  python3 swarm_services.py --tier pro        # Set node tier
  python3 swarm_services.py --usage           # Show usage stats
  python3 swarm_services.py --billing         # Generate billing report
  python3 swarm_services.py --skills          # List available skills
  python3 swarm_services.py --register-skill --name my-skill --price 9.99
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

# Configuration
DATA_DIR = Path("/home/jimmy/swarm_node/shared/services")
CLIENTS_FILE = DATA_DIR / "clients.json"
USAGE_FILE = DATA_DIR / "usage.json"
SKILLS_FILE = DATA_DIR / "skills.json"

# Service tiers
TIERS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "max_nodes": 3,
        "features": ["basic_chat", "standard_response", "community_support"],
        "priority": 1,
        "sla_uptime": None,
        "support_response_hours": None,
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 29.00,
        "max_nodes": 10,
        "features": [
            "basic_chat", "priority_routing", "voice_ai",
            "advanced_monitoring", "auto_update", "custom_skills",
            "email_support",
        ],
        "priority": 2,
        "sla_uptime": 99.0,
        "support_response_hours": 24,
    },
    "business": {
        "name": "Business",
        "price_monthly": 99.00,
        "max_nodes": -1,  # Unlimited
        "features": [
            "basic_chat", "priority_routing", "voice_ai",
            "advanced_monitoring", "auto_update", "custom_skills",
            "dedicated_orchestrator", "custom_roles",
            "usage_analytics", "api_access", "sla_guarantee",
            "priority_support",
        ],
        "priority": 3,
        "sla_uptime": 99.9,
        "support_response_hours": 4,
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 0,  # Custom pricing
        "max_nodes": -1,
        "features": [
            "basic_chat", "priority_routing", "voice_ai",
            "advanced_monitoring", "auto_update", "custom_skills",
            "dedicated_orchestrator", "custom_roles",
            "usage_analytics", "api_access", "sla_guarantee",
            "priority_support", "on_premise", "compliance",
            "audit_logging", "white_label",
        ],
        "priority": 4,
        "sla_uptime": 99.99,
        "support_response_hours": 1,
    },
}

# Default specialty skills
DEFAULT_SKILLS = {
    "voice-ai": {
        "name": "Voice AI Pipeline",
        "description": "Speech-to-text and text-to-speech for voice assistants and phone systems",
        "tier": "pro",
        "monthly_price": 0,  # Included in Pro
        "setup_fee": 0,
        "capabilities": ["sttt", "tts", "voice_chat", "phone_integration"],
    },
    "network-monitoring": {
        "name": "Network Monitoring",
        "description": "Real-time system stats, alerts, and dashboards for network monitoring",
        "tier": "free",
        "monthly_price": 0,
        "setup_fee": 0,
        "capabilities": ["rtu_stats", "alerts", "dashboard", "uptime_monitoring"],
    },
    "ai-automation": {
        "name": "AI Automation",
        "description": "Custom AI workflows, chatbots, and document processing automation",
        "tier": "pro",
        "monthly_price": 19.99,
        "setup_fee": 99.00,
        "capabilities": ["workflow_design", "chatbot", "document_processing", "api_integration"],
    },
    "home-server-setup": {
        "name": "Home Server Setup",
        "description": "NAS configuration, network hardwiring, smart home installation",
        "tier": "pro",
        "monthly_price": 0,
        "setup_fee": 149.00,
        "capabilities": ["nas_setup", "network_config", "smart_home", "camera_nvr"],
    },
    "multi-agent-consulting": {
        "name": "Multi-Agent Consulting",
        "description": "Custom agent design, deployment, and optimization consulting",
        "tier": "business",
        "monthly_price": 0,
        "setup_price": 499.00,
        "hourly_rate": 150.00,
        "capabilities": ["agent_design", "deployment", "optimization", "training"],
    },
    "mcp-server": {
        "name": "MCP Server Access",
        "description": "Expose swarm tools via Model Context Protocol for external AI clients",
        "tier": "pro",
        "monthly_price": 9.99,
        "setup_fee": 0,
        "capabilities": ["mcp_tools", "stdio_transport", "http_transport", "claude_desktop"],
    },
    "compatibility-layer": {
        "name": "Framework Compatibility",
        "description": "Adapters for OpenAI, AutoGen, LangChain, ADK, A2A frameworks",
        "tier": "business",
        "monthly_price": 0,
        "setup_fee": 0,
        "capabilities": ["openai_agents", "autogen", "langchain", "google_adk", "a2a_protocol"],
    },
}


class ServiceManager:
    """Manages paid services, clients, and billing."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.clients = self._load_json(CLIENTS_FILE, {})
        self.usage = self._load_json(USAGE_FILE, {})
        self.skills = self._load_json(SKILLS_FILE, DEFAULT_SKILLS)

    def _load_json(self, path: Path, default: dict) -> dict:
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return default

    def _save_json(self, path: Path, data: dict):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def register_client(self, client_id: str, name: str, email: str,
                        tier: str = "free") -> dict:
        """Register a new client."""
        if tier not in TIERS:
            raise ValueError(f"Invalid tier: {tier}. Available: {list(TIERS.keys())}")

        client = {
            "id": client_id,
            "name": name,
            "email": email,
            "tier": tier,
            "registered_at": datetime.now().isoformat(),
            "nodes": [],
            "monthly_usage": {},
            "payment_status": "active",
            "enabled_skills": [],
        }

        # Auto-enable skills for the tier
        tier_features = TIERS[tier]["features"]
        for skill_id, skill in self.skills.items():
            if skill["tier"] in ("free", tier) or skill["tier"] == "free":
                client["enabled_skills"].append(skill_id)

        self.clients[client_id] = client
        self._save_json(CLIENTS_FILE, self.clients)

        return client

    def add_node(self, client_id: str, node_id: str) -> bool:
        """Add a node to a client's account."""
        if client_id not in self.clients:
            return False

        client = self.clients[client_id]
        tier = TIERS[client["tier"]]

        # Check node limit
        if tier["max_nodes"] != -1 and len(client["nodes"]) >= tier["max_nodes"]:
            return False

        if node_id not in client["nodes"]:
            client["nodes"].append(node_id)
            self._save_json(CLIENTS_FILE, self.clients)

        return True

    def record_usage(self, client_id: str, node_id: str, task_type: str,
                     duration_seconds: float, success: bool = True):
        """Record task usage for billing."""
        month_key = datetime.now().strftime("%Y-%m")

        if client_id not in self.usage:
            self.usage[client_id] = {}
        if month_key not in self.usage[client_id]:
            self.usage[client_id][month_key] = {}
        if node_id not in self.usage[client_id][month_key]:
            self.usage[client_id][month_key][node_id] = []

        self.usage[client_id][month_key][node_id].append({
            "task_type": task_type,
            "duration_seconds": duration_seconds,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        })

        self._save_json(USAGE_FILE, self.usage)

    def get_client_usage(self, client_id: str, month: str = None) -> dict:
        """Get usage stats for a client."""
        if month is None:
            month = datetime.now().strftime("%Y-%m")

        if client_id not in self.usage or month not in self.usage[client_id]:
            return {"total_tasks": 0, "total_duration": 0, "success_rate": 0}

        month_data = self.usage[client_id][month]
        all_tasks = []
        for node_tasks in month_data.values():
            all_tasks.extend(node_tasks)

        total = len(all_tasks)
        successful = sum(1 for t in all_tasks if t.get("success", True))
        total_duration = sum(t.get("duration_seconds", 0) for t in all_tasks)

        return {
            "total_tasks": total,
            "total_duration_seconds": round(total_duration, 2),
            "success_rate": round(successful / total * 100, 1) if total > 0 else 100,
            "by_task_type": self._aggregate_by_type(all_tasks),
            "by_node": {node: len(tasks) for node, tasks in month_data.items()},
        }

    def _aggregate_by_type(self, tasks: list) -> dict:
        result = {}
        for task in tasks:
            tt = task.get("task_type", "unknown")
            if tt not in result:
                result[tt] = {"count": 0, "total_duration": 0}
            result[tt]["count"] += 1
            result[tt]["total_duration"] += task.get("duration_seconds", 0)
        return result

    def generate_invoice(self, client_id: str, month: str = None) -> dict:
        """Generate an invoice for a client."""
        if client_id not in self.clients:
            raise ValueError(f"Client not found: {client_id}")

        client = self.clients[client_id]
        tier = TIERS[client["tier"]]

        if month is None:
            month = datetime.now().strftime("%Y-%m")

        usage = self.get_client_usage(client_id, month)

        # Calculate charges
        line_items = []
        base_price = tier["price_monthly"]

        if client["tier"] == "enterprise":
            # Enterprise: custom pricing, just show base
            line_items.append({
                "description": "Enterprise Base (custom pricing)",
                "quantity": 1,
                "unit_price": base_price,
                "total": base_price,
            })
        elif client["tier"] == "free":
            line_items.append({
                "description": "Free Tier",
                "quantity": 1,
                "unit_price": 0,
                "total": 0,
            })
        else:
            line_items.append({
                "description": f"{tier['name']} Tier Base",
                "quantity": 1,
                "unit_price": base_price,
                "total": base_price,
            })

        # Add skill charges
        for skill_id in client.get("enabled_skills", []):
            skill = self.skills.get(skill_id, {})
            if skill.get("monthly_price", 0) > 0:
                line_items.append({
                    "description": f"Skill: {skill['name']}",
                    "quantity": 1,
                    "unit_price": skill["monthly_price"],
                    "total": skill["monthly_price"],
                })

        subtotal = sum(item["total"] for item in line_items)
        tax = round(subtotal * 0.08, 2)  # 8% tax
        total = subtotal + tax

        return {
            "invoice_id": f"INV-{client_id}-{month}",
            "client": {
                "id": client_id,
                "name": client["name"],
                "email": client["email"],
                "tier": client["tier"],
            },
            "month": month,
            "line_items": line_items,
            "subtotal": round(subtotal, 2),
            "tax": tax,
            "total": round(total, 2),
            "generated_at": datetime.now().isoformat(),
            "due_date": (datetime.now() + timedelta(days=14)).isoformat(),
        }

    def list_skills(self, tier: str = None) -> list:
        """List available skills, optionally filtered by tier."""
        results = []
        for skill_id, skill in self.skills.items():
            if tier and skill["tier"] != tier and skill["tier"] != "free":
                continue
            results.append({
                "id": skill_id,
                **skill,
            })
        return results

    def enable_skill(self, client_id: str, skill_id: str) -> bool:
        """Enable a skill for a client."""
        if client_id not in self.clients:
            return False
        if skill_id not in self.skills:
            return False

        skill = self.skills[skill_id]
        client = self.clients[client_id]

        # Check tier compatibility
        client_tier = TIERS[client["tier"]]
        if skill["tier"] not in client_tier["features"] and skill["tier"] != "free":
            # Need to upgrade tier first
            return False

        if skill_id not in client["enabled_skills"]:
            client["enabled_skills"].append(skill_id)
            self._save_json(CLIENTS_FILE, self.clients)

        return True

    def get_status(self) -> dict:
        """Get overall service status."""
        return {
            "total_clients": len(self.clients),
            "by_tier": {
                tier: sum(1 for c in self.clients.values() if c["tier"] == tier)
                for tier in TIERS
            },
            "total_nodes": sum(len(c.get("nodes", [])) for c in self.clients.values()),
            "total_skills": len(self.skills),
            "active_clients": sum(
                1 for c in self.clients.values()
                if c.get("payment_status") == "active"
            ),
        }


def main():
    parser = argparse.ArgumentParser(description="Swarm Paid Services Manager")
    parser.add_argument("--status", action="store_true", help="Show service status")
    parser.add_argument("--register", action="store_true", help="Register a client")
    parser.add_argument("--client-id", help="Client ID")
    parser.add_argument("--name", help="Client name")
    parser.add_argument("--email", help="Client email")
    parser.add_argument("--tier", choices=list(TIERS.keys()), help="Service tier")
    parser.add_argument("--usage", action="store_true", help="Show usage stats")
    parser.add_argument("--billing", action="store_true", help="Generate invoice")
    parser.add_argument("--skills", action="store_true", help="List available skills")
    parser.add_argument("--enable-skill", help="Enable a skill for a client")
    parser.add_argument("--month", help="Month for usage/billing (YYYY-MM)")

    args = parser.parse_args()
    manager = ServiceManager()

    if args.status:
        status = manager.get_status()
        print(json.dumps(status, indent=2))

    elif args.register:
        if not all([args.client_id, args.name, args.email, args.tier]):
            print("Error: --client-id, --name, --email, --tier required")
            return
        client = manager.register_client(args.client_id, args.name, args.email, args.tier)
        print(json.dumps(client, indent=2))

    elif args.usage:
        if not args.client_id:
            print("Error: --client-id required")
            return
        usage = manager.get_client_usage(args.client_id, args.month)
        print(json.dumps(usage, indent=2))

    elif args.billing:
        if not args.client_id:
            print("Error: --client-id required")
            return
        invoice = manager.generate_invoice(args.client_id, args.month)
        print(json.dumps(invoice, indent=2))

    elif args.skills:
        tier_filter = args.tier if hasattr(args, 'tier') and args.tier else None
        skills = manager.list_skills(tier_filter)
        print(json.dumps(skills, indent=2))

    elif args.enable_skill:
        if not args.client_id:
            print("Error: --client-id required")
            return
        result = manager.enable_skill(args.client_id, args.enable_skill)
        print(json.dumps({"success": result}))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
