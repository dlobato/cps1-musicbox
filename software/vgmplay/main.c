#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>

#include <irq.h>
#include <libbase/uart.h>
#include <libbase/console.h>
#include <liblitedram/sdram.h>
#include <generated/csr.h>

#include "ym2151.h"
#include "msm6295.h"

#define VGM_SAMPLE_RATE 44100
#define TIMER0_TICKS ((uint32_t)(CONFIG_CLOCK_FREQUENCY) / (VGM_SAMPLE_RATE))

const uint32_t vgm_sample_rate = 44100;
const uint32_t sample_to_ms_q0_16 = (uint32_t)((1/44.1) * 65536);
const uint32_t timer0_ticks = (uint32_t)(CONFIG_CLOCK_FREQUENCY / vgm_sample_rate);


#ifndef VGM_DATA_FILE
#error VGM_DATA_FILE undefined
#endif

struct vgm_header {
    uint32_t eof_offset;
    uint32_t n_samples;
    uint32_t loop_n_samples;
    uint32_t loop_offset;
    uint32_t vgm_data_offset;
};


extern const uint8_t vgm_data[];
extern const uint32_t vgm_data_size;

struct vgm_header vgm_header;
uint32_t vgm_current_offset;
uint32_t vgm_current_sample;
bool playing = false;

void timer0_isr(void);
void timer0_enable(uint32_t, uint32_t);
void timer0_disable(void);

uint32_t parse_uint32(const uint8_t *buffer, const size_t buffer_size, const size_t offset);
uint32_t parse_header(const uint8_t *vgm_data, const size_t vgm_data_size, struct vgm_header *vgm_header);


/*-----------------------------------------------------------------------*/
/* Uart                                                                  */
/*-----------------------------------------------------------------------*/

static bool read_newline_nonblock(void)
{
	char c;

	if(readchar_nonblock()) {
		c = getchar();
        if (c == '\r' || c == '\n') return true;
	}

	return false;
}

/*-----------------------------------------------------------------------*/
/* Help                                                                  */
/*-----------------------------------------------------------------------*/

static void help(void)
{
	puts("\nLiteX vgmplay "__DATE__" "__TIME__"\n");
	puts("Enter to play/stop");
}


static void enable_output(bool enable) {
#ifdef CSR_DAO_DUMP_BASE
    dao_dump_control_en_write(enable);
#endif
}

static void play_cmd(void)
{
    playing = true;
    enable_output(true);
	timer0_enable(TIMER0_TICKS, TIMER0_TICKS);
}

static void stop_cmd(void)
{
    playing = false;
    enable_output(false);
	timer0_disable();
}


void timer0_enable(uint32_t load, uint32_t reload) {
    timer0_en_write(0);
    
    timer0_load_write(load);
    timer0_reload_write(reload);

    timer0_en_write(1);
	
    timer0_ev_pending_write(timer0_ev_pending_read());//clear event pending
	irq_setmask(irq_getmask() | (1 << TIMER0_INTERRUPT));
    timer0_ev_enable_write(1);
}

void timer0_disable(void) {
    timer0_ev_enable_write(0);
    timer0_en_write(0);
}

uint32_t parse_uint32(const uint8_t *buffer, const size_t buffer_size, const size_t offset) {
    assert(offset + 4 < buffer_size);

    uint32_t result = buffer[offset];
    result |= buffer[offset + 1] << 8;
    result |= buffer[offset + 2] << 16;
    result |= buffer[offset + 3] << 24;
    return result;
}


// follows https://vgmrips.net/wiki/VGM_Specification
// TODO: check only YM2151 and OKIM6295 clocks are present
uint32_t parse_header(const uint8_t *vgm_data, const size_t vgm_data_size, struct vgm_header *vgm_header) {
    // 0x04: Eof offset (32 bits)
    vgm_header->eof_offset = parse_uint32(vgm_data, vgm_data_size, 0x04) + 0x04;
    if (vgm_data_size < vgm_header->eof_offset) {
        fprintf(stderr, "Total size for file is too small; file may be truncated\n");
        return 0;
    }

    // 0x08: Version number (32 bits)
    uint32_t version = parse_uint32(vgm_data, vgm_data_size, 0x08);
    if (version > 0x171)
        fprintf(stderr, "Warning: version > 1.71 detected, some things may not work\n");

    // 0x14: GD3 offset (32 bits) //TODO: parse GD3 tag
    // uint32_t gd3_offset = parse_uint32(vgm_data, vgm_data_size, 0x14) + 0x14;
    
    // 0x18: Total # samples (32 bits)
    vgm_header->loop_n_samples = parse_uint32(vgm_data, vgm_data_size, 0x18);

    // 0x1C: Loop offset (32 bits)
    vgm_header->loop_offset = parse_uint32(vgm_data, vgm_data_size, 0x1C) + 0x1C;

    // 0x30: YM2151/YM2164 clock (32 bits)
    if (version >= 0x110 && parse_uint32(vgm_data, vgm_data_size, 0x30) == 0) {
        fprintf(stderr, "Warning: vgm file doesn't have YM2151. Nothing to play here...\n");
        return 0;
    }

    //TODO: parse 0x98: OKIM6295 clock (32 bits)
        // Input clock rate in Hz for the OKIM6295 chip. A typical value is
        // 8000000. It should be 0 if there is no OKIM6295 chip used.
        // Set bit 31 (0x80000000) to denote the status of pin 7.

    // 0x34: VGM data offset (32 bits)
    vgm_header->vgm_data_offset = parse_uint32(vgm_data, vgm_data_size, 0x34) + 0x34;
    if (version < 0x150) {
        vgm_header->vgm_data_offset = 0x40;
    }

    return vgm_header->vgm_data_offset;
}

