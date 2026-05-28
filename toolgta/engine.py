"""AUTO GTA5VN v5.0 — Auto Engine

Core automation loop with ROI tracking, adaptive thresholds,
sequence prediction, and humanised key presses.
"""
from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import keyboard
import numpy as np
from mss import MSS

from .constants import C
from .utils import calc_region, emergency_release, get_screen_resolution, is_game_foreground
from .stats import SessionStats
from .gpu_utils import GPUAccelerator

logger = logging.getLogger("AutoGTA")


# ======================================================================
#  ROI Tracker
# ======================================================================


class ROITracker:
    """Track the last match position and provide a smaller search region.

    When a match is found, subsequent frames search a cropped region
    around the last match location.  After *max_misses* consecutive
    failures the tracker falls back to the full region.

    Parameters
    ----------
    padding : int
        Pixels to add around the last match position.
    """

    def __init__(self, padding: int = 50) -> None:
        self.last_match_pos: Optional[Tuple[int, int]] = None
        self.padding: int = padding
        self.miss_count: int = 0
        self.max_misses: int = 5

    def get_roi(
        self, full_region: dict, screen_shape: Tuple[int, int]
    ) -> Optional[dict]:
        """Return a cropped ROI dict if a recent match exists, else ``None``.

        Parameters
        ----------
        full_region : dict
            Original ``{"top", "left", "width", "height"}`` region.
        screen_shape : tuple[int, int]
            ``(height, width)`` of the full screen.

        Returns
        -------
        dict | None
            Cropped region dict, or ``None`` to indicate *use full region*.
        """
        if self.last_match_pos is None or self.miss_count >= self.max_misses:
            return None

        mx, my = self.last_match_pos
        abs_x = full_region["left"] + mx
        abs_y = full_region["top"] + my

        new_left = max(0, abs_x - self.padding)
        new_top = max(0, abs_y - self.padding)
        new_right = min(screen_shape[1], abs_x + self.padding)
        new_bottom = min(screen_shape[0], abs_y + self.padding)

        return {
            "top": new_top,
            "left": new_left,
            "width": max(1, new_right - new_left),
            "height": max(1, new_bottom - new_top),
        }

    def update(self, matched: bool, position: Optional[Tuple[int, int]] = None) -> None:
        """Update tracker state after a match attempt."""
        if matched and position:
            self.last_match_pos = position
            self.miss_count = 0
        elif not matched:
            self.miss_count += 1


# ======================================================================
#  Adaptive Confidence Threshold
# ======================================================================


