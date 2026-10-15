import socket
import struct
import datetime
import json
import urllib.request
import urllib.error
import threading
import os


def _load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
    # Secrets live in a gitignored bridge/.env (see .env.example), not in the repo.
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()


LISTEN_PORT = 8888
LOGFILE = "/data/dl1_bridge.log"

# Runs on the same host as ThingsBoard (host networking), so localhost works
# now that the 9090 -> 9090 port mapping is fixed.
TB_HOST = "localhost"
TB_PORT = 9090

# Map DL1 source IP -> ThingsBoard access token. Add one entry per station.
DEVICE_TOKENS = {
    "192.168.1.50": os.environ["TB_TOKEN_STATION1"],  # Metrostansiya-1 (office test unit)
}


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

    minute = data[10]
    second = data[11]

    temp_raw = struct.unpack(">H", data[17:19])[0]
    humidity_raw = struct.unpack(">H", data[19:21])[0]
    light_raw = data[22]
    wind_speed_raw = data[27]
    wind_dir_raw = struct.unpack(">H", data[31:33])[0]
    # Confirmed 2026-09-07 via a manual tipping-bucket test: single byte at
    # offset 37 (not the 2-byte data[38:40] guess, which is always 0x0000).
    # Scaling assumed to match the temp/humidity convention (raw/10); the
    # value decayed 10 -> 4 -> 0 over ~2 minutes after the manual test rather
    # than accumulating, so it may be a short-term pulse count/intensity
    # rather than a running total mm - re-verify against real rainfall.
    rainfall_raw = data[37]

    return {
        "device_minute": minute,
        "device_second": second,
        "temperature": round(temp_raw / 10.0, 1),
        "humidity": round(humidity_raw / 10.0, 1),
        "light": light_raw * 10,
        "wind_speed": round(wind_speed_raw / 100.0, 2),
        "wind_direction": wind_dir_raw,
        "rainfall": round(rainfall_raw / 10.0, 1),
    }


def push_to_thingsboard(token: str, telemetry: dict) -> bool:
    url = f"http://{TB_HOST}:{TB_PORT}/api/v1/{token}/telemetry"
    body = json.dumps(telemetry).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        log(f"TB push failed: {e}")
        return False


def handle_conn(conn: socket.socket, addr):
    ip = addr[0]
    # DL1 keeps one long-lived connection and can go quiet for a few minutes
    # between reports without actually being dead. A short timeout here made
    # the bridge silently close the connection out from under DL1, which
    # then took a long time to notice and reconnect (2026-09-07 incident).
    conn.settimeout(600)
    try:
        buf = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while len(buf) >= 46:
                frame, buf = buf[:46], buf[46:]
                parsed = parse_frame(frame)
                if not parsed:
                    log(f"{ip}: unrecognized frame ({len(frame)}B): {frame.hex()}")
                    continue
                log(f"{ip}: decoded {parsed}")
                token = DEVICE_TOKENS.get(ip)
                if not token:
                    log(f"{ip}: no ThingsBoard token mapped for this IP, skipping push")
                    continue
                ok = push_to_thingsboard(token, parsed)
                log(f"{ip}: push to ThingsBoard {'OK' if ok else 'FAILED'}")
    except socket.timeout:
        log(f"{ip}: idle timeout, closing connection")
    except Exception as e:
        log(f"{ip}: connection error: {e}")
    finally:
        conn.close()


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", LISTEN_PORT))
    srv.listen(20)
    log(f"DL1 -> ThingsBoard bridge listening on 0.0.0.0:{LISTEN_PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_conn, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
