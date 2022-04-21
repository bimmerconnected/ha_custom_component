"""Coordinator for BMW."""
from __future__ import annotations

from datetime import timedelta
import logging

import async_timeout
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import get_region_from_name
from bimmer_connected.vehicle.models import GPSPosition

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=300)
_LOGGER = logging.getLogger(__name__)


class BMWDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching BMW data."""

    account: MyBMWAccount

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
        self.account = MyBMWAccount(
            username,
            password,
            get_region_from_name(region),
            observer_position=GPSPosition(hass.config.latitude, hass.config.longitude),
        )
        self.read_only = read_only

        self.async_config_entry_first_refresh()

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
                await self.account.get_vehicles()
        except OSError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def notify_listeners(self) -> None:
        """Notify all listeners to refresh HA state machine."""
        for update_callback in self._listeners:
            update_callback()
