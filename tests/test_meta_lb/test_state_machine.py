"""Tests for tuna.router.meta_lb spot state transitions."""

import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import reset_state


class TestSpotStateMachine:
    @pytest.mark.asyncio
    async def test_cold_to_warming_to_ready(self):
        reset_state()
        meta_lb._spot_state = meta_lb.SpotState.COLD
        await meta_lb._set_state(meta_lb.SpotState.WARMING)
        assert meta_lb._spot_state == meta_lb.SpotState.WARMING
        assert not await meta_lb._is_ready()

        await meta_lb._set_state(meta_lb.SpotState.READY)
        assert meta_lb._spot_state == meta_lb.SpotState.READY
        assert await meta_lb._is_ready()

    @pytest.mark.asyncio
    async def test_ready_to_cold(self):
        reset_state()
        meta_lb._spot_state = meta_lb.SpotState.COLD
        meta_lb._spot_ready_since = None
        meta_lb._spot_ready_cumulative_s = 0.0
        await meta_lb._set_state(meta_lb.SpotState.READY)
        assert meta_lb._spot_ready_since is not None

        await meta_lb._set_state(meta_lb.SpotState.COLD, "connection failed")
        assert meta_lb._spot_state == meta_lb.SpotState.COLD
        assert meta_lb._spot_ready_since is None
        assert meta_lb._spot_ready_cumulative_s > 0.0

    @pytest.mark.asyncio
    async def test_set_ready_backward_compat(self):
        reset_state()
        meta_lb._spot_state = meta_lb.SpotState.COLD
        await meta_lb._set_ready(True)
        assert meta_lb._spot_state == meta_lb.SpotState.READY
        assert await meta_lb._is_ready()

        await meta_lb._set_ready(False)
        assert meta_lb._spot_state == meta_lb.SpotState.COLD
        assert not await meta_lb._is_ready()
