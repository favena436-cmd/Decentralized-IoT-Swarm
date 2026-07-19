import argparse
import json
import socket
import threading
import time

import requests

try:
    import paho.mqtt.client as mqtt

    MQTT_AVAILABLE = True
except ImportError:
    mqtt = None
    MQTT_AVAILABLE = False
    print("[!] paho-mqtt not installed. Please run: pip install paho-mqtt")


class GenericAgent:
    """Minimal agent base class that supports optional add-ons."""

    def __init__(self, name="generic-agent"):
        self.name = name
        self.addons = []
        self.status = "idle"
        self.logger = None

    def register_addon(self, addon):
        self.addons.append(addon)
        addon.attach(self)
        return addon

    def remove_addon(self, addon):
        if addon in self.addons:
            self.addons.remove(addon)
            return True
        return False

    def log(self, message):
        if self.logger is not None:
            self.logger(message)
        print(message)

    def handle_message(self, topic, payload):
        for addon in self.addons:
            if addon.handle_message(self, topic, payload):
                return True
        return False

    def start(self):
        self.status = "running"
        for addon in self.addons:
            addon.on_start(self)

    def stop(self):
        self.status = "stopped"
        for addon in self.addons:
            addon.on_stop(self)


class SwarmAddon:
    """Optional add-on that provides swarm-specific routing and translation."""

    def __init__(self):
        self.agent = None
        self.legacy_devices = {
            "s24_node": {"protocol": "tcp", "ip": "127.0.0.1", "port": 9997},
            "esp32_microcontroller": {"protocol": "udp", "ip": "192.168.1.50", "port": 8888},
            "react_dashboard": {"protocol": "websocket", "url": "ws://127.0.0.1:3000/swarm"},
            "legacy_web_api": {
                "protocol": "http",
                "url": "http://192.168.1.100/api/v1/command",
                "payload_type": "xml",
            },
        }

    def attach(self, agent):
        self.agent = agent

    def on_start(self, agent):
        print(f"[Addon] Swarm addon ready for {agent.name}")

    def on_stop(self, agent):
        print(f"[Addon] Swarm addon stopped for {agent.name}")

    def handle_message(self, agent, topic, payload):
        if not isinstance(topic, str) or not topic.startswith("swarm/routes/"):
            return False

        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return False

        if not isinstance(payload, dict):
            return False

        target = payload.get("target_id")
        if target not in self.legacy_devices:
            print(f"[Translator Agent] Target '{target}' not found in translation matrix, but the swarm topic was accepted.")
            return True

        device_info = self.legacy_devices[target]
        protocol = device_info["protocol"]

        if protocol == "tcp":
            self.translate_to_tcp(target, device_info["ip"], device_info["port"], payload)
        elif protocol == "udp":
            self.translate_to_udp(target, device_info["ip"], device_info["port"], payload)
        elif protocol == "http":
            self.translate_to_http(target, device_info["url"], payload, device_info.get("payload_type", "json"))
        elif protocol == "websocket":
            self.translate_to_websocket(target, device_info["url"], payload)
        else:
            print(f"[Translator Agent] Unsupported protocol '{protocol}' for target '{target}'.")

        return True

    def translate_to_tcp(self, target_name, ip, port, json_data):
        """Translate an MQTT JSON payload into a raw TCP socket payload."""
        print(f"  -> [Translating] Routing MQTT -> TCP Socket for {target_name} ({ip}:{port})")
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((ip, port))

            raw_payload = json.dumps(json_data) + "\n"
            sock.sendall(raw_payload.encode("utf-8"))

            buffer = ""
            while True:
                data = sock.recv(4096)
                if not data:
                    break

                buffer += data.decode("utf-8", errors="ignore")
                if "\n" in buffer:
                    line, _ = buffer.split("\n", 1)
                    print(f"  <- [Translated Response] Received raw TCP from {target_name}")

                    response_topic = f"swarm/responses/{json_data.get('id', 'unknown')}"
                    client = getattr(self.agent, "client", None)
                    if client is not None:
                        client.publish(response_topic, line)
                        print(f"  -> [Translating] TCP Response -> MQTT Topic: {response_topic}")
                    break
        except Exception as exc:
            print(f"  [!] TCP Translation failed for {target_name}: {exc}")
        finally:
            if sock is not None:
                sock.close()

    def translate_to_udp(self, target_name, ip, port, json_data):
        """Translate MQTT JSON into a raw UDP datagram for microcontrollers."""
        print(f"  -> [Translating] Routing MQTT -> UDP Datagram for {target_name} ({ip}:{port})")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            raw_payload = json.dumps(json_data).encode("utf-8")
            sock.sendto(raw_payload, (ip, port))
            print("  <- [Translated Response] UDP Fire-and-Forget completed.")
        except Exception as exc:
            print(f"  [!] UDP Translation failed: {exc}")

    def translate_to_http(self, target_name, url, json_data, payload_type="json"):
        """Translate MQTT JSON into an HTTP REST request (JSON or XML)."""
        print(f"  -> [Translating] Routing MQTT -> HTTP REST ({payload_type.upper()}) for {target_name} at {url}")
        try:
            if payload_type == "xml":
                xml_data = (
                    f"<SwarmRequest><target>{target_name}</target>"
                    f"<task>{json_data.get('task', '')}</task></SwarmRequest>"
                )
                headers = {"Content-Type": "application/xml"}
                response = requests.post(url, data=xml_data, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=json_data, timeout=10)

            response.raise_for_status()

            response_topic = f"swarm/responses/{json_data.get('id', 'unknown')}"
            client = getattr(self.agent, "client", None)
            if client is not None:
                client.publish(response_topic, response.text)
                print(f"  -> [Translating] HTTP Response -> MQTT Topic: {response_topic}")
        except Exception as exc:
            print(f"  [!] HTTP REST Translation failed: {exc}")

    def translate_to_websocket(self, target_name, url, json_data):
        """Translate MQTT JSON into a WebSocket-style payload for frontends."""
        print(f"  -> [Translating] Routing MQTT -> WebSocket for {target_name} at {url}")
        print("  <- [Simulated WS] Emitting JSON payload to Frontend Socket...")

        response_topic = f"swarm/responses/{json_data.get('id', 'unknown')}"
        client = getattr(self.agent, "client", None)
        if client is not None:
            client.publish(response_topic, json.dumps({"status": "delivered_to_frontend"}))


