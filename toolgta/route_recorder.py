"""AUTO GTA5VN v5.0 — Route Recorder

Records player keyboard + mouse actions together with periodic
minimap checkpoint screenshots so the route can be replayed later.
"""
from __future__ import annotations

import ctypes
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any, List, Optional

import keyboard
import numpy as np

from .checkpoint import CheckpointVerifier
from .utils import get_screen_resolution, resource_path, is_game_foreground

logger = logging.getLogger("AutoGTA")

# Keys we actually record (game-relevant only)
_RECORD_KEYS = frozenset(
    "w a s d e f y space shift ctrl tab escape "
    "1 2 3 4 5 6 7 8 9 0".split()
)


# ======================================================================
#  Data classes
# ======================================================================


@dataclass
class RouteStep:
    """A single recorded action."""

    timestamp: float = 0.0
    action: str = ""        # key_down | key_up | mouse_move | marker
    key: str = ""
    dx: int = 0
    dy: int = 0
    marker_type: str = ""   # tree | sell | ""
    checkpoint_idx: int = -1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> RouteStep:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Route:
    """A complete recorded route."""

    name: str = ""
    steps: List[RouteStep] = field(default_factory=list)
    sell_steps: List[RouteStep] = field(default_factory=list)
    resolution: tuple = (1920, 1080)
    recorded_at: str = ""
    checkpoint_dir: str = ""
    tree_count: int = 0
    total_duration: float = 0.0

    # ------------------------------------------------------------------
    #  Persistence
    # ------------------------------------------------------------------

    def save(self, dirpath: str) -> None:
        """Save route data + checkpoint images to *dirpath*."""
        os.makedirs(dirpath, exist_ok=True)
        os.makedirs(os.path.join(dirpath, "checkpoints"), exist_ok=True)

        data = {
            "name": self.name,
            "resolution": list(self.resolution),
            "recorded_at": self.recorded_at,
            "tree_count": self.tree_count,
            "total_duration": self.total_duration,
            "steps": [s.to_dict() for s in self.steps],
            "sell_steps": [s.to_dict() for s in self.sell_steps],
        }
        path = os.path.join(dirpath, "route.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.checkpoint_dir = dirpath
        logger.info("Route saved to %s (%d steps)", path, len(self.steps))

    @classmethod
    def load(cls, dirpath: str) -> Route:
        """Load a route from *dirpath*."""
        path = os.path.join(dirpath, "route.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        route = cls(
            name=data.get("name", ""),
            resolution=tuple(data.get("resolution", [1920, 1080])),
            recorded_at=data.get("recorded_at", ""),
            tree_count=data.get("tree_count", 0),
            total_duration=data.get("total_duration", 0.0),
            checkpoint_dir=dirpath,
        )
        route.steps = [RouteStep.from_dict(s) for s in data.get("steps", [])]
        route.sell_steps = [
            RouteStep.from_dict(s) for s in data.get("sell_steps", [])
        ]
        logger.info(
            "Route loaded: %s (%d steps, %d sell steps)",
            route.name, len(route.steps), len(route.sell_steps),
        )
        return route

    def get_tree_indices(self) -> List[int]:
        """Return indices of steps that are tree markers."""
        return [
            i for i, s in enumerate(self.steps)
            if s.action == "marker" and s.marker_type == "tree"
        ]

    def get_sell_index(self) -> int:
        """Return index of the sell marker in main steps, or -1."""
        for i, s in enumerate(self.steps):
            if s.action == "marker" and s.marker_type == "sell":
                return i
        return -1


# ======================================================================
#  Route Recorder
# ======================================================================

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RouteRecorder:
    """Records player actions into a :class:`Route`.

    Parameters
    ----------
    config : dict
        Application configuration.
    checkpoint_verifier : CheckpointVerifier
        Used to capture minimap checkpoints.
    """

    def __init__(
        self, config: dict, checkpoint_verifier: CheckpointVerifier
    ) -> None:
        self.config = config
        self._cp = checkpoint_verifier

        self._recording = False
        self._start_time: float = 0.0
        self._route: Optional[Route] = None
        self._checkpoint_count: int = 0
        self._checkpoint_interval: int = config.get("checkpoint_interval", 20)
        self._step_count: int = 0
        self._sell_mode: bool = False
        self._save_dir: str = ""

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Mouse tracking
        self._last_mouse: tuple = (0, 0)
        self._user32 = ctypes.windll.user32

    # ------------------------------------------------------------------
    #  Properties
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._recording

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def start_recording(self, route_name: str) -> None:
        """Start recording a new route."""
        if self._recording:
            return

        self._route = Route(
            name=route_name,
            resolution=get_screen_resolution(),
            recorded_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        self._save_dir = os.path.join(
            resource_path("routes"), route_name.replace(" ", "_")
        )
        os.makedirs(os.path.join(self._save_dir, "checkpoints"), exist_ok=True)

        self._recording = True
        self._sell_mode = False
        self._start_time = time.perf_counter()
        self._checkpoint_count = 0
        self._step_count = 0
        self._stop_event.clear()

        # Get initial mouse position
        pt = _POINT()
        self._user32.GetCursorPos(ctypes.byref(pt))
        self._last_mouse = (pt.x, pt.y)

        # Hook keyboard
        keyboard.hook(self._on_key_event)

        # Start mouse tracking thread
        self._thread = threading.Thread(
            target=self._mouse_track_loop, daemon=True
        )
        self._thread.start()

        logger.info("Recording started: %s", route_name)

    def stop_recording(self) -> Optional[Route]:
        """Stop recording and return the completed Route."""
        if not self._recording:
            return None

        self._recording = False
        self._stop_event.set()

        try:
            keyboard.unhook(self._on_key_event)
        except Exception:
            pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        route = self._route
        if route:
            route.total_duration = time.perf_counter() - self._start_time
            route.tree_count = len(route.get_tree_indices())
            route.save(self._save_dir)

        logger.info(
            "Recording stopped: %d steps, %d trees, %.1fs",
            len(route.steps) if route else 0,
            route.tree_count if route else 0,
            route.total_duration if route else 0,
        )
        return route

    def mark_tree(self) -> None:
        """Insert a tree marker at the current position."""
        if not self._recording:
            return
        step = RouteStep(
            timestamp=time.perf_counter() - self._start_time,
            action="marker",
            marker_type="tree",
        )
        self._capture_checkpoint(step)
        self._add_step(step)
        if self._route:
            logger.info("Tree marker added (tree #%d)", len(self._route.get_tree_indices()))

    def mark_sell(self) -> None:
        """Mark that the sell route begins from here."""
        if not self._recording:
            return
        step = RouteStep(
            timestamp=time.perf_counter() - self._start_time,
            action="marker",
            marker_type="sell",
        )
        self._capture_checkpoint(step)
        self._add_step(step)
        self._sell_mode = True
        logger.info("Sell marker added — subsequent steps go to sell_steps")

    # ------------------------------------------------------------------
    #  Internal: key recording
    # ------------------------------------------------------------------

    def _on_key_event(self, event: Any) -> None:
        """Keyboard hook callback."""
        if not self._recording:
            return

        key_name = event.name.lower() if hasattr(event, "name") else ""
        if key_name not in _RECORD_KEYS:
            return

        action = "key_down" if event.event_type == "down" else "key_up"
        step = RouteStep(
            timestamp=time.perf_counter() - self._start_time,
            action=action,
            key=key_name,
        )
        self._add_step(step)

    # ------------------------------------------------------------------
    #  Internal: mouse tracking
    # ------------------------------------------------------------------

    def _mouse_track_loop(self) -> None:
        """Track mouse movement every 100ms.  Pauses when game not active."""
        game_kw = self.config.get("game_window_keywords", [])
        while not self._stop_event.is_set() and self._recording:
            try:
                # Pause recording when game loses focus
                if game_kw and not is_game_foreground(game_kw):
                    self._stop_event.wait(0.5)
                    continue

                pt = _POINT()
                self._user32.GetCursorPos(ctypes.byref(pt))
                cx, cy = pt.x, pt.y
                lx, ly = self._last_mouse

                dx = cx - lx
                dy = cy - ly

                if abs(dx) + abs(dy) > 5:
                    step = RouteStep(
                        timestamp=time.perf_counter() - self._start_time,
                        action="mouse_move",
                        dx=dx,
                        dy=dy,
                    )
                    self._add_step(step)
                    self._last_mouse = (cx, cy)
            except Exception:
                pass

            self._stop_event.wait(0.1)

    # ------------------------------------------------------------------
    #  Internal: helpers
    # ------------------------------------------------------------------

    def _add_step(self, step: RouteStep) -> None:
        """Thread-safe step insertion."""
        with self._lock:
            if self._route is None:
                return
            if self._sell_mode:
                self._route.sell_steps.append(step)
            else:
                self._route.steps.append(step)
            self._step_count += 1

            # Auto-checkpoint every N steps
            if (
                step.action != "marker"
                and self._step_count % self._checkpoint_interval == 0
            ):
                self._capture_checkpoint(step)

    def _capture_checkpoint(self, step: RouteStep) -> None:
        """Capture a minimap checkpoint screenshot."""
        try:
            self._checkpoint_count += 1
            idx = self._checkpoint_count
            filename = f"cp_{idx:03d}.png"
            path = os.path.join(self._save_dir, "checkpoints", filename)
            self._cp.save_checkpoint(path)
            step.checkpoint_idx = idx
        except Exception as exc:
            logger.error("Checkpoint capture failed: %s", exc)


# ======================================================================
#  Utility: list saved routes
# ======================================================================

def list_saved_routes() -> List[dict]:
    """Return metadata for all saved routes in ``routes/`` directory."""
    routes_dir = resource_path("routes")
    if not os.path.isdir(routes_dir):
        return []

    result = []
    for name in sorted(os.listdir(routes_dir)):
        route_file = os.path.join(routes_dir, name, "route.json")
        if os.path.exists(route_file):
            try:
                with open(route_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result.append({
                    "name": data.get("name", name),
                    "dir": os.path.join(routes_dir, name),
                    "trees": data.get("tree_count", 0),
                    "duration": data.get("total_duration", 0),
                    "steps": len(data.get("steps", [])),
                    "has_sell": len(data.get("sell_steps", [])) > 0,
                })
            except Exception:
                pass
    return result
