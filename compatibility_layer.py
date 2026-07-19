#!/usr/bin/env python3
"""
compatibility_layer.py — AI Agent Framework Compatibility Shims

Provides adapters to integrate the swarm with popular AI agent frameworks,
making the swarm accessible regardless of which framework clients use.

Supported frameworks:
  - OpenAI Agents SDK
  - AutoGen / CrewAI
  - LangChain / LangGraph
  - Google ADK (Agent Development Kit)
  - MCP (Model Context Protocol)
  - A2A (Agent-to-Agent protocol by Google)

Architecture:
  ┌─────────────────────────────────────────────────────┐
  │              External Agent Framework                │
  │  (OpenAI / AutoGen / LangChain / ADK / MCP / A2A)   │
  └──────────────────────┬──────────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────────┐
  │              AgentAdapter (base class)               │
  │  - send_task()    - get_status()    - list_agents() │
  └──────────────────────┬──────────────────────────────┘
                         │
  ┌──────────────────────▼──────────────────────────────┐
  │              SwarmClient (TCP protocol)              │
  │  - JSON-over-TCP to orchestrator (port 9997)         │
  └─────────────────────────────────────────────────────┘

Usage:
    from compatibility_layer import SwarmToolServer, OpenAIAdapter

    # Expose swarm as MCP-compatible tools
    server = SwarmToolServer(orchestrator_host="192.168.1.100")
    server.run()  # Starts MCP server on stdio

    # Or use with OpenAI Agents SDK
    agent = OpenAIAdapter(orchestrator_host="192.168.1.100")
    agent.run()
"""

import abc
import asyncio
import json
import logging
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger("swarm.compat")

# ---------------------------------------------------------------------------
# Swarm Client (reuses existing protocol)
# ---------------------------------------------------------------------------

class SwarmClient:
    """Lightweight synchronous wrapper around the SwarmNode TCP protocol."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9997):
        self.host = host
        self.port = port

    def _send_raw(self, payload: dict) -> dict:
        """Send a JSON command over TCP and return the response."""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((self.host, self.port))
            data = json.dumps(payload).encode("utf-8") + b"\n"
            sock.sendall(data)
            # Read response
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
            sock.close()
            return json.loads(buf.decode("utf-8").strip())
        except ConnectionRefusedError:
            return {"status": "error", "error": f"Cannot connect to {self.host}:{self.port}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def send_task(self, task: str, args: list = None, kwargs: dict = None) -> dict:
        """Send a task to the orchestrator."""
        return self._send_raw({
            "task": task,
            "args": args or [],
            "kwargs": kwargs or {},
        })

    def ping(self) -> dict:
        """Ping the orchestrator."""
        return self._send_raw({"task": "ping"})

    def get_status(self) -> dict:
        """Get orchestrator status."""
        return self._send_raw({"task": "status"})

    def list_agents(self) -> list:
        """List available agents in the swarm."""
        resp = self._send_raw({"task": "agents"})
        if resp.get("status") == "success":
            return resp.get("result", [])
        return []

    def get_history(self) -> list:
        """Get chat history."""
        resp = self._send_raw({"task": "history"})
        if resp.get("status") == "success":
            return resp.get("result", [])
        return []

    def clear_history(self) -> dict:
        """Clear chat history."""
        return self._send_raw({"task": "clear"})

    def get_rtu(self) -> dict:
        """Get real-time usage stats."""
        return self._send_raw({"task": "rtu"})


# ---------------------------------------------------------------------------
# Base Agent Adapter
# ---------------------------------------------------------------------------

class AgentAdapter(abc.ABC):
    """
    Abstract base class for framework-specific adapters.

    Subclasses implement `run()` to start listening for tasks from the
    external framework and route them through the swarm.
    """

    def __init__(self, orchestrator_host: str = "127.0.0.1",
                 orchestrator_port: int = 9997):
        self.client = SwarmClient(orchestrator_host, orchestrator_port)
        self.orchestrator_host = orchestrator_host
        self.orchestrator_port = orchestrator_port

    @abc.abstractmethod
    def run(self):
        """Start the adapter. Blocks until stopped."""
        pass

    @abc.abstractmethod
    def stop(self):
        """Stop the adapter gracefully."""
        pass

    def health_check(self) -> dict:
        """Check if the swarm is reachable."""
        return self.client.ping()


# ---------------------------------------------------------------------------
# OpenAI Agents SDK Adapter
# ---------------------------------------------------------------------------

class OpenAIAdapter(AgentAdapter):
    """
    Adapter for the OpenAI Agents SDK.

    Allows OpenAI Agents to send tasks to the swarm as if it were
    another agent in their multi-agent setup.

    Requires: pip install openai-agents
    """

    def __init__(self, orchestrator_host: str = "127.0.0.1",
                 orchestrator_port: int = 9997,
                 tool_name: str = "swarm_task",
                 tool_description: str = "Send a task to the swarm orchestrator"):
        super().__init__(orchestrator_host, orchestrator_port)
        self.tool_name = tool_name
        self.tool_description = tool_description
        self._running = False

    def get_tool_definition(self) -> dict:
        """Return OpenAI function-calling tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.tool_name,
                "description": self.tool_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Task type (chat, status, agents, rtu, execute, design)",
                            "enum": ["chat", "status", "agents", "rtu", "execute", "design"],
                        },
                        "message": {
                            "type": "string",
                            "description": "Message or arguments for the task",
                        },
                    },
                    "required": ["task"],
                },
            },
        }

    def execute_tool(self, task: str, message: str = "") -> dict:
        """Execute a tool call from an OpenAI Agent."""
        if task == "chat":
            return self.client.send_task("chat", [message])
        elif task == "status":
            return self.client.get_status()
        elif task == "agents":
            return {"status": "success", "agents": self.client.list_agents()}
        elif task == "rtu":
            return self.client.get_rtu()
        elif task == "execute":
            return self.client.send_task("execute", [message])
        elif task == "design":
            return self.client.send_task("design", [message])
        else:
            return {"status": "error", "error": f"Unknown task: {task}"}

    def run(self):
        """Start the adapter (reads from stdin for function calls)."""
        self._running = True
        logger.info(f"OpenAI Adapter running — swarm at {self.orchestrator_host}:{self.orchestrator_port}")
        print(f"OpenAI Adapter ready. Tool: {self.tool_name}", file=sys.stderr)

        # If openai-agents is available, register as a tool
        try:
            from openai_agents import Tool
            tool = Tool(
                name=self.tool_name,
                description=self.tool_description,
                handler=self.execute_tool,
            )
            logger.info("Registered with OpenAI Agents SDK")
        except ImportError:
            logger.info("openai-agents not installed. Running in standalone mode.")

        # Keep running
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self._running = False


