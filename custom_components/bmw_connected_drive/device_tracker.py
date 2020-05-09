"""Device tracker for BMW Connected Drive vehicles."""
import logging

from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.components.device_tracker.config_entry import TrackerEntity

from . import DOMAIN as BMW_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the BMW ConnectedDrive tracker from config entry."""
    account = hass.data[BMW_DOMAIN][config_entry.entry_id]
    devices = []

    for vehicle in account.account.vehicles:
        if vehicle.state.is_vehicle_tracking_enabled:
            devices.append(BMWDeviceTracker(account, vehicle))
        else:
            _LOGGER.info(
                "Tracking is disabled for vehicle %s (%s)", vehicle.name, vehicle.vin
            )
    async_add_entities(devices, True)

    #    if not self.vehicle.state.is_vehicle_tracking_enabled:
    #         _LOGGER.debug("Tracking is disabled for vehicle %s", dev_id)
    #         return

    # # if not account.read_only:
    # for vehicle in account.account.vehicles:
    #     device = BMWLock(account, vehicle, "lock", "BMW lock")
    #     devices.append(device)
    # async_add_entities(devices, True)


# def setup_scanner(hass, config, see, discovery_info=None):
#     """Set up the BMW tracker."""
#     accounts = hass.data[BMW_DOMAIN]
#     _LOGGER.debug("Found BMW accounts: %s", ", ".join([a.name for a in accounts]))
#     for account in accounts:
#         for vehicle in account.account.vehicles:
#             tracker = BMWDeviceTracker(see, vehicle)
#             account.add_update_listener(tracker.update)
#             tracker.update()
#     return True


class BMWDeviceTracker(TrackerEntity):
    """BMW Connected Drive device tracker."""

    def __init__(self, account, vehicle):
        """Initialize the Tracker."""
        self._account = account
        self._vehicle = vehicle
        self._unique_id = vehicle.vin
        self._location = vehicle.state.gps_position
        self._name = vehicle.name

    @property
    def latitude(self):
        """Return latitude value of the device."""
        return self._location[0]

    @property
    def longitude(self):
        """Return longitude value of the device."""
        return self._location[1]

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    @property
    def device_info(self) -> dict:
        """Return info for device registry."""
        return {
            "identifiers": {(BMW_DOMAIN, self._vehicle.vin)},
            "name": f'{self._vehicle.attributes.get("brand")} {self._vehicle.name}',
            "model": self._vehicle.name,
            "manufacturer": self._vehicle.attributes.get("brand"),
        }

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_GPS

    @property
    def icon(self):
        return "mdi:car"

    def update_callback(self):
        """Schedule a state update."""
        self.schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        """Add callback after being added to hass.

        Show latest data after startup.
        """
        self._account.add_update_listener(self.update_callback)
