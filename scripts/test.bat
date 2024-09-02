@echo off

if "%VIRTUAL_ENV%" == "" (
    python -m venv venv
    if %errorlevel% neq 0 exit /b %errorlevel%

    call venv\\Scripts\\activate.bat
    if %errorlevel% neq 0 exit /b %errorlevel%
)

python src\\tests\\run.py %*
