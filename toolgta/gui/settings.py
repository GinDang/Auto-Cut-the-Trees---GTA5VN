"""AUTO GTA5VN v5.0 — Settings Drawer Widget

Slide-out settings panel with sliders, toggles, region entries,
route settings, and a save button.  Includes v5.0 + v5.0 options.
"""
from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

import customtkinter as ctk

from ..constants import C, blend

if TYPE_CHECKING:
    pass


class SettingsDrawer(ctk.CTkFrame):
    """Expandable settings drawer that slides in from the bottom.

    Sections:
        - Row 1: Sliders — Confidence, Macro ms, Balo max, Check frames
        - Row 2: Toggles — Continue-when-full, region entries
        - Row 3: New v4.0 toggles — Humanize, ROI, Adaptive, GPU, Sound, Multi-scale
        - Row 4: Game keywords + Save button

    Args:
        parent: Root application window.
        config: Current configuration dict.
        on_save: ``callback(config)`` when Save is pressed.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        config: dict[str, Any],
        on_save: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(
            parent, fg_color=C['bg_card'],
            corner_radius=0, border_width=1, border_color=C['border'],
        )
        self._config = config
        self._on_save = on_save
        self._visible: bool = False

        # Widget references populated by _build
        self.conf_slider: ctk.CTkSlider | None = None
        self.macro_slider: ctk.CTkSlider | None = None
        self.wood_slider: ctk.CTkSlider | None = None
        self.inv_slider: ctk.CTkSlider | None = None
        self.full_toggle: ctk.CTkSwitch | None = None
        self.region_entries: dict[tuple[str, str], ctk.CTkEntry] = {}
        self.kw_entry: ctk.CTkEntry | None = None

        # New v4.0 toggles
        self._toggles: dict[str, ctk.CTkSwitch] = {}

        self._build()

    # ── Construction ─────────────────────────────────────────

    def _build(self) -> None:
        inner = ctk.CTkFrame(self, fg_color='transparent')
        inner.pack(fill='x', padx=14, pady=10)

        self._build_sliders(inner)
        self._build_toggles_row(inner)
        self._build_new_toggles(inner)
        self._build_footer(inner)

    def _build_sliders(self, parent: ctk.CTkFrame) -> None:
        """Row 1 — Four adjustment sliders."""
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', pady=(0, 8))
        row.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform='s')

        self.conf_slider, self._conf_val = self._make_slider(
            row, 0, 'Confidence', 0.30, 0.90, 60,
            self._config['confidence_threshold'], C['yellow'],
            self._on_conf,
        )
        self.macro_slider, self._macro_val = self._make_slider(
            row, 1, 'Macro (ms)', 5, 200, 39,
            self._config['macro_delay_ms'], C['blue'],
            self._on_macro, fmt=lambda v: f'{int(v)}',
        )
        self.wood_slider, self._wood_val = self._make_slider(
            row, 2, 'Balo max', 5, 100, 19,
            self._config['max_wood_capacity'], C['green'],
            self._on_wood_cap, fmt=lambda v: f'{int(v)}',
        )
        self.inv_slider, self._inv_val = self._make_slider(
            row, 3, 'Check (frames)', 10, 300, 29,
            self._config['inventory_check_interval'], C['purple'],
            self._on_inv_interval, fmt=lambda v: f'{int(v)}',
        )

    def _build_toggles_row(self, parent: ctk.CTkFrame) -> None:
        """Row 2 — Continue-when-full toggle + region entries."""
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', pady=(0, 6))

        # Continue when full toggle
        tog = ctk.CTkFrame(row, fg_color='transparent')
        tog.pack(side='left', padx=(0, 16))
        ctk.CTkLabel(
            tog, text='Tiep tuc khi day',
            font=ctk.CTkFont(size=10), text_color=C['text_sec'],
        ).pack(side='left', padx=(0, 6))
        self.full_toggle = ctk.CTkSwitch(
            tog, text='', width=40, height=20,
            fg_color=C['border'], progress_color=C['green'],
            button_color=C['white'], button_hover_color=C['text'],
            command=self._on_full_toggle,
        )
        if self._config.get('continue_when_full', False):
            self.full_toggle.select()
        self.full_toggle.pack(side='left')

        # Region entries
        for rkey, rlabel in [('detect_region', 'Detect'), ('notification_region', 'Notif')]:
            grp = ctk.CTkFrame(row, fg_color='transparent')
            grp.pack(side='left', padx=(0, 10))
            ctk.CTkLabel(
                grp, text=f'{rlabel}:',
                font=ctk.CTkFont(size=9), text_color=C['text_dim'],
            ).pack(side='left', padx=(0, 3))

            for fk, fl in [('top_pct', 'T'), ('left_pct', 'L'),
                           ('width_pct', 'W'), ('height_pct', 'H')]:
                ctk.CTkLabel(
                    grp, text=fl,
                    font=ctk.CTkFont(size=8), text_color=C['text_dim'],
                ).pack(side='left')
                ent = ctk.CTkEntry(
                    grp, font=ctk.CTkFont(family='Consolas', size=9),
                    fg_color=C['bg_input'], border_color=C['border'],
                    text_color=C['text'], height=22, width=48, corner_radius=4,
                )
                ent.insert(0, f'{self._config[rkey][fk]:.3f}')
                ent.pack(side='left', padx=(0, 2))
                self.region_entries[(rkey, fk)] = ent

    def _build_new_toggles(self, parent: ctk.CTkFrame) -> None:
        """Row 3 — New v4.0 feature toggles."""
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', pady=(0, 6))

        toggle_defs: list[tuple[str, str, str, bool]] = [
            ('humanize_keys',       'Humanize keys',       C['blue'],   False),
            ('roi_tracking',        'ROI Tracking',        C['green'],  False),
            ('adaptive_confidence', 'Adaptive Confidence', C['yellow'], False),
            ('gpu_acceleration',    'GPU Accel',           C['purple'], False),
            ('sound_alert',         'Sound Alert',         C['orange'], True),
            ('multi_scale',         'Multi-scale',         C['blue'],   False),
        ]

        for cfg_key, label, color, default in toggle_defs:
            grp = ctk.CTkFrame(row, fg_color='transparent')
            grp.pack(side='left', padx=(0, 12))
            ctk.CTkLabel(
                grp, text=label,
                font=ctk.CTkFont(size=9), text_color=C['text_dim'],
            ).pack(side='left', padx=(0, 4))
            switch = ctk.CTkSwitch(
                grp, text='', width=36, height=18,
                fg_color=C['border'], progress_color=color,
                button_color=C['white'], button_hover_color=C['text'],
            )
            if self._config.get(cfg_key, default):
                switch.select()
            switch.pack(side='left')
            self._toggles[cfg_key] = switch

        # Row 3b — v5.0 Route toggles
        row5 = ctk.CTkFrame(parent, fg_color='transparent')
        row5.pack(fill='x', pady=(0, 6))

        route_toggles: list[tuple[str, str, str, bool]] = [
            ('gps_navigation',  'GPS Nav',          C['purple'], True),
            ('self_correction',  'Self-correct',    C['green'],  True),
            ('route_loop',       'Route Loop',      C['blue'],   True),
        ]

        for cfg_key, label, color, default in route_toggles:
            grp = ctk.CTkFrame(row5, fg_color='transparent')
            grp.pack(side='left', padx=(0, 12))
            ctk.CTkLabel(
                grp, text=label,
                font=ctk.CTkFont(size=9), text_color=C['text_dim'],
            ).pack(side='left', padx=(0, 4))
            switch = ctk.CTkSwitch(
                grp, text='', width=36, height=18,
                fg_color=C['border'], progress_color=color,
                button_color=C['white'], button_hover_color=C['text'],
            )
            if self._config.get(cfg_key, default):
                switch.select()
            switch.pack(side='left')
            self._toggles[cfg_key] = switch

        # Mouse sensitivity slider in v5.0 row
        sens_grp = ctk.CTkFrame(row5, fg_color='transparent')
        sens_grp.pack(side='left', padx=(12, 0))
        ctk.CTkLabel(
            sens_grp, text='Mouse sens',
            font=ctk.CTkFont(size=9), text_color=C['text_dim'],
        ).pack(side='left', padx=(0, 4))
        self._sens_val = ctk.CTkLabel(
            sens_grp,
            text=f"{self._config.get('mouse_sensitivity', 2.5):.1f}",
            font=ctk.CTkFont(family='Consolas', size=9, weight='bold'),
            text_color=C['purple'],
        )
        self._sens_val.pack(side='left', padx=(0, 4))
        self._sens_slider = ctk.CTkSlider(
            sens_grp, from_=0.5, to=8.0, number_of_steps=15,
            progress_color=C['purple'], button_color=C['white'],
            button_hover_color=C['purple'], fg_color=C['bg_input'],
            height=14, width=80,
            command=lambda v: (
                self._sens_val.configure(text=f'{v:.1f}'),
                self._config.update({'mouse_sensitivity': v}),
            ),
        )
        self._sens_slider.set(self._config.get('mouse_sensitivity', 2.5))
        self._sens_slider.pack(side='left')

        # Route speed slider
        spd_grp = ctk.CTkFrame(row5, fg_color='transparent')
        spd_grp.pack(side='left', padx=(12, 0))
        ctk.CTkLabel(
            spd_grp, text='Speed',
            font=ctk.CTkFont(size=9), text_color=C['text_dim'],
        ).pack(side='left', padx=(0, 4))
        self._spd_val = ctk.CTkLabel(
            spd_grp,
            text=f"{self._config.get('route_speed', 1.0):.1f}x",
            font=ctk.CTkFont(family='Consolas', size=9, weight='bold'),
            text_color=C['blue'],
        )
        self._spd_val.pack(side='left', padx=(0, 4))
        self._spd_slider = ctk.CTkSlider(
            spd_grp, from_=0.5, to=3.0, number_of_steps=10,
            progress_color=C['blue'], button_color=C['white'],
            button_hover_color=C['blue'], fg_color=C['bg_input'],
            height=14, width=70,
            command=lambda v: (
                self._spd_val.configure(text=f'{v:.1f}x'),
                self._config.update({'route_speed': v}),
            ),
        )
        self._spd_slider.set(self._config.get('route_speed', 1.0))
        self._spd_slider.pack(side='left')

        # Cutting timeout slider
        cut_grp = ctk.CTkFrame(row5, fg_color='transparent')
        cut_grp.pack(side='left', padx=(12, 0))
        ctk.CTkLabel(
            cut_grp, text='Cut(s)',
            font=ctk.CTkFont(size=9), text_color=C['text_dim'],
        ).pack(side='left', padx=(0, 4))
        self._cut_val = ctk.CTkLabel(
            cut_grp,
            text=f"{int(self._config.get('cutting_timeout', 30))}",
            font=ctk.CTkFont(family='Consolas', size=9, weight='bold'),
            text_color=C['orange'],
        )
        self._cut_val.pack(side='left', padx=(0, 4))
        self._cut_slider = ctk.CTkSlider(
            cut_grp, from_=10, to=90, number_of_steps=8,
            progress_color=C['orange'], button_color=C['white'],
            button_hover_color=C['orange'], fg_color=C['bg_input'],
            height=14, width=70,
            command=lambda v: (
                self._cut_val.configure(text=f'{int(v)}'),
                self._config.update({'cutting_timeout': int(v)}),
            ),
        )
        self._cut_slider.set(self._config.get('cutting_timeout', 30))
        self._cut_slider.pack(side='left')

    def _build_footer(self, parent: ctk.CTkFrame) -> None:
        """Row 4 — Game keywords entry + Save button."""
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x')

        kw_grp = ctk.CTkFrame(row, fg_color='transparent')
        kw_grp.pack(side='left', padx=(0, 8))
        ctk.CTkLabel(
            kw_grp, text='Game:',
            font=ctk.CTkFont(size=9), text_color=C['text_dim'],
        ).pack(side='left', padx=(0, 3))
        self.kw_entry = ctk.CTkEntry(
            kw_grp, font=ctk.CTkFont(family='Consolas', size=9),
            fg_color=C['bg_input'], border_color=C['border'],
            text_color=C['text'], height=22, width=140, corner_radius=4,
        )
        self.kw_entry.insert(
            0, ', '.join(self._config.get('game_window_keywords', []))
        )
        self.kw_entry.pack(side='left')

        ctk.CTkButton(
            row, text='💾 LUU',
            font=ctk.CTkFont(size=11, weight='bold'),
            fg_color=C['yellow'], hover_color=blend(C['yellow'], 0.7),
            text_color=C['bg'], height=28, width=80, corner_radius=6,
            command=self._do_save,
        ).pack(side='right')

    # ── Slider factory ───────────────────────────────────────

    def _make_slider(
        self,
        parent: ctk.CTkFrame,
        col: int,
        label: str,
        lo: float,
        hi: float,
        steps: int,
        init: float,
        color: str,
        cmd: Callable[[float], None],
        fmt: Callable[[float], str] | None = None,
    ) -> tuple[ctk.CTkSlider, ctk.CTkLabel]:
        """Create a labeled slider with live value display."""
        if fmt is None:
            fmt = lambda v: f'{v:.2f}'

        cell = ctk.CTkFrame(parent, fg_color='transparent')
        cell.grid(row=0, column=col, padx=4, sticky='ew')

        hdr = ctk.CTkFrame(cell, fg_color='transparent')
        hdr.pack(fill='x')
        ctk.CTkLabel(
            hdr, text=label,
            font=ctk.CTkFont(size=10), text_color=C['text_sec'],
        ).pack(side='left')

        val_lbl = ctk.CTkLabel(
            hdr, text=fmt(init),
            font=ctk.CTkFont(family='Consolas', size=10, weight='bold'),
            text_color=color,
        )
        val_lbl.pack(side='right')

        slider = ctk.CTkSlider(
            cell, from_=lo, to=hi, number_of_steps=steps,
            progress_color=color, button_color=C['white'],
            button_hover_color=color, fg_color=C['bg_input'], height=14,
            command=lambda v, vl=val_lbl, fn=fmt, cb=cmd: (
                vl.configure(text=fn(v)), cb(v)
            ),
        )
        slider.set(init)
        slider.pack(fill='x', pady=(2, 0))
        return slider, val_lbl

    # ── Internal callbacks ───────────────────────────────────

    def _on_conf(self, v: float) -> None:
        self._config['confidence_threshold'] = v

    def _on_macro(self, v: float) -> None:
        self._config['macro_delay_ms'] = int(v)

    def _on_wood_cap(self, v: float) -> None:
        self._config['max_wood_capacity'] = int(v)

    def _on_inv_interval(self, v: float) -> None:
        self._config['inventory_check_interval'] = int(v)

    def _on_full_toggle(self) -> None:
        self._config['continue_when_full'] = self.full_toggle.get() == 1

    def _do_save(self) -> None:
        """Collect all values and invoke the on_save callback."""
        config = self.get_config()
        self._on_save(config)

    # ── Public API ───────────────────────────────────────────

    def get_config(self) -> dict[str, Any]:
        """Collect all current setting values into a config dict."""
        cfg = self._config.copy()

        # Sliders
        cfg['confidence_threshold'] = self.conf_slider.get()
        cfg['macro_delay_ms'] = int(self.macro_slider.get())
        cfg['max_wood_capacity'] = int(self.wood_slider.get())
        cfg['inventory_check_interval'] = int(self.inv_slider.get())

        # Main toggle
        cfg['continue_when_full'] = self.full_toggle.get() == 1

        # Region entries
        for (rk, fk), ent in self.region_entries.items():
            try:
                v = float(ent.get())
                if 0 <= v <= 1:
                    cfg[rk][fk] = v
            except ValueError:
                pass

        # Game keywords
        kw = self.kw_entry.get().strip()
        if kw:
            cfg['game_window_keywords'] = [
                w.strip() for w in kw.split(',') if w.strip()
            ]

        # New v4.0 toggles
        for cfg_key, switch in self._toggles.items():
            cfg[cfg_key] = switch.get() == 1

        # v5.0 mouse sensitivity
        if hasattr(self, '_sens_slider'):
            cfg['mouse_sensitivity'] = self._sens_slider.get()
        if hasattr(self, '_spd_slider'):
            cfg['route_speed'] = round(self._spd_slider.get(), 1)
        if hasattr(self, '_cut_slider'):
            cfg['cutting_timeout'] = int(self._cut_slider.get())

        return cfg

    def toggle_visibility(self) -> None:
        """Toggle the settings drawer open/closed."""
        if self._visible:
            self.pack_forget()
            self._visible = False
        else:
            self.pack(fill='x', side='bottom')
            self._visible = True

    @property
    def is_visible(self) -> bool:
        """Whether the settings drawer is currently shown."""
        return self._visible
