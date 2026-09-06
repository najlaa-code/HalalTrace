# Hardware test rig

The ESP32 stays cabled to your laptop over USB (needed for power anyway) and
just prints sensor readings over serial. A small Python script on the laptop
reads that serial output and drives one CIP cycle against the local backend:

```
ESP32 --USB serial--> serial_to_backend.py --localhost HTTP--> backend
```

No WiFi anywhere in this path — nothing to join, no campus network, no IP
mismatches to debug mid-demo.

## Wiring

- DS18B20 DATA -> GPIO 4 (with a 4.7k pull-up to 3.3V, per the DS18B20 datasheet)
- Turbidity sensor AOUT -> GPIO 32

## 1. Flash the sketch

Open `esp32_cip_sensor/esp32_cip_sensor.ino` in the Arduino IDE and flash it.
Board: an ESP32 dev board (e.g. "ESP32 Dev Module"). Libraries needed
(Library Manager): `OneWire`, `DallasTemperature`.

It just prints one line per second like:

```
DATA,23.44,1187
```

(temperature in °C, raw turbidity ADC value). You can sanity-check this in
the Arduino IDE's own Serial Monitor at 115200 baud before moving to the
bridge script — close the Serial Monitor afterward, since only one program
can hold the serial port at a time.

## 2. Find the COM port and install the bridge's one dependency

```bash
python3 -m pip install -r hardware/requirements.txt
```

```bash
python3 hardware/bridge/serial_to_backend.py --list-ports
```

Note the `COMx` port the ESP32 shows up as (also visible in Arduino IDE's
Tools > Port menu, or Windows Device Manager under "Ports (COM & LPT)").

## 3. Start the backend (plain localhost, no `--host 0.0.0.0` needed here)

```bash
python3 -m uvicorn backend.main:app --reload
```

If `results/cip_model.pkl` and friends aren't ready to test against yet, run
with the stub instead so cycle/end doesn't 503:

```bash
$env:HALALTRACE_USE_ML_STUB = "true"
python3 -m uvicorn backend.main:app --reload
```

## 4. Run the bridge

```bash
python3 hardware/bridge/serial_to_backend.py --port COM5
```

It starts a cycle, streams one reading per second, and prints each POST's
response. Press **Ctrl+C** whenever you want to end the cycle (e.g. once
you've seen enough for the demo) — it ends the cycle cleanly and prints the
PASS/FAIL verdict. It also auto-ends after `--max-seconds` (default 120) as a
safety net if you forget.

Verify from another terminal:

```bash
curl http://127.0.0.1:8000/api/audit-log
```

The new cycle (id starts with `hw-`) should be the newest entry.

## Known placeholder

`turbidity_ntu` is currently the raw ADC value converted to volts, not a real
NTU reading — there's no calibration curve for the specific turbidity sensor
module yet. Good enough to prove the wiring and data path end to end; swap in
a real raw->NTU conversion (in `serial_to_backend.py`) once the sensor is
calibrated against known NTU standards.

Note: the frontend dashboard currently runs entirely on `mockBackend.js`
(see [frontend/src/App.jsx](../frontend/src/App.jsx)) — it is not yet wired
to the backend's `/ws/dashboard` WebSocket, so cycles sent from hardware
won't appear there yet. They will show up in `/api/audit-log` and
`/api/cycle/{cycle_id}` on the backend in the meantime.
