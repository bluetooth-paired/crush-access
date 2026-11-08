@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -c "import sys; sys.exit(not sys.version_info >= (3, 10))" >nul 2>nul
if not errorlevel 1 goto run_python
py -3 -c "import sys; sys.exit(not sys.version_info >= (3, 10))" >nul 2>nul
if not errorlevel 1 goto run_py
echo [ERROR] Install Python 3.10 or later to launch the preview.
pause
exit /b 1

:run_py
py -3 local_server.py
if errorlevel 1 (pause & exit /b 1)
exit /b 0

:run_python
python local_server.py
if errorlevel 1 (pause & exit /b 1)
