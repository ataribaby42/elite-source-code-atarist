# Project rules

- Write all project documentation in English, including README files, technical notes, project instructions, and any new or updated documentation.
- The user handles all Git operations exclusively. Do not run any Git commands or use APIs or other tools to perform Git operations. This includes reading status, diffs, and history, as well as init, add/staging, commit, push, pull, fetch, checkout, branch management, and configuration changes. Do not create, modify, or delete the `.git` directory or its contents.
- The `src-orig` directory contains the original source code. It is read-only: do not modify, add, delete, or rename any files in it.
- All new and modified source code belongs in `src`.
- If original code needs changes, copy it from `src-orig` to `src` first and make changes only in `src`.
- Keep the project root tidy: do not place loose generated or temporary files there. Intermediate files and logs belong in `src/build`; distribution files belong in the root `output` directory (`output/ELITE` and `output/ELITE.ST`). Run the assembler and linker with a working directory under `src` and an explicit `-o` output path, including when trying out the tools, so a default `a.out` is never created in the root.
- The root `tools` directory contains the bundled Windows vasm assembler and vlink linker executables and their license information. The build uses these tools by default; their build scripts and sources remain under `src`.
- The root `build.bat` is the entry point requested by the user. It forwards optional build parameters to scripts in `src`; the build logic remains in `src`.
