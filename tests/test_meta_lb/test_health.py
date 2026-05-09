"""Tests for tuna.router.meta_lb health endpoints."""

import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import client, reset_state


class TestRouterHealth:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        resp = await client.get("/router/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "skyserve_ready" in data

    @pytest.mark.asyncio
    async def test_health_shows_urls(self, client):
        await meta_lb.set_serverless_url("https://modal.example.com")
        await meta_lb.set_spot_url("http://spot.example.com")
        resp = await client.get("/router/health")
        data = resp.json()
        assert data["serverless_base_url"] == "https://modal.example.com"
        assert data["skyserve_base_url"] == "http://spot.example.com"

    @pytest.mark.asyncio
    async def test_health_shows_spot_state(self, client):
        resp = await client.get("/router/health")
        data = resp.json()
        assert data["spot_state"] == "cold"
        assert data["skyserve_ready"] is False

    @pytest.mark.asyncio
    async def test_health_shows_ready_when_spot_ready(self, client):
        await meta_lb._set_state(meta_lb.SpotState.READY)
        resp = await client.get("/router/health")
        data = resp.json()
        assert data["spot_state"] == "ready"
        assert data["skyserve_ready"] is True


class TestHealthNoProbe:
    @pytest.mark.asyncio
    async def test_health_never_hits_skyserve_lb(self, client, mocker):
        """Verify /router/health never sends HTTP to SkyServe LB."""
        await meta_lb.set_spot_url("http://spot.example.com")
        mock_get = mocker.patch.object(meta_lb._http_client, "get", new_callable=mocker.AsyncMock)

        resp = await client.get("/router/health")
        assert resp.status_code == 200
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_health_never_hits_skyserve_lb_when_ready(self, client, mocker):
        await meta_lb.set_spot_url("http://spot.example.com")
        await meta_lb._set_state(meta_lb.SpotState.READY)
        mock_get = mocker.patch.object(meta_lb._http_client, "get", new_callable=mocker.AsyncMock)

        resp = await client.get("/router/health")
        assert resp.status_code == 200
        mock_get.assert_not_called()
