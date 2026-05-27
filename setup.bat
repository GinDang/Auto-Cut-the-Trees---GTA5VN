@echo off
chcp 65001 >nul 2>&1
title AUTO GTA5VN v5.0 - Setup
color 0A

echo.
echo  ========================================
echo       AUTO GTA5VN v5.0 - SETUP 1 CLICK
echo       Tool Tu Dong Chat Cay GTA5VN
echo  ========================================
echo.

REM -- Check Python --------------------------------
echo [1/3] Kiem tra Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [!] PYTHON CHUA CAI DAT!
    echo.
    echo  Cach 1: Tai Python tai https://python.org
    echo          Tick "Add Python to PATH" khi cai
    echo.
    echo  Cach 2: Neu tiem net co Chocolatey:
    echo          choco install python -y
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo       Python %PYVER% -- OK!
echo.

REM -- Install dependencies ------------------------
echo [2/3] Cai thu vien (lan dau mat ~1-2 phut)...
echo.
pip install -r requirements.txt --quiet --disable-pip-version-check 2>nul
if %errorlevel% neq 0 (
    echo  [!] Loi cai thu vien. Thu lai:
    echo      pip install -r requirements.txt
    pause
    exit /b 1
)
echo       Thu vien -- OK!
echo.

REM -- Launch --------------------------------------
echo [3/3] Khoi dong tool...
echo.
echo  ========================================
echo   F7=AutoDetect  F8=AutoE  F9=Macro
echo   Ctrl+F6=Route  F10=Stop  F11=Pause
echo  ========================================
echo.

python -m toolgta

echo.
echo  Tool da dong. Nhan phim bat ky de thoat...
pause >nul
