"""Support for reading vehicle status from BMW connected drive portal."""
import logging

from bimmer_connected.state import ChargingState
from bimmer_connected.vehicle import ConnectedDriveVehicle


from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_UNIT_SYSTEM_IMPERIAL,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    TIME_HOURS,
    UNIT_PERCENTAGE,
    VOLUME_GALLONS,
    VOLUME_LITERS,
    ATTR_DEVICE_CLASS,
    ATTR_ICON,
    ATTR_ID,
    ATTR_NAME,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level

from . import BMWConnectedDriveDataUpdateCoordinator, BMWConnectedDriveVehicleEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_TO_HA_METRIC = {
    "mileage": ["mdi:speedometer", LENGTH_KILOMETERS],
    "remaining_range_total": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "remaining_range_electric": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "remaining_range_fuel": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "max_range_electric": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "remaining_fuel": ["mdi:gas-station", VOLUME_LITERS],
    "charging_time_remaining": ["mdi:update", TIME_HOURS],
    "charging_status": ["mdi:battery-charging", None],
    # No icon as this is dealt with directly as a special case in icon()
    "charging_level_hv": [None, UNIT_PERCENTAGE],
}

ATTR_TO_HA_IMPERIAL = {
    "mileage": ["mdi:speedometer", LENGTH_MILES],
    "remaining_range_total": ["mdi:map-marker-distance", LENGTH_MILES],
    "remaining_range_electric": ["mdi:map-marker-distance", LENGTH_MILES],
    "remaining_range_fuel": ["mdi:map-marker-distance", LENGTH_MILES],
    "max_range_electric": ["mdi:map-marker-distance", LENGTH_MILES],
    "remaining_fuel": ["mdi:gas-station", VOLUME_GALLONS],
    "charging_time_remaining": ["mdi:update", TIME_HOURS],
    "charging_status": ["mdi:battery-charging", None],
    # No icon as this is dealt with directly as a special case in icon()
    "charging_level_hv": [None, UNIT_PERCENTAGE],
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the BMW ConnectedDrive  sensors from config entry."""
    if hass.config.units.name == CONF_UNIT_SYSTEM_IMPERIAL:
        sensor_info = ATTR_TO_HA_IMPERIAL
    else:
        sensor_info = ATTR_TO_HA_METRIC

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.info(
        "%s %s: vehicles: %s",
        DOMAIN,
        "sensor",
        ", ".join([v.name for v in coordinator.account.vehicles]),
    )

    entities = []

    for vehicle in coordinator.account.vehicles:
        _LOGGER.info("drive_train_attributes: %s", ", ".join(vehicle.drive_train_attributes))
        for attribute_name in vehicle.drive_train_attributes:
            _LOGGER.info("available_attributes: %s", ", ".join(vehicle.available_attributes))
            if attribute_name in vehicle.available_attributes:
                sensor = BMWConnectedDriveSensor(
                    coordinator,
                    vehicle,
                    {
                        ATTR_ID: attribute_name,
                        ATTR_NAME: attribute_name,
                        ATTR_ICON: sensor_info[attribute_name],
                        "sensor_info": sensor_info,
                    },
                )
                entities.append(sensor)
    _LOGGER.info("entities to be added: %d", len(entities))
    async_add_entities(entities, True)

    # for account in accounts:
    #     for vehicle in account.account.vehicles:
    #         for attribute_name in vehicle.drive_train_attributes:
    #             if attribute_name in vehicle.available_attributes:
    #                 device = BMWConnectedDriveSensor(
    #                     account, vehicle, attribute_name, attribute_info
    #                 )
    #                 devices.append(device)
    # add_entities(devices, True)


class BMWConnectedDriveSensor(BMWConnectedDriveVehicleEntity, Entity):
    """Representation of a BMW vehicle sensor."""

    def __init__(
        self,
        coordinator: BMWConnectedDriveDataUpdateCoordinator,
        vehicle: ConnectedDriveVehicle,
        bmw_entity_type: dict,
    ) -> None:
        """Initialize the BMWConnectedDriveSensor entity."""
        _LOGGER.info("Initializing BMWConnectedDriveSensor for %s", vehicle.name)
        self._sensor_info = bmw_entity_type["sensor_info"]

        super().__init__(coordinator, vehicle, bmw_entity_type)

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self._id == "charging_level_hv":
            vehicle_state = self.vehicle.state
            charging_state = vehicle_state.charging_status in [ChargingState.CHARGING]

            return icon_for_battery_level(
                battery_level=vehicle_state.charging_level_hv, charging=charging_state
            )
        icon, _ = self._sensor_info.get(self._id, [None, None])
        return icon

    @property
    def unit_of_measurement(self) -> str:
        """Get the unit of measurement."""
        _, unit = self._sensor_info.get(self._id, [None, None])
        return unit

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {"car": self.vehicle.name}

    def update(self) -> None:
        """Read new state data from the library."""
        _LOGGER.debug("Updating %s", self.vehicle.name)
        vehicle_state = self.vehicle.state
        if self._id == "charging_status":
            self._state = getattr(vehicle_state, self._id).value
        elif self.unit_of_measurement == VOLUME_GALLONS:
            value = getattr(vehicle_state, self._id)
            value_converted = self.hass.config.units.volume(value, VOLUME_LITERS)
            self._state = round(value_converted)
        elif self.unit_of_measurement == LENGTH_MILES:
            value = getattr(vehicle_state, self._id)
            value_converted = self.hass.config.units.length(value, LENGTH_KILOMETERS)
            self._state = round(value_converted)
        else:
            self._state = getattr(vehicle_state, self._id)

    def update_callback(self):
        """Schedule a state update."""
        self.schedule_update_ha_state(True)