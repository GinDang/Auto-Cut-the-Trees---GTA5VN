"""AUTO GTA5VN v5.0 — Template Manager

Handles loading, preprocessing, matching, and deduplication of
screen-region templates used for automated key-press detection.
"""
from __future__ import annotations

import glob
import logging
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from .utils import resource_path
from .constants import DEFAULT_CONFIG

logger = logging.getLogger("AutoGTA")


class TemplateManager:
    """Load, preprocess, and match screen templates for key detection.

    Parameters
    ----------
    config : dict
        Application configuration dict (should contain at least the keys
        present in ``DEFAULT_CONFIG``).
    """

    # ------------------------------------------------------------------
    # Construction & loading
    # ------------------------------------------------------------------

    def __init__(self, config: dict) -> None:
        self.config: dict = config
        self.templates: Dict[str, List[dict]] = {"e": [], "f": [], "y": []}
        self.inventory_templates: List[dict] = []
        self.match_counts: Dict[str, defaultdict] = {
            "e": defaultdict(int),
            "f": defaultdict(int),
            "y": defaultdict(int),
        }
        self.start_template: Optional[np.ndarray] = None
        self._load_all()

    # ------------------------------------------------------------------
    # Image preprocessing
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess(img: np.ndarray) -> np.ndarray:
        """Apply contrast enhancement and binary thresholding.

        Parameters
        ----------
        img : np.ndarray
            Grayscale image (uint8).

        Returns
        -------
        np.ndarray
            Binary image ready for template matching.
        """
        p = cv2.convertScaleAbs(img, alpha=2.5, beta=10)
        _, binary = cv2.threshold(p, 160, 255, cv2.THRESH_BINARY_INV)
        return binary

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        """Load all key templates, start template, and inventory templates."""
        # --- Key templates (E / F / Y) --------------------------------
        for key in ("e", "f", "y"):
            folder = resource_path(key.upper())
            if not os.path.isdir(folder):
                continue
            files = glob.glob(os.path.join(folder, f"{key}_*.png"))
            count = 0
            for fp in files:
                try:
                    img = cv2.imread(fp, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        self.templates[key].append(
                            {"image": self._preprocess(img), "index": count, "path": fp}
                        )
                        count += 1
                except Exception as exc:
                    logger.error("Template load error %s: %s", fp, exc)
            logger.info("Loaded %d templates for %s", count, key.upper())

        # --- Start template -------------------------------------------
        sp = resource_path("start_e.png")
        if os.path.exists(sp):
            self.start_template = cv2.imread(sp, cv2.IMREAD_GRAYSCALE)
            if self.start_template is not None:
                logger.info("Start template loaded (shape: %s)", self.start_template.shape)

        # --- Inventory (BALO) templates -------------------------------
        balo_dir = resource_path("BALO")
        if os.path.isdir(balo_dir):
            files = glob.glob(os.path.join(balo_dir, "*.png"))
            for fp in files:
                try:
                    img = cv2.imread(fp, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        self.inventory_templates.append({"image": img, "path": fp})
                except Exception as exc:
                    logger.error("Inventory template error %s: %s", fp, exc)
            logger.info("Loaded %d inventory templates", len(self.inventory_templates))

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------

    def get_sorted_templates(self, key: str) -> List[dict]:
        """Return templates for *key* sorted by historical match count (desc)."""
        return sorted(
            self.templates.get(key, []),
            key=lambda t: self.match_counts[key][t["index"]],
            reverse=True,
        )

    def record_match(self, key: str, idx: int) -> None:
        """Increment the match counter for the given *key* / *idx* pair."""
        self.match_counts[key][idx] += 1

    def get_template_count(self) -> Dict[str, int]:
        """Return ``{key: count}`` for every loaded template group."""
        return {k: len(v) for k, v in self.templates.items()}

    # ------------------------------------------------------------------
    # Multi-scale template matching
    # ------------------------------------------------------------------

    def match_screen(
        self,
        gray: np.ndarray,
        keys: List[str],
        threshold: float,
        gpu: Any | None = None,
    ) -> Tuple[str, float, float, Optional[Tuple[int, int]]]:
        """Match the screen capture against all templates at multiple scales.

        Scans **every** key group independently so that F and Y are always
        evaluated even when E has a high-confidence match.  Early-exit is
        only applied *within* a single key group (at 0.85+).

        Parameters
        ----------
        gray : np.ndarray
            Grayscale screen capture.
        keys : list[str]
            Which key groups to search (e.g. ``["e", "f", "y"]``).
        threshold : float
            Minimum confidence to consider a match valid.
        gpu : GPUAccelerator | None, optional
            If provided **and** its ``available`` attribute is truthy, GPU-
            accelerated ``template_match()`` is used.

        Returns
        -------
        tuple[str, float, float, tuple[int, int] | None]
            ``(best_key, best_score, elapsed_ms, best_position)``.
            *best_position* is ``(x, y)`` of the match location or ``None``.
        """
        t0 = time.perf_counter()
        screen_bin = self._preprocess(gray)

        scales: List[float] = self.config.get(
            "scale_range", [0.85, 0.95, 1.0, 1.05, 1.15]
        )

        # Per-key early-exit threshold (high enough to be confident
        # this really IS the correct key, but we still scan other keys
        # to compare).
        INTRA_KEY_EXIT: float = 0.85

        best_score: float = 0.0
        best_key: str = ""
        best_idx: int = -1
        best_position: Optional[Tuple[int, int]] = None

        use_gpu = gpu is not None and getattr(gpu, "is_available", False)

        for key in keys:
            key_best: float = 0.0   # best score within this key group

            for tmpl in self.get_sorted_templates(key):
                tmpl_img = tmpl["image"]

                for scale in scales:
                    # Resize template if scale != 1.0
                    if scale == 1.0:
                        scaled = tmpl_img
                    else:
                        new_w = max(1, int(tmpl_img.shape[1] * scale))
                        new_h = max(1, int(tmpl_img.shape[0] * scale))
                        scaled = cv2.resize(
                            tmpl_img, (new_w, new_h), interpolation=cv2.INTER_LINEAR
                        )

                    sh, sw = scaled.shape[:2]
                    if sh > screen_bin.shape[0] or sw > screen_bin.shape[1]:
                        continue

                    # --- Matching (GPU or CPU) ---
                    if use_gpu:
                        try:
                            res = gpu.template_match(screen_bin, scaled)
                        except Exception:
                            res = cv2.matchTemplate(
                                screen_bin, scaled, cv2.TM_CCOEFF_NORMED
                            )
                    else:
                        res = cv2.matchTemplate(
                            screen_bin, scaled, cv2.TM_CCOEFF_NORMED
                        )

                    _, mx, _, mx_loc = cv2.minMaxLoc(res)

                    if mx > key_best:
                        key_best = mx

                    if mx > best_score:
                        best_score = mx
                        best_key = key
                        best_idx = tmpl["index"]
                        best_position = (mx_loc[0], mx_loc[1])

                    # Early exit within THIS key's scales if very confident
                    if key_best >= INTRA_KEY_EXIT:
                        break

                # Early exit within THIS key's templates if very confident
                if key_best >= INTRA_KEY_EXIT:
                    break

            # Log per-key best for debugging
            if key_best > 0:
                logger.debug(
                    "match_screen [%s] key_best=%.4f | global_best=%s %.4f",
                    key.upper(), key_best, best_key.upper(), best_score,
                )

            # NOTE: Do NOT break out of keys loop here.
            # Always scan all key groups so F and Y get a chance.

        elapsed = (time.perf_counter() - t0) * 1000

        if best_score >= threshold and best_idx >= 0:
            self.record_match(best_key, best_idx)
            logger.debug(
                "match_screen -> %s (score=%.4f, tmpl=#%d, %.1fms)",
                best_key.upper(), best_score, best_idx, elapsed,
            )

        return best_key, best_score, elapsed, best_position

    # ------------------------------------------------------------------
    # Template deduplication
    # ------------------------------------------------------------------

    def deduplicate_templates(self, ssim_threshold: float = 0.95) -> Dict[str, dict]:
        """Remove near-duplicate templates using normalised cross-correlation.

        For each pair of templates in a key group, compute the NCC score.
        When two templates exceed *ssim_threshold*, the one with the **lower**
        historical match count is removed.

        Parameters
        ----------
        ssim_threshold : float
            Similarity threshold in ``[0, 1]``.  Pairs above this are
            considered duplicates.

        Returns
        -------
        dict[str, dict]
            ``{key: {"original": N, "kept": M, "removed": K}}``
        """
        stats: Dict[str, dict] = {}

        for key in ("e", "f", "y"):
            templates = self.templates.get(key, [])
            original_count = len(templates)
            if original_count < 2:
                stats[key] = {"original": original_count, "kept": original_count, "removed": 0}
                continue

            # Build a set of indices to remove
            to_remove: set[int] = set()

            for i in range(len(templates)):
                if i in to_remove:
                    continue
                for j in range(i + 1, len(templates)):
                    if j in to_remove:
                        continue

                    img_a = templates[i]["image"]
                    img_b = templates[j]["image"]

                    # Resize to common size for comparison
                    h = max(img_a.shape[0], img_b.shape[0])
                    w = max(img_a.shape[1], img_b.shape[1])
                    a_resized = cv2.resize(img_a, (w, h))
                    b_resized = cv2.resize(img_b, (w, h))

                    # Normalised cross-correlation
                    res = cv2.matchTemplate(
                        a_resized, b_resized, cv2.TM_CCOEFF_NORMED
                    )
                    similarity = float(res[0][0]) if res.size else 0.0

                    if similarity >= ssim_threshold:
                        # Keep the template with higher match count
                        count_i = self.match_counts[key][templates[i]["index"]]
                        count_j = self.match_counts[key][templates[j]["index"]]
                        loser = j if count_i >= count_j else i
                        to_remove.add(loser)

            # Filter templates
            self.templates[key] = [
                t for idx, t in enumerate(templates) if idx not in to_remove
            ]
            removed_count = original_count - len(self.templates[key])
            stats[key] = {
                "original": original_count,
                "kept": len(self.templates[key]),
                "removed": removed_count,
            }
            if removed_count:
                logger.info(
                    "Dedup [%s]: %d → %d (removed %d)",
                    key.upper(), original_count, len(self.templates[key]), removed_count,
                )

        return stats

    # ------------------------------------------------------------------
    # Start-screen & inventory checks
    # ------------------------------------------------------------------

    def check_start(self, gray: np.ndarray, threshold: float) -> bool:
        """Return ``True`` if the start template matches in *gray*."""
        if self.start_template is None:
            return False
        try:
            th, tw = self.start_template.shape[:2]
            if th > gray.shape[0] or tw > gray.shape[1]:
                return False
            res = cv2.matchTemplate(gray, self.start_template, cv2.TM_CCOEFF_NORMED)
            _, mx, _, _ = cv2.minMaxLoc(res)
            return mx >= threshold
        except Exception:
            return False

    def check_inventory_full(
        self, gray: np.ndarray, threshold: float
    ) -> Tuple[bool, float]:
        """Check whether any inventory-full template matches.

        Returns
        -------
        tuple[bool, float]
            ``(is_full, best_score)``
        """
        for tmpl in self.inventory_templates:
            try:
                th, tw = tmpl["image"].shape[:2]
                if th > gray.shape[0] or tw > gray.shape[1]:
                    continue
                res = cv2.matchTemplate(gray, tmpl["image"], cv2.TM_CCOEFF_NORMED)
                _, mx, _, _ = cv2.minMaxLoc(res)
                if mx >= threshold:
                    return True, mx
            except Exception:
                continue
        return False, 0.0

    # ------------------------------------------------------------------
    # Notification colour detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_notification_color(
        bgra_img: np.ndarray, min_ratio: float = 0.03
    ) -> Tuple[bool, float]:
        """Detect a pink / red notification bar from GTA5VN by HSV colour.

        Parameters
        ----------
        bgra_img : np.ndarray
            BGRA image captured from screen.
        min_ratio : float
            Minimum ratio of pink pixels to total pixels.

        Returns
        -------
        tuple[bool, float]
            ``(detected, ratio)``
        """
        try:
            bgr = cv2.cvtColor(bgra_img, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

            lower1 = np.array([155, 40, 60])
            upper1 = np.array([180, 255, 255])
            mask1 = cv2.inRange(hsv, lower1, upper1)

            lower2 = np.array([0, 40, 60])
            upper2 = np.array([12, 255, 255])
            mask2 = cv2.inRange(hsv, lower2, upper2)

            lower3 = np.array([140, 30, 50])
            upper3 = np.array([160, 200, 220])
            mask3 = cv2.inRange(hsv, lower3, upper3)

            combined = cv2.bitwise_or(mask1, cv2.bitwise_or(mask2, mask3))
            pink_pixels = cv2.countNonZero(combined)
            total_pixels = combined.shape[0] * combined.shape[1]
            ratio = pink_pixels / max(total_pixels, 1)
            return ratio >= min_ratio, ratio
        except Exception:
            return False, 0.0
