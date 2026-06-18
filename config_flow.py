"""Config flow para Tapo Bulb Energy."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from .const import CONF_TPLINK_ENTRY_ID, DOMAIN, TPLINK_DOMAIN

_LOGGER = logging.getLogger(__name__)


class TapoBulbEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow para Tapo Bulb Energy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Passo inicial: seleciona o dispositivo tplink."""
        errors: dict[str, str] = {}

        tplink_entries = self.hass.config_entries.async_entries(TPLINK_DOMAIN)
        options = {e.entry_id: e.title for e in tplink_entries}

        if not options:
            return self.async_abort(reason="no_tplink_devices")

        if user_input is not None:
            tplink_entry_id = user_input[CONF_TPLINK_ENTRY_ID]
            tplink_entry = self.hass.config_entries.async_get_entry(tplink_entry_id)

            # Extrai host do config entry do tplink
            host = tplink_entry.data.get(CONF_HOST, "") if tplink_entry else ""
            name = user_input.get(CONF_NAME, "").strip()
            if not name:
                name = tplink_entry.title if tplink_entry else tplink_entry_id

            # Evita entrada duplicada para o mesmo dispositivo tplink
            await self.async_set_unique_id(f"tapo_energy_{tplink_entry_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=name,
                data={
                    CONF_TPLINK_ENTRY_ID: tplink_entry_id,
                    CONF_HOST: host,
                    CONF_NAME: name,
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_TPLINK_ENTRY_ID): vol.In(options),
                vol.Optional(CONF_NAME, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
