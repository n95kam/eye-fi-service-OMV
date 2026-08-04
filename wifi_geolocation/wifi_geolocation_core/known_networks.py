"""Locally-cached, user-maintained WiFi AP -> location lookup.

Checked the same way as any other backend (a signal-strength-weighted
centroid across whichever BSSIDs it recognizes), but never makes a
network request -- it only knows what's been written to its local JSON
store. Exists for the case no crowd-sourced database (free or paid) can
ever really solve: a private home AP that no one else has ever wardriven
past, so it simply isn't in anyone else's database at any price. The
user's own APs are exactly the ones they already know the location of --
this backend just remembers that, once, and never needs those AP's
locations from anywhere else again.

The record shape (``source``, ``last_seen``) is deliberately richer than
today's single-instance use needs, anticipating a future opt-in,
crowd-sourced sync between separate HAOS instances -- the same fields a
shared store would also need. No networking of any kind is implemented
yet; this is purely local.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from wifi_geolocation_core.models import AccessPoint, Coordinates, format_bssid

_LOGGER = logging.getLogger(__name__)

# Used when a manually-entered network has no better estimate available --
# same rationale/value as wifidb.py's DEFAULT_ACCURACY_M.
DEFAULT_ACCURACY_M = 100.0

SOURCE_MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class KnownNetworksGeolocationBackend:
    store_path: Path

    async def resolve(self, access_points: list[AccessPoint]) -> Coordinates | None:
        networks = await self._load()
        weighted_points: list[tuple[float, float, float]] = []
        accuracies: list[float] = []

        for ap in access_points:
            record = networks.get(format_bssid(ap.bssid))
            if record is None:
                continue
            weight = 10 ** (ap.signal_strength_dbm / 10)
            weighted_points.append((record["latitude"], record["longitude"], weight))
            accuracies.append(record["accuracy_m"])

        if not weighted_points:
            return None

        total_weight = sum(w for _, _, w in weighted_points)
        lat = sum(lat * w for lat, _, w in weighted_points) / total_weight
        lon = sum(lon * w for _, lon, w in weighted_points) / total_weight
        # Least-precise (largest) figure among contributing records, not an
        # average -- conservative, matching WifiDB's worst-case philosophy.
        return Coordinates(latitude=lat, longitude=lon, accuracy_m=max(accuracies))

    async def add(
        self,
        bssid: str,
        *,
        latitude: float,
        longitude: float,
        accuracy_m: float = DEFAULT_ACCURACY_M,
        source: str = SOURCE_MANUAL,
    ) -> None:
        """Record (or replace) a BSSID -> location mapping."""
        networks = await self._load()
        networks[format_bssid(bssid)] = {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy_m": accuracy_m,
            "source": source,
            "last_seen": time.time(),
        }
        await self._save(networks)

    async def remove(self, bssid: str) -> None:
        networks = await self._load()
        if networks.pop(format_bssid(bssid), None) is not None:
            await self._save(networks)

    async def list_all(self) -> dict[str, dict]:
        return await self._load()

    async def _load(self) -> dict[str, dict]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._load_sync)

    def _load_sync(self) -> dict[str, dict]:
        if not self.store_path.is_file():
            return {}
        try:
            return json.loads(self.store_path.read_text())
        except (json.JSONDecodeError, OSError):
            _LOGGER.exception("Could not read known-networks cache at %s", self.store_path)
            return {}

    async def _save(self, networks: dict[str, dict]) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_sync, networks)

    def _save_sync(self, networks: dict[str, dict]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        # Write-then-atomic-replace: a crash mid-write can never leave a
        # truncated/corrupt cache file behind.
        tmp_path = self.store_path.with_suffix(self.store_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(networks, indent=2, sort_keys=True))
        tmp_path.replace(self.store_path)
