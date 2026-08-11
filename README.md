# Smartcar for Home Assistant (Lexus)

A HACS custom integration that connects your vehicle to Home Assistant through the
[Smartcar](https://smartcar.com) **API v3**. Built and tested against a Lexus
(Toyota Connected) account, but the Smartcar API is make-agnostic — the same
integration works for any supported brand.

v3 authenticates **machine-to-machine**, so Home Assistant setup is just your
app's **Client ID + Client Secret** — no browser OAuth, no redirect URI, no
refresh tokens. The integration fetches an application token, discovers your
connected vehicles, and polls each vehicle's signals in one request per cycle.
Signals the vehicle doesn't support are skipped, so their entities show
*unavailable* rather than breaking anything.

## Entities

Created per connected vehicle (those the vehicle doesn't report stay *unavailable*):

| Platform | Entities |
|---|---|
| `sensor` | Odometer, fuel level / remaining / range, engine oil life, speed, outside & cabin temperature, gear, drive mode, 4× tire pressure |
| `device_tracker` | Vehicle GPS location |
| `lock` | Doors — remote lock/unlock with **real lock state** (requires `control_security`) |
| `binary_sensor` | Online, at home, in service, front/rear trunk, sunroof, and diagnostic (airbag, brake fluid, tire-pressure, transmission) problem sensors |
| `button` | Refresh data (force an immediate poll) |

> EV/hybrid vehicles expose different signals (battery, charging) — those map in
> automatically once a vehicle reporting them is connected.

## Prerequisites

1. **A Smartcar developer app (v3).** Sign up at
   **[dashboard.smartcar.com](https://dashboard.smartcar.com)** (free tier covers
   personal use). Open your application → **API Credentials** → **Create Secret**.
   Copy the **Client ID** (`client_...`) and **Client Secret** (shown once).
2. **A connected vehicle.** Your car must be linked to the application before HA
   can read it:
   - **Real vehicle:** run Smartcar Connect and sign in with your Lexus/Toyota
     account to authorize the car.
   - **Testing:** create a **simulated vehicle** in the dashboard's **Simulator**
     tab, connect it, and press **Play**.

   You can confirm a vehicle is connected — the integration reads it from
   Smartcar's Connections API automatically.

## Installation

### HACS
1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/Conexo-Casa/lexus-smartcar-ha` as an **Integration**.
2. Install **Smartcar**, then restart Home Assistant.

### Manual
Copy `custom_components/smartcar/` into `config/custom_components/` and restart.

## Configuration

1. **Settings → Devices & Services → Add Integration → Smartcar.**
2. Enter your **Client ID** and **Client Secret**. HA validates them by fetching a
   token, then creates a device for each connected vehicle.
3. **Configure** on the integration lets you set the **polling interval** (default
   30 min, minimum 5). Smartcar bills per request and rate-limits, so poll no more
   than you need; use the **Refresh data** button for an on-demand update.

## How it works (v3)

- **Auth:** `POST https://iam.smartcar.com/oauth2/token` with
  `grant_type=client_credentials` → a 1-hour bearer token (no refresh token; the
  client re-requests on expiry).
- **Discovery:** `GET /v3/connections` returns each connected vehicle's `vehicleId`
  + `userId` (plus make/model/year and granted permissions) — no browser flow.
- **Data:** `GET /v3/vehicles/{id}/signals` (with the `sc-user-id` header) returns
  every signal; the coordinator keeps the `SUCCESS` ones, keyed by signal code.
- **Commands:** lock/unlock via
  `POST /v3/vehicles/{id}/commands/security/{lock,unlock}` (synchronous).

## Troubleshooting

- **No entities / no devices** — no vehicle is connected to the app yet. Connect
  one (real via Connect, or a simulator vehicle) and reload the integration.
- **Entities unavailable** — the vehicle doesn't report that signal, or the
  permission wasn't granted. Check the diagnostics download (Device → ⋮ → Download
  diagnostics) for the signals present.
- **Invalid auth** — re-check the Client ID/Secret; rotating the secret in the
  dashboard triggers a re-auth prompt in HA.

## Disclaimer

Not affiliated with Smartcar, Toyota, or Lexus. Remote commands depend on your
vehicle's capabilities and connected-services subscription. Use at your own risk.
