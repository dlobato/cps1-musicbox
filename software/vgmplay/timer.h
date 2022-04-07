#pragma once
#include <stdint.h>
#include <stddef.h>
#include "vgm.h"

struct timer_ctx {
    uint32_t current_sample;
    uint32_t current_offset;
    const struct vgm_header *vgm_header;
    const uint8_t *vgm_buffer;
    const size_t vgm_buffer_size;
};

void timer0_isr(void);
void timer0_init(const uint32_t ticks, struct timer_ctx *ctx);
void timer0_enable(void);
void timer0_disable(void);