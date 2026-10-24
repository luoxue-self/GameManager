@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "APP="
for %%f in ("%~dp0*.exe") do if not defined APP set "APP=%%~ff"
if not defined APP (
  echo [ERROR] ?????????.exe not found next to this file.
  pause
  exit /b 1
)
"%APP%" --reset-password
