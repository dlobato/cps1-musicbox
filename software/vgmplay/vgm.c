#include "vgm.h"
#include <stdio.h>
#include <assert.h>

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
bool parse_header(const uint8_t *vgm_data, const size_t vgm_data_size, struct vgm_header *vgm_header) {
    if (vgm_data_size < 64 || vgm_data[0] != 'V' || vgm_data[1] != 'g' || vgm_data[2] != 'm' ||
        vgm_data[3] != ' ') {
        fprintf(stderr, "Invalid valid VGM file\n");
        return false;
    }

    // 0x04: Eof offset (32 bits)
    vgm_header->eof_offset = parse_uint32(vgm_data, vgm_data_size, 0x04) + 0x04;
    if (vgm_data_size < vgm_header->eof_offset) {
        fprintf(stderr, "Total size for file is too small; file may be truncated\n");
        return false;
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
        return false;
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

    return true;
}