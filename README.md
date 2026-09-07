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

## Bridge & data flow

```
DL1 logger (station) --TCP, 46B frames--> dl1-bridge (Python) --HTTP--> ThingsBoard
```

- [`bridge/dl1_bridge_server.py`](./bridge/dl1_bridge_server.py) — production bridge, runs as a long-lived process on the same host as ThingsBoard. Listens on a TCP port, decodes incoming frames, maps the source IP to a ThingsBoard device access token, and forwards telemetry via the ThingsBoard REST API.
- [`bridge/dl1_bridge_local.py`](./bridge/dl1_bridge_local.py) — earlier prototype that relayed data through a local machine before the bridge was moved onto the server. Kept for reference only.
- [`bridge/make_dashboard.py`](./bridge/make_dashboard.py) — provisions a ThingsBoard device and dashboard (time-series widgets for each measurement) via the ThingsBoard API, so the setup can be reproduced or repeated for additional stations.

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
├── bridge/            # DL1 -> ThingsBoard bridge and provisioning scripts
└── Rasmlar/           # reference photos of the test station hardware
```

## Security note

This repository is private and contains real infrastructure details (server addresses, access tokens, default credentials) for an active deployment. Treat its contents as confidential; do not make this repository public without first rotating and redacting credentials.
