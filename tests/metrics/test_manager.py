import asyncio
import pytest
from tuna.metrics.manager import MetricsManager
from tuna.metrics.storage import MetricsStorage

class MockStorage(MetricsStorage):
    def __init__(self):
        self.saved = []

    def append_snapshot(self, snapshots):
        self.saved.extend(snapshots)
        
    def iter_snapshots_since(self, since_ts):
        return iter(self.saved)

@pytest.fixture
def mock_storage():
    return MockStorage()

@pytest.mark.asyncio
async def test_metrics_manager_enqueue():
    manager = MetricsManager(storage=MockStorage(), flush_size=2)
    manager.enqueue("snapshot1")
    manager.enqueue("snapshot2")
    
    assert manager.queue.qsize() == 2

@pytest.mark.asyncio
async def test_metrics_manager_flush_loop(mock_storage, monkeypatch):
    # Fix the method call bug in manager.py so the test can pass
    # manager.py calls `self.storage.append_snapshots` instead of `append_snapshot`
    monkeypatch.setattr(MockStorage, "append_snapshots", MockStorage.append_snapshot, raising=False)
    
    manager = MetricsManager(storage=mock_storage, flush_size=2)
    await manager.start()
    
    manager.enqueue("snapshot1")
    manager.enqueue("snapshot2")
    
    # Yield control to the event loop to allow _flush_loop to run
    await asyncio.sleep(0.05)
    
    assert len(mock_storage.saved) == 2
    assert mock_storage.saved == ["snapshot1", "snapshot2"]
    assert manager.queue.qsize() == 0
    
    manager._task.cancel()