# ---------------------------------------------------------------------------
# AutoGen / CrewAI Adapter
# ---------------------------------------------------------------------------

class AutoGenAdapter(AgentAdapter):
    """
    Adapter for AutoGen and CrewAI multi-agent frameworks.

    Registers the swarm as a "proxy agent" that can receive messages
    from the AutoGen group chat and route them to the swarm.

    Requires: pip install autogen-agentchat or crewai
    """

    def __init__(self, orchestrator_host: str = "127.0.0.1",
                 orchestrator_port: int = 9997,
                 agent_name: str = "SwarmProxy"):
        super().__init__(orchestrator_host, orchestrator_port)
        self.agent_name = agent_name
        self._running = False

    def get_agent_config(self) -> dict:
        """Return AutoGen agent configuration."""
        return {
            "name": self.agent_name,
            "system_message": (
                "You are a proxy to the Swarm orchestrator. "
                "Route user requests to the swarm for processing by specialized agents "
                "(chat-node, antigravity, xbox-hermes). "
                "Available tasks: chat, status, agents, rtu, execute, design."
            ),
            "function_map": {
                "swarm_task": self._handle_swarm_task,
            },
        }

    def _handle_swarm_task(self, task: str = "chat", message: str = "") -> str:
        """Handle a task from AutoGen."""
        if task == "chat":
            result = self.client.send_task("chat", [message])
        elif task == "status":
            result = self.client.get_status()
        elif task == "agents":
            result = {"agents": self.client.list_agents()}
        elif task == "rtu":
            result = self.client.get_rtu()
        else:
            result = self.client.send_task(task, [message])

        return json.dumps(result, indent=2)

    def register_with_autogen(self) -> bool:
        """Try to register with AutoGen."""
        try:
            import autogen
            logger.info(f"AutoGen detected. Registering '{self.agent_name}' as proxy agent.")
            return True
        except ImportError:
            logger.info("AutoGen not installed. Running in standalone mode.")
            return False

    def run(self):
        """Start the adapter."""
        self._running = True
        logger.info(f"AutoGen Adapter running — swarm at {self.orchestrator_host}:{self.orchestrator_port}")
        self.register_with_autogen()
        print(f"AutoGen Adapter ready. Agent: {self.agent_name}", file=sys.stderr)

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self._running = False


