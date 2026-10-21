# Tapo Bulb Energy

[![Validate](https://github.com/gugahdl/HA-Tapo-Bulb-Energy/actions/workflows/validate.yml/badge.svg)](https://github.com/gugahdl/HA-Tapo-Bulb-Energy/actions/workflows/validate.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom integration that adds energy and on-time usage sensors for **TP-Link Tapo smart bulbs** (built and tested on the **L530E**), filling a gap left by the built-in TP-Link integration.

## Why does this exist?

Home Assistant's built-in **TP-Link** integration is powered by [python-kasa](https://github.com/python-kasa/python-kasa). For Tapo bulbs, python-kasa already fetches the device's `get_device_usage` response (accumulated on-time and estimated energy) on every update, but it does not expose that data as sensors.

This integration doesn't reimplement a device protocol or add new network connections. It reads that response from the TP-Link integration's cached device state (falling back to a direct query over the same session only if the cache is empty):

```json
{
  "time_usage":  {"today": 123, "past7": 456, "past30": 789},
  "power_usage": {"today_mwh": 12345, "past7_mwh": 67890, "past30_mwh": 123456}
}
```

...which this integration turns into six sensors (see below).

## Prerequisites

- Home Assistant 2024.11 or later
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
3. Pick your bulb from the list. Only compatible TP-Link bulbs that are not monitored yet are listed, and the host/IP is resolved automatically.
4. Done — six sensors are created for that bulb

**Automatic discovery:** when Home Assistant starts, every compatible TP-Link bulb that is not monitored yet shows up under **Settings → Devices & Services → Discovered**. Click **Add** to start monitoring it, or **Ignore** to stop being asked.

To monitor another bulb, add the integration again (or accept its discovery card). To swap which bulb an existing entry monitors, use its **Configure** button. The new bulb's sensors start with a fresh history, because sensor IDs are tied to the bulb's IP.

## Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Tempo Ligada Hoje | min | On-time today |
| Tempo Ligada 7 Dias | min | On-time over the past 7 days |
| Tempo Ligada 30 Dias | min | On-time over the past 30 days |
| Energia Hoje | kWh | Energy consumed today |
| Energia 7 Dias | kWh | Energy consumed over the past 7 days |
| Energia 30 Dias | kWh | Energy consumed over the past 30 days |

**Energia Hoje** uses `state_class: total_increasing`, so Home Assistant's statistics and Energy dashboard handle the firmware's midnight reset automatically. The 7- and 30-day sensors are rolling windows (they go down when an old day drops out), so they have no state class and no long-term sum statistics; use **Energia Hoje** in the Energy dashboard.

The bulb has no power meter: these values are the firmware's own estimates. There is no instantaneous power (W) reading on Tapo bulbs.

## Notes

- Updates every 5 minutes from the TP-Link integration's cached state — no extra credentials, ports, or connections
- Sensors become unavailable while the bulb is offline (for example, switched off at the wall)
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