class AdaptiveThreshold:
    """Dynamically adjust the match confidence threshold.

    The threshold is computed as the midpoint between the 10th-percentile
    of true-match scores and the maximum non-match score, clamped to
    ``[min_threshold, max_threshold]``.

    Parameters
    ----------
    base : float
        Default threshold used until enough history is collected.
    window : int
        Maximum number of score samples to keep.
    min_threshold : float
        Absolute lower bound.
    max_threshold : float
        Absolute upper bound.
    """

    def __init__(
        self,
        base: float = 0.65,
        window: int = 100,
        min_threshold: float = 0.50,
        max_threshold: float = 0.80,
    ) -> None:
        self.base: float = base
        self.window: int = window
        self.min_t: float = min_threshold
        self.max_t: float = max_threshold
        self.history: deque[Tuple[float, bool]] = deque(maxlen=window)

    def update(self, score: float, was_match: bool) -> None:
        """Record a score observation."""
        self.history.append((score, was_match))

    @property
    def current(self) -> float:
        """Return the current adaptive threshold."""
        if len(self.history) < 20:
            return self.base

        matches = [s for s, m in self.history if m]
        non_matches = [s for s, m in self.history if not m]

        if matches and non_matches:
            lowest_match = sorted(matches)[len(matches) // 10]  # 10th percentile
            highest_non = sorted(non_matches)[-1]
            optimal = (lowest_match + highest_non) / 2
            return max(self.min_t, min(self.max_t, optimal))

        return self.base


# ======================================================================
#  Sequence Predictor
# ======================================================================


class SequencePredictor:
    """Predict the next key based on detected repeating patterns.

    Parameters
    ----------
    max_history : int
        Maximum number of key events to retain.
    """

    def __init__(self, max_history: int = 50) -> None:
        self.history: deque[str] = deque(maxlen=max_history)

    def record(self, key: str) -> None:
        """Record a matched key."""
        self.history.append(key)

    def predict_next(self) -> Optional[str]:
        """Predict the most likely next key based on pattern detection.

        Looks for repeating subsequences of lengths 3, 2, 4, and 5.

        Returns
        -------
        str | None
            Predicted next key, or ``None`` if no pattern found.
        """
        if len(self.history) < 3:
            return None

        h = list(self.history)
        for plen in (3, 2, 4, 5):
            if len(h) >= plen * 2:
                pattern = h[-plen:]
                prev = h[-2 * plen : -plen]
                if pattern == prev:
                    return pattern[0]
        return None

    def get_prioritized_keys(self, all_keys: List[str]) -> List[str]:
        """Return *all_keys* reordered so the predicted key comes first."""
        predicted = self.predict_next()
        if predicted and predicted in all_keys:
            return [predicted] + [k for k in all_keys if k != predicted]
        return list(all_keys)


# ======================================================================
#  Humanised Input Helpers
# ======================================================================


def humanized_send(key: str, jitter: float = 0.3) -> None:
    """Send a key press with human-like hold-time variation.

    Parameters
    ----------
    key : str
        Key name recognised by the ``keyboard`` library.
    jitter : float
        Unused here but kept for API symmetry with ``humanized_delay``.
    """
    hold = random.uniform(0.01, 0.05)
    keyboard.press(key)
    time.sleep(hold)
    keyboard.release(key)


def humanized_delay(base_ms: float, jitter: float = 0.3) -> float:
    """Return a delay (in **seconds**) with random jitter applied.

    Parameters
    ----------
    base_ms : float
        Base delay in **milliseconds**.
    jitter : float
        Fractional jitter range (e.g. 0.3 → ±30 %).

    Returns
    -------
    float
        Actual delay in seconds (minimum 5 ms).
    """
    variation = random.uniform(-jitter, jitter)
    actual = base_ms * (1 + variation)
    return max(5, actual) / 1000.0


# ======================================================================
#  Auto Engine
# ======================================================================


class AutoEngine:
    """Core automation engine driving the screen-capture → match → keypress loop.

    Parameters
    ----------
    tmgr : TemplateManager
        Template manager instance.
    config : dict
        Application configuration.
    ui_cb : callable | None
        ``ui_cb(event_name, data_dict)`` callback for GUI updates.
    """

    def __init__(
        self,
        tmgr: Any,
        config: dict,
        ui_cb: Optional[Callable[[str, Optional[dict]], None]] = None,
        gpu: Optional[GPUAccelerator] = None,
    ) -> None:
        self.tmgr = tmgr
        self.config: dict = config
        self.ui_cb = ui_cb

        # Engine state
        self.running: bool = False
        self.paused: bool = False
        self.stop_event: threading.Event = threading.Event()
        self.current_mode: int = 0
        self.counters: Dict[str, int] = {"e": 0, "f": 0, "y": 0}
        self.fps: float = 0.0
        self.last_confidence: float = 0.0
        self.inventory_full_notified: bool = False
        self.inventory_paused: bool = False
        self.wood_estimate: int = 0

        # Advanced subsystems
        self._roi_tracker: ROITracker = ROITracker(
            padding=self.config.get("roi_padding", 50)
        )
        self._adaptive: AdaptiveThreshold = AdaptiveThreshold(
            base=self.config.get("confidence_threshold", 0.55)
        )
        self._predictor: SequencePredictor = SequencePredictor(max_history=50)
        self._gpu: GPUAccelerator = gpu if gpu is not None else GPUAccelerator()
        self._stats: SessionStats = SessionStats()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self, mode: int) -> bool:
        """Start the automation loop in the given *mode*.

        Returns ``False`` if already running.  Mode 4 (Route Auto)
        is handled externally by the app — this method will simply
        return ``True`` to acknowledge.
        """
        if self.running:
            return False
        if mode == 4:
            # Mode 4 is managed by the app's Route Player, not this engine
            logger.info("Mode 4 (Route Auto) — managed by app")
            return True
        self.running = True
        self.paused = False
        self.current_mode = mode
        self.stop_event.clear()
        self.counters = {"e": 0, "f": 0, "y": 0}
        self.inventory_full_notified = False
        self.inventory_paused = False
        self.wood_estimate = 0
        self._roi_tracker = ROITracker(padding=self.config.get("roi_padding", 50))
        self._adaptive = AdaptiveThreshold(
            base=self.config.get("confidence_threshold", 0.55)
        )
        self._predictor = SequencePredictor(max_history=50)
        self._stats = SessionStats()
        threading.Thread(target=self._run, args=(mode,), daemon=True).start()
        logger.info("Started mode %d", mode)
        return True

    def stop(self) -> None:
        """Stop the automation loop and release held keys."""
        self.running = False
        self.stop_event.set()
        emergency_release()
        logger.info("Stopped")

    def resume_from_full(self) -> None:
        """Resume the loop after an inventory-full pause."""
        self.inventory_paused = False
        self.inventory_full_notified = True
        self._notify(
            "status",
            {"text": "Mode %d dang chay" % self.current_mode, "state": "running"},
        )
        logger.info("Resumed after full inventory")

    def get_session_stats(self) -> dict:
        """Return a snapshot of the current session statistics."""
        return self._stats.get_summary()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _notify(self, evt: str, data: Optional[dict] = None) -> None:
        """Fire the UI callback, if registered."""
        if self.ui_cb:
            self.ui_cb(evt, data)

    def _update_wood_estimate(self) -> None:
        # 1 wood = 1 complete E+F+Y cycle → use min of all counters
        self.wood_estimate = min(self.counters.values()) if self.counters else 0
        self._notify(
            "wood",
            {"count": self.wood_estimate, "max": self.config.get("max_wood_capacity", 39)},
        )

    # ------------------------------------------------------------------
    # Inventory check
    # ------------------------------------------------------------------

    def _check_inventory(
        self,
        sct: MSS,
        mon_inv: dict,
        mon_notif: dict,
        thr: float,
        continue_full: bool,
        max_wood: int,
    ) -> None:
        """Check for full inventory via colour detection and template matching."""
        if self.inventory_full_notified and self.config.get("continue_when_full", False):
            return

        is_full = False
        detect_method = ""
        score = 0.0

        try:
            # --- Colour-based detection --------------------------------
            if self.config.get("notification_color_detect", True):
                notif_img = np.array(sct.grab(mon_notif))
                color_ratio = self.config.get("notification_color_ratio", 0.03)
                color_found, ratio = self.tmgr.detect_notification_color(
                    notif_img, color_ratio
                )
                if color_found:
                    is_full = True
                    score = ratio
                    detect_method = "color"
                    logger.warning(
                        "Notification COLOR detected! (pink ratio: %.4f)", ratio
                    )

            # --- Template-based detection ------------------------------
            if not is_full and self.tmgr.inventory_templates:
                inv_img = np.array(sct.grab(mon_inv))
                inv_gray = cv2.cvtColor(inv_img, cv2.COLOR_BGRA2GRAY)
                tmpl_found, tmpl_score = self.tmgr.check_inventory_full(inv_gray, thr)
                if not tmpl_found:
                    notif_gray = cv2.cvtColor(
                        np.array(sct.grab(mon_notif)), cv2.COLOR_BGRA2GRAY
                    )
                    tmpl_found, tmpl_score = self.tmgr.check_inventory_full(
                        notif_gray, thr
                    )
                if tmpl_found:
                    is_full = True
                    score = tmpl_score
                    detect_method = "template"
                    logger.warning(
                        "Notification TEMPLATE detected! (score: %.4f)", tmpl_score
                    )

            # --- Notify -----------------------------------------------
            if is_full and not self.inventory_full_notified:
                self._notify("inventory_full", {"score": score, "method": detect_method})
                if continue_full:
                    self.inventory_full_notified = True
                    logger.info("Continue-when-full enabled")
                else:
                    self.inventory_paused = True
                    self.inventory_full_notified = True
                    self._notify(
                        "status", {"text": "DUNG - Balo day!", "state": "inventory_full"}
                    )

            # --- Estimate-based fallback DISABLED ----------------------
            # Only color detection + BALO template matching are used.
            # The estimate fallback was removed to avoid false positives
            # caused by E-counter inflation from start-screen spam.

        except Exception as exc:
            logger.error("Inventory check error: %s", exc)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run(self, mode: int) -> None:  # noqa: C901 — complex by necessity
        """Main automation loop (runs in a daemon thread)."""
        sct = MSS()
        sw, sh = get_screen_resolution()

        mon_start = calc_region(self.config["start_region"], sw, sh)
        mon_box = calc_region(self.config["detect_region"], sw, sh)
        mon_inv = calc_region(self.config["inventory_region"], sw, sh)
        mon_notif = calc_region(self.config["notification_region"], sw, sh)

        # Config values
        use_adaptive = self.config.get("adaptive_confidence", False)
        threshold = (
            self._adaptive.current
            if use_adaptive
            else self.config.get("confidence_threshold", 0.55)
        )
        start_thr = self.config.get("start_threshold", 0.78)
        inv_thr = self.config.get("inventory_threshold", 0.60)
        macro_delay = self.config.get("macro_delay_ms", 30) / 1000.0
        game_kw: list = self.config.get("game_window_keywords", [])
        continue_full = self.config.get("continue_when_full", False)
        inv_interval = self.config.get("inventory_check_interval", 60)
        max_wood = self.config.get("max_wood_capacity", 30)
        use_roi = self.config.get("roi_tracking", False)
        use_humanize = self.config.get("humanize_keys", False)

        keys_pressed = False
        fps_count = 0
        fps_t = time.perf_counter()
        macro_seq = ["e", "f", "y"]
        macro_idx = 0
        frame_count = 0
        last_inv_check = 0
        last_start_press = 0.0
        START_COOLDOWN = 5.0  # seconds before re-checking start screen

        # --- Active key tracking ---
        # Once we detect which key the game shows (E/F/Y), we "lock on"
        # and spam that key rapidly without re-scanning every template.
        # After several consecutive misses we fall back to full scan.
        active_key: str = ""          # currently locked-on key ("" = none)
        active_key_hits: int = 0      # consecutive hits on the active key
        active_key_misses: int = 0    # consecutive misses on the active key
        ACTIVE_KEY_MAX_MISSES: int = 5   # misses before resetting
        is_chopping: bool = False     # True after start E, until idle timeout
        last_match_time: float = 0.0  # timestamp of last successful match
        CHOPPING_TIMEOUT: float = 8.0  # seconds of no matches before "idle"

        self._notify(
            "status", {"text": "Mode %d dang chay" % mode, "state": "running"}
        )
        self._stats.start()

        try:
            while self.running and not self.stop_event.is_set():
                # --- Inventory pause ----------------------------------
                if self.inventory_paused:
                    if keys_pressed:
                        emergency_release()
                        keys_pressed = False
                    time.sleep(0.3)
                    continue

                # --- Game foreground check ----------------------------
                if not is_game_foreground(game_kw):
                    if not self.paused:
                        self.paused = True
                        if keys_pressed:
                            emergency_release()
                            keys_pressed = False
                        self._notify(
                            "status",
                            {"text": "Tam dung - Game khong active", "state": "paused"},
                        )
                    time.sleep(0.5)
                    continue
                elif self.paused:
                    self.paused = False
                    self._notify(
                        "status",
                        {"text": "Mode %d dang chay" % mode, "state": "running"},
                    )

                # --- FPS counter --------------------------------------
                fps_count += 1
                now = time.perf_counter()
                if now - fps_t >= 1.0:
                    self.fps = fps_count / (now - fps_t)
                    fps_count = 0
                    fps_t = now
                    self._notify("fps", {"value": self.fps})

                frame_count += 1

                # --- Inventory check ----------------------------------
                if inv_interval > 0 and (frame_count - last_inv_check) >= inv_interval:
                    last_inv_check = frame_count
                    self._check_inventory(
                        sct, mon_inv, mon_notif, inv_thr, continue_full, max_wood
                    )

                # ======================================================
                # MODE 3: Macro
                # ======================================================
                if mode == 3:
                    if not keys_pressed:
                        keyboard.press("w")
                        keyboard.press(".")
                        keys_pressed = True

                    key = macro_seq[macro_idx]
                    if use_humanize:
                        humanized_send(key)
                    else:
                        keyboard.send(key)

                    self.counters[key] += 1
                    macro_idx = (macro_idx + 1) % len(macro_seq)
                    self._notify("counter", dict(self.counters))
                    self._update_wood_estimate()
                    self._stats.record_press(key)

                    if use_humanize:
                        time.sleep(humanized_delay(self.config.get("macro_delay_ms", 30)))
                    else:
                        time.sleep(macro_delay)
                    continue

                # ======================================================
                # MODE 1 & 2: Template matching
                # ======================================================

                # --- Check chopping timeout → reset to idle -----------
                if is_chopping and (now - last_match_time) > CHOPPING_TIMEOUT:
                    logger.info("Chopping timeout (%.0fs no match) -> idle", CHOPPING_TIMEOUT)
                    is_chopping = False
                    active_key = ""
                    active_key_hits = 0
                    active_key_misses = 0

                # --- Start-screen fast-press --------------------------
                # Only check start screen when NOT actively chopping
                if (
                    not is_chopping
                    and self.tmgr.start_template is not None
                    and (now - last_start_press) >= START_COOLDOWN
                ):
                    try:
                        img = np.array(sct.grab(mon_start))
                        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                        if self.tmgr.check_start(gray, start_thr):
                            # Press E a few times to start chopping
                            for _ in range(3):
                                if use_humanize:
                                    humanized_send("e")
                                else:
                                    keyboard.send("e")
                                time.sleep(0.05)
                            last_start_press = now
                            is_chopping = True
                            last_match_time = now
                            active_key = ""
                            active_key_hits = 0
                            active_key_misses = 0
                            logger.info("Start-screen detected -> begin chopping")
                            # Small delay for game to transition
                            time.sleep(0.3)
                            continue
                    except Exception:
                        pass

                # --- Screen capture (with optional ROI) ---------------
                try:
                    capture_region = mon_box
                    if use_roi:
                        roi = self._roi_tracker.get_roi(mon_box, (sh, sw))
                        if roi is not None:
                            capture_region = roi

                    screen = np.array(sct.grab(capture_region))
                    gray = cv2.cvtColor(screen, cv2.COLOR_BGRA2GRAY)
                except Exception:
                    time.sleep(0.05)
                    continue

                if not keys_pressed:
                    keyboard.press("w")
                    keyboard.press(".")
                    keys_pressed = True

                # --- Determine scan keys ------------------------------
                if active_key:
                    # We have a locked-on key — scan ONLY that key first
                    # for speed, but also include all keys for comparison
                    scan_keys = [active_key] + [
                        k for k in (["e", "f", "y"] if mode == 1 else ["e"])
                        if k != active_key
                    ]
                else:
                    scan_keys = ["e", "f", "y"] if mode == 1 else ["e"]
                    scan_keys = self._predictor.get_prioritized_keys(scan_keys)

                # --- Adaptive threshold --------------------------------
                if use_adaptive:
                    threshold = self._adaptive.current

                # --- Template matching --------------------------------
                best_key, best_score, elapsed, best_pos = self.tmgr.match_screen(
                    gray, scan_keys, threshold, gpu=self._gpu
                )
                self.last_confidence = best_score
                self._notify("confidence", {"value": best_score})
                self._stats.record_detection_time(elapsed)
                self._stats.record_confidence(best_score)
                self._stats.record_fps(self.fps)

                matched = best_score >= threshold and bool(best_key)

                # Update adaptive threshold
                if use_adaptive:
                    self._adaptive.update(best_score, matched)

                # Update ROI tracker
                if use_roi:
                    self._roi_tracker.update(matched, best_pos)

                if matched:
                    # --- Key detected! ---
                    is_chopping = True
                    last_match_time = now

                    if best_key == active_key:
                        # Still the same key → increment hits
                        active_key_hits += 1
                        active_key_misses = 0
                    else:
                        # Different key detected → switch to it
                        if active_key:
                            logger.info(
                                "Key switch: %s -> %s (score=%.4f)",
                                active_key.upper(), best_key.upper(), best_score,
                            )
                        active_key = best_key
                        active_key_hits = 1
                        active_key_misses = 0

                    # Press the detected key
                    if use_humanize:
                        humanized_send(best_key)
                    else:
                        keyboard.send(best_key)

                    self.counters[best_key] += 1
                    self._notify("counter", dict(self.counters))
                    self._update_wood_estimate()
                    self._predictor.record(best_key)
                    self._stats.record_press(best_key)
                    logger.info(
                        "Mode %d -> %s (%.4f, %.1fms) [active=%s, hits=%d]",
                        mode, best_key.upper(), best_score, elapsed,
                        active_key.upper(), active_key_hits,
                    )

                    # Fast repeat — keep spamming the active key
                    if use_humanize:
                        time.sleep(humanized_delay(10))
                    else:
                        time.sleep(0.010)
                else:
                    # --- No match ---
                    if active_key:
                        active_key_misses += 1
                        if active_key_misses >= ACTIVE_KEY_MAX_MISSES:
                            logger.debug(
                                "Active key %s lost (%d misses) -> reset",
                                active_key.upper(), active_key_misses,
                            )
                            active_key = ""
                            active_key_hits = 0
                            active_key_misses = 0
                    time.sleep(0.020)

        except Exception as exc:
            logger.error("Loop crash: %s", exc, exc_info=True)
        finally:
            emergency_release()
            self.running = False
            self.paused = False
            self._stats.stop()
            self._notify("status", {"text": "Da dung", "state": "stopped"})

