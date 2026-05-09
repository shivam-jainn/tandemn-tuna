"""Tests for tuna.router.meta_lb spot failover behavior."""

import httpx
import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import client, mock_response


class TestSpotFailoverRetry:
    @pytest.mark.asyncio
    async def test_spot_connection_error_retries_on_serverless(self, client, mocker):
        """When spot fails with connection error, retry on serverless."""
        await meta_lb.set_serverless_url("http://serverless.example.com")
        await meta_lb.set_spot_url("http://spot.example.com")
        await meta_lb._set_state(meta_lb.SpotState.READY)

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.side_effect = [
            httpx.ConnectError("spot died"),
            mock_response(
                mocker, content=b'{"ok":true}', status_code=200,
                headers={"content-type": "application/json"},
            ),
        ]
        resp = await client.post("/v1/chat/completions", json={"prompt": "hi"})
        assert resp.status_code == 200
        assert not await meta_lb._is_ready()
        assert meta_lb._spot_state == meta_lb.SpotState.COLD

    @pytest.mark.asyncio
    async def test_spot_5xx_retries_on_serverless(self, client, mocker):
        """When spot returns 500, retry on serverless."""
        await meta_lb.set_serverless_url("http://serverless.example.com")
        await meta_lb.set_spot_url("http://spot.example.com")
        await meta_lb._set_state(meta_lb.SpotState.READY)

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.side_effect = [
            mock_response(mocker, content=b"error", status_code=500),
            mock_response(
                mocker, content=b'{"ok":true}', status_code=200,
                headers={"content-type": "application/json"},
            ),
        ]
        resp = await client.post("/v1/chat/completions", json={"prompt": "hi"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_spot_failure_no_serverless_returns_502(self, client, mocker):
        """When spot fails and no serverless configured, return 502."""
        await meta_lb.set_spot_url("http://spot.example.com")
        await meta_lb._set_state(meta_lb.SpotState.READY)

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.side_effect = httpx.ConnectError("spot died")
        resp = await client.post("/v1/chat/completions", json={"prompt": "hi"})
        assert resp.status_code == 502

    @pytest.mark.asyncio
    async def test_serverless_failure_no_retry(self, client, mocker):
        """When serverless fails, don't retry on spot."""
        await meta_lb.set_serverless_url("http://serverless.example.com")
        await meta_lb._set_state(meta_lb.SpotState.COLD)

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.side_effect = httpx.ConnectError("serverless died")
        resp = await client.post("/v1/chat/completions", json={"prompt": "hi"})
        assert resp.status_code == 502
        assert mock_send.call_count == 1

    @pytest.mark.asyncio
    async def test_spot_4xx_no_retry(self, client, mocker):
        """Client errors (4xx) from spot are NOT retried."""
        await meta_lb.set_serverless_url("http://serverless.example.com")
        await meta_lb.set_spot_url("http://spot.example.com")
        await meta_lb._set_state(meta_lb.SpotState.READY)

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(
            mocker, content=b"bad request", status_code=400,
            headers={"content-type": "text/plain"},
        )
        resp = await client.post("/v1/chat/completions", json={"prompt": "hi"})
        assert resp.status_code == 400
        assert mock_send.call_count == 1
