@echo off
REM ===================================================================
REM  STEWARD — the one door. Visible on purpose: you see it run.
REM  No install, no download, no cloud. Python 3, and nothing else.
REM ===================================================================
setlocal
cd /d "%~dp0"
echo.
echo   Waking Steward...
echo.
where python >nul 2>nul
if %errorlevel%==0 ( python run.py & goto done )
where py >nul 2>nul
if %errorlevel%==0 ( py run.py & goto done )
echo   I could not find Python on this machine.
echo   Install Python 3 from python.org, then double-click this again.
:done
echo.
pause