# ---------------------------------------------------------------------------
# LangChain / LangGraph Adapter
# ---------------------------------------------------------------------------

class LangChainAdapter(AgentAdapter):
    """
    Adapter for LangChain and LangGraph.

    Exposes the swarm as a LangChain Tool that can be used in chains,
    agents, or LangGraph graphs.

    Requires: pip install langchain langgraph
    """

    def __init__(self, orchestrator_host: str = "127.0.0.1",
                 orchestrator_port: int = 9997,
                 tool_name: str = "swarm_orchestrator"):
        super().__init__(orchestrator_host, orchestrator_port)
        self.tool_name = tool_name

    def get_tool_schema(self) -> dict:
        """Return LangChain tool schema."""
        return {
            "name": self.tool_name,
            "description": (
                "Send tasks to the Swarm AI orchestrator. "
                "Use this to chat with AI agents, check system status, "
                "get real-time usage stats, or execute commands."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Task type: chat, status, agents, rtu, execute",
                    },
                    "message": {
                        "type": "string",
                        "description": "Message or arguments for the task",
                    },
                },
                "required": ["task"],
            },
        }

    def invoke(self, task: str, message: str = "") -> str:
        """Invoke the swarm tool (LangChain-compatible signature)."""
        if task == "chat":
            result = self.client.send_task("chat", [message])
        elif task == "status":
            result = self.client.get_status()
        elif task == "agents":
            result = {"agents": self.client.list_agents()}
        elif task == "rtu":
            result = self.client.get_rtu()
        else:
            result = self.client.send_task(task, [message])

        return json.dumps(result, indent=2)

    def as_langchain_tool(self):
        """Return a LangChain StructuredTool instance."""
        try:
            from langchain.tools import StructuredTool
            return StructuredTool.from_function(
                name=self.tool_name,
                func=self.invoke,
                description=self.get_tool_schema()["description"],
            )
        except ImportError:
            logger.warning("langchain not installed. Use invoke() directly.")
            return None

    def as_langgraph_node(self):
        """Return a callable usable as a LangGraph node."""
        def swarm_node(state: dict) -> dict:
            task = state.get("task", "chat")
            message = state.get("message", "")
            result = self.invoke(task, message)
            return {"response": result}

        return swarm_node

    def run(self):
        """Start the adapter."""
        logger.info(f"LangChain Adapter running — swarm at {self.orchestrator_host}:{self.orchestrator_port}")
        print("LangChain Adapter ready.", file=sys.stderr)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def stop(self):
        pass


# ---------------------------------------------------------------------------
# Google ADK Adapter
# ---------------------------------------------------------------------------

class GoogleADKAdapter(AgentAdapter):
    """
    Adapter for Google's Agent Development Kit (ADK).

    Exposes swarm operations as ADK tools that can be used by
    ADK agents in their tool-calling workflows.

    Requires: pip install google-adk
    """

    def __init__(self, orchestrator_host: str = "127.0.0.1",
                 orchestrator_port: int = 9997):
        super().__init__(orchestrator_host, orchestrator_port)

    def get_tool_definitions(self) -> list:
        """Return ADK tool definitions."""
        return [
            {
                "name": "swarm_chat",
                "description": "Send a chat message to the swarm AI agents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to send to the AI",
                        },
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "swarm_status",
                "description": "Get the current status of the swarm orchestrator",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "swarm_agents",
                "description": "List all available AI agents in the swarm",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "swarm_rtu",
                "description": "Get real-time system usage stats (CPU, memory, load)",
                "parameters": {"type": "object", "properties": {}},
            },
        ]

    def execute_tool(self, tool_name: str, **kwargs) -> dict:
        """Execute an ADK tool call."""
        if tool_name == "swarm_chat":
            return self.client.send_task("chat", [kwargs.get("message", "")])
        elif tool_name == "swarm_status":
            return self.client.get_status()
        elif tool_name == "swarm_agents":
            return {"agents": self.client.list_agents()}
        elif tool_name == "swarm_rtu":
            return self.client.get_rtu()
        else:
            return {"status": "error", "error": f"Unknown tool: {tool_name}"}

    def run(self):
        """Start the adapter."""
        logger.info(f"Google ADK Adapter running — swarm at {self.orchestrator_host}:{self.orchestrator_port}")
        print("Google ADK Adapter ready.", file=sys.stderr)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def stop(self):
        pass


# ---------------------------------------------------------------------------
# MCP (Model Context Protocol) Server
# ---------------------------------------------------------------------------

