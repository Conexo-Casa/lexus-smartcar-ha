"""Base entity for the Smartcar integration (v3)."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartcarCoordinator


class SmartcarEntity(CoordinatorEntity[SmartcarCoordinator]):
    """Common base: ties every entity to the vehicle's HA device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartcarCoordinator, key: str) -> None:
        """Set the unique id and device metadata."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.vehicle_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.vehicle_id)},
            manufacturer=coordinator.vehicle_info.get("make", "Smartcar"),
            model=coordinator.vehicle_info.get("model"),
            name=coordinator.device_name,
            serial_number=coordinator.vin,
            sw_version=coordinator.firmware,
            configuration_url="https://dashboard.smartcar.com",
        )
