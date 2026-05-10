from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from tuna.metrics.snapshot import MetricsSnapshot


class MetricsStorage(ABC):
    @abstractmethod
    def append_snapshot(
        self,
        snapshots: list[MetricsSnapshot],
    ) -> None:
        """
        @params snapshot: The MetricsSnapshot object to be stored.

        Appends a metrics snapshot to the storage.
        """
        pass

    @abstractmethod
    def iter_snapshots_since(
        self,
        since_ts: int,
    ) -> Iterator[dict]:
        pass
    

