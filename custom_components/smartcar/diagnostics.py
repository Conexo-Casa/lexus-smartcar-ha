"""Diagnostics support for Smartcar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATORS, DOMAIN
from .coordinator import SmartcarCoordinator

# Never leak location, VIN, or OAuth material into a diagnostics download.
TO_REDACT = {
    "latitude",
    "longitude",
    "vin",
    "access_token",
    "refresh_token",
    "token",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinators: list[SmartcarCoordinator] = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATORS
    ]
    return {
        "options": dict(entry.options),
        "vehicles": [
            {
                "info": async_redact_data(coordinator.vehicle_info, TO_REDACT),
                "signals_present": sorted(coordinator.data or {}),
                "data": async_redact_data(coordinator.data or {}, TO_REDACT),
            }
            for coordinator in coordinators
        ],
    }
