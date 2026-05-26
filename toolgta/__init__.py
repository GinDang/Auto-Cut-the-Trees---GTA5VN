"""
AUTO GTA5VN - Core Package
Version 5.0

Foundation modules for the GTA5VN automation tool.
Includes route recording, GPS navigation, and state machine.
"""
from __future__ import annotations

from .constants import APP_NAME, APP_VERSION, C, CONFIG_FILE, DEFAULT_CONFIG, HOTKEYS, LOG_FILE, blend
from .config import load_config, save_config, validate_config
from .utils import (
    calc_region,
    emergency_release,
    get_screen_resolution,
    is_game_foreground,
    resource_path,
    setup_logger,
)
from .gpu_utils import GPUAccelerator
from .stats import SessionStats
from .state_machine import GameState, StateMachine
from .mouse_control import MouseController
from .checkpoint import CheckpointVerifier

__all__ = [
    # constants
    "APP_NAME",
    "APP_VERSION",
    "CONFIG_FILE",
    "LOG_FILE",
    "DEFAULT_CONFIG",
    "C",
    "HOTKEYS",
    "blend",
    # config
    "load_config",
    "save_config",
    "validate_config",
    # utils
    "resource_path",
    "get_screen_resolution",
    "calc_region",
    "is_game_foreground",
    "setup_logger",
    "emergency_release",
    # gpu
    "GPUAccelerator",
    # stats
    "SessionStats",
    # v5.0
    "GameState",
    "StateMachine",
    "MouseController",
    "CheckpointVerifier",
]
