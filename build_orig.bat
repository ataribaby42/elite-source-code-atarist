@echo off
call "%~dp0src-orig\build.bat" %*
exit /b %errorlevel%
