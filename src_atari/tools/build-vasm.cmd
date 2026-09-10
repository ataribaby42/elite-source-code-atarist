@echo off
setlocal
for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "ELITE_VS=%%i"
if not defined ELITE_VS (
  echo Visual Studio C++ Build Tools were not found.
  exit /b 1
)
call "%ELITE_VS%\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
pushd "%~dp0..\build\toolchain\vasm"
if errorlevel 1 exit /b 1
if not exist obj-msvc mkdir obj-msvc
pushd obj-msvc
cl /nologo /O2 /MT /wd4996 /I.. /I..\cpus\m68k /I..\syntax\mot /DOUTBIN /DOUTTOS /DOUTVOBJ /DOUTELF /Fe:..\vasmm68k_mot.exe ..\vasm.c ..\atom.c ..\expr.c ..\symtab.c ..\symbol.c ..\error.c ..\parse.c ..\reloc.c ..\hugeint.c ..\cond.c ..\listing.c ..\source.c ..\supp.c ..\dwarf.c ..\osdep.c ..\cpus\m68k\cpu.c ..\syntax\mot\syntax.c ..\output_*.c
set "ELITE_RESULT=%errorlevel%"
popd
popd
exit /b %ELITE_RESULT%
