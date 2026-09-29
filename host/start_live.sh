#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
serial="${1:-serial@/dev/ttyUSB0:telosb}"
if [ "$#" -gt 0 ]; then shift; fi

# RoleStart sends the serial command to the USB-attached mote. The remaining
# motes discover it through radio beacons and begin sampling automatically.
(cd "$here/../examples/Sensing/AutoStar" && java RoleStart "$serial")
exec python3 "$here/ingest.py" --serial "$serial" "$@"
