@echo off


if not exist venv (
    python -m venv venv
    if %errorlevel% neq 0 exit /b %errorlevel%
)

if not exist venv (
    echo Failed to create venv!
    if %errorlevel% neq 0 exit /b %errorlevel%
)

if "%VIRTUAL_ENV%" == "" (
    call venv\\Scripts\\activate.bat
    if %errorlevel% neq 0 exit /b %errorlevel%
)

if "%VIRTUAL_ENV%" == "" (
    echo Failed to activate venv!
    if %errorlevel% neq 0 exit /b %errorlevel%
)

python src\\run.py
