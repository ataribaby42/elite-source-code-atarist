/* Preserve the module order and absolute addresses of ELITE.LNK. */
SECTIONS
{
  . = 0x12000;
  .text : { *(text) }
  .bss (NOLOAD) : {
    . = ALIGN(2);
    textscr = .;
    *(workspace)
    . = . + 3588;
    hyper_buffer = .;  . = . + 3 * 15 * 8;
    left_arm = .;      . = . + 200 * 2;
    right_arm = .;     . = . + 200 * 2;
    . = . + 32768 - (. & 0x7fff);
    other_screen = .;  . = . + 16384 * 2;
    save1_buffer = .;  . = . + 4096;
    max1 = .;
    save2_buffer = .;  . = . + 4096;
    max2 = .;
    bitmaps = .;       . = . + 146862;
    texture = .;       . = . + 24358;
    obj_data = .;      . = . + 20172;
    logo = .;          . = . + 16276;
    cockpit = .;       . = . + 13386;
    vars = .;
    . = . + var_size;
    ram_end = .;
  }
}
