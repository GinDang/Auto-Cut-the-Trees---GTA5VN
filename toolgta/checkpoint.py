"""AUTO GTA5VN v5.0 — Checkpoint Verifier

Screenshot comparison system for route self-correction.
Compares minimap captures to verify the player is at the
expected position along a recorded route.
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

import cv2
import numpy as np
from mss import MSS

from .utils import calc_region, get_screen_resolution

logger = logging.getLogger("AutoGTA")


class CheckpointVerifier:
    """Compare minimap screenshots for position verification.

    Parameters
    ----------
    minimap_region : dict
        Percentage-based region ``{top_pct, left_pct, width_pct, height_pct}``.
    threshold : float
        Minimum similarity score to consider "at checkpoint".
    """

    _DEFAULT_REGION: dict = {
        "top_pct": 0.78,
        "left_pct": 0.01,
        "width_pct": 0.14,
        "height_pct": 0.22,
    }

    def __init__(
        self,
        minimap_region: Optional[dict] = None,
        threshold: float = 0.65,
    ) -> None:
        self.minimap_region = minimap_region or self._DEFAULT_REGION
        self.threshold = threshold
        self._sct: Optional[MSS] = None

    def _get_sct(self) -> MSS:
        if self._sct is None:
            self._sct = MSS()
        return self._sct

    # ------------------------------------------------------------------
    #  Capture
    # ------------------------------------------------------------------

    def capture_minimap(self) -> np.ndarray:
        """Capture the minimap region as a grayscale numpy array."""
        sw, sh = get_screen_resolution()
        region = calc_region(self.minimap_region, sw, sh)
        img = np.array(self._get_sct().grab(region))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

    def capture_minimap_color(self) -> np.ndarray:
        """Capture the minimap region as a BGR numpy array."""
        sw, sh = get_screen_resolution()
        region = calc_region(self.minimap_region, sw, sh)
        img = np.array(self._get_sct().grab(region))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def save_checkpoint(self, save_path: str) -> str:
        """Capture minimap and save to *save_path*.  Returns the path."""
        gray = self.capture_minimap()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        cv2.imwrite(save_path, gray)
        return save_path

    # ------------------------------------------------------------------
    #  Comparison
    # ------------------------------------------------------------------

    def compare(
        self, current: np.ndarray, expected: np.ndarray
    ) -> float:
        """Compare two minimap images and return similarity ``[0.0, 1.0]``.

        Uses a blend of template-matching and histogram comparison
        for robustness.
        """
        if current is None or expected is None:
            return 0.0
        if current.size == 0 or expected.size == 0:
            return 0.0

        # Resize to same dimensions
        h, w = expected.shape[:2]
        current_r = cv2.resize(current, (w, h), interpolation=cv2.INTER_AREA)

        # Ensure grayscale
        if len(current_r.shape) == 3:
            current_r = cv2.cvtColor(current_r, cv2.COLOR_BGR2GRAY)
        if len(expected.shape) == 3:
            expected = cv2.cvtColor(expected, cv2.COLOR_BGR2GRAY)

        # --- Method 1: Template matching ---
        try:
            res = cv2.matchTemplate(
                current_r, expected, cv2.TM_CCOEFF_NORMED
            )
            _, tm_score, _, _ = cv2.minMaxLoc(res)
            tm_score = max(0.0, tm_score)
        except Exception:
            tm_score = 0.0

        # --- Method 2: Histogram comparison ---
        try:
            hist_c = cv2.calcHist([current_r], [0], None, [64], [0, 256])
            hist_e = cv2.calcHist([expected], [0], None, [64], [0, 256])
            cv2.normalize(hist_c, hist_c)
            cv2.normalize(hist_e, hist_e)
            hist_score = cv2.compareHist(
                hist_c, hist_e, cv2.HISTCMP_CORREL
            )
            hist_score = max(0.0, (hist_score + 1.0) / 2.0)
        except Exception:
            hist_score = 0.0

        # Blend: 60% template, 40% histogram
        return tm_score * 0.6 + hist_score * 0.4

    def compare_with_file(self, checkpoint_path: str) -> float:
        """Capture current minimap, load checkpoint, and compare."""
        if not os.path.exists(checkpoint_path):
            logger.warning("Checkpoint file not found: %s", checkpoint_path)
            return 0.0
        current = self.capture_minimap()
        expected = cv2.imread(checkpoint_path, cv2.IMREAD_GRAYSCALE)
        if expected is None:
            return 0.0
        return self.compare(current, expected)

    def is_at_checkpoint(self, checkpoint_path: str) -> bool:
        """Return ``True`` if current minimap matches the checkpoint."""
        return self.compare_with_file(checkpoint_path) >= self.threshold

    # ------------------------------------------------------------------
    #  Drift estimation
    # ------------------------------------------------------------------

    def estimate_drift(
        self, current: np.ndarray, expected: np.ndarray
    ) -> Tuple[int, int]:
        """Estimate pixel drift ``(dx, dy)`` between images.

        Positive *dx* = player is to the right of expected.
        Positive *dy* = player is below expected.
        """
        if current is None or expected is None:
            return 0, 0

        h, w = expected.shape[:2]
        current_r = cv2.resize(current, (w, h), interpolation=cv2.INTER_AREA)

        if len(current_r.shape) == 3:
            current_r = cv2.cvtColor(current_r, cv2.COLOR_BGR2GRAY)
        if len(expected.shape) == 3:
            expected = cv2.cvtColor(expected, cv2.COLOR_BGR2GRAY)

        try:
            res = cv2.matchTemplate(
                current_r, expected, cv2.TM_CCOEFF_NORMED
            )
            _, _, _, max_loc = cv2.minMaxLoc(res)
            cx, cy = w // 2, h // 2
            dx = max_loc[0] - cx
            dy = max_loc[1] - cy
            return dx, dy
        except Exception:
            return 0, 0

    # ------------------------------------------------------------------
    #  Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Release the MSS instance."""
        if self._sct:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None
