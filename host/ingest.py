#!/usr/bin/env python3
"""Read TinyOS PrintfClient lines and store TelosB measurements in MongoDB."""

from __future__ import print_function

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone


MEASUREMENT = re.compile(
    r"^parent=(\d+) src=(\d+) count=(\d+) humidity=(\d+) "
    r"temperature=(\d+) photo=(\d+) solar=(\d+)$"
)
INVALID_READING = 0xFFFF


def sht11_values(temperature_raw, humidity_raw):
    """Convert SHT11 raw values at the TelosB nominal 3 V supply.

    Sensirion SHT1x datasheet, section 4, 14-bit temperature and 12-bit RH.
    The converted values are estimates because the actual supply voltage is
    not measured by this application.
    """
    if temperature_raw == INVALID_READING or humidity_raw == INVALID_READING:
        return None, None

    temperature_c = -39.6 + 0.01 * temperature_raw
    rh_linear = (
        -2.0468 + 0.0367 * humidity_raw
        - 1.5955e-6 * humidity_raw * humidity_raw
    )
    rh_compensated = rh_linear + (temperature_c - 25.0) * (
        0.01 + 0.00008 * humidity_raw
    )
    humidity_pct = max(0.0, min(100.0, rh_compensated))
    return round(temperature_c, 2), round(humidity_pct, 2)


def parse_measurement(line, received_at=None):
    match = MEASUREMENT.fullmatch(line.strip())
    if match is None:
        return None

    parent_id, source_id, count, humidity, temperature, photo, solar = (
        int(value) for value in match.groups()
    )
    temperature_c, humidity_pct = sht11_values(temperature, humidity)

    if received_at is None:
        received_at = datetime.now(timezone.utc)

    return {
        "timestamp": received_at,
        "parent_id": parent_id,
        "source_id": source_id,
        "count": count,
        "temperature_raw": temperature,
        "humidity_raw": humidity,
        "photo_raw": None if photo == INVALID_READING else photo,
        "solar_raw": None if solar == INVALID_READING else solar,
        "temperature_c": temperature_c,
        "humidity_pct": humidity_pct,
        "raw_line": line.strip(),
    }


def journal_record(document):
    result = dict(document)
    result["timestamp"] = document["timestamp"].isoformat()
    return json.dumps(result, sort_keys=True)


def recover_journal(collection, journal_path):
    """Replay journaled measurements that were not inserted before a stop."""
    if not os.path.exists(journal_path):
        return 0

    recovered = 0
    with open(journal_path, "r") as journal:
        for line in journal:
            try:
                document = json.loads(line)
                date_text = document["timestamp"].split("+")[0].rstrip("Z")
                format_text = "%Y-%m-%dT%H:%M:%S.%f" if "." in date_text else "%Y-%m-%dT%H:%M:%S"
                document["timestamp"] = datetime.strptime(
                    date_text, format_text
                ).replace(tzinfo=timezone.utc)
                selector = {
                    "timestamp": document["timestamp"],
                    "source_id": document["source_id"],
                }
            except (ValueError, KeyError, TypeError) as error:
                print("Skipping invalid journal line: {}".format(error), file=sys.stderr)
                continue

            result = collection.update_one(
                selector, {"$setOnInsert": document}, upsert=True
            )
            if result.upserted_id is not None:
                recovered += 1
    return recovered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="serial@/dev/ttyUSB0:telosb")
    parser.add_argument("--mongo-uri", default="mongodb://127.0.0.1:27017/")
    parser.add_argument("--db", default="iot_wsn")
    parser.add_argument("--collection", default="measurements")
    parser.add_argument("--journal", default="measurements.jsonl")
    args = parser.parse_args()

    from pymongo import ASCENDING, MongoClient

    client = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    collection = client[args.db][args.collection]
    collection.create_index([("source_id", ASCENDING), ("timestamp", ASCENDING)])

    journal_path = os.path.abspath(args.journal)
    if not os.path.isdir(os.path.dirname(journal_path)):
        os.makedirs(os.path.dirname(journal_path))

    recovered = recover_journal(collection, journal_path)
    print("Recovered {} journal measurements into MongoDB".format(
        recovered
    ), file=sys.stderr)

    command = [
        "java", "net.tinyos.tools.PrintfClient", "-comm", args.serial
    ]
    print("Reading {} into {}.{}; journal {}".format(
        args.serial, args.db, args.collection, journal_path
    ), file=sys.stderr)

    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True, bufsize=1
    )
    try:
        with open(journal_path, "a", buffering=1) as journal:
            for line in process.stdout:
                document = parse_measurement(line)
                if document is None:
                    print(line.rstrip(), file=sys.stderr)
                    continue

                journal.write(journal_record(document) + "\n")
                journal.flush()
                os.fsync(journal.fileno())

                try:
                    collection.insert_one(dict(document))
                except Exception as error:
                    print("MongoDB insert failed; measurement is in journal: {}".format(
                        error
                    ), file=sys.stderr)
                    continue

                print(journal_record(document), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        process.terminate()
        process.wait()
        client.close()


if __name__ == "__main__":
    main()
