"""
AUTO GTA5VN - Session Statistics
Version 5.0

Tracks per-session metrics such as key presses, FPS, detection
confidence, detection latency, inventory events, and game pauses.
Provides summary generation and elapsed time formatting.
"""
from __future__ import annotations

import time
from typing import Any


class SessionStats:
    """Accumulator for a single automation session's statistics.

    Create an instance at the start of a session, call the various
    ``record_*`` methods during execution, and retrieve a final
    summary via :meth:`get_summary`.

    Attributes:
        _start_time: ``perf_counter`` timestamp when the session started.
        _end_time: ``perf_counter`` timestamp when the session stopped.
        _press_counts: Per-key press counters for ``e``, ``f``, ``y``.
        _fps_samples: List of instantaneous FPS measurements.
        _confidence_samples: List of match confidence scores.
        _inventory_full_count: Number of times inventory-full was triggered.
        _game_pause_count: Number of times the engine paused (game not foreground).
        _detection_times_ms: List of detection durations in milliseconds.
    """

    def __init__(self) -> None:
        """Initialise all counters and sample lists to their defaults."""
        self._start_time: float | None = None
        self._end_time: float | None = None
        self._press_counts: dict[str, int] = {"e": 0, "f": 0, "y": 0}
        self._fps_samples: list[float] = []
        self._confidence_samples: list[float] = []
        self._inventory_full_count: int = 0
        self._game_pause_count: int = 0
        self._detection_times_ms: list[float] = []

    # ----------------------------------------------------------
    #  Lifecycle
    # ----------------------------------------------------------

    def start(self) -> None:
        """Mark the session as started (records the current timestamp)."""
        self._start_time = time.perf_counter()

    def stop(self) -> None:
        """Mark the session as stopped (records the current timestamp)."""
        self._end_time = time.perf_counter()

    # ----------------------------------------------------------
    #  Recording helpers
    # ----------------------------------------------------------

    def record_press(self, key: str) -> None:
        """Increment the press counter for *key*.

        Args:
            key: One of ``"e"``, ``"f"``, or ``"y"``.
        """
        if key in self._press_counts:
            self._press_counts[key] += 1

    def record_fps(self, fps: float) -> None:
        """Append an instantaneous FPS measurement.

        Args:
            fps: Frames per second value.
        """
        self._fps_samples.append(fps)

    def record_confidence(self, conf: float) -> None:
        """Append a template-match confidence score.

        Args:
            conf: Confidence value (typically ``0.0`` – ``1.0``).
        """
        self._confidence_samples.append(conf)

    def record_detection_time(self, ms: float) -> None:
        """Append a detection duration measurement.

        Args:
            ms: Detection time in milliseconds.
        """
        self._detection_times_ms.append(ms)

    def record_inventory_full(self) -> None:
        """Increment the inventory-full event counter."""
        self._inventory_full_count += 1

    def record_game_pause(self) -> None:
        """Increment the game-not-foreground pause counter."""
        self._game_pause_count += 1

    # ----------------------------------------------------------
    #  Computed metrics
    # ----------------------------------------------------------

    def elapsed_seconds(self) -> float:
        """Return the total elapsed session time in seconds.

        If the session has not been stopped yet, measures from start
        to *now*.  Returns ``0.0`` if the session was never started.

        Returns:
            Elapsed time in seconds.
        """
        if self._start_time is None:
            return 0.0
        end = self._end_time if self._end_time is not None else time.perf_counter()
        return max(0.0, end - self._start_time)

    def elapsed_str(self) -> str:
        """Return elapsed time formatted as ``\"Xh Ym Zs\"``.

        Returns:
            Human-readable elapsed time string.
        """
        total = int(self.elapsed_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m}m {s}s"

    def avg_fps(self) -> float:
        """Return the average FPS across all samples.

        Returns:
            Average FPS, or ``0.0`` if no samples have been recorded.
        """
        if not self._fps_samples:
            return 0.0
        return sum(self._fps_samples) / len(self._fps_samples)

    def avg_confidence(self) -> float:
        """Return the average template-match confidence.

        Returns:
            Average confidence, or ``0.0`` if no samples recorded.
        """
        if not self._confidence_samples:
            return 0.0
        return sum(self._confidence_samples) / len(self._confidence_samples)

    def avg_detection_ms(self) -> float:
        """Return the average detection time in milliseconds.

        Returns:
            Average detection latency, or ``0.0`` if no samples.
        """
        if not self._detection_times_ms:
            return 0.0
        return sum(self._detection_times_ms) / len(self._detection_times_ms)

    def total_presses(self) -> int:
        """Return the total number of key presses across all keys.

        Returns:
            Sum of all press counts.
        """
        return sum(self._press_counts.values())

    def wood_estimate(self) -> int:
        """Estimate the number of wood collected.

        One wood unit is assumed to require a full ``e → f → y`` cycle
        (3 presses).

        Returns:
            Estimated wood count.
        """
        return self.total_presses() // 3

    # ----------------------------------------------------------
    #  Summary
    # ----------------------------------------------------------

    def get_summary(self) -> dict[str, Any]:
        """Generate a comprehensive session summary dictionary.

        Returns:
            Dictionary containing all session metrics.
        """
        return {
            "elapsed": self.elapsed_str(),
            "elapsed_seconds": round(self.elapsed_seconds(), 2),
            "total_presses": self.total_presses(),
            "press_counts": dict(self._press_counts),
            "wood_estimate": self.wood_estimate(),
            "avg_fps": round(self.avg_fps(), 2),
            "avg_confidence": round(self.avg_confidence(), 4),
            "avg_detection_ms": round(self.avg_detection_ms(), 2),
            "inventory_full_count": self._inventory_full_count,
            "game_pause_count": self._game_pause_count,
        }

    # ----------------------------------------------------------
    #  Reset
    # ----------------------------------------------------------

    def reset(self) -> None:
        """Reset all counters and sample lists to their initial state."""
        self._start_time = None
        self._end_time = None
        self._press_counts = {"e": 0, "f": 0, "y": 0}
        self._fps_samples.clear()
        self._confidence_samples.clear()
        self._detection_times_ms.clear()
        self._inventory_full_count = 0
        self._game_pause_count = 0

    # ----------------------------------------------------------
    #  Repr
    # ----------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<SessionStats elapsed={self.elapsed_str()!r} "
            f"presses={self.total_presses()} "
            f"wood≈{self.wood_estimate()}>"
        )
