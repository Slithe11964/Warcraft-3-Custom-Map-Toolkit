@echo off
rem Drag a Reforged-format .w3x map onto this file to make a copy in a 1.29.2 subfolder.
rem The copy keeps the original filename and uses its basename as the in-game name.
rem Uses ..\FFERPG_0.9.7.3-r7.w3x as the template. Everything it prints is also saved in downgrade_log.txt.
setlocal
set "HERE=%~dp0"
set "LOG=%HERE%downgrade_log.txt"
call :main "%~1" > "%LOG%" 2>&1
type "%LOG%"
echo.
pause
exit /b

:main
if "%~1"=="" goto nomap
set "R7=%HERE%..\FFERPG_0.9.7.3-r7.w3x"
if not exist "%R7%" goto notemplate
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython
set "OUTDIR=%~dp1"
set "OUTDIR=%OUTDIR%1.29.2"
if not exist "%OUTDIR%\" mkdir "%OUTDIR%"
if not exist "%OUTDIR%\" goto nooutputdir
set "OUT=%OUTDIR%\%~nx1"
if exist "%OUT%" goto outputexists
echo Converting "%~nx1" with %PY% ...
%PY% "%HERE%tools\downgrade.py" "%~1" "%OUT%" --w3i-template "%R7%" --fill-from "%R7%" --name "%~n1"
if errorlevel 1 goto failed
echo.
echo Done: "%OUT%"
exit /b 0
:failed
echo.
echo The conversion FAILED. The messages above say why.
exit /b 1
:outputexists
echo Output already exists: "%OUT%". Move or rename that copy before converting again.
exit /b 1
:nooutputdir
echo Could not create output folder "%OUTDIR%".
exit /b 1
:nomap
echo Drag a Reforged .w3x map onto downgrade_129.bat (do not double-click it).
exit /b 1
:notemplate
echo Missing the template map "%R7%".
exit /b 1
:nopython
echo Python was not found. Install it from python.org and tick "Add Python to PATH".
exit /b 1
