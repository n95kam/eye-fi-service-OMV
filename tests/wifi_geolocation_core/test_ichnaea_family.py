import pytest

from _fakes import RaisingSession, fake_session
from wifi_geolocation_core.beacondb import BEACONDB_URL, BeaconDbGeolocationBackend
from wifi_geolocation_core.combain import COMBAIN_URL, CombainGeolocationBackend
from wifi_geolocation_core.models import AccessPoint, Coordinates
from wifi_geolocation_core.mozilla import MOZILLA_MLS_URL, MozillaGeolocationBackend

AP = [AccessPoint(bssid="0018560304f8", signal_strength_dbm=-65)]


@pytest.mark.asyncio
async def test_combain_resolves_and_sends_api_key():
    session = fake_session(200, {"location": {"lat": 1.0, "lng": 2.0}, "accuracy": 10.0})
    backend = CombainGeolocationBackend(api_key="k", session=session)

    result = await backend.resolve(AP)

    assert result == Coordinates(latitude=1.0, longitude=2.0, accuracy_m=10.0)
    assert session.requests[0]["url"] == COMBAIN_URL
    assert session.requests[0]["params"] == {"key": "k"}


@pytest.mark.asyncio
async def test_beacondb_resolves_without_api_key():
    session = fake_session(200, {"location": {"lat": 3.0, "lng": 4.0}})
    backend = BeaconDbGeolocationBackend(session=session)

    result = await backend.resolve(AP)

    assert result == Coordinates(latitude=3.0, longitude=4.0, accuracy_m=None)
    assert session.requests[0]["url"] == BEACONDB_URL
    assert session.requests[0]["params"] == {}  # no key sent


@pytest.mark.asyncio
async def test_mozilla_defaults_to_public_url_but_is_overridable():
    session = fake_session(200, {"location": {"lat": 5.0, "lng": 6.0}})
    backend = MozillaGeolocationBackend(session=session)
    assert backend.base_url == MOZILLA_MLS_URL

    custom = MozillaGeolocationBackend(session=session, base_url="https://my-ichnaea.example/v1/geolocate")
    result = await custom.resolve(AP)

    assert result == Coordinates(latitude=5.0, longitude=6.0, accuracy_m=None)
    assert session.requests[0]["url"] == "https://my-ichnaea.example/v1/geolocate"


@pytest.mark.asyncio
async def test_ichnaea_family_returns_none_on_missing_location():
    session = fake_session(200, {})
    assert await CombainGeolocationBackend(api_key="k", session=session).resolve(AP) is None


@pytest.mark.asyncio
async def test_ichnaea_family_returns_none_on_non_200():
    session = fake_session(403, {})
    assert await CombainGeolocationBackend(api_key="k", session=session).resolve(AP) is None


@pytest.mark.asyncio
async def test_ichnaea_family_returns_none_on_404_not_found(caplog):
    # Google's Geolocation API (and Ichnaea, which BeaconDB/Combain/Mozilla
    # all mirror) responds 404 specifically to mean "none of these access
    # points are in the database" -- confirmed live against BeaconDB, which
    # returns this for every genuinely-private AP. Must resolve to None
    # without being logged as a warning-level error like a real failure.
    session = fake_session(404, {"error": {"code": 404, "message": "Not found"}})

    with caplog.at_level("WARNING"):
        result = await BeaconDbGeolocationBackend(session=session).resolve(AP)

    assert result is None
    assert not any(record.levelname == "WARNING" for record in caplog.records)


@pytest.mark.asyncio
async def test_ichnaea_family_verify_credentials_false_on_401_or_403():
    session_401 = fake_session(401, {})
    session_403 = fake_session(403, {})

    assert await CombainGeolocationBackend(api_key="k", session=session_401).verify_credentials() is False
    assert await CombainGeolocationBackend(api_key="k", session=session_403).verify_credentials() is False


@pytest.mark.asyncio
async def test_ichnaea_family_verify_credentials_true_on_200_or_404():
    session_200 = fake_session(200, {"location": {"lat": 1.0, "lng": 2.0}})
    session_404 = fake_session(404, {"error": {"code": 404}})

    assert await CombainGeolocationBackend(api_key="k", session=session_200).verify_credentials() is True
    assert await CombainGeolocationBackend(api_key="k", session=session_404).verify_credentials() is True


@pytest.mark.asyncio
async def test_ichnaea_family_verify_credentials_true_and_does_not_raise_on_timeout():
    session = RaisingSession(TimeoutError())
    assert await CombainGeolocationBackend(api_key="k", session=session).verify_credentials() is True


@pytest.mark.asyncio
async def test_ichnaea_family_timeout_does_not_crash_resolve():
    # aiohttp.ClientTimeout(total=...) raises a bare TimeoutError, not an
    # aiohttp.ClientError subclass -- same fix/rationale as WiGLE/WifiDB.
    session = RaisingSession(TimeoutError())
    assert await BeaconDbGeolocationBackend(session=session).resolve(AP) is None
