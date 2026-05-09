"""Tests for tuna.router.meta_lb warming task behavior."""

import asyncio
import httpx
import pytest

from tuna.router import meta_lb
from tests.test_utils.meta_lb import reset_state


class TestWarmingTask:
    @pytest.mark.asyncio
    async def test_warming_starts_on_cold(self, mocker):
        """Background poke loop starts when state is COLD and keeps poking."""
        reset_state()
        meta_lb._spot_state = meta_lb.SpotState.COLD
        meta_lb._warming_task = None
        meta_lb._skyserve_base_url = "http://spot.example.com"

        meta_lb._http_client = httpx.AsyncClient()
        mock_get = mocker.patch.object(
            meta_lb._http_client, "get", new_callable=mocker.AsyncMock,
        )
        mock_resp = mocker.AsyncMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        mocker.patch("asyncio.sleep", new_callable=mocker.AsyncMock)

        orig_timeout = meta_lb.WARMUP_TIMEOUT_SECONDS
        orig_interval = meta_lb.WARMUP_POKE_INTERVAL_SECONDS
        meta_lb.WARMUP_TIMEOUT_SECONDS = 2.0
        meta_lb.WARMUP_POKE_INTERVAL_SECONDS = 1.0
        try:
            await meta_lb._enter_warming()
            assert meta_lb._warming_task is not None
            await asyncio.wait_for(meta_lb._warming_task, timeout=5)
            assert meta_lb._spot_state == meta_lb.SpotState.READY
        finally:
            meta_lb.WARMUP_TIMEOUT_SECONDS = orig_timeout
            meta_lb.WARMUP_POKE_INTERVAL_SECONDS = orig_interval
            await meta_lb._http_client.aclose()

    @pytest.mark.asyncio
    async def test_warming_does_not_start_when_already_warming(self):
        """If already warming, _enter_warming is a no-op."""
        reset_state()
        meta_lb._spot_state = meta_lb.SpotState.WARMING
        meta_lb._skyserve_base_url = "http://spot.example.com"

        old_task = meta_lb._warming_task
        await meta_lb._enter_warming()
        assert meta_lb._warming_task is old_task

    @pytest.mark.asyncio
    async def test_warming_does_not_start_when_ready(self):
        """If already ready, _enter_warming is a no-op."""
        reset_state()
        meta_lb._spot_state = meta_lb.SpotState.READY
        meta_lb._skyserve_base_url = "http://spot.example.com"

        old_task = meta_lb._warming_task
        await meta_lb._enter_warming()
        assert meta_lb._warming_task is old_task

    @pytest.mark.asyncio
    async def test_warming_timeout_returns_to_cold(self, mocker):
        """After timeout, warming transitions back to COLD."""
        reset_state()
        meta_lb._spot_state = meta_lb.SpotState.COLD
        meta_lb._warming_task = None
        meta_lb._skyserve_base_url = "http://spot.example.com"

        meta_lb._http_client = httpx.AsyncClient()
        mock_get = mocker.patch.object(
            meta_lb._http_client, "get", new_callable=mocker.AsyncMock,
        )
        mock_get.side_effect = httpx.ConnectError("refused")
        mocker.patch("asyncio.sleep", new_callable=mocker.AsyncMock)

        orig_timeout = meta_lb.WARMUP_TIMEOUT_SECONDS
        orig_interval = meta_lb.WARMUP_POKE_INTERVAL_SECONDS
        meta_lb.WARMUP_TIMEOUT_SECONDS = 3.0
        meta_lb.WARMUP_POKE_INTERVAL_SECONDS = 1.0

        try:
            await meta_lb._enter_warming()
            await asyncio.wait_for(meta_lb._warming_task, timeout=10)
            assert meta_lb._spot_state == meta_lb.SpotState.COLD
            assert mock_get.call_count == 6
        finally:
            meta_lb.WARMUP_TIMEOUT_SECONDS = orig_timeout
            meta_lb.WARMUP_POKE_INTERVAL_SECONDS = orig_interval
            await meta_lb._http_client.aclose()

    @pytest.mark.asyncio
    async def test_warming_exits_when_state_changes_externally(self, mocker):
        """Warming task stops if state changes externally (e.g., spot-replicas)."""
        reset_state()
        meta_lb._spot_state = meta_lb.SpotState.COLD
        meta_lb._warming_task = None
        meta_lb._skyserve_base_url = "http://spot.example.com"

        call_count = 0

        meta_lb._http_client = httpx.AsyncClient()

        async def _fake_get(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                meta_lb._spot_state = meta_lb.SpotState.READY
            raise httpx.ConnectError("refused")

        mocker.patch.object(meta_lb._http_client, "get", side_effect=_fake_get)
        mocker.patch("asyncio.sleep", new_callable=mocker.AsyncMock)

        orig_timeout = meta_lb.WARMUP_TIMEOUT_SECONDS
        orig_interval = meta_lb.WARMUP_POKE_INTERVAL_SECONDS
        meta_lb.WARMUP_TIMEOUT_SECONDS = 10.0
        meta_lb.WARMUP_POKE_INTERVAL_SECONDS = 1.0
        try:
            await meta_lb._enter_warming()
            await asyncio.wait_for(meta_lb._warming_task, timeout=5)
            assert call_count == 2
        finally:
            meta_lb.WARMUP_TIMEOUT_SECONDS = orig_timeout
            meta_lb.WARMUP_POKE_INTERVAL_SECONDS = orig_interval
            await meta_lb._http_client.aclose()
