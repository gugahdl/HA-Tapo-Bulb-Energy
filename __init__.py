"""Tapo Bulb Energy - integracao config-entry based."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_TPLINK_ENTRY_ID, DOMAIN, SCAN_INTERVAL, TPLINK_DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


@dataclass
class TapoBulbEnergyData:
    """Dados de runtime de uma entrada de config."""
    coordinator: DataUpdateCoordinator
    device_id: str
    device_mac: str
    name: str
    host: str


def _get_device_from_runtime(runtime_data):
    """Extrai device do runtime_data de um config entry tplink."""
    if runtime_data is None:
        return None, None

    # Caminho principal: parent_coordinator ou coordinator
    for attr in ("parent_coordinator", "coordinator"):
        coord = getattr(runtime_data, attr, None)
        if coord is None:
            continue
        device = getattr(coord, "device", None)
        if device is not None:
            return coord, device

    # Fallback: varre todos os atributos em busca de obj com device.protocol
    for attr in dir(runtime_data):
        if attr.startswith("_"):
            continue
        try:
            obj = getattr(runtime_data, attr, None)
        except Exception:
            continue
        if obj is None:
            continue
        device = getattr(obj, "device", None)
        if device is not None and hasattr(device, "protocol"):
            return obj, device

    return None, None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura a integracao a partir de um config entry."""
    tplink_entry_id = entry.data[CONF_TPLINK_ENTRY_ID]
    name = entry.data.get(CONF_NAME, entry.title)
    host = entry.data.get(CONF_HOST, "")

    tplink_entry = hass.config_entries.async_get_entry(tplink_entry_id)
    if tplink_entry is None:
        raise ConfigEntryNotReady(
            f"[tapo_bulb_energy] Entry tplink {tplink_entry_id} nao encontrado."
        )

    runtime_data = getattr(tplink_entry, "runtime_data", None)
    _, device = _get_device_from_runtime(runtime_data)

    if device is None:
        raise ConfigEntryNotReady(
            f"[tapo_bulb_energy] Device tplink nao esta pronto para {host or tplink_entry_id}."
        )

    # Obtém host do device se não estava no config entry
    host = host or getattr(device, "host", host) or host
    device_id: str = getattr(device, "device_id", "") or ""
    device_mac: str = format_mac(getattr(device, "mac", "00:00:00:00:00:00"))

    _LOGGER.info(
        "[tapo_bulb_energy] %s (%s) - sessao tplink localizada, device_id: %s",
        name, host, device_id,
    )

    # Nome do coordinator = mesmo formato do YAML para preservar unique_ids e historico
    host_key = host.replace(".", "_")

    async def async_update_data() -> dict[str, Any]:
        """Le get_device_usage reutilizando o protocolo tplink existente."""
        try:
            result = await device.protocol.query({"get_device_usage": None})
            usage = result.get("get_device_usage", {})
            time_data = usage.get("time_usage", {})
            power_data = usage.get("power_usage", {})
            return {
                "today_runtime":  time_data.get("today", 0),
                "past7_runtime":  time_data.get("past7", 0),
                "past30_runtime": time_data.get("past30", 0),
                "today_energy":   round(power_data.get("today_mwh", 0) / 1_000_000, 4),
                "past7_energy":   round(power_data.get("past7_mwh",  0) / 1_000_000, 4),
                "past30_energy":  round(power_data.get("past30_mwh", 0) / 1_000_000, 4),
            }
        except Exception as err:
            raise UpdateFailed(f"[tapo_bulb_energy] Falha ao ler {host}: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"tapo_bulb_energy_{host_key}",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = TapoBulbEnergyData(
        coordinator=coordinator,
        device_id=device_id,
        device_mac=device_mac,
        name=name,
        host=host,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove a integracao."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