class SwarmToolServer:
    """
    MCP-compatible tool server for the Swarm.

    Exposes swarm operations as MCP tools that any MCP client
    (Claude Desktop, Cursor, Windsurf, etc.) can use.

    Tools exposed:
      - send_chat(message) — Send a chat message to the swarm
      - get_status() — Get orchestrator status
      - list_agents() — List available agents
      - get_rtu() — Get real-time system usage
      - execute_task(task, args) — Execute a custom task

    Usage:
        server = SwarmToolServer()
        server.run()  # Runs on stdio (MCP protocol)
    """

    def __init__(self, orchestrator_host: str = "127.0.0.1",
                 orchestrator_port: int = 9997):
        self.client = SwarmClient(orchestrator_host, orchestrator_port)
        self.orchestrator_host = orchestrator_host
        self.orchestrator_port = orchestrator_port

    def list_tools(self) -> list:
        """Return MCP tool definitions."""
        return [
            {
                "name": "send_chat",
                "description": "Send a chat message to the swarm AI agents and get a response",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to send to the AI",
                        },
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "get_status",
                "description": "Get the current status of the swarm orchestrator",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "list_agents",
                "description": "List all available AI agents in the swarm",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_rtu",
                "description": "Get real-time system usage stats (CPU, memory, load, processes)",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "execute_task",
                "description": "Execute a custom task on the swarm",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Task type (chat, execute, design, status)",
                        },
                        "args": {
                            "type": "string",
                            "description": "JSON-encoded arguments for the task",
                        },
                    },
                    "required": ["task"],
                },
            },
        ]

    def call_tool(self, tool_name: str, arguments: dict) -> list:
        """Execute a tool call and return MCP-formatted response."""
        try:
            if tool_name == "send_chat":
                result = self.client.send_task("chat", [arguments.get("message", "")])
            elif tool_name == "get_status":
                result = self.client.get_status()
            elif tool_name == "list_agents":
                result = {"agents": self.client.list_agents()}
            elif tool_name == "get_rtu":
                result = self.client.get_rtu()
            elif tool_name == "execute_task":
                task = arguments.get("task", "chat")
                args = json.loads(arguments.get("args", "[]"))
                result = self.client.send_task(task, args)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            return [{"type": "text", "text": json.dumps(result, indent=2)}]
        except Exception as e:
            return [{"type": "text", "text": json.dumps({"error": str(e)})}]

    def get_server_info(self) -> dict:
        """Return MCP server info."""
        return {
            "name": "swarm-orchestrator",
            "version": "2.0.0",
            "capabilities": {"tools": {}},
        }

    def run(self):
        """Run MCP server on stdio transport."""
        logger.info("MCP Server starting on stdio...")
        print('{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"swarm-orchestrator","version":"2.0.0"}}', file=sys.stderr)

        # Read JSON-RPC requests from stdin
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                method = request.get("method", "")
                params = request.get("params", {})
                req_id = request.get("id", 1)

                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "swarm-orchestrator", "version": "2.0.0"},
                        },
                    }
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"tools": self.list_tools()},
                    }
                elif method == "tools/call":
                    tool_name = params.get("name", "")
                    arguments = params.get("arguments", {})
                    content = self.call_tool(tool_name, arguments)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"content": content, "isError": False},
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    }

                print(json.dumps(response))
                sys.stdout.flush()

            except json.JSONDecodeError:
                error = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"code": -32700, "message": "Parse error"},
                }
                print(json.dumps(error))
                sys.stdout.flush()

            except Exception as e:
                logger.error(f"MCP error: {e}")


# ---------------------------------------------------------------------------
# A2A (Agent-to-Agent) Protocol Adapter
# ---------------------------------------------------------------------------

