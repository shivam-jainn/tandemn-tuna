from dataclasses import dataclass
from typing import Dict

@dataclass
class LatencySnapshot:
    """Latency metrics snapshot."""
    p50: float
    p95: float
    p99: float

    spot_p50_latency_ms: float
    spot_p95_latency_ms: float
    spot_p99_latency_ms: float

    serverless_p50_latency_ms: float
    serverless_p95_latency_ms: float
    serverless_p99_latency_ms: float


@dataclass
class TTFTSnapshot:
    """TTFT metrics snapshot."""
    spot_ttft_ms: float
    serverless_ttft_ms: float


@dataclass
class FailoverSnapshot:
    """Failover metrics snapshot."""
    spot_failover_count: int
    last_spot_failover_timestamp: float
    mean_failover_latency_ms: float
    failover_rolling_counts: Dict[int, int]


@dataclass
class MetricsSnapshot:
    """Top-level metrics snapshot."""
    
    timestamp: int

    total: int
    spot: int
    svl: int
    rejected: int

    pct_spot: float
    pct_serverless: float

    window_total: int
    window_spot: int
    window_serverless: int

    gpu_seconds_spot: float
    gpu_seconds_serverless: float

    uptime_seconds: float
    spot_ready_seconds: float

    latency: LatencySnapshot
    ttft: TTFTSnapshot
    failover: FailoverSnapshot