#include <generated/csr.h>
#include <generated/soc.h>
#include <irq.h>
#include <libbase/uart.h>

void isr(void);
void timer0_isr(void);

#ifdef CONFIG_CPU_HAS_INTERRUPT

void isr(void) {
    __attribute__((unused)) unsigned int irqs;

    irqs = irq_pending() & irq_getmask();

#ifndef UART_POLLING
    if (irqs & (1 << UART_INTERRUPT)) uart_isr();
#endif

    if (irqs & (1 << TIMER0_INTERRUPT)) timer0_isr();
}

#else

void isr(void){};

#endif
