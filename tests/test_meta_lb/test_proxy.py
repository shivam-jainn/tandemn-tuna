"""Tests for tuna.router.meta_lb proxy behavior."""

import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import client


class TestProxy503:
    @pytest.mark.asyncio
    async def test_no_backends_returns_503(self, client):
        resp = await client.get("/v1/chat/completions")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_only_spot_not_ready_returns_503(self, client):
        await meta_lb.set_spot_url("http://spot.example.com")
        await meta_lb._set_state(meta_lb.SpotState.COLD)
        resp = await client.get("/v1/chat/completions")
        assert resp.status_code == 503
