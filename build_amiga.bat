rem Persistent default options live here; anything on the command line overrides
rem them, last occurrence winning. "all" builds every delivered image: one call
rem each, named by its outputname.
if /i "%~1"=="all" goto release
call "%~dp0src_amiga\build.bat" outputname=ELITE noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes altgfx=no %*
call "%~dp0src_amiga\build.bat" outputname=ELITE_ALT noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes altgfx=yes %*
exit /b %errorlevel%

:release
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE                         altgfx=no  frame=yes display=pal
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE.WIDE.PAL                altgfx=no  frame=no  display=pal            frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE.WIDE.NTSC               altgfx=no  frame=no  display=ntsc           frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE.WIDE.PAL-HIRES          altgfx=no  frame=no  display=pal-hires      frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE.WIDE.NTSC-HIRES         altgfx=no  frame=no  display=ntsc-hires     frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE.WIDE.PAL-HIRESLACE      altgfx=no  frame=no  display=pal-hireslace  frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE.WIDE.NTSC-HIRESLACE     altgfx=no  frame=no  display=ntsc-hireslace frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE_ALT                     altgfx=yes frame=yes display=pal
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE_ALT.WIDE.PAL            altgfx=yes frame=no  display=pal            frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE_ALT.WIDE.NTSC           altgfx=yes frame=no  display=ntsc           frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE_ALT.WIDE.PAL-HIRES      altgfx=yes frame=no  display=pal-hires      frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE_ALT.WIDE.NTSC-HIRES     altgfx=yes frame=no  display=ntsc-hires     frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE_ALT.WIDE.PAL-HIRESLACE  altgfx=yes frame=no  display=pal-hireslace  frametime=yes
call "%~dp0src_amiga\build.bat" noprotect=yes commander=default laser=singlebeam aifiresound=no scannerlogo=no fastdraw=yes outputname=ELITE_ALT.WIDE.NTSC-HIRESLACE altgfx=yes frame=no  display=ntsc-hireslace frametime=yes
exit /b %errorlevel%
