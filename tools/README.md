# Bundled build tools

These executables are used automatically by root `build_atari.bat`,
`build_amiga.bat`, `build_orig.bat`, their `.sh` counterparts and the
corresponding source-tree Python builds:

| Executable | Host | Version | Purpose |
| --- | --- | --- | --- |
| `vasmm68k_mot.exe` | Windows x64 | vasm 2.0f | MC68000 assembler, Motorola syntax; bin, TOS, vobj and ELF output |
| `vlink.exe` | Windows x64 | vlink 0.18a | Linker |
| `vasmm68k_mot` | Linux x86-64 | vasm 2.0f | The same assembler |
| `vlink` | Linux x86-64 | vlink 0.18a | The same linker |

The Windows pair was built with MSVC using `/MT`, so no separate Visual C++ runtime
package is needed; the Linux pair was built with gcc and needs only libc and libm. The
two produce identical game files. A normal game build requires Windows or Linux and
Python 3.10+; it does not download or compile these tools. Keep this folder in the
project root when copying the project. Intermediate files stay in each source tree's
`build` directory; game output goes to `output_atari`, `output_amiga` or `output_orig`
respectively.

The original source archives are preserved in `src_atari/vendor/vasm.tar.gz` and
`src_atari/vendor/vlink.tar.gz`. Their versions, source URLs and SHA-256 hashes are
recorded in `src_atari/tools/toolchain.json`. The upstream Legal sections are included
in `vasm-LICENSE.txt` and `vlink-LICENSE.txt`.

To rebuild the Windows tools, run `src_atari/tools/setup-toolchain.ps1` with Visual
Studio 2022 C++ Build Tools and the Windows SDK installed. It compiles under
`src_atari/build/toolchain` and refreshes those two executables. The Linux pair comes
from the same vendored archives: `make CPU=m68k SYNTAX=mot` in the vasm source and
`make` in the vlink source. Custom binaries can also be selected with
`build_atari.bat -Vasm <path> -Vlink <path>`, with `--vasm` and `--vlink` on the Python
and shell builds, or with `ELITE_VASM` and `ELITE_VLINK` in the environment.
