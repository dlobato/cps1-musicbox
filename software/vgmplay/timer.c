#include "timer.h"
#include "ym2151.h"
#include "msm6295.h"
#include <irq.h>
#include <generated/csr.h>

struct timer_ctx *_ctx = 0;

void timer0_init(const uint32_t ticks, struct timer_ctx *ctx)
{
    _ctx = ctx;

    timer0_en_write(0);
    
    timer0_load_write(ticks);
    timer0_reload_write(ticks);
}

void timer0_enable(void) {
    timer0_en_write(1);
    timer0_ev_pending_write(timer0_ev_pending_read());//clear event pending
	irq_setmask(irq_getmask() | (1 << TIMER0_INTERRUPT));
    timer0_ev_enable_write(1);
}

void timer0_disable(void) {
    timer0_ev_enable_write(0);
    timer0_en_write(0);
}

void timer0_isr(void) {
    static uint32_t delay = 0;

	timer0_ev_pending_write(timer0_ev_pending_read());//clear event pending

    if (_ctx == 0) return;


    _ctx->current_sample++;

    if (delay == 0) {
#ifdef CSR_SIM_TRACE_BASE
        {
            static bool trace_enabled = false;
            static uint32_t marker = 0;

            if (!trace_enabled) sim_trace_enable_write(1);
            sim_marker_marker_write(marker++);
        }
#endif
        uint8_t cmd = _ctx->vgm_buffer[_ctx->current_offset++];
        switch (cmd) {
            // YM2151, write value dd to register aa
            case 0x54:
                ym2151_write_cmd(_ctx->vgm_buffer[_ctx->current_offset], _ctx->vgm_buffer[_ctx->current_offset + 1]);
                _ctx->current_offset += 2;
                break;

            // Wait n samples, n can range from 0 to 65535 (approx 1.49 seconds)
            case 0x61:
                delay = _ctx->vgm_buffer[_ctx->current_offset] | (_ctx->vgm_buffer[_ctx->current_offset + 1] << 8);
                _ctx->current_offset += 2;
                break;

            // wait 735 samples (60th of a second)
            case 0x62:
                delay = 735;
                break;

            // wait 882 samples (50th of a second)
            case 0x63:
                delay = 882;
                break;

            // end of sound data
            case 0x66:
                _ctx->current_offset = _ctx->vgm_header->loop_offset;
                break;

            // data block: TODO
            case 0x67:
                if (_ctx->vgm_buffer[_ctx->current_offset++] == 0x66) {
                    uint8_t type = _ctx->vgm_buffer[_ctx->current_offset++];
                    uint32_t size = parse_uint32(_ctx->vgm_buffer, _ctx->vgm_buffer_size, _ctx->current_offset);
                    _ctx->current_offset += 4;
                    
                    if (type == 0x8B) {//8B = OKIM6295 ROM data
                        uint32_t data_block_offset = _ctx->current_offset;

                        uint32_t rom_size = parse_uint32(_ctx->vgm_buffer, _ctx->vgm_buffer_size, data_block_offset);
                        (void)rom_size;
                        data_block_offset += 4;
                        uint32_t rom_start_address = parse_uint32(_ctx->vgm_buffer, _ctx->vgm_buffer_size, data_block_offset);
                        data_block_offset += 4;
                        size_t rom_block_size = size - 8;
                        msm6295_write_rom(rom_start_address, _ctx->vgm_buffer + data_block_offset, rom_block_size);
                    }

                    _ctx->current_offset += size;
                }
                break;

            case 0x70:
            case 0x71:
            case 0x72:
            case 0x73:
            case 0x74:
            case 0x75:
            case 0x76:
            case 0x77:
            case 0x78:
            case 0x79:
            case 0x7a:
            case 0x7b:
            case 0x7c:
            case 0x7d:
            case 0x7e:
            case 0x7f:
                delay = (cmd & 15) + 1;
                break;

            // aa dd: OKIM6295, write value dd to register aa
            case 0xb8:
                msm6295_write_cmd(_ctx->vgm_buffer[_ctx->current_offset], _ctx->vgm_buffer[_ctx->current_offset + 1]);
                _ctx->current_offset += 2;
                break;

            default:
                break;
        }

        return;
    }

    delay--;
}