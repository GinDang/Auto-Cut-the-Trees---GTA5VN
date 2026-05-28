# Changelog

Tat ca thay doi dang chu y cua AUTO GTA5VN.

## [5.1] — 2026-05-28

### Sua loi (Bugfix)
- **Fix F/Y khong nhan dien** — Early-exit trong template matching thoat 3 vong lap khi E match 0.70+ → F va Y khong bao gio duoc quet. Gio luon scan tat ca key groups, chi early-exit trong cung 1 key (0.85+)
- **Fix Start Screen spam E** — Start screen detection false positive (threshold 0.68) → spam E 10 lan moi 3 giay, bo qua F/Y. Gio: threshold 0.78, chi bam 3 lan, cooldown 5s, khong check khi dang chat
- **Fix Confidence qua thap** — Tang confidence_threshold 0.55 → 0.65, start_threshold 0.68 → 0.78, tat adaptive_confidence (tranh tu giam qua thap)

### Them moi
- **Active Key Tracking** — Khi phat hien game hien nut nao (E/F/Y), tool "khoa" vao key do va spam nhanh (10ms/lan). Sau 5 frame khong match → reset, quet lai tat ca
- **Chopping State Machine** — Theo doi trang thai "dang chat" vs "idle". Chi check start screen khi idle. Timeout 8 giay khong match → chuyen ve idle
- **Debug Logging** — Log chi tiet per-key score, key switch, active key hits/misses de de debug lan test tiep

### Thay doi
- `AdaptiveThreshold.base`: 0.55 → 0.65
- `AdaptiveThreshold.min_threshold`: 0.35 → 0.50
- `INTRA_KEY_EXIT`: 0.85 (thay the cross-key exit 0.70)
- `START_COOLDOWN`: 3s → 5s
- Start E presses: 10 → 3
- Match delay: 15ms → 10ms (spam nhanh hon)

---

## [5.0] — 2026-05-26

### Them moi
- **Mode 4: Route Auto** — Ghi va phat lai duong di tu dong
- **Route Recorder** — Ghi keyboard + mouse + minimap checkpoints
- **Route Player** — Replay route voi checkpoint verification va stuck detection
- **GPS Navigator** — Doc vach chi duong mau tim/hong tren minimap de tu dieu huong
- **State Machine (FSM)** — Quan ly trang thai: IDLE → RECORDING → NAVIGATING → CUTTING → SELLING → STUCK
- **Mouse Controller** — Xoay camera bang ctypes Win32 API
- **Checkpoint Verifier** — So sanh minimap screenshots de xac nhan vi tri
- **Route Panel UI** — Quan ly route: ghi, phat, xoa, chon, refresh
- **Auto-sell** — Tu dong ban go khi balo day, quay lai route chinh
- **Auto-resume** — Tu dong tiep tuc route sau khi chat cay xong (timeout configurable)
- **Game Focus Safety** — Route tu pause khi game mat focus, tu resume khi quay lai
- **Resolution Scaling** — Tu dong scale mouse deltas cho cac resolution khac nhau
- **Route Speed** — Toc do replay tu 0.5x den 3.0x
- **Stuck Notification** — Hien thong bao khi route bi ket lien tuc
- **Emergency Release** — Tha tat ca phim khi switch mode (tranh ket phim)
- **Config Backup** — Luu backup config.json.bak khi save (tranh corrupt)
- **Delete Confirmation** — Hoi xac nhan truoc khi xoa route

### Cai tien
- **Settings v5.0** — Them toggle GPS Nav, Self-correct, Route Loop, slider Mouse sensitivity, Route Speed, Cutting Timeout
- **Config Validation v5.0** — Them validation cho mouse_sensitivity, route_speed, checkpoint_threshold, stuck_max_low, cutting_timeout
- **Checkpoint interval** — Tang default tu 20 len 50 (giam file PNG, tang performance)
- **Topbar route status** — Hien ten route, progress %, loop count khi chay Mode 4
- **Docstrings** — Cap nhat tat ca module tu v4.0 len v5.0
- **README** — Viet lai hoan toan cho v5.0

### Hotkeys moi
- `Ctrl+F6` — Mode 4 (Route Auto)
- `Ctrl+F8` — Danh dau cay (khi ghi route)
- `Ctrl+F9` — Danh dau NPC ban (khi ghi route)

---

## [4.0] — 2026-05

### Them moi
- **Humanized Input** — Nhan phim voi hold-time random (giong nguoi that)
- **ROI Tracking** — Thu nho vung quet quanh vi tri match truoc, tang FPS
- **Adaptive Confidence** — Tu dong dieu chinh nguong dua tren lich su match
- **GPU Acceleration** — Ho tro CUDA va OpenCL qua OpenCV UMat
- **Multi-scale** — Tim template o nhieu ty le (0.85x – 1.15x)
- **Sequence Predictor** — Du doan phim tiep theo dua tren pattern
- **Session Stats** — Thong ke phien chi tiet (FPS, confidence, detection ms...)
- **Settings Drawer** — Panel cai dat slide-out voi slider, toggle, region entries
- **Capture Dialog** — Chup va luu template truc tiep tu trong tool
- **Notification Bar** — Thanh canh bao khi balo day voi nut Continue/Stop
- **Sound Alert** — Am thanh beep khi balo day
- **Config Validation** — Kiem tra gia tri config hop le truoc khi save

### Cai tien
- **Dark Theme** — Giao dien toi premium voi glassmorphism
- **Modular GUI** — Chia nho thanh widget modules (topbar, controls, stats, log...)
- **Logging** — Ghi log ra file va hien trong Log Panel

---

## [3.0] — 2026-04

### Them moi
- **Multi-file Template** — Ho tro nhieu template cho moi phim (E/, F/, Y/ folders)
- **Color Detection** — Nhan dien balo day bang mau sac HSV (khong can template)
- **Template Manager** — Quan ly, load, va match templates tu dong
- **Game Focus Check** — Chi hoat dong khi cua so game active

---

## [2.0] — 2026-03

### Them moi
- **Package Structure** — Refactor tu 1 file thanh package `toolgta/`
- **CustomTkinter GUI** — Giao dien do hoa hien dai
- **3 che do** — Auto Detect, Auto E, Macro
- **Balo Detection** — Phat hien balo day bang template matching

---

## [1.0] — 2026-02

### Them moi
- **Macro co ban** — Nhan E > F > Y trinh tu
- **Template Matching** — Nhan dien phim tren man hinh bang OpenCV
- **Console Interface** — Giao dien dong lenh
