"""Lock platform for Smartcar (v3 remote lock/unlock).

Unlike v2.0, v3 reports real lock state via the ``closure-islocked`` signal, so
this is NOT an assumed-state lock — it reflects the vehicle's actual status.
Requires the ``control_security`` permission on the connection.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import SmartcarError
from .const import DATA_COORDINATORS, DOMAIN
from .coordinator import SmartcarCoordinator
from .entity import SmartcarEntity

_LOGGER = logging.getLogger(__name__)

CODE = "closure-islocked"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a lock for every vehicle that granted control_security."""
    coordinators: list[SmartcarCoordinator] = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATORS
    ]
    async_add_entities(
        SmartcarLock(c) for c in coordinators if c.has_permission("control_security")
    )


class SmartcarLock(SmartcarEntity, LockEntity):
    """Remote door lock with real state from closure-islocked."""

    _attr_translation_key = "doors"

    def __init__(self, coordinator: SmartcarCoordinator) -> None:
        """Initialise the lock."""
        super().__init__(coordinator, "lock")

    @property
    def is_locked(self) -> bool | None:
        """Return the reported lock state."""
        body = self.coordinator.data.get(CODE)
        if body is None:
            return None
        return body.get("value")

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the doors."""
        await self._async_command(lock=True)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the doors."""
        await self._async_command(lock=False)

    async def _async_command(self, lock: bool) -> None:
        """Issue the command, then refresh to pick up the new state."""
        self._attr_is_locking = lock
        self._attr_is_unlocking = not lock
        self.async_write_ha_state()
        try:
            if lock:
                await self.coordinator.api.async_lock(
                    self.coordinator.vehicle_id, self.coordinator.user_id
                )
            else:
                await self.coordinator.api.async_unlock(
                    self.coordinator.vehicle_id, self.coordinator.user_id
                )
        except SmartcarError as err:
            raise HomeAssistantError(
                f"Smartcar {'lock' if lock else 'unlock'} failed: {err}"
            ) from err
        finally:
            self._attr_is_locking = False
            self._attr_is_unlocking = False
        await self.coordinator.async_request_refresh()
