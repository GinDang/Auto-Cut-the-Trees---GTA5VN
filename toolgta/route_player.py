"""AUTO GTA5VN v5.0 — Route Player

Replays a recorded route with checkpoint verification,
self-correction, and stuck detection.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import keyboard

from .checkpoint import CheckpointVerifier
from .mouse_control import MouseController
from .route_recorder import Route, RouteStep
from .utils import emergency_release, is_game_foreground, get_screen_resolution

logger = logging.getLogger("AutoGTA")


class RoutePlayer:
    """Plays back a recorded :class:`Route`.

    Parameters
    ----------
    route : Route
        The route to replay.
    checkpoint_verifier : CheckpointVerifier
        For position verification.
    mouse_ctrl : MouseController
        For mouse movement.
    config : dict
        Application config.
    ui_cb : callable | None
        ``ui_cb(event, data)`` for GUI updates.
    """

    def __init__(
        self,
        route: Route,
        checkpoint_verifier: CheckpointVerifier,
        mouse_ctrl: MouseController,
        config: dict,
        ui_cb: Optional[Callable] = None,
    ) -> None:
        self.route = route
        self._cp = checkpoint_verifier
        self._mouse = mouse_ctrl
        self.config = config
        self._ui_cb = ui_cb

        self._playing = False
        self._paused = False
        self._current_idx = 0
        self._loop_count = 0
        self._mode = "main"  # "main" or "sell"

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Stuck detection
        self._consecutive_low: int = 0
        self._stuck_threshold: int = config.get("stuck_max_low", 3)

        # Keys currently held by player
        self._held_keys: set = set()

        # Game window check
        self._game_keywords: list = config.get("game_window_keywords", [])
        self._game_paused: bool = False

        # Resolution scaling: adjust mouse deltas if screen changed
        rec_w, rec_h = route.resolution
        cur_w, cur_h = get_screen_resolution()
        self._scale_x: float = cur_w / rec_w if rec_w > 0 else 1.0
        self._scale_y: float = cur_h / rec_h if rec_h > 0 else 1.0

        # Speed multiplier (1.0 = normal)
        self._speed_mult: float = config.get("route_speed", 1.0)

    # ------------------------------------------------------------------
    #  Properties
    # ------------------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def progress(self) -> float:
        """Playback progress ``[0.0, 1.0]``."""
        steps = self._active_steps
        if not steps:
            return 0.0
        return min(1.0, self._current_idx / max(len(steps), 1))

    @property
    def current_step(self) -> int:
        return self._current_idx

    @property
    def loop_count(self) -> int:
        return self._loop_count

    @property
    def _active_steps(self) -> list:
        if self._mode == "sell":
            return self.route.sell_steps
        return self.route.steps

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start route playback in a daemon thread."""
        if self._playing:
            return
        self._playing = True
        self._paused = False
        self._current_idx = 0
        self._mode = "main"
        self._stop_event.clear()
        self._held_keys.clear()

        self._thread = threading.Thread(target=self._play_loop, daemon=True)
        self._thread.start()
        logger.info("Route playback started: %s", self.route.name)

    def stop(self) -> None:
        """Stop playback and release all keys."""
        self._playing = False
        self._stop_event.set()
        self._release_all()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("Route playback stopped (loop=%d)", self._loop_count)

    def pause(self) -> None:
        self._paused = True
        self._release_all()

    def resume(self) -> None:
        self._paused = False

    def switch_to_sell(self) -> None:
        """Switch to playing the sell route."""
        self._release_all()
        self._mode = "sell"
        self._current_idx = 0
        logger.info("Switched to sell route (%d steps)", len(self.route.sell_steps))

    def switch_to_main(self) -> None:
        """Switch back to main route from beginning."""
        self._release_all()
        self._mode = "main"
        self._current_idx = 0
        self._loop_count += 1
        logger.info("Switched to main route (loop #%d)", self._loop_count)

    # ------------------------------------------------------------------
    #  Main loop
    # ------------------------------------------------------------------

    def _play_loop(self) -> None:
        """Main playback thread."""
        try:
            while self._playing and not self._stop_event.is_set():
                # Pause check
                if self._paused:
                    self._stop_event.wait(0.3)
                    continue

                # Game foreground check — pause when game not active
                if self._game_keywords and not is_game_foreground(self._game_keywords):
                    if not self._game_paused:
                        self._game_paused = True
                        self._release_all()
                        self._notify("status", {"text": "Route tạm dừng — game không active", "state": "paused"})
                    self._stop_event.wait(0.5)
                    continue
                elif self._game_paused:
                    self._game_paused = False
                    self._notify("status", {"text": "Route tiếp tục", "state": "running"})

                steps = self._active_steps
                if not steps:
                    self._stop_event.wait(0.5)
                    continue

                # End of route?
                if self._current_idx >= len(steps):
                    if self._mode == "sell":
                        # Sell route finished → back to main
                        self._notify("sell_complete", {})
                        self.switch_to_main()
                        continue
                    else:
                        # Main route finished → loop
                        loop = self.config.get("route_loop", True)
                        if loop:
                            self.switch_to_main()
                            continue
                        else:
                            break

                step = steps[self._current_idx]

                # Execute step
                self._execute_step(step)

                # Handle markers
                if step.action == "marker":
                    self._handle_marker(step)

                # Checkpoint verification
                if step.checkpoint_idx > 0:
                    score = self._verify_checkpoint(step)
                    if score >= 0:
                        self._notify("checkpoint", {
                            "idx": step.checkpoint_idx,
                            "score": score,
                        })

                # Wait for timing
                next_idx = self._current_idx + 1
                if next_idx < len(steps):
                    delay = steps[next_idx].timestamp - step.timestamp
                    # Apply speed multiplier
                    if self._speed_mult > 0:
                        delay = delay / self._speed_mult
                    if 0 < delay < 5.0:
                        self._stop_event.wait(delay)
                    elif delay >= 5.0:
                        self._stop_event.wait(0.1)

                self._current_idx += 1
                self._notify("progress", {
                    "idx": self._current_idx,
                    "total": len(steps),
                    "loop": self._loop_count,
                    "mode": self._mode,
                })

        except Exception as exc:
            logger.error("Route playback error: %s", exc, exc_info=True)
        finally:
            self._release_all()
            self._playing = False
            self._notify("playback_stopped", {"loop": self._loop_count})

    # ------------------------------------------------------------------
    #  Step execution
    # ------------------------------------------------------------------

    def _execute_step(self, step: RouteStep) -> None:
        """Execute a single route step."""
        try:
            if step.action == "key_down":
                keyboard.press(step.key)
                self._held_keys.add(step.key)
            elif step.action == "key_up":
                keyboard.release(step.key)
                self._held_keys.discard(step.key)
            elif step.action == "mouse_move":
                # Scale mouse deltas for different resolutions
                dx = int(step.dx * self._scale_x)
                dy = int(step.dy * self._scale_y)
                self._mouse.move_relative(dx, dy)
            # Markers are handled separately
        except Exception as exc:
            logger.debug("Step execution error: %s", exc)

    def _handle_marker(self, step: RouteStep) -> None:
        """Handle a marker step."""
        if step.marker_type == "tree":
            self._release_all()
            self._notify("tree_reached", {
                "idx": self._current_idx,
                "total_trees": self.route.tree_count,
            })
            # Pause playback — engine's E/F/Y detection handles cutting
            # Will be resumed externally after cutting is done
            self._paused = True
            logger.info("Tree reached at step %d — pausing for cutting", self._current_idx)

        elif step.marker_type == "sell":
            self._release_all()
            self._notify("sell_reached", {})
            self._paused = True
            logger.info("Sell point reached — pausing for sell interaction")

    # ------------------------------------------------------------------
    #  Checkpoint verification
    # ------------------------------------------------------------------

    def _verify_checkpoint(self, step: RouteStep) -> float:
        """Verify position at a checkpoint.  Returns score or -1."""
        import os
        cp_dir = self.route.checkpoint_dir
        if not cp_dir:
            return -1.0

        cp_path = os.path.join(
            cp_dir, "checkpoints", f"cp_{step.checkpoint_idx:03d}.png"
        )
        if not os.path.exists(cp_path):
            return -1.0

        score = self._cp.compare_with_file(cp_path)
        logger.debug("Checkpoint %d score: %.3f", step.checkpoint_idx, score)

        # Stuck detection
        if score < self._cp.threshold * 0.7:
            self._consecutive_low += 1
            if self._consecutive_low >= self._stuck_threshold:
                logger.warning("Stuck detected! %d consecutive low scores", self._consecutive_low)
                self._unstuck()
                self._consecutive_low = 0
        else:
            self._consecutive_low = 0

        return score

    def _unstuck(self) -> None:
        """Try to get unstuck."""
        self._release_all()
        self._notify("stuck", {"idx": self._current_idx})
        logger.info("Attempting to unstuck...")

        try:
            # Step back
            keyboard.press("s")
            time.sleep(1.0)
            keyboard.release("s")

            # Jump
            keyboard.press("space")
            time.sleep(0.2)
            keyboard.release("space")

            # Random rotate
            self._mouse.random_look(max_dx=120)
            time.sleep(0.3)

            # Forward again
            keyboard.press("w")
            time.sleep(0.5)
            keyboard.release("w")
        except Exception:
            pass

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    def _release_all(self) -> None:
        """Release all held keys."""
        for key in list(self._held_keys):
            try:
                keyboard.release(key)
            except Exception:
                pass
        self._held_keys.clear()
        emergency_release()

    def _notify(self, event: str, data: dict) -> None:
        if self._ui_cb:
            try:
                self._ui_cb(event, data)
            except Exception:
                pass
