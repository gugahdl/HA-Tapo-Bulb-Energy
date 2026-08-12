# Tapo Bulb Energy

[![Validate](https://github.com/gugahdl/HA-Tapo-Bulb-Energy/actions/workflows/validate.yml/badge.svg)](https://github.com/gugahdl/HA-Tapo-Bulb-Energy/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom integration that adds energy and on-time usage sensors for **TP-Link Tapo smart bulbs** (built and tested on the **L530E**), filling a gap left by the built-in TP-Link integration.

## Why does this exist?

Home Assistant's built-in **TP-Link** integration is powered by [python-kasa](https://github.com/python-kasa/python-kasa). That library calls the device's `get_device_usage` API to report accumulated on-time and energy consumption — but it only wires that call up for **smart plugs** (via the `Emeter`/`Energy` modules). For **bulbs**, `get_device_usage` is never queried, even though the bulb's firmware supports it and returns real data.

This integration doesn't reimplement a device protocol or add new network connections — it reuses the TP-Link integration's already-authenticated session for the same device and issues the missing `get_device_usage` query directly:

```json
{
  "time_usage":  {"today": 123, "past7": 456, "past30": 789},
  "power_usage": {"today_mwh": 12345, "past7_mwh": 67890, "past30_mwh": 123456}
}
```

...which this integration turns into six sensors (see below).

## Prerequisites

- Home Assistant 2023.1 or later
- The built-in **TP-Link** integration already set up with your Tapo bulb

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → three-dot menu → **Custom repositories**
3. Add `https://github.com/gugahdl/HA-Tapo-Bulb-Energy` with category **Integration**
4. Search for **Tapo Bulb Energy** and install it
5. Restart Home Assistant

### Manual

1. Download the latest release (or clone this repo)
2. Copy all files into `config/custom_components/tapo_bulb_energy/`
3. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Tapo Bulb Energy**
3. Pick your bulb from the device selector (only TP-Link devices are listed — the host/IP is resolved automatically, no manual typing)
4. Done — six sensors are created for that bulb

To monitor another bulb, add the integration again and pick a different device. To swap which bulb an existing entry monitors, use its **Configure** button — no need to remove and re-add it.

## Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Tempo Ligada Hoje | min | On-time today |
| Tempo Ligada 7 Dias | min | On-time over the past 7 days |
| Tempo Ligada 30 Dias | min | On-time over the past 30 days |
| Energia Hoje | kWh | Energy consumed today |
| Energia 7 Dias | kWh | Energy consumed over the past 7 days |
| Energia 30 Dias | kWh | Energy consumed over the past 30 days |

Energy sensors use `state_class: total` with automatic midnight-reset detection: when the firmware's daily counter drops, the sensor emits a fresh `last_reset` so Home Assistant's energy dashboard handles the rollover correctly.

## Notes

- Polls every 5 minutes
- Reuses the TP-Link integration's device session — no extra credentials, ports, or connections
- Sensor `unique_id`s are host-based, preserving history across restarts
- UI is available in English and Portuguese (pt-BR); other languages fall back to English
- If you remove the underlying TP-Link device/entry, this integration's sensors will start failing updates until you remove or reconfigure the entry — it does not currently detect and self-remove in that case (see Roadmap)

## Roadmap / not yet implemented

Contributions welcome — these are known gaps, not blockers for normal use:

- [ ] `diagnostics.py` for one-click debug info export from the UI
- [ ] Automated tests (`pytest-homeassistant-custom-component`)
- [ ] Auto-remove/notify when the linked TP-Link device or entry is deleted
- [ ] Add GitHub repository topics (e.g. `home-assistant`, `hacs`, `tplink`, `tapo`) — required for HACS default-store eligibility
- [ ] Submit the integration icon to [home-assistant/brands](https://github.com/home-assistant/brands) for the default icon set — also required for HACS default-store eligibility
- [ ] Additional language translations beyond en/pt-BR

## License

MIT — see [LICENSE](LICENSE)
