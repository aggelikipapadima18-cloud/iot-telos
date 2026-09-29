#!/usr/bin/env python3
"""Insert a clearly labeled three-day simulated TelosB dataset into MongoDB."""

import argparse
import csv
import math
import random
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone

from ingest import sht11_values


SCENARIO = "demo-3days-v2"
SOURCE_IDS = (1, 2)
CSV_FIELDS = (
    "timestamp", "source_id", "parent_id", "count", "temperature_raw",
    "humidity_raw", "temperature_c", "humidity_pct", "photo_raw", "solar_raw",
    "data_origin", "scenario_id",
)


def pulse(position, center, width):
    return math.exp(-0.5 * ((position - center) / width) ** 2)


def humidity_raw_for(target_pct, temperature_raw):
    low, high = 0, 4095
    while low < high:
        middle = (low + high) // 2
        _, measured = sht11_values(temperature_raw, middle)
        if measured < target_pct:
            low = middle + 1
        else:
            high = middle
    return low


def make_document(timestamp, source_id, count, interval, rng, noise):
    elapsed_hours = count * interval / 3600.0
    local_time = timestamp + timedelta(hours=3)
    local_hour = (local_time.hour + local_time.minute / 60.0
                  + local_time.second / 3600.0)
    daylight = max(0.0, math.sin(math.pi * (local_hour - 6.5) / 12.0))
    daily_wave = math.sin(2 * math.pi * (local_hour - 8) / 24.0)
    weather = (1.2 * math.sin(2 * math.pi * elapsed_hours / 49 + 0.2)
               + 0.55 * math.sin(2 * math.pi * elapsed_hours / 67 + 1.1))
    ventilation = pulse(elapsed_hours, 39, 0.8)
    heat_event = pulse(elapsed_hours, 59, 2.2)
    cloud = min(0.7, 0.55 * pulse(elapsed_hours, 15, 1.1)
                + 0.35 * pulse(elapsed_hours, 44, 1.6)
                + 0.50 * pulse(elapsed_hours, 62, 1.0))

    # Correlated noise gives adjacent 20-second readings small natural changes.
    node_noise = noise[source_id]
    node_noise["temperature"] = (0.992 * node_noise["temperature"]
                                 + rng.gauss(0, 0.035))
    node_noise["humidity"] = (0.985 * node_noise["humidity"]
                              + rng.gauss(0, 0.14))
    node_noise["light"] = (0.96 * node_noise["light"]
                           + rng.gauss(0, 1.5))

    temperature_target = (28.5 + 3.2 * daily_wave + weather
                          + 0.35 * source_id + 1.5 * heat_event
                          - 2.2 * ventilation + 0.4 * daylight * (source_id == 1)
                          + node_noise["temperature"])
    humidity_target = (47.5 - 2.2 * (temperature_target - 28.5)
                       + 2.3 * math.sin(2 * math.pi * elapsed_hours / 37 + 1)
                       + 5.0 * ventilation - 1.5 * heat_event
                       - 1.1 * source_id + node_noise["humidity"])
    temperature_raw = int(round((temperature_target + 39.6) * 100))
    humidity_raw = humidity_raw_for(humidity_target, temperature_raw)
    temperature_c, humidity_pct = sht11_values(temperature_raw, humidity_raw)
    shade = 0.75 if source_id == 2 else 1.0
    photo_raw = max(1, int(round(5 + 125 * daylight * (1 - cloud) * shade
                                 + node_noise["light"] + rng.gauss(0, 1.8))))
    solar_raw = max(1, int(round(3 + 155 * daylight * (1 - cloud) * shade
                                 + 1.2 * node_noise["light"]
                                 + rng.gauss(0, 2.0))))
    raw_line = (
        "parent=0 src={} count={} humidity={} temperature={} photo={} solar={}"
        .format(source_id, count, humidity_raw, temperature_raw,
                photo_raw, solar_raw)
    )
    return {
        "_id": "{}-{}-{}".format(SCENARIO, source_id, count),
        "timestamp": timestamp,
        "parent_id": 0,
        "source_id": source_id,
        "count": count,
        "temperature_raw": temperature_raw,
        "humidity_raw": humidity_raw,
        "photo_raw": photo_raw,
        "solar_raw": solar_raw,
        "temperature_c": temperature_c,
        "humidity_pct": humidity_pct,
        "raw_line": raw_line,
        "data_origin": "synthetic",
        "scenario_id": SCENARIO,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo-uri", default="mongodb://127.0.0.1:27017/")
    parser.add_argument("--db", default="iot_wsn")
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--interval", type=int, default=20)
    parser.add_argument("--end", help="fixed UTC end (YYYY-MM-DDTHH:MM:SSZ)")
    parser.add_argument("--csv", help="also write generated records to this CSV")
    parser.add_argument("--no-db", action="store_true", help="write CSV without MongoDB")
    args = parser.parse_args()
    if args.days <= 0 or args.interval <= 0:
        parser.error("days and interval must be positive")
    if args.no_db and not args.csv:
        parser.error("--no-db requires --csv")
    if args.end:
        if not (args.end.endswith("Z") or args.end.endswith("+00:00")):
            parser.error("--end must be in UTC")
        end_text = args.end[:-1] if args.end.endswith("Z") else args.end[:-6]
        try:
            end = datetime.strptime(end_text, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            parser.error("--end must be YYYY-MM-DDTHH:MM:SSZ")
        end = end.replace(tzinfo=timezone.utc)
    else:
        end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(days=args.days)
    steps = args.days * 86400 // args.interval
    rng = random.Random(20260929)
    noise = {source_id: {"temperature": 0.0, "humidity": 0.0, "light": 0.0}
             for source_id in SOURCE_IDS}
    client = None
    try:
        if not args.no_db:
            from pymongo import ASCENDING, MongoClient

            client = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            collection = client[args.db].synthetic_measurements
            collection.create_index([("source_id", ASCENDING),
                                     ("timestamp", ASCENDING)])
            collection.delete_many({"scenario_id": {"$in":
                                   ("demo-3days-v1", SCENARIO)}})

        with ExitStack() as stack:
            writer = None
            if args.csv:
                target = stack.enter_context(open(args.csv, "w", newline="",
                                                  encoding="utf-8"))
                writer = csv.DictWriter(target, fieldnames=CSV_FIELDS)
                writer.writeheader()
            batch = []
            for count in range(steps):
                timestamp = start + timedelta(seconds=count * args.interval)
                for source_id in SOURCE_IDS:
                    document = make_document(timestamp, source_id, count,
                                             args.interval, rng, noise)
                    if writer:
                        row = {field: document[field] for field in CSV_FIELDS}
                        row["timestamp"] = timestamp.isoformat()
                        writer.writerow(row)
                    if client:
                        batch.append(document)
                if client and len(batch) >= 500:
                    collection.insert_many(batch)
                    batch = []
            if client and batch:
                collection.insert_many(batch)
    finally:
        if client:
            client.close()
    print("Generated {} synthetic measurements, {} sources, {} to {} UTC".format(
        steps * len(SOURCE_IDS), len(SOURCE_IDS), start.isoformat(),
        (end - timedelta(seconds=args.interval)).isoformat()
    ))


if __name__ == "__main__":
    main()
