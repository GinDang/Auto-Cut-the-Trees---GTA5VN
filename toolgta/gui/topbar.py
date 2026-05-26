"""AUTO GTA5VN v5.0 — Top Bar Widget

Horizontal status bar showing app title, status indicator, FPS,
confidence score, GPU status, and resolution info.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from ..constants import C, APP_VERSION, blend

if TYPE_CHECKING:
    pass


class TopBar(ctk.CTkFrame):
    """Top status bar for the main application window.

    Displays:
        - App title and version
        - Pulsing status dot + status text
        - FPS counter
        - Confidence score
        - GPU indicator
        - Screen resolution
    """

    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent, fg_color=C['bg_card'], height=42, corner_radius=0)
        self.pack(fill='x')
        self.pack_propagate(False)

        self._pulse_state: bool = True
        self._build()

    # ── Construction ─────────────────────────────────────────

    def _build(self) -> None:
        """Construct all top-bar widgets."""
        inner = ctk.CTkFrame(self, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=14)

        # App title
        ctk.CTkLabel(
            inner, text='AUTO GTA5VN',
            font=ctk.CTkFont(family='Segoe UI', size=16, weight='bold'),
            text_color=C['white'],
        ).pack(side='left')

        self._separator(inner)

        # Pulsing status dot
        self.dot = ctk.CTkLabel(
            inner, text='●', font=ctk.CTkFont(size=14, weight='bold'),
            text_color=C['text_dim'], width=14,
        )
        self.dot.pack(side='left', padx=(0, 4))

        # Status text
        self.status_lbl = ctk.CTkLabel(
            inner, text='Cho khoi chay',
            font=ctk.CTkFont(family='Segoe UI', size=12),
            text_color=C['text_sec'],
        )
        self.status_lbl.pack(side='left')

        self._separator(inner)

        # FPS
        self.fps_lbl = ctk.CTkLabel(
            inner, text='FPS --',
            font=ctk.CTkFont(family='Consolas', size=11),
            text_color=C['text_dim'],
        )
        self.fps_lbl.pack(side='left', padx=(0, 12))

        # Confidence score
        self.conf_lbl = ctk.CTkLabel(
            inner, text='Score --',
            font=ctk.CTkFont(family='Consolas', size=11),
            text_color=C['text_dim'],
        )
        self.conf_lbl.pack(side='left')

        # Right-side: resolution
        self.res_lbl = ctk.CTkLabel(
            inner, text='...',
            font=ctk.CTkFont(family='Consolas', size=10),
            text_color=C['text_dim'],
        )
        self.res_lbl.pack(side='right', padx=(6, 0))

        # GPU indicator
        self.gpu_lbl = ctk.CTkLabel(
            inner, text='CPU',
            font=ctk.CTkFont(family='Consolas', size=10),
            text_color=C['text_dim'],
        )
        self.gpu_lbl.pack(side='right', padx=(0, 10))

        # Separator before GPU
        self._separator(inner, side='right')

        # Version label
        ctk.CTkLabel(
            inner, text=f'v{APP_VERSION}',
            font=ctk.CTkFont(family='Consolas', size=10),
            text_color=C['text_dim'],
        ).pack(side='right', padx=(0, 8))

    @staticmethod
    def _separator(parent: ctk.CTkFrame, side: str = 'left') -> None:
        """Insert a vertical separator line."""
        ctk.CTkFrame(
            parent, width=1, fg_color=C['border'],
        ).pack(side=side, fill='y', padx=14, pady=8)

    # ── Public API ───────────────────────────────────────────

    _STATE_COLORS: dict[str, str] = {
        'running': C['green'],
        'paused': C['yellow'],
        'stopped': C['text_sec'],
        'inventory_full': C['orange'],
    }

    def set_status(self, text: str, state: str) -> None:
        """Update status text and color based on state."""
        self.status_lbl.configure(text=text)
        color = self._STATE_COLORS.get(state, C['text_sec'])
        self.status_lbl.configure(text_color=color)

    def set_fps(self, value: float) -> None:
        """Update FPS display."""
        self.fps_lbl.configure(text=f'FPS {value:.0f}')

    def set_confidence(self, value: float) -> None:
        """Update confidence score with color coding."""
        if value >= 0.55:
            color = C['green']
        elif value >= 0.40:
            color = C['yellow']
        else:
            color = C['text_dim']
        self.conf_lbl.configure(text=f'Score {value:.3f}', text_color=color)

    def set_resolution(self, w: int, h: int) -> None:
        """Display screen resolution."""
        self.res_lbl.configure(text=f'{w}x{h}')

    def set_gpu(self, name: str) -> None:
        """Display GPU device name or 'CPU'."""
        is_gpu = name.upper() != 'CPU'
        color = C['green'] if is_gpu else C['text_dim']
        prefix = '⚡ ' if is_gpu else ''
        self.gpu_lbl.configure(text=f'{prefix}{name}', text_color=color)

    def pulse(self, running: bool, paused: bool, inv_paused: bool) -> None:
        """Animate the status dot based on engine state.

        Called periodically (~550ms) from the main app loop.
        """
        self._pulse_state = not self._pulse_state

        if running and not paused and not inv_paused:
            c = C['green'] if self._pulse_state else blend(C['green'], 0.3)
            self.dot.configure(text_color=c)
        elif paused:
            c = C['yellow'] if self._pulse_state else blend(C['yellow'], 0.3)
            self.dot.configure(text_color=c)
        elif inv_paused:
            c = C['orange'] if self._pulse_state else blend(C['orange'], 0.3)
            self.dot.configure(text_color=c)
        elif not running:
            self.dot.configure(text_color=C['text_dim'])
