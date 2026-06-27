@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title WatermarkPro v2 — Uninstallation
color 0E

REM ================================================================
REM  WatermarkPro v2 — Uninstall Script
REM  Must be run as Administrator
REM ================================================================

cd /d "%~dp0"

set INSTALL_DIR=C:\Program Files\WatermarkPro
set SVC_NAME=WatermarkProGuardian
set TASK_NAME=WatermarkPro
set REG_KEY=HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\WatermarkPro
set STEP=0
set ERRORS=0

echo.
echo  ================================================================
echo   WatermarkPro v2  ^|  System Uninstallation
echo  ================================================================
echo.

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 1 — Administrator check                                │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Checking administrator rights"
net session >nul 2>&1
if errorlevel 1 (
    call :fail "NOT running as administrator"
    echo.
    echo  HOW TO FIX:
    echo    Right-click uninstall.bat
    echo    Choose "Run as administrator"
    echo.
    pause & exit /b 1
)
call :pass "Running as Administrator"

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 2 — Stop and remove Windows Service                   │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Removing Guardian Windows Service"

sc query "%SVC_NAME%" >nul 2>&1
if not errorlevel 1 (
    echo          Service found — stopping it...
    sc stop "%SVC_NAME%" >nul 2>&1
    
    REM Wait for the service to fully stop and release file locks
    :WAIT_STOP_UNINSTALL
    sc query "%SVC_NAME%" | find "STOPPED" >nul
    if errorlevel 1 (
        timeout /t 1 /nobreak >nul
        goto WAIT_STOP_UNINSTALL
    )
    
    sc delete "%SVC_NAME%" >nul 2>&1
    echo          Service deleted from SCM.
) else (
    echo          Service not found (already removed).
)
call :pass "Service cleanup complete"

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 3 — Remove Task Scheduler entry                       │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Removing Task Scheduler entry"

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if not errorlevel 1 (
    schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
    if errorlevel 1 (
        call :fail "Failed to remove Task Scheduler entry"
        set /A ERRORS+=1
    ) else (
        echo          Task '%TASK_NAME%' deleted.
        call :pass "Task Scheduler entry removed"
    )
) else (
    echo          Task not found (already removed).
    call :pass "Task Scheduler cleanup complete"
)

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 4 — Kill running processes (unlocks files)            │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Closing running instances"

taskkill /F /IM WatermarkPro.exe >nul 2>&1
if errorlevel 1 (
    echo          WatermarkPro.exe not running.
) else (
    echo          WatermarkPro.exe terminated.
)

taskkill /F /IM WatermarkProAdmin.exe >nul 2>&1
if errorlevel 1 (
    echo          WatermarkProAdmin.exe not running.
) else (
    echo          WatermarkProAdmin.exe terminated.
)

taskkill /F /IM WatermarkProService.exe >nul 2>&1
if errorlevel 1 (
    echo          WatermarkProService.exe not running.
) else (
    echo          WatermarkProService.exe terminated.
)

timeout /t 2 /nobreak >nul
call :pass "Processes closed"

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 5 — Remove Registry entry from Windows Apps List      │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Removing from Windows Installed Apps"

reg query "%REG_KEY%" >nul 2>&1
if not errorlevel 1 (
    reg delete "%REG_KEY%" /f >nul 2>&1
    if errorlevel 1 (
        call :fail "Failed to delete registry key"
        set /A ERRORS+=1
    ) else (
        echo          Registry uninstall entry deleted.
        call :pass "Removed from Windows Settings > Apps"
    )
) else (
    echo          Registry entry not found (already removed).
    call :pass "Registry cleanup complete"
)

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 6 — Delete installation directory                     │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Deleting installation files"

if exist "%INSTALL_DIR%" (
    rd /s /q "%INSTALL_DIR%" >nul 2>&1
    if exist "%INSTALL_DIR%" (
        call :fail "Could not delete '%INSTALL_DIR%' (files may be locked)"
        echo.
        echo  HOW TO FIX:
        echo    1. Close all WatermarkPro windows.
        echo    2. Restart your computer.
        echo    3. Manually delete the folder: %INSTALL_DIR%
        echo.
        set /A ERRORS+=1
    ) else (
        echo          Folder deleted: %INSTALL_DIR%
        call :pass "Files successfully removed"
    )
) else (
    echo          Installation folder not found (already deleted).
    call :pass "File cleanup complete"
)

REM ================================================================
REM  FINAL STATUS DASHBOARD
REM ================================================================
echo.
echo  ================================================================
echo   UNINSTALLATION COMPLETE — STATUS DASHBOARD
echo  ================================================================
echo.
if !ERRORS!==0 (
    color 0A
    echo   [ALL STEPS PASSED]
    echo.
    echo   WatermarkPro has been completely removed from your system.
    echo   - Windows Service deleted
    echo   - Scheduled Task deleted
    echo   - Program Files deleted
    echo   - Removed from Windows Apps List
) else (
    color 0C
    echo   [COMPLETED WITH !ERRORS! STEP(S) THAT NEED ATTENTION]
    echo   Review the output above. Steps marked FAIL need manual fixing.
)
echo.
echo  ================================================================
echo.
pause
goto :eof

REM ================================================================
REM  SUBROUTINES
REM ================================================================
:begin_step
set /A STEP+=1
echo.
echo  ┌─ Step !STEP! — %~1
goto :eof

:pass
echo  └─ PASSED : %~1
goto :eof

:fail
set /A ERRORS+=1
echo  └─ FAILED : %~1
goto :eof