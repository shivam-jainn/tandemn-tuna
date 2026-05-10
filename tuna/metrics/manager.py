import asyncio

from tuna.metrics.storage import MetricsStorage
from tuna.metrics.snapshot import MetricsSnapshot

class MetricsManager:
    """
    Metrics manager Responsible for:

    - batching and flushing
    - backpressure
    """

    def __init__(
        self,
        storage: MetricsStorage,
        flush_size: int = 100,
    ):
        self.storage = storage
        self.flush_size = flush_size

        self.queue: asyncio.Queue[
            MetricsSnapshot
        ] = asyncio.Queue()

        self._task = None
    
    async def start(self):
        self._task = asyncio.create_task(
            self._flush_loop()
        )
    
    def enqueue(
        self,
        snapshot: MetricsSnapshot,
    ):
        try:
            self.queue.put_nowait(snapshot)
        except asyncio.QueueFull:
            pass
    
    async def _flush_loop(self):
        batch = []

        while True:
            snapshot = await self.queue.get()

            batch.append(snapshot)

            if len(batch) >= self.flush_size:
                await asyncio.to_thread(
                    self.storage.append_snapshot,
                    batch,
                )

                batch.clear()

from tuna.metrics.storage_clients.jsonl import JSONLStorage

metrics_manager = MetricsManager(
    storage=JSONLStorage(),
    flush_size=100,
)