@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Jotter -- build script
echo ============================================================

:: ── 1. Install / upgrade PyInstaller ──────────────────────────
echo.
echo [1/3] Installing PyInstaller...
pip install --upgrade pyinstaller --quiet
if errorlevel 1 ( echo ERROR: pip failed. Is Python in your PATH? & pause & exit /b 1 )

:: ── 2. Build the EXE with PyInstaller ─────────────────────────
echo.
echo [2/3] Building Jotter.exe with PyInstaller...
python -m PyInstaller --clean jotter.spec
if errorlevel 1 ( echo ERROR: PyInstaller failed. & pause & exit /b 1 )

:: ── 3. Compile the installer with Inno Setup ──────────────────
echo.
echo [3/3] Compiling installer with Inno Setup...

:: Try common Inno Setup locations (5, 6, 7)
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 7\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 7\ISCC.exe"
if exist "C:\Program Files\Inno Setup 7\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 7\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 5\ISCC.exe"

if "%ISCC%"=="" (
    echo.
    echo  Inno Setup not found.
    echo  Download it free from: https://jrsoftware.org/isdl.php
    echo  Then re-run this script.
    echo.
    echo  PyInstaller output is in: dist\Jotter.exe
    pause
    exit /b 0
)

%ISCC% jotter.iss
if errorlevel 1 ( echo ERROR: Inno Setup compile failed. & pause & exit /b 1 )

echo.
echo ============================================================
echo  Done!  Installer is at:  installer\JotterSetup.exe
echo ============================================================
pause
