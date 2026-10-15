# Meteostansiya

**Telemetry backend for a network of solar-powered automatic weather stations.**

Each station's DL1 data logger reports sensor readings over cellular, Ethernet or LoRa as compact binary TCP frames. This repository decodes those frames and stores them for dashboards, alerting and export. It contains two interchangeable backends:

| | **v1 — ThingsBoard** | **v2 — Grafana + VictoriaMetrics** |
|---|---|---|
| Storage | ThingsBoard CE + PostgreSQL | VictoriaMetrics (time-series DB) |
| Dashboards | ThingsBoard widgets | Grafana |
| Memory (measured, idle) | ~1.2 GB | ~80 MB |
| Best for | Device/customer management, rule engine | Lightweight hosting, metrics and alerting |

The two stacks are **fully independent**. They share no code or runtime, and each can be deployed on its own.

---

## Contents

- [Architecture](#architecture)
- [Hardware](#hardware)
- [DL1 protocol](#dl1-protocol)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Running both stacks at once](#running-both-stacks-at-once)
- [Data export](#data-export)
- [Server requirements](#server-requirements)
- [Operations and troubleshooting](#operations-and-troubleshooting)
- [Known limitations](#known-limitations)
- [Repository layout](#repository-layout)
- [Security](#security)
- [Changelog](#changelog)

---

## Architecture

```
                          v1:  v1 bridge ──HTTP──▶ ThingsBoard (+ PostgreSQL)
DL1 logger ──TCP frames──▶
                          v2:  v2 bridge ────────▶ VictoriaMetrics ◀── Grafana
```

A DL1 opens a TCP connection to one configured `IP:port` and pushes one frame per collection interval. The bridge listens on that port and does four things:

1. splits the byte stream into frames, using the length field in the header;
2. decodes the sensor values;
3. stamps them with **server time**, because the logger's clock is unreliable;
4. writes them to the storage backend.

## Hardware

Each station is a solar panel and a 12 V battery powering an RS485 sensor bus and a central data logger.

| Sensor | RS485 address | Measures |
|---|---|---|
| Combined T/RH/Light | `0001` | Temperature, relative humidity, illuminance |
| Anemometer | `0002` | Wind speed |
| Wind vane | `0003` | Wind direction |
| Rain gauge | `0004` | Rainfall |

**Data logger:** *Intelligent Data Logger · DL1* (board `LS-DL1-V1.21`, firmware V3.6) with three uplinks:

- **Cellular:** Quectel EC200S (SIM, 4G)
- **LoRa:** Ebyte E22-400T22S (SX1268, 400 MHz)
- **Ethernet:** onboard RJ45

Uplink targets are set on the device under `8.Set` → `a. Wireless IP` / `b. LAN IP` / `d. LoRa`. The matching channel must also be enabled in `c. Data Router`.

Reference photos of the hardware are in [`Rasmlar/`](./Rasmlar).

## DL1 protocol

The protocol was reverse-engineered by comparing raw frames with the values shown on the logger's own screen. Frames start with `40 01`, followed by a big-endian payload length (`data[2:4]`). The total frame length is that payload length + 2, which is 46 bytes with the current sensor set.

| Field | Offset | Encoding | Unit | Status |
|---|---|---|---|---|
| Temperature | `data[17:19]` | uint16 BE ÷ 10 | °C | confirmed |
| Humidity | `data[19:21]` | uint16 BE ÷ 10 | %RH | confirmed |
| Light | `data[22]` | uint8 × 10 | lux | confirmed |
| Wind speed | `data[27]` | uint8 ÷ 100 | m/s | likely, may be uint16 `data[26:28]` |
| Wind direction | `data[31:33]` | uint16 BE | ° | confirmed |
| Rainfall | `data[37]` | uint8 ÷ 10 | mm | provisional, needs real rain |
| Battery voltage | `data[38:40]` | uint16 BE ÷ 100 | V | confirmed by battery swap |
| Logger clock | `data[6:12]` | YY MM DD hh mm ss | — | unreliable, ignored |
| Checksum | last 4 bytes | unknown | — | not verified |

Every received frame is logged in hex (`raw (46B): …`), so new sensors can be mapped by comparing their frames with the values on the logger's screen. Full reverse-engineering notes are in [`CLAUDE.md`](./CLAUDE.md).

## Quick start

Requirements: Docker with the Compose plugin, and one TCP port reachable from the stations.

### v2: Grafana + VictoriaMetrics

```sh
cd v2-grafana
cp .env.example .env          # set GRAFANA_ADMIN_PASSWORD at minimum
docker compose up -d
```

- **Grafana:** `http://<server>:3000`, dashboard **Meteostansiyalar**
- **DL1 target:** `<server-ip>:8888`

### v1: ThingsBoard

```sh
cd v1-thingsboard
cp .env.example .env
docker compose up -d thingsboard      # first start takes a few minutes
```

1. Log in to ThingsBoard at `http://<server>:9090` and **change the default tenant password**.
2. Create a device and copy its ID and access token into `.env` (`TB_DEVICE_ID`, `TB_DEVICE_TOKEN`).
3. Start the bridge and create the dashboard:

```sh
docker compose up -d bridge
python3 bridge/make_dashboard.py
```

- **DL1 target:** `<server-ip>:8888`

## Configuration

Each stack is configured only through its own `.env`, which is gitignored. The same file is read by Docker Compose and by the Python scripts when they run outside Docker.

**v1** ([`v1-thingsboard/.env.example`](./v1-thingsboard/.env.example))

| Variable | Purpose |
|---|---|
| `TB_USERNAME`, `TB_PASSWORD` | Tenant login used by `make_dashboard.py` |
| `TB_DEVICE_ID`, `TB_DEVICE_TOKEN` | ThingsBoard device that receives telemetry |
| `LISTEN_PORT`, `LOGFILE` | Bridge port and log file when run directly |
| `TB_HTTP_PORT`, `BRIDGE_PORT` | Host ports published by Compose |

**v2** ([`v2-grafana/.env.example`](./v2-grafana/.env.example))

| Variable | Purpose |
|---|---|
| `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD` | Grafana admin login |
| `DEFAULT_STATION` | `station` label written for incoming data |
| `GRAFANA_PORT`, `BRIDGE_PORT` | Host ports published by Compose |
| `VM_RETENTION` | Data retention, e.g. `5y` |

## Running both stacks at once

A DL1 can report to only one `IP:port`. To feed both stacks from the same station, run the optional relay [`tools/dl1_tee.py`](./tools/dl1_tee.py) on the port the station targets, and move the bridges to other ports:

```sh
# in v1-thingsboard/.env: BRIDGE_PORT=8801   in v2-grafana/.env: BRIDGE_PORT=8802
python3 tools/dl1_tee.py --listen 8888 --to 127.0.0.1:8801 --to 127.0.0.1:8802
```

The tee copies every byte to each target:

- If a target is down, the tee skips it and reconnects on the next frame, so one stack being stopped never affects the other.
- Restarting a bridge does not drop the station's connection. Restarting the tee does.

## Data export

**v2 (Grafana).** Use panel menu **⋮ → Inspect → Data → Download CSV**. Enable *Download for Excel* to get an Excel-friendly file.

**v2, bulk export of all measurements** straight from VictoriaMetrics:

```sh
curl -sg 'http://127.0.0.1:8428/api/v1/export/csv?format=__timestamp__:rfc3339,__name__,station,__value__&match[]={__name__=~"meteo_.*"}&start=-7d' > meteo.csv
```

Timestamps are in UTC, one value per row.

**v1 (ThingsBoard).** Use the widget menu → **Export to CSV / XLS**.

## Server requirements

Minimum and recommended specifications, measured resource usage and cost estimates are in [`docs/SERVER_REQUIREMENTS.md`](./docs/SERVER_REQUIREMENTS.md) (Uzbek).

| | Minimum | Recommended |
|---|---|---|
| **v1** | 1 vCPU · 2 GB RAM · 20 GB SSD | 2 vCPU · 4 GB RAM · 40 GB SSD |
| **v2** | 1 vCPU · 1 GB RAM · 10 GB SSD | 1–2 vCPU · 2 GB RAM · 20 GB SSD |

Both stacks need a **static public IPv4**, because the DL1 accepts only an IP address and not a hostname. They also need an open inbound TCP port for the stations.

## Operations and troubleshooting

| Symptom | Check |
|---|---|
| No new data | Bridge log: is there a recent `connection opened` / `decoded`? v1: `LOGFILE`; v2: `docker logs meteo-v2-bridge` |
| Connection open but logger silent | Known DL1 firmware issue; power-cycle the logger. Avoid unnecessary bridge restarts, because each one forces a reconnect |
| Logger shows `Server: Normal` but nothing arrives | That status only means a TCP connection was opened. Verify that the target `IP:port` is still yours |
| Burst of old readings after reconnect | The logger is flushing its buffer. These readings get arrival-time timestamps |
| Readings drop or logger misbehaves | Check `battery_voltage`. Below ~11.8 V the 12 V battery is nearly empty |
| `resync, dropping byte …` in log | Non-frame bytes in the stream, e.g. leaked modem AT commands. They are discarded safely |

## Known limitations

- **Single station per stack.** All connections are attributed to one device or station. Station identification from the DL1 ID inside the frame is still to be implemented, because source IPs change with every mobile connection.
- **Logger clock.** The DL1 real-time clock resets to `2018-07-25` after a power cycle, so server time is used. As a result, buffered readings flushed after an outage are not placed at their true time.
- **Checksum.** The 4-byte trailer is not validated.
- **Unconfirmed fields.** Wind speed width and rainfall semantics still need confirmation.

## Repository layout

```
.
├── v1-thingsboard/          v1 stack
│   ├── bridge/              dl1_bridge.py, make_dashboard.py
│   ├── legacy/              earlier office-server / laptop-relay scripts (reference)
│   ├── docker-compose.yml
│   └── .env.example
├── v2-grafana/              v2 stack
│   ├── bridge/              dl1_bridge.py
│   ├── grafana/             provisioning + dashboards
│   ├── docker-compose.yml
│   └── .env.example
├── tools/dl1_tee.py         optional stream relay for running both stacks
├── docs/                    server requirements
├── Rasmlar/                 hardware reference photos
├── CHANGELOG.md
└── CLAUDE.md                detailed engineering log (infra, incidents, protocol notes)
```

## Security

This repository is public.

- **Credentials and addresses:** tokens, passwords and server or tunnel addresses are kept out of tracked files. They live in each stack's gitignored `.env`, and `CLAUDE.md` uses `<PLACEHOLDER>` values.
- **Older commits:** earlier commits still contain previous credentials. Treat those as compromised and rotate them before production use.
- **Default passwords:** always replace default passwords (ThingsBoard demo tenant, Grafana admin).
- **Unauthenticated DL1 port:** the station port accepts frames from anyone who can reach it. Restrict it with a firewall where possible.

## Changelog

See [`CHANGELOG.md`](./CHANGELOG.md).
