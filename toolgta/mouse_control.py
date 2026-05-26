"""AUTO GTA5VN v5.0 — Mouse Controller

Low-level mouse movement using ctypes Win32 API for reliable
input in fullscreen games.  Supports relative movement,
camera rotation, and smooth humanised rotation.
"""
from __future__ import annotations

import ctypes
import logging
import random
import time
from typing import Tuple

logger = logging.getLogger("AutoGTA")

# Win32 constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


_user32 = ctypes.windll.user32


class MouseController:
    """Mouse controller for camera rotation in GTA V / FiveM.

    Parameters
    ----------
    sensitivity : float
        Pixels-per-degree conversion factor.  Higher = faster rotation.
    """

    def __init__(self, sensitivity: float = 2.5) -> None:
        self.sensitivity: float = sensitivity

    # ------------------------------------------------------------------
    #  Low-level
    # ------------------------------------------------------------------

    @staticmethod
    def get_position() -> Tuple[int, int]:
        """Return the current cursor ``(x, y)``."""
        pt = _POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    @staticmethod
    def move_relative(dx: int, dy: int) -> None:
        """Move cursor by *(dx, dy)* pixels relative to current position."""
        _user32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)

    # ------------------------------------------------------------------
    #  Camera helpers
    # ------------------------------------------------------------------

    def rotate_camera(self, angle_degrees: float) -> None:
        """Rotate the camera by *angle_degrees*.

        Positive = right, negative = left.
        """
        dx = int(angle_degrees * self.sensitivity)
        if dx != 0:
            self.move_relative(dx, 0)

    def smooth_rotate(
        self,
        angle_degrees: float,
        duration: float = 0.3,
        steps: int = 10,
    ) -> None:
        """Rotate smoothly over *duration* seconds in *steps* increments."""
        if abs(angle_degrees) < 0.5:
            return
        per_step = angle_degrees / steps
        delay = duration / steps
        for _ in range(steps):
            jitter = random.uniform(-0.3, 0.3)
            dx = int((per_step + jitter) * self.sensitivity)
            if dx != 0:
                self.move_relative(dx, 0)
            time.sleep(delay)

    def look_up(self, pixels: int = 20) -> None:
        """Tilt camera up."""
        self.move_relative(0, -abs(pixels))

    def look_down(self, pixels: int = 20) -> None:
        """Tilt camera down."""
        self.move_relative(0, abs(pixels))

    def random_look(self, max_dx: int = 80, max_dy: int = 30) -> None:
        """Random small camera movement (anti-AFK)."""
        dx = random.randint(-max_dx, max_dx)
        dy = random.randint(-max_dy, max_dy)
        self.smooth_rotate(dx / self.sensitivity, duration=0.4, steps=5)
        if abs(dy) > 5:
            self.move_relative(0, dy)
