"""The Smartcar integration (Smartcar API v3, machine-to-machine auth)."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartcarApi, SmartcarAuthError, SmartcarError
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_SCAN_INTERVAL,
    DATA_COORDINATORS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)
from .coordinator import SmartcarCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.LOCK,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smartcar from a config entry."""
    websession = async_get_clientsession(hass)
    api = SmartcarApi(
        websession,
        entry.data[CONF_CLIENT_ID],
        entry.data[CONF_CLIENT_SECRET],
    )

    try:
        connections = await api.async_list_connections()
    except SmartcarAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except SmartcarError as err:
        raise ConfigEntryNotReady(f"Cannot reach Smartcar: {err}") from err

    if not connections:
        _LOGGER.warning(
            "No vehicles are connected to this Smartcar application yet. "
            "Connect one via Smartcar Connect (or the dashboard simulator), "
            "then reload this entry"
        )

    interval = timedelta(
        minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES)
    )

    coordinators: list[SmartcarCoordinator] = []
    for connection in connections:
        coordinator = SmartcarCoordinator(hass, entry, api, connection, interval)
        await coordinator.async_config_entry_first_refresh()
        coordinators.append(coordinator)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATORS: coordinators,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options (e.g. scan interval) change."""
    await hass.config_entries.async_reload(entry.entry_id)
