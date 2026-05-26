"""AUTO GTA5VN v5.0 — Capture Manager

Auto-capture tool for creating and managing screen-region templates.
Provides utilities to grab screen regions, name templates following the
existing convention, and convert captures for GUI preview.
"""
from __future__ import annotations

import glob
import logging
import os
from typing import Optional, Tuple

import cv2
import numpy as np
from mss import MSS

from .utils import calc_region, get_screen_resolution, resource_path

logger = logging.getLogger("AutoGTA")


class CaptureManager:
    """Capture screen regions and save them as reusable templates.

    Parameters
    ----------
    config : dict
        Application configuration containing region definitions.
    """

    def __init__(self, config: dict) -> None:
        self.config: dict = config

    # ------------------------------------------------------------------
    # Screen capture
    # ------------------------------------------------------------------

    def capture_screen_region(
        self, region_key: str = "detect_region"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Capture the specified config region from the primary monitor.

        Parameters
        ----------
        region_key : str
            Key into ``self.config`` that holds the region percentages
            (e.g. ``"detect_region"``, ``"start_region"``).

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            ``(bgra_image, gray_image)``.
        """
        sw, sh = get_screen_resolution()
        region = calc_region(self.config[region_key], sw, sh)
        with MSS() as sct:
            img = np.array(sct.grab(region))
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        return img, gray

    # ------------------------------------------------------------------
    # Template naming
    # ------------------------------------------------------------------

    @staticmethod
    def get_next_index(key: str) -> int:
        """Return the next available numeric index for template *key*.

        Scans the template folder for existing files matching the
        ``<key>_*.png`` pattern and returns ``max(existing) + 1``.

        Parameters
        ----------
        key : str
            Template key (e.g. ``"e"``, ``"f"``, ``"y"``).

        Returns
        -------
        int
            Next index (1-based).
        """
        folder = resource_path(key.upper())
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)

        existing = glob.glob(os.path.join(folder, f"{key}_*.png"))
        if not existing:
            return 1

        indices: list[int] = []
        for f in existing:
            base = os.path.basename(f)
            try:
                # Handle both "e_ (1).png" and "e_1.png" naming conventions
                name = (
                    base.replace(f"{key}_ (", "")
                    .replace(f"{key}_", "")
                    .replace(").png", "")
                    .replace(".png", "")
                )
                indices.append(int(name))
            except (ValueError, IndexError):
                pass

        return max(indices, default=0) + 1

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def save_template(
        self,
        gray_image: np.ndarray,
        key: str,
        crop_rect: Optional[Tuple[int, int, int, int]] = None,
    ) -> str:
        """Save a grayscale image as a template file.

        Parameters
        ----------
        gray_image : np.ndarray
            Grayscale image to save.
        key : str
            Template key (e.g. ``"e"``).
        crop_rect : tuple[int, int, int, int] | None
            Optional ``(x, y, w, h)`` crop rectangle within the image.

        Returns
        -------
        str
            Absolute path to the saved template file.
        """
        if crop_rect is not None:
            x, y, w, h = crop_rect
            gray_image = gray_image[y : y + h, x : x + w]

        folder = resource_path(key.upper())
        os.makedirs(folder, exist_ok=True)
        idx = self.get_next_index(key)

        # Follow the existing naming convention: key_ (index).png
        filepath = os.path.join(folder, f"{key}_ ({idx}).png")
        cv2.imwrite(filepath, gray_image)
        logger.info("Template saved: %s", filepath)
        return filepath

    # ------------------------------------------------------------------
    # Preview conversion
    # ------------------------------------------------------------------

    @staticmethod
    def preview_as_pil(bgra_image: np.ndarray):
        """Convert a BGRA numpy array to a :class:`PIL.Image.Image`.

        Useful for displaying captures inside a Tkinter GUI.

        Parameters
        ----------
        bgra_image : np.ndarray
            BGRA image (e.g. from ``mss.grab()``).

        Returns
        -------
        PIL.Image.Image
            RGB PIL image.
        """
        from PIL import Image  # lazy import to avoid hard dependency

        rgb = cv2.cvtColor(bgra_image, cv2.COLOR_BGRA2RGB)
        return Image.fromarray(rgb)
