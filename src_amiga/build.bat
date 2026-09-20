@echo off
rem Windows entry point: find an interpreter and run build.py.
setlocal enabledelayedexpansion
set "ELITE_PYTHON="
if /i "%~1"=="-Python" (
    set "ELITE_PYTHON=%~2"
    goto :run
)
for /f "delims=" %%I in ('where python 2^>nul') do (
    set "ELITE_CANDIDATE=%%I"
    rem The Microsoft Store stub opens the Store instead of running Python.
    if "!ELITE_CANDIDATE:WindowsApps=!"=="!ELITE_CANDIDATE!" (
        set "ELITE_PYTHON=%%I"
        goto :run
    )
)
where py >nul 2>&1 && set "ELITE_PYTHON=py -3"
:run
if not defined ELITE_PYTHON (
    echo build.bat: Python 3.10 or later is required. Install it, or pass
    echo            -Python "C:\path\python.exe" as the first argument.
    exit /b 1
)
%ELITE_PYTHON% -B "%~dp0build.py" %*
exit /b %errorlevel%
