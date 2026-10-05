@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3.12 -c "import sys" >nul 2>nul
if errorlevel 1 goto use_launcher
py -3.12 run.py %*
goto finished
:use_launcher
py -3 run.py %*
goto finished
:use_python
where python >nul 2>nul
if errorlevel 1 goto missing_python
python run.py %*
goto finished
:missing_python
echo Python not found. Install Python 3.12 from https://www.python.org/downloads/windows/
echo During installation enable Add python.exe to PATH, then run this file again.
pause
exit /b 1
:finished
set "relay_exit=%errorlevel%"
if not "%relay_exit%"=="0" pause
exit /b %relay_exit%
