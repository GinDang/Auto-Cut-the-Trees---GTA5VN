"""
AUTO GTA5VN - Utility Functions
Version 5.0

General-purpose helpers used across the entire application:
path resolution, screen measurement, game window detection,
logging setup, and emergency key release safety net.
"""
from __future__ import annotations

import atexit
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from typing import Any

from .constants import LOG_FILE


# ===========================================================
#  PATH RESOLUTION
# ===========================================================

def resource_path(relative_path: str) -> str:
    """Resolve a relative path for **writable** data files.

    For a PyInstaller bundle the base is the directory containing the ``.exe``
    (so that config, routes, templates live *beside* the exe and are writable).
    For dev mode it is the project root.

    Use this for: ``config.json``, ``routes/``, ``E/``, ``F/``, ``Y/``, ``BALO/``, logs.

    Args:
        relative_path: Path relative to the application root.

    Returns:
        Absolute path string.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle → use exe directory (writable)
        base: str = os.path.dirname(sys.executable)
    else:
        # Dev mode → project root (parent of toolgta/)
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


def bundled_path(relative_path: str) -> str:
    """Resolve a relative path for **readonly** bundled assets.

    For a PyInstaller bundle the base is ``sys._MEIPASS`` (temp extraction dir).
    For dev mode it is the same as :func:`resource_path`.

    Use this for: bundled default assets that don't change at runtime.

    Args:
        relative_path: Path relative to the bundle root.

    Returns:
        Absolute path string.
    """
    try:
        base: str = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


# ===========================================================
#  SCREEN HELPERS
# ===========================================================

def get_screen_resolution() -> tuple[int, int]:
    """Return the primary monitor resolution ``(width, height)`` using MSS.

    Returns:
        A tuple of ``(width, height)`` in pixels.
    """
    from mss import MSS

    with MSS() as sct:
        m: dict[str, int] = sct.monitors[1]
    return m["width"], m["height"]


def calc_region(
    pct: dict[str, float], sw: int, sh: int
) -> dict[str, int]:
    """Convert percentage-based region definition to pixel coordinates.

    Args:
        pct: Dictionary with keys ``top_pct``, ``left_pct``,
             ``width_pct``, ``height_pct`` (each in ``[0.0, 1.0]``).
        sw: Screen width in pixels.
        sh: Screen height in pixels.

    Returns:
        Dictionary with integer keys ``top``, ``left``, ``width``, ``height``.
    """
    return {
        "top": int(pct["top_pct"] * sh),
        "left": int(pct["left_pct"] * sw),
        "width": int(pct["width_pct"] * sw),
        "height": int(pct["height_pct"] * sh),
    }


# ===========================================================
#  GAME WINDOW DETECTION
# ===========================================================

def is_game_foreground(keywords: list[str]) -> bool:
    """Check whether the foreground window title contains any of *keywords*.

    Uses ``win32gui`` to read the active window title.  If the import
    or API call fails (e.g. on non-Windows systems), returns ``True``
    to avoid pausing the engine unnecessarily.

    Args:
        keywords: Substrings to match (case-insensitive) against the
                  foreground window title.

    Returns:
        ``True`` if any keyword is found in the title, or on error.
    """
    try:
        import win32gui  # type: ignore[import-untyped]

        hwnd: int = win32gui.GetForegroundWindow()
        title: str = win32gui.GetWindowText(hwnd).lower()
        return any(kw.lower() in title for kw in keywords)
    except Exception:
        return True


# ===========================================================
#  LOGGING
# ===========================================================

def setup_logger() -> logging.Logger:
    """Configure and return the application logger ``"AutoGTA"``.

    Creates both a :class:`~logging.handlers.RotatingFileHandler`
    (10 MB, 3 backups) and a :class:`~logging.StreamHandler` for
    console output.

    Returns:
        The configured :class:`logging.Logger` instance.
    """
    lg: logging.Logger = logging.getLogger("AutoGTA")
    lg.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )

    # File handler
    try:
        log_path: str = resource_path(LOG_FILE)
        fh = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        lg.addHandler(fh)
    except Exception:
        pass

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    lg.addHandler(ch)

    return lg


# ===========================================================
#  EMERGENCY KEY RELEASE
# ===========================================================

_HELD_KEYS: list[str] = ["w", ".", "e", "f", "y"]


def emergency_release() -> None:
    """Release all potentially held keyboard keys safely.

    Iterates over :data:`_HELD_KEYS` (``w``, ``.``, ``e``, ``f``,
    ``y``) and calls ``keyboard.release()`` for each one.  Errors are
    silently ignored so this function is safe to call from signal
    handlers and ``atexit``.
    """
    try:
        import keyboard  # type: ignore[import-untyped]

        for key in _HELD_KEYS:
            try:
                keyboard.release(key)
            except Exception:
                pass
    except ImportError:
        pass


def _signal_handler(signum: int, frame: Any) -> None:
    """Signal handler wrapper that calls :func:`emergency_release` and exits."""
    emergency_release()
    sys.exit(128 + signum)


# --- Register emergency release at import time ---
atexit.register(emergency_release)

try:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
except (OSError, ValueError):
    # signal.signal may fail if called from a non-main thread
    pass