void timer0_isr(void) {
    static uint32_t delay = 0;

	timer0_ev_pending_write(timer0_ev_pending_read());//clear event pending
    vgm_current_sample++;

    if (delay == 0) {
        uint8_t cmd = vgm_data[vgm_current_offset++];
        switch (cmd) {
            // YM2151, write value dd to register aa
            case 0x54:
                ym2151_write_cmd(vgm_data[vgm_current_offset], vgm_data[vgm_current_offset + 1]);
                vgm_current_offset += 2;
                break;

            // Wait n samples, n can range from 0 to 65535 (approx 1.49 seconds)
            case 0x61:
                delay = vgm_data[vgm_current_offset] | (vgm_data[vgm_current_offset + 1] << 8);
                vgm_current_offset += 2;
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
                vgm_current_offset = vgm_header.loop_offset;
                break;

            // data block: TODO
            case 0x67:
                if (vgm_data[vgm_current_offset++] == 0x66) {
                    uint8_t type = vgm_data[vgm_current_offset++];
                    uint32_t size = parse_uint32(vgm_data, vgm_data_size, vgm_current_offset);
                    vgm_current_offset += 4;
                    
                    if (type == 0x8B) {//8B = OKIM6295 ROM data
                        uint32_t data_block_offset = vgm_current_offset;

                        uint32_t rom_size = parse_uint32(vgm_data, vgm_data_size, data_block_offset);
                        (void)rom_size;
                        data_block_offset += 4;
                        uint32_t rom_start_address = parse_uint32(vgm_data, vgm_data_size, data_block_offset);
                        data_block_offset += 4;
                        size_t rom_block_size = size - 8;
                        memcpy((void *)(jt6295_rom_dma_base_read() + rom_start_address), vgm_data + data_block_offset, rom_block_size);
                    }

                    vgm_current_offset += size;
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
                {
                    static bool trace_enabled = false;
                    static uint32_t marker = 0;
                    if (!trace_enabled) sim_trace_enable_write(1);
                    sim_marker_marker_write(marker++);
                }
                msm6295_write_cmd(vgm_data[vgm_current_offset], vgm_data[vgm_current_offset + 1]);
                vgm_current_offset += 2;
                break;

            default:
                break;
        }

        return;
    }

    delay--;
}


//-------------------------------------------------
//  main - program entry point
//-------------------------------------------------

int main(int argc, char *argv[]) {
#ifdef CONFIG_CPU_HAS_INTERRUPT
    irq_setmask(0);
    irq_setie(1);
#endif
    uart_init();


    int sdr_ok = sdram_init();
    if (sdr_ok != 1)
		fprintf(stderr, "Memory initialization failed\n");


    // TODO: implement vgz files support
    // check the ID
    if (vgm_data_size < 64 || vgm_data[0] != 'V' || vgm_data[1] != 'g' || vgm_data[2] != 'm' ||
        vgm_data[3] != ' ') {
        fprintf(stderr, "File '%s' does not appear to be a valid VGM file\n", VGM_DATA_FILE);
        return -1;
    }

    // parse the header
    vgm_current_offset = parse_header(vgm_data, vgm_data_size, &vgm_header);
    if (vgm_current_offset == 0) {
        fprintf(stderr, "Wrong header found on file %s\n", VGM_DATA_FILE);
        return -1;
    }
    vgm_current_sample = 0;

    jt51_control_reset_write(0);
    jt6295_control_reset_write(0);

    mixer_control_enable_fm_write(1);
    mixer_control_enable_pcm_write(1);
    mixer_control_pcm_level_write(3);

    help();

	while(1) {
        if (playing) {
            printf("\rplaying %s %lu ms", "blanka", (vgm_current_sample * sample_to_ms_q0_16) >> 16);
        }

        if (read_newline_nonblock()) {
            playing = !playing;
            if (playing)
                play_cmd();
            else
                stop_cmd();
        }
	}

    return 0;
}