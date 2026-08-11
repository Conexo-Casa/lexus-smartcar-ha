"""Config and options flow for the Smartcar integration (v3).

v3 authenticates machine-to-machine, so setup is just the app's Client ID and
Client Secret — no browser OAuth, no redirect URI. We validate by fetching an
application access token.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartcarApi, SmartcarAuthError, SmartcarError
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
    }
)


class SmartcarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Smartcar config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect and validate the app credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip()
            client_secret = user_input[CONF_CLIENT_SECRET].strip()

            await self.async_set_unique_id(client_id)
            self._abort_if_unique_id_configured()

            api = SmartcarApi(
                async_get_clientsession(self.hass), client_id, client_secret
            )
            try:
                # A successful token fetch proves the credentials are valid.
                await api.async_get_token()
            except SmartcarAuthError:
                errors["base"] = "invalid_auth"
            except SmartcarError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Smartcar",
                    data={
                        CONF_CLIENT_ID: client_id,
                        CONF_CLIENT_SECRET: client_secret,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-auth (rotated secret)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect a fresh secret and update the entry."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            client_id = reauth_entry.data[CONF_CLIENT_ID]
            client_secret = user_input[CONF_CLIENT_SECRET].strip()
            api = SmartcarApi(
                async_get_clientsession(self.hass), client_id, client_secret
            )
            try:
                await api.async_get_token()
            except SmartcarAuthError:
                errors["base"] = "invalid_auth"
            except SmartcarError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={**reauth_entry.data, CONF_CLIENT_SECRET: client_secret},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_CLIENT_SECRET): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return SmartcarOptionsFlow()


class SmartcarOptionsFlow(OptionsFlow):
    """Options: adjust the polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the poll interval option."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=MIN_SCAN_INTERVAL_MINUTES, max=MAX_SCAN_INTERVAL_MINUTES
                    ),
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
