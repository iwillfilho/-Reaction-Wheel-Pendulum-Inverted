/*
 * Mapa de pinos e opções de montagem - WeAct Black Pill STM32F411CEU6.
 *
 * Esta é a referência de ligação do firmware; docs/ligacoes.md repete esta
 * tabela com as cores de fio e os cuidados elétricos.
 *
 *   Função                       Pino   Periférico
 *   --------------------------   ----   ---------------------------
 *   IBT-2 RPWM                   PB0    TIM3_CH3, PWM 20 kHz
 *   IBT-2 LPWM                   PB1    TIM3_CH4, PWM 20 kHz
 *   IBT-2 R_EN + L_EN (juntos)   PB10   GPIO, pull-down externo 10 k
 *   Sensor óptico A (D0)         PA15   TIM2_CH1, modo encoder
 *   Sensor óptico B (D0)         PB3    TIM2_CH2, modo encoder
 *   MPU6050 SCL                  PB6    I2C1, 400 kHz
 *   MPU6050 SDA                  PB7    I2C1
 *   Telemetria TX (-> RX do adaptador USB-serial)   PA2   USART2
 *   Telemetria RX (<- TX do adaptador USB-serial)   PA3   USART2
 *   Tensão do barramento (divisor 10 k / 2,2 k)     PA4   ADC1_IN4
 *   IBT-2 R_IS (divisor 10 k / 10 k, opcional)      PA5   ADC1_IN5
 *   IBT-2 L_IS (divisor 10 k / 10 k, opcional)      PA6   ADC1_IN6
 *   Botão KEY da placa (armar / parar)              PA0   GPIO, ativo em nível baixo
 *   LED da placa                                    PC13  GPIO, ativo em nível baixo
 *   Reservados: PA13/PA14 (SWD), PA11/PA12 (USB), PB2 (BOOT1)
 */
#ifndef BOARD_H
#define BOARD_H

#include <stdbool.h>
#include <stdint.h>

#include "stm32f4xx_hal.h"

/* ---- opções de montagem -------------------------------------------------- */

/* 1: o divisor de tensão do barramento está ligado em PA4.
   0: sem divisor; o firmware assume a tensão nominal e perde as proteções de
      sub/sobretensão (use só nos primeiros testes de bancada). */
#define USE_VBUS_SENSE 1

/* 1: R_IS e L_IS do IBT-2 ligados em PA5/PA6 (aparecem só no comando "diag"). */
#define USE_CURRENT_SENSE 0

/* Divisor do barramento: (R_cima + R_baixo) / R_baixo = (10k + 2,2k) / 2,2k */
#define VBUS_DIVIDER 5.545f

/* ---- orientação dos sensores (conferir na bancada: docs/testes_bancada.md) -
   Montagem padrão: MPU6050 (GY-521) colado no braço, placa paralela ao plano
   de oscilação, eixo Y do módulo apontando para o motor (para cima). Assim o
   eixo Z do giroscópio fica alinhado com o pivô. Índices: 0 = X, 1 = Y, 2 = Z.
   Cada sinal pode ser invertido em tempo de execução com o comando "inv". */
#define IMU_GYRO_AXIS     2
#define IMU_ACC_UP_AXIS   1
#define IMU_ACC_SIDE_AXIS 0
#define IMU_GYRO_SIGN     (+1)
#define IMU_ANGLE_SIGN    (+1)
#define ENC_SIGN          (+1)
#define MOTOR_SIGN        (+1)

/* ---- pinos --------------------------------------------------------------- */
#define PWM_R_PORT   GPIOB
#define PWM_R_PIN    GPIO_PIN_0
#define PWM_L_PORT   GPIOB
#define PWM_L_PIN    GPIO_PIN_1
#define MOTOR_EN_PORT GPIOB
#define MOTOR_EN_PIN  GPIO_PIN_10
#define ENC_A_PORT   GPIOA
#define ENC_A_PIN    GPIO_PIN_15
#define ENC_B_PORT   GPIOB
#define ENC_B_PIN    GPIO_PIN_3
#define I2C_SCL_PORT GPIOB
#define I2C_SCL_PIN  GPIO_PIN_6
#define I2C_SDA_PORT GPIOB
#define I2C_SDA_PIN  GPIO_PIN_7
#define UART_TX_PIN  GPIO_PIN_2   /* GPIOA */
#define UART_RX_PIN  GPIO_PIN_3   /* GPIOA */
#define ADC_VBUS_CH  ADC_CHANNEL_4
#define ADC_RIS_CH   ADC_CHANNEL_5
#define ADC_LIS_CH   ADC_CHANNEL_6
#define KEY_PORT     GPIOA
#define KEY_PIN      GPIO_PIN_0
#define LED_PORT     GPIOC
#define LED_PIN      GPIO_PIN_13

/* ---- temporização --------------------------------------------------------- */
#define SYSCLK_HZ    96000000u
#define PWM_HZ       20000u
#define PWM_ARR      (SYSCLK_HZ / PWM_HZ - 1u)   /* 4799: resolução de 1/4800 */
#define CONTROL_HZ   1000u
#define UART_BAUD    460800u

extern TIM_HandleTypeDef htim2;    /* encoder */
extern TIM_HandleTypeDef htim3;    /* PWM */
extern TIM_HandleTypeDef htim11;   /* base de tempo do controle */
extern I2C_HandleTypeDef hi2c1;
extern UART_HandleTypeDef huart2;
extern ADC_HandleTypeDef hadc1;

void board_init(void);
void board_watchdog_start(void);
void board_watchdog_kick(void);
void board_tick_start(void);
bool board_tick_take(void);          /* true uma vez a cada período de controle */
uint32_t board_tick_overruns(void);  /* períodos perdidos (laço atrasou) */
void board_tick_isr(void);
void board_delay_us(uint32_t us);
void board_i2c_recover(void);        /* destrava o barramento e reinicia o I2C1 */
float board_adc_volts(uint32_t channel);
void board_led(bool on);
bool board_key_pressed(void);
bool board_clock_is_hse(void);

#endif /* BOARD_H */
