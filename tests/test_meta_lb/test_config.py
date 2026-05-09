"""Tests for tuna.router.meta_lb configuration endpoints."""

import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import client


class TestRouterConfig:
    @pytest.mark.asyncio
    async def test_push_serverless_url(self, client):
        resp = await client.post(
            "/router/config",
            json={"serverless_url": "https://modal.example.com"},
        )
        assert resp.status_code == 200
        assert await meta_lb._get_serverless_url() == "https://modal.example.com"

    @pytest.mark.asyncio
    async def test_push_spot_url(self, client):
        resp = await client.post(
            "/router/config",
            json={"spot_url": "http://spot.example.com"},
        )
        assert resp.status_code == 200
        assert await meta_lb._get_skyserve_url() == "http://spot.example.com"

    @pytest.mark.asyncio
    async def test_push_both_urls(self, client):
        resp = await client.post(
            "/router/config",
            json={
                "serverless_url": "https://modal.example.com",
                "spot_url": "http://spot.example.com",
            },
        )
        assert resp.status_code == 200
        assert await meta_lb._get_serverless_url() == "https://modal.example.com"
        assert await meta_lb._get_skyserve_url() == "http://spot.example.com"

    @pytest.mark.asyncio
    async def test_push_strips_trailing_slash(self, client):
        await client.post(
            "/router/config",
            json={"serverless_url": "https://modal.example.com/"},
        )
        assert await meta_lb._get_serverless_url() == "https://modal.example.com"
