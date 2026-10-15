# Meteostansiya

Telemetry pipeline for a network of remote weather-monitoring stations, streaming sensor data over cellular, Ethernet, or LoRa into [ThingsBoard](https://thingsboard.io/) for storage and monitoring.

## Overview

Five solar-powered, mobile weather stations are being deployed. Each station reports meteorological readings (temperature, humidity, light, wind speed, wind direction, rainfall) back to a central server, where the data is decoded and pushed into ThingsBoard for visualization and alerting. Image/video capture is out of scope — reference photos of the hardware live in [`Rasmlar/`](./Rasmlar).

## Hardware

Each station is built around solar panel + RS485 sensor bus + a central data logger:

| Sensor | RS485 Address | Measures |
|---|---|---|
| Combined T/RH/Light | `0001` | Temperature, humidity, light (single housing) |
| Anemometer | `0002` | Wind speed |
| Wind vane | `0003` | Wind direction |
| Rain gauge | `0004` | Rainfall |

**Data logger:** "Intelligent Data Logger · DL1" (board `LS-DL1-V1.21`, firmware V3.6), which aggregates all four sensors and forwards telemetry over its choice of uplink:

- **Cellular** — Quectel EC200S module (SIM, GPRS/4G)
- **LoRa** — Ebyte E22-400T22S (SX1268, 400 MHz, 22 dBm)
- **Ethernet** — onboard RJ45

The logger buffers readings locally, so a temporary loss of connectivity does not drop data.

## Protocol

The DL1 pushes a fixed-size **46-byte binary frame** over TCP at each collection interval. The frame layout was reverse-engineered by comparing raw bytes against the logger's own on-device screen readings; see [`CLAUDE.md`](./CLAUDE.md) for the full byte-offset breakdown (temperature, humidity, light, wind speed, wind direction confirmed; rainfall offset provisional pending a real rainfall event).

## Two independent stacks

The repository holds two complete, independent versions of the receiving side. They share no code or runtime, and each one is deployed from its own folder with its own `docker-compose.yml` and `.env`:

```
v1:  DL1 --TCP--> v1 bridge --HTTP--> ThingsBoard (+ PostgreSQL)
v2:  DL1 --TCP--> v2 bridge --> VictoriaMetrics <-- Grafana
```

- [`v1-thingsboard/`](./v1-thingsboard) — ThingsBoard CE stack.
  - [`bridge/dl1_bridge.py`](./v1-thingsboard/bridge/dl1_bridge.py) — decodes DL1 frames and pushes telemetry to a ThingsBoard device.
  - [`bridge/make_dashboard.py`](./v1-thingsboard/bridge/make_dashboard.py) — creates or updates the ThingsBoard dashboard via the API.
  - [`legacy/`](./v1-thingsboard/legacy) — earlier office-server and laptop-relay bridges, kept for reference.
- [`v2-grafana/`](./v2-grafana) — Grafana + VictoriaMetrics stack.
  - [`bridge/dl1_bridge.py`](./v2-grafana/bridge/dl1_bridge.py) — decodes DL1 frames and writes them to VictoriaMetrics (Influx line protocol).
  - [`grafana/`](./v2-grafana/grafana) — provisioned datasource and dashboard (station selector, one panel per measurement).
- [`tools/dl1_tee.py`](./tools/dl1_tee.py) — optional relay. A DL1 reports to a single IP:port, so to run both stacks side by side the tee accepts the DL1 connection and copies the byte stream to both bridges. Neither stack needs it; point the DL1 straight at one bridge to run that stack alone.

Run either stack:

```sh
cd v2-grafana            # or v1-thingsboard
cp .env.example .env     # fill in values
docker compose up -d
```

## Infrastructure

- **Server:** self-hosted Ubuntu box running [Coolify](https://coolify.io/), reachable over [Tailscale](https://tailscale.com/) and the local office LAN.
- **ThingsBoard:** deployed via Coolify, with a named Docker volume so device/dashboard state survives redeploys.
- **Reverse proxy / port sharing:** the ISP only exposes ports 80/443 externally, so [`sslh`](https://www.rutschle.net/tech/sslh/) multiplexes port 443 — routing TLS traffic to Traefik and raw (non-TLS) bytes from the DL1 loggers straight to the bridge — avoiding the need for a dedicated inbound port per deployment.

Full operational history, incident write-ups, and the exact current configuration are tracked in [`CLAUDE.md`](./CLAUDE.md).

## Status

Station 1 (office test unit) is connected end-to-end over Ethernet/local network and confirmed pushing telemetry into ThingsBoard. Remaining work includes validating the cellular (SIM) path, rotating default credentials, confirming the rainfall byte offset, and onboarding the remaining four stations.

## Repository layout

```
.
├── CLAUDE.md          # detailed project log: infra, incidents, protocol notes
├── docs/              # server requirements for v1 and v2
├── v1-thingsboard/    # v1: ThingsBoard stack (bridge, dashboard script, compose)
├── v2-grafana/        # v2: Grafana + VictoriaMetrics stack (bridge, provisioning, compose)
├── tools/             # optional DL1 stream tee for running both stacks at once
└── Rasmlar/           # reference photos of the test station hardware
```

## Server requirements

Two deployment variants are documented in [`docs/SERVER_REQUIREMENTS.md`](./docs/SERVER_REQUIREMENTS.md) (in Uzbek):

- **v1 — ThingsBoard**: full IoT platform, ~1.2 GB RAM for ThingsBoard alone; 2 vCPU / 4 GB RAM / 40 GB SSD recommended.
- **v2 — Grafana + VictoriaMetrics**: lightweight time-series stack, ~80 MB RAM measured; 1–2 vCPU / 2 GB RAM / 20 GB SSD recommended.

## Security note

This repository is public. Credentials, access tokens and server addresses are not stored in tracked files: each stack reads them from its own gitignored `.env` (see [`v1-thingsboard/.env.example`](./v1-thingsboard/.env.example) and [`v2-grafana/.env.example`](./v2-grafana/.env.example)), and `CLAUDE.md` uses `<PLACEHOLDER>` values resolved in a local, gitignored `CLAUDE.local.md`. Older commits still contain earlier credentials, which must be treated as compromised and rotated.
