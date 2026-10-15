"""Test-only sidecar: follows the Mac bridge log and copies every decoded
frame into VictoriaMetrics, so Grafana can be compared with ThingsBoard
without restarting dl1_bridge_mac.py (each restart forces a DL1 reconnect).

Usage: python3 log_to_vm.py [--since 2026-10-14T17:41:19]
"""
import ast
import datetime
import re
import sys
import time
import urllib.request

LOGFILE = "/tmp/dl1_bridge_mac.log"
VM_URL = "http://127.0.0.1:8428/write"  # InfluxDB line protocol endpoint
STATION = "1"

LINE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\] \S+: decoded (?P<data>\{.*\})$")


def to_line(ts: datetime.datetime, data: dict) -> str:
    fields = ",".join(
        f"{k}={float(v)}" for k, v in data.items() if not k.startswith("device_")
    )
    ns = int(ts.timestamp() * 1e9)
    return f"meteo,station={STATION} {fields} {ns}"


def push(lines):
    if not lines:
        return
    body = ("\n".join(lines) + "\n").encode()
    urllib.request.urlopen(urllib.request.Request(VM_URL, data=body, method="POST"), timeout=8)


def main():
    since = None
    if "--since" in sys.argv:
        since = datetime.datetime.fromisoformat(sys.argv[sys.argv.index("--since") + 1])
    with open(LOGFILE) as f:
        batch = []
        while True:
            line = f.readline()
            if not line:
                try:
                    push(batch)
                    batch = []
                except Exception as e:
                    print(f"push failed, will retry: {e}", flush=True)
                time.sleep(2)
                continue
            m = LINE_RE.match(line.strip())
            if not m:
                continue
            ts = datetime.datetime.fromisoformat(m["ts"])
            if since and ts < since:
                continue
            batch.append(to_line(ts, ast.literal_eval(m["data"])))


if __name__ == "__main__":
    main()
