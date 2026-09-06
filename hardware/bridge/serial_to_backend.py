"""Reads DATA lines from the ESP32 over USB serial and drives one CIP cycle
against the local HalalTrace backend (cycle/start -> reading -> cycle/end).

No WiFi involved: the ESP32 stays cabled to this machine over USB, and this
script talks to the backend over localhost.

Usage:
    python serial_to_backend.py --port COM5
    python serial_to_backend.py --list-ports

Press Ctrl+C at any time to end the cycle early and see the verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

import serial
import serial.tools.list_ports


def list_ports() -> None:
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return
    for p in ports:
        print(f"{p.device}  -  {p.description}")


def post_json(url: str, payload: dict) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Serial port, e.g. COM5")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--host", default="127.0.0.1", help="Backend host")
    parser.add_argument("--backend-port", type=int, default=8000, help="Backend port")
    parser.add_argument("--line-id", default="line_A")
    parser.add_argument(
        "--max-seconds",
        type=int,
        default=120,
        help="Safety cap: end the cycle automatically after this many readings.",
    )
    parser.add_argument("--list-ports", action="store_true")
    args = parser.parse_args()

    if args.list_ports:
        list_ports()
        return 0

    if not args.port:
        print("No --port given. Available ports:")
        list_ports()
        print("\nRe-run with --port <name>, e.g. --port COM5")
        return 1

    base_url = f"http://{args.host}:{args.backend_port}"
    cycle_id = "hw-" + time.strftime("%Y%m%dT%H%M%S")

    print(f"Opening {args.port} at {args.baud} baud...")
    ser = serial.Serial(args.port, args.baud, timeout=1)
    time.sleep(2)  # let the ESP32 finish its post-reset boot chatter
    ser.reset_input_buffer()

    print(f"Starting cycle {cycle_id!r} on {args.line_id!r}...")
    status, body = post_json(
        f"{base_url}/api/line/{args.line_id}/cycle/start", {"cycle_id": cycle_id}
    )
    print(f"cycle/start -> {status} {body}")
    if status != 201:
        print("Cycle did not start. Is the backend running? Aborting.")
        return 1

    start_time = time.monotonic()
    readings_sent = 0
    try:
        while readings_sent < args.max_seconds:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line.startswith("DATA,"):
                if line:
                    print(f"(serial) {line}")
                continue

            _, temp_str, turbidity_raw_str = line.split(",")
            temp_c = float(temp_str)
            turbidity_raw = int(turbidity_raw_str)
            # Placeholder conversion: raw ADC -> volts, NOT a calibrated NTU
            # value yet. Swap in a real raw->NTU curve once the sensor is
            # calibrated.
            turbidity_ntu = turbidity_raw * (3.3 / 4095.0)
            t_sec = time.monotonic() - start_time

            status, body = post_json(
                f"{base_url}/api/line/{args.line_id}/reading",
                {
                    "cycle_id": cycle_id,
                    "t_sec": round(t_sec, 2),
                    "turbidity_ntu": round(turbidity_ntu, 3),
                    "temp_c": temp_c,
                },
            )
            readings_sent += 1
            print(
                f"[{readings_sent}] t={t_sec:.1f}s temp={temp_c:.2f}C "
                f"turbidity_raw={turbidity_raw} -> reading POST {status}"
            )
    except KeyboardInterrupt:
        print("\nInterrupted, ending cycle now...")
    finally:
        ser.close()

    print("Ending cycle...")
    status, body = post_json(
        f"{base_url}/api/line/{args.line_id}/cycle/end", {"cycle_id": cycle_id}
    )
    print(f"cycle/end -> {status} {body}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
