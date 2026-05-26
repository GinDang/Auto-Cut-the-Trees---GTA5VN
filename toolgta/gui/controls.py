"""AUTO GTA5VN v5.0 — Control Panel Widget

Left sidebar with mode selection buttons, capture button, settings,
and stop button.  Each mode button shows its hotkey hint.
"""
from __future__ import annotations

from typing import Callable, TYPE_CHECKING

import customtkinter as ctk

from ..constants import C, HOTKEYS, blend

if TYPE_CHECKING:
    pass

# Mode definitions: (id, label, active_color, dim_color, hotkey)
_MODES: list[tuple[int, str, str, str, str]] = [
    (1, '[ 1 ]  Auto Detect', C['yellow'], C['yellow_dim'], HOTKEYS['mode1']),
    (2, '[ 2 ]  Auto E',      C['blue'],   C['blue_dim'],   HOTKEYS['mode2']),
    (3, '[ 3 ]  Macro',       C['green'],  C['green_dim'],  HOTKEYS['mode3']),
    (4, '[ 4 ]  Route Auto',  C['purple'], C['purple_dim'], HOTKEYS.get('mode4', 'ctrl+F6')),
]


class ControlPanel(ctk.CTkFrame):
    """Left sidebar panel containing mode buttons, capture, settings, and stop.

    Args:
        parent: Parent widget.
        on_mode_select: ``callback(mode_id)`` when a mode button is clicked.
        on_stop: Called when STOP is pressed.
        on_settings: Called when SETTINGS is pressed.
        on_capture: Called when CAPTURE is pressed.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        on_mode_select: Callable[[int], None],
        on_stop: Callable[[], None],
        on_settings: Callable[[], None],
        on_capture: Callable[[], None],
    ) -> None:
        super().__init__(
            parent, fg_color=C['bg_card'], width=210,
            corner_radius=12, border_width=1, border_color=C['border'],
        )
        self.pack_propagate(False)

        self._on_mode_select = on_mode_select
        self._on_stop = on_stop
        self._on_settings = on_settings
        self._on_capture = on_capture

        # (mode_id, button_widget, active_color, dim_color)
        self.mode_btns: list[tuple[int, ctk.CTkButton, str, str]] = []

        self._build()

    # ── Construction ─────────────────────────────────────────

    def _build(self) -> None:
        inner = ctk.CTkFrame(self, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=10, pady=10)

        # Section header
        ctk.CTkLabel(
            inner, text='CHE DO',
            font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
            text_color=C['text_sec'],
        ).pack(anchor='w', pady=(0, 6))

        # ── Mode buttons with hotkey hints ───────────────────
        for mid, title, color, dim, hotkey in _MODES:
            row = ctk.CTkFrame(inner, fg_color='transparent')
            row.pack(fill='x', pady=2)

            btn = ctk.CTkButton(
                row, text=title,
                font=ctk.CTkFont(family='Segoe UI', size=11),
                text_color=C['text'], fg_color=C['bg_input'],
                hover_color=dim, border_width=1, border_color=C['border'],
                corner_radius=8, height=36, anchor='w',
                command=lambda m=mid: self._on_mode_select(m),
            )
            btn.pack(side='left', fill='x', expand=True)

            # Hotkey hint badge
            ctk.CTkLabel(
                row, text=hotkey,
                font=ctk.CTkFont(family='Consolas', size=9, weight='bold'),
                text_color=C['text_dim'],
                fg_color=C['bg_input'], corner_radius=4,
                width=28, height=20,
            ).pack(side='right', padx=(4, 0))

            self.mode_btns.append((mid, btn, color, dim))

        # ── Spacer ───────────────────────────────────────────
        ctk.CTkFrame(inner, fg_color='transparent').pack(fill='both', expand=True)

        # ── CAPTURE button ───────────────────────────────────
        capture_row = ctk.CTkFrame(inner, fg_color='transparent')
        capture_row.pack(fill='x', pady=(0, 4))

        ctk.CTkButton(
            capture_row, text='📷 CAPTURE',
            font=ctk.CTkFont(family='Segoe UI', size=11, weight='bold'),
            fg_color=C['purple_dim'], hover_color=C['purple'],
            text_color=C['purple'], border_width=1,
            border_color=C['purple'],
            height=32, corner_radius=8,
            command=self._on_capture,
        ).pack(side='left', fill='x', expand=True)

        ctk.CTkLabel(
            capture_row, text=HOTKEYS['capture'],
            font=ctk.CTkFont(family='Consolas', size=8),
            text_color=C['text_dim'],
            fg_color=C['bg_input'], corner_radius=4,
            width=48, height=20,
        ).pack(side='right', padx=(4, 0))

        # ── SETTINGS button ─────────────────────────────────
        ctk.CTkButton(
            inner, text='⚙  CAI DAT',
            font=ctk.CTkFont(size=11), fg_color='transparent',
            hover_color=C['bg_hover'], text_color=C['text_dim'],
            height=30, corner_radius=8, border_width=1,
            border_color=C['border'],
            command=self._on_settings,
        ).pack(fill='x', pady=(0, 4))

        # ── STOP button ─────────────────────────────────────
        stop_row = ctk.CTkFrame(inner, fg_color='transparent')
        stop_row.pack(fill='x')

        self.stop_btn = ctk.CTkButton(
            stop_row, text='■  TAT AUTO',
            font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
            fg_color=C['red'], hover_color=blend(C['red'], 0.7),
            text_color=C['white'], height=38, corner_radius=8,
            command=self._on_stop,
        )
        self.stop_btn.pack(side='left', fill='x', expand=True)

        ctk.CTkLabel(
            stop_row, text=HOTKEYS['stop'],
            font=ctk.CTkFont(family='Consolas', size=9, weight='bold'),
            text_color=C['text_dim'],
            fg_color=C['bg_input'], corner_radius=4,
            width=28, height=20,
        ).pack(side='right', padx=(4, 0))

    # ── Public API ───────────────────────────────────────────

    def highlight_mode(self, mode_id: int) -> None:
        """Highlight the active mode button and reset others."""
        for mid, btn, color, dim in self.mode_btns:
            if mid == mode_id:
                btn.configure(fg_color=dim, border_color=color)
            else:
                btn.configure(fg_color=C['bg_input'], border_color=C['border'])

    def clear_highlight(self) -> None:
        """Reset all mode buttons to default style."""
        for _, btn, _, _ in self.mode_btns:
            btn.configure(fg_color=C['bg_input'], border_color=C['border'])
