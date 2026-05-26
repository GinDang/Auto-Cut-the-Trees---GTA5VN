"""
AUTO GTA5VN - Configuration Management
Version 5.0

Load, save, and validate the application configuration file.
Handles deep-merging of saved settings with defaults so that
new keys added in later versions are always present.
Atomic save with backup to prevent corruption.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from .constants import CONFIG_FILE, DEFAULT_CONFIG
from .utils import resource_path

logger: logging.Logger = logging.getLogger("AutoGTA")


# ===========================================================
#  LOAD / SAVE
# ===========================================================

def load_config() -> dict[str, Any]:
    """Load configuration from disk, merged over ``DEFAULT_CONFIG``.

    Missing keys are filled from defaults.  Nested dicts (e.g. region
    definitions) are recursively updated so that partial overrides
    work correctly.

    Returns:
        A fully-populated configuration dictionary.
    """
    cfg: dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG))
    path: str = resource_path(CONFIG_FILE)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                saved: dict[str, Any] = json.load(f)
            for k, v in saved.items():
                if isinstance(v, dict) and k in cfg and isinstance(cfg[k], dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
            logger.info("Config loaded from %s", path)
    except Exception as e:
        logger.warning("Config load failed: %s", e)
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    """Persist the configuration dictionary to disk as JSON.

    Uses atomic write: saves to a temporary file first, then
    renames.  Keeps a ``.bak`` backup of the previous config.

    Args:
        cfg: The configuration dictionary to save.
    """
    path: str = resource_path(CONFIG_FILE)
    tmp_path = path + ".tmp"
    bak_path = path + ".bak"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        # Backup old config
        if os.path.exists(path):
            try:
                if os.path.exists(bak_path):
                    os.remove(bak_path)
                os.rename(path, bak_path)
            except Exception:
                pass
        # Atomic rename
        os.rename(tmp_path, path)
        logger.info("Config saved to %s", path)
    except Exception as e:
        logger.error("Config save failed: %s", e)
        # Try to clean up tmp
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# ===========================================================
#  VALIDATION
# ===========================================================

def validate_config(cfg: dict[str, Any]) -> list[str]:
    """Validate configuration values and return a list of error messages.

    Checks numeric ranges for key parameters.  An empty list means the
    configuration is valid.

    Args:
        cfg: The configuration dictionary to validate.

    Returns:
        A list of human-readable error strings.  Empty if valid.
    """
    errors: list[str] = []

    # --- confidence_threshold: 0.1 – 1.0 ---
    ct = cfg.get("confidence_threshold")
    if ct is not None and not (0.1 <= ct <= 1.0):
        errors.append(
            f"confidence_threshold must be between 0.1 and 1.0 (got {ct})"
        )

    # --- start_threshold: 0.1 – 1.0 ---
    st = cfg.get("start_threshold")
    if st is not None and not (0.1 <= st <= 1.0):
        errors.append(
            f"start_threshold must be between 0.1 and 1.0 (got {st})"
        )

    # --- inventory_threshold: 0.1 – 1.0 ---
    it = cfg.get("inventory_threshold")
    if it is not None and not (0.1 <= it <= 1.0):
        errors.append(
            f"inventory_threshold must be between 0.1 and 1.0 (got {it})"
        )

    # --- macro_delay_ms: 5 – 1000 ---
    md = cfg.get("macro_delay_ms")
    if md is not None and not (5 <= md <= 1000):
        errors.append(
            f"macro_delay_ms must be between 5 and 1000 (got {md})"
        )

    # --- max_wood_capacity: 1 – 200 ---
    mw = cfg.get("max_wood_capacity")
    if mw is not None and not (1 <= mw <= 200):
        errors.append(
            f"max_wood_capacity must be between 1 and 200 (got {mw})"
        )

    # --- inventory_check_interval: 1 – 10000 ---
    ici = cfg.get("inventory_check_interval")
    if ici is not None and not (1 <= ici <= 10000):
        errors.append(
            f"inventory_check_interval must be between 1 and 10000 (got {ici})"
        )

    # --- notification_color_ratio: 0.001 – 1.0 ---
    ncr = cfg.get("notification_color_ratio")
    if ncr is not None and not (0.001 <= ncr <= 1.0):
        errors.append(
            f"notification_color_ratio must be between 0.001 and 1.0 (got {ncr})"
        )

    # --- humanize_jitter: 0.0 – 1.0 ---
    hj = cfg.get("humanize_jitter")
    if hj is not None and not (0.0 <= hj <= 1.0):
        errors.append(
            f"humanize_jitter must be between 0.0 and 1.0 (got {hj})"
        )

    # --- roi_padding: 0 – 500 ---
    rp = cfg.get("roi_padding")
    if rp is not None and not (0 <= rp <= 500):
        errors.append(
            f"roi_padding must be between 0 and 500 (got {rp})"
        )

    # --- scale_range: list of floats 0.1 – 3.0 ---
    sr = cfg.get("scale_range")
    if sr is not None:
        if not isinstance(sr, list) or len(sr) == 0:
            errors.append("scale_range must be a non-empty list of floats")
        else:
            for i, s in enumerate(sr):
                if not isinstance(s, (int, float)) or not (0.1 <= s <= 3.0):
                    errors.append(
                        f"scale_range[{i}] must be between 0.1 and 3.0 (got {s})"
                    )

    # --- Region dicts: all pct values must be 0.0 – 1.0 ---
    region_keys = [
        "start_region",
        "detect_region",
        "inventory_region",
        "notification_region",
        "minimap_region",
    ]
    for rk in region_keys:
        region = cfg.get(rk)
        if region is not None and isinstance(region, dict):
            for fk in ("top_pct", "left_pct", "width_pct", "height_pct"):
                val = region.get(fk)
                if val is not None and not (0.0 <= val <= 1.0):
                    errors.append(
                        f"{rk}.{fk} must be between 0.0 and 1.0 (got {val})"
                    )

    # --- v5.0 validation ---
    ms = cfg.get("mouse_sensitivity")
    if ms is not None and not (0.5 <= ms <= 8.0):
        errors.append(f"mouse_sensitivity must be between 0.5 and 8.0 (got {ms})")

    rs = cfg.get("route_speed")
    if rs is not None and not (0.1 <= rs <= 5.0):
        errors.append(f"route_speed must be between 0.1 and 5.0 (got {rs})")

    cpt = cfg.get("checkpoint_threshold")
    if cpt is not None and not (0.1 <= cpt <= 1.0):
        errors.append(f"checkpoint_threshold must be between 0.1 and 1.0 (got {cpt})")

    sml = cfg.get("stuck_max_low")
    if sml is not None and not (1 <= sml <= 20):
        errors.append(f"stuck_max_low must be between 1 and 20 (got {sml})")

    cto = cfg.get("cutting_timeout")
    if cto is not None and not (5 <= cto <= 120):
        errors.append(f"cutting_timeout must be between 5 and 120 (got {cto})")

    return errors
