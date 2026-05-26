"""AUTO GTA5VN v5.0 — Notification Bar Widget

Orange-themed alert bar that appears when the inventory is full.
Provides "Continue" and "Stop" action buttons.
"""
from __future__ import annotations

from typing import Callable, TYPE_CHECKING

import customtkinter as ctk

from ..constants import C, blend

if TYPE_CHECKING:
    pass


class NotificationBar(ctk.CTkFrame):
    """Collapsible notification bar for inventory-full alerts.

    Starts hidden.  Call :meth:`show` to display with a message and
    :meth:`hide` to dismiss.

    Args:
        parent: Parent widget (the center column frame).
        on_continue: Callback when user clicks "Tiep tuc" (continue).
        on_stop: Callback when user clicks "Dung" (stop).
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        on_continue: Callable[[], None],
        on_stop: Callable[[], None],
    ) -> None:
        super().__init__(
            parent, fg_color=C['orange_dim'],
            corner_radius=10, border_width=1, border_color=C['orange'],
        )
        self._parent = parent
        self._on_continue = on_continue
        self._on_stop = on_stop
        self._visible: bool = False

        self._build()

    # ── Construction ─────────────────────────────────────────

    def _build(self) -> None:
        inner = ctk.CTkFrame(self, fg_color='transparent')
        inner.pack(fill='x', padx=12, pady=8)

        top = ctk.CTkFrame(inner, fg_color='transparent')
        top.pack(fill='x')

        # Alert icon + title
        self._title_lbl = ctk.CTkLabel(
            top, text='⚠ Balo day!',
            font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
            text_color=C['orange'],
        )
        self._title_lbl.pack(side='left')

        # Action buttons
        btn_row = ctk.CTkFrame(top, fg_color='transparent')
        btn_row.pack(side='right')

        ctk.CTkButton(
            btn_row, text='▶ Tiep tuc',
            font=ctk.CTkFont(size=10, weight='bold'),
            fg_color=C['green'], hover_color=blend(C['green'], 0.7),
            text_color=C['bg'], corner_radius=6, height=26, width=90,
            command=self._on_continue,
        ).pack(side='left', padx=(0, 4))

        ctk.CTkButton(
            btn_row, text='■ Dung',
            font=ctk.CTkFont(size=10, weight='bold'),
            fg_color=C['red'], hover_color=blend(C['red'], 0.7),
            text_color=C['white'], corner_radius=6, height=26, width=70,
            command=self._on_stop,
        ).pack(side='left')

        # Description text
        self._desc_lbl = ctk.CTkLabel(
            inner, text='',
            font=ctk.CTkFont(size=10),
            text_color=C['text_sec'], wraplength=400,
        )
        self._desc_lbl.pack(anchor='w', pady=(4, 0))

    # ── Public API ───────────────────────────────────────────

    def show(self, title: str, description: str) -> None:
        """Display the notification bar with the given title and description."""
        if self._visible:
            return
        self._title_lbl.configure(text=title)
        self._desc_lbl.configure(text=description)
        self.pack(fill='x', pady=(0, 6))
        self._visible = True

    def hide(self) -> None:
        """Hide the notification bar."""
        if self._visible:
            self.pack_forget()
            self._visible = False

    @property
    def is_visible(self) -> bool:
        """Whether the notification bar is currently shown."""
        return self._visible
