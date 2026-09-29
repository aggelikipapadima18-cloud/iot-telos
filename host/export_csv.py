#!/usr/bin/env python3
"""Export received measurements from MongoDB for the analysis notebook."""

import argparse
import csv
from datetime import timezone

from pymongo import MongoClient


FIELDS = (
    "timestamp", "source_id", "parent_id", "count", "temperature_raw",
    "humidity_raw", "temperature_c", "humidity_pct", "photo_raw", "solar_raw",
    "data_origin", "scenario_id",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="measurements.csv")
    parser.add_argument("--mongo-uri", default="mongodb://127.0.0.1:27017/")
    parser.add_argument("--db", default="iot_wsn")
    parser.add_argument("--collection", choices=("measurements", "synthetic_measurements"),
                        default="measurements")
    args = parser.parse_args()

    client = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    cursor = client[args.db][args.collection].find().sort("timestamp", 1)
    count = 0
    with open(args.output, "w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        for document in cursor:
            row = {field: document.get(field) for field in FIELDS}
            row["data_origin"] = document.get("data_origin", "real")
            timestamp = row["timestamp"]
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            row["timestamp"] = timestamp.isoformat()
            writer.writerow(row)
            count += 1
    client.close()
    print("Exported {} measurements to {}".format(count, args.output))


if __name__ == "__main__":
    main()
