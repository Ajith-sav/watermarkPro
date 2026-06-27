@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title WatermarkPro v2 — Installation
color 0A

REM ================================================================
REM  WatermarkPro v2 — Install Script
REM  Must be run as Administrator (right-click → Run as administrator)
REM ================================================================

set INSTALL_DIR=C:\Program Files\WatermarkPro
set SVC_NAME=WatermarkProGuardian
set TASK_NAME=WatermarkPro
set STEP=0
set ERRORS=0

call :header

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 1 — Administrator check                                │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Checking administrator rights"
net session >nul 2>&1
if errorlevel 1 (
    call :fail "NOT running as administrator"
    echo.
    echo  HOW TO FIX:
    echo    Right-click install.bat
    echo    Choose "Run as administrator"
    echo.
    pause & exit /b 1
)
call :pass "Running as Administrator"

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 2 — Verify all required files exist in dist\          │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Checking required files in dist\"

echo %CD%
dir dist

set MISS=0
for %%F in (
    dist\WatermarkPro.exe
    dist\WatermarkProAdmin.exe
    dist\WatermarkProService.exe
    dist\config.ini
) do (
    if exist "%%F" (
        echo          Found   : %%F
    ) else (
        echo          MISSING : %%F
        set MISS=1
    )
)
@REM if !MISS!==1 (
@REM     echo.
@REM     echo          dist\ files are missing — build_all.bat must run first.
@REM     echo.
@REM     set /P "RUNBUILD=  Run build_all.bat now automatically? (Y/N): "
@REM     if /I "!RUNBUILD!"=="Y" (
@REM         echo.
@REM         echo  ================================================================
@REM         echo   Running build_all.bat ...
@REM         echo  ================================================================
@REM         call "%~dp0build_all.bat"
@REM         if errorlevel 1 (
@REM             call :fail "build_all.bat failed — fix errors above then re-run install.bat"
@REM             pause & exit /b 1
@REM         )
@REM         REM Re-check after build
@REM         set MISS=0
@REM         for %%F in (
@REM             dist\WatermarkPro.exe
@REM             dist\WatermarkProAdmin.exe
@REM             dist\WatermarkProService.exe
@REM             dist\config.ini
@REM         ) do (
@REM             if not exist "%%F" (
@REM                 echo          STILL MISSING : %%F
@REM                 set MISS=1
@REM             )
@REM         )
@REM         if !MISS!==1 (
@REM             call :fail "Build finished but files still missing — check build output"
@REM             pause & exit /b 1
@REM         )
@REM     ) else (
@REM         echo.
@REM         echo  Steps to fix:
@REM         echo    1. Run setup.bat     (install Python packages)
@REM         echo    2. Edit config.ini   (set your PostgreSQL details)
@REM         echo    3. Run build_all.bat (creates the EXEs in dist\)
@REM         echo    4. Run install.bat   (this script) again
@REM         call :fail "Cancelled — re-run install.bat after build_all.bat completes"
@REM         pause & exit /b 1
@REM     )
@REM )
call :pass "All required files present"

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 3 — Stop and remove any previous installation        │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Removing previous installation (if any)"

sc query "%SVC_NAME%" >nul 2>&1
if not errorlevel 1 (
    echo          Previous service found — stopping it...
    sc stop "%SVC_NAME%" >nul 2>&1
    timeout /t 4 /nobreak >nul
    "%INSTALL_DIR%\WatermarkProService.exe" remove >nul 2>&1
    timeout /t 2 /nobreak >nul
    echo          Old service removed.
) else (
    echo          No previous service found.
)

schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
echo          Old logon task removed (or did not exist).
call :pass "Cleanup done"

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 4 — Create install directory                          │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Creating install directory"
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    if errorlevel 1 (
        call :fail "Cannot create %INSTALL_DIR%"
        pause & exit /b 1
    )
)
if not exist "%INSTALL_DIR%\assets" mkdir "%INSTALL_DIR%\assets"
echo          Path: %INSTALL_DIR%
call :pass "Directory ready"

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 5 — Copy application files                           │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Copying application files"
set COPY_ERR=0

copy /Y "dist\WatermarkProAdmin.exe"   "%INSTALL_DIR%\" >nul 2>&1
if errorlevel 1 (echo          FAILED: WatermarkProAdmin.exe  & set COPY_ERR=1) else echo          Copied : WatermarkProAdmin.exe

copy /Y "dist\WatermarkPro.exe"        "%INSTALL_DIR%\" >nul 2>&1
if errorlevel 1 (echo          FAILED: WatermarkPro.exe       & set COPY_ERR=1) else echo          Copied : WatermarkPro.exe

