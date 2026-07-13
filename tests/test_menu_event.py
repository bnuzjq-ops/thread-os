import unittest

from threads_bot_system.menu_event import parse_menu_event


class MenuEventTests(unittest.TestCase):
    def test_parses_nested_feishu_menu_event(self):
        event = parse_menu_event(
            {
                "header": {"event_id": "evt-1"},
                "event": {
                    "action": {"value": "action_send"},
                    "sender": {"sender_id": {"open_id": "ou_1"}},
                },
            }
        )
        self.assertEqual(event.event_key, "action_send")
        self.assertEqual(event.user_open_id, "ou_1")
        self.assertEqual(event.trace_id, "evt-1")

    def test_rejects_unknown_event(self):
        with self.assertRaises(ValueError):
            parse_menu_event({"event_key": "retry", "open_id": "ou_1"})

    def test_parses_official_operator_id_shape(self):
        event = parse_menu_event(
            {
                "header": {"event_id": "evt-2"},
                "event": {
                    "event_key": "system_health",
                    "operator": {"operator_id": {"open_id": "ou_2"}},
                },
            }
        )
        self.assertEqual(event.user_open_id, "ou_2")


if __name__ == "__main__":
    unittest.main()
