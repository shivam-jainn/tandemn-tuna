"""Tests for tuna.router.meta_lb routing decisions."""

import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import client, mock_response


class TestRoutingDecision:
    @pytest.mark.asyncio
    async def test_routes_to_serverless_when_spot_not_ready(self, client, mocker):
        await meta_lb.set_serverless_url("http://serverless.example.com")
        await meta_lb.set_spot_url("http://spot.example.com")
        await meta_lb._set_state(meta_lb.SpotState.COLD)

        mocker.patch.object(meta_lb, "_enter_warming", new_callable=mocker.AsyncMock)

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(
            mocker, content=b'{"ok": true}', status_code=200,
            headers={"content-type": "application/json"},
        )

        resp = await client.post("/v1/chat/completions", json={"prompt": "hi"})
        assert resp.status_code == 200

        called_request = mock_send.call_args[0][0]
        assert str(called_request.url).startswith("http://serverless.example.com/")
        assert meta_lb._req_to_serverless == 1

    @pytest.mark.asyncio
    async def test_routes_to_spot_when_ready(self, client, mocker):
        await meta_lb.set_serverless_url("http://serverless.example.com")
        await meta_lb.set_spot_url("http://spot.example.com")
        await meta_lb._set_state(meta_lb.SpotState.READY)

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(
            mocker, content=b'{"ok": true}', status_code=200,
            headers={"content-type": "application/json"},
        )

        resp = await client.post("/v1/chat/completions", json={"prompt": "hi"})
        assert resp.status_code == 200

        called_request = mock_send.call_args[0][0]
        assert str(called_request.url).startswith("http://spot.example.com/")
        assert meta_lb._req_to_spot == 1

    @pytest.mark.asyncio
    async def test_preserves_query_string(self, client, mocker):
        await meta_lb.set_serverless_url("http://serverless.example.com")

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(
            mocker, content=b"ok", status_code=200,
            headers={"content-type": "text/plain"},
        )

        resp = await client.get("/v1/models?foo=bar")
        called_request = mock_send.call_args[0][0]
        assert "foo=bar" in str(called_request.url)

    @pytest.mark.asyncio
    async def test_triggers_warming_on_serverless_route_when_spot_cold(self, client, mocker):
        await meta_lb.set_serverless_url("http://serverless.example.com")
        await meta_lb.set_spot_url("http://spot.example.com")
        await meta_lb._set_state(meta_lb.SpotState.COLD)

        mock_warming = mocker.patch.object(
            meta_lb, "_enter_warming", new_callable=mocker.AsyncMock,
        )
        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(mocker)

        await client.get("/v1/models")
        mock_warming.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_warming_when_already_warming(self, client, mocker):
        await meta_lb.set_serverless_url("http://serverless.example.com")
        await meta_lb.set_spot_url("http://spot.example.com")
        meta_lb._spot_state = meta_lb.SpotState.WARMING

        mock_warming = mocker.patch.object(
            meta_lb, "_enter_warming", new_callable=mocker.AsyncMock,
        )
        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(mocker)

        await client.get("/v1/models")
        mock_warming.assert_not_called()
