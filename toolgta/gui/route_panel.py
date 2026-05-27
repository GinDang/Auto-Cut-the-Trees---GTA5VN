"""AUTO GTA5VN v5.0 — Route Management Panel

GUI panel for recording, managing, and playing back routes.
Includes record/play controls, route list with selection highlighting,
progress bar, marker buttons, delete route, and refresh.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from typing import Any, Callable, List, Optional

import customtkinter as ctk

from ..constants import C, HOTKEYS, blend
from ..route_recorder import list_saved_routes

logger = logging.getLogger("AutoGTA")


class RoutePanel(ctk.CTkFrame):
    """Route management panel for recording and replaying routes.

    Parameters
    ----------
    parent : ctk.CTkFrame
        Parent widget.
    on_record_start : callable
        ``callback(route_name)`` when Record is pressed.
    on_record_stop : callable
        ``callback()`` when Stop Recording is pressed.
    on_play : callable
        ``callback(route_dir)`` when Play is pressed.
    on_play_stop : callable
        ``callback()`` when Stop Playback is pressed.
    on_mark_tree : callable
        ``callback()`` when Mark Tree is pressed.
    on_mark_sell : callable
        ``callback()`` when Mark Sell is pressed.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        on_record_start: Callable,
        on_record_stop: Callable,
        on_play: Callable,
        on_play_stop: Callable,
        on_mark_tree: Callable,
        on_mark_sell: Callable,
    ) -> None:
        super().__init__(
            parent, fg_color=C["bg_card"],
            corner_radius=12, border_width=1, border_color=C["border"],
        )

        self._on_record_start = on_record_start
        self._on_record_stop = on_record_stop
        self._on_play = on_play
        self._on_play_stop = on_play_stop
        self._on_mark_tree = on_mark_tree
        self._on_mark_sell = on_mark_sell

        self._is_recording = False
        self._is_playing = False
        self._selected_route: str = ""
        self._selected_label: ctk.CTkLabel | None = None  # for highlight

        self._build()

    # ------------------------------------------------------------------
    #  Build UI
    # ------------------------------------------------------------------

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 2}

        # ── Header ───────────────────────────────────────────
        hdr_frame = ctk.CTkFrame(self, fg_color="transparent")
        hdr_frame.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            hdr_frame, text="🗺  Route Manager",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["purple"], anchor="w",
        ).pack(side="left")

        # Refresh button
        ctk.CTkButton(
            hdr_frame, text="⟳", width=28, height=22,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", hover_color=C["bg_hover"],
            text_color=C["text_sec"],
            command=self._refresh_routes,
        ).pack(side="right")

        # ── Record controls ──────────────────────────────────
        rec_frame = ctk.CTkFrame(self, fg_color="transparent")
        rec_frame.pack(fill="x", **pad)

        self._name_entry = ctk.CTkEntry(
            rec_frame, placeholder_text="Tên route...",
            height=28, font=ctk.CTkFont(size=12),
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text"],
        )
        self._name_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._rec_btn = ctk.CTkButton(
            rec_frame, text="● REC", width=65, height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=C["red_dim"], hover_color=C["red"],
            text_color=C["red"], command=self._toggle_record,
        )
        self._rec_btn.pack(side="right")

        # ── Marker buttons ───────────────────────────────────
        marker_frame = ctk.CTkFrame(self, fg_color="transparent")
        marker_frame.pack(fill="x", **pad)

        self._tree_btn = ctk.CTkButton(
            marker_frame, text=f"🌳 Cây  [{HOTKEYS.get('mark_tree', '')}]",
            height=26, font=ctk.CTkFont(size=11),
            fg_color=C["green_dim"], hover_color=C["green"],
            text_color=C["green"], command=self._on_mark_tree,
            state="disabled",
        )
        self._tree_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))

        self._sell_btn = ctk.CTkButton(
            marker_frame, text=f"💰 Bán  [{HOTKEYS.get('mark_sell', '')}]",
            height=26, font=ctk.CTkFont(size=11),
            fg_color=C["orange_dim"], hover_color=C["orange"],
            text_color=C["orange"], command=self._on_mark_sell,
            state="disabled",
        )
        self._sell_btn.pack(side="right", fill="x", expand=True)

        # ── Divider ──────────────────────────────────────────
        ctk.CTkFrame(
            self, fg_color=C["divider"], height=1
        ).pack(fill="x", padx=8, pady=6)

        # ── Route list header ────────────────────────────────
        list_hdr = ctk.CTkFrame(self, fg_color="transparent")
        list_hdr.pack(fill="x", **pad)

        ctk.CTkLabel(
            list_hdr, text="Routes:",
            font=ctk.CTkFont(size=12),
            text_color=C["text_sec"], anchor="w",
        ).pack(side="left")

        self._del_btn = ctk.CTkButton(
            list_hdr, text="🗑", width=28, height=22,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", hover_color=C["red_dim"],
            text_color=C["text_dim"],
            command=self._delete_selected,
            state="disabled",
        )
        self._del_btn.pack(side="right")

        self._route_list_frame = ctk.CTkScrollableFrame(
            self, fg_color=C["bg_card_alt"], height=100,
            corner_radius=8,
        )
        self._route_list_frame.pack(fill="both", expand=True, **pad)

        self._refresh_routes()

        # ── Play controls ────────────────────────────────────
        play_frame = ctk.CTkFrame(self, fg_color="transparent")
        play_frame.pack(fill="x", padx=8, pady=(4, 2))

        self._play_btn = ctk.CTkButton(
            play_frame, text="▶ Play", width=80, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=C["purple_dim"], hover_color=C["purple"],
            text_color=C["purple"], command=self._toggle_play,
        )
        self._play_btn.pack(side="left", padx=(0, 4))

        self._stop_play_btn = ctk.CTkButton(
            play_frame, text="⏹ Stop", width=65, height=30,
            font=ctk.CTkFont(size=12),
            fg_color=C["bg_card_alt"], hover_color=C["red_dim"],
            text_color=C["text_sec"], command=self._stop_play,
            state="disabled",
        )
        self._stop_play_btn.pack(side="left")

        # ── Progress ─────────────────────────────────────────
        self._progress_bar = ctk.CTkProgressBar(
            self, height=6, corner_radius=3,
            fg_color=C["bg_card_alt"], progress_color=C["purple"],
        )
        self._progress_bar.pack(fill="x", padx=8, pady=(2, 2))
        self._progress_bar.set(0)

        self._status_label = ctk.CTkLabel(
            self, text="Sẵn sàng",
            font=ctk.CTkFont(size=11),
            text_color=C["text_dim"], anchor="w",
        )
        self._status_label.pack(fill="x", padx=8, pady=(0, 8))

    # ------------------------------------------------------------------
    #  Route list
    # ------------------------------------------------------------------

    def _refresh_routes(self) -> None:
        """Reload the route list from disk."""
        for child in self._route_list_frame.winfo_children():
            child.destroy()

        self._selected_label = None
        routes = list_saved_routes()
        if not routes:
            ctk.CTkLabel(
                self._route_list_frame,
                text="Chưa có route nào — bấm REC để tạo",
                font=ctk.CTkFont(size=11),
                text_color=C["text_dim"],
            ).pack(pady=10)
            return

        for r in routes:
            self._add_route_item(r)

    def _add_route_item(self, r: dict) -> None:
        """Add a single route item to the list."""
        frame = ctk.CTkFrame(
            self._route_list_frame, fg_color="transparent",
            height=28, cursor="hand2",
        )
        frame.pack(fill="x", pady=1)

        sell_icon = "💰" if r.get("has_sell") else "  "
        dur = r.get("duration", 0)
        dur_str = f"{int(dur // 60)}:{int(dur % 60):02d}"
        step_str = f"{r.get('steps', 0)}"

        label = ctk.CTkLabel(
            frame,
            text=f"  {r['name']}  ({r['trees']}🌳 {step_str}步 {dur_str}) {sell_icon}",
            font=ctk.CTkFont(size=11),
            text_color=C["text"], anchor="w",
        )
        label.pack(fill="x", side="left", expand=True)

        route_dir = r["dir"]
        label.bind("<Button-1>", lambda e, d=route_dir, lbl=label: self._select_route(d, lbl))
        frame.bind("<Button-1>", lambda e, d=route_dir, lbl=label: self._select_route(d, lbl))

    def _select_route(self, route_dir: str, label: ctk.CTkLabel = None) -> None:
        """Select a route from the list with visual highlighting."""
        # Unhighlight previous
        if self._selected_label is not None:
            try:
                self._selected_label.configure(text_color=C["text"])
            except Exception:
                pass

        self._selected_route = route_dir
        self._selected_label = label

        # Highlight new
        if label is not None:
            label.configure(text_color=C["purple"])

        self._del_btn.configure(state="normal")
        name = os.path.basename(route_dir)
        self._status_label.configure(text=f"✓ Đã chọn: {name}", text_color=C["text_dim"])

    def _delete_selected(self) -> None:
        """Delete the selected route directory after confirmation."""
        if not self._selected_route:
            return
        name = os.path.basename(self._selected_route)

        # Confirm dialog
        confirm = ctk.CTkInputDialog(
            text=f"Nhập 'xoa' để xóa route '{name}':",
            title="Xác nhận xóa route",
        )
        result = confirm.get_input()
        if result is None or result.strip().lower() != 'xoa':
            self._status_label.configure(text="Đã hủy xóa", text_color=C["text_dim"])
            return

        try:
            shutil.rmtree(self._selected_route, ignore_errors=True)
            logger.info("Deleted route: %s", name)
        except Exception as exc:
            logger.error("Failed to delete route %s: %s", name, exc)
        self._selected_route = ""
        self._selected_label = None
        self._del_btn.configure(state="disabled")
        self._refresh_routes()
        self._status_label.configure(text=f"Đã xóa: {name}", text_color=C["green"])

    # ------------------------------------------------------------------
    #  Record controls
    # ------------------------------------------------------------------

    def _toggle_record(self) -> None:
        if self._is_recording:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self) -> None:
        name = self._name_entry.get().strip()
        if not name:
            name = f"route_{int(time.time())}"
        self._is_recording = True
        self._rec_btn.configure(text="⏹ STOP", fg_color=C["red"], text_color=C["white"])
        self._tree_btn.configure(state="normal")
        self._sell_btn.configure(state="normal")
        self._status_label.configure(text="🔴 Đang ghi... Di chuyển trong game!", text_color=C["red"])
        self._on_record_start(name)

    def _stop_record(self) -> None:
        self._is_recording = False
        self._rec_btn.configure(text="● REC", fg_color=C["red_dim"], text_color=C["red"])
        self._tree_btn.configure(state="disabled")
        self._sell_btn.configure(state="disabled")
        self._status_label.configure(text="✓ Đã lưu route!", text_color=C["green"])
        self._on_record_stop()
        self._refresh_routes()

    # ------------------------------------------------------------------
    #  Play controls
    # ------------------------------------------------------------------

    def _toggle_play(self) -> None:
        if self._is_playing:
            return
        if not self._selected_route:
            self._status_label.configure(text="⚠ Chọn route trước!", text_color=C["orange"])
            return
        if not os.path.exists(self._selected_route):
            self._status_label.configure(text="⚠ Route không tồn tại!", text_color=C["red"])
            self._refresh_routes()
            return
        self._start_play()

    def _start_play(self) -> None:
        self._is_playing = True
        self._play_btn.configure(
            text="▶ Playing...", fg_color=C["purple"],
            text_color=C["white"], state="disabled",
        )
        self._stop_play_btn.configure(state="normal")
        self._status_label.configure(text="Đang chạy route...", text_color=C["purple"])
        self._on_play(self._selected_route)

    def _stop_play(self) -> None:
        was_playing = self._is_playing
        self._is_playing = False
        self._play_btn.configure(
            text="▶ Play", fg_color=C["purple_dim"],
            text_color=C["purple"], state="normal",
        )
        self._stop_play_btn.configure(state="disabled")
        self._progress_bar.set(0)
        self._status_label.configure(text="Đã dừng", text_color=C["text_dim"])
        # Only notify if we were actually playing (avoid double-stop)
        if was_playing:
            self._on_play_stop()

    # ------------------------------------------------------------------
    #  External updates
    # ------------------------------------------------------------------

    def update_progress(self, idx: int, total: int, loop: int, mode: str) -> None:
        """Update progress bar and status text."""
        if total > 0:
            self._progress_bar.set(idx / total)
        mode_str = "chính" if mode == "main" else "bán gỗ"
        self._status_label.configure(
            text=f"Bước {idx}/{total} | Loop #{loop} | Route {mode_str}",
            text_color=C["text_dim"],
        )

    def on_playback_stopped(self) -> None:
        """Called when playback stops (externally)."""
        self._is_playing = False
        self._play_btn.configure(
            text="▶ Play", fg_color=C["purple_dim"],
            text_color=C["purple"], state="normal",
        )
        self._stop_play_btn.configure(state="disabled")
        self._progress_bar.set(0)
        self._status_label.configure(text="Sẵn sàng", text_color=C["text_dim"])

    def on_tree_reached(self, idx: int, total: int) -> None:
        """Called when a tree marker is reached."""
        self._status_label.configure(
            text=f"🌳 Đang chặt cây... ({idx}/{total})",
            text_color=C["green"],
        )

    def on_checkpoint(self, idx: int, score: float) -> None:
        """Called when a checkpoint is verified."""
        color = C["green"] if score >= 0.65 else C["orange"] if score >= 0.4 else C["red"]
        self._status_label.configure(
            text=f"CP#{idx}: {score:.0%}", text_color=color,
        )

    def on_stuck(self) -> None:
        """Called when stuck is detected."""
        self._status_label.configure(
            text="⚠ Bị kẹt — đang sửa...", text_color=C["orange"],
        )

    def on_selling(self) -> None:
        """Called when auto-sell route is triggered."""
        self._status_label.configure(
            text="💰 Đang đi bán gỗ...", text_color=C["orange"],
        )
