"""Tests for tuna.router.meta_lb route stats and backpressure."""

import asyncio
import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import client, mock_response


class TestRouteStats:
    @pytest.mark.asyncio
    async def test_stats_increment(self, client, mocker):
        await meta_lb.set_serverless_url("http://serverless.example.com")

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(mocker)

        for _ in range(5):
            await client.get("/test")

        stats = await meta_lb._route_stats()
        assert stats["total"] == 5
        assert stats["serverless"] == 5
        assert stats["spot"] == 0


class TestBackpressure:
    @pytest.mark.asyncio
    async def test_under_limit_succeeds(self, client, mocker):
        await meta_lb.set_serverless_url("http://serverless.example.com")

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(mocker)

        resp = await client.get("/v1/models")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_over_limit_returns_429(self, client):
        await meta_lb.set_serverless_url("http://serverless.example.com")

        meta_lb._request_semaphore = asyncio.Semaphore(1)
        await meta_lb._request_semaphore.acquire()

        resp = await client.get("/v1/models")
        assert resp.status_code == 429
        data = resp.json()
        assert data["error"] == "router_overloaded"

        meta_lb._request_semaphore.release()

    @pytest.mark.asyncio
    async def test_429_includes_retry_after(self, client):
        await meta_lb.set_serverless_url("http://serverless.example.com")

        meta_lb._request_semaphore = asyncio.Semaphore(1)
        await meta_lb._request_semaphore.acquire()

        resp = await client.get("/v1/models")
        assert resp.status_code == 429
        assert resp.headers["retry-after"] == "1"

        meta_lb._request_semaphore.release()

    @pytest.mark.asyncio
    async def test_rejected_count_tracked(self, client):
        await meta_lb.set_serverless_url("http://serverless.example.com")

        meta_lb._request_semaphore = asyncio.Semaphore(1)
        await meta_lb._request_semaphore.acquire()

        await client.get("/v1/models")
        await client.get("/v1/models")

        stats = await meta_lb._route_stats()
        assert stats["rejected"] == 2

        meta_lb._request_semaphore.release()
