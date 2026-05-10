from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from tuna.metrics.snapshot import MetricsSnapshot
from tuna.metrics.storage import MetricsStorage


class JSONLStorage(MetricsStorage):
    """
    @param root: Optional root directory for storing metrics snapshots. Defaults to ~/.tuna/metrics.

    - Snapshots are stored in a directory structure organized by date, with each day's snapshots saved in a separate subdirectory. Each snapshot is appended to a JSONL file named after the hour it was recorded (e.g., 14.jsonl for snapshots recorded between 2 PM and 3 PM).
    - The append_snapshot method takes a MetricsSnapshot object, converts it to a dictionary, and appends it as a JSON line to the appropriate file based on the current date and hour.
    - The iter_snapshots_since method iterates through the stored snapshots, yielding those that have a timestamp greater than or equal to the provided since_ts parameter. It handles potential JSON decoding errors and missing timestamp keys gracefully, skipping any malformed entries.
    """
    def __init__(
        self,
        root: Path | None = None,
    ):
        self.root = root or (
            Path.home() / ".tuna" / "metrics"
        )

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def append_snapshot(
        self,
        snapshots: list[MetricsSnapshot],
    ) -> None:
        now = datetime.now(UTC)

        day_dir = self.root / now.strftime("%Y-%m-%d")

        day_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = (
            day_dir / f"{now.strftime('%H')}.jsonl"
        )

        for snapshot in snapshots:
            with open(
                file_path,
                "a",
                encoding="utf-8",
            ) as f:
                json.dump(asdict(snapshot), f)
                f.write("\n")

    def iter_snapshots_since(
        self,
        since_ts: int,
    ) -> Iterator[dict]:

        for day_dir in sorted(
            self.root.glob("*")
        ):
            if not day_dir.is_dir():
                continue

            for jsonl_file in sorted(
                day_dir.glob("*.jsonl")
            ):
                with open(
                    jsonl_file,
                    encoding="utf-8",
                ) as f:

                    for line in f:
                        try:
                            snapshot = json.loads(line)

                            if (
                                snapshot["timestamp"]
                                >= since_ts
                            ):
                                yield snapshot

                        except (
                            json.JSONDecodeError,
                            KeyError,
                        ):
                            continue