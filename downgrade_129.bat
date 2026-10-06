@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0downgrade_129.ps1" %*
pause
