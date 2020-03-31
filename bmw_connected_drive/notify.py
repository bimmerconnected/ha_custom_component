"""Support for BMW notifications."""
import logging

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TITLE,
    ATTR_TITLE_DEFAULT,
    BaseNotificationService,
)
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LOCATION,
    ATTR_LONGITUDE,
    ATTR_NAME,
)

from . import DOMAIN as BMW_DOMAIN

ATTR_LAT = "lat"
ATTR_LON = "lon"
ATTR_SUBJECT = "subject"
ATTR_TEXT = "text"

_LOGGER = logging.getLogger(__name__)


def get_service(hass, config, discovery_info=None):
    """Get the BMW notification service."""
    accounts = hass.data[BMW_DOMAIN]
    _LOGGER.error("Found BMW accounts: %s", ", ".join([a.name for a in accounts])) # TODO
    #TODO the above logger is set to error to see the message in the log easily -> change to debug
    for account in accounts:
        for vehicle in account.account.vehicles:
            return BMWNotificationService(vehicle) # TODO


class BMWNotificationService(BaseNotificationService):
    """Send Notifications to BMW."""

    def __init__(self, vehicle):
        """Set up the notification service."""
        self._vehicle = vehicle
        self.targets = {self._vehicle.name: self._vehicle} # TODO

    def send_message(self, message="", **kwargs):
        """Send the message to the car."""
        _LOGGER.error("Sending message to %s", self._vehicle.name) # TODO
        #TODO the above logger is set to error to see the message in the log easily -> change to debug

        # Extract params from data dict
        data = kwargs.get(ATTR_DATA)
        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)

        # Check if message is a POI
        if data is not None and ATTR_LOCATION in data:
            self._vehicle.remote_services.trigger_send_poi(
                {
                    ATTR_LAT: data[ATTR_LOCATION].get(ATTR_LATITUDE),
                    ATTR_LON: data[ATTR_LOCATION].get(ATTR_LONGITUDE),
                    ATTR_NAME: message,
                }
            )
        else:
            self._vehicle.remote_services.trigger_send_message(
                {
                    ATTR_TEXT: message,
                    ATTR_SUBJECT: title,
                }
            )
