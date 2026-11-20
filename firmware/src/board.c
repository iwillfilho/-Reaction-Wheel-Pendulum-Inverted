/* Inicialização da placa: relógio, pinos e periféricos. */
#include "board.h"

TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;
TIM_HandleTypeDef htim11;
I2C_HandleTypeDef hi2c1;
UART_HandleTypeDef huart2;
ADC_HandleTypeDef hadc1;
static IWDG_HandleTypeDef hiwdg;

static volatile uint8_t tick_pending;
static volatile uint32_t tick_overruns;
static bool clock_hse;

/* 96 MHz a partir do cristal de 25 MHz (48 MHz exatos para o USB). Se o
   cristal não partir, usa o oscilador interno: tudo funciona, só com o
   relógio menos preciso. */
static void clock_init(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE | RCC_OSCILLATORTYPE_LSI;
    osc.HSEState = RCC_HSE_ON;
    osc.LSIState = RCC_LSI_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 25;
    osc.PLL.PLLN = 192;
    osc.PLL.PLLP = RCC_PLLP_DIV2;
    osc.PLL.PLLQ = 4;
    clock_hse = (HAL_RCC_OscConfig(&osc) == HAL_OK);
    if (!clock_hse) {
        osc.OscillatorType = RCC_OSCILLATORTYPE_HSI | RCC_OSCILLATORTYPE_LSI;
        osc.HSEState = RCC_HSE_OFF;
        osc.HSIState = RCC_HSI_ON;
        osc.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
        osc.PLL.PLLSource = RCC_PLLSOURCE_HSI;
        osc.PLL.PLLM = 16;
        (void)HAL_RCC_OscConfig(&osc);
    }

    clk.ClockType = RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV2;   /* 48 MHz; os timers do APB1 recebem 96 MHz */
    clk.APB2CLKDivider = RCC_HCLK_DIV1;
    (void)HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_3);
}

static void gpio_init(void)
{
    GPIO_InitTypeDef g = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* Habilitação da ponte H: primeira coisa, e em nível baixo. */
    HAL_GPIO_WritePin(MOTOR_EN_PORT, MOTOR_EN_PIN, GPIO_PIN_RESET);
    g.Pin = MOTOR_EN_PIN;
    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pull = GPIO_PULLDOWN;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(MOTOR_EN_PORT, &g);

    /* LED (ativo em baixo) */
    HAL_GPIO_WritePin(LED_PORT, LED_PIN, GPIO_PIN_SET);
    g.Pin = LED_PIN;
    g.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(LED_PORT, &g);

    /* Botão KEY (fecha para o GND) */
    g.Pin = KEY_PIN;
    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(KEY_PORT, &g);

    /* PWM: PB0 / PB1 = TIM3_CH3 / CH4 */
    g.Pin = PWM_R_PIN | PWM_L_PIN;
    g.Mode = GPIO_MODE_AF_PP;
    g.Pull = GPIO_PULLDOWN;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    g.Alternate = GPIO_AF2_TIM3;
    HAL_GPIO_Init(GPIOB, &g);

    /* Encoder: PA15 / PB3 = TIM2_CH1 / CH2 (livres porque só o SWD é usado) */
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    g.Alternate = GPIO_AF1_TIM2;
    g.Pin = ENC_A_PIN;
    HAL_GPIO_Init(ENC_A_PORT, &g);
    g.Pin = ENC_B_PIN;
    HAL_GPIO_Init(ENC_B_PORT, &g);

    /* USART2: PA2 / PA3 */
    g.Pin = UART_TX_PIN | UART_RX_PIN;
    g.Mode = GPIO_MODE_AF_PP;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    g.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(GPIOA, &g);

    /* Entradas analógicas: PA4, PA5, PA6 */
    g.Pin = GPIO_PIN_4 | GPIO_PIN_5 | GPIO_PIN_6;
    g.Mode = GPIO_MODE_ANALOG;
    g.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &g);
}

static void i2c_pins_as_i2c(void)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = I2C_SCL_PIN | I2C_SDA_PIN;
    g.Mode = GPIO_MODE_AF_OD;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    g.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(GPIOB, &g);
}

