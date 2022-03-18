    .section .rodata
    .global vgm_data
    .type   vgm_data, @object
    .balign  4
vgm_data:
    .incbin VGM_DATA_FILE
vgm_data_end:
    .global vgm_data_size
    .type   vgm_data_size, @object
    .balign  4
vgm_data_size:
    .int    vgm_data_end - vgm_data