"""AUTO GTA5VN v5.0 — Template Downloader

Downloads E/F/Y/BALO template packs from GitHub Releases
on first run if templates are missing locally.
Designed for portable use at internet cafes.
"""
from __future__ import annotations

import io
import logging
import os
import zipfile
from typing import Optional
from urllib import request, error

from .utils import resource_path

logger = logging.getLogger("AutoGTA")

# GitHub release URL for template pack
_TEMPLATES_URL = (
    "https://github.com/GinDang/Auto-Cut-the-Trees---GTA5VN"
    "/releases/download/templates-v1/templates.zip"
)

_REQUIRED_FOLDERS = ["E", "F", "Y"]
_MIN_FILES_PER_FOLDER = 5  # At least 5 templates per key


def templates_present() -> bool:
    """Check if template folders exist with enough files."""
    for folder in _REQUIRED_FOLDERS:
        path = resource_path(folder)
        if not os.path.isdir(path):
            return False
        pngs = [f for f in os.listdir(path) if f.endswith(".png")]
        if len(pngs) < _MIN_FILES_PER_FOLDER:
            return False
    return True


def download_templates(
    url: Optional[str] = None,
    progress_cb=None,
) -> bool:
    """Download and extract template pack from GitHub.

    Parameters
    ----------
    url : str | None
        Override download URL. Uses default GitHub release if None.
    progress_cb : callable | None
        Called with ``(status_text: str)`` for UI updates.

    Returns
    -------
    bool
        True if downloaded and extracted successfully.
    """
    url = url or _TEMPLATES_URL
    base_dir = resource_path("")

    def _notify(msg: str) -> None:
        logger.info(msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    _notify("Dang tai template tu GitHub...")

    try:
        req = request.Request(url, headers={"User-Agent": "AutoGTA5VN/5.0"})
        with request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        _notify(f"Da tai {len(data) // 1024} KB — dang giai nen...")
    except error.URLError as exc:
        _notify(f"Loi tai template: {exc}")
        logger.error("Template download failed: %s", exc)
        return False
    except Exception as exc:
        _notify(f"Loi: {exc}")
        logger.error("Template download error: %s", exc)
        return False

    # Extract zip
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Security: only extract known folders
            safe_prefixes = ("E/", "F/", "Y/", "BALO/", "E\\", "F\\", "Y\\", "BALO\\")
            extracted = 0
            for info in zf.infolist():
                if info.is_dir():
                    continue
                # Check path is safe
                name = info.filename.replace("\\", "/")
                if any(name.startswith(p.replace("\\", "/")) for p in safe_prefixes):
                    target = os.path.join(base_dir, info.filename)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(info) as src, open(target, "wb") as dst:
                        dst.write(src.read())
                    extracted += 1

        _notify(f"Hoan tat! Da giai nen {extracted} templates.")
        logger.info("Templates extracted: %d files to %s", extracted, base_dir)
        return extracted > 0
    except Exception as exc:
        _notify(f"Loi giai nen: {exc}")
        logger.error("Template extraction failed: %s", exc)
        return False


def ensure_templates(progress_cb=None) -> bool:
    """Check templates and download if missing.

    Call this at app startup.

    Returns True if templates are available (existing or downloaded).
    """
    if templates_present():
        return True

    logger.info("Templates missing — attempting download...")
    if download_templates(progress_cb=progress_cb):
        return templates_present()

    # Templates still missing — user needs to copy manually
    logger.warning(
        "Templates not available. Copy E/, F/, Y/ folders "
        "next to the executable."
    )
    return False
