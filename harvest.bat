@echo off
REM  STEWARD'S HARVEST — ingest recent arXiv onto the shelf. Resumable.
setlocal
cd /d "%~dp0"
echo.
echo   Steward begins harvesting recent arXiv (politely)...
echo.
where python >nul 2>nul
if %errorlevel%==0 ( python harvest.py %1 %2 & goto done )
where py >nul 2>nul
if %errorlevel%==0 ( py harvest.py %1 %2 & goto done )
echo   I could not find Python on this machine.
:done
echo.
pause
