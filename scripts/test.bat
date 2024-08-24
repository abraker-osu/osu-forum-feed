@echo off

if "%VIRTUAL_ENV%" == "" (
    python -m venv venv
    if %errorlevel% neq 0 exit /b %errorlevel%

    venv\\Scripts\\activate.bat
    if %errorlevel% neq 0 exit /b %errorlevel%
)

python src\\test\run.py
