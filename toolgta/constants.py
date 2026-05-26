"""
AUTO GTA5VN - Constants & Configuration Defaults
Version 5.0

All application-wide constants, default configuration values,
color palette, hotkey mappings, and color utility functions.
"""
from __future__ import annotations

# ===========================================================
#  APP IDENTITY
# ===========================================================

APP_NAME: str = "AUTO GTA5VN"
APP_VERSION: str = "5.0"
CONFIG_FILE: str = "config.json"
LOG_FILE: str = "auto_gta5vn.log"


# ===========================================================
#  DEFAULT CONFIGURATION
# ===========================================================

DEFAULT_CONFIG: dict = {
    # --- Screen regions (percentage-based) ---
    "start_region": {
        "top_pct": 0.0,
        "left_pct": 0.0,
        "width_pct": 0.375,
        "height_pct": 0.1667,
    },
    "detect_region": {
        "top_pct": 0.2778,
        "left_pct": 0.3646,
        "width_pct": 0.2865,
        "height_pct": 0.3704,
    },
    "inventory_region": {
        "top_pct": 0.04,
        "left_pct": 0.68,
        "width_pct": 0.30,
        "height_pct": 0.08,
    },
    "notification_region": {
        "top_pct": 0.03,
        "left_pct": 0.65,
        "width_pct": 0.34,
        "height_pct": 0.10,
    },

    # --- Detection thresholds ---
    "notification_color_detect": True,
    "notification_color_ratio": 0.03,
    "confidence_threshold": 0.55,
    "start_threshold": 0.68,
    "inventory_threshold": 0.60,

    # --- Timing & limits ---
    "macro_delay_ms": 30,
    "max_wood_capacity": 30,
    "continue_when_full": False,
    "inventory_check_interval": 60,

    # --- Game window detection ---
    "game_window_keywords": ["GTA", "FiveM", "RAGE", "Grand Theft Auto"],

    # --- v4.0 new keys ---
    "humanize_keys": True,
    "humanize_jitter": 0.3,
    "roi_tracking": True,
    "roi_padding": 50,
    "adaptive_confidence": True,
    "gpu_acceleration": True,
    "sound_alert": True,
    "multi_scale": True,
    "scale_range": [0.85, 0.95, 1.0, 1.05, 1.15],

    # --- v5.0 Route Auto ---
    "minimap_region": {
        "top_pct": 0.78,
        "left_pct": 0.01,
        "width_pct": 0.14,
        "height_pct": 0.22,
    },
    "gps_color_lower": [140, 80, 100],
    "gps_color_upper": [170, 255, 255],
    "gps_navigation": True,
    "checkpoint_threshold": 0.65,
    "checkpoint_interval": 50,
    "stuck_timeout": 5.0,
    "stuck_max_low": 3,
    "mouse_sensitivity": 2.5,
    "arrival_threshold": 10,
    "route_loop": True,
    "self_correction": True,
    "route_speed": 1.0,
    "cutting_timeout": 30,
}


# ===========================================================
#  COLOR PALETTE
# ===========================================================

C: dict[str, str] = {
    "bg":           "#0B0B0B",
    "bg_card":      "#151515",
    "bg_card_alt":  "#1C1C1C",
    "bg_input":     "#222222",
    "bg_hover":     "#2A2A2A",
    "white":        "#FFFFFF",
    "text":         "#F2F2F2",
    "text_sec":     "#AAAAAA",
    "text_dim":     "#666666",
    "border":       "#333333",
    "border_light": "#444444",
    "divider":      "#2A2A2A",
    "yellow":       "#FFD600",
    "yellow_dim":   "#3D3200",
    "red":          "#FF4455",
    "red_dim":      "#3D1118",
    "green":        "#2AE87B",
    "green_dim":    "#0D3D22",
    "blue":         "#4A9EFF",
    "blue_dim":     "#112840",
    "orange":       "#FF8C42",
    "orange_dim":   "#3D2210",
    "purple":       "#B07AFF",
    "purple_dim":   "#291A40",
}


# ===========================================================
#  HOTKEY MAPPINGS
# ===========================================================

HOTKEYS: dict[str, str] = {
    "stop":          "F10",
    "mode1":         "F7",
    "mode2":         "F8",
    "mode3":         "F9",
    "mode4":         "ctrl+F6",
    "pause":         "F11",
    "toggle_window": "F12",
    "capture":       "ctrl+F7",
    "mark_tree":     "ctrl+F8",
    "mark_sell":     "ctrl+F9",
}


# ===========================================================
#  COLOR UTILITY
# ===========================================================

def blend(fg_hex: str, opacity: float, bg_hex: str | None = None) -> str:
    """Blend a foreground color with a background color at a given opacity.

    Args:
        fg_hex: Foreground color as a hex string (e.g. ``"#FFD600"``).
        opacity: Blend factor in ``[0.0, 1.0]``.  ``1.0`` = fully foreground.
        bg_hex: Background color hex string.  Defaults to ``C["bg"]``.

    Returns:
        Blended color as a hex string (e.g. ``"#1a1a00"``).
    """
    bg_hex = bg_hex or C["bg"]
    fg = tuple(int(fg_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    bg = tuple(int(bg_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    r = tuple(int(fg[i] * opacity + bg[i] * (1 - opacity)) for i in range(3))
    return f"#{r[0]:02x}{r[1]:02x}{r[2]:02x}"
