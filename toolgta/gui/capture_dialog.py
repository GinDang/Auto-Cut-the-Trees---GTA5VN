"""AUTO GTA5VN v5.0 — Capture Dialog

Top-level dialog for capturing and saving detection templates.
Allows the user to take a screenshot of the current detect region,
preview it, and save it as a template for E, F, or Y keys.
"""
from __future__ import annotations

import os
from typing import Any, Callable, TYPE_CHECKING

import customtkinter as ctk

from ..constants import C, blend

if TYPE_CHECKING:
    import numpy as np
    from ..capture import CaptureManager
    from ..template_manager import TemplateManager

# Try importing Pillow for image preview
try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


class CaptureDialog(ctk.CTkToplevel):
    """Dialog for capturing and saving detection templates.

    Workflow:
        1. User clicks CAPTURE → screenshot of detect region is taken
        2. Preview image is displayed
        3. User selects key target (E / F / Y)
        4. User clicks SAVE → template is saved to the appropriate folder

    Args:
        parent: Parent window.
        capture_manager: CaptureManager instance for screen capture.
        template_manager: TemplateManager instance for template I/O.
        on_complete: Optional ``callback(key, filepath)`` after saving.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        capture_manager: Any,
        template_manager: Any,
        on_complete: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title('📷 Capture Template')
        self.geometry('520x440')
        self.configure(fg_color=C['bg'])
        self.resizable(False, False)

        self.capture_mgr = capture_manager
        self.tmgr = template_manager
        self.on_complete = on_complete

        self._current_image: Any = None   # BGRA numpy array
        self._current_gray: Any = None    # Grayscale numpy array
        self._selected_key: str = 'e'     # Default key
        self._preview_image: Any = None   # CTkImage reference (keep alive)

        self._build()

        # Focus this dialog
        self.focus_force()
        self.grab_set()

    # ── Construction ─────────────────────────────────────────

    def _build(self) -> None:
        # ── Instruction text ──
        ctk.CTkLabel(
            self, text='Nhan CAPTURE de chup vung detect hien tai',
            font=ctk.CTkFont(family='Segoe UI', size=12),
            text_color=C['text_sec'],
        ).pack(pady=(14, 8))

        # ── Preview area ──
        preview_frame = ctk.CTkFrame(
            self, fg_color=C['bg_card'], corner_radius=10,
            border_width=1, border_color=C['border'],
            width=460, height=220,
        )
        preview_frame.pack(padx=20, pady=(0, 10))
        preview_frame.pack_propagate(False)

        self._preview_lbl = ctk.CTkLabel(
            preview_frame, text='[ Preview ]',
            font=ctk.CTkFont(family='Consolas', size=11),
            text_color=C['text_dim'],
        )
        self._preview_lbl.pack(expand=True)

        # ── CAPTURE button ──
        ctk.CTkButton(
            self, text='📷  CAPTURE',
            font=ctk.CTkFont(family='Segoe UI', size=13, weight='bold'),
            fg_color=C['purple'], hover_color=blend(C['purple'], 0.7),
            text_color=C['white'], height=38, width=200, corner_radius=8,
            command=self._do_capture,
        ).pack(pady=(0, 10))

        # ── Key selector row ──
        key_frame = ctk.CTkFrame(self, fg_color='transparent')
        key_frame.pack(pady=(0, 10))

        ctk.CTkLabel(
            key_frame, text='Template cho phim:',
            font=ctk.CTkFont(size=11), text_color=C['text_sec'],
        ).pack(side='left', padx=(0, 10))

        self._key_btns: dict[str, ctk.CTkButton] = {}
        key_configs = [
            ('e', C['yellow'], C['yellow_dim']),
            ('f', C['blue'],   C['blue_dim']),
            ('y', C['green'],  C['green_dim']),
        ]
        for key, color, dim in key_configs:
            btn = ctk.CTkButton(
                key_frame, text=f'  {key.upper()}  ',
                font=ctk.CTkFont(family='Consolas', size=12, weight='bold'),
                fg_color=C['bg_input'], hover_color=dim,
                text_color=color, border_width=1, border_color=C['border'],
                corner_radius=6, height=30, width=50,
                command=lambda k=key, c=color, d=dim: self._select_key(k, c, d),
            )
            btn.pack(side='left', padx=3)
            self._key_btns[key] = btn

        # Highlight default key
        self._select_key('e', C['yellow'], C['yellow_dim'])

        # ── Bottom row: SAVE + Status ──
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(fill='x', padx=20, pady=(0, 14))

        ctk.CTkButton(
            bottom, text='💾  LUU TEMPLATE',
            font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
            fg_color=C['green'], hover_color=blend(C['green'], 0.7),
            text_color=C['bg'], height=36, width=180, corner_radius=8,
            command=self._do_save,
        ).pack(side='left')

        self._status_lbl = ctk.CTkLabel(
            bottom, text='',
            font=ctk.CTkFont(size=10),
            text_color=C['text_dim'],
        )
        self._status_lbl.pack(side='right')

    # ── Internal handlers ────────────────────────────────────

    def _select_key(self, key: str, color: str, dim: str) -> None:
        """Mark the selected key button as active."""
        self._selected_key = key
        for k, btn in self._key_btns.items():
            if k == key:
                btn.configure(fg_color=dim, border_color=color)
            else:
                btn.configure(fg_color=C['bg_input'], border_color=C['border'])

    def _do_capture(self) -> None:
        """Take a screenshot of the detect region and show preview."""
        try:
            bgra, gray = self.capture_mgr.capture_screen_region()
            self._current_image = bgra
            self._current_gray = gray

            if _HAS_PIL and bgra is not None:
                import cv2
                # Convert BGRA -> RGB for PIL
                rgb = cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGB)
                pil_img = Image.fromarray(rgb)

                # Resize to fit preview area
                max_w, max_h = 440, 200
                pil_img.thumbnail((max_w, max_h), Image.LANCZOS)

                ctk_img = ctk.CTkImage(light_image=pil_img, size=pil_img.size)
                self._preview_image = ctk_img  # prevent GC
                self._preview_lbl.configure(image=ctk_img, text='')
            else:
                self._preview_lbl.configure(
                    text='[Captured — Pillow not available for preview]'
                )

            self._status_lbl.configure(
                text='✓ Da chup! Chon phim va luu.',
                text_color=C['green'],
            )
        except Exception as e:
            self._status_lbl.configure(
                text=f'✗ Loi: {e}', text_color=C['red'],
            )

    def _do_save(self) -> None:
        """Save the captured template to disk."""
        if self._current_gray is None:
            self._status_lbl.configure(
                text='✗ Chua chup anh!', text_color=C['orange'],
            )
            return

        try:
            filepath = self.capture_mgr.save_template(
                self._current_gray, self._selected_key
            )
            basename = os.path.basename(filepath)
            self._status_lbl.configure(
                text=f'✓ Da luu: {basename}', text_color=C['green'],
            )

            if self.on_complete:
                self.on_complete(self._selected_key, filepath)

        except Exception as e:
            self._status_lbl.configure(
                text=f'✗ Loi luu: {e}', text_color=C['red'],
            )
