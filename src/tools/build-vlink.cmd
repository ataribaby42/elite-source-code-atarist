@echo off
setlocal
for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "ELITE_VS=%%i"
if not defined ELITE_VS exit /b 1
call "%ELITE_VS%\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0..\build\toolchain\vlink"
if errorlevel 1 exit /b 1
if not exist obj-msvc mkdir obj-msvc
pushd obj-msvc
cl /nologo /O2 /MT /wd4996 /I.. /Fe:..\vlink.exe ..\main.c ..\support.c ..\errors.c ..\linker.c ..\dir.c ..\targets.c ..\ar.c ..\ldscript.c ..\pmatch.c ..\expr.c ..\elf.c ..\tosopts.c ..\t_*.c ..\version.c /link kernel32.lib user32.lib
set "ELITE_RESULT=%errorlevel%"
popd
popd
exit /b %ELITE_RESULT%
