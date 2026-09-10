@echo off
rem Add default build options to the call below, before the forwarded arguments.
rem Example for a future option: call "%~dp0src\build.bat" option1=yes %*
call "%~dp0src\build.bat" %*
exit /b %errorlevel%
