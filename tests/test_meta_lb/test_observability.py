import asyncio
import time

import pytest

from tests.test_utils.meta_lb import client
from tuna.router import meta_lb

class TestObservability:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("latencies, expected_p50, expected_p95, expected_p99", [
        # 10 values: Small to Extreme ends
        ([0.01, 0.02, 0.03, 0.04, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0], 0.075, 7.75, 9.55),
        # All same small values
        ([0.001] * 10, 0.001, 0.001, 0.001),
        # Spike at the end
        ([0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 100.0], 0.01, 55.005, 91.001),
    ])
    async def test_percentile_calculation_accuracy(self, client, mocker, latencies, expected_p50, expected_p95, expected_p99):
        # Clear and manually populate deques (meta_lb stores nanoseconds)
        meta_lb._spot_latencies.clear()
        meta_lb._serverless_latencies.clear()
        
        for latency in latencies:
            meta_lb._serverless_latencies.append(int(latency * 1_000_000_000))
            
        resp = await client.get("/router/health")
        stats = resp.json()["route_stats"]
        
        assert stats["p50"] == pytest.approx(expected_p50, abs=0.01)
        assert stats["p95"] == pytest.approx(expected_p95, abs=0.01)
        assert stats["p99"] == pytest.approx(expected_p99, abs=0.01)
        
        # Verify backend-specific fields
        assert "serverless_p50_latency_ms" in stats
        assert stats["serverless_p50_latency_ms"] == pytest.approx(expected_p50 * 1000, abs=10.0)
        assert "serverless_ttft_ms" in stats

    @pytest.mark.asyncio
    async def test_pxx_on_health(self, client, mocker):
        # Clear stats
        meta_lb._spot_latencies.clear()
        meta_lb._serverless_latencies.clear()

        # Mock a response with a 50ms delay
        async def mock_send(*args, **kwargs):
            m = mocker.Mock()
            m.status_code = 200
            m.headers = {"content-type": "application/json"}
            async def aiter(*args, **kwargs):
                yield b"chunk"
            m.aiter_bytes = aiter
            m.aclose = mocker.AsyncMock()
            await asyncio.sleep(0.05)
            return m

        mocker.patch.object(meta_lb._http_client, "send", side_effect=mock_send)
        await meta_lb.set_serverless_url("http://example.com")

        # Trigger some requests
        for _ in range(5):
            await client.post("/v1/chat/completions", json={})

        resp = await client.get("/router/health")
        data = resp.json()

        assert resp.status_code == 200
        stats = data["route_stats"]

        # Check if the pxx latencies exist in the route_stats
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats
        # Latency should be roughly 0.05s
        assert 0.04 <= stats["p50"] <= 0.2
