#include "motor.h"

#include "board.h"

void motor_apply(bool enable, bool brake, float duty, int sign)
{
    uint32_t r = 0, l = 0;

    if (enable && !brake) {
        float d = duty * (float)sign;
        if (d > 1.0f) {
            d = 1.0f;
        } else if (d < -1.0f) {
            d = -1.0f;
        }
        uint32_t pulse = (uint32_t)((d < 0.0f ? -d : d) * (float)(PWM_ARR + 1u));
        if (d >= 0.0f) {
            r = pulse;
        } else {
            l = pulse;
        }
    }
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_3, r);
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_4, l);
    HAL_GPIO_WritePin(MOTOR_EN_PORT, MOTOR_EN_PIN, enable ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

int32_t encoder_count(void)
{
    return (int32_t)__HAL_TIM_GET_COUNTER(&htim2);
}
