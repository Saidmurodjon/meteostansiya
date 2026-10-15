"""v2 bridge: DL1 data logger (TCP, binary frames) -> VictoriaMetrics.

Self-contained on purpose - it shares no code or runtime with v1
(ThingsBoard), so each version can be deployed on its own. The frame
layout is the same one documented in CLAUDE.md ("DL1 protokoli").
"""
import datetime
import os
import socket
import struct
import threading
import urllib.request


def _load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")):
    # Settings live in a gitignored v2-grafana/.env (see .env.example).
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()

LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "8888"))
LOGFILE = os.environ.get("LOGFILE", "/tmp/dl1_bridge_v2.log")
VM_WRITE_URL = os.environ.get("VM_WRITE_URL", "http://localhost:8428/write")

# Stations arrive over mobile networks / tunnels, so the source IP does not
# identify the DL1 - label everything with one station until per-station
# identification (DL1 ID inside the frame) is implemented.
DEFAULT_STATION = os.environ.get("DEFAULT_STATION", "1")


def log(msg: str):
    line = f"[{datetime.datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", buffering=1) as f:
            f.write(line + "\n")
    except Exception:
        pass


def parse_frame(data: bytes):
    if len(data) != 46:
        return None
    if data[0] != 0x40 or data[1] != 0x01:
        return None

    return {
        "temperature": round(struct.unpack(">H", data[17:19])[0] / 10.0, 1),
        "humidity": round(struct.unpack(">H", data[19:21])[0] / 10.0, 1),
        "light": data[22] * 10,
        "wind_speed": round(data[27] / 100.0, 2),
        "wind_direction": struct.unpack(">H", data[31:33])[0],
        "rainfall": round(data[37] / 10.0, 1),
        "battery_voltage": round(struct.unpack(">H", data[38:40])[0] / 100.0, 2),
    }


def push_to_vm(station: str, values: dict) -> bool:
    # InfluxDB line protocol; VictoriaMetrics stores it as meteo_<field>{station="..."}.
    # Server time is used - the DL1's own clock is unreliable (resets to 2018).
    fields = ",".join(f"{k}={float(v)}" for k, v in values.items())
    ts_ns = int(datetime.datetime.now().timestamp() * 1e9)
    body = f"meteo,station={station} {fields} {ts_ns}\n".encode()
    req = urllib.request.Request(VM_WRITE_URL, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        log(f"VictoriaMetrics push failed: {e}")
        return False


def handle_conn(conn: socket.socket, addr):
    ip = addr[0]
    log(f"{ip}: connection opened")
    conn.settimeout(600)
    try:
        buf = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            # Frame length comes from header bytes 2-3 (payload length, +2 for
            # the 40 01 prefix) so frames grow safely when sensors are added.
            while len(buf) >= 4:
                if buf[0] != 0x40 or buf[1] != 0x01:
                    log(f"{ip}: resync, dropping byte {buf[:1].hex()}")
                    buf = buf[1:]
                    continue
                flen = struct.unpack(">H", buf[2:4])[0] + 2
                if len(buf) < flen:
                    break
                frame, buf = buf[:flen], buf[flen:]
                log(f"{ip}: raw ({flen}B): {frame.hex()}")
                parsed = parse_frame(frame)
                if not parsed:
                    log(f"{ip}: unrecognized frame ({len(frame)}B): {frame.hex()}")
                    continue
                log(f"{ip}: decoded {parsed}")
                ok = push_to_vm(DEFAULT_STATION, parsed)
                log(f"{ip}: push to VictoriaMetrics {'OK' if ok else 'FAILED'}")
    except socket.timeout:
        log(f"{ip}: idle timeout, closing connection")
    except Exception as e:
        log(f"{ip}: connection error: {e}")
    finally:
        conn.close()
        log(f"{ip}: connection closed")


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", LISTEN_PORT))
    srv.listen(20)
    log(f"[v2] DL1 -> VictoriaMetrics bridge listening on 0.0.0.0:{LISTEN_PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_conn, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
