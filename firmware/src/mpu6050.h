/* MPU6050 (módulo GY-521) por I2C, com tempo limite e recuperação do barramento. */
#ifndef MPU6050_H
#define MPU6050_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    float acc[3];    /* g */
    float gyro[3];   /* rad/s */
} mpu6050_sample_t;

/* Acorda e configura o sensor. Retorna false se ele não responder. */
bool mpu6050_init(void);

/* Lê acelerômetro e giroscópio (~0,4 ms). Em caso de erro destrava o
   barramento, reconfigura o sensor e retorna false neste período. */
bool mpu6050_read(mpu6050_sample_t *s);

uint8_t mpu6050_who_am_i(void);     /* 0x68 no original; clones respondem outros valores */
uint32_t mpu6050_error_count(void);

#endif /* MPU6050_H */
