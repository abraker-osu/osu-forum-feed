@echo off

if "%VIRTUAL_ENV%" == "" (
    py -m venv venv
    venv\\Scripts\\activate.bat
)

py -m pip install --upgrade pip
pip install -r requirements.txt
