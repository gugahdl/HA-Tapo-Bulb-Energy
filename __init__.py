"""Tapo Bulb Energy - integracao config-entry based."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import (
    SOURCE_INTEGRATION_DISCOVERY,
    ConfigEntry,
    ConfigEntryState,
)
from homeassistant.const import CONF_HOST, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, discovery_flow
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_TPLINK_ENTRY_ID, DOMAIN, SCAN_INTERVAL, TPLINK_DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class TapoBulbEnergyData:
    """Dados de runtime de uma entrada de config."""
    coordinator: DataUpdateCoordinator
    device_id: str
    device_mac: str
    name: str
    host: str
    host_key: str


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
    _LOGGER.warning(
        "[tapo_bulb_energy] Estrutura do runtime_data do tplink mudou; usando fallback"
    )
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


def supports_usage(tplink_entry: ConfigEntry) -> bool:
    """Indica se o device de uma entrada tplink carregada expoe get_device_usage."""
    if tplink_entry.state is not ConfigEntryState.LOADED:
        return False
    _, device = _get_device_from_runtime(getattr(tplink_entry, "runtime_data", None))
    return device is not None and "get_device_usage" in device.internal_state


@callback
def async_available_bulbs(
    hass: HomeAssistant, keep_tplink_entry_id: str | None = None
) -> dict[str, str]:
    """Lampadas tplink compativeis que ainda nao sao monitoradas.

    Retorna {tplink_entry_id: titulo}. keep_tplink_entry_id permanece na lista
    mesmo ja configurado (usado pelo options flow para a lampada atual).
    """
    configured = {
        entry.data.get(CONF_TPLINK_ENTRY_ID)
        for entry in hass.config_entries.async_entries(DOMAIN, include_ignore=False)
    }
    return {
        entry.entry_id: entry.title
        for entry in hass.config_entries.async_entries(TPLINK_DOMAIN)
        if (entry.entry_id == keep_tplink_entry_id or entry.entry_id not in configured)
        and supports_usage(entry)
    }


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Oferece como descobertas as lampadas tplink compativeis ao iniciar o HA."""

    @callback
    def _async_discover(_hass: HomeAssistant) -> None:
        for tplink_entry_id in async_available_bulbs(hass):
            discovery_flow.async_create_flow(
                hass,
                DOMAIN,
                context={"source": SOURCE_INTEGRATION_DISCOVERY},
                data={CONF_TPLINK_ENTRY_ID: tplink_entry_id},
            )

    async_at_started(hass, _async_discover)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura a integracao a partir de um config entry."""
    tplink_entry_id = entry.data[CONF_TPLINK_ENTRY_ID]
    name = entry.data.get(CONF_NAME, entry.title)
    host = entry.data.get(CONF_HOST, "")

    tplink_entry = hass.config_entries.async_get_entry(tplink_entry_id)
    if tplink_entry is None:
        raise ConfigEntryError(
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

    # Mesmo formato do YAML nos unique_ids dos sensores, para preservar o historico
    host_key = host.replace(".", "_")

    async def async_update_data() -> dict[str, float | int | None]:
        """Le get_device_usage do cache que o tplink ja atualiza a cada 5 s.

        O device e buscado a cada ciclo porque o tplink cria um objeto novo
        quando recarrega (troca de IP, credenciais, reload manual).
        """
        tplink_entry = hass.config_entries.async_get_entry(tplink_entry_id)
        if tplink_entry is None or tplink_entry.state is not ConfigEntryState.LOADED:
            raise UpdateFailed(f"[tapo_bulb_energy] tplink nao carregado para {host}")
        coord, device = _get_device_from_runtime(tplink_entry.runtime_data)
        if device is None or not getattr(coord, "last_update_success", True):
            raise UpdateFailed(f"[tapo_bulb_energy] {host} indisponivel")

        usage = device.internal_state.get("get_device_usage")
        if not usage:
            # Normalmente nao acontece: o python-kasa ja pede get_device_usage
            try:
                result = await device.protocol.query({"get_device_usage": None})
            except Exception as err:
                raise UpdateFailed(
                    f"[tapo_bulb_energy] Falha ao ler {host}: {err}"
                ) from err
            usage = result.get("get_device_usage") or {}

        time_data = usage.get("time_usage") or {}
        power_data = usage.get("power_usage") or {}

        def kwh(period: str) -> float | None:
            if (mwh := power_data.get(f"{period}_mwh")) is not None:
                return round(mwh / 1_000_000, 4)
            if (wh := power_data.get(period)) is not None:
                return round(wh / 1_000, 4)
            return None

        # Campo ausente vira None (estado desconhecido), nunca 0: um 0 falso
        # seguido do valor real seria contado como reset e duplicaria o consumo.
        return {
            "today_runtime": time_data.get("today"),
            "past7_runtime": time_data.get("past7"),
            "past30_runtime": time_data.get("past30"),
            "today_energy": kwh("today"),
            "past7_energy": kwh("past7"),
            "past30_energy": kwh("past30"),
        }

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
        host_key=host_key,
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recarrega a entrada quando o dispositivo monitorado muda via Options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove a integracao."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
