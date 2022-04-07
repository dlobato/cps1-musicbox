#include "msm6295.h"
#include <generated/csr.h>
#include <generated/soc.h>
#include <string.h>

#include <generated/csr.h>

uint8_t msm6295_rom[JT6295_ROM_SIZE] __attribute__ ((section (".msm6295_rom")));

void msm6295_init(void) {
    jt6295_rom_dma_base_write((uint32_t)msm6295_rom);
    jt6295_control_reset_write(0);
    jt6295_control_enable_filter_write(1);
}

uint8_t *msm6295_write_rom(size_t rom_addr, const uint8_t *src, size_t n) {
    if (rom_addr > JT6295_ROM_SIZE) return 0;
    
    return memcpy((void *)(msm6295_rom + rom_addr), src, n);
}

void msm6295_write_cmd(uint8_t addr, uint8_t data) {
    (void)addr;
    // wait ready TODO: check if there's any busy bit on dout
    // while (jt6295_dout_read() & 0x80) {
    // }

    // write addr
    jt6295_control_wr_n_write(0);
    jt6295_din_write(data);
    jt6295_control_wr_n_write(1);
}