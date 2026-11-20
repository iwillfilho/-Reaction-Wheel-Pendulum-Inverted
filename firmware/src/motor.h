/* Ponte H BTS7960 (módulo IBT-2) e encoder óptico da roda. */
#ifndef MOTOR_H
#define MOTOR_H

#include <stdbool.h>
#include <stdint.h>

/*
 * enable = false : ponte desabilitada, motor solto.
 * brake  = true  : os dois lados em nível baixo -> motor em curto (freio dinâmico).
 * duty em [-1, 1]: um lado recebe o PWM, o outro fica em nível baixo.
 * sign (+1 ou -1) inverte o sentido sem trocar os fios do motor.
 */
void motor_apply(bool enable, bool brake, float duty, int sign);

/* Contagem acumulada do encoder em quadratura (4 x número de ranhuras por volta). */
int32_t encoder_count(void);

#endif /* MOTOR_H */
