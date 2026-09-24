/* Preserve the module order and absolute addresses of ELITE.LNK. */
SECTIONS
{
  . = 0x12000;
  .text : { *(text) }
  .bss (NOLOAD) : {
    . = ALIGN(2);
    textscr = .;
    *(workspace)
    . = . + 4094;
    hyper_buffer = .;  . = . + 3 * 15 * 8;
    left_arm = .;      . = . + 200 * 2;
    right_arm = .;     . = . + 200 * 2;
    . = . + 32768 - (. & 0x7fff);
    other_screen = .;  . = . + 16384 * 2;
    save1_buffer = .;  . = . + 4096;
    max1 = .;
    save2_buffer = .;  . = . + 4096;
    max2 = .;
    bitmaps = .;       . = . + 142778; /* PNG Cobra removed: 4084 masked bytes. */
    texture = .;       . = . + 24358;
    obj_data = .;      . = . + 20292;
    logo = .;          . = . + 16276;
    cockpit = .;       . = . + 13386;
    cockpit_end = .;
    /* Keep the cache outside the bounded cockpit input buffer. */
    *(ship_graphics)
    vars = .;
    . = . + var_size;
    ram_end = .;
  }
}
