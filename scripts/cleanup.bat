@echo off


echo "Removing all __pycache__"
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s/q "%%d"

echo Removing "logs/..."
rd /s/q logs

echo Removing "cache/..."
rd /s/q cache

echo [ DONE ]
