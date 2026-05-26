"""AUTO GTA5VN v5.0 — Main Application Window

Assembles all GUI widget modules, registers global hotkeys,
manages the automation engine lifecycle, routes engine events
to widgets, and integrates v5.0 route system.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import customtkinter as ctk
import keyboard
import winsound

from ..constants import C, APP_NAME, APP_VERSION, HOTKEYS, blend
from ..config import load_config, save_config, validate_config
from ..utils import get_screen_resolution, setup_logger, emergency_release
from ..engine import AutoEngine
from ..template_manager import TemplateManager
from ..gpu_utils import GPUAccelerator
from ..capture import CaptureManager
from ..state_machine import StateMachine, GameState
from ..checkpoint import CheckpointVerifier
from ..mouse_control import MouseController
from ..route_recorder import RouteRecorder, Route
from ..route_player import RoutePlayer
from ..gps_navigator import GPSNavigator

from .topbar import TopBar
from .controls import ControlPanel
from .stats_panel import StatsPanel
from .log_panel import LogPanel
from .settings import SettingsDrawer
from .notification import NotificationBar
from .capture_dialog import CaptureDialog
from .route_panel import RoutePanel

logger = logging.getLogger('AutoGTA')

# Mode definitions: (id, active_color, dim_color)
_MODE_COLORS: dict[int, tuple[str, str]] = {
    1: (C['yellow'], C['yellow_dim']),
    2: (C['blue'], C['blue_dim']),
    3: (C['green'], C['green_dim']),
}


class AutoGTAApp(ctk.CTk):
    """Main application window for AUTO GTA5VN v5.0.

    Responsibilities:
        - Assembles TopBar, ControlPanel, StatsPanel, LogPanel,
          SettingsDrawer, NotificationBar, RoutePanel widgets
        - Initialises TemplateManager, AutoEngine, GPUAccelerator,
          CaptureManager, StateMachine, RouteRecorder/Player
        - Registers global hotkeys (F7–F12, Ctrl+F6–F9)
        - Routes engine + route callback events to widgets
        - Manages session stats polling and status dot pulse
    """

    def __init__(self) -> None:
        super().__init__()
        self.title(f'{APP_NAME} v{APP_VERSION}')
        self.geometry('1060x580')
        self.minsize(920, 480)
        self.configure(fg_color=C['bg'])
        self.resizable(True, True)
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')

        # ── Core objects ─────────────────────────────────────
        self.config: dict[str, Any] = load_config()
        self.gpu = GPUAccelerator()
        self.tmgr = TemplateManager(self.config)
        self.capture_mgr = CaptureManager(self.config)
        self.engine = AutoEngine(
            self.tmgr, self.config,
            ui_cb=self._on_event, gpu=self.gpu,
        )

        # ── v5.0 objects ─────────────────────────────────────
        self.fsm = StateMachine(ui_cb=self._on_event)
        self._mouse_ctrl = MouseController(
            sensitivity=self.config.get('mouse_sensitivity', 2.5)
        )
        self._cp_verifier = CheckpointVerifier(
            minimap_region=self.config.get('minimap_region'),
            threshold=self.config.get('checkpoint_threshold', 0.65),
        )
        self._recorder = RouteRecorder(self.config, self._cp_verifier)
        self._gps_nav = GPSNavigator(self.config, self._mouse_ctrl)
        self._player: RoutePlayer | None = None
        self._cutting_timer_id: str | None = None
        self._stuck_count: int = 0  # consecutive stuck events

        self._active_mode: int = 0

        # ── Build UI ─────────────────────────────────────────
        self._build()
        self._register_hotkeys()
        self.protocol('WM_DELETE_WINDOW', self._close)

        # ── Periodic tickers ─────────────────────────────────
        self._tick_pulse()
        self._tick_session_stats()

        # ── Initial info ─────────────────────────────────────
        sw, sh = get_screen_resolution()
        self.topbar.set_resolution(sw, sh)
        gpu_name = self.gpu.device_name if self.gpu.is_available else 'CPU'
        self.topbar.set_gpu(gpu_name)
        logger.info(
            'App ready — %dx%d | GPU: %s', sw, sh, gpu_name,
        )

    # ══════════════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════════════

    def _build(self) -> None:
        """Construct the full window layout."""
        # Top bar
        self.topbar = TopBar(self)

        # Body: three columns
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=8, pady=8)

        # Left — controls
        self.controls = ControlPanel(
            body,
            on_mode_select=self._select_mode,
            on_stop=self._stop,
            on_settings=self._toggle_settings,
            on_capture=self._open_capture,
        )
        self.controls.pack(side='left', fill='y', padx=(0, 6))

        # Center — stats + notification + route panel
        center = ctk.CTkFrame(body, fg_color='transparent')
        center.pack(side='left', fill='both', expand=True, padx=(0, 6))

        self.stats_panel = StatsPanel(center)
        self.stats_panel.pack(fill='both', expand=True, pady=(0, 6))

        self.notification = NotificationBar(
            center,
            on_continue=self._dismiss_continue,
            on_stop=self._dismiss_stop,
        )

        # Right — route panel + log
        right = ctk.CTkFrame(body, fg_color='transparent')
        right.pack(side='right', fill='y')

        self.route_panel = RoutePanel(
            right,
            on_record_start=self._route_record_start,
            on_record_stop=self._route_record_stop,
            on_play=self._route_play,
            on_play_stop=self._route_play_stop,
            on_mark_tree=self._route_mark_tree,
            on_mark_sell=self._route_mark_sell,
        )
        self.route_panel.pack(fill='both', expand=True, pady=(0, 6))

        self.log_panel = LogPanel(right, initial_info=self._get_sys_info())
        self.log_panel.pack(fill='both', expand=True)

        # Bottom — settings drawer (starts hidden)
        self.settings = SettingsDrawer(
            self, self.config, on_save=self._save_all,
        )

    # ══════════════════════════════════════════════════════════
    #  HOTKEYS
    # ══════════════════════════════════════════════════════════

    def _register_hotkeys(self) -> None:
        """Bind global keyboard shortcuts."""
        keyboard.add_hotkey(HOTKEYS['stop'], self._stop)
        keyboard.add_hotkey(HOTKEYS['mode1'], lambda: self._select_mode(1))
        keyboard.add_hotkey(HOTKEYS['mode2'], lambda: self._select_mode(2))
        keyboard.add_hotkey(HOTKEYS['mode3'], lambda: self._select_mode(3))
        keyboard.add_hotkey(HOTKEYS.get('mode4', 'ctrl+F6'), lambda: self._select_mode(4))
        keyboard.add_hotkey(HOTKEYS['pause'], self._toggle_pause)
        keyboard.add_hotkey(HOTKEYS['capture'], self._open_capture)
        keyboard.add_hotkey(HOTKEYS.get('mark_tree', 'ctrl+F8'), self._route_mark_tree)
        keyboard.add_hotkey(HOTKEYS.get('mark_sell', 'ctrl+F9'), self._route_mark_sell)

    # ══════════════════════════════════════════════════════════
    #  ENGINE EVENT ROUTING
    # ══════════════════════════════════════════════════════════

    def _on_event(self, evt: str, data: dict | None) -> None:
        """Thread-safe bridge from engine callbacks to the Tk main loop."""
        self.after(0, lambda: self._proc(evt, data))

    def _proc(self, evt: str, data: dict | None) -> None:
        """Route engine events to the appropriate widgets."""
        if data is None:
            return
        try:
            if evt == 'status':
                self.topbar.set_status(
                    data.get('text', ''),
                    data.get('state', 'stopped'),
                )
            elif evt == 'fps':
                self.topbar.set_fps(data['value'])
            elif evt == 'confidence':
                self.topbar.set_confidence(data['value'])
            elif evt == 'counter':
                self.stats_panel.update_counters(data)
            elif evt == 'wood':
                self.stats_panel.update_wood(
                    data.get('count', 0), data.get('max', 30),
                )
            elif evt == 'inventory_full':
                self._handle_inventory_full(data)
            # ── v5.0 route events ─────────────────────────
            elif evt == 'progress':
                self.route_panel.update_progress(
                    data.get('idx', 0), data.get('total', 0),
                    data.get('loop', 0), data.get('mode', 'main'),
                )
                # Also update topbar with route progress
                pct = 0
                total = data.get('total', 0)
                if total > 0:
                    pct = int(100 * data.get('idx', 0) / total)
                loop = data.get('loop', 0)
                mode_str = 'chính' if data.get('mode') == 'main' else 'bán'
                self.topbar.set_status(
                    f'Route {mode_str} — {pct}% — Loop #{loop}', 'running',
                )
            elif evt == 'tree_reached':
                self.route_panel.on_tree_reached(
                    data.get('idx', 0), data.get('total_trees', 0),
                )
                # Start E/F/Y detection for cutting, with auto-resume timer
                self.fsm.transition(GameState.CUTTING, reason='tree_reached')
                if not self.engine.running:
                    self.engine.start(1)
                # Auto-resume route after cutting timeout (configurable)
                cut_timeout = int(self.config.get('cutting_timeout', 30) * 1000)
                self._cutting_timer_id = self.after(
                    cut_timeout, self._resume_route_after_cut
                )
                self._stuck_count = 0
            elif evt == 'sell_reached':
                self.log_panel.log('[Route] Đến NPC bán gỗ')
            elif evt == 'sell_complete':
                self.log_panel.log('[Route] Bán xong — quay lại route')
                self.fsm.transition(GameState.NAVIGATING, reason='sell_done')
            elif evt == 'checkpoint':
                self.route_panel.on_checkpoint(
                    data.get('idx', 0), data.get('score', 0),
                )
            elif evt == 'stuck':
                self.route_panel.on_stuck()
                self._stuck_count += 1
                self.log_panel.log(f'[Route] ⚠ Bị kẹt (lần {self._stuck_count}) — đang sửa...')
                # Show notification after 3 consecutive stucks
                if self._stuck_count >= 3:
                    self.notification.show(
                        '⚠ Route bị kẹt liên tục!',
                        f'Đã kẹt {self._stuck_count} lần liên tiếp. Kiểm tra route hoặc dừng lại.',
                    )
            elif evt == 'playback_stopped':
                self.route_panel.on_playback_stopped()
            elif evt == 'state_change':
                self.log_panel.log(
                    f"[FSM] {data.get('prev', '')} → {data.get('state', '')} ({data.get('reason', '')})"
                )
        except Exception:
            pass

    def _handle_inventory_full(self, data: dict) -> None:
        """Process inventory-full event: sound + notification + auto-sell."""
        # Sound alert
        if self.config.get('sound_alert', True):
            try:
                for _ in range(3):
                    winsound.Beep(1000, 200)
            except Exception:
                pass

        # Build notification message
        estimated = data.get('estimated', False)
        method = data.get('method', '')
        score = data.get('score', 0)

        if estimated:
            msg = 'Uoc tinh balo day dua tren so lan chat.'
        elif method == 'color':
            msg = f'Phat hien thong bao hong (ty le: {score:.1%})'
        elif method == 'template':
            msg = f'Template match (score: {score:.2f})'
        else:
            msg = f'Phat hien (score: {score:.2f})'

        # v5.0: Auto-sell if route player is active and has sell route
        if (self._player and self._player.is_playing
                and self._player.route.sell_steps):
            self.engine.stop()  # Stop cutting engine
            self._player.switch_to_sell()
            self._player.resume()
            self.fsm.transition(GameState.SELLING, reason='inventory_full')
            self.log_panel.log('[Route] Balo đầy → tự đi bán gỗ')
            self.route_panel.update_progress(
                0, len(self._player.route.sell_steps), self._player.loop_count, 'sell'
            )
            return

        self.notification.show(
            '⚠ Tui do da day!',
            msg + ' — Ban go hoac xe go.',
        )

    # ══════════════════════════════════════════════════════════
    #  MODE CONTROL
    # ══════════════════════════════════════════════════════════

    def _select_mode(self, mode: int) -> None:
        """Start a mode (stop current if running)."""
        # Stop any running engine/route
        emergency_release()  # Release all held keys before switching
        if self.engine.running:
            self.engine.stop()
        if self._player and self._player.is_playing:
            self._player.stop()
        self._cancel_cutting_timer()
        self.notification.hide()

        if mode == 4:
            # Mode 4 is managed by Route Panel
            self._active_mode = 4
            self.controls.highlight_mode(4)
            self.fsm.transition(GameState.IDLE, reason='mode4_selected')
            self.topbar.set_status('Mode 4 — Chọn route rồi bấm Play', 'stopped')
            self.log_panel.log('[Sys] Mode 4 (Route Auto) — chọn route và bấm Play')
            return

        self.after(200, lambda: self._start_mode(mode))

    def _start_mode(self, mode: int) -> None:
        """Sync config and start the engine in the given mode."""
        self._sync_config_from_settings()
        self.engine.config = self.config
        if self.engine.start(mode):
            self._active_mode = mode
            self.controls.highlight_mode(mode)
            self.stats_panel.reset()

    def _stop(self) -> None:
        """Stop everything and reset UI."""
        self._cancel_cutting_timer()
        self.engine.stop()
        if self._player and self._player.is_playing:
            self._player.stop()
        self._active_mode = 0
        self.notification.hide()
        self.controls.clear_highlight()
        self.fsm.transition(GameState.IDLE, reason='user_stop')
        self.topbar.set_status('Da dung', 'stopped')
        self.topbar.set_fps(0)
        self.route_panel.on_playback_stopped()

        # Final session stats update
        stats = self.engine.get_session_stats()
        if stats:
            self._update_session_display(stats)

    def _toggle_pause(self) -> None:
        """Toggle pause on the running engine."""
        if self.engine.running:
            self.engine.paused = not self.engine.paused
            if self.engine.paused:
                self.topbar.set_status('Tam dung — F11 de tiep', 'paused')
            else:
                self.topbar.set_status(
                    f'Mode {self._active_mode} dang chay', 'running',
                )

    # ══════════════════════════════════════════════════════════
    #  NOTIFICATION ACTIONS
    # ══════════════════════════════════════════════════════════

    def _dismiss_continue(self) -> None:
        """Continue running after inventory-full alert."""
        self.notification.hide()
        self.engine.resume_from_full()

    def _dismiss_stop(self) -> None:
        """Stop after inventory-full alert."""
        self.notification.hide()
        self._stop()

    # ══════════════════════════════════════════════════════════
    #  ROUTE AUTO-RESUME (v5.0)
    # ══════════════════════════════════════════════════════════

    def _resume_route_after_cut(self) -> None:
        """Resume route playback after cutting timeout.

        Called by a timer set when a tree marker is reached.
        Stops the cutting engine and resumes route traversal.
        """
        if not self._player or not self._player.is_playing:
            return
        if self.fsm.state != GameState.CUTTING:
            return

        self.engine.stop()
        self._player.resume()
        self.fsm.transition(GameState.NAVIGATING, reason='cut_timeout')
        self.log_panel.log('[Route] Hết thời gian chặt → tiếp tục route')

    def _cancel_cutting_timer(self) -> None:
        """Cancel any pending cutting timeout timer."""
        if self._cutting_timer_id is not None:
            try:
                self.after_cancel(self._cutting_timer_id)
            except Exception:
                pass
            self._cutting_timer_id = None

    # ══════════════════════════════════════════════════════════
    #  CAPTURE
    # ══════════════════════════════════════════════════════════

    def _open_capture(self) -> None:
        """Open the template capture dialog."""
        CaptureDialog(
            self, self.capture_mgr, self.tmgr,
            on_complete=self._on_capture_complete,
        )

    def _on_capture_complete(self, key: str, filepath: str) -> None:
        """Handle a newly captured template."""
        basename = os.path.basename(filepath)
        self.log_panel.log(
            f'[Capture] Saved {key.upper()} template: {basename}',
        )
        # Reload templates
        self.tmgr = TemplateManager(self.config)
        self.engine.tmgr = self.tmgr
        logger.info('Templates reloaded after capture')

    # ══════════════════════════════════════════════════════════
    #  SETTINGS
    # ══════════════════════════════════════════════════════════

    def _toggle_settings(self) -> None:
        """Toggle the settings drawer visibility."""
        self.settings.toggle_visibility()

    def _sync_config_from_settings(self) -> None:
        """Pull current values from the settings drawer."""
        self.config = self.settings.get_config()

    def _save_all(self, config: dict[str, Any]) -> None:
        """Save configuration from the settings drawer."""
        try:
            errors = validate_config(config)
            if errors:
                for err in errors:
                    self.log_panel.log(f'[Err] Config: {err}')
                return

            self.config = config
            self.engine.config = config
            save_config(config)
            self.log_panel.log('[Sys] Cai dat da luu OK')
        except Exception as exc:
            self.log_panel.log(f'[Err] Luu that bai: {exc}')

    # ══════════════════════════════════════════════════════════
    #  PERIODIC TICKERS
    # ══════════════════════════════════════════════════════════

    def _tick_pulse(self) -> None:
        """Animate the status dot every ~550ms."""
        self.topbar.pulse(
            self.engine.running,
            self.engine.paused,
            getattr(self.engine, 'inventory_paused', False),
        )
        self.after(550, self._tick_pulse)

    def _tick_session_stats(self) -> None:
        """Poll session stats every ~2s while running."""
        if self.engine.running:
            stats = self.engine.get_session_stats()
            if stats:
                self._update_session_display(stats)
        self.after(2000, self._tick_session_stats)

    def _update_session_display(self, stats: dict) -> None:
        """Map engine session stats to widget display format."""
        display = {
            'elapsed_str': stats.get('elapsed', '00:00:00'),
            'avg_fps': stats.get('avg_fps', 0),
            'avg_confidence': stats.get('avg_confidence', 0),
            'avg_detection_ms': stats.get('avg_detection_ms', 0),
            'total_wood': stats.get('wood_estimate', 0),
            'max_wood': self.config.get('max_wood_capacity', 30),
            'full_count': stats.get('inventory_full_count', 0),
            'pause_count': stats.get('game_pause_count', 0),
        }
        self.stats_panel.update_session_stats(display)

    # ══════════════════════════════════════════════════════════
    #  ROUTE MANAGEMENT (v5.0)
    # ══════════════════════════════════════════════════════════

    def _route_record_start(self, route_name: str) -> None:
        """Start recording a route."""
        self._recorder.start_recording(route_name)
        self.fsm.transition(GameState.RECORDING, reason='user_record')
        self.log_panel.log(f'[Route] Bắt đầu ghi: {route_name}')

    def _route_record_stop(self) -> None:
        """Stop recording and save the route."""
        route = self._recorder.stop_recording()
        self.fsm.transition(GameState.IDLE, reason='record_done')
        if route:
            self.log_panel.log(
                f'[Route] Đã lưu: {route.name} ({len(route.steps)} bước, '
                f'{route.tree_count} cây, {route.total_duration:.0f}s)'
            )

    def _route_play(self, route_dir: str) -> None:
        """Load and start playing a route."""
        try:
            route = Route.load(route_dir)
            self._player = RoutePlayer(
                route, self._cp_verifier, self._mouse_ctrl,
                self.config, ui_cb=self._on_event,
            )
            self._player.start()
            self.fsm.transition(GameState.NAVIGATING, reason='route_play')
            self.log_panel.log(f'[Route] Bắt đầu chạy: {route.name}')
        except Exception as exc:
            self.log_panel.log(f'[Route] Lỗi load route: {exc}')

    def _route_play_stop(self) -> None:
        """Stop route playback."""
        if self._player and self._player.is_playing:
            self._player.stop()
        self.fsm.transition(GameState.IDLE, reason='user_stop')
        self.log_panel.log('[Route] Đã dừng playback')

    def _route_mark_tree(self) -> None:
        """Mark current position as a tree."""
        if self._recorder.is_recording:
            self._recorder.mark_tree()
            self.log_panel.log('[Route] 🌳 Đã đánh dấu cây')

    def _route_mark_sell(self) -> None:
        """Mark current position as the sell NPC."""
        if self._recorder.is_recording:
            self._recorder.mark_sell()
            self.log_panel.log('[Route] 💰 Đã đánh dấu NPC bán')

    # ══════════════════════════════════════════════════════════
    #  SYSTEM INFO
    # ══════════════════════════════════════════════════════════

    def _get_sys_info(self) -> str:
        """Build startup system info string for the log panel."""
        tmpl = self.tmgr.get_template_count()
        info = (
            f"E={tmpl.get('e', 0)} "
            f"F={tmpl.get('f', 0)} "
            f"Y={tmpl.get('y', 0)} "
            f"Balo={len(self.tmgr.inventory_templates)}"
        )
        cd = 'ON' if self.config.get('notification_color_detect', True) else 'OFF'
        gpu_str = (
            self.gpu.device_name if self.gpu.is_available else 'CPU only'
        )
        m4_key = HOTKEYS.get('mode4', 'ctrl+F6')
        lines = [
            f'[Sys] v{APP_VERSION} — Templates: {info}',
            f'[Sys] Color detect: {cd} | GPS nav: {self.config.get("gps_navigation", True)}',
            f'[Sys] GPU: {gpu_str}',
            f'[Sys] Hotkeys: F7/F8/F9=Mode  {m4_key}=Route  F10=Stop  F11=Pause',
            f'[Sys] Ctrl+F7=Capture  Ctrl+F8=Mark Tree  Ctrl+F9=Mark Sell',
        ]
        return '\n'.join(lines)

    # ══════════════════════════════════════════════════════════
    #  CLEANUP
    # ══════════════════════════════════════════════════════════

    def _close(self) -> None:
        """Graceful shutdown: stop engine, route, unhook keys, destroy window."""
        logger.info('Closing...')
        self.engine.stop()
        if self._player and self._player.is_playing:
            self._player.stop()
        if self._recorder.is_recording:
            self._recorder.stop_recording()
        self._gps_nav.cleanup()
        self._cp_verifier.cleanup()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.destroy()
