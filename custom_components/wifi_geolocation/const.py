"""Constants for the WiFi Geolocation HA integration."""

DOMAIN = "wifi_geolocation"

BACKEND_GOOGLE = "google"
BACKEND_WIGLE = "wigle"
BACKEND_COMBAIN = "combain"
BACKEND_HERE = "here"
BACKEND_UNWIRED_LABS = "unwired_labs"
BACKEND_BEACONDB = "beacondb"
BACKEND_MOZILLA = "mozilla"
BACKEND_WIFIDB = "wifidb"
BACKEND_KNOWN_NETWORKS = "known_networks"

# Canonical listing order (free/open services first, then paid ones, then
# WiGLE) -- only used to break ties when two backends are given the same
# priority number in the config flow, and to order the priority-field form.
# Not an enforced fallback order; the user's own priority numbers are.
# Known Networks goes first: it's local and instant (no network call at
# all), and it's the only backend that can ever cover a private AP no
# crowd-sourced database -- free or paid -- has ever seen.
BACKEND_PRIORITY_ORDER = [
    BACKEND_KNOWN_NETWORKS,
    BACKEND_BEACONDB,
    BACKEND_MOZILLA,
    BACKEND_WIFIDB,
    BACKEND_GOOGLE,
    BACKEND_HERE,
    BACKEND_COMBAIN,
    BACKEND_UNWIRED_LABS,
    BACKEND_WIGLE,
]

BACKEND_LABELS = {
    BACKEND_GOOGLE: "Google Geolocation API",
    BACKEND_WIGLE: "WiGLE",
    BACKEND_COMBAIN: "Combain Positioning API",
    BACKEND_HERE: "HERE Technologies Positioning API",
    BACKEND_UNWIRED_LABS: "Unwired Labs LocationAPI",
    BACKEND_BEACONDB: "BeaconDB (free, no account needed)",
    BACKEND_MOZILLA: "Mozilla Location Service / self-hosted Ichnaea",
    BACKEND_WIFIDB: "WifiDB (free, no account needed -- beta community project)",
    BACKEND_KNOWN_NETWORKS: "Known Networks (your own local cache -- free, no account, no external calls)",
}

CONF_BACKENDS = "backends"  # stored in the config entry: list[str], in priority order
CONF_PRIORITY_PREFIX = "priority_"  # form field per backend; 0 = disabled

CONF_GOOGLE_API_KEY = "google_api_key"
CONF_WIGLE_API_NAME = "wigle_api_name"
CONF_WIGLE_API_TOKEN = "wigle_api_token"
CONF_COMBAIN_API_KEY = "combain_api_key"
CONF_HERE_API_KEY = "here_api_key"
CONF_UNWIRED_LABS_API_KEY = "unwired_labs_api_key"
CONF_UNWIRED_LABS_BASE_URL = "unwired_labs_base_url"
CONF_MOZILLA_API_KEY = "mozilla_api_key"
CONF_MOZILLA_BASE_URL = "mozilla_base_url"

# Known Networks' "credential" form is really "add one network" -- see
# config_flow.py's _apply_backend_config docstring for why its submitted
# values are never stored under the config entry itself.
CONF_KNOWN_NETWORK_BSSID = "bssid"
CONF_KNOWN_NETWORK_LATITUDE = "latitude"
CONF_KNOWN_NETWORK_LONGITUDE = "longitude"
CONF_KNOWN_NETWORK_ACCURACY_M = "accuracy_m"

# Fixed, well-known filename under HA's own config directory -- always
# derivable from `hass` alone, so it never needs to be threaded through
# the config entry's stored data.
KNOWN_NETWORKS_STORE_FILENAME = "wifi_geolocation_known_networks.json"

SERVICE_RESOLVE = "resolve"
