@echo off

if "%VIRTUAL_ENV%" == "" (
    python -m venv venv
    if %errorlevel% neq 0 exit /b %errorlevel%

    call venv\\Scripts\\activate.bat
    if %errorlevel% neq 0 exit /b %errorlevel%
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
