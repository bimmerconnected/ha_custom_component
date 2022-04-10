"""Device tracker for MyBMW vehicles."""
from __future__ import annotations

import logging
from typing import Literal

from bimmer_connected.vehicle import MyBMWVehicle

from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BMWBaseEntity
from .const import ATTR_DIRECTION, DOMAIN
from .coordinator import BMWDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MyBMW tracker from config entry."""
    coordinator: BMWDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[BMWDeviceTracker] = []

    for vehicle in coordinator.account.vehicles:
        entities.append(BMWDeviceTracker(coordinator, vehicle))
        if not vehicle.is_vehicle_tracking_enabled:
            _LOGGER.info(
                "Tracking is (currently) disabled for vehicle %s (%s), defaulting to unknown",
                vehicle.name,
                vehicle.vin,
            )
    async_add_entities(entities)


class BMWDeviceTracker(BMWBaseEntity, TrackerEntity):
    """MyBMW device tracker."""

    _attr_force_update = False
    _attr_icon = "mdi:car"

    def __init__(
        self,
        coordinator: BMWDataUpdateCoordinator,
        vehicle: MyBMWVehicle,
    ) -> None:
        """Initialize the Tracker."""
        super().__init__(coordinator, vehicle)

        self._attr_unique_id = vehicle.vin
        self._attr_name = vehicle.name

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        return {ATTR_DIRECTION: self.vehicle.vehicle_location.heading}

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return (
            self.vehicle.vehicle_location.location[0]
            if self.vehicle.is_vehicle_tracking_enabled
            else None
        )

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return (
            self.vehicle.vehicle_location.location[1]
            if self.vehicle.is_vehicle_tracking_enabled
            else None
        )

    @property
    def source_type(self) -> Literal["gps"]:
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_GPS
