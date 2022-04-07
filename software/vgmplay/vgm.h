#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#define VGM_SAMPLE_RATE 44100


struct vgm_header {
    uint32_t eof_offset;
    uint32_t n_samples;
    uint32_t loop_n_samples;
    uint32_t loop_offset;
    uint32_t vgm_data_offset;
};

uint32_t parse_uint32(const uint8_t *buffer, const size_t buffer_size, const size_t offset);
bool parse_header(const uint8_t *vgm_data, const size_t vgm_data_size, struct vgm_header *vgm_header);