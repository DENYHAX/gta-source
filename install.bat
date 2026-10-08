@echo off
rem CS:Source Mode for GTA San Andreas - installer launcher
setlocal
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python was not found. Install Python 3.11 or newer from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" in the installer.
  pause
  exit /b 1
)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
  echo Python 3.11 or newer is needed. Install it from https://www.python.org/downloads/
  pause
  exit /b 1
)
echo Installing the Python packages the installer needs (numpy, Pillow) ...
%PY% -m pip install --disable-pip-version-check --user -q -r installer\requirements.txt
%PY% installer\install.py %*
echo.
pause
