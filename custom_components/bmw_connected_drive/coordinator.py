"""Coordinator for BMW."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, cast

import async_timeout
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name
from bimmer_connected.vehicle import ConnectedDriveVehicle

from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import ATTR_VIN, DOMAIN, SERVICE_MAP

SCAN_INTERVAL = timedelta(seconds=300)
_LOGGER = logging.getLogger(__name__)


class BMWDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching BMW data."""

    account: ConnectedDriveAccount

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        username: str,
        password: str,
        region: str,
        read_only: bool = False,
    ) -> None:
        """Initialize account-wide BMW data updater."""
        # Storing username & password in coordinator is needed until a new library version
        # that does not do blocking IO on init.
        self._username = username
        self._password = password
        self._region = get_region_from_name(region)

        self.account = None
        self.read_only = read_only

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{username}",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> None:
        """Fetch data from BMW."""
        try:
            async with async_timeout.timeout(15):
                if isinstance(self.account, ConnectedDriveAccount):
                    # pylint: disable=protected-access
                    await self.hass.async_add_executor_job(self.account._get_vehicles)
                else:
                    self.account = await self.hass.async_add_executor_job(
                        ConnectedDriveAccount,
                        self._username,
                        self._password,
                        self._region,
                    )
        except OSError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    # Deprecated and will be removed in 2022.4 when only buttons are supported.
    # Required to call `async_request_refresh` from a service call with arguments.
    async def async_request_refresh(self, *args: Any, **kwargs: Any) -> None:
        """Request a refresh.

        Refresh will wait a bit to see if it can batch them.
        Allows to be called from a service call.
        """
        await super().async_request_refresh()

    # Deprecated and will be removed in 2022.4 when only buttons are supported.
    async def async_execute_service(self, call: ServiceCall) -> None:
        """Execute a service for a vehicle."""
        _LOGGER.warning(
            "BMW Connected Drive services are deprecated. Please migrate to the dedicated button entities. "
            "See https://www.home-assistant.io/integrations/bmw_connected_drive/#buttons for details"
        )

        vin: str | None = call.data.get(ATTR_VIN)
        device_id: str | None = call.data.get(CONF_DEVICE_ID)

        coordinator: BMWDataUpdateCoordinator
        vehicle: ConnectedDriveVehicle | None = None

        if not vin and device_id:
            # If vin is None, device_id must be set (given by SERVICE_SCHEMA)
            if not (
                device := device_registry.async_get(self.hass).async_get(device_id)
            ):
                _LOGGER.error("Could not find a device for id: %s", device_id)
                return
            vin = next(iter(device.identifiers))[1]
        else:
            vin = cast(str, vin)

        # Search through all coordinators for vehicle
        # Double check for read_only accounts as another account could create the services
        entry_coordinator: BMWDataUpdateCoordinator
        for entry_coordinator in self.hass.data[DOMAIN].values():
            if (
                isinstance(entry_coordinator, DataUpdateCoordinator)
                and not entry_coordinator.read_only
            ):
                account: ConnectedDriveAccount = entry_coordinator.account
                if vehicle := account.get_vehicle(vin):
                    coordinator = entry_coordinator
                    break
        if not vehicle:
            _LOGGER.error("Could not find a vehicle for VIN %s", vin)
            return
        function_name = SERVICE_MAP[call.service]
        function_call = getattr(vehicle.remote_services, function_name)
        await self.hass.async_add_executor_job(function_call)

        if call.service in [
            "find_vehicle",
            "activate_air_conditioning",
            "deactivate_air_conditioning",
        ]:
            await coordinator.async_request_refresh()
