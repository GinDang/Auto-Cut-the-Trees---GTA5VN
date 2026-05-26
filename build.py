"""
AUTO GTA5VN v5.0 — Build Script (PyInstaller)

Dong goi tool thanh portable .exe cho tiem net.

Cach dung:
    pip install pyinstaller
    python build.py

Ket qua:
    dist/AutoGTA5VN/
    ├── AutoGTA5VN.exe     ← Chay file nay
    ├── E/ F/ Y/ BALO/     ← Templates (tu copy hoac tu download)
    ├── config.json        ← Tu tao khi chay
    ├── routes/            ← Tu tao khi ghi route
    └── auto_gta5vn.log   ← Log file

Portable: Copy folder dist/AutoGTA5VN/ vao USB → chay duoc ngay.
"""
import os
import shutil
import subprocess
import sys


def build():
    print("=" * 50)
    print("AUTO GTA5VN v5.0 — Building Portable EXE")
    print("=" * 50)
    print()

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller chua cai. Dang cai...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] Da cai PyInstaller")

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--name", "AutoGTA5VN",
        # Folder mode (NOT --onefile) — faster startup, easier to update
        "--distpath", "dist",
        "--workpath", "build_temp",
        "--specpath", "build_temp",
        # Icon (if exists)
        # "--icon", "icon.ico",
        # Hidden imports that PyInstaller might miss
        "--hidden-import", "keyboard",
        "--hidden-import", "mss",
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "win32api",
        "--hidden-import", "win32gui",
        # Exclude unused modules to reduce size
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "tkinter.test",
        "--exclude-module", "unittest",
        "--exclude-module", "email",
        "--exclude-module", "html",
        "--exclude-module", "http",
        "--exclude-module", "xml",
        "--exclude-module", "pydoc",
        "--exclude-module", "doctest",
        # No console window
        "--windowed",
        # Entry point
        "toolgta/__main__.py",
    ]

    print()
    print("[*] Dang build... (co the mat 1-3 phut)")
    print(f"    Command: {' '.join(cmd[-3:])}")
    print()

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print("[!] Build that bai!")
        return False

    # Copy template folders next to exe
    dist_dir = os.path.join("dist", "AutoGTA5VN")
    if not os.path.isdir(dist_dir):
        # --onefile mode fallback
        dist_dir = "dist"

    print()
    print("[*] Copy templates...")
    for folder in ["E", "F", "Y", "BALO"]:
        src = folder
        dst = os.path.join(dist_dir, folder)
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            count = len([f for f in os.listdir(dst) if f.endswith(".png")])
            print(f"    {folder}/ → {count} templates")
        else:
            os.makedirs(dst, exist_ok=True)
            print(f"    {folder}/ → (empty, se tu download)")

    # Copy start_e.png if exists
    if os.path.isfile("start_e.png"):
        shutil.copy2("start_e.png", os.path.join(dist_dir, "start_e.png"))
        print("    start_e.png → copied")

    # Create routes folder
    os.makedirs(os.path.join(dist_dir, "routes"), exist_ok=True)
    print("    routes/ → created")

    # Clean up build temp
    if os.path.isdir("build_temp"):
        shutil.rmtree("build_temp", ignore_errors=True)

    # Calculate output size
    total_size = 0
    for dp, _, fns in os.walk(dist_dir):
        for fn in fns:
            total_size += os.path.getsize(os.path.join(dp, fn))

    print()
    print("=" * 50)
    print(f"[OK] Build thanh cong!")
    print(f"     Output: {os.path.abspath(dist_dir)}")
    print(f"     Size:   {total_size / 1024 / 1024:.1f} MB")
    print()
    print("HUONG DAN:")
    print(f"  1. Copy folder '{dist_dir}' vao USB")
    print(f"  2. Tai tiem net, mo folder va chay AutoGTA5VN.exe")
    print(f"  3. Khong can cai Python!")
    print("=" * 50)

    return True


if __name__ == "__main__":
    build()
