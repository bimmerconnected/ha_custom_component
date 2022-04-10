"""Reads vehicle status from MyBMW portal."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, cast

from bimmer_connected.vehicle import MyBMWVehicle
from bimmer_connected.vehicle.doors_windows import LockState
from bimmer_connected.vehicle.fuel_and_battery import ChargingState
from bimmer_connected.vehicle.reports import ConditionBasedService

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.unit_system import UnitSystem

from . import BMWBaseEntity
from .const import DOMAIN, UNIT_MAP
from .coordinator import BMWDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _are_doors_closed(
    vehicle: MyBMWVehicle, extra_attributes: dict[str, Any], *args: Any
) -> bool:
    # device class opening: On means open, Off means closed
    _LOGGER.debug("Status of lid: %s", vehicle.doors_and_windows.all_lids_closed)
    for lid in vehicle.doors_and_windows.lids:
        extra_attributes[lid.name] = lid.state.value
    return not vehicle.doors_and_windows.all_lids_closed


def _are_windows_closed(
    vehicle: MyBMWVehicle, extra_attributes: dict[str, Any], *args: Any
) -> bool:
    # device class opening: On means open, Off means closed
    for window in vehicle.doors_and_windows.windows:
        extra_attributes[window.name] = window.state.value
    return not vehicle.doors_and_windows.all_windows_closed


def _are_doors_locked(
    vehicle: MyBMWVehicle, extra_attributes: dict[str, Any], *args: Any
) -> bool:
    # device class lock: On means unlocked, Off means locked
    # Possible values: LOCKED, SECURED, SELECTIVE_LOCKED, UNLOCKED
    extra_attributes[
        "door_lock_state"
    ] = vehicle.doors_and_windows.door_lock_state.value
    extra_attributes["last_update_reason"] = vehicle.last_update_reason
    return vehicle.doors_and_windows.door_lock_state not in {
        LockState.LOCKED,
        LockState.SECURED,
    }


def _are_problems_detected(
    vehicle: MyBMWVehicle,
    extra_attributes: dict[str, Any],
    unit_system: UnitSystem,
) -> bool:
    # device class problem: On means problem detected, Off means no problem
    for report in vehicle.condition_based_services.messages:
        extra_attributes.update(_format_cbs_report(report, unit_system))
    return cast(bool, vehicle.condition_based_services.is_service_required)


def _check_control_messages(
    vehicle: MyBMWVehicle, extra_attributes: dict[str, Any], *args: Any
) -> bool:
    # device class problem: On means problem detected, Off means no problem
    check_control_messages = vehicle.check_control_messages
    has_check_control_messages = check_control_messages.has_check_control_messages
    if has_check_control_messages:
        cbs_list = [
            message.description_short for message in check_control_messages.messages
        ]
        extra_attributes["check_control_messages"] = cbs_list
    else:
        extra_attributes["check_control_messages"] = "OK"
    return cast(bool, vehicle.check_control_messages.has_check_control_messages)


def _is_vehicle_charging(
    vehicle: MyBMWVehicle, extra_attributes: dict[str, Any], *args: Any
) -> bool:
    # device class power: On means power detected, Off means no power
    extra_attributes["charging_status"] = vehicle.fuel_and_battery.charging_status.value
    return cast(
        bool, vehicle.fuel_and_battery.charging_status == ChargingState.CHARGING
    )


def _is_vehicle_plugged_in(
    vehicle: MyBMWVehicle, extra_attributes: dict[str, Any], *args: Any
) -> bool:
    # device class plug: On means device is plugged in,
    #                    Off means device is unplugged
    return cast(bool, vehicle.fuel_and_battery.is_charger_connected)


def _format_cbs_report(
    report: ConditionBasedService, unit_system: UnitSystem
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    service_type = report.service_type.lower().replace("_", " ")
    result[f"{service_type} status"] = report.state.value
    if report.due_date is not None:
        result[f"{service_type} date"] = report.due_date.strftime("%Y-%m-%d")
    if report.due_distance.value is not None:
        distance = round(
            unit_system.length(
                report.due_distance[0],
                UNIT_MAP.get(report.due_distance[1], report.due_distance[1]),
            )
        )
        result[f"{service_type} distance"] = f"{distance} {unit_system.length_unit}"
    return result


@dataclass
class BMWRequiredKeysMixin:
    """Mixin for required keys."""

    value_fn: Callable[[MyBMWVehicle, dict[str, Any], UnitSystem], bool]


@dataclass
class BMWBinarySensorEntityDescription(
    BinarySensorEntityDescription, BMWRequiredKeysMixin
):
    """Describes BMW binary_sensor entity."""


SENSOR_TYPES: tuple[BMWBinarySensorEntityDescription, ...] = (
    BMWBinarySensorEntityDescription(
        key="lids",
        name="Doors",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:car-door-lock",
        value_fn=_are_doors_closed,
    ),
    BMWBinarySensorEntityDescription(
        key="windows",
        name="Windows",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:car-door",
        value_fn=_are_windows_closed,
    ),
    BMWBinarySensorEntityDescription(
        key="door_lock_state",
        name="Door lock state",
        device_class=BinarySensorDeviceClass.LOCK,
        icon="mdi:car-key",
        value_fn=_are_doors_locked,
    ),
    BMWBinarySensorEntityDescription(
        key="condition_based_services",
        name="Condition based services",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:wrench",
        value_fn=_are_problems_detected,
    ),
    BMWBinarySensorEntityDescription(
        key="check_control_messages",
        name="Control messages",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:car-tire-alert",
        value_fn=_check_control_messages,
    ),
    # electric
    BMWBinarySensorEntityDescription(
        key="charging_status",
        name="Charging status",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        icon="mdi:ev-station",
        value_fn=_is_vehicle_charging,
    ),
    BMWBinarySensorEntityDescription(
        key="connection_status",
        name="Connection status",
        device_class=BinarySensorDeviceClass.PLUG,
        icon="mdi:car-electric",
        value_fn=_is_vehicle_plugged_in,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BMW binary sensors from config entry."""
    coordinator: BMWDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        BMWBinarySensor(coordinator, vehicle, description, hass.config.units)
        for vehicle in coordinator.account.vehicles
        for description in SENSOR_TYPES
        if description.key in vehicle.available_attributes
    ]
    async_add_entities(entities)


class BMWBinarySensor(BMWBaseEntity, BinarySensorEntity):
    """Representation of a BMW vehicle binary sensor."""

    entity_description: BMWBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: BMWDataUpdateCoordinator,
        vehicle: MyBMWVehicle,
        description: BMWBinarySensorEntityDescription,
        unit_system: UnitSystem,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, vehicle)
        self.entity_description = description
        self._unit_system = unit_system

        self._attr_name = f"{vehicle.name} {description.key}"
        self._attr_unique_id = f"{vehicle.vin}-{description.key}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        _LOGGER.debug("Updating binary sensors of %s", self.vehicle.name)
        result = self._attrs.copy()

        sensor_value = self.entity_description.value_fn(
            self.vehicle, result, self._unit_system
        )

        self._attr_extra_state_attributes = result

        return sensor_value
