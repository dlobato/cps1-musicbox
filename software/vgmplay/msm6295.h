#pragma once
#include <stdint.h>
#include <stddef.h>

void msm6295_init(void);
uint8_t *msm6295_write_rom(size_t rom_addr, const uint8_t *src, size_t n);
void msm6295_write_cmd(uint8_t addr, uint8_t data);