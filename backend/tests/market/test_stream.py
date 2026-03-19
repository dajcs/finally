"""Tests for SSE streaming endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


def _make_request(disconnects_after: int = 1) -> MagicMock:
    """Create a mock Request that reports disconnected after N is_disconnected() calls."""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    # Returns False for the first (disconnects_after) calls, then True
    side_effects = [False] * disconnects_after + [True]
    request.is_disconnected = AsyncMock(side_effect=side_effects)
    return request


@pytest.mark.asyncio
class TestGenerateEvents:
    """Unit tests for the _generate_events async generator."""

    async def test_first_event_is_retry_directive(self):
        """First yielded value must be the SSE retry directive."""
        cache = PriceCache()
        cache.update("AAPL", 190.0)
        request = _make_request(disconnects_after=1)

        events = []
        async for event in _generate_events(cache, request, interval=0.01):
            events.append(event)

        assert events[0] == "retry: 1000\n\n"

    async def test_data_event_contains_prices(self):
        """A data event should contain JSON-serialized prices for all cached tickers."""
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        cache.update("GOOGL", 175.25)
        request = _make_request(disconnects_after=1)

        events = []
        async for event in _generate_events(cache, request, interval=0.01):
            events.append(event)

        data_events = [e for e in events if e.startswith("data:")]
        assert len(data_events) >= 1

        payload = json.loads(data_events[0][5:])
        assert "AAPL" in payload
        assert "GOOGL" in payload
        assert payload["AAPL"]["price"] == 190.50
        assert payload["GOOGL"]["price"] == 175.25

    async def test_data_event_structure(self):
        """Each price entry in the data event must have the expected keys."""
        cache = PriceCache()
        cache.update("AAPL", 190.0)
        request = _make_request(disconnects_after=1)

        events = []
        async for event in _generate_events(cache, request, interval=0.01):
            events.append(event)

        data_events = [e for e in events if e.startswith("data:")]
        payload = json.loads(data_events[0][5:])
        entry = payload["AAPL"]
        expected_keys = {"ticker", "price", "previous_price", "timestamp", "change", "change_percent", "direction"}
        assert set(entry.keys()) == expected_keys

    async def test_no_data_event_when_cache_empty(self):
        """No data event should be sent when the cache is empty."""
        cache = PriceCache()  # empty
        request = _make_request(disconnects_after=1)

        events = []
        async for event in _generate_events(cache, request, interval=0.01):
            events.append(event)

        data_events = [e for e in events if e.startswith("data:")]
        assert len(data_events) == 0

    async def test_disconnect_stops_generator(self):
        """Generator should stop when the client disconnects."""
        cache = PriceCache()
        cache.update("AAPL", 190.0)
        # Disconnect immediately (0 non-disconnect calls)
        request = _make_request(disconnects_after=0)

        events = []
        async for event in _generate_events(cache, request, interval=0.01):
            events.append(event)

        # Only the retry directive, no data events
        assert events == ["retry: 1000\n\n"]

    async def test_no_duplicate_events_on_same_version(self):
        """No data event should be sent if the cache version hasn't changed."""
        cache = PriceCache()
        cache.update("AAPL", 190.0)

        # Allow two loop iterations without a version change in between
        request = _make_request(disconnects_after=2)

        events = []
        async for event in _generate_events(cache, request, interval=0.01):
            events.append(event)

        data_events = [e for e in events if e.startswith("data:")]
        # Only one data event — version didn't change between the two iterations
        assert len(data_events) == 1


class TestCreateStreamRouter:
    """Tests for the create_stream_router factory."""

    def test_factory_creates_new_router_each_call(self):
        """Each call to create_stream_router must return a distinct router instance."""
        cache = PriceCache()
        router1 = create_stream_router(cache)
        router2 = create_stream_router(cache)
        assert router1 is not router2

    def test_router_has_prices_route(self):
        """The returned router must include a GET /prices route."""
        cache = PriceCache()
        router = create_stream_router(cache)
        routes = [r.path for r in router.routes]
        assert any("/prices" in path for path in routes)
