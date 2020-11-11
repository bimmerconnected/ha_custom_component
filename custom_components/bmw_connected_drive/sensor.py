"""Support for reading vehicle status from BMW connected drive portal."""
import logging

from bimmer_connected.state import ChargingState

from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_UNIT_SYSTEM_IMPERIAL,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    PERCENTAGE,
    TIME_HOURS,
    TIME_MINUTES,
    VOLUME_GALLONS,
    VOLUME_LITERS,
    ENERGY_WATT_HOUR,
    ENERGY_KILO_WATT_HOUR,
    MASS_KILOGRAMS,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level

from . import DOMAIN as BMW_DOMAIN
from .const import (
    ATTRIBUTION,
    CONF_LAST_TRIP,
    CONF_ALL_TRIPS,
    CONF_CHARGING_PROFILE,
    CONF_DESTINATIONS,
)

_LOGGER = logging.getLogger(__name__)

ATTR_TO_HA_METRIC = {
    "mileage": ["mdi:speedometer", LENGTH_KILOMETERS],
    "remaining_range_total": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "remaining_range_electric": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "remaining_range_fuel": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "max_range_electric": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "remaining_fuel": ["mdi:gas-station", VOLUME_LITERS],
    # LastTrip attributes
    "avgCombinedConsumption": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "avgElectricConsumption": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "avgRecuperation": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_KILOMETERS}"],
    "electricDistance": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "savedFuel": ["mdi:fuel", VOLUME_LITERS],
    "totalDistance": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    # AllTrips attributes
    "chargecycleRange": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "totalElectricDistance": ["mdi:map-marker-distance", LENGTH_KILOMETERS],
    "totalSavedFuel": ["mdi:fuel", VOLUME_LITERS],
}