static void i2c_init(void)
{
    __HAL_RCC_I2C1_CLK_ENABLE();
    i2c_pins_as_i2c();
    hi2c1.Instance = I2C1;
    hi2c1.Init.ClockSpeed = 400000;
    hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    (void)HAL_I2C_Init(&hi2c1);
}

/* O ruído do motor pode deixar o MPU6050 segurando SDA em baixo no meio de um
   byte. Solução padrão: até 9 pulsos de relógio à mão, uma condição de parada
   e reinício do periférico. Leva menos de 0,3 ms. */
void board_i2c_recover(void)
{
    GPIO_InitTypeDef g = {0};

    (void)HAL_I2C_DeInit(&hi2c1);
    HAL_GPIO_WritePin(GPIOB, I2C_SCL_PIN | I2C_SDA_PIN, GPIO_PIN_SET);
    g.Pin = I2C_SCL_PIN | I2C_SDA_PIN;
    g.Mode = GPIO_MODE_OUTPUT_OD;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOB, &g);

    for (int k = 0; k < 9 && HAL_GPIO_ReadPin(I2C_SDA_PORT, I2C_SDA_PIN) == GPIO_PIN_RESET; k++) {
        HAL_GPIO_WritePin(I2C_SCL_PORT, I2C_SCL_PIN, GPIO_PIN_RESET);
        board_delay_us(5);
        HAL_GPIO_WritePin(I2C_SCL_PORT, I2C_SCL_PIN, GPIO_PIN_SET);
        board_delay_us(5);
    }
    /* condição de parada: SDA sobe com SCL em alto */
    HAL_GPIO_WritePin(I2C_SDA_PORT, I2C_SDA_PIN, GPIO_PIN_RESET);
    board_delay_us(5);
    HAL_GPIO_WritePin(I2C_SCL_PORT, I2C_SCL_PIN, GPIO_PIN_SET);
    board_delay_us(5);
    HAL_GPIO_WritePin(I2C_SDA_PORT, I2C_SDA_PIN, GPIO_PIN_SET);
    board_delay_us(5);

    __HAL_RCC_I2C1_FORCE_RESET();
    __HAL_RCC_I2C1_RELEASE_RESET();
    i2c_init();
}

static void pwm_init(void)
{
    TIM_OC_InitTypeDef oc = {0};

    __HAL_RCC_TIM3_CLK_ENABLE();
    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 0;
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.Period = PWM_ARR;
    htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    (void)HAL_TIM_PWM_Init(&htim3);

    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = 0;
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    oc.OCFastMode = TIM_OCFAST_DISABLE;
    (void)HAL_TIM_PWM_ConfigChannel(&htim3, &oc, TIM_CHANNEL_3);
    (void)HAL_TIM_PWM_ConfigChannel(&htim3, &oc, TIM_CHANNEL_4);
    (void)HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_3);
    (void)HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_4);
}

static void encoder_init(void)
{
    TIM_Encoder_InitTypeDef e = {0};

    __HAL_RCC_TIM2_CLK_ENABLE();
    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 0;
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 0xFFFFFFFFu;               /* TIM2 tem 32 bits */
    /* Filtro digital: com DIV4 e filtro 0xF a borda precisa ficar estável por
       ~11 us. Os sensores de fenda com LM393 não têm histerese e repicam na
       borda; a 2000 rpm as bordas ficam a ~190 us uma da outra, sobra folga. */
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV4;
    htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;

    e.EncoderMode = TIM_ENCODERMODE_TI12;          /* conta as 4 bordas */
    e.IC1Polarity = TIM_ICPOLARITY_RISING;
    e.IC1Selection = TIM_ICSELECTION_DIRECTTI;
    e.IC1Prescaler = TIM_ICPSC_DIV1;
    e.IC1Filter = 0x0F;
    e.IC2Polarity = TIM_ICPOLARITY_RISING;
    e.IC2Selection = TIM_ICSELECTION_DIRECTTI;
    e.IC2Prescaler = TIM_ICPSC_DIV1;
    e.IC2Filter = 0x0F;
    (void)HAL_TIM_Encoder_Init(&htim2, &e);
    (void)HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
}

