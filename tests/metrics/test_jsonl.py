import json
import pytest
from pathlib import Path
from tuna.metrics.storage_clients.jsonl import JSONLStorage
from tuna.metrics.snapshot import (
    MetricsSnapshot, LatencySnapshot, TTFTSnapshot, FailoverSnapshot
)

def test_jsonl_storage_initialization(tmp_path):
    storage = JSONLStorage(root=tmp_path)
    assert storage.root.exists()

def test_jsonl_storage_append_snapshot(tmp_path):
    storage = JSONLStorage(root=tmp_path)
    
    latency = LatencySnapshot(1,2,3,1,2,3,1,2,3)
    ttft = TTFTSnapshot(1,2)
    failover = FailoverSnapshot(1, 1.0, 1.0, {})
    snapshot = MetricsSnapshot(
        timestamp=1000,
        total=10, spot=5, svl=5, rejected=0,
        pct_spot=50.0, pct_serverless=50.0,
        window_total=10, window_spot=5, window_serverless=5,
        gpu_seconds_spot=10.0, gpu_seconds_serverless=10.0,
        uptime_seconds=10.0, spot_ready_seconds=5.0,
        latency=latency, ttft=ttft, failover=failover
    )
    
    # Append to storage
    storage.append_snapshot([snapshot])
    
    # Verify file was created
    day_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
    assert len(day_dirs) == 1
    day_dir = day_dirs[0]
    
    jsonl_files = list(day_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1
    
    # Verify content
    with open(jsonl_files[0], "r") as f:
        line = f.readline()
        data = json.loads(line)
        assert data["total"] == 10
        assert data["latency"]["p50"] == 1

def test_jsonl_storage_iter_snapshots_since(tmp_path, monkeypatch):
    storage = JSONLStorage(root=tmp_path)
    
    # Adding mock data with timestamps directly to the file to bypass MetricsSnapshot lacking timestamp (per file snapshot.py)
    day_dir = tmp_path / "2026-05-10"
    day_dir.mkdir(parents=True, exist_ok=True)
    file_path = day_dir / "14.jsonl"
    
    with open(file_path, "w") as f:
        f.write(json.dumps({"total": 10, "timestamp": 1000}) + "\n")
        f.write(json.dumps({"total": 20, "timestamp": 2000}) + "\n")
        f.write(json.dumps({"total": 30, "timestamp": 500}) + "\n")
        f.write("{invalid_json\n")
    
    results = list(storage.iter_snapshots_since(since_ts=1000))
    
    assert len(results) == 2
    assert results[0]["total"] == 10
    assert results[1]["total"] == 20
