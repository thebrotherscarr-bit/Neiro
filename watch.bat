@echo off
REM  STEWARD'S WATCH — the sentinel + mind-window, in its own window.
setlocal
cd /d "%~dp0"
echo.
echo   Steward begins watching himself...
echo.
where python >nul 2>nul
if %errorlevel%==0 ( python watch.py %1 & goto done )
where py >nul 2>nul
if %errorlevel%==0 ( py watch.py %1 & goto done )
echo   I could not find Python on this machine.
:done
echo.
pause
