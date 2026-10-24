import unittest
from datetime import datetime, timedelta, timezone

from build_radar import GRACE_HOURS, expires_at, featured_event, finishes_at, retained


class FightRetentionTests(unittest.TestCase):
    def setUp(self):
        self.event = {
            "name": "UFC Test Card",
            "sport": "UFC",
            "when_utc": datetime(2026, 10, 24, 14, 0, tzinfo=timezone.utc),
        }

    def test_ufc_card_is_retained_for_exactly_24_hours_after_finish(self):
        finish = finishes_at(self.event)
        self.assertEqual(GRACE_HOURS, 24)
        self.assertEqual(expires_at(self.event), finish + timedelta(hours=24))
        self.assertTrue(retained(self.event, finish + timedelta(hours=23, minutes=59)))
        self.assertTrue(retained(self.event, finish + timedelta(hours=24)))
        self.assertFalse(retained(self.event, finish + timedelta(hours=24, microseconds=1)))

    def test_recently_finished_card_remains_the_featured_card(self):
        later = dict(self.event, name="Next UFC Card",
                     when_utc=self.event["when_utc"] + timedelta(days=7))
        now = finishes_at(self.event) + timedelta(hours=12)
        visible = [event for event in (self.event, later) if retained(event, now)]
        self.assertIs(featured_event(visible), self.event)


if __name__ == "__main__":
    unittest.main()
