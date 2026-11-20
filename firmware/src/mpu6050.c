#include "mpu6050.h"

#include "board.h"

#define MPU_ADDR         (0x68u << 1)   /* AD0 em nível baixo (padrão do GY-521) */
#define REG_SMPLRT_DIV   0x19u
#define REG_CONFIG       0x1Au
#define REG_GYRO_CONFIG  0x1Bu
#define REG_ACCEL_CONFIG 0x1Cu
#define REG_ACCEL_XOUT_H 0x3Bu
#define REG_PWR_MGMT_1   0x6Bu
#define REG_WHO_AM_I     0x75u

#define I2C_TIMEOUT_MS   3u
#define ACC_LSB_PER_G    8192.0f                       /* fundo de escala de +-4 g */
#define GYRO_RAD_PER_LSB (0.0174532925f / 65.5f)       /* fundo de escala de +-500 graus/s */

static uint8_t who_am_i;
static uint32_t errors;
static bool configured;

static bool write_reg(uint8_t reg, uint8_t value)
{
    return HAL_I2C_Mem_Write(&hi2c1, MPU_ADDR, reg, I2C_MEMADD_SIZE_8BIT, &value, 1, I2C_TIMEOUT_MS) == HAL_OK;
}

bool mpu6050_init(void)
{
    configured = false;
    if (HAL_I2C_Mem_Read(&hi2c1, MPU_ADDR, REG_WHO_AM_I, I2C_MEMADD_SIZE_8BIT, &who_am_i, 1, I2C_TIMEOUT_MS) != HAL_OK) {
        who_am_i = 0;
        return false;
    }
    /* Não exige WHO_AM_I == 0x68: muitos GY-521 vendidos hoje trazem chips
       compatíveis que respondem 0x70, 0x72 ou 0x98 e funcionam igual. */
    configured = write_reg(REG_PWR_MGMT_1, 0x01)      /* acorda, relógio pelo giroscópio X */
              && write_reg(REG_SMPLRT_DIV, 0x00)      /* 1 kHz */
              && write_reg(REG_CONFIG, 0x02)          /* filtro digital: ~94 Hz, atraso de 3 ms */
              && write_reg(REG_GYRO_CONFIG, 0x08)     /* +-500 graus/s */
              && write_reg(REG_ACCEL_CONFIG, 0x08);   /* +-4 g */
    return configured;
}

bool mpu6050_read(mpu6050_sample_t *s)
{
    uint8_t b[14];

    if (!configured) {
        /* sensor ausente ou reiniciado por ruído: tenta de novo a cada chamada */
        errors++;
        board_i2c_recover();
        (void)mpu6050_init();
        return false;
    }
    if (HAL_I2C_Mem_Read(&hi2c1, MPU_ADDR, REG_ACCEL_XOUT_H, I2C_MEMADD_SIZE_8BIT, b, sizeof(b), I2C_TIMEOUT_MS) != HAL_OK) {
        errors++;
        configured = false;
        board_i2c_recover();
        (void)mpu6050_init();
        return false;
    }
    for (int k = 0; k < 3; k++) {
        int16_t a = (int16_t)((uint16_t)b[2 * k] << 8 | b[2 * k + 1]);
        int16_t g = (int16_t)((uint16_t)b[8 + 2 * k] << 8 | b[9 + 2 * k]);
        s->acc[k] = (float)a / ACC_LSB_PER_G;
        s->gyro[k] = (float)g * GYRO_RAD_PER_LSB;
    }
    /* tudo zero = sensor voltou a dormir depois de uma queda de tensão */
    if (b[0] == 0 && b[1] == 0 && b[2] == 0 && b[3] == 0 && b[4] == 0 && b[5] == 0) {
        errors++;
        configured = false;
        return false;
    }
    return true;
}

uint8_t mpu6050_who_am_i(void)
{
    return who_am_i;
}

uint32_t mpu6050_error_count(void)
{
    return errors;
}
