"""Tests for tuna.router.meta_lb authentication."""

import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import client, mock_response


class TestAuth:
    @pytest.mark.asyncio
    async def test_rejects_missing_key(self, client):
        meta_lb.API_KEY = "secret123"
        await meta_lb.set_serverless_url("http://serverless.example.com")

        resp = await client.get("/v1/models")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_accepts_correct_key(self, client, mocker):
        meta_lb.API_KEY = "secret123"
        await meta_lb.set_serverless_url("http://serverless.example.com")

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(mocker)

        resp = await client.get("/v1/models", headers={"x-api-key": "secret123"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_accepts_bearer_token(self, client, mocker):
        meta_lb.API_KEY = "secret123"
        await meta_lb.set_serverless_url("http://serverless.example.com")

        mock_send = mocker.patch.object(
            meta_lb._http_client, "send", new_callable=mocker.AsyncMock,
        )
        mock_send.return_value = mock_response(mocker)

        resp = await client.get(
            "/v1/models", headers={"Authorization": "Bearer secret123"}
        )
        assert resp.status_code == 200
