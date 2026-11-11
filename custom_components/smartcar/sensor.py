"""Sensor platform for Smartcar (v3 signals).

Each sensor maps to a v3 signal ``code`` and extracts its value from that
signal's ``body`` (shapes vary by signal). A sensor whose signal is absent from
the last poll (unsupported / ERROR) reports ``unavailable``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DATA_COORDINATORS, DOMAIN
from .coordinator import SmartcarCoordinator
from .entity import SmartcarEntity

# Tire positions in the wheel-tires values grid (row, column).
_TIRE_POS = {
    "front_left": (0, 0),
    "front_right": (0, 1),
    "back_left": (1, 0),
    "back_right": (1, 1),
}


def _tire(pos: str) -> Callable[[dict[str, Any]], StateType]:
    """Return a value_fn pulling one tire's pressure from wheel-tires."""
    row, col = _TIRE_POS[pos]

    def _fn(body: dict[str, Any]) -> StateType:
        for v in body.get("values", []):
            if v.get("row") == row and v.get("column") == col:
                return v.get("tirePressure")
        return None

    return _fn


@dataclass(frozen=True, kw_only=True)
class SmartcarSensorDescription(SensorEntityDescription):
    """Sensor description with a source signal code and extractor."""

    code: str
    value_fn: Callable[[dict[str, Any]], StateType]


SENSORS: tuple[SmartcarSensorDescription, ...] = (
    SmartcarSensorDescription(
        key="odometer",
        translation_key="odometer",
        code="odometer-traveleddistance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarSensorDescription(
        key="fuel_level",
        translation_key="fuel_level",
        code="internalcombustionengine-fuellevel",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:gas-station",
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarSensorDescription(
        key="fuel_remaining",
        translation_key="fuel_remaining",
        code="internalcombustionengine-amountremaining",
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarSensorDescription(
        key="fuel_range",
        translation_key="fuel_range",
        code="internalcombustionengine-range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        icon="mdi:map-marker-distance",
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarSensorDescription(
        key="oil_life",
        translation_key="oil_life",
        code="internalcombustionengine-oillife",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:oil",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarSensorDescription(
        key="speed",
        translation_key="speed",
        code="motion-currentspeed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarSensorDescription(
        key="temp_exterior",
        translation_key="temp_exterior",
        code="climate-externaltemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarSensorDescription(
        key="temp_cabin",
        translation_key="temp_cabin",
        code="climate-internaltemperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda b: b.get("value"),
    ),
    SmartcarSensorDescription(
        key="gear",
        translation_key="gear",
        code="transmission-gearstate",
        device_class=SensorDeviceClass.ENUM,
        # Smartcar sends PARK/DRIVE/...; HA translation keys must be lowercase.
        options=["park", "drive", "reverse", "neutral"],
        icon="mdi:car-shift-pattern",
        value_fn=lambda b: v.lower() if isinstance(v := b.get("value"), str) else None,
    ),
    SmartcarSensorDescription(
        key="drive_mode",
        translation_key="drive_mode",
        code="transmission-drivemode",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:car-cog",
        value_fn=lambda b: b.get("canonical") or b.get("oemDisplayName"),
    ),
    # Tire pressures (kPa) from the wheel-tires grid.
    SmartcarSensorDescription(
        key="tire_front_left",
        translation_key="tire_front_left",
        code="wheel-tires",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        value_fn=_tire("front_left"),
    ),
    SmartcarSensorDescription(
        key="tire_front_right",
        translation_key="tire_front_right",
        code="wheel-tires",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        value_fn=_tire("front_right"),
    ),
    SmartcarSensorDescription(
        key="tire_back_left",
        translation_key="tire_back_left",
        code="wheel-tires",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        value_fn=_tire("back_left"),
    ),
    SmartcarSensorDescription(
        key="tire_back_right",
        translation_key="tire_back_right",
        code="wheel-tires",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        value_fn=_tire("back_right"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smartcar sensors for every vehicle."""
    coordinators: list[SmartcarCoordinator] = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATORS
    ]
    async_add_entities(
        SmartcarSensor(coordinator, description)
        for coordinator in coordinators
        for description in SENSORS
    )


class SmartcarSensor(SmartcarEntity, SensorEntity):
    """A single Smartcar-derived sensor."""

    entity_description: SmartcarSensorDescription

    def __init__(
        self,
        coordinator: SmartcarCoordinator,
        description: SmartcarSensorDescription,
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
    def native_value(self) -> StateType:
        """Extract the value from the source signal body."""
        body = self.coordinator.data.get(self.entity_description.code)
        if body is None:
            return None
        return self.entity_description.value_fn(body)
