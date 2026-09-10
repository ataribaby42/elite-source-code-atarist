# Bundled Windows build tools

These native Windows x64 executables are used automatically by root `build.bat`
and `python src/build.py`:

| Executable | Version | Purpose |
| --- | --- | --- |
| `vasmm68k_mot.exe` | vasm 2.0f | MC68000 assembler, Motorola syntax; bin, TOS, vobj and ELF output |
| `vlink.exe` | vlink 0.18a | Linker |

They were built with MSVC using `/MT`, so no separate Visual C++ runtime package
is needed. A normal game build requires only Windows and Python 3.10+; it does
not download or compile these tools. Keep this folder beside `src` when copying
the project. Intermediate files stay in `src/build`; game output goes to root
`output/ELITE` and `output/ELITE.ST`.

The original source archives are preserved in `src/vendor/vasm.tar.gz` and
`src/vendor/vlink.tar.gz`. Their versions, source URLs and SHA-256 hashes are
recorded in `src/tools/toolchain.json`. The upstream Legal sections are included
in `vasm-LICENSE.txt` and `vlink-LICENSE.txt`.

To rebuild the tools themselves, run `src/tools/setup-toolchain.ps1` with Visual
Studio 2022 C++ Build Tools and the Windows SDK installed. It compiles under
`src/build/toolchain` and refreshes these two executables. Custom binaries can also be
selected with `build.bat -Vasm <path> -Vlink <path>` or the corresponding
`--vasm` and `--vlink` Python options.
