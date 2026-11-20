#include "telemetry.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "board.h"

#define TX_SIZE 2048u            /* potência de 2 */
#define TX_MASK (TX_SIZE - 1u)
#define RX_LINE 48u

static uint8_t tx_buf[TX_SIZE];
static volatile uint32_t tx_head;   /* próxima posição livre */
static volatile uint32_t tx_tail;   /* próximo byte a enviar */
static volatile uint32_t tx_sending;   /* bytes do bloco em transmissão (0 = parado) */

static uint8_t rx_byte;
static char rx_line[RX_LINE];
static volatile uint32_t rx_len;
static char rx_ready[RX_LINE];
static volatile bool rx_has_line;

/* Dispara o envio do próximo trecho contíguo da fila. Chamar com interrupções
   mascaradas ou de dentro da interrupção da serial. */
static void tx_kick(void)
{
    if (tx_sending != 0u || tx_head == tx_tail) {
        return;
    }
    uint32_t tail = tx_tail & TX_MASK;
    uint32_t n = tx_head - tx_tail;
    if (n > TX_SIZE - tail) {
        n = TX_SIZE - tail;          /* até o fim do vetor; o resto vai no próximo bloco */
    }
    tx_sending = n;
    if (HAL_UART_Transmit_IT(&huart2, &tx_buf[tail], (uint16_t)n) != HAL_OK) {
        tx_sending = 0;
    }
}

void tele_init(void)
{
    tx_head = tx_tail = tx_sending = 0;
    rx_len = 0;
    rx_has_line = false;
    (void)HAL_UART_Receive_IT(&huart2, &rx_byte, 1);
}

void tele_printf(const char *fmt, ...)
{
    char tmp[160];
    va_list ap;

    va_start(ap, fmt);
    int n = vsnprintf(tmp, sizeof(tmp), fmt, ap);
    va_end(ap);
    if (n <= 0) {
        return;
    }
    if ((size_t)n >= sizeof(tmp)) {
        n = (int)sizeof(tmp) - 1;
    }

    __disable_irq();
    if (TX_SIZE - (tx_head - tx_tail) >= (uint32_t)n) {
        for (int k = 0; k < n; k++) {
            tx_buf[(tx_head + (uint32_t)k) & TX_MASK] = (uint8_t)tmp[k];
        }
        tx_head += (uint32_t)n;
        tx_kick();
    }
    __enable_irq();
}

char *tele_fixed3(char *dst, float v)
{
    long m = (long)(v * 1000.0f + (v >= 0.0f ? 0.5f : -0.5f));
    long a = m < 0 ? -m : m;
    (void)snprintf(dst, 16, "%s%ld.%03ld", m < 0 ? "-" : "", a / 1000, a % 1000);
    return dst;
}

bool tele_get_line(char *dst, size_t size)
{
    if (!rx_has_line || size == 0) {
        return false;
    }
    __disable_irq();
    strncpy(dst, rx_ready, size - 1);
    dst[size - 1] = '\0';
    rx_has_line = false;
    __enable_irq();
    return true;
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart != &huart2) {
        return;
    }
    tx_tail += tx_sending;
    tx_sending = 0;
    tx_kick();
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart != &huart2) {
        return;
    }
    char ch = (char)rx_byte;
    if (ch == '\n' || ch == '\r') {
        if (rx_len > 0 && !rx_has_line) {
            rx_line[rx_len] = '\0';
            memcpy(rx_ready, rx_line, rx_len + 1);
            rx_has_line = true;
        }
        rx_len = 0;
    } else if (rx_len < RX_LINE - 1u) {
        rx_line[rx_len++] = ch;
    }
    (void)HAL_UART_Receive_IT(&huart2, &rx_byte, 1);
}

/* Erro de recepção (ruído, estouro): limpa e volta a escutar. */
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart != &huart2) {
        return;
    }
    rx_len = 0;
    (void)HAL_UART_Receive_IT(&huart2, &rx_byte, 1);
}
