import pytest
import asyncio
from unittest.mock import patch, MagicMock
from collections import deque

from tuna.router.meta_lb import _route_stats
from tuna.router import meta_lb
from tuna.metrics.snapshot import MetricsSnapshot

@pytest.mark.asyncio
async def test_route_stats_integration():
    """
    Test that meta_lb._route_stats() generates data that can map correctly 
    into our Metrics components, functioning as an integration point test.
    """
    # Setup some dummy static state in meta_lb
    meta_lb._req_total = 100
    meta_lb._req_to_spot = 60
    meta_lb._req_to_serverless = 40
    meta_lb._rejected_count = 5
    
    meta_lb._spot_failover_count = 2
    meta_lb._last_spot_failover_timestamp = 1000.0
    
    meta_lb._spot_latencies.extend([100.0, 150.0, 200.0])
    meta_lb._serverless_latencies.extend([50.0, 60.0, 70.0])
    
    stats = await _route_stats()
    
    # Verify that standard metrics structure is present matching what stats output needs
    assert "total" in stats
    assert "spot" in stats
    assert "svl" in stats
    assert "failover" in stats
    assert "latency" in stats
    
    assert stats["total"] == 100
    assert stats["spot"] == 60
    assert stats["svl"] == 40
    assert stats["failover"]["spot_failover_count"] == 2
    
    assert "p50" in stats["latency"]
    assert "serverless_p99_latency_ms" in stats["latency"]
