"""Config flow for BMW ConnectedDrive integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from . import BMWConnectedDriveDataUpdateCoordinator
from .const import DOMAIN, CONF_ALLOWED_REGIONS, CONF_READ_ONLY, CONF_REGION

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_REGION): vol.In(CONF_ALLOWED_REGIONS),
        vol.Optional(CONF_READ_ONLY, default=False): bool,
    }
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    entry = config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title=data[CONF_USERNAME],
        data=data,
        source=config_entries.SOURCE_IGNORE,
        connection_class=config_entries.CONN_CLASS_CLOUD_POLL,
        system_options={},
    )

    hub = BMWConnectedDriveDataUpdateCoordinator(hass, entry)
    _LOGGER.debug("Hub added")
    if not await hub.async_connect(
        data[CONF_USERNAME], data[CONF_PASSWORD], data[CONF_REGION]
    ):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": data[CONF_USERNAME]}


class BMWConnectedDriveConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BMW ConnectedDrive."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            unique_id = f"{user_input[CONF_REGION]}-{user_input[CONF_USERNAME]}"

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except (InvalidAuth, OSError):
                errors["base"] = "invalid_auth"
            # except Exception:  # pylint: disable=broad-except
            #     _LOGGER.exception("Unexpected exception")
            #     errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
