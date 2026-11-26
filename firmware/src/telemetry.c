/* Telemetria e comandos pela porta serial virtual do USB (CDC), no mesmo cabo
   USB-C que alimenta a Black Pill. No PC aparece como /dev/ttyACM0 (Linux) ou
   COMx (Windows). A interface é a mesma de antes (tele_init, tele_printf,
   tele_get_line): o resto do firmware não muda, e o controle nunca espera
   pela serial. */
#include "telemetry.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "board.h"
#include "usbd_cdc.h"
#include "usbd_core.h"
#include "usbd_desc.h"

#define TX_SIZE 2048u            /* potência de 2 */
#define TX_MASK (TX_SIZE - 1u)
#define TX_CHUNK 512u            /* maior bloco entregue ao USB de uma vez */
#define RX_LINE 48u

static USBD_HandleTypeDef usb_dev;
static bool usb_ok;

static uint8_t tx_buf[TX_SIZE];
static volatile uint32_t tx_head;      /* próxima posição livre */
static volatile uint32_t tx_tail;      /* próximo byte a enviar */
static volatile uint32_t tx_sending;   /* bytes do bloco em transmissão (0 = parado) */

static uint8_t rx_pkt[CDC_DATA_FS_MAX_PACKET_SIZE];
static char rx_line[RX_LINE];
static volatile uint32_t rx_len;
static char rx_ready[RX_LINE];
static volatile bool rx_has_line;

/* 460800 8N1: só para o terminal do PC ficar contente; no USB não importa. */
static uint8_t line_coding[7] = {0x00, 0x08, 0x07, 0x00, 0x00, 0x00, 0x08};

/* Dispara o envio do próximo trecho contíguo da fila. Chamar com interrupções
   mascaradas ou de dentro da interrupção do USB. */
static void tx_kick(void)
{
    if (!usb_ok || tx_sending != 0u || tx_head == tx_tail || usb_dev.dev_state != USBD_STATE_CONFIGURED) {
        return;
    }
    uint32_t tail = tx_tail & TX_MASK;
    uint32_t n = tx_head - tx_tail;
    if (n > TX_SIZE - tail) {
        n = TX_SIZE - tail;          /* até o fim do vetor; o resto vai no próximo bloco */
    }
    if (n > TX_CHUNK) {
        n = TX_CHUNK;
    }
    tx_sending = n;
    (void)USBD_CDC_SetTxBuffer(&usb_dev, &tx_buf[tail], n);
    if (USBD_CDC_TransmitPacket(&usb_dev) != (uint8_t)USBD_OK) {
        tx_sending = 0;              /* tenta de novo no próximo tele_printf */
    }
}

/* ---- funções chamadas pela classe CDC (dentro da interrupção do USB) ---- */

static int8_t cdc_init(void)
{
    tx_sending = 0;
    rx_len = 0;
    (void)USBD_CDC_SetRxBuffer(&usb_dev, rx_pkt);   /* a classe já arma a primeira recepção */
    return (int8_t)USBD_OK;
}

static int8_t cdc_deinit(void)
{
    tx_sending = 0;
    return (int8_t)USBD_OK;
}

static int8_t cdc_control(uint8_t cmd, uint8_t *pbuf, uint16_t length)
{
    if (cmd == CDC_SET_LINE_CODING && length >= sizeof(line_coding)) {
        memcpy(line_coding, pbuf, sizeof(line_coding));
    } else if (cmd == CDC_GET_LINE_CODING && length >= sizeof(line_coding)) {
        memcpy(pbuf, line_coding, sizeof(line_coding));
    }
    return (int8_t)USBD_OK;
}

static int8_t cdc_receive(uint8_t *buf, uint32_t *len)
{
    for (uint32_t k = 0; k < *len; k++) {
        char ch = (char)buf[k];
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
    }
    (void)USBD_CDC_SetRxBuffer(&usb_dev, rx_pkt);
    (void)USBD_CDC_ReceivePacket(&usb_dev);
    return (int8_t)USBD_OK;
}

static int8_t cdc_tx_done(uint8_t *buf, uint32_t *len, uint8_t epnum)
{
    (void)buf;
    (void)len;
    (void)epnum;
    tx_tail += tx_sending;
    tx_sending = 0;
    tx_kick();
    return (int8_t)USBD_OK;
}

static USBD_CDC_ItfTypeDef cdc_fops = {cdc_init, cdc_deinit, cdc_control, cdc_receive, cdc_tx_done};

/* ---- interface usada pelo firmware ---- */

void tele_init(void)
{
    tx_head = tx_tail = tx_sending = 0;
    rx_len = 0;
    rx_has_line = false;

    /* O USB precisa dos 48 MHz exatos que só o cristal dá. Com o relógio
       interno o controle funciona, mas sem telemetria. */
    usb_ok = board_clock_is_hse() &&
             USBD_Init(&usb_dev, &Class_Desc, DEVICE_FS) == USBD_OK &&
             USBD_RegisterClass(&usb_dev, &USBD_CDC) == USBD_OK &&
             USBD_CDC_RegisterInterface(&usb_dev, &cdc_fops) == (uint8_t)USBD_OK &&
             USBD_Start(&usb_dev) == USBD_OK;
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
