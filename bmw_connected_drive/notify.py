"""Support for BMW notifications."""
import logging

from homeassistant.components.notify import (
    ATTR_TITLE,
    ATTR_TITLE_DEFAULT,
    BaseNotificationService,
)

from . import DOMAIN as BMW_DOMAIN
from .const import SUBJECT, TEXT

_LOGGER = logging.getLogger(__name__)


def get_service(hass, config, discovery_info=None):
    """Get the BMW notification service."""
    accounts = hass.data[BMW_DOMAIN]
    _LOGGER.error("Found BMW accounts: %s", ", ".join([a.name for a in accounts]))
    #TODO the above logger is set to error to see the message in the log easily -> change to debug
    for account in accounts:
        for vehicle in account.account.vehicles:
            return BMWNotificationService(vehicle)


class BMWNotificationService(BaseNotificationService):
    """Send Notifications to BMW."""

    def __init__(self, vehicle):
        """Set up the notification service."""
        self._vehicle = vehicle
        self.targets = {self._vehicle.name: self._vehicle}

    def send_message(self, message="", **kwargs):
        """Send the message to the car."""
        _LOGGER.error("Sending message to %s", self._vehicle.name)
        #TODO the above logger is set to error to see the message in the log easily -> change to debug

        # Extract params from data dict
        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        self._vehicle.remote_services.trigger_send_message({TEXT: message, SUBJECT: title})
