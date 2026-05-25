# AUTO GTA5VN - Auto Cut the Trees

Tool tu dong chat cay trong GTA5VN (FiveM). Nhan dien phim E / F / Y tren man hinh va tu dong nhan phim.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows&logoColor=white)

---

## Tinh nang

- **3 che do hoat dong:**
  - `Auto Detect` - Nhan dien E / F / Y tu dong
  - `Auto E` - Chi nhan dien va nhan E
  - `Macro` - Nhan E > F > Y trinh tu (nhanh nhat)
- **Nhan dien balo day:**
  - Phat hien thong bao hong in-game bang mau sac (HSV)
  - Template matching (thu muc BALO/)
  - Uoc tinh tu so lan nhan phim
- **Ho tro da resolution** (1080p, 1440p, 4K...)
- **Giao dien dieu khien ngang** - Dark theme, hien dai
- **Cai dat tuy chinh** - Confidence, macro delay, vung quet, balo max...
- **F10** - Phim tat dung nhanh

---

## Yeu cau he thong

- **OS:** Windows 10/11
- **Python:** 3.10 tro len
- **Game:** GTA5VN (FiveM) chay o che do **Windowed** hoac **Borderless**

---

## Cai dat

### Buoc 1: Cai Python

Tai va cai Python tu [python.org](https://www.python.org/downloads/)

> **Luu y:** Tick chon **"Add Python to PATH"** khi cai dat.

### Buoc 2: Clone repository

```bash
git clone https://github.com/GinDang/Auto-Cut-the-Trees---GTA5VN.git
cd Auto-Cut-the-Trees---GTA5VN
```

### Buoc 3: Cai thu vien

```bash
pip install opencv-python numpy mss keyboard customtkinter pywin32
```

Hoac su dung file requirements:

```bash
pip install -r requirements.txt
```

---

## Chay tool

```bash
python toolgta.py
```

Tool se khoi dong voi giao dien dieu khien:

```
+--------------------------------------------------------------------+
| AUTO GTA5VN   * Cho khoi chay   FPS --  Score --     v3.0  1920x1080|
+-------------+------------------------+-----------------------------+
| CHE DO      |  E  0    F  0    Y  0  |  LOG                        |
|             |                        |  [Sys] Templates: E=39...   |
| [1] Auto    |  BALO         0/30 go  |  [Sys] Color detect: ON     |
| [2] Auto E  |  ==================== |  [Sys] F10 = Dung auto      |
| [3] Macro   |                        |                             |
|             |                        |                             |
| CAI DAT     |                        |                             |
| TAT F10     |                        |                             |
+-------------+------------------------+-----------------------------+
| Settings drawer (an, nhan CAI DAT de mo)                           |
+--------------------------------------------------------------------+
```

---

## Huong dan su dung

### 1. Mo game truoc

Bat GTA5VN (FiveM) va vao server. Di den khu vuc co cay.

### 2. Chon che do

| Che do | Mo ta | Khi nao dung |
|--------|-------|-------------|
| **Auto Detect** | Nhan dien E/F/Y tren man hinh | Pho thong, an toan |
| **Auto E** | Chi nhan dien phim E | Khi chi can nhan E |
| **Macro** | Nhan E > F > Y lien tuc | Nhanh nhat, it an toan |

### 3. Bat dau

- Click vao nut che do (1/2/3)
- Tool se tu dong giu phim W (di chuyen) va . (chay)
- Khi phat hien phim tren man hinh, tool se nhan phim tuong ung

### 4. Dung

- Nhan **F10** hoac click **TAT AUTO**
- Tool se tha tat ca phim va dung

### 5. Balo day

Khi balo day, tool se:
- Hien thong bao canh bao
- Cho ban chon **Tiep tuc** hoac **Dung**
- Neu bat "Tiep tuc khi day" trong cai dat, tool chi canh bao 1 lan va tiep tuc

---

## Cai dat nang cao

Click **CAI DAT** de mo panel cai dat:

| Tham so | Mo ta | Mac dinh |
|---------|-------|----------|
| Confidence | Nguong nhan dien (cao = chinh xac hon) | 0.55 |
| Macro (ms) | Delay giua cac phim o che do Macro | 30ms |
| Balo max | So go toi da truoc khi canh bao | 30 |
| Check (frames) | Kiem tra balo moi bao nhieu frame | 60 |
| Tiep tuc khi day | Tu dong tiep tuc khi balo day | OFF |
| Detect region | Vung quet nhan dien phim (% man hinh) | Center |
| Notif region | Vung quet thong bao (% man hinh) | Top-right |
| Game keywords | Tu khoa cua so game | GTA, FiveM... |

---

## Cau truc thu muc

```
Auto-Cut-the-Trees---GTA5VN/
|-- toolgta.py          # File chinh
|-- start_e.png         # Template bat dau
|-- config.json         # Cai dat (tu dong tao)
|-- auto_gta5vn.log     # Log file
|-- requirements.txt    # Thu vien can thiet
|-- E/                  # Templates phim E (e_0.png, e_1.png...)
|-- F/                  # Templates phim F
|-- Y/                  # Templates phim Y
|-- BALO/               # Templates thong bao balo day
```

---

## Xu ly loi thuong gap

### Tool khong nhan dien duoc phim

- Tang kich thuoc cua so game
- Giam `Confidence` xuong 0.40-0.50
- Dam bao game chay Windowed/Borderless (khong Fullscreen)

### Tool nhan dien sai

- Tang `Confidence` len 0.60-0.70
- Kiem tra vung Detect region co dung khong

### Loi "Game khong active"

- Click vao cua so game de focus
- Kiem tra `Game keywords` co chua ten cua so game

### Balo day khong phat hien

- Them template vao thu muc `BALO/` (chup man hinh thong bao balo day)
- Dam bao `Color detect: ON` trong log

---

## Phim tat

| Phim | Chuc nang |
|------|----------|
| F10 | Dung tool |

---

## License

MIT License - Su dung tu do.

---

## Tac gia

**GinDang** - [GitHub](https://github.com/GinDang)
