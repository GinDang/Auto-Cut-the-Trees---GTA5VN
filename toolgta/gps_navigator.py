"""AUTO GTA5VN v5.0 — GPS Arrow Navigator

Detects the GPS navigation line on the GTA5VN minimap (purple/magenta)
and provides steering guidance to follow it.
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import keyboard
import numpy as np
from mss import MSS

from .mouse_control import MouseController
from .utils import calc_region, get_screen_resolution

logger = logging.getLogger("AutoGTA")


@dataclass
class GPSReading:
    """Result of a single GPS detection scan."""

    found: bool = False
    angle: float = 0.0          # degrees: 0=up, +90=right, -90=left
    distance_px: int = 0        # GPS pixel count (rough distance)
    confidence: float = 0.0     # detection confidence 0–1


class GPSNavigator:
    """Reads the GPS navigation line from the minimap and steers toward it.

    Parameters
    ----------
    config : dict
        Application configuration.
    mouse_ctrl : MouseController
        For camera rotation.
    """

    def __init__(self, config: dict, mouse_ctrl: MouseController) -> None:
        self.config = config
        self._mouse = mouse_ctrl
        self._sct: Optional[MSS] = None

        # GPS colour range in HSV (purple / magenta)
        self._gps_lower = np.array(
            config.get("gps_color_lower", [140, 80, 100]), dtype=np.uint8
        )
        self._gps_upper = np.array(
            config.get("gps_color_upper", [170, 255, 255]), dtype=np.uint8
        )

        # Also detect pink range (some servers use different hues)
        self._gps_lower2 = np.array([155, 60, 120], dtype=np.uint8)
        self._gps_upper2 = np.array([180, 255, 255], dtype=np.uint8)

        self._minimap_pct: dict = config.get("minimap_region", {
            "top_pct": 0.78,
            "left_pct": 0.01,
            "width_pct": 0.14,
            "height_pct": 0.22,
        })

        self._steer_gain: float = config.get("mouse_sensitivity", 2.5)
        self._arrival_min_px: int = config.get("arrival_threshold", 10)
        self._dead_zone: float = 15.0   # degrees — go straight if within

        # State
        self._last_reading = GPSReading()
        self._arrived = False

    # ------------------------------------------------------------------
    #  Internals
    # ------------------------------------------------------------------

    def _get_sct(self) -> MSS:
        if self._sct is None:
            self._sct = MSS()
        return self._sct

    def capture_minimap(self) -> np.ndarray:
        """Capture minimap region as BGR numpy array."""
        sw, sh = get_screen_resolution()
        region = calc_region(self._minimap_pct, sw, sh)
        img = np.array(self._get_sct().grab(region))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    # ------------------------------------------------------------------
    #  GPS detection
    # ------------------------------------------------------------------

    def detect_gps(self, minimap_bgr: Optional[np.ndarray] = None) -> GPSReading:
        """Detect the GPS line and compute the heading angle.

        Parameters
        ----------
        minimap_bgr : np.ndarray | None
            BGR minimap image.  Captured fresh if ``None``.

        Returns
        -------
        GPSReading
            Detection result with angle and confidence.
        """
        if minimap_bgr is None:
            minimap_bgr = self.capture_minimap()

        h, w = minimap_bgr.shape[:2]
        cx, cy = w // 2, h // 2  # Player at centre

        # --- HSV filter for GPS colour ---
        hsv = cv2.cvtColor(minimap_bgr, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self._gps_lower, self._gps_upper)
        mask2 = cv2.inRange(hsv, self._gps_lower2, self._gps_upper2)
        mask = cv2.bitwise_or(mask1, mask2)

        # Morphology cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.dilate(mask, kernel, iterations=1)
        mask = cv2.erode(mask, kernel, iterations=1)

        # Count GPS pixels
        gps_pixels = cv2.countNonZero(mask)

        if gps_pixels < self._arrival_min_px:
            self._arrived = True
            self._last_reading = GPSReading(
                found=False, distance_px=gps_pixels
            )
            return self._last_reading

        self._arrived = False

        # --- Find GPS direction from centre ---
        # Get all GPS pixel coordinates
        ys, xs = np.nonzero(mask)

        if len(xs) == 0:
            self._last_reading = GPSReading(found=False)
            return self._last_reading

        # Focus on pixels near the player (inner 60% of minimap)
        radius = int(min(w, h) * 0.3)
        distances = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        near_mask = distances < radius

        if np.sum(near_mask) > 3:
            near_xs = xs[near_mask]
            near_ys = ys[near_mask]
        else:
            near_xs = xs
            near_ys = ys

        # Compute centroid of nearby GPS pixels
        gps_cx = int(np.mean(near_xs))
        gps_cy = int(np.mean(near_ys))

        # Angle from player centre to GPS centroid
        # In image coords: +x = right, +y = down
        # We want: 0° = up (north), +90° = right (east)
        dx = gps_cx - cx
        dy = -(gps_cy - cy)   # Flip Y (image Y is inverted)

        angle_rad = math.atan2(dx, dy)  # atan2(x, y) for "up = 0°"
        angle_deg = math.degrees(angle_rad)

        confidence = min(1.0, gps_pixels / 200.0)

        self._last_reading = GPSReading(
            found=True,
            angle=angle_deg,
            distance_px=gps_pixels,
            confidence=confidence,
        )
        return self._last_reading

    # ------------------------------------------------------------------
    #  Properties
    # ------------------------------------------------------------------

    @property
    def is_arrived(self) -> bool:
        """``True`` if GPS line has disappeared (arrived at waypoint)."""
        return self._arrived

    @property
    def last_reading(self) -> GPSReading:
        return self._last_reading

    # ------------------------------------------------------------------
    #  Navigation
    # ------------------------------------------------------------------

    def navigate_step(self) -> GPSReading:
        """Execute a single navigation step: detect → steer → move.

        Returns the GPS reading.
        """
        reading = self.detect_gps()

        if not reading.found:
            return reading

        angle = reading.angle

        # Proportional steering
        if abs(angle) > self._dead_zone:
            # Scale rotation: bigger angle → faster turn
            rotation = angle * 0.3   # damping factor
            rotation = max(-45, min(45, rotation))  # clamp
            self._mouse.rotate_camera(rotation)

        # Move forward
        try:
            keyboard.press("w")
        except Exception:
            pass

        return reading

    def navigate_loop(
        self,
        timeout: float = 60.0,
        stop_event: Optional[object] = None,
    ) -> bool:
        """Keep navigating until arrived or *timeout*.

        Parameters
        ----------
        timeout : float
            Maximum seconds to navigate.
        stop_event : threading.Event | None
            Checked each iteration; if set, stops early.

        Returns
        -------
        bool
            ``True`` if arrived, ``False`` if timeout / stopped.
        """
        start = time.perf_counter()
        logger.info("GPS navigation started (timeout=%.0fs)", timeout)

        try:
            while time.perf_counter() - start < timeout:
                if stop_event and stop_event.is_set():
                    return False

                reading = self.navigate_step()

                if self._arrived:
                    logger.info("GPS navigation: arrived!")
                    return True

                time.sleep(0.2)
        except Exception as exc:
            logger.error("GPS navigation error: %s", exc)
        finally:
            try:
                keyboard.release("w")
            except Exception:
                pass

        logger.warning("GPS navigation: timeout (%.0fs)", timeout)
        return False

    # ------------------------------------------------------------------
    #  Utility
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset arrived state."""
        self._arrived = False
        self._last_reading = GPSReading()

    def cleanup(self) -> None:
        """Release resources."""
        if self._sct:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None
