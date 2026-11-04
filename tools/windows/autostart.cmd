@echo off
rem Agent Status Bar: start the daemon when you sign in to Windows.
rem Needed for the claude.ai browser extension (the chat has no hooks to start the daemon).
rem   autostart.cmd          turn on and start the daemon now
rem   autostart.cmd remove   turn off
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LINK=%STARTUP%\agent-status-daemon.cmd"

if /i "%~1"=="remove" (
  del "%LINK%" 2>nul
  echo Autostart is off. The daemon keeps running until you sign out.
  exit /b 0
)

where pyw >nul 2>nul || (
  echo The Python launcher "pyw" was not found. Install Python from python.org and run this again.
  exit /b 1
)

> "%LINK%" echo @start "" pyw -3 "%ROOT%\host\daemon.py"
start "" pyw -3 "%ROOT%\host\daemon.py"
echo Autostart is on: the daemon starts with Windows, without a window.
echo It is running now too. Check: http://127.0.0.1:8765/
echo To turn it off: tools\windows\autostart.cmd remove
