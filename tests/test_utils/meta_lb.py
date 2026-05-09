import asyncio

import httpx
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tuna.router import meta_lb


def mock_response(mocker, *, content=b"ok", status_code=200, headers=None):
    """Create a mock httpx.Response compatible with async streaming."""
    if headers is None:
        headers = {}

    async def _aiter_bytes(chunk_size=4096):
        yield content

    resp = mocker.AsyncMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = httpx.Headers(headers)
    resp.aiter_bytes = _aiter_bytes
    resp.aclose = mocker.AsyncMock()
    return resp


def reset_state():
    """Reset all mutable module state for clean tests."""
    meta_lb._serverless_base_url = ""
    meta_lb._skyserve_base_url = ""
    meta_lb._spot_state = meta_lb.SpotState.COLD
    meta_lb._warming_task = None
    meta_lb._last_probe_ts = None
    meta_lb._last_probe_err = None
    meta_lb._req_total = 0
    meta_lb._req_to_spot = 0
    meta_lb._req_to_serverless = 0
    meta_lb._rejected_count = 0
    meta_lb._recent_routes.clear()
    meta_lb._gpu_seconds_spot = 0.0
    meta_lb._gpu_seconds_serverless = 0.0
    meta_lb._spot_ready_cumulative_s = 0.0
    meta_lb._spot_ready_since = None
    meta_lb._last_real_request_ts = 0.0
    meta_lb._ttft = 0

    # failover metrics
    meta_lb._spot_failover_count = 0
    meta_lb._last_spot_failover_timestamp = None
    meta_lb._spot_failover_timestamps.clear()
    meta_lb._failover_latencies.clear()

    # Ensure we have a fresh asyncio lock
    meta_lb._state_lock = asyncio.Lock()
    meta_lb._request_semaphore = asyncio.Semaphore(
        meta_lb.MAX_CONCURRENT_REQUESTS
    )


@pytest_asyncio.fixture
async def client():
    """httpx async test client with clean state per test."""

    reset_state()

    meta_lb._http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=2.0,
            read=30.0,
            write=10.0,
            pool=5.0,
        ),
        limits=httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
        ),
        follow_redirects=True,
    )

    # Disable auth for tests
    original_key = meta_lb.API_KEY
    meta_lb.API_KEY = ""

    async with AsyncClient(
        transport=ASGITransport(app=meta_lb.app),
        base_url="http://test",
    ) as c:
        yield c

    meta_lb.API_KEY = original_key

    if meta_lb._http_client:
        await meta_lb._http_client.aclose()
        meta_lb._http_client = None