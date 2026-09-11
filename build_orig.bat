@echo off
call "%~dp0src_orig\build.bat" %*
exit /b %errorlevel%
