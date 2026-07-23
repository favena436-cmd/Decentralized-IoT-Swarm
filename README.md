# Decentralized Autonomous IoT Swarm Node

An enterprise-grade, edge-compute smart home architecture powered by localized AI (Gemma 2B) running natively on mobile hardware (Snapdragon NPUs). Designed for absolute privacy, zero-token cost IoT routing, and infinite scalability.

## 🌟 Core Architecture

1. **Enterprise Smart Router (`enterprise_smart_router.py`)**: 
   Intercepts all voice and text commands. Uses a zero-token local Python heuristic to determine complexity. Simple IoT commands are routed to local hardware; heavy reasoning is conditionally offloaded to the cloud.
2. **Universal Translator / Polyglot Bridge Agent (`universal_translator_agent.py`)**:
   An Enterprise Service Bus (ESB) middleware agent. It listens to modern MQTT topics and dynamically translates payloads into legacy protocols (TCP Sockets, HTTP, UDP).
3. **Android Edge Compute Node (Kotlin)**:
   A native Android application (`S24SwarmNode`) running MediaPipe and Gemma 2B. Configured with a strict "Swarm Edge Coordinator" persona.

## 🚀 Getting Started

### 1. Requirements
* Python 3.10+
* Android Device (Physical preferred for NPU acceleration, or Emulator with KVM enabled)

```bash
pip install -r requirements.txt
```

### 2. Configure Credentials & Environment
Copy the example environment file and add your Google Gemini API key:
```bash
cp .env.example .env
```
Open `.env` and configure:
* `GEMINI_API_KEY`: Required for the Cloud Agent fallback when complex reasoning is needed.
* `MQTT_BROKER_IP`: (Optional) Change if running Mosquitto on a different network node.

### 3. Install Mosquitto Broker Natively
```bash
sudo apt update && sudo apt install -y mosquitto mosquitto-clients
```

### 4. Boot the Swarm
```bash
chmod +x run_swarm.sh
./run_swarm.sh
```

---
## Legacy Swarm Chat Node (Reference)
Manages voice I/O, TTS/STT, conversational state. The user-facing layer of the swarm.

### Quick Start
```bash
./scripts/start.sh
python3 health_check.py
tail -f logs/service.log
```
Edit `config/node.json` to set `orchestrator_host` and `orchestrator_port`.
