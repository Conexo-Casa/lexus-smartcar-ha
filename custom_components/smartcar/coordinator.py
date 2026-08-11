"""DataUpdateCoordinator for the Smartcar integration (v3).

One coordinator per connected vehicle. Each poll calls GET /vehicles/{id}/signals
(with the sc-user-id header) and flattens the JSON:API list into a dict keyed by
signal ``code`` — e.g. ``data["odometer-traveleddistance"] == {"value": 78432,
"unit": "km"}``. Only signals whose ``status.value == "SUCCESS"`` are kept, so a
signal the vehicle can't provide (ERROR) is simply absent and its entity reports
``unavailable``.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartcarApi, SmartcarAuthError, SmartcarError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmartcarCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls a single vehicle's v3 signals."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: SmartcarApi,
        connection: dict[str, Any],
        update_interval: timedelta,
    ) -> None:
        """Store the API client and the connection (vehicle + user + attrs)."""
        self.api = api
        self.vehicle_id: str = connection["vehicle_id"]
        self.user_id: str = connection["user_id"]
        self.vehicle_info: dict[str, Any] = connection.get("vehicle", {})
        self.permissions: list[str] = connection.get("permissions", [])
        # Populated from the first signals payload (device metadata).
        self.vin: str | None = None
        self.firmware: str | None = None
        self.nickname: str | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.vehicle_id[:8]}",
            update_interval=update_interval,
            config_entry=entry,
        )

    @property
    def device_name(self) -> str:
        """Friendly vehicle name, preferring the OEM nickname."""
        if self.nickname:
            return self.nickname
        year = self.vehicle_info.get("year", "")
        make = self.vehicle_info.get("make", "Smartcar")
        model = self.vehicle_info.get("model", "")
        return " ".join(str(p) for p in (year, make, model) if p).strip() or "Vehicle"

    def has_permission(self, permission: str) -> bool:
        """Whether the connection granted a given permission scope."""
        return permission in self.permissions

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch signals and flatten to {code: body} for SUCCESS signals."""
        try:
            signals = await self.api.async_get_signals(self.vehicle_id, self.user_id)
        except SmartcarAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SmartcarError as err:
            raise UpdateFailed(str(err)) from err

        data: dict[str, dict[str, Any]] = {}
        for item in signals:
            attrs = item.get("attributes", {})
            code = attrs.get("code")
            if not code:
                continue
            if attrs.get("status", {}).get("value") != "SUCCESS":
                _LOGGER.debug("%s: signal %s not SUCCESS", self.name, code)
                continue
            data[code] = attrs.get("body", {})

        # Capture device metadata from the payload (best-effort).
        if vin := data.get("vehicleidentification-vin", {}).get("value"):
            self.vin = vin
        if fw := data.get(
            "connectivitysoftware-currentfirmwareversion", {}
        ).get("value"):
            self.firmware = fw
        if nick := data.get("vehicleidentification-nickname", {}).get("value"):
            self.nickname = nick

        return data
