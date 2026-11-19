call "%~dp0src_atari\build.bat" outputname=ELITE noprotect=yes commander=default laser=singlebeam scannerlogo=no altgfx=no %*
if not "%errorlevel%"=="0" exit /b %errorlevel%
call "%~dp0src_atari\build.bat" outputname=ELITE_ALT noprotect=yes commander=default laser=singlebeam scannerlogo=no altgfx=yes %*
if not "%errorlevel%"=="0" exit /b %errorlevel%
