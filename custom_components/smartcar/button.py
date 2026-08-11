"""Button platform for Smartcar (force a data refresh)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATORS, DOMAIN
from .coordinator import SmartcarCoordinator
from .entity import SmartcarEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a refresh button for every vehicle."""
    coordinators: list[SmartcarCoordinator] = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATORS
    ]
    async_add_entities(SmartcarRefreshButton(c) for c in coordinators)


class SmartcarRefreshButton(SmartcarEntity, ButtonEntity):
    """Triggers an immediate poll of the vehicle."""

    _attr_translation_key = "refresh"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: SmartcarCoordinator) -> None:
        """Initialise the button."""
        super().__init__(coordinator, "refresh")

    async def async_press(self) -> None:
        """Force a coordinator refresh."""
        await self.coordinator.async_request_refresh()
