@echo off
setlocal
cd /d "%~dp0"
set "BSA_SETUP_PYTHON="
if exist ".venv\Scripts\python.exe" set "BSA_SETUP_PYTHON=%CD%\.venv\Scripts\python.exe"
if not defined BSA_SETUP_PYTHON if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set "BSA_SETUP_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if defined BSA_SETUP_PYTHON goto found
py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12)" >nul 2>&1
if not errorlevel 1 (
  py -3.12 "%~dp0scripts\bootstrap.py" %*
  goto result
)
python -c "import sys; assert sys.version_info[:2] == (3,12)" >nul 2>&1
if not errorlevel 1 (
  python "%~dp0scripts\bootstrap.py" %*
  goto result
)
echo CPython 3.12 is required. Install Python 3.12, then run Setup.cmd again.
exit /b 1
:found
"%BSA_SETUP_PYTHON%" "%~dp0scripts\bootstrap.py" %*
:result
if errorlevel 1 (
  echo Setup failed. See the error above. Existing files have been preserved.
  exit /b 1
)
echo Setup complete. See .bsa\setup-result.json and docs\INSTALL.md.
exit /b 0
