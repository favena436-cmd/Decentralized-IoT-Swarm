#!/bin/bash

# Master Startup Script for the Decentralized IoT Swarm Node
echo "==================================================="
echo "🚀 Booting Decentralized IoT Swarm Architecture..."
echo "==================================================="

# 1. Start the MQTT Broker in the background
echo "[1/3] Starting MQTT Coordinator (Mosquitto)..."
if command -v docker &> /dev/null; then
    cd mqtt_broker && docker compose up -d
    cd ..
elif command -v mosquitto &> /dev/null; then
    nohup mosquitto -c mqtt_broker/mosquitto.conf > mosquitto.log 2>&1 &
    echo "      -> Mosquitto running natively in background"
else
    echo "      [!] Neither Docker nor Mosquitto is installed. Please run: sudo apt install -y mosquitto"
    exit 1
fi

# Wait a second to let the broker spin up
sleep 2

# 2. Start the Polyglot Translator Agent in the background
echo "[2/3] Initializing Universal Translator Agent..."
nohup python3 agents/universal_translator_agent.py > translator.log 2>&1 &
echo "      -> Translator Agent running in background (logs in translator.log)"

# 3. Start the Enterprise Smart Router
echo "[3/3] Booting Enterprise Smart Router..."
python3 agents/enterprise_smart_router.py
