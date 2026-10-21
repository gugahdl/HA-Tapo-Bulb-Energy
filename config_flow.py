"""Config flow para Tapo Bulb Energy."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from . import async_available_bulbs
from .const import CONF_TPLINK_ENTRY_ID, DOMAIN, TPLINK_DOMAIN

_LOGGER = logging.getLogger(__name__)


def _unique_id(tplink_entry_id: str) -> str:
    """unique_id da entrada; mesmo formato da v2.0 para reconhecer entradas antigas."""
    return f"tapo_energy_{tplink_entry_id}"


def _entry_data(hass: HomeAssistant, tplink_entry_id: str) -> tuple[str, dict[str, Any]]:
    """Monta (titulo, data) da entrada a partir da entrada tplink."""
    tplink_entry = hass.config_entries.async_get_entry(tplink_entry_id)
    host = tplink_entry.data.get(CONF_HOST, "") if tplink_entry else ""
    title = tplink_entry.title if tplink_entry else tplink_entry_id
    return title, {CONF_TPLINK_ENTRY_ID: tplink_entry_id, CONF_HOST: host}


def _bulb_schema(bulbs: dict[str, str], default: str | None = None) -> vol.Schema:
    """Lista de lampadas como dropdown."""
    key = (
        vol.Required(CONF_TPLINK_ENTRY_ID, default=default)
        if default
        else vol.Required(CONF_TPLINK_ENTRY_ID)
    )
    return vol.Schema(
        {
            key: selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=entry_id, label=title)
                        for entry_id, title in bulbs.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


class TapoBulbEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow para Tapo Bulb Energy."""

    VERSION = 1

    _tplink_entry_id: str

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Cria o options flow handler."""
        return OptionsFlowHandler()

    def _abort_if_tplink_entry_configured(self, tplink_entry_id: str) -> None:
        """Barra duplicata tambem por data, alem do unique_id."""
        self._async_abort_entries_match({CONF_TPLINK_ENTRY_ID: tplink_entry_id})

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Passo inicial: lista so lampadas compativeis ainda nao monitoradas."""
        if not self.hass.config_entries.async_entries(TPLINK_DOMAIN):
            return self.async_abort(reason="no_tplink_devices")

        if user_input is not None:
            tplink_entry_id = user_input[CONF_TPLINK_ENTRY_ID]
            await self.async_set_unique_id(_unique_id(tplink_entry_id))
            self._abort_if_unique_id_configured()
            self._abort_if_tplink_entry_configured(tplink_entry_id)
            title, data = _entry_data(self.hass, tplink_entry_id)
            return self.async_create_entry(title=title, data=data)

        bulbs = async_available_bulbs(self.hass)
        if not bulbs:
            return self.async_abort(reason="no_bulbs_available")

        return self.async_show_form(step_id="user", data_schema=_bulb_schema(bulbs))

    async def async_step_integration_discovery(
        self, discovery_info: dict[str, Any]
    ) -> ConfigFlowResult:
        """Lampada tplink compativel encontrada ao iniciar o HA."""
        tplink_entry_id = discovery_info[CONF_TPLINK_ENTRY_ID]
        await self.async_set_unique_id(_unique_id(tplink_entry_id))
        self._abort_if_unique_id_configured()
        self._abort_if_tplink_entry_configured(tplink_entry_id)

        self._tplink_entry_id = tplink_entry_id
        title, _ = _entry_data(self.hass, tplink_entry_id)
        self.context["title_placeholders"] = {"name": title}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirma a lampada descoberta."""
        title, data = _entry_data(self.hass, self._tplink_entry_id)
        if user_input is not None:
            return self.async_create_entry(title=title, data=data)

        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": title},
        )


class OptionsFlowHandler(OptionsFlow):
    """Permite trocar a lâmpada monitorada sem remover a integração."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Mostra as lampadas disponiveis (mais a atual) para reconfigurar."""
        current = self.config_entry.data.get(CONF_TPLINK_ENTRY_ID)

        if user_input is not None:
            tplink_entry_id = user_input[CONF_TPLINK_ENTRY_ID]
            if tplink_entry_id != current:
                title, data = _entry_data(self.hass, tplink_entry_id)
                # Dispara o update listener, que recarrega a entrada
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=title,
                    data=data,
                    unique_id=_unique_id(tplink_entry_id),
                )
            return self.async_create_entry(title="", data={})

        bulbs = async_available_bulbs(self.hass, keep_tplink_entry_id=current)
        if not bulbs:
            return self.async_abort(reason="no_bulbs_available")

        return self.async_show_form(
            step_id="init",
            data_schema=_bulb_schema(bulbs, default=current if current in bulbs else None),
        )
