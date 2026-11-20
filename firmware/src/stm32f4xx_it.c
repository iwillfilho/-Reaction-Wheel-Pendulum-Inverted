/* Tratadores de interrupção e de exceção. */
#include "board.h"

void SysTick_Handler(void)
{
    HAL_IncTick();
}

/* Base de tempo do controle (1 kHz). */
void TIM1_TRG_COM_TIM11_IRQHandler(void)
{
    if (__HAL_TIM_GET_FLAG(&htim11, TIM_FLAG_UPDATE) != RESET) {
        __HAL_TIM_CLEAR_IT(&htim11, TIM_IT_UPDATE);
        board_tick_isr();
    }
}

void USART2_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart2);
}

/* Qualquer exceção grave: desabilita a ponte H direto no registrador e espera
   o cão de guarda reiniciar o processador. */
static void halt_motor_off(void)
{
    MOTOR_EN_PORT->BSRR = (uint32_t)MOTOR_EN_PIN << 16u;
    TIM3->CCR3 = 0;
    TIM3->CCR4 = 0;
    for (;;) {
    }
}

void NMI_Handler(void)        { halt_motor_off(); }
void HardFault_Handler(void)  { halt_motor_off(); }
void MemManage_Handler(void)  { halt_motor_off(); }
void BusFault_Handler(void)   { halt_motor_off(); }
void UsageFault_Handler(void) { halt_motor_off(); }
void SVC_Handler(void)        {}
void DebugMon_Handler(void)   {}
void PendSV_Handler(void)     {}
