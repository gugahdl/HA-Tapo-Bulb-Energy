"""Config flow para Tapo Bulb Energy."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, selector

from .const import CONF_DEVICE_ID, CONF_TPLINK_ENTRY_ID, DOMAIN, TPLINK_DOMAIN

_LOGGER = logging.getLogger(__name__)


def _resolve_tplink_entry_and_host(
    hass: HomeAssistant, device_id: str
) -> tuple[str | None, str]:
    """Resolve tplink_entry_id and host from device registry."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None, ""
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == TPLINK_DOMAIN:
            return entry_id, entry.data.get(CONF_HOST, "")
    return None, ""


class TapoBulbEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow para Tapo Bulb Energy."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Cria o options flow handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Passo inicial: seleciona o dispositivo tplink via device selector."""
        if not self.hass.config_entries.async_entries(TPLINK_DOMAIN):
            return self.async_abort(reason="no_tplink_devices")

        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            tplink_entry_id, host = _resolve_tplink_entry_and_host(self.hass, device_id)

            if tplink_entry_id is None:
                errors[CONF_DEVICE_ID] = "no_tplink_entry"
            else:
                await self.async_set_unique_id(f"tapo_energy_{device_id}")
                self._abort_if_unique_id_configured()

                device = dr.async_get(self.hass).async_get(device_id)
                name = (device.name_by_user or device.name) if device else device_id

                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_DEVICE_ID: device_id,
                        CONF_TPLINK_ENTRY_ID: tplink_entry_id,
                        CONF_HOST: host,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): selector.DeviceSelector(
                    selector.DeviceSelectorConfig(integration=TPLINK_DOMAIN)
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


class OptionsFlowHandler(OptionsFlow):
    """Permite trocar a lâmpada monitorada sem remover a integração."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Inicializa o options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Mostra o seletor de dispositivo para reconfigurar."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            tplink_entry_id, host = _resolve_tplink_entry_and_host(self.hass, device_id)

            if tplink_entry_id is None:
                errors[CONF_DEVICE_ID] = "no_tplink_entry"
            else:
                device = dr.async_get(self.hass).async_get(device_id)
                name = (device.name_by_user or device.name) if device else device_id

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=name,
                    data={
                        CONF_DEVICE_ID: device_id,
                        CONF_TPLINK_ENTRY_ID: tplink_entry_id,
                        CONF_HOST: host,
                    },
                )
                return self.async_create_entry(title="", data={})

        current_device_id = self.config_entry.data.get(CONF_DEVICE_ID, vol.UNDEFINED)

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID, default=current_device_id): selector.DeviceSelector(
                    selector.DeviceSelectorConfig(integration=TPLINK_DOMAIN)
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
