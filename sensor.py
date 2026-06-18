"""Sensor platform para Tapo Bulb Energy (config-entry based)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN


@dataclass
class TapoSensorDescription:
    """Descricao de um sensor Tapo."""
    key: str
    name: str
    unit: str
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass
    icon: str | None = None


SENSOR_DESCRIPTIONS: list[TapoSensorDescription] = [
    TapoSensorDescription(
        key="today_runtime",
        name="Tempo Ligada Hoje",
        unit=UnitOfTime.MINUTES,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:clock-outline",
    ),
    TapoSensorDescription(
        key="past7_runtime",
        name="Tempo Ligada 7 Dias",
        unit=UnitOfTime.MINUTES,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:clock-outline",
    ),
    TapoSensorDescription(
        key="past30_runtime",
        name="Tempo Ligada 30 Dias",
        unit=UnitOfTime.MINUTES,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:clock-outline",
    ),
    TapoSensorDescription(
        key="today_energy",
        name="Energia Hoje",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:lightning-bolt",
    ),
    TapoSensorDescription(
        key="past7_energy",
        name="Energia 7 Dias",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:lightning-bolt",
    ),
    TapoSensorDescription(
        key="past30_energy",
        name="Energia 30 Dias",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:lightning-bolt",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cria os sensores a partir do config entry."""
    data = entry.runtime_data

    entities = [
        TapoBulbEnergySensor(
            data.coordinator,
            description,
            data.name,
            data.device_mac,
            data.device_id,
        )
        for description in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class TapoBulbEnergySensor(CoordinatorEntity, RestoreEntity, SensorEntity):
    """Sensor de energia de uma lampada Tapo."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: TapoSensorDescription,
        device_name: str,
        device_mac: str,
        device_id: str,
    ) -> None:
        """Inicializa o sensor."""
        super().__init__(coordinator)
        self._description = description
        self._attr_name = f"{device_name} {description.name}"

        # Preserva o mesmo unique_id do codigo YAML para manter historico
        host_key = coordinator.name.replace("tapo_bulb_energy_", "")
        self._attr_unique_id = f"tapo_energy_{host_key}_{description.key}"

        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_icon = description.icon

        # Usado para detectar quando o firmware resetou (today_energy)
        self._last_value: float | None = None

        # Vincula ao mesmo device que a integracao tplink registrou
        if device_id:
            self._attr_device_info = DeviceInfo(
                identifiers={("tplink", device_id)},
            )
        else:
            self._attr_device_info = DeviceInfo(
                connections={(CONNECTION_NETWORK_MAC, device_mac)},
            )

    async def async_added_to_hass(self) -> None:
        """Restaura o ultimo valor conhecido apos reinicio do HA."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._last_value = float(last_state.state)
            except (ValueError, TypeError):
                self._last_value = None

    def _handle_coordinator_update(self) -> None:
        """Detecta reset do firmware (today_energy) e sinaliza last_reset."""
        if self._description.key == "today_energy" and self.coordinator.data:
            value = self.coordinator.data.get("today_energy")
            if value is not None:
                if self._last_value is not None and value < self._last_value:
                    # Firmware resetou a meia-noite — sinaliza oficialmente
                    self._attr_last_reset = dt_util.utcnow()
                self._last_value = value
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float | None:
        """Retorna o valor atual do sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Atributos extras."""
        return {"source": "get_device_usage via tplink session"}
