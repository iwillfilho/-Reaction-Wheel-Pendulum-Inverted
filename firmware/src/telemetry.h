/* Serial de telemetria e comandos (USART2), sem bloquear o laço de controle. */
#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <stdbool.h>
#include <stddef.h>

void tele_init(void);

/* printf sem ponto flutuante (%d, %ld, %u, %s, %x). Se a fila encher, o texto
   é descartado: o controle nunca espera pela serial. */
void tele_printf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

/* Escreve v com 3 casas decimais em dst (>= 16 bytes) e retorna dst. */
char *tele_fixed3(char *dst, float v);

/* Copia uma linha de comando recebida, se houver. */
bool tele_get_line(char *dst, size_t size);

#endif /* TELEMETRY_H */
