import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="Publish a sample swarm message")
    parser.add_argument("--broker", default="127.0.0.1", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    args = parser.parse_args()

    try:
        import paho.mqtt.publish as publish
    except ImportError as exc:
        print("paho-mqtt is required for this example. Install it with: pip install -r requirements.txt")
        raise SystemExit(str(exc)) from exc

    payload = {
        "id": "demo-001",
        "target_id": "s24_node",
        "task": "ping",
        "message": "hello from sample publisher",
    }
    publish.single("swarm/routes/demo", json.dumps(payload), hostname=args.broker, port=args.port)
    print(f"Published sample message to {args.broker}:{args.port} on swarm/routes/demo")


if __name__ == "__main__":
    main()
