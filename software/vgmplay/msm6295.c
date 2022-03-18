#include "msm6295.h"

#include <generated/csr.h>

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