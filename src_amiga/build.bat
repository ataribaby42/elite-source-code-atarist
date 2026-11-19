@echo off
rem Windows entry point: find an interpreter and run build.py.
setlocal enabledelayedexpansion
set "ELITE_PYTHON="
set "ELITE_PYTHON_ARGS="
rem Root wrappers prepend defaults, so -Python need not be the first argument.
:scan
if "%~1"=="" goto :select
if /i "%~1"=="-Python" (
    set "ELITE_PYTHON=%~2"
    if "%~2"=="" (
        echo build.bat: -Python requires an interpreter path.
        exit /b 1
    )
    shift /1
)
shift /1
goto :scan
:select
if defined ELITE_PYTHON goto :run
for /f "delims=" %%I in ('where python 2^>nul') do (
    set "ELITE_CANDIDATE=%%I"
    rem The Microsoft Store stub opens the Store instead of running Python.
    if "!ELITE_CANDIDATE:WindowsApps=!"=="!ELITE_CANDIDATE!" (
        set "ELITE_PYTHON=%%I"
        goto :run
    )
)
where py >nul 2>&1
if not errorlevel 1 (
    set "ELITE_PYTHON=py"
    set "ELITE_PYTHON_ARGS=-3"
)
:run
if not defined ELITE_PYTHON (
    echo build.bat: Python 3.10 or later is required. Install it, or pass
    echo            -Python "C:\path\python.exe".
    exit /b 1
)
"%ELITE_PYTHON%" %ELITE_PYTHON_ARGS% -B "%~dp0build.py" %*
exit /b %errorlevel%