ATTR_TO_HA_IMPERIAL = {
    "mileage": ["mdi:speedometer", LENGTH_MILES],
    "remaining_range_total": ["mdi:map-marker-distance", LENGTH_MILES],
    "remaining_range_electric": ["mdi:map-marker-distance", LENGTH_MILES],
    "remaining_range_fuel": ["mdi:map-marker-distance", LENGTH_MILES],
    "max_range_electric": ["mdi:map-marker-distance", LENGTH_MILES],
    "remaining_fuel": ["mdi:gas-station", VOLUME_GALLONS],
    # LastTrip attributes
    "avgCombinedConsumption": ["mdi:flash", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "avgElectricConsumption": ["mdi:power-plug-outline", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "avgRecuperation": ["mdi:recycle-variant", f"{ENERGY_KILO_WATT_HOUR}/100{LENGTH_MILES}"],
    "electricDistance": ["mdi:map-marker-distance", LENGTH_MILES],
    "savedFuel": ["mdi:fuel", VOLUME_GALLONS],
    "totalDistance": ["mdi:map-marker-distance", LENGTH_MILES],
    # AllTrips attributes
    "chargecycleRange": ["mdi:map-marker-distance", LENGTH_MILES],
    "totalElectricDistance": ["mdi:map-marker-distance", LENGTH_MILES],
    "totalSavedFuel": ["mdi:fuel", VOLUME_GALLONS],
}

ATTR_TO_HA = {
    "charging_time_remaining": ["mdi:update", TIME_HOURS],
    "charging_status": ["mdi:battery-charging", None],
    # No icon as this is dealt with directly as a special case in icon()
    "charging_level_hv": [None, PERCENTAGE],
    # LastTrip attributes
    "date": ["mdi:calendar-blank", None],
    "duration": ["mdi:timer-outline", TIME_MINUTES],
    "electricDistanceRatio": ["mdi:percent-outline", PERCENTAGE],
    # AllTrips attributes
    "batterySizeMax": ["mdi:battery-charging-high", ENERGY_WATT_HOUR],
    "resetDate": ["mdi:calendar-blank", None],
    "savedCO2": ["mdi:tree-outline", MASS_KILOGRAMS],
    "savedCO2greenEnergy": ["mdi:tree-outline", MASS_KILOGRAMS],
    # ChargingProfile attributes
    "climatizationEnabled": ["mdi:snowflake", None],
    "preferredChargingWindow": ["mdi:dock-window", None],
    "timer1": ["mdi:av-timer", None],
    "timer2": ["mdi:av-timer", None],
    "timer3": ["mdi:av-timer", None],
    "overrideTimer": ["mdi:av-timer", None],
    # Destination attributes
    "Destination_xx": ["mdi:pin-outline", None],
}

ATTR_TO_HA_METRIC.update(ATTR_TO_HA)
ATTR_TO_HA_IMPERIAL.update(ATTR_TO_HA)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the BMW ConnectedDrive sensors from config entry."""

    if hass.config.units.name == CONF_UNIT_SYSTEM_IMPERIAL:
        attribute_info = ATTR_TO_HA_IMPERIAL
    else:
        attribute_info = ATTR_TO_HA_METRIC

    account = hass.data[BMW_DOMAIN][config_entry.entry_id]
    devices = []

    for vehicle in account.account.vehicles:
        for attribute_name in vehicle.drive_train_attributes:
            if attribute_name in vehicle.available_attributes:
                device = BMWConnectedDriveSensor(
                    account, vehicle, attribute_name, attribute_info
                )
                devices.append(device)
        for service in vehicle.state.attributes:
            # Add sensors for LastTrip, AllTrips & ChargingProfile
            if service in (CONF_LAST_TRIP, CONF_ALL_TRIPS, CONF_CHARGING_PROFILE):
                for attribute_name in vehicle.state.attributes[service]:
                    device = BMWConnectedDriveSensor(
                        account, vehicle, attribute_name, attribute_info, service
                    )
                    devices.append(device)
            # Add sensors for Destinations
            if service == CONF_DESTINATIONS:
                dest_nr = 1
                for destination in vehicle.state.attributes[service]:
                    attribute_name = f"Destination_{dest_nr}"
                    device = BMWConnectedDriveSensor(
                        account, vehicle, attribute_name, attribute_info, service
                    )
                    devices.append(device)
                    dest_nr += 1
    async_add_entities(devices, True)


class BMWConnectedDriveSensor(Entity):
    """Representation of a BMW vehicle sensor."""

    def __init__(self, account, vehicle, attribute: str, attribute_info, service=None):
        """Initialize BMW vehicle sensor."""
        self._vehicle = vehicle
        self._account = account
        self._attribute = attribute
        self._service = service
        self._state = None
        self._attribute_info = attribute_info
        if self._service:
            self._name = f"{self._vehicle.name} {self._service.lower()}_{self._attribute}"
            self._unique_id = f"{self._vehicle.vin}-{self._service.lower()}-{self._attribute}"
        else:
            self._name = f"{self._vehicle.name} {self._attribute}"
            self._unique_id = f"{self._vehicle.vin}-{self._attribute}"

    @property
    def device_info(self) -> dict:
        """Return info for device registry."""
        return {
            "identifiers": {(BMW_DOMAIN, self._vehicle.vin)},
            "sw_version": self._vehicle.vin,
            "name": f'{self._vehicle.attributes.get("brand")} {self._vehicle.name}',
            "model": self._vehicle.name,
            "manufacturer": self._vehicle.attributes.get("brand"),
        }

    @property
    def should_poll(self) -> bool:
        """Return False.

        Data update is triggered from BMWConnectedDriveEntity.
        """
        return False

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""

        if self._attribute == "charging_level_hv":
            vehicle_state = self._vehicle.state.vehicle_status
            charging_state = vehicle_state.charging_status in [ChargingState.CHARGING]
            return icon_for_battery_level(
                battery_level=vehicle_state.charging_level_hv, charging=charging_state
            )
        elif "Destination_" in self._attribute:
            icon, _ = self._attribute_info.get("Destination_xx", [None, None])
        else:
            icon, _ = self._attribute_info.get(self._attribute, [None, None])
        return icon

    @property
    def state(self):
        """Return the state of the sensor.

        The return type of this call depends on the attribute that
        is configured.
        """
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Get the unit of measurement."""
        _, unit = self._attribute_info.get(self._attribute, [None, None])
        return unit

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        vehicle_all_trips = self._vehicle.state.all_trips
        vehicle_charging_profile = self._vehicle.state.charging_profile
        vehicle_last_destinations = self._vehicle.state.last_destinations
        result = {
            "car": self._vehicle.name,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }
        if self._service == CONF_ALL_TRIPS:
            if self._attribute in ("avgCombinedConsumption", "avgElectricConsumption",
                "avgRecuperation", "chargecycleRange", "totalElectricDistance"):
                items = getattr(vehicle_all_trips, self._attribute)
                for item in items:
                    result[item] = items[item]
        elif self._service == CONF_CHARGING_PROFILE:
            if self._attribute in ("preferredChargingWindow", "timer1", "timer2",
                "timer3", "overrideTimer"):
                items = getattr(vehicle_charging_profile, self._attribute)
                for item in items:
                    result[item] = items[item]
        elif self._service == CONF_DESTINATIONS:
            destinations =  vehicle_last_destinations.attributes
            _, dest_nr = self._attribute.split('_')
            dest = destinations[int(dest_nr) - 1]
            for item in dest:
                result[item] = dest[item]
        return sorted(result.items())

    def update(self) -> None:
        """Read new state data from the library."""
        _LOGGER.debug("Updating %s", self._vehicle.name)
        vehicle_state = self._vehicle.state.vehicle_status
        vehicle_last_trip = self._vehicle.state.last_trip
        vehicle_all_trips = self._vehicle.state.all_trips
        vehicle_charging_profile = self._vehicle.state.charging_profile
        vehicle_last_destinations = self._vehicle.state.last_destinations
        if self._attribute == "charging_status":
            self._state = getattr(vehicle_state, self._attribute).value
        elif self.unit_of_measurement == VOLUME_GALLONS:
            value = getattr(vehicle_state, self._attribute)
            value_converted = self.hass.config.units.volume(value, VOLUME_LITERS)
            self._state = round(value_converted)
        elif self.unit_of_measurement == LENGTH_MILES:
            value = getattr(vehicle_state, self._attribute)
            value_converted = self.hass.config.units.length(value, LENGTH_KILOMETERS)
            self._state = round(value_converted)
        elif self._service is None:
            self._state = getattr(vehicle_state, self._attribute)
        elif self._service == CONF_LAST_TRIP:
            self._state = getattr(vehicle_last_trip, self._attribute)
        elif self._service == CONF_ALL_TRIPS:
            attr = getattr(vehicle_all_trips, self._attribute)
            if self._attribute in ("avgCombinedConsumption", "avgElectricConsumption",
                "avgRecuperation", "chargecycleRange"):
                self._state = attr['userAverage']
            elif self._attribute == "totalElectricDistance":
                self._state = attr['userTotal']
            else:
                self._state = attr
        elif self._service == CONF_CHARGING_PROFILE:
            attr = getattr(vehicle_charging_profile, self._attribute)
            if self._attribute == "preferredChargingWindow":
                self._state = f"{attr['startTime']}-{attr['endTime']}"
            elif self._attribute in ("timer1", "timer2", "timer3", "overrideTimer"):
                self._state = attr['timerEnabled']
            else:
                self._state = attr
        elif self._service == CONF_DESTINATIONS:
            _, dest_nr = self._attribute.split('_')
            destinations =  vehicle_last_destinations.attributes
            dest = destinations[int(dest_nr) - 1]
            self._state = dest['city']

    def update_callback(self):
        """Schedule a state update."""
        self.schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        """Add callback after being added to hass.

        Show latest data after startup.
        """
        self._account.add_update_listener(self.update_callback)
