#include "ym2151.h"
#include <generated/csr.h>

void ym2151_init(void) {
    jt51_control_reset_write(0);
}

void ym2151_write_cmd(uint8_t addr, uint8_t data) {
    // wait ready
    while (jt51_dout_read() & 0x80) {
    }

    // write addr
    jt51_control_wr_n_write(0);
    jt51_control_a0_write(0);
    jt51_din_write(addr);
    jt51_control_cs_n_write(0);  // toogle CS
    jt51_control_cs_n_write(1);
    jt51_control_a0_write(1);

    // write data
    jt51_din_write(data);
    jt51_control_cs_n_write(0);  // toogle CS
    jt51_control_cs_n_write(1);
    jt51_control_wr_n_write(1);
}