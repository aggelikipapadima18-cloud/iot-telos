import unittest
import os
import tempfile
from datetime import datetime, timezone

from ingest import journal_record, parse_measurement, recover_journal, sht11_values


class IngestTest(unittest.TestCase):
    def test_real_telosb_line(self):
        received_at = datetime(2026, 9, 29, 16, 0, tzinfo=timezone.utc)
        document = parse_measurement(
            "parent=0 src=1 count=0 humidity=1006 temperature=6901 photo=8 solar=4",
            received_at,
        )
        self.assertEqual(document["source_id"], 1)
        self.assertEqual(document["count"], 0)
        self.assertEqual(document["timestamp"], received_at)
        self.assertEqual(document["temperature_c"], 29.41)
        self.assertGreater(document["humidity_pct"], 30)
        self.assertLess(document["humidity_pct"], 40)

    def test_bad_or_incomplete_lines_are_ignored(self):
        self.assertIsNone(parse_measurement("serial resynchronising"))
        self.assertIsNone(parse_measurement("parent=0 src=1 invalid_len=2"))
        self.assertIsNone(parse_measurement("parent=0 src=1 count=1 humidity=2"))

    def test_failed_sensor_reading_is_not_converted(self):
        self.assertEqual(sht11_values(65535, 1000), (None, None))
        self.assertEqual(sht11_values(7000, 65535), (None, None))

    def test_journal_recovery_is_idempotent(self):
        class MemoryCollection:
            def __init__(self):
                self.documents = {}

            def update_one(self, selector, update, upsert):
                key = (selector["source_id"], selector["timestamp"])
                inserted = key not in self.documents
                if inserted:
                    self.documents[key] = update["$setOnInsert"]
                return type("Result", (), {"upserted_id": 1 if inserted else None})()

        document = parse_measurement(
            "parent=0 src=2 count=4 humidity=900 temperature=7000 photo=8 solar=7",
            datetime(2026, 9, 29, 16, 0, tzinfo=timezone.utc),
        )
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as journal:
            journal.write(journal_record(document) + "\n")
            path = journal.name
        try:
            collection = MemoryCollection()
            self.assertEqual(recover_journal(collection, path), 1)
            self.assertEqual(recover_journal(collection, path), 0)
            self.assertEqual(len(collection.documents), 1)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
