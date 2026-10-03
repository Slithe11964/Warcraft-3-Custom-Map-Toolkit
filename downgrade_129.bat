@echo off
setlocal
rem Drag a Reforged-format .w3x map onto this file to make a 1.29.2 copy next to it.
rem Uses ..\FFERPG_0.9.7.3-r7.w3x as the template (map info, and the object fields Reforged leaves out).
set "HERE=%~dp0"
set "R7=%HERE%..\FFERPG_0.9.7.3-r7.w3x"
if "%~1"=="" (
  echo Drag a Reforged .w3x map onto this file.
  pause
  exit /b 1
)
if not exist "%R7%" (
  echo Missing template: %R7%
  pause
  exit /b 1
)
set "PY=python"
where py >nul 2>nul && set "PY=py"
set "OUT=%~dpn1-1.29.2.w3x"
if exist "%OUT%" (
  echo Replacing the old %~n1-1.29.2.w3x
  del "%OUT%"
)
%PY% "%HERE%tools\downgrade.py" "%~1" "%OUT%" --w3i-template "%R7%" --fill-from "%R7%" --name "%~n1 (1.29.2)"
if errorlevel 1 (
  echo.
  echo The conversion FAILED - see the messages above.
) else (
  echo.
  echo Done: %OUT%
)
pause
