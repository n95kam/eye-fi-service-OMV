[日本語版 README](README.ja.md) | Japanese

# Eye-Fi OMV

**Bring your old Eye-Fi camera back to life. 📷**

Give your old digital camera a new place in your everyday life.

Eye-Fi OMV is a personal modification of an existing Eye-Fi integration for Home Assistant. It is intended for setups that receive photos from Eye-Fi cards and store them on network storage such as OpenMediaVault (OMV).

The idea is simple: bring old Eye-Fi cards and classic digital cameras back into use by combining them with modern NAS storage and smart home systems.

## ✨ What is this?

Eye-Fi cards were Wi-Fi-enabled memory cards that could transfer photos from a camera over a local network.

Although the original manufacturer's services have ended, some Eye-Fi hardware may still be usable with a suitable local setup.

This project uses Home Assistant as part of a local photo-receiving workflow and aims to store received photos on network storage.

- 📡 **Receive photos from Eye-Fi** — Receive photos from compatible Eye-Fi cards over a local network.
- 🗄️ **Store photos on a NAS** — Collect photos in a configured destination such as OpenMediaVault.
- 🧹 **Clean up local temporary files** — After a successful storage operation, the modified code attempts to delete the local source image and its associated `.log` file.
- 🏠 **Integrate with a smart home** — Use Home Assistant as part of a modern home network workflow.

If storage fails and the image is queued for retry, the local source files are retained at that point. However, the behavior of all retry and recovery scenarios has not been fully tested. In particular, a later successful retry is not guaranteed to remove the original local files.

## 📷 Why Eye-Fi again?

Older digital cameras have a character of their own.

Some cameras with CCD sensors produce colors and images that many people find distinctive and appealing. The results depend on the camera, lens, and shooting conditions, but using these older cameras can still be a lot of fun.

Instead of manually importing every photo, it is convenient to collect them on a NAS and manage them alongside the rest of your digital life.

**Keep the joy of shooting with a classic camera, while making photo management feel modern.**

That is the idea behind this project.

## 🛠️ What has been modified?

This repository is a personal modification of an existing Eye-Fi Home Assistant integration.

The main changes include:

- Documentation and setup focused on environments using OMV or other network storage.
- Improved handling of storage success and failure.
- Removal of the local source image and associated `.log` file after a successful storage operation.
- Improvements to logging around storage and retry behavior.

The changes may be small, but they build on an existing project that made this possible in the first place.

## ⚠️ Status and limitations

**This is an experimental personal modification.**

The modified setup has been tested with a real Eye-Fi card, Home Assistant, and network storage. In the tested setup, photos appeared on the NAS and the local Eye-Fi download folder was left empty after transfer.

However, this is not a comprehensive test suite, and this project has not been tested as extensively as the original integration. Its reliability across different hardware and configurations is unknown.

Please keep the following limitations in mind:

- Compatibility with every Eye-Fi card, camera, or storage destination is not guaranteed.
- Network outages, insufficient storage space, permission errors, and all retry/recovery scenarios have not been fully tested.
- A photo that enters the retry queue may remain in the local download directory even if a later retry succeeds.
- Successful transfer does not replace a proper backup strategy or guarantee long-term photo preservation.

If you use this with important photos, keep independent backups and test with disposable images first.

## 🙏 Credits and acknowledgements

