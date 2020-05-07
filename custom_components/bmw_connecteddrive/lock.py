"""Support for BMW car locks with BMW ConnectedDrive."""
import logging

from bimmer_connected.state import LockState
from bimmer_connected.vehicle import ConnectedDriveVehicle

from homeassistant.components.lock import DOMAIN as LOCK, LockDevice as LockEntity
from homeassistant.const import ATTR_ID, ATTR_NAME, STATE_LOCKED, STATE_UNLOCKED

from . import BMWConnectedDriveDataUpdateCoordinator, BMWConnectedDriveVehicleEntity
from .const import DOMAIN

# from .const import ATTRIBUTION

DOOR_LOCK_STATE = "door_lock_state"
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the BMW Connected Drive lock from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    if not coordinator.read_only:
        for vehicle in coordinator.account.vehicles:
            async_add_entities(
                [
                    BMWConnectedDriveLock(
                        coordinator, vehicle, {ATTR_ID: LOCK, ATTR_NAME: LOCK,},
                    )
                ], True
            )


class BMWConnectedDriveLock(BMWConnectedDriveVehicleEntity, LockEntity):
    """Representation of a BMW vehicle lock."""

    def __init__(
        self,
        coordinator: BMWConnectedDriveDataUpdateCoordinator,
        vehicle: ConnectedDriveVehicle,
        bmw_entity_type: dict,
    ) -> None:
        """Initialize the BMWConnectedDriveLock entity."""
        self.door_lock_state_available = DOOR_LOCK_STATE in vehicle.available_attributes

        super().__init__(coordinator, vehicle, bmw_entity_type)

    @property
    def device_state_attributes(self):
        """Return the state attributes of the lock."""
        vehicle_state = self.vehicle.state
        result = {"car": self.vehicle.name}
        if self.door_lock_state_available:
            result["door_lock_state"] = vehicle_state.door_lock_state.value
            result["last_update_reason"] = vehicle_state.last_update_reason
        return result

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self._state == STATE_LOCKED

    async def async_lock(self, **kwargs):
        await self.coordinator.async_add_executor_job(self.lock)
        return True

    def lock(self, **kwargs):
        """Lock the car."""
        _LOGGER.debug("%s: locking doors", self.vehicle.name)
        # Optimistic state set here because it takes some time before the
        # update callback response
        self._state = STATE_LOCKED
        self.async_update_ha_state()
        self.vehicle.remote_services.trigger_remote_door_lock()

    async def async_unlock(self, **kwargs):
        await self.coordinator.async_add_executor_job(self.unlock)
        return True

    def unlock(self, **kwargs):
        """Unlock the car."""
        _LOGGER.debug("%s: unlocking doors", self.vehicle.name)
        # Optimistic state set here because it takes some time before the
        # update callback response
        self._state = STATE_UNLOCKED
        self.async_update_ha_state()
        self.vehicle.remote_services.trigger_remote_door_unlock()

    def update(self):
        """Update state of the lock."""
        _LOGGER.debug("%s: updating data for %s", self.vehicle.name, self.name)
        vehicle_state = self.vehicle.state

        # Possible values: LOCKED, SECURED, SELECTIVE_LOCKED, UNLOCKED
        self._state = (
            STATE_LOCKED
            if vehicle_state.door_lock_state in [LockState.LOCKED, LockState.SECURED]
            else STATE_UNLOCKED
        )
        
        return self._state

    # def update_callback(self):
    #     """Schedule a state update."""
    #     self.schedule_update_ha_state(True)

    # async def async_added_to_hass(self):
    #     """Add callback after being added to hass.

    #     Show latest data after startup.
    #     """
    #     self._account.add_update_listener(self.update_callback)
