"""AUTO GTA5VN v5.0 — Game State Machine

Finite State Machine that manages the overall automation state.
Each state has enter/exit hooks and the engine dispatches logic
based on the current state.
"""
from __future__ import annotations

import logging
import time
from enum import Enum, auto
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger("AutoGTA")


class GameState(Enum):
    """All possible automation states."""

    IDLE = auto()
    RECORDING = auto()
    NAVIGATING = auto()
    CUTTING = auto()
    SELLING = auto()
    PAUSED = auto()
    STUCK = auto()


class StateMachine:
    """Manages game automation state transitions.

    Parameters
    ----------
    ui_cb : callable | None
        ``ui_cb(event_name, data_dict)`` callback for GUI updates.
    """

    def __init__(
        self, ui_cb: Optional[Callable[[str, Optional[dict]], None]] = None
    ) -> None:
        self.state: GameState = GameState.IDLE
        self.prev_state: GameState = GameState.IDLE
        self.state_enter_time: float = time.time()
        self.state_data: dict[str, Any] = {}
        self._transition_log: List[Tuple[float, str, str, str]] = []
        self._ui_cb = ui_cb

    # ------------------------------------------------------------------
    #  Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """``True`` if not IDLE or PAUSED."""
        return self.state not in (GameState.IDLE, GameState.PAUSED)

    @property
    def state_name(self) -> str:
        return self.state.name

    # ------------------------------------------------------------------
    #  Transitions
    # ------------------------------------------------------------------

    def transition(self, new_state: GameState, reason: str = "") -> None:
        """Transition to *new_state*, log, and notify UI."""
        if new_state == self.state:
            return

        old = self.state
        self.prev_state = old
        self.state = new_state
        self.state_enter_time = time.time()
        self.state_data = {}

        entry = (time.time(), old.name, new_state.name, reason)
        self._transition_log.append(entry)
        if len(self._transition_log) > 200:
            self._transition_log = self._transition_log[-100:]

        logger.info(
            "FSM: %s -> %s (%s)", old.name, new_state.name, reason or "—"
        )

        if self._ui_cb:
            try:
                self._ui_cb(
                    "state_change",
                    {
                        "state": new_state.name,
                        "prev": old.name,
                        "reason": reason,
                    },
                )
            except Exception:
                pass

    def time_in_state(self) -> float:
        """Seconds since entering current state."""
        return time.time() - self.state_enter_time

    def get_log(self, last_n: int = 20) -> List[Tuple[float, str, str, str]]:
        """Return the most recent *last_n* transition entries."""
        return self._transition_log[-last_n:]

    def reset(self) -> None:
        """Reset to IDLE."""
        self.transition(GameState.IDLE, reason="reset")
        self._transition_log.clear()
        self.state_data = {}
