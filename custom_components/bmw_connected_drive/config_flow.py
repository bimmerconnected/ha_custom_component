"""Config flow for BMW ConnectedDrive integration."""
from __future__ import annotations

from typing import Any

from bimmer_connected.api.authentication import MyBMWAuthentication
from bimmer_connected.api.regions import get_region_from_name
from httpx import HTTPError
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_REGION, CONF_SOURCE, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN
from .const import CONF_ALLOWED_REGIONS, CONF_READ_ONLY, CONF_REFRESH_TOKEN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_REGION): vol.In(CONF_ALLOWED_REGIONS),
    }
)


async def validate_input(
    hass: core.HomeAssistant, data: dict[str, Any]
) -> dict[str, str]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    auth = MyBMWAuthentication(
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        get_region_from_name(data[CONF_REGION]),
    )

    try:
        await auth.login()
    except HTTPError as ex:
        raise CannotConnect from ex

    # Return info that you want to store in the config entry.
    retval = {"title": f"{data[CONF_USERNAME]}{data.get(CONF_SOURCE, '')}"}
    if auth.refresh_token:
        retval[CONF_REFRESH_TOKEN] = auth.refresh_token
    return retval


class BMWConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MyBMW."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            unique_id = f"{user_input[CONF_REGION]}-{user_input[CONF_USERNAME]}"

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            info = None
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"

            if info:
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        **user_input,
                        CONF_REFRESH_TOKEN: info.get(CONF_REFRESH_TOKEN),
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BMWOptionsFlow:
        """Return a MyBMW option flow."""
        return BMWOptionsFlow(config_entry)


class BMWOptionsFlow(config_entries.OptionsFlowWithConfigEntry):
    """Handle a option flow for MyBMW."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_account_options()

    async def async_step_account_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Manually update & reload the config entry after options change.
            # Required as each successful login will store the latest refresh_token
            # using async_update_entry, which would otherwise trigger a full reload
            # if the options would be refreshed using a listener.
            changed = self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=user_input,
            )
            if changed:
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="account_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_READ_ONLY,
                        default=self.config_entry.options.get(CONF_READ_ONLY, False),
                    ): bool,
                }
            ),
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
