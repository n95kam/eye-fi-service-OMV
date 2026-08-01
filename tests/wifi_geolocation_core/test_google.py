import pytest

from _fakes import fake_session
from wifi_geolocation_core.google import GOOGLE_GEOLOCATION_URL, GoogleGeolocationBackend
from wifi_geolocation_core.models import AccessPoint, Coordinates

AP = [AccessPoint(bssid="0018560304f8", signal_strength_dbm=-65)]


@pytest.mark.asyncio
async def test_google_sends_wifi_access_points_shape_and_api_key():
    session = fake_session(200, {"location": {"lat": 1.0, "lng": 2.0}, "accuracy": 10.0})
    backend = GoogleGeolocationBackend(api_key="k", session=session)

    result = await backend.resolve(AP)

    assert result == Coordinates(latitude=1.0, longitude=2.0, accuracy_m=10.0)
    request = session.requests[0]
    assert request["url"] == GOOGLE_GEOLOCATION_URL
    assert request["params"] == {"key": "k"}


@pytest.mark.asyncio
async def test_google_returns_none_on_non_200():
    session = fake_session(403, {})
    backend = GoogleGeolocationBackend(api_key="k", session=session)
    assert await backend.resolve(AP) is None


@pytest.mark.asyncio
async def test_google_verify_credentials_false_on_401_or_403():
    for status in (401, 403):
        session = fake_session(status, {})
        backend = GoogleGeolocationBackend(api_key="k", session=session)
        assert await backend.verify_credentials() is False


@pytest.mark.asyncio
async def test_google_verify_credentials_true_on_200():
    session = fake_session(200, {"location": {"lat": 1.0, "lng": 2.0}})
    backend = GoogleGeolocationBackend(api_key="k", session=session)
    assert await backend.verify_credentials() is True
