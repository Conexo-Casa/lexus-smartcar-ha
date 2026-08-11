"""Binary sensor platform for Smartcar (v3 signals)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATORS, DOMAIN
from .coordinator import SmartcarCoordinator
from .entity import SmartcarEntity


def _diag(body: dict[str, Any]) -> bool | None:
    """Problem when a diagnostics status is anything other than OK."""
    status = body.get("status")
    if status is None:
        return None
    return status != "OK"


@dataclass(frozen=True, kw_only=True)
class SmartcarBinaryDescription(BinarySensorEntityDescription):
    """Binary sensor description with source code and extractor."""

    code: str
    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[SmartcarBinaryDescription, ...] = (
    SmartcarBinaryDescription(
        key="online",
        translation_key="online",
        code="connectivitystatus-isonline",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarBinaryDescription(
        key="at_home",
        translation_key="at_home",
        code="location-isathome",
        icon="mdi:home-map-marker",
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarBinaryDescription(
        key="in_service",
        translation_key="in_service",
        code="service-isinservice",
        icon="mdi:car-wrench",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarBinaryDescription(
        key="front_trunk",
        translation_key="front_trunk",
        code="closure-fronttrunk",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda b: b.get("isOpen"),
    ),
    SmartcarBinaryDescription(
        key="rear_trunk",
        translation_key="rear_trunk",
        code="closure-reartrunk",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda b: b.get("isOpen"),
    ),
    SmartcarBinaryDescription(
        key="sunroof",
        translation_key="sunroof",
        code="closure-sunroof",
        device_class=BinarySensorDeviceClass.WINDOW,
        value_fn=lambda b: b.get("isOpen"),
    ),
    # Diagnostics reported as problem sensors (on = not OK).
    SmartcarBinaryDescription(
        key="diag_airbag",
        translation_key="diag_airbag",
        code="diagnostics-airbag",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_diag,
    ),
    SmartcarBinaryDescription(
        key="diag_brakefluid",
        translation_key="diag_brakefluid",
        code="diagnostics-brakefluid",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_diag,
    ),
    SmartcarBinaryDescription(
        key="diag_tirepressure",
        translation_key="diag_tirepressure",
        code="diagnostics-tirepressure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_diag,
    ),
    SmartcarBinaryDescription(
        key="diag_transmission",
        translation_key="diag_transmission",
        code="diagnostics-transmission",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_diag,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smartcar binary sensors for every vehicle."""
    coordinators: list[SmartcarCoordinator] = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATORS
    ]
    async_add_entities(
        SmartcarBinarySensor(coordinator, description)
        for coordinator in coordinators
        for description in BINARY_SENSORS
    )


class SmartcarBinarySensor(SmartcarEntity, BinarySensorEntity):
    """A single Smartcar-derived binary sensor."""

    entity_description: SmartcarBinaryDescription

    def __init__(
        self,
        coordinator: SmartcarCoordinator,
        description: SmartcarBinaryDescription,
    ) -> None:
        """Initialise from a description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Available only when the source signal is present."""
        return (
            super().available and self.entity_description.code in self.coordinator.data
        )

    @property
    def is_on(self) -> bool | None:
        """Extract the boolean value from the source signal."""
        body = self.coordinator.data.get(self.entity_description.code)
        if body is None:
            return None
        return self.entity_description.value_fn(body)
