@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Jotter -- build script
echo ============================================================

:: ── 1. Install / upgrade PyInstaller ──────────────────────────
echo.
echo [1/2] Installing PyInstaller...
pip install --upgrade pyinstaller --quiet
if errorlevel 1 ( echo ERROR: pip failed. Is Python in your PATH? & pause & exit /b 1 )

:: ── 2. Build the EXE with PyInstaller ─────────────────────────
echo.
echo [2/2] Building Jotter.exe with PyInstaller...
python -m PyInstaller --clean jotter.spec
if errorlevel 1 ( echo ERROR: PyInstaller failed. & pause & exit /b 1 )

echo.
echo ============================================================
echo  Done!  Jotter.exe is at:  dist\Jotter.exe
echo ============================================================
pause
