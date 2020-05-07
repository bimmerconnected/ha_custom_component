"""The BMW Connected Drive integration."""
import asyncio
from datetime import timedelta
import json
import logging

import async_timeout
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name
from bimmer_connected.vehicle import ConnectedDriveVehicle
import voluptuous as vol

from homeassistant.components.lock import DOMAIN as LOCK
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ICON,
    ATTR_ID,
    ATTR_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

# from .account import BMWConnectedDriveAccount
from .const import CONF_ALLOWED_REGIONS, CONF_READ_ONLY, CONF_REGION, DOMAIN

_LOGGER = logging.getLogger(__name__)


CONFIG = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_REGION): vol.In(CONF_ALLOWED_REGIONS),
        vol.Optional(CONF_READ_ONLY, default=False): bool,
    }
)

# PLATFORMS = ["binary_sensor", "device_tracker", "lock", "notify", "sensor"]
PLATFORMS = ["binary_sensor", "lock", "sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the BMW Connected Drive component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up BMW Connected Drive from a config entry."""
    coordinator = BMWConnectedDriveDataUpdateCoordinator(hass, entry,)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class BMWConnectedDriveDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to hold Atag data."""

    def __init__(self, hass, entry):
        """Initialize."""
        self.account = None
        self.read_only = entry.data[CONF_READ_ONLY]
        self._entry = entry
        self._hass = hass

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=5)
        )

    async def _async_update_data(self):
        """Update data via library."""
        with async_timeout.timeout(20):
            try:
                if not self.account:
                    await self.async_connect(
                        self._entry.data[CONF_USERNAME],
                        self._entry.data[CONF_PASSWORD],
                        self._entry.data[CONF_REGION],
                    )

                await self._hass.async_add_executor_job(
                    self.account.update_vehicle_states
                )
            except Exception as error:
                raise UpdateFailed(error)

        return self.account

    async def async_connect(self, username, password, region) -> bool:
        """Test if we can authenticate with BMW Connected Drive."""
        await self._hass.async_add_executor_job(
            self.connect, username, password, region
        )
        return True

    def connect(self, username, password, region):
        """Get the BMW Connected Drive account."""
        self.account = ConnectedDriveAccount(
            username, password, get_region_from_name(region)
        )

    async def async_add_executor_job(self, target, *args):
        """Add an executor job from within the event loop."""

        self._hass.async_add_executor_job(target, *args)
        return True


class BMWConnectedDriveVehicleEntity(Entity):
    """Defines a base BMWConnectedDriveVehicle entity."""

    def __init__(
        self,
        coordinator: BMWConnectedDriveDataUpdateCoordinator,
        vehicle: ConnectedDriveVehicle,
        bmw_entity_type: dict,
    ) -> None:
        """Initialize the BMWConnectedDriveVehicle entity."""
        self.coordinator = coordinator
        self.vehicle = vehicle

        self._id = bmw_entity_type[ATTR_ID]  # attribute
        self._unique_id = f"{vehicle.vin}-{self._id}"

        self._name = f"{vehicle.name} {bmw_entity_type[ATTR_NAME].title()}"
        self._unique_id = f"{vehicle.vin}-{self._id}"
        self._device_class = bmw_entity_type.get(ATTR_DEVICE_CLASS, None)
        self._icon = bmw_entity_type.get(ATTR_ICON, None)
        self._state = None

    @property
    def device_info(self) -> dict:
        """Return info for device registry."""
        return {
            "identifiers": {(DOMAIN, self.vehicle.vin)},
            "name": self.vehicle.name,
            "model": self.vehicle.name,
            "manufacturer": self.vehicle.attributes.get("brand"),
        }

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return the polling requirement of the entity."""
        return False

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    @property
    def state(self):
        """Return the state of the sensor.

        The return type of this call depends on the attribute that
        is configured.
        """
        return self._state

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self._unique_id

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update Atag entity."""
        await self.coordinator.async_request_refresh()
