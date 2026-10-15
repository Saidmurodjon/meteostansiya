# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); dates are in `YYYY-MM-DD`.

## [Unreleased]

### Planned
- Production server (VPS with static IPv4) to replace the temporary Mac + ngrok setup — waiting for owner approval.
- Per-station identification from the DL1 ID inside the frame (mobile source IPs change on every connection).
- Excel (`.xlsx`) export script for v2.
- Inactivity alerts (no data for N minutes → Telegram/email).
- Rotation of credentials that remain in older public commits.

## 2026-10-15

### Added
- **v2 stack — Grafana + VictoriaMetrics** (`v2-grafana/`): its own DL1 → VictoriaMetrics bridge, provisioned Grafana datasource and dashboard (station selector, one panel per measurement, battery thresholds), `docker-compose.yml` and `.env.example`. Fully independent of ThingsBoard.
- **`tools/dl1_tee.py`** — optional relay that fans one DL1 TCP stream out to several bridges, so v1 and v2 can run side by side. Skips targets that are down and detects targets restarted behind Docker's port proxy.
- **Battery voltage** (`battery_voltage`, `data[38:40]` ÷ 100, volts) decoded and stored in both stacks. Confirmed when the depleted main 12 V battery (≈10.2 V) was replaced and the reading jumped to ≈12.1 V.
- `docker-compose.yml` and `.env.example` for v1.
- `docs/SERVER_REQUIREMENTS.md` — minimum and recommended server specs for v1 and v2.

### Changed
- Repository split into `v1-thingsboard/` and `v2-grafana/`; the two stacks share no code or runtime.
- Bridges read the frame length from the header (`data[2:4]` + 2) instead of assuming 46 bytes, resynchronise on the `40 01` prefix, and log every raw frame in hex — needed for reverse-engineering frames when new sensors are added.
- `make_dashboard.py` updates the existing ThingsBoard dashboard in place instead of creating a duplicate.
- All bridge settings (ports, hosts, tokens, log paths) come from environment variables / `.env`.
- Earlier office-server and laptop-relay scripts moved to `v1-thingsboard/legacy/`.

### Fixed
- DL1 occasionally injects modem AT commands (`AT+QISEND=0,46\r\n`) into the TCP stream; the resync logic now discards them instead of corrupting the following frames.

### Security
- Tokens, passwords and server/tunnel addresses removed from tracked files: scripts read gitignored `.env` files, `CLAUDE.md` uses placeholders resolved in a gitignored `CLAUDE.local.md`. Values in older commits must be treated as compromised.

### Removed
- `bridge/log_to_vm.py` — the interim script that fed Grafana by tailing the ThingsBoard bridge log.

## 2026-10-14

### Added
- First end-to-end delivery over **cellular (SIM)** from Station 1 in the field, through a temporary ThingsBoard on a Mac exposed with an ngrok TCP tunnel.
- `dl1_bridge_mac.py` and `make_dashboard_mac.py` for that temporary Mac setup (now `v1-thingsboard/bridge/`).

### Notes
- Over the cellular link the DL1 sends readings buffered during an outage as a fast burst; the bridge stamps them with arrival time, so they are not placed at their real time.
- The DL1 real-time clock is unreliable: after a power cycle it resets to `2018-07-25`. Timestamps are taken from the server.

## 2026-09-09

### Changed
- Synced the repository copy of the office-server bridge before planned server downtime.

## 2026-09-07

### Added
- Initial DL1 → ThingsBoard bridge, reverse-engineered 46-byte frame parser and ThingsBoard dashboard script.

### Fixed
- Rainfall read from `data[37]` (was `data[38:40]`, which is always zero on the office unit).
- Bridge idle-connection timeout raised from 60 s to 600 s; idle closes are now logged.

### Notes
- Documented DL1 connectivity incidents: the logger can stop sending on an open connection, and repeated reconnects (e.g. bridge restarts) make this more likely. Data from outages over Ethernet is not back-filled.
