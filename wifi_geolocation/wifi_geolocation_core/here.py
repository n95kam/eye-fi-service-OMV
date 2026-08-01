"""HERE Technologies Positioning API backend.

Different request shape than the Ichnaea family: a "wlan" array of
{"mac", "rss"} rather than "wifiAccessPoints" of {"macAddress",
"signalStrength"}. Verify field casing/response shape against HERE's
current API docs before relying on this in production -- implemented from
documented parameter names, not tested against a live HERE account.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import aiohttp

from wifi_geolocation_core.models import AccessPoint, Coordinates

_LOGGER = logging.getLogger(__name__)

HERE_POSITIONING_URL = "https://pos.ls.hereapi.com/positioning/v1/locate"


@dataclass(frozen=True, slots=True)
class HereGeolocationBackend:
    api_key: str
    session: aiohttp.ClientSession

    async def verify_credentials(self) -> bool:
        """Cheap single-request check with a dummy all-zero MAC; only a
        confirmed 401/403 counts as invalid -- same rationale as
        WigleGeolocationBackend.verify_credentials. Not live-verified
        against a real HERE account (see module docstring); 401/403 is
        the standard REST auth-failure convention, so this is a safe
        default even unverified -- worst case it just never fires."""
        payload = {"wlan": [{"mac": "000000000000", "rss": -100}]}
        try:
            async with self.session.post(
                HERE_POSITIONING_URL,
                params={"apiKey": self.api_key},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status not in (401, 403)
        except (aiohttp.ClientError, TimeoutError):
            return True

    async def resolve(self, access_points: list[AccessPoint]) -> Coordinates | None:
        payload = {
            "wlan": [
                {"mac": ap.bssid.replace(":", "").upper(), "rss": ap.signal_strength_dbm}
                for ap in access_points
            ]
        }
        try:
            async with self.session.post(
                HERE_POSITIONING_URL,
                params={"apiKey": self.api_key},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("HERE Positioning API returned HTTP %s", resp.status)
                    return None
                body = await resp.json()
        except aiohttp.ClientError:
            _LOGGER.exception("HERE Positioning API request failed")
            return None

        location = body.get("location")
        if not location:
            return None
        return Coordinates(
            latitude=location["lat"],
            longitude=location["lng"],
            accuracy_m=location.get("accuracy"),
        )
