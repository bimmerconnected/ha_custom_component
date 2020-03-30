"""Support for BMW notifications."""
import logging

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TARGET,
    ATTR_TITLE,
    ATTR_TITLE_DEFAULT,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)

from . import DOMAIN as BMW_DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_service(hass, config, discovery_info=None):
    """Get the BMW notification service."""
    accounts = hass.data[BMW_DOMAIN]
    _LOGGER.error("Found BMW accounts: %s", ", ".join([a.name for a in accounts]))
    #TODO the above logger is set to error to see the message in the log easily -> change to debug
    for account in accounts:
        for vehicle in account.account.vehicles:
            return BMWNotificationService(account, vehicle)


class BMWNotificationService(BaseNotificationService):
    """Send Notifications to BMW."""

    def __init__(self, name, vehicle):
        """Set up the notification service."""
        _LOGGER.error("Init of BMWNotificationService setup") # TODO
        self.name = name
        self._vehicle = vehicle
        self.targets = {vehicle.name: vehicle}

    def send_message(self, message="", **kwargs):
        """Send the message to the car."""
        _LOGGER.error("Sending message to %s", self._vehicle.name)
        #TODO the above logger is set to error to see the message in the log easily -> change to debug

        # Extract params from data dict
        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)

        # TODO
        self._vehicle.remote_services.trigger_send_message({"text": message, "subject": title})
