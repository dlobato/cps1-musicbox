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
#include "timer.h"
#include "vgm.h"

const uint32_t vgm_sample_rate = 44100;
const uint32_t sample_to_ms_q0_16 = (uint32_t)((1/44.1) * 65536);
const uint32_t timer0_ticks = (uint32_t)(CONFIG_CLOCK_FREQUENCY / vgm_sample_rate);


#ifndef VGM_DATA_FILE
#error VGM_DATA_FILE undefined
#endif

extern const uint8_t vgm_data[];
extern const uint32_t vgm_data_size;

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
    enable_output(true);
	timer0_enable();
}

static void stop_cmd(void)
{
    enable_output(false);
	timer0_disable();
}


//-------------------------------------------------
//  main - program entry point
//-------------------------------------------------

int main(int argc, char *argv[]) {
    struct vgm_header vgm_header;

#ifdef CONFIG_CPU_HAS_INTERRUPT
    irq_setmask(0);
    irq_setie(1);
#endif
    uart_init();

    // parse the header
    if (!parse_header(vgm_data, vgm_data_size, &vgm_header)) {
        fprintf(stderr, "Failed to parse header on file %s\n", VGM_DATA_FILE);
        return -1;
    }
    
    struct timer_ctx timer_ctx = {
        .current_offset = vgm_header.vgm_data_offset,
        .current_sample = 0,
        .vgm_buffer = vgm_data,
        .vgm_buffer_size = vgm_data_size,
        .vgm_header = &vgm_header
    };

    ym2151_init();
    msm6295_init();
    timer0_init(timer0_ticks, &timer_ctx);

    mixer_control_enable_fm_write(1);
    mixer_control_enable_pcm_write(1);
    mixer_control_pcm_level_write(2);

    help();

    bool playing = false;

	while(1) {
        if (playing) {
            printf("\rplaying %s %lu ms", VGM_DATA_FILE, (timer_ctx.current_sample * sample_to_ms_q0_16) >> 16);
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