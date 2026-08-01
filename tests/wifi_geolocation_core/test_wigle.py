import pytest

from _fakes import RaisingSession, fake_session
from wifi_geolocation_core.models import AccessPoint, Coordinates
from wifi_geolocation_core.wigle import WigleGeolocationBackend

AP = [AccessPoint(bssid="0018560304f8", signal_strength_dbm=-65)]


@pytest.mark.asyncio
async def test_wigle_resolves_from_matching_result():
    session = fake_session(200, {"results": [{"trilat": 1.0, "trilong": 2.0}]})
    backend = WigleGeolocationBackend(api_name="n", api_token="t", session=session)

    result = await backend.resolve(AP)

    assert result == Coordinates(latitude=1.0, longitude=2.0)


@pytest.mark.asyncio
async def test_wigle_returns_none_when_no_results():
    session = fake_session(200, {"results": []})
    backend = WigleGeolocationBackend(api_name="n", api_token="t", session=session)

    assert await backend.resolve(AP) is None


@pytest.mark.asyncio
async def test_wigle_429_triggers_cooldown_and_returns_none():
    session = fake_session(429, {"success": False, "message": "too many queries today"})
    backend = WigleGeolocationBackend(api_name="n", api_token="t", session=session)

    assert await backend.resolve(AP) is None
    assert backend._cooldown.active() is True


@pytest.mark.asyncio
async def test_wigle_skips_lookup_entirely_while_in_cooldown():
    session = fake_session(429, {"success": False, "message": "too many queries today"})
    backend = WigleGeolocationBackend(api_name="n", api_token="t", session=session)

    await backend.resolve(AP)  # triggers the cooldown
    request_count_after_first_call = len(session.requests)

    result = await backend.resolve(AP)

    assert result is None
    assert len(session.requests) == request_count_after_first_call  # no new requests made


@pytest.mark.asyncio
async def test_wigle_verify_credentials_false_on_401():
    session = fake_session(401, {"success": False, "message": "not authorized"})
    backend = WigleGeolocationBackend(api_name="n", api_token="t", session=session)

    assert await backend.verify_credentials() is False


@pytest.mark.asyncio
async def test_wigle_verify_credentials_true_on_200():
    session = fake_session(200, {"results": []})
    backend = WigleGeolocationBackend(api_name="n", api_token="t", session=session)

    assert await backend.verify_credentials() is True


@pytest.mark.asyncio
async def test_wigle_verify_credentials_true_and_does_not_raise_on_timeout():
    # Inconclusive (e.g. a network hiccup during the check itself) must
    # not block saving a credential that might be perfectly valid.
    session = RaisingSession(TimeoutError())
    backend = WigleGeolocationBackend(api_name="n", api_token="t", session=session)

    assert await backend.verify_credentials() is True


@pytest.mark.asyncio
async def test_wigle_timeout_on_one_ap_does_not_crash_resolve():
    # aiohttp.ClientTimeout(total=...) raises a bare TimeoutError, not an
    # aiohttp.ClientError subclass -- same fix/rationale as WifiDB's.
    many_aps = [
        AccessPoint(bssid="0018560304f8", signal_strength_dbm=-65),
        AccessPoint(bssid="001122334455", signal_strength_dbm=-70),
    ]
    session = RaisingSession(TimeoutError())
    backend = WigleGeolocationBackend(api_name="n", api_token="t", session=session)

    result = await backend.resolve(many_aps)

    assert result is None
    assert len(session.requests) == 2  # kept going past the timeout


@pytest.mark.asyncio
async def test_wigle_429_stops_trying_remaining_access_points():
    many_aps = [
        AccessPoint(bssid="0018560304f8", signal_strength_dbm=-65),
        AccessPoint(bssid="001122334455", signal_strength_dbm=-70),
        AccessPoint(bssid="aabbccddeeff", signal_strength_dbm=-80),
    ]
    session = fake_session(429, {"success": False, "message": "too many queries today"})
    backend = WigleGeolocationBackend(api_name="n", api_token="t", session=session)

    await backend.resolve(many_aps)

    assert len(session.requests) == 1  # stopped after the first 429, didn't try the rest
