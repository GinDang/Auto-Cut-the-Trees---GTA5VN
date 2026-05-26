"""AUTO GTA5VN v5.0 — GUI Package

Modular GUI components for the Auto GTA5VN application.
Each widget is self-contained and communicates via callbacks.
"""
from __future__ import annotations

from .topbar import TopBar
from .controls import ControlPanel
from .stats_panel import StatsPanel
from .log_panel import LogPanel
from .settings import SettingsDrawer
from .notification import NotificationBar
from .capture_dialog import CaptureDialog
from .app import AutoGTAApp

__all__ = [
    'TopBar',
    'ControlPanel',
    'StatsPanel',
    'LogPanel',
    'SettingsDrawer',
    'NotificationBar',
    'CaptureDialog',
    'AutoGTAApp',
]
