# AUTO GTA5VN - Auto Cut the Trees

Tool tu dong chat cay trong GTA5VN (FiveM). Nhan dien phim, ghi route, GPS navigation, va tu dong hoa 80-100%.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows&logoColor=white)
![Version](https://img.shields.io/badge/Version-5.0-purple)

---

## Tinh nang chinh

### 4 che do hoat dong

| Che do | Mo ta | Hotkey |
|--------|-------|--------|
| **[1] Auto Detect** | Nhan dien E / F / Y tren man hinh | F7 |
| **[2] Auto E** | Chi nhan dien va nhan E | F8 |
| **[3] Macro** | Nhan E > F > Y trinh tu (nhanh nhat) | F9 |
| **[4] Route Auto** | Tu dong di chuyen + chat cay + ban go | Ctrl+F6 |

### Route System (v5.0)
- **Route Recorder**: Ghi lai toan bo hanh trinh (phim + chuot)
- **Route Player**: Tu dong replay voi checkpoint verification
- **GPS Navigation**: Doc vach chi duong tren minimap de tu sua huong
- **Auto-sell**: Tu dong ban go khi balo day, quay lai tiep tuc
- **Resolution Scaling**: Ghi o 1080p, chay o 1440p → tu dieu chinh
- **Game Focus Safety**: Tu dong pause khi alt-tab, resume khi quay lai

### Tinh nang khac
- **Nhan dien balo day**: HSV color + template matching
- **ROI Tracking**: Thu nho vung quet de tang toc
- **Adaptive Confidence**: Tu dieu chinh nguong nhan dien
- **GPU Acceleration**: Dung CUDA/OpenCL neu co
- **Humanized Input**: Nhan phim giong nguoi that
- **Multi-scale**: Tim template o nhieu ty le

---

## Yeu cau he thong

- **OS:** Windows 10/11
- **Python:** 3.10 tro len
- **Game:** GTA5VN (FiveM) — Windowed hoac Borderless
- **RAM:** 4GB+
- **Luu y:** Hoat dong tren may tiem net (portable, khong can cai dat)

---

## Cai dat

### Buoc 1: Clone repository

```bash
git clone https://github.com/GinDang/Auto-Cut-the-Trees---GTA5VN.git
cd Auto-Cut-the-Trees---GTA5VN
```

### Buoc 2: Cai thu vien

```bash
pip install -r requirements.txt
```

---

## Chay tool

```bash
python -m toolgta
```

---

## Giao dien

```
+----------------------------------------------------------------------+
| AUTO GTA5VN  ● Route chinh — 45% — Loop #2   FPS 18  v5.0  1920x1080|
+-----------+------------------------+-----------+---------------------+
| CHE DO    |  E  12   F  5   Y  8  | ROUTES    | LOG                 |
|           |                       |           |                     |
| [1] Auto  |  BALO    18/30 go     | main_farm | [Sys] v5.0          |
| [2] AutoE |  ===============     | sell_npc  | [Route] Di chuyen...|
| [3] Macro |                       |           | [Route] Chat cay #3 |
| [4] Route |  THONG KE PHIEN      | [● REC]   | [FSM] NAV → CUT    |
|           |  ⏱ 00:12:34          | [▶ Play]  |                     |
| CAPTURE   |  ⚡ Det: 8.2ms        | [■ Stop]  |                     |
| CAI DAT   |  🌳 18/30 go          | [🗑 Xoa]  |                     |
| TAT AUTO  |                       |           |                     |
+-----------+------------------------+-----------+---------------------+
| Settings drawer (an di, nhan CAI DAT de mo)                          |
+----------------------------------------------------------------------+
```

---

## Huong dan su dung

### Che do 1/2/3 (co ban)

1. Mo game truoc, di den khu vuc co cay
2. Chon che do (click hoac F7/F8/F9)
3. Tool tu dong nhan dien phim va nhan tuong ung
4. F10 hoac click **TAT AUTO** de dung

### Che do 4: Route Auto (nang cao)

#### Buoc 1: Ghi route (chi can 1 lan)

```
1. Nhap ten route → Bam ● REC
2. Chuyen sang game → bat dau di chuyen
3. Den cay → Ctrl+F8 (danh dau cay)
4. Chat cay binh thuong
5. Di den cay tiep → Ctrl+F8
6. Khi muon danh dau duong di ban → Ctrl+F9
7. Di den NPC ban
8. Quay lai tool → ⏹ STOP
```

#### Buoc 2: Tu dong hoa

```
1. Chon route trong danh sach (click)
2. Bam ▶ Play hoac Ctrl+F6
3. Tool tu dong:
   Di chuyen → Chat cay → Di chuyen → Chat → ...
   Balo day → Di ban → Quay lai → Loop ♾️
```

---

## Phim tat

| Phim | Chuc nang |
|------|----------|
| **F7** | Mode 1 — Auto Detect |
| **F8** | Mode 2 — Auto E |
| **F9** | Mode 3 — Macro |
| **Ctrl+F6** | Mode 4 — Route Auto |
| **F10** | Dung tool |
| **F11** | Pause / Tiep tuc |
| **Ctrl+F7** | Capture template |
| **Ctrl+F8** | Danh dau cay (khi ghi route) |
| **Ctrl+F9** | Danh dau NPC ban (khi ghi route) |

---

## Cai dat nang cao

Click **CAI DAT** de mo panel cai dat:

### Co ban (v4.0)

| Tham so | Mo ta | Mac dinh |
|---------|-------|----------|
| Confidence | Nguong nhan dien (cao = chinh xac hon) | 0.55 |
| Macro (ms) | Delay giua cac phim che do Macro | 30 |
| Balo max | So go toi da truoc khi canh bao | 30 |
| Tiep tuc khi day | Tu dong tiep tuc khi balo day | OFF |
| Detect region | Vung quet nhan dien phim (% man hinh) | Center |
| Game keywords | Tu khoa cua so game | GTA, FiveM... |

### Route (v5.0)

| Tham so | Mo ta | Mac dinh |
|---------|-------|----------|
| GPS Nav | Bat/tat GPS navigation | ON |
| Self-correct | Bat/tat checkpoint verification | ON |
| Route Loop | Bat/tat loop vo han | ON |
| Mouse sensitivity | Do nhay chuot khi xoay camera (0.5–8.0) | 2.5 |
| Route Speed | Toc do replay (0.5x–3.0x) | 1.0x |
| Cutting Timeout | Thoi gian cho chat cay (10–90s) | 30s |

---

## Cau truc thu muc

```
Auto-Cut-the-Trees---GTA5VN/
├── toolgta/                    # Main package
│   ├── __init__.py             # Package exports
│   ├── __main__.py             # Entry point
│   ├── constants.py            # Config defaults, colors, hotkeys
│   ├── config.py               # Load/save/validate config
│   ├── engine.py               # Core automation engine (Mode 1/2/3)
│   ├── capture.py              # Screen capture manager
│   ├── template_manager.py     # Template loading & matching
│   ├── stats.py                # Session statistics
│   ├── utils.py                # Utilities (screen, game focus)
│   ├── gpu_utils.py            # GPU acceleration (CUDA/OpenCL)
│   ├── state_machine.py        # v5.0 — FSM (IDLE/CUT/NAV/SELL/STUCK)
│   ├── mouse_control.py        # v5.0 — Camera rotation (ctypes)
│   ├── checkpoint.py           # v5.0 — Minimap checkpoint verification
│   ├── route_recorder.py       # v5.0 — Route recording
│   ├── route_player.py         # v5.0 — Route playback
│   ├── gps_navigator.py        # v5.0 — GPS line detection
│   └── gui/
│       ├── app.py              # Main window
│       ├── topbar.py           # Status bar
│       ├── controls.py         # Mode buttons
│       ├── stats_panel.py      # E/F/Y counters + balo
│       ├── log_panel.py        # Log textbox
│       ├── notification.py     # Alert bar
│       ├── settings.py         # Settings drawer
│       ├── capture_dialog.py   # Template capture dialog
│       └── route_panel.py      # v5.0 — Route manager UI
├── routes/                     # Saved routes (auto-created)
├── E/ F/ Y/ BALO/              # Template images
├── config.json                 # User settings (auto-created)
├── auto_gta5vn.log             # Log file
├── requirements.txt            # Python dependencies
└── README.md
```

---

## Xu ly loi thuong gap

### Tool khong nhan dien duoc phim
- Giam `Confidence` xuong 0.40–0.50
- Dam bao game chay **Windowed/Borderless** (khong Fullscreen)
- Kiem tra vung Detect region co dung khong

### Route bi ket (stuck)
- Dieu chinh `Mouse sensitivity` trong Settings
- Giam `Checkpoint threshold` neu checkpoint khong match
- Thu ghi route moi o khu vuc it vat can

### GPS khong hoat dong
- Kiem tra minimap hinh **vuong** (khong tron)
- Dieu chinh mau GPS (`gps_color_lower/upper`) phu hop server
- Dam bao vach chi duong mau **tim/hong** hien tren minimap

### Balo day khong phat hien
- Them template vao thu muc `BALO/`
- Dam bao `Color detect: ON` trong log
- Kiem tra `inventory_region` trong config

---

## License

MIT License — Su dung tu do.

---

## Tac gia

**GinDang** — [GitHub](https://github.com/GinDang)
