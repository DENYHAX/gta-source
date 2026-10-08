@echo off
rem CS:Source Mode for GTA San Andreas - uninstaller
setlocal
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY set "PY=python"
%PY% installer\install.py --uninstall %*
echo.
pause