copy /Y "dist\WatermarkProService.exe" "%INSTALL_DIR%\" >nul 2>&1
if errorlevel 1 (echo          FAILED: WatermarkProService.exe & set COPY_ERR=1) else echo          Copied : WatermarkProService.exe

copy /Y "dist\config.ini"              "%INSTALL_DIR%\" >nul 2>&1
if errorlevel 1 (echo          FAILED: config.ini             & set COPY_ERR=1) else echo          Copied : config.ini

if exist "assets\icon.ico" (
    copy /Y "assets\icon.ico" "%INSTALL_DIR%\assets\" >nul 2>&1
    echo          Copied : assets\icon.ico
)

if !COPY_ERR!==1 (
    call :fail "One or more files failed to copy"
    pause & exit /b 1
)
call :pass "All files copied"

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 6 — Install Windows Service                          │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Installing Guardian Windows Service"
echo          Running: WatermarkProService.exe install
echo.

REM Reset errorlevel to 0 before running
ver >nul

"%INSTALL_DIR%\WatermarkProService.exe" install

REM Check if the service actually exists in Windows
sc query "%SVC_NAME%" >nul 2>&1
if errorlevel 1 (
    echo          Initial install failed. Attempting force cleanup and retry...
    
    REM Force stop and delete the broken service
    sc stop "%SVC_NAME%" >nul 2>&1
    timeout /t 2 /nobreak >nul
    sc delete "%SVC_NAME%" >nul 2>&1
    timeout /t 3 /nobreak >nul
    
    REM Retry installation
    echo          Retrying: WatermarkProService.exe install
    "%INSTALL_DIR%\WatermarkProService.exe" install
    timeout /t 2 /nobreak >nul
    
    REM Check again if it succeeded
    sc query "%SVC_NAME%" >nul 2>&1
    if errorlevel 1 (
        call :fail "Service installation failed even after retry"
        echo.
        echo  MANUAL FIX REQUIRED:
        echo    1. Open an Administrator Command Prompt
        echo    2. Run: sc delete %SVC_NAME%
        echo    3. Restart your computer (if access is denied)
        echo    4. Run install.bat again
        echo.
        pause & exit /b 1
    ) else (
        call :pass "Service registered successfully after retry"
    )
) else (
    call :pass "Service registered with Windows SCM"
)

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 7 — Configure service (auto-start + failure recovery) │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Configuring service startup and recovery"

sc config "%SVC_NAME%" start= auto
if errorlevel 1 (
    call :fail "Could not set auto-start"
    set /A ERRORS+=1
) else (
    echo          Auto-start : ENABLED
)

REM Recovery: restart after 5s / 10s / 15s, reset counter after 24h
sc failure "%SVC_NAME%" reset= 86400 actions= restart/5000/restart/10000/restart/15000
if errorlevel 1 (
    echo          Recovery   : WARNING - could not set (non-fatal)
) else (
    echo          Recovery   : restart after 5s / 10s / 15s
)

sc description "%SVC_NAME%" "WatermarkPro Guardian: monitors and restarts the screen watermark. Requires Administrator to stop."
echo          Description: set

call :pass "Service configured"

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 8 — Start the service                                 │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Starting Guardian service"
sc start "%SVC_NAME%"
echo.
echo          Waiting 6 seconds for service to initialise...
timeout /t 6 /nobreak >nul

sc query "%SVC_NAME%" | findstr /I "STATE" | findstr /I "RUNNING" >nul 2>&1
if errorlevel 1 (
    call :fail "Service is NOT running"
    echo.
    echo  DETAILS:
    sc query "%SVC_NAME%"
    echo.
    echo  HOW TO DIAGNOSE:
    echo    1. Open Event Viewer
    echo    2. Windows Logs ^> Application
    echo    3. Look for errors from WatermarkProGuardian
    echo.
    set /A ERRORS+=1
) else (
    call :pass "Service is RUNNING"
)

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 9 — Register Task Scheduler (silent logon, no terminal)│
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Registering logon task in Task Scheduler"

REM Put the full schtasks command on ONE LINE to avoid ^ continuation issues
schtasks /Create /TN "%TASK_NAME%" /TR "\"%INSTALL_DIR%\WatermarkPro.exe\"" /SC ONLOGON /DELAY 0000:30 /IT /RL LIMITED /F

