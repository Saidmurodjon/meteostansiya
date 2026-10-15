import socket
import struct
import datetime
import json
import urllib.request
import urllib.error
import threading
import os


def _load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")):
    # Secrets live in a gitignored v1-thingsboard/.env (see .env.example), not in the repo.
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()


LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "8888"))
LOGFILE = os.environ.get("LOGFILE", "/tmp/dl1_bridge_v1.log")

TB_HOST = os.environ.get("TB_HOST", "localhost")
TB_PORT = int(os.environ.get("TB_PORT", "9090"))

# Stations arrive over mobile networks / tunnels, so the source IP does not
# identify the DL1 - every connection goes to this one device token until
# per-station identification (DL1 ID inside the frame) is implemented.
DEFAULT_TOKEN = os.environ["TB_DEVICE_TOKEN"]


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
    rainfall_raw = data[37]
    battery_raw = struct.unpack(">H", data[38:40])[0]

    return {
        "device_minute": minute,
        "device_second": second,
        "temperature": round(temp_raw / 10.0, 1),
        "humidity": round(humidity_raw / 10.0, 1),
        "light": light_raw * 10,
        "wind_speed": round(wind_speed_raw / 100.0, 2),
        "wind_direction": wind_dir_raw,
        "rainfall": round(rainfall_raw / 10.0, 1),
        "battery_voltage": round(battery_raw / 100.0, 2),
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
                ok = push_to_thingsboard(DEFAULT_TOKEN, parsed)
                log(f"{ip}: push to ThingsBoard {'OK' if ok else 'FAILED'}")
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
    log(f"[v1] DL1 -> ThingsBoard bridge listening on 0.0.0.0:{LISTEN_PORT}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_conn, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
