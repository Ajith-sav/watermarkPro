@echo off
REM ============================================================
REM  WatermarkPro v2 — Dependency Setup
REM  Run once before first build.
REM ============================================================
setlocal EnableDelayedExpansion
title WatermarkPro v2 Setup

echo.
echo  ====================================================
echo   WatermarkPro v2  ^|  Dependency Setup
echo  ====================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.  Install Python 3.10+ and tick "Add to PATH".
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK] %%v

REM ── Virtual environment ───────────────────────────────────
if exist ".venv\Scripts\activate.bat" (
    echo  [OK] .venv already exists.
) else (
    echo  [..] Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo  [OK] /.venv activated — completely isolated from system Python.

REM ── Upgrade pip ───────────────────────────────────────────
python -m pip install --upgrade pip --quiet
echo  [OK] pip upgraded.

REM ── Install packages ──────────────────────────────────────
echo  [..] Installing packages (this may take a minute)...
echo.
set FAIL=0

python -m pip install "psycopg2-binary>=2.9.9" --quiet
if errorlevel 1 (echo  [FAIL] psycopg2-binary & set FAIL=1) else echo  [OK] psycopg2-binary

python -m pip install "pystray>=0.19.5" --quiet
if errorlevel 1 (echo  [FAIL] pystray & set FAIL=1) else echo  [OK] pystray

python -m pip install "Pillow>=10.0.0" --quiet
if errorlevel 1 (echo  [FAIL] Pillow  & set FAIL=1) else echo  [OK] Pillow

python -m pip install "psutil>=5.9.0" --quiet
if errorlevel 1 (echo  [FAIL] psutil  & set FAIL=1) else echo  [OK] psutil

python -m pip install "pywin32>=306" --quiet
if errorlevel 1 (echo  [FAIL] pywin32 & set FAIL=1) else (
    echo  [OK] pywin32
    for /f "tokens=*" %%p in ('python -c "import sys; print(sys.prefix)"') do (
        python "%%p\Scripts\pywin32_postinstall.py" -install >nul 2>&1
    )
)

python -m pip install "pyinstaller>=6.0.0" --quiet
if errorlevel 1 echo  [WARN] pyinstaller ^(only for build^)

echo.
REM ── Verify imports ────────────────────────────────────────
python -c "
checks = [('psycopg2','psycopg2-binary'),('PIL','Pillow'),
          ('psutil','psutil'),('pystray','pystray'),('win32api','pywin32')]
ok = True
for mod, label in checks:
    try:
        __import__(mod); print(f'  [OK] {label}')
    except ImportError as e:
        print(f'  [FAIL] {label}: {e}'); ok = False
import sys; sys.exit(0 if ok else 1)
"
if errorlevel 1 set FAIL=1

REM ── Create config.ini from template if missing ────────────
if not exist "config.ini" (
    if exist "config.ini.template" (
        copy "config.ini.template" "config.ini" >nul
        echo.
        echo  [!!] config.ini created from template.
        echo       EDIT config.ini NOW and set your PostgreSQL connection details.
        notepad config.ini
    )
)

REM ── Create assets dir ────────────────────────────────────
if not exist "assets\" mkdir assets

echo.
if !FAIL!==0 (
    echo  ====================================================
    echo   All packages ready.  Next steps:
    echo    1. Edit config.ini with your PostgreSQL details
    echo    2. Run db_setup.sql on your PostgreSQL server
    echo    3. Run build_all.bat to build the EXEs
    echo    4. Run install.bat as Administrator to deploy
    echo  ====================================================
) else (
    echo  [ERROR] Some packages failed.  Run as Administrator or check proxy settings.
)
echo.
pause