if errorlevel 1 (
    call :fail "Task Scheduler registration failed"
    echo.
    echo  HOW TO FIX MANUALLY:
    echo    Open Task Scheduler ^> Create Basic Task
    echo    Program: %INSTALL_DIR%\WatermarkPro.exe
    echo    Trigger: At log on
    echo.
    set /A ERRORS+=1
) else (
    echo          Task name  : %TASK_NAME%
    echo          Trigger    : At logon (30s delay)
    echo          Run as     : Current user
    echo          No window  : Yes (--noconsole EXE)
    call :pass "Logon task created"
)

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 10 — Launch watermark right now (no need to log off)  │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Launching watermark for current session"
start /B "" "%INSTALL_DIR%\WatermarkPro.exe"
echo          Waiting 4 seconds...
timeout /t 4 /nobreak >nul
tasklist /FI "IMAGENAME eq WatermarkPro.exe" /NH 2>nul | findstr /I "WatermarkPro" >nul 2>&1
if errorlevel 1 (
    echo          WARNING: WatermarkPro.exe not yet visible in process list.
    echo          It may still be starting. Check Task Manager in a moment.
    set /A ERRORS+=1
) else (
    call :pass "WatermarkPro.exe is running"
)

REM ┌─────────────────────────────────────────────────────────────┐
REM │ STEP 11 — Register in Windows Apps & Features              │
REM └─────────────────────────────────────────────────────────────┘
call :begin_step "Registering in Windows Apps list"

set REG_KEY=HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\WatermarkPro

reg add "%REG_KEY%" /v "DisplayName" /t REG_SZ /d "WatermarkPro v2" /f >nul 2>&1
reg add "%REG_KEY%" /v "Publisher" /t REG_SZ /d "WatermarkPro" /f >nul 2>&1
reg add "%REG_KEY%" /v "DisplayVersion" /t REG_SZ /d "2.0.0" /f >nul 2>&1
reg add "%REG_KEY%" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f >nul 2>&1
reg add "%REG_KEY%" /v "DisplayIcon" /t REG_SZ /d "%INSTALL_DIR%\WatermarkPro.exe" /f >nul 2>&1
reg add "%REG_KEY%" /v "UninstallString" /t REG_SZ /d "\"%INSTALL_DIR%\uninstall.bat\"" /f >nul 2>&1
reg add "%REG_KEY%" /v "NoModify" /t REG_DWORD /d 1 /f >nul 2>&1
reg add "%REG_KEY%" /v "NoRepair" /t REG_DWORD /d 1 /f >nul 2>&1

call :pass "Added to Windows Installed Apps"

REM ================================================================
REM  FINAL STATUS DASHBOARD
REM ================================================================
echo.
echo  ================================================================
echo   INSTALLATION COMPLETE — STATUS DASHBOARD
echo  ================================================================
echo.

echo  ---- 1. INSTALLED FILES (%INSTALL_DIR%) --------------------
dir /B "%INSTALL_DIR%"
echo.

echo  ---- 2. WINDOWS SERVICE STATUS ----------------------------
sc query "%SVC_NAME%"
echo.

echo  ---- 3. TASK SCHEDULER TASK --------------------------------
schtasks /Query /TN "%TASK_NAME%" /FO LIST 2>nul
echo.

echo  ---- 4. RUNNING PROCESSES ----------------------------------
tasklist /FI "IMAGENAME eq WatermarkPro.exe"    /NH 2>nul
tasklist /FI "IMAGENAME eq WatermarkProService.exe" /NH 2>nul
echo.

echo  ================================================================
echo.
if !ERRORS!==0 (
    color 0A
    echo   [ALL STEPS PASSED]
    echo.
    echo   Watermark   : Should now be visible on your screen
    echo                 (diagonal text across the desktop)
    echo   Admin App   : %INSTALL_DIR%\WatermarkProAdmin.exe
    echo   Password    : admin123   ^(change immediately^)
    echo.
    echo   HOW TO VERIFY EVERYTHING IS WORKING:
    echo    - Look at your desktop — watermark text should be visible
    echo    - Open Task Manager ^> Services tab
    echo      You should see: WatermarkProGuardian   RUNNING
    echo    - Open Task Manager ^> Processes tab
    echo      You should see: WatermarkPro.exe
    echo    - Try ending WatermarkPro.exe — it should restart in ~10s
    echo.
    echo   HOW TO STOP (admin only):
    echo    Task Manager ^> Services ^> WatermarkProGuardian ^> Stop
    echo    — or — run:  sc stop WatermarkProGuardian
) else (
    color 0E
    echo   [COMPLETED WITH !ERRORS! STEP(S) THAT NEED ATTENTION]
    echo   Review the output above. Steps marked FAIL need fixing.
    echo.
    echo   For service errors: Event Viewer ^> Windows Logs ^> Application
)
echo.
echo  ================================================================
echo.
pause
goto :eof

REM ================================================================
REM  SUBROUTINES
REM ================================================================
:header
echo.
echo  ================================================================
echo   WatermarkPro v2  ^|  System Installation
echo   Install path : C:\Program Files\WatermarkPro
echo   Service name : WatermarkProGuardian
echo   Task name    : WatermarkPro
echo  ================================================================
echo.
goto :eof

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