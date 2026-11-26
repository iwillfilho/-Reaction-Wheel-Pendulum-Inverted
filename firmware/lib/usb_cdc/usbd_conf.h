/* Configuração da biblioteca USB Device da ST para a Black Pill (USB OTG FS,
   PA11 = D-, PA12 = D+). Usada só pela porta serial virtual (CDC). */
#ifndef USBD_CONF_H
#define USBD_CONF_H

#include "stm32f4xx_hal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define USBD_MAX_NUM_INTERFACES     1U
#define USBD_MAX_NUM_CONFIGURATION  1U
#define USBD_MAX_STR_DESC_SIZ       0x100U
#define USBD_SELF_POWERED           0U    /* a placa vive do próprio USB */
#define USBD_DEBUG_LEVEL            0U

#define DEVICE_FS 0
#define DEVICE_HS 1

/* memória estática: nada de malloc no firmware */
#define USBD_malloc  (void *)USBD_static_malloc
#define USBD_free    USBD_static_free
#define USBD_memset  memset
#define USBD_memcpy  memcpy
#define USBD_Delay   HAL_Delay

#define USBD_UsrLog(...) do {} while (0)
#define USBD_ErrLog(...) do {} while (0)
#define USBD_DbgLog(...) do {} while (0)

void *USBD_static_malloc(uint32_t size);
void USBD_static_free(void *p);

extern PCD_HandleTypeDef hpcd_USB_OTG_FS;

#endif /* USBD_CONF_H */
