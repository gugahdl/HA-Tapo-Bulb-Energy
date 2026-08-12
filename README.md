# Tapo Bulb Energy

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that exposes energy and runtime usage sensors for **Tapo L530E smart bulbs** (and similar Tapo bulbs).

## Why does this exist?

The official [python-kasa](https://github.com/python-kasa/python-kasa) library — which powers Home Assistant's built-in **TP-Link** integration — does **not** expose the `get_device_usage` API call for bulbs. It only makes that data available for smart plugs (via the `Emeter` module).

Tapo bulbs do support `get_device_usage` at the firmware level (tested on L530E), returning:

- **Runtime** (today / past 7 days / past 30 days) in minutes
- **Energy consumption** (today / past 7 days / past 30 days) in mWh

This integration hooks into the existing tplink session — reusing its already-authenticated protocol connection — and queries `get_device_usage` directly, with no extra credentials or network connections required.

## Prerequisites

- Home Assistant 2023.1 or later
- The built-in **TP-Link** integration already set up with your Tapo bulb

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add `https://github.com/gugahdl/ha-tapo-bulb-energy` with category **Integration**
4. Search for **Tapo Bulb Energy** and install it
5. Restart Home Assistant

### Manual

1. Download the latest release
2. Copy all files into `config/custom_components/tapo_bulb_energy/`
3. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Tapo Bulb Energy**
3. Select your Tapo bulb from the device picker (only TP-Link devices are shown)
4. Done — six sensors are created automatically

To change the monitored bulb later, go to the integration's **Configure** button (no need to remove and re-add it).

## Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Tempo Ligada Hoje | min | On-time today |
| Tempo Ligada 7 Dias | min | On-time over the past 7 days |
| Tempo Ligada 30 Dias | min | On-time over the past 30 days |
| Energia Hoje | kWh | Energy consumed today |
| Energia 7 Dias | kWh | Energy consumed over the past 7 days |
| Energia 30 Dias | kWh | Energy consumed over the past 30 days |

Energy sensors use `state_class: total` with automatic midnight-reset detection (daily value drop triggers `last_reset`).

## Notes

- Polls every 5 minutes
- Reuses the tplink integration's device session — no separate credentials needed
- Sensor unique IDs are based on the device IP to preserve history across restarts
- After changing the device via **Configure**, old sensor entities become unavailable and can be deleted manually

## License

MIT — see [LICENSE](LICENSE)
