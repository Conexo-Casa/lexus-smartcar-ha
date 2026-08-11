"""Device tracker platform for Smartcar (vehicle GPS location, v3)."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATORS, DOMAIN
from .coordinator import SmartcarCoordinator
from .entity import SmartcarEntity

CODE = "location-preciselocation"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a location tracker for every vehicle."""
    coordinators: list[SmartcarCoordinator] = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATORS
    ]
    async_add_entities(SmartcarDeviceTracker(c) for c in coordinators)


class SmartcarDeviceTracker(SmartcarEntity, TrackerEntity):
    """Reports the vehicle's latitude/longitude."""

    _attr_translation_key = "location"

    def __init__(self, coordinator: SmartcarCoordinator) -> None:
        """Initialise the tracker."""
        super().__init__(coordinator, "location")

    @property
    def available(self) -> bool:
        """Available only when a location signal was returned."""
        return super().available and CODE in self.coordinator.data

    @property
    def source_type(self) -> SourceType:
        """GPS-based tracker."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return the last known latitude."""
        return self.coordinator.data.get(CODE, {}).get("latitude")

    @property
    def longitude(self) -> float | None:
        """Return the last known longitude."""
        return self.coordinator.data.get(CODE, {}).get("longitude")
