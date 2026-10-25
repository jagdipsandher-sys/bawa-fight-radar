import json
import unittest
from datetime import datetime, timedelta, timezone

import build_boxing
from send_fights import event_when, load_boxing


class BoxingRadarTests(unittest.TestCase):
    def setUp(self):
        with open("boxing.json") as source:
            self.raw = json.load(source)

    def test_selection_contract_and_sources(self):
        build_boxing.validate(self.raw)
        self.assertTrue(any(item["category"] == "heavyweight" for item in self.raw))
        self.assertTrue(any(item["category"] == "notable" for item in self.raw))
        exhibitions = [item for item in self.raw if item["category"] == "exhibition"]
        self.assertTrue(exhibitions)
        self.assertTrue(all(item["status"] == "date_tbc" for item in exhibitions))
        self.assertTrue(all("date_utc" not in item and "local_date" not in item for item in exhibitions))
        self.assertTrue(all(item["link"].startswith("https://") for item in self.raw))

    def test_confirmed_fight_uses_full_24_hour_grace(self):
        canelo = build_boxing.enrich(next(item for item in self.raw if item["name"].startswith("Canelo")))
        self.assertEqual(canelo["_expires"], canelo["_end"] + timedelta(hours=24))
        during_grace = canelo["_end"] + timedelta(hours=23, minutes=59)
        after_grace = canelo["_end"] + timedelta(hours=24, minutes=1)
        self.assertGreaterEqual(canelo["_expires"], during_grace)
        self.assertLess(canelo["_expires"], after_grace)

    def test_current_launch_set_has_three_separate_lanes(self):
        events = build_boxing.load_events(datetime(2026, 10, 25, tzinfo=timezone.utc))
        counts = {category: len([event for event in events if event["category"] == category])
                  for category in build_boxing.CATEGORY_META}
        self.assertEqual(counts, {"heavyweight": 3, "notable": 2, "exhibition": 1})

    def test_email_does_not_invent_a_time_for_date_only_fight(self):
        events = load_boxing(
            datetime(2026, 11, 17, tzinfo=timezone.utc),
            datetime(2026, 11, 19, tzinfo=timezone.utc),
        )
        teremoana = next(event for event in events if event["name"].startswith("Teremoana"))
        self.assertFalse(teremoana["time_confirmed"])
        self.assertIn("Sydney time TBC", event_when(teremoana))


if __name__ == "__main__":
    unittest.main()
