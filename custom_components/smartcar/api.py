"""Async client for the Smartcar API v3 (machine-to-machine auth).

Auth model: exchange Client ID + Secret for a 1-hour bearer token at the IAM
endpoint (no refresh token — re-request on expiry). Vehicles are found via the
Connections API; every per-vehicle read carries the `sc-user-id` header.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import (
    API_BASE_URL,
    TOKEN_REFRESH_MARGIN_SECONDS,
    TOKEN_TTL_SECONDS,
    TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)


class SmartcarError(Exception):
    """Generic Smartcar API error."""


class SmartcarAuthError(SmartcarError):
    """Invalid client credentials or rejected token (triggers reauth)."""


class SmartcarRateLimitError(SmartcarError):
    """Rate limit reached (429)."""


class SmartcarApi:
    """v3 client: token management + connections + signals."""

    def __init__(
        self, websession: ClientSession, client_id: str, client_secret: str
    ) -> None:
        """Store credentials and the shared aiohttp session."""
        self._session = websession
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expiry: float = 0.0

    # ── Auth ─────────────────────────────────────────────────────────────────

    async def async_get_token(self) -> str:
        """Return a valid bearer token, refreshing via client_credentials."""
        now = time.time()
        if self._token and now < self._token_expiry - TOKEN_REFRESH_MARGIN_SECONDS:
            return self._token

        try:
            async with self._session.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 401:
                    raise SmartcarAuthError(f"Invalid client credentials: {body}")
                if resp.status >= 400:
                    raise SmartcarError(f"Token request failed {resp.status}: {body}")
        except ClientError as err:
            raise SmartcarError(f"Token transport error: {err}") from err

        self._token = body["access_token"]
        self._token_expiry = now + body.get("expires_in", TOKEN_TTL_SECONDS)
        return self._token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        user_id: str | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated v3 request."""
        token = await self.async_get_token()
        headers = {"Authorization": f"Bearer {token}"}
        if user_id:
            headers["sc-user-id"] = user_id
        url = f"{API_BASE_URL}{path}"
        try:
            async with self._session.request(
                method, url, headers=headers, json=json
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 401:
                    raise SmartcarAuthError(f"Unauthorized: {body}")
                if resp.status == 429:
                    raise SmartcarRateLimitError(f"Rate limited: {body}")
                if resp.status >= 400:
                    raise SmartcarError(f"{method} {path} -> {resp.status}: {body}")
                return body
        except ClientError as err:
            raise SmartcarError(f"Transport error on {method} {path}: {err}") from err

    # ── Discovery ────────────────────────────────────────────────────────────

    async def async_list_connections(self) -> list[dict[str, Any]]:
        """Return all vehicle connections with inline vehicle + user info.

        The v3 /connections response nests the useful fields (confirmed live):
        ``vehicleId`` lives under ``relationships.vehicle.data.id``; ``userId``
        and the vehicle attributes/permissions live under ``attributes``. That
        means one call yields everything needed to build the device — no extra
        ``GET /vehicles/{id}`` required.
        """
        data = await self._request("GET", "/connections")
        out: list[dict[str, Any]] = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            rel_vehicle = (
                item.get("relationships", {}).get("vehicle", {}).get("data", {})
            )
            vehicle_id = rel_vehicle.get("id")
            user_id = (attrs.get("user") or {}).get("id")
            if not vehicle_id or not user_id:
                _LOGGER.warning("Skipping malformed connection: %s", item.get("id"))
                continue
            out.append(
                {
                    "connection_id": item.get("id"),
                    "vehicle_id": vehicle_id,
                    "user_id": user_id,
                    "vehicle": attrs.get("vehicle", {}),
                    "permissions": attrs.get("permissions", []),
                }
            )
        return out

    async def async_get_vehicle(self, vehicle_id: str) -> dict[str, Any]:
        """Return vehicle attributes {make, model, year, powertrainType, mode}.

        Usually unnecessary — async_list_connections already returns these — but
        handy for a targeted refresh.
        """
        data = await self._request("GET", f"/vehicles/{vehicle_id}")
        return data.get("data", {}).get("attributes", {})

    # ── Read signals ─────────────────────────────────────────────────────────

    async def async_get_signals(
        self, vehicle_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        """Return the raw list of signal objects for a vehicle.

        Each item: {"attributes": {"code","name","group","status":{"value"},
        "body":{"unit","value"}}, "meta": {...}}.
        """
        data = await self._request(
            "GET", f"/vehicles/{vehicle_id}/signals", user_id=user_id
        )
        return data.get("data", [])

    # ── Commands (v3, sc-user-id required, synchronous) ──────────────────────

    async def async_command(
        self, vehicle_id: str, user_id: str, command_path: str
    ) -> dict[str, Any]:
        """POST a vehicle command, e.g. 'security/lock'. Returns the execution."""
        return await self._request(
            "POST",
            f"/vehicles/{vehicle_id}/commands/{command_path}",
            user_id=user_id,
        )

    async def async_lock(self, vehicle_id: str, user_id: str) -> dict[str, Any]:
        """Lock all doors."""
        return await self.async_command(vehicle_id, user_id, "security/lock")

    async def async_unlock(self, vehicle_id: str, user_id: str) -> dict[str, Any]:
        """Unlock all doors."""
        return await self.async_command(vehicle_id, user_id, "security/unlock")
