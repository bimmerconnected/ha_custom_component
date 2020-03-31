"""Support for BMW notifications."""
import logging

from homeassistant.components.notify import (
    ATTR_TARGET,
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
ATTR_LOCATION_ATTRIBUTES = ["street", "city", "postalCode", "country"]
ATTR_SUBJECT = "subject"
ATTR_TEXT = "text"

_LOGGER = logging.getLogger(__name__)


def get_service(hass, config, discovery_info=None):
    """Get the BMW notification service."""
    accounts = hass.data[BMW_DOMAIN]
    _LOGGER.error("Found BMW accounts: %s", ", ".join([a.name for a in accounts])) # TODO
    #TODO the above logger is set to error to see the message in the log easily -> change to debug
    return BMWNotificationService(accounts) 


class BMWNotificationService(BaseNotificationService):
    """Send Notifications to BMW."""

    def __init__(self, accounts):
        """Set up the notification service."""
        # self.targets = {v.name: v for v in account.account.vehicles}
        self.targets = {}
        for account in accounts:
            self.targets.update({"{}_{}".format(account.name, v.name): v for v in account.account.vehicles})

    def send_message(self, message=None, **kwargs):
        """Send the message to the car."""

        for _vehicle in kwargs[ATTR_TARGET]:
            _LOGGER.error("Sending message to %s", _vehicle.name) # TODO
            #TODO the above logger is set to error to see the message in the log easily -> change to debug

            # Extract params from data dict
            title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
            data = kwargs.get(ATTR_DATA)

            # Check if message is a POI
            if data is not None and ATTR_LOCATION in data:
                location_dict = {
                        ATTR_LAT: data[ATTR_LOCATION][ATTR_LATITUDE],
                        ATTR_LON: data[ATTR_LOCATION][ATTR_LONGITUDE],
                        ATTR_NAME: message,
                    }
                # Update dictionary with additional attributes if available
                location_dict.update({k: v for k, v in data[ATTR_LOCATION].items() if k in ATTR_LOCATION_ATTRIBUTES})

                _vehicle.remote_services.trigger_send_poi(
                    location_dict
                )
            else:
                _vehicle.remote_services.trigger_send_message(
                    {
                        ATTR_TEXT: message,
                        ATTR_SUBJECT: title,
                    }
                )
