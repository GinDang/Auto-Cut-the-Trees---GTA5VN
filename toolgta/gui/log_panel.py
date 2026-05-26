"""AUTO GTA5VN v5.0 — Log Panel Widget

Right sidebar with scrollable log textbox and a log handler that
forwards ``logging.Logger`` records to the textbox.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk

from ..constants import C

if TYPE_CHECKING:
    pass


class LogPanel(ctk.CTkFrame):
    """Scrollable log panel with header, clear button, and auto-scroll.

    Args:
        parent: Parent widget.
        initial_info: Multi-line string to display on startup.
    """

    _MAX_LINES: int = 200
    _TRIM_LINES: int = 50

    def __init__(self, parent: ctk.CTkFrame, initial_info: str = '') -> None:
        super().__init__(
            parent, fg_color=C['bg_card'], width=290,
            corner_radius=12, border_width=1, border_color=C['border'],
        )
        self.pack_propagate(False)

        self._build()

        # Insert initial system info
        if initial_info:
            for line in initial_info.split('\n'):
                self.log(line)

        self.setup_log_handler()

    # ── Construction ─────────────────────────────────────────

    def _build(self) -> None:
        inner = ctk.CTkFrame(self, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=10, pady=10)

        # Header row
        hdr = ctk.CTkFrame(inner, fg_color='transparent')
        hdr.pack(fill='x', pady=(0, 6))

        ctk.CTkLabel(
            hdr, text='📋 LOG',
            font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
            text_color=C['text_sec'],
        ).pack(side='left')

        ctk.CTkButton(
            hdr, text='Xoa', font=ctk.CTkFont(size=9),
            fg_color='transparent', hover_color=C['bg_hover'],
            text_color=C['text_dim'], width=32, height=20,
            corner_radius=4, command=self.clear,
        ).pack(side='right')

        # Log textbox
        self.log_box = ctk.CTkTextbox(
            inner, font=ctk.CTkFont(family='Consolas', size=10),
            fg_color=C['bg'], text_color=C['text_dim'],
            border_width=1, border_color=C['border'],
            corner_radius=8, wrap='word', state='disabled',
        )
        self.log_box.pack(fill='both', expand=True)

    # ── Public API ───────────────────────────────────────────

    def log(self, msg: str) -> None:
        """Append a message to the log and auto-scroll to bottom.

        Automatically trims old lines when the buffer exceeds
        :attr:`_MAX_LINES`.
        """
        try:
            self.log_box.configure(state='normal')
            self.log_box.insert('end', msg + '\n')
            self.log_box.see('end')
            lines = int(self.log_box.index('end-1c').split('.')[0])
            if lines > self._MAX_LINES:
                self.log_box.delete('1.0', f'{self._TRIM_LINES}.0')
            self.log_box.configure(state='disabled')
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all log contents."""
        self.log_box.configure(state='normal')
        self.log_box.delete('1.0', 'end')
        self.log_box.configure(state='disabled')

    def setup_log_handler(self) -> None:
        """Attach a logging handler that forwards records to this panel.

        Records from the ``AutoGTA`` logger at INFO level and above
        are formatted and displayed in the log textbox.
        """
        panel = self

        class _TkLogHandler(logging.Handler):
            """Bridges the logging framework to the CTk textbox."""

            def __init__(self) -> None:
                super().__init__()

            def emit(self, record: logging.LogRecord) -> None:
                try:
                    msg = self.format(record)
                    panel.after(0, lambda m=msg: panel.log(m))
                except Exception:
                    pass

        handler = _TkLogHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
        )
        logging.getLogger('AutoGTA').addHandler(handler)
