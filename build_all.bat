@echo off
REM ============================================================
REM  WatermarkPro v2 — Complete Build and Install Script
REM  Builds all three EXEs and installs the Windows Service.
REM
REM  Run order:
REM    1. setup.bat       (install Python deps — do once)
REM    2. build_all.bat   (this file — build all EXEs)
REM    3. install.bat     (copy to Program Files, register service)
REM ============================================================
setlocal EnableDelayedExpansion
title WatermarkPro v2 Build

echo.
echo  ====================================================
echo   WatermarkPro v2  ^|  Full Build
echo  ====================================================
echo.

REM ── Activate venv ─────────────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo  [ERROR] Run setup.bat first to create the virtual environment.
    pause & exit /b 1
)
call .venv\Scripts\activate.bat

REM ── Generate icon ─────────────────────────────────────────
echo  [..] Generating app icon...
python -c "from user_app._icon import generate_ico; generate_ico('assets/icon.ico')"
if exist "assets\icon.ico" (echo  [OK] Icon ready) else (echo  [WARN] Icon generation failed)

REM ── Clean previous dist ───────────────────────────────────
echo  [..] Cleaning previous build...
if exist "dist\"  rmdir /s /q dist
if exist "build\" rmdir /s /q build

REM ── Build User EXE ────────────────────────────────────────
echo.
echo  [..] Building WatermarkPro.exe (User watermark)...
pyinstaller user_app.spec --clean --noconfirm
if not exist "dist\WatermarkPro.exe" (
    echo  [FAIL] WatermarkPro.exe not created.
    pause & exit /b 1
)
echo  [OK] WatermarkPro.exe built.

REM ── Build Admin EXE ───────────────────────────────────────
echo.
echo  [..] Building WatermarkProAdmin.exe (Admin dashboard)...
pyinstaller admin_app.spec --clean --noconfirm
if not exist "dist\WatermarkProAdmin.exe" (
    echo  [FAIL] WatermarkProAdmin.exe not created.
    pause & exit /b 1
)
echo  [OK] WatermarkProAdmin.exe built.

REM ── Build Service EXE ─────────────────────────────────────
echo.
echo  [..] Building WatermarkProService.exe (Guardian service)...
pyinstaller service.spec --clean --noconfirm
if not exist "dist\WatermarkProService.exe" (
    echo  [FAIL] WatermarkProService.exe not created.
    pause & exit /b 1
)
echo  [OK] WatermarkProService.exe built.

REM ── Copy config ───────────────────────────────────────────
if exist "config.ini" (
    copy /Y "config.ini" "dist\config.ini" >nul
    echo  [OK] config.ini copied to dist\
) else (
    echo  [WARN] config.ini not found — copy config.ini.template to config.ini first!
)

echo.
echo  ====================================================
echo   BUILD COMPLETE
echo.
echo   dist\WatermarkPro.exe         ^← deploy to all users
echo   dist\WatermarkProAdmin.exe    ^← IT admin machines only
echo   dist\WatermarkProService.exe  ^← run install.bat to register
echo   dist\config.ini               ^← deploy alongside EXEs
echo  ====================================================
echo.
echo  Next step: run install.bat as Administrator to deploy.
pause
