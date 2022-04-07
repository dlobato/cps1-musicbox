BUILD_DIR?=../build/

include $(BUILD_DIR)/software/include/generated/variables.mak
include $(SOC_DIRECTORY)/software/common.mak

OBJDUMP := $(TARGET_PREFIX)objdump

OBJECTS   = vgm_data.o main.o vgm.o ym2151.o msm6295.o timer.o isr.o crt0.o

all: vgmplay.bin
	$(PYTHON) -m litex.soc.software.memusage vgmplay.elf $(BUILD_DIR)/software/include/generated/regions.ld $(TRIPLE)

# pull in dependency info for *existing* .o files
-include $(OBJECTS:.o=.d)

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@
	chmod -x $@

vgmplay.elf: $(OBJECTS)
	$(CC) $(LDFLAGS) -T linker.ld -N -o $@ \
		$(OBJECTS) \
		$(PACKAGES:%=-L$(BUILD_DIR)/software/%) \
		-Wl,--gc-sections \
		-Wl,-Map,$@.map \
		$(LIBS:lib%=-l%)
	chmod -x $@

%.asm: %.elf
	$(OBJDUMP) -S -d $^ > $@

main.o: CFLAGS += -DVGM_DATA_FILE=\"stf2_title.vgm\"
main.o: main.c
	$(compile)

crt0.o: $(CPU_DIRECTORY)/crt0.S
	$(assemble)

vgm_data.o: CFLAGS += -DVGM_DATA_FILE=\"stf2_title.vgm\"
vgm_data.o: vgm_data.S
	$(assemble)

%.o: %.cpp
	$(compilexx)

%.o: %.c
	$(compile)

%.o: %.S
	$(assemble)

clean:
	$(RM) $(OBJECTS) $(OBJECTS:.o=.d) vgmplay.elf vgmplay.bin .*~ *~

.PHONY: all main.o clean load
