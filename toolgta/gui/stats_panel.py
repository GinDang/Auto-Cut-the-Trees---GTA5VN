"""AUTO GTA5VN v5.0 — Stats Panel Widget

Center panel showing E/F/Y counters, inventory progress bar,
and a premium session statistics card.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from ..constants import C

if TYPE_CHECKING:
    pass


class StatsPanel(ctk.CTkFrame):
    """Combined stats display: counters, inventory bar, and session metrics.

    Layout::

        Row 1:  [  E: 12  ] [  F: 5  ] [  Y: 8  ]
        Row 2:  BALO ■■■■■■■░░░ 28/30 go
        Row 3:  THONG KE PHIEN
                ⏱ 00:12:34   FPS 18.5   Conf 0.62
                ⚡ Det: 12.3ms   🌳 28/30 go
                ⚠ Balo day: 1   ⏸ Pause: 3

    Args:
        parent: Parent widget.
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, fg_color='transparent')
        self.cnt_lbls: dict[str, ctk.CTkLabel] = {}
        self._build()

    # ── Construction ─────────────────────────────────────────

    def _build(self) -> None:
        self._build_counters()
        self._build_inventory()
        self._build_session_stats()

    def _build_counters(self) -> None:
        """Row 1 — E / F / Y counter cards."""
        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.pack(fill='x', pady=(0, 6))
        frame.grid_columnconfigure((0, 1, 2), weight=1, uniform='c')

        cfgs = [
            ('E', C['yellow']),
            ('F', C['blue']),
            ('Y', C['green']),
        ]
        for col, (key, color) in enumerate(cfgs):
            card = ctk.CTkFrame(
                frame, fg_color=C['bg_card'], corner_radius=10,
                border_width=1, border_color=C['border'],
            )
            card.grid(row=0, column=col, padx=3, sticky='nsew')

            row = ctk.CTkFrame(card, fg_color='transparent')
            row.pack(pady=10, padx=14)

            ctk.CTkLabel(
                row, text=key,
                font=ctk.CTkFont(family='Segoe UI', size=13, weight='bold'),
                text_color=color,
            ).pack(side='left', padx=(0, 10))

            lbl = ctk.CTkLabel(
                row, text='0',
                font=ctk.CTkFont(family='Consolas', size=22, weight='bold'),
                text_color=C['white'],
            )
            lbl.pack(side='left')
            self.cnt_lbls[key.lower()] = lbl

    def _build_inventory(self) -> None:
        """Row 2 — Inventory / balo progress bar."""
        self.inv_card = ctk.CTkFrame(
            self, fg_color=C['bg_card'], corner_radius=10,
            border_width=1, border_color=C['border'],
        )
        self.inv_card.pack(fill='x', pady=(0, 6))

        inner = ctk.CTkFrame(self.inv_card, fg_color='transparent')
        inner.pack(fill='x', padx=14, pady=10)

        top = ctk.CTkFrame(inner, fg_color='transparent')
        top.pack(fill='x')

        ctk.CTkLabel(
            top, text='🎒 BALO',
            font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
            text_color=C['text'],
        ).pack(side='left')

        self.wood_lbl = ctk.CTkLabel(
            top, text='0 / 30 go',
            font=ctk.CTkFont(family='Consolas', size=11, weight='bold'),
            text_color=C['text_sec'],
        )
        self.wood_lbl.pack(side='right')

        self.inv_status_lbl = ctk.CTkLabel(
            top, text='',
            font=ctk.CTkFont(size=10),
            text_color=C['text_dim'],
        )
        self.inv_status_lbl.pack(side='right', padx=(0, 10))

        self.wood_prog = ctk.CTkProgressBar(
            inner, height=6, corner_radius=3,
            fg_color=C['bg_input'], progress_color=C['green'],
        )
        self.wood_prog.pack(fill='x', pady=(6, 0))
        self.wood_prog.set(0)

    def _build_session_stats(self) -> None:
        """Row 3 — Premium session statistics card."""
        card = ctk.CTkFrame(
            self, fg_color=C['bg_card'], corner_radius=10,
            border_width=1, border_color=C['border'],
        )
        card.pack(fill='x', pady=(0, 6))

        inner = ctk.CTkFrame(card, fg_color='transparent')
        inner.pack(fill='x', padx=14, pady=10)

        # Header
        hdr = ctk.CTkFrame(inner, fg_color='transparent')
        hdr.pack(fill='x', pady=(0, 6))
        ctk.CTkLabel(
            hdr, text='📊 THONG KE PHIEN',
            font=ctk.CTkFont(family='Segoe UI', size=11, weight='bold'),
            text_color=C['text_sec'],
        ).pack(side='left')

        # Row A: elapsed, FPS, confidence
        row_a = ctk.CTkFrame(inner, fg_color='transparent')
        row_a.pack(fill='x', pady=(0, 3))

        self._elapsed_lbl = self._stat_label(row_a, '⏱', '00:00:00', C['blue'])
        self._avg_fps_lbl = self._stat_label(row_a, 'FPS', '--', C['green'])
        self._avg_conf_lbl = self._stat_label(row_a, 'Conf', '--', C['yellow'])

        # Row B: detection ms, total wood
        row_b = ctk.CTkFrame(inner, fg_color='transparent')
        row_b.pack(fill='x', pady=(0, 3))

        self._det_ms_lbl = self._stat_label(row_b, '⚡ Det', '--ms', C['purple'])
        self._total_wood_lbl = self._stat_label(row_b, '🌳', '--/-- go', C['green'])

        # Row C: balo full count, pause count
        row_c = ctk.CTkFrame(inner, fg_color='transparent')
        row_c.pack(fill='x')

        self._full_count_lbl = self._stat_label(row_c, '⚠ Balo day', '0', C['orange'])
        self._pause_count_lbl = self._stat_label(row_c, '⏸ Pause', '0', C['text_sec'])

    @staticmethod
    def _stat_label(
        parent: ctk.CTkFrame,
        prefix: str,
        initial: str,
        color: str,
    ) -> ctk.CTkLabel:
        """Create a compact stat indicator with icon/prefix and value."""
        grp = ctk.CTkFrame(parent, fg_color='transparent')
        grp.pack(side='left', padx=(0, 16))

        ctk.CTkLabel(
            grp, text=prefix,
            font=ctk.CTkFont(family='Segoe UI', size=10),
            text_color=C['text_dim'],
        ).pack(side='left', padx=(0, 4))

        lbl = ctk.CTkLabel(
            grp, text=initial,
            font=ctk.CTkFont(family='Consolas', size=10, weight='bold'),
            text_color=color,
        )
        lbl.pack(side='left')
        return lbl

    # ── Public API ───────────────────────────────────────────

    def update_counters(self, data: dict[str, int]) -> None:
        """Update E/F/Y counter labels.

        Args:
            data: Dict like ``{'e': 12, 'f': 5, 'y': 8}``.
        """
        for k in ('e', 'f', 'y'):
            if k in data:
                self.cnt_lbls[k].configure(text=str(data[k]))

    def update_wood(self, count: int, max_count: int) -> None:
        """Update inventory progress bar and label."""
        ratio = min(count / max(max_count, 1), 1.0)
        self.wood_lbl.configure(text=f'{count} / {max_count} go')
        self.wood_prog.set(ratio)

        if ratio >= 1.0:
            self.wood_prog.configure(progress_color=C['red'])
            self.inv_status_lbl.configure(text='! Day!', text_color=C['red'])
        elif ratio >= 0.8:
            self.wood_prog.configure(progress_color=C['orange'])
            self.inv_status_lbl.configure(text='Sap day', text_color=C['orange'])
        else:
            self.wood_prog.configure(progress_color=C['green'])
            self.inv_status_lbl.configure(text='', text_color=C['text_dim'])

    def update_session_stats(self, stats: dict) -> None:
        """Update the session statistics card.

        Expected keys in *stats*:
            - ``elapsed_str``: formatted HH:MM:SS
            - ``avg_fps``: float
            - ``avg_confidence``: float
            - ``avg_detection_ms``: float
            - ``total_wood``: int
            - ``max_wood``: int
            - ``full_count``: int  (number of times inventory was full)
            - ``pause_count``: int
        """
        self._elapsed_lbl.configure(text=stats.get('elapsed_str', '00:00:00'))
        avg_fps = stats.get('avg_fps', 0)
        self._avg_fps_lbl.configure(text=f'{avg_fps:.1f}' if avg_fps else '--')
        avg_conf = stats.get('avg_confidence', 0)
        self._avg_conf_lbl.configure(text=f'{avg_conf:.2f}' if avg_conf else '--')
        det_ms = stats.get('avg_detection_ms', 0)
        self._det_ms_lbl.configure(text=f'{det_ms:.1f}ms' if det_ms else '--ms')

        tw = stats.get('total_wood', 0)
        mw = stats.get('max_wood', 30)
        self._total_wood_lbl.configure(text=f'{tw}/{mw} go')

        self._full_count_lbl.configure(text=str(stats.get('full_count', 0)))
        self._pause_count_lbl.configure(text=str(stats.get('pause_count', 0)))

    def reset(self) -> None:
        """Reset all counters and stats to defaults."""
        for lbl in self.cnt_lbls.values():
            lbl.configure(text='0')
        self.update_wood(0, 30)
        self._elapsed_lbl.configure(text='00:00:00')
        self._avg_fps_lbl.configure(text='--')
        self._avg_conf_lbl.configure(text='--')
        self._det_ms_lbl.configure(text='--ms')
        self._total_wood_lbl.configure(text='--/-- go')
        self._full_count_lbl.configure(text='0')
        self._pause_count_lbl.configure(text='0')
