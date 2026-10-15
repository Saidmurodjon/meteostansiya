"""Optional: fan one DL1 TCP stream out to several bridges.

A DL1 can only report to a single IP:port, so to run v1 (ThingsBoard) and
v2 (Grafana + VictoriaMetrics) side by side this relay accepts the DL1
connection and copies every byte to each target bridge. Neither version
depends on it - point the DL1 straight at one bridge to run that one alone.

A target that is down is skipped (and retried on the next chunk), so one
stack being stopped never blocks the other. Targets see the tee's address,
not the DL1's - bridges must not rely on source IP.

Usage: python3 dl1_tee.py --listen 8888 --to 127.0.0.1:8801 --to 127.0.0.1:8802
"""
import argparse
import datetime
import select
import socket
import threading

LOGFILE = "/tmp/dl1_tee.log"


def log(msg: str):
    line = f"[{datetime.datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", buffering=1) as f:
            f.write(line + "\n")
    except Exception:
        pass


class Target:
    def __init__(self, host: str, port: int):
        self.addr = (host, port)
        self.sock = None

    def _peer_closed(self) -> bool:
        # Bridges never write back, so readable-with-EOF means the target went
        # away. Needed because Docker's port proxy keeps accepting writes after
        # the container behind it restarts, so sendall() alone never fails.
        r, _, _ = select.select([self.sock], [], [], 0)
        if not r:
            return False
        try:
            return self.sock.recv(1, socket.MSG_PEEK) == b""
        except OSError:
            return True

    def send(self, data: bytes):
        if self.sock is not None and self._peer_closed():
            log(f"target {self.addr[0]}:{self.addr[1]} closed by peer, reconnecting")
            self.close()
        for attempt in (1, 2):
            if self.sock is None:
                try:
                    self.sock = socket.create_connection(self.addr, timeout=3)
                    log(f"target {self.addr[0]}:{self.addr[1]} connected")
                except OSError as e:
                    log(f"target {self.addr[0]}:{self.addr[1]} unavailable: {e}")
                    return
            try:
                self.sock.sendall(data)
                return
            except OSError as e:
                log(f"target {self.addr[0]}:{self.addr[1]} send failed ({e}), reconnecting")
                self.close()

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None


def handle_conn(conn: socket.socket, addr, targets):
    log(f"{addr[0]}: connection opened")
    outs = [Target(h, p) for h, p in targets]
    conn.settimeout(600)
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            for t in outs:
                t.send(chunk)
    except socket.timeout:
        log(f"{addr[0]}: idle timeout, closing connection")
    except OSError as e:
        log(f"{addr[0]}: connection error: {e}")
    finally:
        conn.close()
        for t in outs:
            t.close()
        log(f"{addr[0]}: connection closed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", type=int, default=8888)
    ap.add_argument("--to", action="append", required=True, help="host:port, repeatable")
    args = ap.parse_args()
    targets = [(t.rsplit(":", 1)[0], int(t.rsplit(":", 1)[1])) for t in args.to]

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", args.listen))
    srv.listen(20)
    log(f"DL1 tee listening on 0.0.0.0:{args.listen} -> {', '.join(args.to)}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_conn, args=(conn, addr, targets), daemon=True).start()


if __name__ == "__main__":
    main()