static void uart_init(void)
{
    __HAL_RCC_USART2_CLK_ENABLE();
    huart2.Instance = USART2;
    huart2.Init.BaudRate = UART_BAUD;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    (void)HAL_UART_Init(&huart2);
    HAL_NVIC_SetPriority(USART2_IRQn, 3, 0);
    HAL_NVIC_EnableIRQ(USART2_IRQn);
}

static void adc_init(void)
{
    __HAL_RCC_ADC1_CLK_ENABLE();
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;   /* 24 MHz */
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DMAContinuousRequests = DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    (void)HAL_ADC_Init(&hadc1);
}

/* Uma conversão bloqueante (~5 us). Retorna a tensão no pino, em volts. */
float board_adc_volts(uint32_t channel)
{
    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = channel;
    ch.Rank = 1;
    ch.SamplingTime = ADC_SAMPLETIME_84CYCLES;
    if (HAL_ADC_ConfigChannel(&hadc1, &ch) != HAL_OK || HAL_ADC_Start(&hadc1) != HAL_OK) {
        return 0.0f;
    }
    if (HAL_ADC_PollForConversion(&hadc1, 2) != HAL_OK) {
        (void)HAL_ADC_Stop(&hadc1);
        return 0.0f;
    }
    return (float)HAL_ADC_GetValue(&hadc1) * (3.3f / 4095.0f);
}

void board_init(void)
{
    clock_init();

    /* contador de ciclos para atrasos de microssegundos */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    gpio_init();
    pwm_init();
    encoder_init();
    i2c_init();
    uart_init();
    adc_init();
}

void board_delay_us(uint32_t us)
{
    uint32_t start = DWT->CYCCNT;
    uint32_t cycles = us * (SystemCoreClock / 1000000u);
    while ((DWT->CYCCNT - start) < cycles) {
    }
}

/* Cão de guarda de 100 ms: se o laço travar, o processador reinicia e a
   ponte H volta desabilitada (pull-down no pino de habilitação). */
void board_watchdog_start(void)
{
    __HAL_DBGMCU_FREEZE_IWDG();   /* não dispara com o depurador parado */
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_32;   /* 32 kHz / 32 = 1 kHz */
    hiwdg.Init.Reload = 100;
    (void)HAL_IWDG_Init(&hiwdg);
}

void board_watchdog_kick(void)
{
    (void)HAL_IWDG_Refresh(&hiwdg);
}

void board_tick_start(void)
{
    __HAL_RCC_TIM11_CLK_ENABLE();
    htim11.Instance = TIM11;
    htim11.Init.Prescaler = SYSCLK_HZ / 1000000u - 1u;     /* 1 MHz */
    htim11.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim11.Init.Period = 1000000u / CONTROL_HZ - 1u;
    htim11.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim11.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    (void)HAL_TIM_Base_Init(&htim11);
    HAL_NVIC_SetPriority(TIM1_TRG_COM_TIM11_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(TIM1_TRG_COM_TIM11_IRQn);
    (void)HAL_TIM_Base_Start_IT(&htim11);
}

void board_tick_isr(void)
{
    if (tick_pending) {
        tick_overruns++;
    }
    tick_pending = 1;
}

bool board_tick_take(void)
{
    if (!tick_pending) {
        return false;
    }
    tick_pending = 0;
    return true;
}

uint32_t board_tick_overruns(void)
{
    return tick_overruns;
}

void board_led(bool on)
{
    HAL_GPIO_WritePin(LED_PORT, LED_PIN, on ? GPIO_PIN_RESET : GPIO_PIN_SET);
}

bool board_key_pressed(void)
{
    return HAL_GPIO_ReadPin(KEY_PORT, KEY_PIN) == GPIO_PIN_RESET;
}

bool board_clock_is_hse(void)
{
    return clock_hse;
}
