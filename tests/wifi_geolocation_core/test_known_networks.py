import json

import pytest

from wifi_geolocation_core.known_networks import (
    DEFAULT_ACCURACY_M,
    SOURCE_MANUAL,
    KnownNetworksGeolocationBackend,
)
from wifi_geolocation_core.models import AccessPoint, Coordinates

AP_HOME = AccessPoint(bssid="0018560304f8", signal_strength_dbm=-40)
AP_UNKNOWN = AccessPoint(bssid="aabbccddeeff", signal_strength_dbm=-70)


@pytest.mark.asyncio
async def test_returns_none_when_no_known_networks_match(tmp_path):
    backend = KnownNetworksGeolocationBackend(store_path=tmp_path / "known.json")
    assert await backend.resolve([AP_UNKNOWN]) is None


@pytest.mark.asyncio
async def test_add_then_resolve_round_trips(tmp_path):
    backend = KnownNetworksGeolocationBackend(store_path=tmp_path / "known.json")
    await backend.add("0018560304f8", latitude=1.0, longitude=2.0, accuracy_m=15.0)

    result = await backend.resolve([AP_HOME])

    assert result == Coordinates(latitude=1.0, longitude=2.0, accuracy_m=15.0)


@pytest.mark.asyncio
async def test_unknown_ap_among_known_ones_is_ignored_not_a_failure(tmp_path):
    backend = KnownNetworksGeolocationBackend(store_path=tmp_path / "known.json")
    await backend.add("0018560304f8", latitude=1.0, longitude=2.0)

    result = await backend.resolve([AP_HOME, AP_UNKNOWN])

    assert result == Coordinates(latitude=1.0, longitude=2.0, accuracy_m=DEFAULT_ACCURACY_M)


@pytest.mark.asyncio
async def test_weighted_centroid_across_multiple_known_aps(tmp_path):
    backend = KnownNetworksGeolocationBackend(store_path=tmp_path / "known.json")
    strong = AccessPoint(bssid="0018560304f8", signal_strength_dbm=-30)
    weak = AccessPoint(bssid="aabbccddeeff", signal_strength_dbm=-90)
    await backend.add("0018560304f8", latitude=0.0, longitude=0.0)
    await backend.add("aabbccddeeff", latitude=10.0, longitude=10.0)

    result = await backend.resolve([strong, weak])

    # Much stronger signal should pull the centroid close to (0, 0).
    assert result.latitude < 1.0
    assert result.longitude < 1.0


@pytest.mark.asyncio
async def test_accuracy_is_least_precise_among_contributors_not_averaged(tmp_path):
    backend = KnownNetworksGeolocationBackend(store_path=tmp_path / "known.json")
    ap_a = AccessPoint(bssid="0018560304f8", signal_strength_dbm=-50)
    ap_b = AccessPoint(bssid="aabbccddeeff", signal_strength_dbm=-50)
    await backend.add("0018560304f8", latitude=0.0, longitude=0.0, accuracy_m=10.0)
    await backend.add("aabbccddeeff", latitude=0.0, longitude=0.0, accuracy_m=100.0)

    result = await backend.resolve([ap_a, ap_b])

    assert result.accuracy_m == 100.0


@pytest.mark.asyncio
async def test_add_overwrites_existing_record_for_same_bssid(tmp_path):
    backend = KnownNetworksGeolocationBackend(store_path=tmp_path / "known.json")
    await backend.add("0018560304f8", latitude=1.0, longitude=1.0)
    await backend.add("0018560304f8", latitude=9.0, longitude=9.0)

    result = await backend.resolve([AP_HOME])

    assert result == Coordinates(latitude=9.0, longitude=9.0, accuracy_m=DEFAULT_ACCURACY_M)


@pytest.mark.asyncio
async def test_remove_deletes_a_record(tmp_path):
    backend = KnownNetworksGeolocationBackend(store_path=tmp_path / "known.json")
    await backend.add("0018560304f8", latitude=1.0, longitude=1.0)
    await backend.remove("0018560304f8")

    assert await backend.resolve([AP_HOME]) is None


@pytest.mark.asyncio
async def test_list_all_returns_stored_records_keyed_by_colon_bssid(tmp_path):
    backend = KnownNetworksGeolocationBackend(store_path=tmp_path / "known.json")
    await backend.add("0018560304f8", latitude=1.0, longitude=2.0, accuracy_m=15.0)

    networks = await backend.list_all()

    assert networks == {
        "00:18:56:03:04:f8": {
            "latitude": 1.0,
            "longitude": 2.0,
            "accuracy_m": 15.0,
            "source": SOURCE_MANUAL,
            "last_seen": networks["00:18:56:03:04:f8"]["last_seen"],
        }
    }


@pytest.mark.asyncio
async def test_survives_a_missing_store_file(tmp_path):
    backend = KnownNetworksGeolocationBackend(store_path=tmp_path / "does_not_exist.json")
    assert await backend.resolve([AP_HOME]) is None


@pytest.mark.asyncio
async def test_survives_a_corrupt_store_file(tmp_path):
    store_path = tmp_path / "known.json"
    store_path.write_text("{not valid json")
    backend = KnownNetworksGeolocationBackend(store_path=store_path)

    assert await backend.resolve([AP_HOME]) is None


@pytest.mark.asyncio
async def test_persists_across_backend_instances(tmp_path):
    store_path = tmp_path / "known.json"
    await KnownNetworksGeolocationBackend(store_path=store_path).add(
        "0018560304f8", latitude=1.0, longitude=2.0
    )

    reloaded = KnownNetworksGeolocationBackend(store_path=store_path)
    result = await reloaded.resolve([AP_HOME])

    assert result == Coordinates(latitude=1.0, longitude=2.0, accuracy_m=DEFAULT_ACCURACY_M)
    assert json.loads(store_path.read_text())  # wrote real, parseable JSON
