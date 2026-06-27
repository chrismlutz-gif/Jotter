@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  Jotter -- Push to GitHub
echo ============================================================
echo.

:: Check git is available
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git not found in PATH.
    echo Install Git for Windows from https://git-scm.com
    pause & exit /b 1
)

:: Use Windows Credential Manager so token is saved after first use
git config --global credential.helper manager

:: Stage files
set FILES=editor.py jotter.ico jotter.spec jotter.iss build.bat push_to_github.bat README.md LICENSE .gitignore

if exist ".git" (
    echo Existing repo found -- committing update...
    echo.
    git add %FILES%
    git status
    echo.
    set /p MSG="Commit message: "
    if "!MSG!"=="" set MSG=Update Jotter
    git commit -m "!MSG!"
    if errorlevel 1 (
        echo Nothing to commit.
        pause & exit /b 0
    )
) else (
    echo No repo found -- initialising fresh...
    echo.
    git init -b main
    git config user.name "Chris Lutz"
    git config user.email "chrismlutz@gmail.com"
    git remote add origin https://github.com/chrismlutz-gif/Jotter.git
    git add %FILES%
    git status
    echo.
    git commit -m "Initial commit -- Jotter v1.0"
)

:: Push
echo.
echo Pushing to https://github.com/chrismlutz-gif/Jotter ...
echo.
echo NOTE: If prompted for a password, use a Personal Access Token -- NOT your GitHub password.
echo       Create one at: https://github.com/settings/tokens
echo       Click "Generate new token (classic)", tick "repo", copy the token, paste it here.
echo       Windows will save it so you won't be asked again.
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo Push failed. See note above about Personal Access Tokens.
) else (
    echo.
    echo Done! Live at: https://github.com/chrismlutz-gif/Jotter
)
echo.
pause
