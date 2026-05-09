"""Tests for tuna.router.meta_lb spot replica reporting."""

import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import client


class TestSpotReplicas:
    @pytest.mark.asyncio
    async def test_replicas_zero_marks_cold(self, client):
        """POST /router/spot-replicas with 0 replicas: READY → COLD."""
        await meta_lb._set_state(meta_lb.SpotState.READY)
        resp = await client.post(
            "/router/spot-replicas",
            json={"replicas": 0},
        )
        assert resp.status_code == 200
        assert meta_lb._spot_state == meta_lb.SpotState.COLD

    @pytest.mark.asyncio
    async def test_replicas_positive_marks_ready(self, client):
        """POST /router/spot-replicas with 1 replica: COLD → READY."""
        await meta_lb._set_state(meta_lb.SpotState.COLD)
        resp = await client.post(
            "/router/spot-replicas",
            json={"replicas": 1},
        )
        assert resp.status_code == 200
        assert meta_lb._spot_state == meta_lb.SpotState.READY

    @pytest.mark.asyncio
    async def test_replicas_positive_during_warming_marks_ready(self, client):
        """POST with replicas=1 during WARMING transitions to READY."""
        meta_lb._spot_state = meta_lb.SpotState.WARMING
        resp = await client.post(
            "/router/spot-replicas",
            json={"replicas": 1},
        )
        assert resp.status_code == 200
        assert meta_lb._spot_state == meta_lb.SpotState.READY

    @pytest.mark.asyncio
    async def test_replicas_zero_during_cold_no_change(self, client):
        """POST with replicas=0 during COLD doesn't change state."""
        await meta_lb._set_state(meta_lb.SpotState.COLD)
        resp = await client.post(
            "/router/spot-replicas",
            json={"replicas": 0},
        )
        assert resp.status_code == 200
        assert meta_lb._spot_state == meta_lb.SpotState.COLD

    @pytest.mark.asyncio
    async def test_replicas_requires_auth(self, client):
        """Spot-replicas endpoint requires auth."""
        meta_lb.API_KEY = "secret"
        resp = await client.post(
            "/router/spot-replicas",
            json={"replicas": 1},
        )
        assert resp.status_code == 401
