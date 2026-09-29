# TelosB star network and data collection

The three TelosB motes run the **same** `AutoStar` firmware, installed with
different node IDs. The mote connected to the computer becomes the parent
when `host/start_live.sh` sends a serial activation message. It broadcasts
beacons every 3 seconds. Other motes discover its ID and send their latest
sensor readings to it every 20 seconds. The parent prints each received
message on one terminal line.

The IRIS XM2110 and MIB520CA are used for the required Blink check. The
TelosB radio network uses the three TelosB boards.

## Build and flash in the Ubuntu TinyOS VM

Keep this repository inside the TinyOS tree, for example at
`~/tinyos-main/iot-implementation`.

```bash
cd ~/tinyos-main/iot-implementation/examples/Sensing/AutoStar
make telosb
make telosb install.0 bsl,/dev/ttyUSB0  # USB parent
make telosb install.1 bsl,/dev/ttyUSB1  # sensor mote
make telosb install.2 bsl,/dev/ttyUSB2  # sensor mote
make -f Makefile.role                 # builds RoleStart Java command
```

The ports shown are from the tested VM. Confirm them after reconnecting USB
devices. To verify IRIS Blink, use the MIB520CA programming port (the lower
of its two `/dev/ttyUSB*` ports):

```bash
cd ~/tinyos-main/apps/Blink
make iris install.3 mib520,/dev/ttyUSB2
```

## Store and view measurements

MongoDB must be running locally in the VM. Install Python 3 PyMongo as
`python3-pymongo` on Ubuntu 16.04. Run this command **once**; it owns the
parent's serial port and stores each parsed line in MongoDB and an append
only JSONL journal:

```bash
cd ~/tinyos-main/iot-implementation
make -C examples/Sensing/AutoStar -f Makefile.role
bash host/start_live.sh serial@/dev/ttyUSB0:telosb \
  --journal "$HOME/measurements.jsonl"
```

On startup the ingester replays journal entries missing from MongoDB. Keep
the same journal path when restarting it.

In a second terminal:

```bash
cd ~/tinyos-main/iot-implementation/host
python3 dashboard.py --bind 0.0.0.0 --port 8765
```

Open `http://127.0.0.1:8765/` inside the VM. When using VirtualBox NAT,
forward host port 8765 to guest port 8765 to open it on Windows. The page
refreshes every 5 seconds and offers 1, 6, 24, and 72 hour history.

For unattended running inside the tested VM, install the provided systemd
units after building `RoleStart.class`:

```bash
sudo cp deployment/iot-ingest.service deployment/iot-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now iot-ingest.service iot-dashboard.service
systemctl status iot-ingest.service iot-dashboard.service
```

These units use the tested `iotlab` account and project path; edit them if
your VM differs. Do not also run `start_live.sh` or `dashboard.py` manually
while the units own their ports. The Windows computer and VM must remain on
for the three day collection period.

## Optional three day simulation

For an immediate demonstration, generate 20-second readings for two motes
over a three day window:

```bash
cd ~/tinyos-main/iot-implementation
python3 host/generate_synthetic.py
python3 host/export_csv.py --collection synthetic_measurements \
  --output analysis/measurements.csv
```

The generator writes to `iot_wsn.synthetic_measurements`; it does not alter
the live `iot_wsn.measurements` collection. Every generated document and CSV
row is labeled `data_origin=synthetic`. Select **Συνθετικές · 3 ημέρες** in
the dashboard to view it. The assignment's actual three day sensor
collection remains a separate requirement.

The repository also includes `analysis/synthetic-3days.csv` so the notebook
can run without access to this VM. If `analysis/measurements.csv` is present,
the notebook uses that file instead.

For analysis, after collecting approximately 3 days:

```bash
cd ~/tinyos-main/iot-implementation
python3 host/export_csv.py --output analysis/measurements.csv
```

Run `analysis/sensor_forecast.ipynb` with Python packages `pandas`, `numpy`,
`matplotlib`, `scikit-learn`, and `statsmodels`. It shows descriptive
statistics, checks missing values, and trains Linear Regression and ARIMA
with a chronological train/test split.

The timestamp is assigned by the receiving computer, in UTC. Temperature
and humidity conversions assume 3 V supply and use the Sensirion SHT1x
datasheet equations
([Sensirion SHT1x datasheet, section 4](https://sensirion.com/en/media/documents/BD45ECB5/61642783/Sensirion_Humidity_Sensors_SHT1x_Datasheet.pdf));
raw readings are kept as well. Radio delivery is best
effort, so the `count` sequence can reveal missing packets. A three day
dataset requires the VM, parent mote, MongoDB, and ingester to remain
running; the current snapshot is shorter.
