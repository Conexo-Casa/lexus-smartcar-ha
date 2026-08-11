"""Constants for the Smartcar integration (Smartcar API v3).

v3 uses machine-to-machine (client_credentials) auth: the app exchanges its
Client ID + Secret at the IAM endpoint for a 1-hour bearer token (no refresh
token — just request a new one). Vehicles are discovered via the Connections
API, and every read is scoped by a `sc-user-id` header. See references and the
Smartcar dashboard for setup.
"""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "smartcar"

# ── v3 endpoints ─────────────────────────────────────────────────────────────
# Token endpoint lives on its own IAM host, distinct from the API host.
TOKEN_URL = "https://iam.smartcar.com/oauth2/token"
API_BASE_URL = "https://vehicle.api.smartcar.com/v3"

# ── Config entry data keys ───────────────────────────────────────────────────
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"

# ── Polling ──────────────────────────────────────────────────────────────────
# Smartcar bills per request and rate-limits; default to a conservative poll.
DEFAULT_SCAN_INTERVAL_MINUTES = 30
MIN_SCAN_INTERVAL_MINUTES = 5
MAX_SCAN_INTERVAL_MINUTES = 1440
CONF_SCAN_INTERVAL = "scan_interval_minutes"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

# Access tokens live 3600s; refresh a little early.
TOKEN_TTL_SECONDS = 3600
TOKEN_REFRESH_MARGIN_SECONDS = 120

# ── Runtime data keys ────────────────────────────────────────────────────────
DATA_COORDINATORS = "coordinators"

# NOTE: The v3 /signals endpoint returns a flat list of coded signals
# (attributes.code + attributes.body{unit,value}). The exact `code` values are
# finalized from a live /signals payload — do not hardcode a guessed schema.