This project is based on the existing [Eye-Fi Service Integration](https://github.com/dgtlrift/eye-fi-service-integration).

Many thanks to the original author for creating and sharing the project. Without that existing code and foundation, this modification would not have been possible.

This modification was developed with help from OpenAI's ChatGPT using **vibe coding** to explore changes, troubleshoot issues, and refine the implementation.

I am not an expert software developer, and I have not been able to perform extensive testing on my own. With the help of AI, however, I was able to make the changes and verify the basic workflow with real hardware.

This project is shared as-is, without any guarantee that it will work correctly in every environment. Feedback, code reviews, and suggestions for safer or more robust implementations are very welcome.

## 🤝 Contributions welcome

If this project interests you, contributions and feedback are appreciated.

- Code reviews
- Bug reports
- Reports from testing other Eye-Fi cards and cameras
- Improvements for NAS and network storage support
- Suggestions for safer file cleanup and retry handling

In particular, advice from people experienced with Python and Home Assistant integration development would be greatly appreciated.

Suggestions and constructive criticism are welcome. If something could be implemented more safely or reliably, I'd be happy to learn from it.

The goal is simple: make it possible to enjoy older camera equipment again.

If this small project helps someone bring a forgotten camera back into use, that would make me happy.

---

**Project:** [eye-fi-service-OMV](https://github.com/n95kam/eye-fi-service-OMV)

**Original project:** [dgtlrift/eye-fi-service-integration](https://github.com/dgtlrift/eye-fi-service-integration)

*An experimental community modification. Not affiliated with or endorsed by the original author, Eye-Fi, or OpenMediaVault.*
# Eye-Fi Home Assistant Integration

A Home Assistant custom integration that acts as an Eye-Fi card upload
server — running natively inside HA's asyncio event loop — with full
preservation of the card's WiFi-based geotagging feature (EXIF GPS tags
written locally, since Eye-Fi's own cloud/Skyhook geolocation service is
long dead).

This is a clean-room implementation: no code is forked from prior Eye-Fi
servers. Their source was read only to document the wire protocol and
`.log` sidecar format (see [Credits](#credits)), then re-implemented
async-native for Python 3 / asyncio.

## Architecture

The codebase is split into two independent core/adapter pairs, so neither
the upload protocol nor geotagging logic is ever trapped inside Home
Assistant's process model:

```
eyefi_core/                     framework-agnostic, installable, zero HA imports
├── protocol.py                 SOAP XML envelopes, credential MD5, integrity digest
├── soap_server.py              aiohttp server: StartSession/GetPhotoStatus/UploadPhoto/MarkLastPhotoInRoll
├── tar_extract.py              untar + integrity verification, JPEG + .log sidecar extraction
├── geotag.py                   .log parsing, EXIF GPS write (piexif); GeolocationBackend Protocol only --
│                                  concrete backends live in wifi_geolocation_core, not here
├── events.py                   pub/sub interface (in-process now; WebSocket-backed later, same shape)
└── storage/                    pluggable backends behind one async interface
    ├── local_nas.py            default — filesystem write (local or pre-mounted remote NAS)
    ├── remote_nas.py           smbprotocol (SMB2/3) or asyncssh (SFTP), no mount required
    ├── apple_dropfolder.py     alias over local_nas/remote_nas — see docs/apple-ecosystem-setup.md
    ├── google_photos.py        appendonly scope — upload-only, no read-back/dedup
    ├── onedrive.py             Microsoft Graph API
    ├── smugmug.py              REST API v2, OAuth 1.0a
    ├── backblaze.py            B2 native API
    └── pcloud.py                REST API, OAuth2

custom_components/eyefi/        thin HA adapter — no protocol/geotag/storage logic here
├── config_flow.py              card mac/upload-key + destination config UI (no geolocation API key -- see below)
├── __init__.py                 starts eyefi_core embedded, calls wifi_geolocation.resolve if that
│                                  integration is loaded, bridges events onto hass.bus
└── camera.py                   optional camera entity showing the latest received photo

wifi_geolocation/                a second, independent core package (its own pyproject.toml,
│                                  installed from this repo's #subdirectory=wifi_geolocation)
└── wifi_geolocation_core/       zero HA imports; one GeolocationBackend Protocol, N backends
    ├── models.py                AccessPoint, Coordinates, GeolocationBackend, format_bssid
    ├── ichnaea_compatible.py     shared impl for the Google-shaped JSON API (Google/Combain/BeaconDB/Mozilla)
    ├── google.py, combain.py, beacondb.py, mozilla.py   thin wrappers around ichnaea_compatible.py
    ├── here.py                  HERE Positioning API (different request shape)
    ├── unwired_labs.py          Unwired Labs LocationAPI (different request/response shape)
    ├── wigle.py                 WiGLE community BSSID database (its own bespoke shape)
    └── fallback.py               tries multiple backends in priority order

custom_components/wifi_geolocation/   thin HA adapter around wifi_geolocation_core
├── config_flow.py              pick any of the 7 backends (boolean toggles) + their credentials
├── __init__.py                 builds the configured backend(s), registers the wifi_geolocation.resolve service
└── services.yaml
```

**Why a separate `wifi_geolocation` integration instead of eyefi holding its
own Google/WiGLE config:** eyefi's config flow never asks for a geolocation
API key at all. If `wifi_geolocation` is installed and configured, eyefi's
adapter calls its `wifi_geolocation.resolve` service (see
`custom_components/eyefi/__init__.py`'s `_ServiceBackedGeolocationBackend`)
to turn WiFi AP sightings into coordinates; if it isn't installed,
geotagging is silently skipped, exactly like eyefi_core already treats any
unresolvable location. The two integrations share no Python imports —
only the service's JSON request/response contract — so `wifi_geolocation`
could serve other consumers later without eyefi knowing or caring.

Both `eyefi_core` and `wifi_geolocation_core` run **embedded** (imported
directly by their respective `custom_components/.../__init__.py`) for v1 —
simplest, lowest latency. Their public APIs are plain dicts/dataclasses in
and out, with zero `homeassistant.*` imports, so `eyefi_core` can later run
as a standalone daemon (`eyefi_core/service.py`, not yet built) exposing
`/config` `/status` `/events` over HTTP+WebSocket — at which point a future
Homebridge/HOOBS plugin becomes a thin client of the same running service
instead of a reimplementation from a spec.

## How it works

1. The card connects over WiFi and POSTs SOAP XML to
   `/api/soap/eyefilm/v1` on port 59278 (hardcoded in card firmware):
   `StartSession` → `GetPhotoStatus` → `UploadPhoto` → `MarkLastPhotoInRoll`.
2. `UploadPhoto`'s multipart body carries a tar archive: the JPEG plus a
   sidecar `.log` file recording every WiFi AP the card saw around the
   moment the photo was taken, verified against an MD5 integrity digest
   before anything touches disk.
3. If the `wifi_geolocation` integration is installed and configured, the
   `.log` is parsed for AP sightings near the shot time, resolved to a
   lat/long via whichever backend(s) you enabled there, and written into
   the JPEG's EXIF `GPSLatitude`/`GPSLongitude` tags — asynchronously,
   after the photo is already safely received, so a slow/failed lookup
   never blocks delivery. If it's not installed, this step is skipped.
4. The photo is handed to whichever storage backend you configured
   (local/remote NAS, a shared folder for the Apple ecosystem, or one of
   the cloud destinations), wrapped in a spool/retry queue so a
   temporarily unreachable destination doesn't lose the upload.
5. Three events fire along the way — `eyefi_image_received`,
   `eyefi_image_geotagged`, `eyefi_image_stored` — both on eyefi_core's
   internal pub/sub bus and (via the adapter) on `hass.bus`, so automations
   can react at any stage.

## Installation

Neither `eyefi_core` nor `wifi_geolocation_core` are on PyPI yet, so each
integration's `manifest.json` points its `requirements` entry at this repo
directly:

- `custom_components/eyefi/manifest.json` →
  `eyefi-core @ git+https://github.com/dgtlrift/eye-fi-service-integration.git@main`
- `custom_components/wifi_geolocation/manifest.json` →
  `wifi-geolocation-core @ git+https://github.com/dgtlrift/eye-fi-service-integration.git@main#subdirectory=wifi_geolocation`

Once published to PyPI, those `requirements` entries should point there
instead.

1. Copy `custom_components/eyefi/` into your HA config's
   `custom_components/` directory. If you want geotagging, also copy
   `custom_components/wifi_geolocation/` there.
2. Restart Home Assistant so it installs each integration's Python package
   via its manifest's `requirements`.
3. **(Optional, do this first if you want geotagging)** Settings → Devices
   & Services → **Add Integration** → **WiFi Geolocation** → enable
   whichever backend(s) you want and enter their credentials (see
   [Geotagging](#geotagging) below).
4. Settings → Devices & Services → **Add Integration** → **Eye-Fi**.
5. Enter the card's MAC address and upload key (found in Eye-Fi Manager's
   `Settings.xml`, or on the card packaging), a local download/spool
   directory, and pick a storage destination. There's no geolocation API
   key to enter here — eyefi automatically uses WiFi Geolocation if it's
   installed.
6. To add more cards later, open the Eye-Fi integration's **Configure**
   button — the options flow lets you add further mac/upload-key pairs to
   the same entry. The same **Configure** button also has a **notify
   service** field for push notifications (see below) — leave it blank
   there to change only that without adding a card.

### Photo-import notifications

Optional: enter a notify service (initial setup, or later via
**Configure**) and eyefi pushes a notification through the Home
Assistant Companion App each time a photo finishes uploading, with the
filename and geotag result. Pairing a phone via the Companion App
auto-creates a `notify.<name>` service — find yours under **Developer
Tools → Actions** by searching "notify" (e.g. `mobile_app_jims_iphone`);
enter just the part after `notify.`. Leave it blank to disable. A
notification failure (a stale/renamed service, etc.) is logged but never
affects the upload pipeline itself — the same event-bus isolation that
already protects the HA event bridge (`eyefi_image_stored`) from a
misbehaving subscriber.

### Storage destinations

| Destination | Notes |
|---|---|
| `local_nas` (default) | Filesystem write — local disk or an SMB/NFS mount |
| `remote_nas` | SMB2/3 (`smbprotocol`) or SFTP (`asyncssh`) — no OS-level mount needed |
| `apple_dropfolder` | Writes to a shared folder; see [docs/apple-ecosystem-setup.md](docs/apple-ecosystem-setup.md) for the Mac Folder Action / iOS Shortcuts side |
| `google_photos` | `photoslibrary.appendonly` scope — upload-only since Google's March 2025 API changes |
| `onedrive` | Microsoft Graph API |
| `smugmug` | REST API v2, OAuth 1.0a |
| `backblaze` | B2 native API |
| `pcloud` | REST API, OAuth2 |

OAuth-based destinations currently expect a pre-obtained access token
pasted into the config flow rather than a full in-app OAuth2 redirect —
a reasonable v1 scope; HA's `application_credentials`/
`config_entry_oauth2_flow` helpers would be the natural next step for a
proper in-app authorization flow.

### Geotagging

Geotagging is handled entirely by the separate **WiFi Geolocation**
integration (`custom_components/wifi_geolocation`) — install it if you
want GPS coordinates resolved from the card's WiFi scan, skip it if you
don't. Its config flow lets you enable and order backends: normally a
draggable chip list (HA's frontend has supported this for the `select`
selector since 2023, but the Python-side schema never exposed it — see
`_selector_patch.py`'s docstring for the full story and the reason a
runtime patch is applied for it), falling back to one plain priority
number per backend (0 = disabled, 1+ = priority, lower tried first) if
that patch can't apply for any reason. Either way, they're tried in that
order at runtime, stopping at the first one that resolves a location.
Change it any time via the integration's **Configure** button —
reordering or adding/removing backends there doesn't require removing
and re-adding the integration. A backend that stays enabled keeps its
stored credentials by default (it's not re-prompted just for staying
enabled); to force one back into the credential-entry queue instead —
e.g. after rotating or fixing a revoked API key, or to add another Known
Networks entry (see below) — select it under **Configure**'s "Re-open
setup for" field, which only appears when at least one already-configured
backend has something to offer there. Every credential submitted
(initial setup, a newly-added backend, or a re-entered one) is verified
with a single live request before it's saved — only a confirmed
rejection (401/403) blocks saving, shown as an inline form error asking
to re-enter; anything else, including a network hiccup during the check
itself, is treated as "looks fine" so a good key can never be rejected on
a fluke. This is what would have caught the WiGLE 401 at Configure time
instead of during a live backfill run hitting WiGLE hundreds of times
with the same rejection.

**Known Networks** is a different kind of backend from the rest: a local,
free, instant lookup against a cache you maintain yourself (BSSID →
lat/long), never a network request. It exists because no crowd-sourced
database — free or paid — can ever really cover a private AP nobody's
ever wardriven past; if it's your own home router, you already know
where it is, so this backend just remembers that once instead of asking
an external service that will never have the answer. Enabling it prompts
for one network (BSSID, latitude, longitude, optional accuracy — default
100m); add more later via the same "Re-open setup for" field used for
credential replacement above. Its data lives in its own local JSON file
(`wifi_geolocation_known_networks.json` under HA's config directory), not
the config entry, so disabling the backend never deletes what's already
been added. Default priority order puts it first, since it's the only
backend that can never be rate-limited, cost money, or simply not have
your AP's data at any price.

| Backend | Notes |
|---|---|
| **Known Networks** | Free, local, no account. Your own manually-maintained BSSID → location cache — see above. |
| **BeaconDB** | Free, open, community-run — no account needed. |
| **WifiDB** | Free, open, community-run — no account needed. A single-maintainer "Beta" project with no SLA; unlike every other backend here it returns no accuracy figure at all, so a fixed conservative estimate (100m — typical outdoor WiFi AP range) is used instead. Uses its `search.php` endpoint, not the documented `locate.php`, which turned out to be dead code in practice (queries a table its own live scanner no longer populates). |
| **Mozilla Location Service** | Ichnaea-compatible. Mozilla's own public instance was shut down in 2024 — only useful pointed at a self-hosted Ichnaea instance; the base URL is configurable. |
| **Google Geolocation API** | Needs an API key, paid past the free tier. |
| **HERE Technologies Positioning API** | Needs an API key. |
| **Combain Positioning API** | Needs an API key. |
| **Unwired Labs LocationAPI** | Needs an API token; region-specific base URL (us1/eu1/...). |
| **WiGLE** | Free-tier BSSID lookups against a community-sourced war-driving database; needs an API name/token pair. Its daily query quota is easy to exhaust; a 429 response pauses all WiGLE lookups for 24h rather than continuing to hit an already-exhausted quota (see `wifi_geolocation_core/cooldown.py`) — other backends don't have this yet, but the same helper is trivial to apply if they start rate-limiting too. |

Any other integration (not just eyefi) can resolve WiFi APs to coordinates
the same way, by calling the `wifi_geolocation.resolve` service with a
list of `{bssid, signal_strength_dbm}` readings — see
`custom_components/wifi_geolocation/services.yaml`.

## Development

```console
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -e ./wifi_geolocation
pytest
```

Both `eyefi_core` and `wifi_geolocation_core` are fully testable standalone,
without a running HA instance. `custom_components/eyefi` and
`custom_components/wifi_geolocation` aren't covered end-to-end (that needs
the `homeassistant` package and a running HA core to exercise
meaningfully), but their config-flow schemas *are* tested — see
`tests/custom_components/`, which runs every schema through the real
`voluptuous_serialize.convert()` HA's frontend uses, without needing
`homeassistant` installed. This exists because of a real bug: a schema
validator that `voluptuous_serialize` can't handle causes a 500 error on
every "Add Integration" attempt, and that failure mode is invisible to
`py_compile` or a plain unit test — it only shows up against a real HA
instance otherwise.

## Credits

Read-only reference material used to document the wire protocol and
`.log` sidecar format — no code copied verbatim, and none of these were
forked:

- [`tachang/EyeFiServer`](https://github.com/tachang/EyeFiServer) — the
  original documented protocol (SOAP envelopes, credential flow); see
  `Documentation/EyeFi Protocol.txt`.
- [`dgrant/eyefiserver2`](https://github.com/dgrant/eyefiserver2) — Python
  fork with geotagging already implemented; primary source for the `.log`
  format and Google Geolocation API usage.
- [`usefulthink/node-eyefi`](https://github.com/usefulthink/node-eyefi) —
  JS protocol implementation, initial reference.
- [`ryantm/heyefi`](https://github.com/ryantm/heyefi) — Haskell, archived;
  config schema (mac address + upload key per card) reference only.

## License

MIT, for `eyefi_core`, `wifi_geolocation_core`, and both HA adapters — see
[LICENSE](LICENSE).
