@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "merge_fx_sequences.py" --gui
  goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
  python "merge_fx_sequences.py" --gui
  goto :eof
)

echo Python not found. Please install Python 3 first.
pause