class DealTypeAgent(GenericAgent):
    """A deal-type agent that exposes a lightweight contract lifecycle."""

    def __init__(self, name="deal-agent"):
        super().__init__(name=name)
        self.deal = None
        self.allowed_states = ["created", "accepted", "updated", "settled", "failed"]
        self.state = "idle"

    def create_deal(self, deal_id, payload):
        self.deal = {"deal_id": deal_id, "payload": payload, "state": "created"}
        self.state = "created"
        return self.deal

    def advance(self, action, payload=None):
        if self.deal is None:
            raise ValueError("No active deal to advance")

        current_state = self.deal.get("state")
        transitions = {
            "created": {"accept": "accepted", "fail": "failed"},
            "accepted": {"update": "updated", "fail": "failed", "settle": "settled"},
            "updated": {"settle": "settled", "fail": "failed"},
        }

        next_state = transitions.get(current_state, {}).get(action)
        if next_state is None:
            raise ValueError(f"Unsupported transition '{action}' from state '{current_state}'")

        self.deal["state"] = next_state
        self.deal["last_action"] = action
        if payload is not None:
            self.deal["payload"] = payload
        self.state = next_state
        return {**self.deal, "state": next_state}

    def get_deal(self):
        return self.deal


class UniversalTranslatorAgent(GenericAgent):
    """Translator agent with swarm-specific functionality available as an add-on."""

    def __init__(self, mqtt_broker="127.0.0.1", mqtt_port=1883, name="UniversalTranslatorAgent"):
        super().__init__(name=name)
        self.broker = mqtt_broker
        self.port = mqtt_port
        self.client = None

        self.swarm_addon = SwarmAddon()
        self.register_addon(self.swarm_addon)

        if MQTT_AVAILABLE:
            self.client = mqtt.Client(client_id=name)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message

    def start(self):
        if not MQTT_AVAILABLE or self.client is None:
            print("[Translator Agent] MQTT support is unavailable; translator will not start.")
            return

        super().start()
        print(f"[Translator Agent] Connecting to MQTT Broker at {self.broker}:{self.port}...")
        self.client.connect(self.broker, self.port, 60)

        thread = threading.Thread(target=self.client.loop_forever)
        thread.daemon = True
        thread.start()
        print("[Translator Agent] Active and listening for cross-language translation tasks.")

    def on_connect(self, client, userdata, flags, rc):
        self.log("[Translator Agent] Connected to MQTT Swarm Broker. Subscribing to universal routes...")
        client.subscribe("swarm/routes/#")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8")
        self.log(f"[Translator Agent] Received MQTT Message on {msg.topic}")

        try:
            self.handle_message(msg.topic, payload)
        except Exception as exc:
            self.log(f"[Translator Agent] Translation Error: {exc}")


def build_parser():
    parser = argparse.ArgumentParser(description="Run the universal translator agent")
    parser.add_argument("--broker", default="127.0.0.1", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--name", default="UniversalTranslatorAgent", help="Agent name")
    parser.add_argument("--enable-swarm", action="store_true", help="Enable swarm routing add-on")
    parser.add_argument("--disable-swarm", action="store_true", help="Disable swarm routing add-on")
    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    translator = UniversalTranslatorAgent(mqtt_broker=args.broker, mqtt_port=args.port, name=args.name)

    if args.disable_swarm:
        translator.remove_addon(translator.swarm_addon)
    elif not args.enable_swarm:
        translator.remove_addon(translator.swarm_addon)

    translator.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down Universal Translator...")
