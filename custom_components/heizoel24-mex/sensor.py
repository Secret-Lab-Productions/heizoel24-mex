"""Platform for sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    ELECTRIC_POTENTIAL_VOLT,
    PERCENTAGE,
    TEMP_FAHRENHEIT,
    VOLUME_LITERS,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Renault entities from config entry."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TankVolume(coordinator, config_entry, 0),
        MaxTankVolume(coordinator, config_entry, 0),
        TankPercent(coordinator, config_entry, 0),
        Battery(coordinator, config_entry, 0),
        Temperature(coordinator, config_entry, 0),
    ]

    async_add_entities(entities, True)


class MexSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_attribution = "Data provided by the Proteus/E-Sensorix API"

    def __init__(self, coordinator, config_entry, idx, name, unique_id_suffix):
        super().__init__(coordinator)
        self.idx = idx
        self.config_entry = config_entry
        self._name = name

        conf = self.config_entry.data
        deviceid = conf["deviceid"]
        self._attr_unique_id = "mex" + deviceid + unique_id_suffix
        self._state = None
        self._should_poll = True

        self._last_update = None
        self._last_update_successful = None
        self._medium = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, deviceid)},
            name=conf.get("DeviceName", "Ecofrog " + str(deviceid)),
            # config_entries=[self.config_entry.entry_id],
            manufacturer="E-Sensorix",
            model="Mex",
        )

        if self.coordinator.data:
            self._state = self._get_value()
            _LOGGER.debug("Sensor %s init-time value %s", self._attr_name, self._state)
        _LOGGER.debug("Sensor %s initialised", self._attr_unique_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        value = self._get_value()
        _LOGGER.debug("Sensor %s value set to %s", self._attr_name, value)
        self._state = value
        self.async_write_ha_state()
        self._should_poll = False

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        attributes = {}

        if (datum := self.coordinator.data[self.idx].get("last_update")) is not None:
            attributes["last_update"] = datum

        if (
            datum := self.coordinator.data[self.idx].get("last_update_successful")
        ) is not None:
            attributes["last_update_successful"] = datum

        if (datum := self.coordinator.data[self.idx].get("Medium")) is not None:
            attributes["medium"] = datum

        _LOGGER.debug("Sensor %s extra attrs %s", self._attr_name, attributes)
        return attributes


class TankVolume(MexSensor):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_name = "Volume"
    _attr_native_unit_of_measurement = VOLUME_LITERS
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator, config_entry, idx):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, config_entry, idx, "Volume", "_volume")

    def _get_value(self):
        return int(self.coordinator.data[self.idx]["ActualVolume"])

    @property
    def icon(self):
        try:
            value = int(self.coordinator.data[self.idx].get("ActualVolumePercent"))
        except (KeyError, ValueError, TypeError):
            value = None

        if value is None:
            return "mdi:storage-tank"
        elif value >= 85:
            return "mdi:gauge-full"
        elif value >= 30:
            return "mdi:gauge"
        elif value >= 15:
            return "mdi:gauge-low"
        else:
            return "mdi:gauge-empty"


class MaxTankVolume(MexSensor):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_name = "Max Volume"
    _attr_native_unit_of_measurement = VOLUME_LITERS
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_icon = "mdi:gauge-full"

    def __init__(self, coordinator, config_entry, idx):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, config_entry, idx, "Max Volume", "_maxvolume")

    def _get_value(self):
        return int(self.coordinator.data[self.idx]["MaxVolume"])


class TankPercent(MexSensor):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_name = "Percent Full"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.VOLUME

    def __init__(self, coordinator, config_entry, idx):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, config_entry, idx, "Full", "_full")

    def _get_value(self):
        return int(self.coordinator.data[self.idx]["ActualVolumePercent"])

    @property
    def icon(self):
        value = self._state
        if value is None:
            return "mdi:storage-tank"
        elif value >= 85:
            return "mdi:gauge-full"
        elif value >= 30:
            return "mdi:gauge"
        elif value >= 15:
            return "mdi:gauge-low"
        else:
            return "mdi:gauge-empty"


class Battery(MexSensor):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_name = "Battery"
    _attr_native_unit_of_measurement = ELECTRIC_POTENTIAL_VOLT
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_icon = "mdi:battery"

    def __init__(self, coordinator, config_entry, idx):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, config_entry, idx, "Battery", "_battery")

    def _get_value(self):
        return float(self.coordinator.data[self.idx]["Battery"])


class Temperature(MexSensor):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_name = "Temperature"
    _attr_native_unit_of_measurement = TEMP_FAHRENHEIT
    _attr_device_class = SensorDeviceClass.TEMPERATURE

    def __init__(self, coordinator, config_entry, idx):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, config_entry, idx, "Temperature", "_temperature")

    def _get_value(self):
        return int(self.coordinator.data[self.idx]["Temperature"])


# End of file.
