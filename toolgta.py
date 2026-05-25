"""
AUTO GTA5VN - Tool tu dong chat cay
Version 3.0 - Horizontal Control Panel
"""

import time
import keyboard
import cv2
import numpy as np
from mss import MSS
import glob
import threading
import sys
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from collections import defaultdict

import customtkinter as ctk

# ===========================================================
#  CONFIGURATION & CONSTANTS
# ===========================================================

APP_NAME = "AUTO GTA5VN"
APP_VERSION = "3.0"
CONFIG_FILE = "config.json"
LOG_FILE = "auto_gta5vn.log"

DEFAULT_CONFIG = {
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
    "notification_color_detect": True,
    "notification_color_ratio": 0.03,
    "confidence_threshold": 0.55,
    "start_threshold": 0.68,
    "inventory_threshold": 0.60,
    "macro_delay_ms": 30,
    "max_wood_capacity": 30,
    "continue_when_full": False,
    "inventory_check_interval": 60,
    "game_window_keywords": ["GTA", "FiveM", "RAGE", "Grand Theft Auto"],
}

C = {
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


def blend(fg_hex, opacity, bg_hex=None):
    bg_hex = bg_hex or C["bg"]
    fg = tuple(int(fg_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    bg = tuple(int(bg_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    r = tuple(int(fg[i] * opacity + bg[i] * (1 - opacity)) for i in range(3))
    return f"#{r[0]:02x}{r[1]:02x}{r[2]:02x}"


# ===========================================================
#  LOGGING
# ===========================================================

def setup_logger():
    lg = logging.getLogger("AutoGTA")
    lg.setLevel(logging.DEBUG)
    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE)
        fh = RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        lg.addHandler(fh)
    except Exception:
        pass
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    lg.addHandler(ch)
    return lg

logger = setup_logger()


# ===========================================================
#  UTILITIES
# ===========================================================

def resource_path(relative_path):
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    path = resource_path(CONFIG_FILE)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for k, v in saved.items():
                if isinstance(v, dict) and k in cfg and isinstance(cfg[k], dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
            logger.info("Config loaded")
    except Exception as e:
        logger.warning("Config load failed: %s", e)
    return cfg


def save_config(cfg):
    path = resource_path(CONFIG_FILE)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        logger.info("Config saved")
    except Exception as e:
        logger.error("Config save failed: %s", e)


def get_screen_resolution():
    with MSS() as sct:
        m = sct.monitors[1]
    return m["width"], m["height"]


def calc_region(pct, sw, sh):
    return {
        "top": int(pct["top_pct"] * sh),
        "left": int(pct["left_pct"] * sw),
        "width": int(pct["width_pct"] * sw),
        "height": int(pct["height_pct"] * sh),
    }


def is_game_foreground(keywords):
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd).lower()
        return any(kw.lower() in title for kw in keywords)
    except Exception:
        return True


# ===========================================================
#  TEMPLATE MANAGER
# ===========================================================

class TemplateManager:
    def __init__(self, config):
        self.config = config
        self.templates = {"e": [], "f": [], "y": []}
        self.inventory_templates = []
        self.match_counts = {"e": defaultdict(int), "f": defaultdict(int), "y": defaultdict(int)}
        self.start_template = None
        self._load_all()

    def _preprocess(self, img):
        p = cv2.convertScaleAbs(img, alpha=2.5, beta=10)
        _, binary = cv2.threshold(p, 160, 255, cv2.THRESH_BINARY_INV)
        return binary

    def _load_all(self):
        for key in ["e", "f", "y"]:
            folder = resource_path(key.upper())
            if not os.path.isdir(folder):
                continue
            files = glob.glob(os.path.join(folder, f"{key}_*.png"))
            count = 0
            for fp in files:
                try:
                    img = cv2.imread(fp, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        self.templates[key].append({"image": self._preprocess(img), "index": count})
                        count += 1
                except Exception as e:
                    logger.error("Template load error %s: %s", fp, e)
            logger.info("Loaded %d templates for %s", count, key.upper())

        sp = resource_path("start_e.png")
        if os.path.exists(sp):
            self.start_template = cv2.imread(sp, cv2.IMREAD_GRAYSCALE)
            if self.start_template is not None:
                logger.info("Start template loaded (shape: %s)", self.start_template.shape)

        balo_dir = resource_path("BALO")
        if os.path.isdir(balo_dir):
            files = glob.glob(os.path.join(balo_dir, "*.png"))
            for fp in files:
                try:
                    img = cv2.imread(fp, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        self.inventory_templates.append({"image": img, "path": fp})
                except Exception as e:
                    logger.error("Inventory template error %s: %s", fp, e)
            logger.info("Loaded %d inventory templates", len(self.inventory_templates))

    def get_sorted_templates(self, key):
        return sorted(self.templates.get(key, []),
                      key=lambda t: self.match_counts[key][t["index"]], reverse=True)

    def record_match(self, key, idx):
        self.match_counts[key][idx] += 1

    def match_screen(self, gray, keys, threshold):
        t0 = time.perf_counter()
        screen_bin = self._preprocess(gray)
        best_score, best_key, best_idx = 0.0, "", -1
        for key in keys:
            for tmpl in self.get_sorted_templates(key):
                th, tw = tmpl["image"].shape[:2]
                if th > screen_bin.shape[0] or tw > screen_bin.shape[1]:
                    continue
                res = cv2.matchTemplate(screen_bin, tmpl["image"], cv2.TM_CCOEFF_NORMED)
                _, mx, _, _ = cv2.minMaxLoc(res)
                if mx > best_score:
                    best_score, best_key, best_idx = mx, key, tmpl["index"]
                if mx >= 0.70:
                    break
            if best_score >= 0.70:
                break
        elapsed = (time.perf_counter() - t0) * 1000
        if best_score >= threshold and best_idx >= 0:
            self.record_match(best_key, best_idx)
        return best_key, best_score, elapsed

    def check_start(self, gray, threshold):
        if self.start_template is None:
            return False
        try:
            th, tw = self.start_template.shape[:2]
            if th > gray.shape[0] or tw > gray.shape[1]:
                return False
            res = cv2.matchTemplate(gray, self.start_template, cv2.TM_CCOEFF_NORMED)
            _, mx, _, _ = cv2.minMaxLoc(res)
            return mx >= threshold
        except Exception:
            return False

    def check_inventory_full(self, gray, threshold):
        for tmpl in self.inventory_templates:
            try:
                th, tw = tmpl["image"].shape[:2]
                if th > gray.shape[0] or tw > gray.shape[1]:
                    continue
                res = cv2.matchTemplate(gray, tmpl["image"], cv2.TM_CCOEFF_NORMED)
                _, mx, _, _ = cv2.minMaxLoc(res)
                if mx >= threshold:
                    return True, mx
            except Exception:
                continue
        return False, 0.0

    @staticmethod
    def detect_notification_color(bgra_img, min_ratio=0.03):
        """Detect pink/red notification bar from GTA5VN by HSV color."""
        try:
            bgr = cv2.cvtColor(bgra_img, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            lower1 = np.array([155, 40, 60])
            upper1 = np.array([180, 255, 255])
            mask1 = cv2.inRange(hsv, lower1, upper1)
            lower2 = np.array([0, 40, 60])
            upper2 = np.array([12, 255, 255])
            mask2 = cv2.inRange(hsv, lower2, upper2)
            lower3 = np.array([140, 30, 50])
            upper3 = np.array([160, 200, 220])
            mask3 = cv2.inRange(hsv, lower3, upper3)
            combined = cv2.bitwise_or(mask1, cv2.bitwise_or(mask2, mask3))
            pink_pixels = cv2.countNonZero(combined)
            total_pixels = combined.shape[0] * combined.shape[1]
            ratio = pink_pixels / max(total_pixels, 1)
            return ratio >= min_ratio, ratio
        except Exception:
            return False, 0.0


# ===========================================================
#  AUTO ENGINE
# ===========================================================

class AutoEngine:
    def __init__(self, tmgr, config, ui_cb=None):
        self.tmgr = tmgr
        self.config = config
        self.ui_cb = ui_cb
        self.running = False
        self.paused = False
        self.stop_event = threading.Event()
        self.current_mode = 0
        self.counters = {"e": 0, "f": 0, "y": 0}
        self.fps = 0.0
        self.last_confidence = 0.0
        self.inventory_full_notified = False
        self.inventory_paused = False
        self.wood_estimate = 0

    def start(self, mode):
        if self.running:
            return False
        self.running = True
        self.paused = False
        self.current_mode = mode
        self.stop_event.clear()
        self.counters = {"e": 0, "f": 0, "y": 0}
        self.inventory_full_notified = False
        self.inventory_paused = False
        self.wood_estimate = 0
        threading.Thread(target=self._run, args=(mode,), daemon=True).start()
        logger.info("Started mode %d", mode)
        return True

    def stop(self):
        self.running = False
        self.stop_event.set()
        try:
            keyboard.release("w")
            keyboard.release(".")
        except Exception:
            pass
        logger.info("Stopped")

    def resume_from_full(self):
        self.inventory_paused = False
        self.inventory_full_notified = True
        self._notify("status", {"text": "Mode %d dang chay" % self.current_mode, "state": "running"})
        logger.info("Resumed after full inventory")

    def _notify(self, evt, data=None):
        if self.ui_cb:
            self.ui_cb(evt, data)

    def _run(self, mode):
        sct = MSS()
        sw, sh = get_screen_resolution()
        mon_start = calc_region(self.config["start_region"], sw, sh)
        mon_box = calc_region(self.config["detect_region"], sw, sh)
        mon_inv = calc_region(self.config["inventory_region"], sw, sh)
        mon_notif = calc_region(self.config["notification_region"], sw, sh)
        threshold = self.config.get("confidence_threshold", 0.55)
        start_thr = self.config.get("start_threshold", 0.68)
        inv_thr = self.config.get("inventory_threshold", 0.60)
        macro_delay = self.config.get("macro_delay_ms", 30) / 1000.0
        game_kw = self.config.get("game_window_keywords", [])
        continue_full = self.config.get("continue_when_full", False)
        inv_interval = self.config.get("inventory_check_interval", 60)
        max_wood = self.config.get("max_wood_capacity", 30)
        keys_pressed = False
        fps_count = 0
        fps_t = time.perf_counter()
        macro_seq = ["e", "f", "y"]
        macro_idx = 0
        frame_count = 0
        last_inv_check = 0

        self._notify("status", {"text": "Mode %d dang chay" % mode, "state": "running"})

        try:
            while self.running and not self.stop_event.is_set():
                if self.inventory_paused:
                    if keys_pressed:
                        keyboard.release("w")
                        keyboard.release(".")
                        keys_pressed = False
                    time.sleep(0.3)
                    continue

                if not is_game_foreground(game_kw):
                    if not self.paused:
                        self.paused = True
                        if keys_pressed:
                            keyboard.release("w")
                            keyboard.release(".")
                            keys_pressed = False
                        self._notify("status", {"text": "Tam dung - Game khong active", "state": "paused"})
                    time.sleep(0.5)
                    continue
                elif self.paused:
                    self.paused = False
                    self._notify("status", {"text": "Mode %d dang chay" % mode, "state": "running"})

                fps_count += 1
                now = time.perf_counter()
                if now - fps_t >= 1.0:
                    self.fps = fps_count / (now - fps_t)
                    fps_count = 0
                    fps_t = now
                    self._notify("fps", {"value": self.fps})

                frame_count += 1

                if inv_interval > 0 and (frame_count - last_inv_check) >= inv_interval:
                    last_inv_check = frame_count
                    self._check_inventory(sct, mon_inv, mon_notif, inv_thr, continue_full, max_wood)

                # MODE 3: MACRO
                if mode == 3:
                    if not keys_pressed:
                        keyboard.press("w")
                        keyboard.press(".")
                        keys_pressed = True
                    key = macro_seq[macro_idx]
                    keyboard.send(key)
                    self.counters[key] += 1
                    macro_idx = (macro_idx + 1) % len(macro_seq)
                    self._notify("counter", dict(self.counters))
                    self._update_wood_estimate()
                    time.sleep(macro_delay)
                    continue

                # MODE 1 & 2: Template
                if self.tmgr.start_template is not None:
                    try:
                        img = np.array(sct.grab(mon_start))
                        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                        if self.tmgr.check_start(gray, start_thr):
                            for _ in range(10):
                                keyboard.send("e")
                                time.sleep(0.007)
                            continue
                    except Exception:
                        pass

                try:
                    screen = np.array(sct.grab(mon_box))
                    gray = cv2.cvtColor(screen, cv2.COLOR_BGRA2GRAY)
                except Exception:
                    time.sleep(0.05)
                    continue

                if not keys_pressed:
                    keyboard.press("w")
                    keyboard.press(".")
                    keys_pressed = True

                scan_keys = ["e", "f", "y"] if mode == 1 else ["e"]
                best_key, best_score, elapsed = self.tmgr.match_screen(gray, scan_keys, threshold)
                self.last_confidence = best_score
                self._notify("confidence", {"value": best_score})

                if best_score >= threshold and best_key:
                    keyboard.send(best_key)
                    self.counters[best_key] += 1
                    self._notify("counter", dict(self.counters))
                    self._update_wood_estimate()
                    logger.info("Mode %d -> %s (%.4f, %.1fms)", mode, best_key.upper(), best_score, elapsed)
                    time.sleep(0.015)
                else:
                    time.sleep(0.020)

        except Exception as e:
            logger.error("Loop crash: %s", e, exc_info=True)
        finally:
            try:
                keyboard.release("w")
                keyboard.release(".")
            except Exception:
                pass
            self.running = False
            self.paused = False
            self._notify("status", {"text": "Da dung", "state": "stopped"})

    def _update_wood_estimate(self):
        total = sum(self.counters.values())
        self.wood_estimate = total // 3
        self._notify("wood", {"count": self.wood_estimate, "max": self.config.get("max_wood_capacity", 30)})

    def _check_inventory(self, sct, mon_inv, mon_notif, thr, continue_full, max_wood):
        if self.inventory_full_notified and self.config.get("continue_when_full", False):
            return
        is_full = False
        detect_method = ""
        score = 0.0
        try:
            if self.config.get("notification_color_detect", True):
                notif_img = np.array(sct.grab(mon_notif))
                color_ratio = self.config.get("notification_color_ratio", 0.03)
                color_found, ratio = self.tmgr.detect_notification_color(notif_img, color_ratio)
                if color_found:
                    is_full = True
                    score = ratio
                    detect_method = "color"
                    logger.warning("Notification COLOR detected! (pink ratio: %.4f)", ratio)

            if not is_full and self.tmgr.inventory_templates:
                inv_img = np.array(sct.grab(mon_inv))
                inv_gray = cv2.cvtColor(inv_img, cv2.COLOR_BGRA2GRAY)
                tmpl_found, tmpl_score = self.tmgr.check_inventory_full(inv_gray, thr)
                if not tmpl_found:
                    notif_gray = cv2.cvtColor(np.array(sct.grab(mon_notif)), cv2.COLOR_BGRA2GRAY)
                    tmpl_found, tmpl_score = self.tmgr.check_inventory_full(notif_gray, thr)
                if tmpl_found:
                    is_full = True
                    score = tmpl_score
                    detect_method = "template"
                    logger.warning("Notification TEMPLATE detected! (score: %.4f)", tmpl_score)

            if is_full and not self.inventory_full_notified:
                self._notify("inventory_full", {"score": score, "method": detect_method})
                if continue_full:
                    self.inventory_full_notified = True
                    logger.info("Continue-when-full enabled")
                else:
                    self.inventory_paused = True
                    self.inventory_full_notified = True
                    self._notify("status", {"text": "DUNG - Balo day!", "state": "inventory_full"})

            if not is_full and self.wood_estimate >= max_wood and not self.inventory_full_notified:
                logger.warning("Wood estimate reached max: %d/%d", self.wood_estimate, max_wood)
                self._notify("inventory_full", {"score": 0, "estimated": True, "method": "estimate"})
                if continue_full:
                    self.inventory_full_notified = True
                else:
                    self.inventory_paused = True
                    self.inventory_full_notified = True
                    self._notify("status", {"text": "DUNG - Balo day!", "state": "inventory_full"})

        except Exception as e:
            logger.error("Inventory check error: %s", e)


# ===========================================================
#  GUI - HORIZONTAL CONTROL PANEL
# ===========================================================

class AutoGTAApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("980x520")
        self.minsize(860, 440)
        self.configure(fg_color=C["bg"])
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.config = load_config()
        self.tmgr = TemplateManager(self.config)
        self.engine = AutoEngine(self.tmgr, self.config, ui_cb=self._on_event)
        self._pulse = True
        self._active_mode = 0
        self._notif_visible = False
        self._settings_vis = False
        self._build()
        keyboard.add_hotkey("F10", self._stop)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._tick_pulse()
        sw, sh = get_screen_resolution()
        self.res_lbl.configure(text=f"{sw}x{sh}")
        logger.info("App ready - %dx%d", sw, sh)

    def _build(self):
        self._build_topbar()
        self._build_body()
        self._build_settings_drawer()

    # -- TOP BAR --
    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=C["bg_card"], height=42, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14)

        ctk.CTkLabel(inner, text="AUTO GTA5VN",
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=C["white"]).pack(side="left")

        ctk.CTkFrame(inner, width=1, fg_color=C["border"]).pack(side="left", fill="y", padx=14, pady=8)

        self.dot = ctk.CTkLabel(inner, text="*", font=ctk.CTkFont(size=14, weight="bold"),
                                text_color=C["text_dim"], width=14)
        self.dot.pack(side="left", padx=(0, 4))

        self.status_lbl = ctk.CTkLabel(inner, text="Cho khoi chay",
                                        font=ctk.CTkFont(family="Segoe UI", size=12),
                                        text_color=C["text_sec"])
        self.status_lbl.pack(side="left")

        ctk.CTkFrame(inner, width=1, fg_color=C["border"]).pack(side="left", fill="y", padx=14, pady=8)

        self.fps_lbl = ctk.CTkLabel(inner, text="FPS --",
                                     font=ctk.CTkFont(family="Consolas", size=11),
                                     text_color=C["text_dim"])
        self.fps_lbl.pack(side="left", padx=(0, 12))

        self.conf_lbl = ctk.CTkLabel(inner, text="Score --",
                                      font=ctk.CTkFont(family="Consolas", size=11),
                                      text_color=C["text_dim"])
        self.conf_lbl.pack(side="left")

        self.res_lbl = ctk.CTkLabel(inner, text="...",
                                    font=ctk.CTkFont(family="Consolas", size=10),
                                    text_color=C["text_dim"])
        self.res_lbl.pack(side="right", padx=(6, 0))

        ctk.CTkLabel(inner, text=f"v{APP_VERSION}",
                     font=ctk.CTkFont(family="Consolas", size=10),
                     text_color=C["text_dim"]).pack(side="right", padx=(0, 8))

    # -- BODY (3 columns) --
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=8)
        self._build_left(body)
        self._build_center(body)
        self._build_right(body)

    # -- LEFT: Modes + Controls --
    def _build_left(self, parent):
        left = ctk.CTkFrame(parent, fg_color=C["bg_card"], width=195,
                             corner_radius=12, border_width=1, border_color=C["border"])
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)
        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(inner, text="CHE DO",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                     text_color=C["text_sec"]).pack(anchor="w", pady=(0, 6))

        modes = [
            (1, "[ 1 ]  Auto Detect", C["yellow"], C["yellow_dim"]),
            (2, "[ 2 ]  Auto E",      C["blue"],   C["blue_dim"]),
            (3, "[ 3 ]  Macro",       C["green"],  C["green_dim"]),
        ]
        self.mode_btns = []
        for mid, title, color, dim in modes:
            btn = ctk.CTkButton(
                inner, text=title,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=C["text"], fg_color=C["bg_input"],
                hover_color=dim, border_width=1, border_color=C["border"],
                corner_radius=8, height=36, anchor="w",
                command=lambda m=mid, c=color, d=dim: self._select_mode(m, c, d))
            btn.pack(fill="x", pady=2)
            self.mode_btns.append((mid, btn, color, dim))

        ctk.CTkFrame(inner, fg_color="transparent").pack(fill="both", expand=True)

        ctk.CTkButton(inner, text="CAI DAT",
                      font=ctk.CTkFont(size=11), fg_color="transparent",
                      hover_color=C["bg_hover"], text_color=C["text_dim"],
                      height=30, corner_radius=8, border_width=1,
                      border_color=C["border"],
                      command=self._toggle_settings).pack(fill="x", pady=(0, 4))

        self.stop_btn = ctk.CTkButton(
            inner, text="TAT AUTO   F10",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=C["red"], hover_color=blend(C["red"], 0.7),
            text_color=C["white"], height=38, corner_radius=8,
            command=self._stop)
        self.stop_btn.pack(fill="x")

    # -- CENTER: Stats + Inventory + Notification --
    def _build_center(self, parent):
        center = ctk.CTkFrame(parent, fg_color="transparent")
        center.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self._build_counters(center)
        self._build_inventory(center)
        self._build_notification_bar(center)

    def _build_counters(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 6))
        frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="c")
        self.cnt_lbls = {}
        cfgs = [
            ("E", C["yellow"]),
            ("F", C["blue"]),
            ("Y", C["green"]),
        ]
        for col, (key, color) in enumerate(cfgs):
            card = ctk.CTkFrame(frame, fg_color=C["bg_card"], corner_radius=10,
                                border_width=1, border_color=C["border"])
            card.grid(row=0, column=col, padx=3, sticky="nsew")
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(pady=10, padx=12)
            ctk.CTkLabel(row, text=key,
                         font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                         text_color=color).pack(side="left", padx=(0, 10))
            lbl = ctk.CTkLabel(row, text="0",
                               font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
                               text_color=C["white"])
            lbl.pack(side="left")
            self.cnt_lbls[key.lower()] = lbl

    def _build_inventory(self, parent):
        self.inv_card = ctk.CTkFrame(parent, fg_color=C["bg_card"], corner_radius=10,
                                      border_width=1, border_color=C["border"])
        self.inv_card.pack(fill="x", pady=(0, 6))
        inner = ctk.CTkFrame(self.inv_card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(top, text="BALO",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                     text_color=C["text"]).pack(side="left")

        self.wood_lbl = ctk.CTkLabel(top, text="0 / 30 go",
                                      font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                                      text_color=C["text_sec"])
        self.wood_lbl.pack(side="right")

        self.inv_status_lbl = ctk.CTkLabel(top, text="",
                                            font=ctk.CTkFont(size=10),
                                            text_color=C["text_dim"])
        self.inv_status_lbl.pack(side="right", padx=(0, 10))

        self.wood_prog = ctk.CTkProgressBar(inner, height=6, corner_radius=3,
                                             fg_color=C["bg_input"],
                                             progress_color=C["green"])
        self.wood_prog.pack(fill="x", pady=(6, 0))
        self.wood_prog.set(0)

    def _build_notification_bar(self, parent):
        self.notif_parent = parent
        self.notif_frame = ctk.CTkFrame(parent, fg_color=C["orange_dim"],
                                         corner_radius=10, border_width=1,
                                         border_color=C["orange"])
        inner = ctk.CTkFrame(self.notif_frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        self.notif_title = ctk.CTkLabel(top, text="! Balo day!",
                                         font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                         text_color=C["orange"])
        self.notif_title.pack(side="left")

        btn_row = ctk.CTkFrame(top, fg_color="transparent")
        btn_row.pack(side="right")

        ctk.CTkButton(btn_row, text="> Tiep tuc",
                      font=ctk.CTkFont(size=10, weight="bold"),
                      fg_color=C["green"], hover_color=blend(C["green"], 0.7),
                      text_color=C["bg"], corner_radius=6, height=26, width=90,
                      command=self._dismiss_continue).pack(side="left", padx=(0, 4))

        ctk.CTkButton(btn_row, text="|| Dung",
                      font=ctk.CTkFont(size=10, weight="bold"),
                      fg_color=C["red"], hover_color=blend(C["red"], 0.7),
                      text_color=C["white"], corner_radius=6, height=26, width=70,
                      command=self._dismiss_stop).pack(side="left")

        self.notif_desc = ctk.CTkLabel(inner, text="",
                                        font=ctk.CTkFont(size=10),
                                        text_color=C["text_sec"], wraplength=380)
        self.notif_desc.pack(anchor="w", pady=(4, 0))

    # -- RIGHT: Log --
    def _build_right(self, parent):
        right = ctk.CTkFrame(parent, fg_color=C["bg_card"], width=280,
                              corner_radius=12, border_width=1, border_color=C["border"])
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        inner = ctk.CTkFrame(right, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(hdr, text="LOG",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                     text_color=C["text_sec"]).pack(side="left")

        ctk.CTkButton(hdr, text="Xoa", font=ctk.CTkFont(size=9),
                      fg_color="transparent", hover_color=C["bg_hover"],
                      text_color=C["text_dim"], width=32, height=20,
                      corner_radius=4, command=self._clear_log).pack(side="right")

        self.log_box = ctk.CTkTextbox(
            inner, font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=C["bg"], text_color=C["text_dim"],
            border_width=1, border_color=C["border"],
            corner_radius=8, wrap="word", state="disabled")
        self.log_box.pack(fill="both", expand=True)

        info = (f"E={len(self.tmgr.templates['e'])} "
                f"F={len(self.tmgr.templates['f'])} "
                f"Y={len(self.tmgr.templates['y'])} "
                f"Balo={len(self.tmgr.inventory_templates)}")
        self._log(f"[Sys] Templates: {info}")
        cd = "ON" if self.config.get("notification_color_detect", True) else "OFF"
        self._log(f"[Sys] Color detect: {cd}")
        self._log("[Sys] F10 = Dung auto")
        self._setup_log_handler()

    # -- SETTINGS DRAWER --
    def _build_settings_drawer(self):
        self.settings_frame = ctk.CTkFrame(self, fg_color=C["bg_card"],
                                            corner_radius=0, border_width=1,
                                            border_color=C["border"])
        inner = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 6))
        row1.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="s")

        self.conf_slider, self.conf_val = self._make_slider(
            row1, 0, "Confidence", 0.30, 0.90, 60,
            self.config["confidence_threshold"], C["yellow"], self._on_conf)
        self.macro_slider, self.macro_val = self._make_slider(
            row1, 1, "Macro (ms)", 5, 200, 39,
            self.config["macro_delay_ms"], C["blue"], self._on_macro,
            fmt=lambda v: f"{int(v)}")
        self.wood_slider, self.wood_val = self._make_slider(
            row1, 2, "Balo max", 5, 100, 19,
            self.config["max_wood_capacity"], C["green"], self._on_wood_cap,
            fmt=lambda v: f"{int(v)}")
        self.inv_slider, self.inv_val = self._make_slider(
            row1, 3, "Check (frames)", 10, 300, 29,
            self.config["inventory_check_interval"], C["purple"], self._on_inv_interval,
            fmt=lambda v: f"{int(v)}")

        row2 = ctk.CTkFrame(inner, fg_color="transparent")
        row2.pack(fill="x")

        tog = ctk.CTkFrame(row2, fg_color="transparent")
        tog.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(tog, text="Tiep tuc khi day",
                     font=ctk.CTkFont(size=10), text_color=C["text_sec"]).pack(side="left", padx=(0, 6))
        self.full_toggle = ctk.CTkSwitch(
            tog, text="", width=40, height=20,
            fg_color=C["border"], progress_color=C["green"],
            button_color=C["white"], button_hover_color=C["text"],
            command=self._on_full_toggle)
        if self.config.get("continue_when_full", False):
            self.full_toggle.select()
        self.full_toggle.pack(side="left")

        self.region_entries = {}
        for rkey, rlabel in [("detect_region", "Detect"), ("notification_region", "Notif")]:
            grp = ctk.CTkFrame(row2, fg_color="transparent")
            grp.pack(side="left", padx=(0, 10))
            ctk.CTkLabel(grp, text=f"{rlabel}:", font=ctk.CTkFont(size=9),
                         text_color=C["text_dim"]).pack(side="left", padx=(0, 3))
            for fk, fl in [("top_pct", "T"), ("left_pct", "L"),
                           ("width_pct", "W"), ("height_pct", "H")]:
                ctk.CTkLabel(grp, text=fl, font=ctk.CTkFont(size=8),
                             text_color=C["text_dim"]).pack(side="left")
                ent = ctk.CTkEntry(grp, font=ctk.CTkFont(family="Consolas", size=9),
                                    fg_color=C["bg_input"], border_color=C["border"],
                                    text_color=C["text"], height=22, width=48, corner_radius=4)
                ent.insert(0, f"{self.config[rkey][fk]:.3f}")
                ent.pack(side="left", padx=(0, 2))
                self.region_entries[(rkey, fk)] = ent

        kw_grp = ctk.CTkFrame(row2, fg_color="transparent")
        kw_grp.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(kw_grp, text="Game:", font=ctk.CTkFont(size=9),
                     text_color=C["text_dim"]).pack(side="left", padx=(0, 3))
        self.kw_entry = ctk.CTkEntry(kw_grp, font=ctk.CTkFont(family="Consolas", size=9),
                                      fg_color=C["bg_input"], border_color=C["border"],
                                      text_color=C["text"], height=22, width=120, corner_radius=4)
        self.kw_entry.insert(0, ", ".join(self.config.get("game_window_keywords", [])))
        self.kw_entry.pack(side="left")

        ctk.CTkButton(row2, text="LUU",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      fg_color=C["yellow"], hover_color=blend(C["yellow"], 0.7),
                      text_color=C["bg"], height=28, width=70, corner_radius=6,
                      command=self._save_all).pack(side="right")

    def _make_slider(self, parent, col, label, lo, hi, steps, init, color, cmd, fmt=None):
        if fmt is None:
            fmt = lambda v: f"{v:.2f}"
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=0, column=col, padx=4, sticky="ew")
        hdr = ctk.CTkFrame(cell, fg_color="transparent")
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=label, font=ctk.CTkFont(size=10),
                     text_color=C["text_sec"]).pack(side="left")
        val_lbl = ctk.CTkLabel(hdr, text=fmt(init),
                               font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                               text_color=color)
        val_lbl.pack(side="right")
        slider = ctk.CTkSlider(cell, from_=lo, to=hi, number_of_steps=steps,
                                progress_color=color, button_color=C["white"],
                                button_hover_color=color, fg_color=C["bg_input"], height=14,
                                command=lambda v, vl=val_lbl, fn=fmt, cb=cmd: (
                                    vl.configure(text=fn(v)), cb(v)))
        slider.set(init)
        slider.pack(fill="x", pady=(2, 0))
        return slider, val_lbl

    # -- HANDLERS --
    def _setup_log_handler(self):
        class H(logging.Handler):
            def __init__(s, app):
                super().__init__()
                s.app = app
            def emit(s, rec):
                try:
                    msg = s.format(rec)
                    s.app.after(0, lambda m=msg: s.app._log(m))
                except Exception:
                    pass
        h = H(self)
        h.setLevel(logging.INFO)
        h.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        logging.getLogger("AutoGTA").addHandler(h)

    def _on_event(self, evt, data):
        self.after(0, lambda: self._proc(evt, data))

    def _proc(self, evt, data):
        try:
            if evt == "status":
                txt = data.get("text", "")
                state = data.get("state", "stopped")
                self.status_lbl.configure(text=txt)
                cmap = {"running": C["green"], "paused": C["yellow"],
                        "stopped": C["text_sec"], "inventory_full": C["orange"]}
                self.status_lbl.configure(text_color=cmap.get(state, C["text_sec"]))
            elif evt == "fps":
                self.fps_lbl.configure(text=f"FPS {data['value']:.0f}")
            elif evt == "confidence":
                v = data["value"]
                clr = C["green"] if v >= 0.55 else C["yellow"] if v >= 0.40 else C["text_dim"]
                self.conf_lbl.configure(text=f"Score {v:.3f}", text_color=clr)
            elif evt == "counter":
                for k in ["e", "f", "y"]:
                    if k in data:
                        self.cnt_lbls[k].configure(text=str(data[k]))
            elif evt == "wood":
                count = data.get("count", 0)
                mx = data.get("max", 30)
                ratio = min(count / max(mx, 1), 1.0)
                self.wood_lbl.configure(text=f"{count} / {mx} go")
                self.wood_prog.set(ratio)
                if ratio >= 1.0:
                    self.wood_prog.configure(progress_color=C["red"])
                    self.inv_status_lbl.configure(text="! Day!", text_color=C["red"])
                elif ratio >= 0.8:
                    self.wood_prog.configure(progress_color=C["orange"])
                    self.inv_status_lbl.configure(text="Sap day", text_color=C["orange"])
                else:
                    self.wood_prog.configure(progress_color=C["green"])
                    self.inv_status_lbl.configure(text="", text_color=C["text_dim"])
            elif evt == "inventory_full":
                estimated = data.get("estimated", False)
                method = data.get("method", "")
                if estimated:
                    msg = "Uoc tinh balo day dua tren so lan chat."
                elif method == "color":
                    msg = f"Phat hien thong bao hong (ty le: {data.get('score', 0):.1%})"
                elif method == "template":
                    msg = f"Template match (score: {data.get('score', 0):.2f})"
                else:
                    msg = f"Phat hien (score: {data.get('score', 0):.2f})"
                self._show_notif("! Tui do da day!", msg + " - Ban go hoac xe go.")
        except Exception:
            pass

    def _select_mode(self, mode, color, dim):
        if self.engine.running:
            self.engine.stop()
            self._hide_notif()
            self.after(200, lambda: self._start_mode(mode, color, dim))
        else:
            self._start_mode(mode, color, dim)

    def _start_mode(self, mode, color, dim):
        self._sync_config()
        self.engine.config = self.config
        if self.engine.start(mode):
            self._active_mode = mode
            for mid, btn, c, d in self.mode_btns:
                if mid == mode:
                    btn.configure(fg_color=dim, border_color=c)
                else:
                    btn.configure(fg_color=C["bg_input"], border_color=C["border"])

    def _stop(self):
        self.engine.stop()
        self._active_mode = 0
        self._hide_notif()
        for _, btn, _, _ in self.mode_btns:
            btn.configure(fg_color=C["bg_input"], border_color=C["border"])
        self.status_lbl.configure(text="Da dung", text_color=C["red"])
        self.dot.configure(text_color=C["red"])
        self.fps_lbl.configure(text="FPS --")

    def _show_notif(self, title, desc):
        if self._notif_visible:
            return
        self.notif_title.configure(text=title)
        self.notif_desc.configure(text=desc)
        self.notif_frame.pack(fill="x", pady=(0, 6))
        self._notif_visible = True

    def _hide_notif(self):
        if self._notif_visible:
            self.notif_frame.pack_forget()
            self._notif_visible = False

    def _dismiss_continue(self):
        self._hide_notif()
        self.engine.resume_from_full()

    def _dismiss_stop(self):
        self._hide_notif()
        self._stop()

    def _toggle_settings(self):
        if self._settings_vis:
            self.settings_frame.pack_forget()
            self._settings_vis = False
        else:
            self.settings_frame.pack(fill="x", side="bottom")
            self._settings_vis = True

    def _on_conf(self, v): self.config["confidence_threshold"] = v
    def _on_macro(self, v): self.config["macro_delay_ms"] = int(v)
    def _on_wood_cap(self, v): self.config["max_wood_capacity"] = int(v)
    def _on_inv_interval(self, v): self.config["inventory_check_interval"] = int(v)
    def _on_full_toggle(self): self.config["continue_when_full"] = self.full_toggle.get() == 1

    def _sync_config(self):
        self.config["confidence_threshold"] = self.conf_slider.get()
        self.config["macro_delay_ms"] = int(self.macro_slider.get())
        self.config["max_wood_capacity"] = int(self.wood_slider.get())
        self.config["inventory_check_interval"] = int(self.inv_slider.get())
        self.config["continue_when_full"] = self.full_toggle.get() == 1

    def _save_all(self):
        try:
            self._sync_config()
            for (rk, fk), ent in self.region_entries.items():
                try:
                    v = float(ent.get())
                    if 0 <= v <= 1:
                        self.config[rk][fk] = v
                except ValueError:
                    pass
            kw = self.kw_entry.get().strip()
            if kw:
                self.config["game_window_keywords"] = [w.strip() for w in kw.split(",") if w.strip()]
            self.engine.config = self.config
            save_config(self.config)
            self._log("[Sys] Cai dat da luu OK")
        except Exception as e:
            self._log(f"[Err] Luu that bai: {e}")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _log(self, msg):
        try:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            lines = int(self.log_box.index("end-1c").split(".")[0])
            if lines > 200:
                self.log_box.delete("1.0", "50.0")
            self.log_box.configure(state="disabled")
        except Exception:
            pass

    def _tick_pulse(self):
        if self.engine.running and not self.engine.paused and not self.engine.inventory_paused:
            self._pulse = not self._pulse
            c = C["green"] if self._pulse else blend(C["green"], 0.3)
            self.dot.configure(text_color=c)
        elif self.engine.paused:
            self._pulse = not self._pulse
            c = C["yellow"] if self._pulse else blend(C["yellow"], 0.3)
            self.dot.configure(text_color=c)
        elif self.engine.inventory_paused:
            self._pulse = not self._pulse
            c = C["orange"] if self._pulse else blend(C["orange"], 0.3)
            self.dot.configure(text_color=c)
        elif not self.engine.running:
            self.dot.configure(text_color=C["text_dim"])
        self.after(550, self._tick_pulse)

    def _close(self):
        logger.info("Closing...")
        self.engine.stop()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.destroy()


# ===========================================================
#  MAIN
# ===========================================================

if __name__ == "__main__":
    logger.info("=" * 40)
    logger.info("AUTO GTA5VN v%s starting", APP_VERSION)
    logger.info("=" * 40)
    app = AutoGTAApp()
    app.mainloop()
