import asyncio
import time
import httpx
import pytest
from tests.test_utils.meta_lb import client, reset_state
from tuna.router import meta_lb

class TestFailoverMetrics:
    @pytest.mark.asyncio
    async def test_failover_metrics_on_spot_failure(self, client, mocker):
        # Clear stats
        reset_state()

        # Config both urls
        await meta_lb.set_serverless_url("http://serverless-target")
        await meta_lb.set_spot_url("http://spot-target")

        # Mark spot as READY so we route to it first
        await meta_lb._set_state(meta_lb.SpotState.READY)

        # Mock responses
        # First call: Spot failure (503)
        # Second call: Serverless success (200)
        spot_resp = mocker.AsyncMock(spec=httpx.Response)
        spot_resp.status_code = 503
        spot_resp.headers = httpx.Headers({"content-type": "application/json"})
        async def aiter_spot(*args, **kwargs):
            yield b"spot-failure"
        spot_resp.aiter_bytes = aiter_spot
        spot_resp.aclose = mocker.AsyncMock()

        serverless_resp = mocker.AsyncMock(spec=httpx.Response)
        serverless_resp.status_code = 200
        serverless_resp.headers = httpx.Headers({"content-type": "application/json"})
        async def aiter_svl(*args, **kwargs):
            yield b"serverless-success"
        serverless_resp.aiter_bytes = aiter_svl
        serverless_resp.aclose = mocker.AsyncMock()

        mocker.patch.object(meta_lb._http_client, "send", side_effect=[spot_resp, serverless_resp])

        # Trigger a request that will failover to serverless
        resp = await client.post("/v1/chat/completions", json={"prompt": "hi"})
        assert resp.status_code == 200  # Should succeed via serverless

        # Verify the success body
        body = b""
        async for chunk in resp.aiter_bytes():
            body += chunk
        assert body == b"serverless-success"

        # Check that failover metrics were recorded
        stats_resp = await client.get("/router/health")
        stats = stats_resp.json()["route_stats"]

        assert stats["spot_failover_count"] == 1
        assert stats["last_spot_failover_timestamp"] is not None
        assert stats["spot"] == 1 # Original route attempt
        assert stats["serverless"] == 1 # Failover attempt

    @pytest.mark.asyncio
    async def test_rolling_failover_windows(self, client):
        """Table-driven test for sliding window failover metrics."""
        reset_state()
        
        # We manually inject timestamps into the internal deque to simulate time passing
        # CRITICAL: We append them in ascending order for bisect to work
        now = time.time()
        
        # Test cases: (offset_seconds_from_now, description)
        # We'll simulate failovers at different points in the past
        test_failovers = [
            (50000, "50000s ago - should be pruned"),
            (10000, "10000s ago - should be in 36000s"),
            (1000, "1000s ago - should be in 36000s, 3600s"),
            (100, "100s ago - should be in 360s, 3600s, 36000s"),
            (10, "10s ago - should be in all buckets"),
        ]
        
        for offset, _ in test_failovers:
            meta_lb._spot_failover_timestamps.append(now - offset)
            meta_lb._spot_failover_count += 1
            
        # Trigger health check to calculate rolling windows
        resp = await client.get("/router/health")
        stats = resp.json()["route_stats"]
        
        # Expectations table: (window_key, expected_count)
        expectations = [
            ("spot_failover_count_60s", 1),    # Only the 10s one
            ("spot_failover_count_360s", 2),   # 10s, 100s
            ("spot_failover_count_3600s", 3),  # 10s, 100s, 1000s
            ("spot_failover_count_36000s", 4), # 10s, 100s, 1000s, 10000s
        ]
        
        for key, expected in expectations:
            assert stats[key] == expected, f"Window {key} failed: expected {expected}, got {stats[key]}"
        
        # Verify pruning worked (the 50000s one should be gone from the internal deque)
        # Pruning happens inside _route_stats() called by /router/health
        assert len(meta_lb._spot_failover_timestamps) == 4

    @pytest.mark.asyncio
    async def test_mean_failover_latency(self, client):
        """Test mean failover latency calculation and 24h window."""
        reset_state()
        
        # Manually inject some failover latencies (timestamp, latency_ns)
        # CRITICAL: We append them in ascending epoch order for the prune while loop to work correctly
        now = time.time()
        
        # 100s latency, 25h ago (should be pruned)
        meta_lb._failover_latencies.append((now - 90000, 100 * 1_000_000_000))
        # 20s latency, 2h ago
        meta_lb._failover_latencies.append((now - 7200, 20 * 1_000_000_000))
        # 10s latency, 1h ago
        meta_lb._failover_latencies.append((now - 3600, 10 * 1_000_000_000))
        
        resp = await client.get("/router/health")
        stats = resp.json()["route_stats"]
        
        # Mean should be (10 + 20) / 2 = 15s (15000ms)
        expected_mean_ms = 15000.0
        assert stats["mean_failover_latency_ms"] == expected_mean_ms
        
        # Verify pruning worked
        assert len(meta_lb._failover_latencies) == 2