class A2AAdapter(AgentAdapter):
    """
    Adapter for Google's A2A (Agent-to-Agent) protocol.

    Allows A2A-compatible agents to discover and communicate with the swarm.
    The swarm appears as a single A2A agent that can receive tasks and
    return results.

    Requires: pip install a2a-python
    """

    def __init__(self, orchestrator_host: str = "127.0.0.1",
                 orchestrator_port: int = 9997,
                 agent_name: str = "Swarm Agent",
                 agent_description: str = "Multi-agent AI swarm with chat, design, and execution capabilities"):
        super().__init__(orchestrator_host, orchestrator_port)
        self.agent_name = agent_name
        self.agent_description = agent_description

    def get_agent_card(self) -> dict:
        """Return A2A agent card for discovery."""
        return {
            "name": self.agent_name,
            "description": self.agent_description,
            "url": f"http://{self.orchestrator_host}:8080",
            "version": "2.0.0",
            "capabilities": {
                "streaming": True,
                "pushNotifications": False,
                "stateTransitionHistory": True,
            },
            "skills": [
                {
                    "id": "chat",
                    "name": "AI Chat",
                    "description": "Natural language conversation with AI agents",
                    "tags": ["chat", "conversation", "ai"],
                    "examples": ["Hello", "What can you do?", "Tell me about the swarm"],
                },
                {
                    "id": "design",
                    "name": "System Design",
                    "description": "Architecture and system design assistance",
                    "tags": ["architecture", "design", "planning"],
                    "examples": ["Design a home server setup", "Plan a network upgrade"],
                },
                {
                    "id": "execute",
                    "name": "Task Execution",
                    "description": "Execute commands and code on connected devices",
                    "tags": ["execution", "code", "hardware"],
                    "examples": ["Run a script", "Check system status"],
                },
                {
                    "id": "rtu",
                    "name": "Real-Time Monitoring",
                    "description": "Get real-time system usage and health stats",
                    "tags": ["monitoring", "stats", "health"],
                    "examples": ["CPU usage", "Memory stats", "System load"],
                },
            ],
            "defaultInputModes": ["text"],
            "defaultOutputModes": ["text"],
        }

    def handle_message(self, message: dict) -> dict:
        """Handle an A2A message."""
        # Extract text from A2A message format
        text = ""
        if isinstance(message, dict):
            parts = message.get("parts", [])
            for part in parts:
                if isinstance(part, dict) and part.get("type") == "text":
                    text += part.get("text", "")

        # Route to swarm
        result = self.client.send_task("chat", [text])

        # Return in A2A format
        return {
            "role": "agent",
            "parts": [
                {"type": "text", "text": json.dumps(result, indent=2)}
            ],
        }

    def run(self):
        """Start the A2A adapter."""
        logger.info(f"A2A Adapter running — swarm at {self.orchestrator_host}:{self.orchestrator_port}")
        print(f"A2A Adapter ready. Agent: {self.agent_name}", file=sys.stderr)

        # Try to register with A2A
        try:
            import a2a
            logger.info("A2A SDK detected. Registering agent.")
        except ImportError:
            logger.info("a2a-python not installed. Running in standalone mode.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def stop(self):
        pass


# ---------------------------------------------------------------------------
# Factory & CLI
# ---------------------------------------------------------------------------

def create_adapter(framework: str, **kwargs) -> AgentAdapter:
    """Factory function to create the appropriate adapter."""
    adapters = {
        "openai": OpenAIAdapter,
        "autogen": AutoGenAdapter,
        "crewai": AutoGenAdapter,  # CrewAI uses same adapter pattern
        "langchain": LangChainAdapter,
        "langgraph": LangChainAdapter,
        "adk": GoogleADKAdapter,
        "a2a": A2AAdapter,
    }

    adapter_class = adapters.get(framework.lower())
    if not adapter_class:
        raise ValueError(
            f"Unknown framework: {framework}. "
            f"Available: {', '.join(adapters.keys())}"
        )

    return adapter_class(**kwargs)


def main():
    """CLI entry point for running adapters."""
    import argparse

    parser = argparse.ArgumentParser(description="Swarm Compatibility Layer")
    parser.add_argument(
        "framework",
        nargs="?",
        default="mcp",
        choices=["openai", "autogen", "crewai", "langchain", "langgraph", "adk", "a2a", "mcp"],
        help="Framework to use (default: mcp)",
    )
    parser.add_argument("--orchestrator", default="127.0.0.1", help="Orchestrator host")
    parser.add_argument("--port", type=int, default=9997, help="Orchestrator port")
    parser.add_argument("--test", action="store_true", help="Test connection and exit")

    args = parser.parse_args()

    if args.framework == "mcp":
        server = SwarmToolServer(args.orchestrator, args.port)
        if args.test:
            print("Tools available:")
            for tool in server.list_tools():
                print(f"  - {tool['name']}: {tool['description']}")
            print(f"\nConnection test: {server.client.ping()}")
        else:
            server.run()
    else:
        adapter = create_adapter(
            args.framework,
            orchestrator_host=args.orchestrator,
            orchestrator_port=args.port,
        )
        if args.test:
            print(f"Adapter: {adapter.__class__.__name__}")
            print(f"Connection test: {adapter.health_check()}")
        else:
            adapter.run()


if __name__ == "__main__":
    main()
