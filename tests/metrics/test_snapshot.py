from tuna.metrics.snapshot import (
    FailoverSnapshot,
    LatencySnapshot,
    MetricsSnapshot,
    TTFTSnapshot
)

def test_latency_snapshot_creation():
    latency = LatencySnapshot(
        p50=1.0, p95=2.0, p99=3.0,
        spot_p50_latency_ms=1.1, spot_p95_latency_ms=2.1, spot_p99_latency_ms=3.1,
        serverless_p50_latency_ms=1.2, serverless_p95_latency_ms=2.2, serverless_p99_latency_ms=3.2
    )
    assert latency.p50 == 1.0

def test_metrics_snapshot_creation():
    latency = LatencySnapshot(1,2,3,1,2,3,1,2,3)
    ttft = TTFTSnapshot(100.0, 200.0)
    failover = FailoverSnapshot(1, 1234.5, 50.0, {1: 1})
    
    snapshot = MetricsSnapshot(
        timestamp=1000,
        total=10, spot=5, svl=5, rejected=0,
        pct_spot=50.0, pct_serverless=50.0,
        window_total=10, window_spot=5, window_serverless=5,
        gpu_seconds_spot=100.0, gpu_seconds_serverless=100.0,
        uptime_seconds=3600.0, spot_ready_seconds=1800.0,
        latency=latency, ttft=ttft, failover=failover
    )
    
    assert snapshot.total == 10
    assert snapshot.latency.p50 == 1
    assert snapshot.ttft.spot_ttft_ms == 100.0
    assert snapshot.failover.spot_failover_count == 1
