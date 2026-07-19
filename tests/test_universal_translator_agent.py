import json
import socket
import threading
import time
import unittest
from unittest.mock import patch

from universal_translator_agent import DealTypeAgent, GenericAgent, SwarmAddon, UniversalTranslatorAgent


class TestUniversalTranslatorAgent(unittest.TestCase):
    def test_generic_agent_accepts_addons(self):
        agent = GenericAgent(name="demo-agent")
        addon = SwarmAddon()

        agent.register_addon(addon)

        self.assertIn(addon, agent.addons)

    def test_swarm_addon_can_handle_swarm_topic(self):
        agent = GenericAgent(name="demo-agent")
        addon = SwarmAddon()
        agent.register_addon(addon)

        handled = agent.handle_message("swarm/routes/demo", {"target_id": "demo_target", "id": "abc"})

        self.assertTrue(handled)

    def test_swarm_addon_selects_tcp_translation_path(self):
        addon = SwarmAddon()
        payload = {"target_id": "s24_node", "id": "abc", "task": "ping"}

        class MockSocket:
            def __init__(self, *args, **kwargs):
                self.connected = False

            def settimeout(self, timeout):
                self.timeout = timeout

            def connect(self, address):
                self.connected = True

            def sendall(self, data):
                self.sent = data

            def recv(self, size):
                return b"pong\n"

            def close(self):
                self.closed = True

        with patch("universal_translator_agent.socket.socket", return_value=MockSocket()):
            handled = addon.handle_message(None, "swarm/routes/demo", payload)

        self.assertTrue(handled)

    def test_swarm_addon_can_build_http_payload(self):
        addon = SwarmAddon()
        payload = {"target_id": "legacy_web_api", "id": "abc", "task": "ping"}
        handled = addon.handle_message(None, "swarm/routes/demo", payload)

        self.assertTrue(handled)

    def test_universal_translator_agent_can_be_instantiated(self):
        translator = UniversalTranslatorAgent(name="demo-translator")
        self.assertEqual(translator.name, "demo-translator")
        self.assertEqual(translator.status, "idle")

    def test_deal_type_agent_creates_a_deal_contract(self):
        agent = DealTypeAgent(name="deal-agent")
        payload = {"customer": "demo", "amount": 100}
        deal = agent.create_deal("deal-001", payload)

        self.assertEqual(deal["deal_id"], "deal-001")
        self.assertEqual(agent.get_deal()["payload"], payload)

    def test_deal_type_agent_supports_lifecycle_transitions(self):
        agent = DealTypeAgent(name="deal-agent")
        agent.create_deal("deal-002", {"customer": "demo"})

        accepted = agent.advance("accept")
        updated = agent.advance("update", {"customer": "demo", "updated": True})
        settled = agent.advance("settle")

        self.assertEqual(accepted["state"], "accepted")
        self.assertEqual(updated["state"], "updated")
        self.assertEqual(settled["state"], "settled")


if __name__ == "__main__":
    unittest.main()
