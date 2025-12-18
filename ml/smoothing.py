from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TableCountSmoother:
    n_tables: int
    smooth_window: int
    change_confirm_frames: int
    hold_seconds: float

    # внутреннее состояние для сглаживания
    stable_counts: List[int] = field(init=False)
    recent_counts: List[List[int]] = field(init=False)
    pending_target: List[int] = field(init=False)
    pending_streak: List[int] = field(init=False)
    last_seen_nonzero_ts: List[float] = field(init=False)
    last_nonzero_count: List[int] = field(init=False)

    def __post_init__(self) -> None:
        self.smooth_window = max(1, int(self.smooth_window))
        self.change_confirm_frames = max(1, int(self.change_confirm_frames))
        self.n_tables = int(self.n_tables)

        self.stable_counts = [0] * self.n_tables
        self.recent_counts = [[] for _ in range(self.n_tables)]
        self.pending_target = [0] * self.n_tables
        self.pending_streak = [0] * self.n_tables
        self.last_seen_nonzero_ts = [0.0] * self.n_tables
        self.last_nonzero_count = [0] * self.n_tables

    @staticmethod
    def _mode_or_median(values: List[int]) -> int:
        if not values:
            return 0
        counts = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1
        best_freq = max(counts.values())
        mode_vals = [k for k, v in counts.items() if v == best_freq]
        if len(mode_vals) == 1:
            return int(mode_vals[0])
        # при равенстве берем медиану
        values_sorted = sorted(values)
        return int(values_sorted[len(values_sorted) // 2])

    def update(self, inferred_counts: Optional[List[int]], now_ts: float) -> None:
        """обновляем сглаживание по кадрам"""

        if inferred_counts is None:
            return
        if len(inferred_counts) != self.n_tables:
            raise ValueError(
                f"inferred_counts length mismatch: expected {self.n_tables}, got {len(inferred_counts)}"
            )

        for idx in range(self.n_tables):
            recent = self.recent_counts[idx]
            recent.append(int(inferred_counts[idx]))
            if len(recent) > self.smooth_window:
                del recent[0]

            smoothed = self._mode_or_median(recent)

            if smoothed == self.stable_counts[idx]:
                self.pending_streak[idx] = 0
                self.pending_target[idx] = smoothed
            else:
                if self.pending_target[idx] != smoothed:
                    self.pending_target[idx] = smoothed
                    self.pending_streak[idx] = 1
                else:
                    self.pending_streak[idx] += 1

                if self.pending_streak[idx] >= self.change_confirm_frames:
                    self.stable_counts[idx] = smoothed
                    self.pending_streak[idx] = 0

            if self.stable_counts[idx] > 0:
                self.last_seen_nonzero_ts[idx] = float(now_ts)
                self.last_nonzero_count[idx] = int(self.stable_counts[idx])

    def current(self, now_ts: float) -> List[int]:
        """текущий статус с удержанием"""

        status = [0] * self.n_tables
        for idx in range(self.n_tables):
            count = int(self.stable_counts[idx])
            if count > 0:
                status[idx] = count
                continue

            if (
                self.hold_seconds > 0
                and (float(now_ts) - float(self.last_seen_nonzero_ts[idx])) <= self.hold_seconds
            ):
                status[idx] = int(self.last_nonzero_count[idx])
            else:
                status[idx] = 0

        return status
