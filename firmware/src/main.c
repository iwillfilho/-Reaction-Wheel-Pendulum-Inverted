/*
 * Pêndulo invertido com roda de reação - laço principal.
 *
 * A cada 1 ms: lê MPU6050, encoder e tensão do barramento, chama a lógica de
 * controle (lib/control, a mesma testada no PC) e atualiza a ponte H.
 *
 * Uso: botão KEY (ou comando "a") calibra o giroscópio com o pêndulo parado;
 * depois é só levar o braço até a vertical que o controle assume sozinho.
 * Apertar de novo (ou "s") desliga.
 */
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "board.h"
#include "lqr_gains.h"
#include "motor.h"
#include "mpu6050.h"
#include "rwp_control.h"
#include "telemetry.h"

#define RAD2MDEG   57295.78f                 /* rad -> milésimos de grau */
#define RADS2DRPM  95.49297f                 /* rad/s -> décimos de rpm */
#define DEBOUNCE_MS 20u

static rwp_t ctl;
static rwp_inputs_t in;
static rwp_outputs_t out;

/* Sinais de montagem; partem de board.h e podem ser trocados pela serial. */
static int sign_gyro = IMU_GYRO_SIGN;
static int sign_angle = IMU_ANGLE_SIGN;
static int sign_enc = ENC_SIGN;
static int sign_motor = MOTOR_SIGN;

static uint32_t tele_div = 5;                /* telemetria a cada 5 ms (200 Hz) */
static bool ev_button, ev_stop, ev_manual;
static float manual_duty;
static mpu6050_sample_t imu;
static float vbus = RWP_VBUS_NOM;

/* Teste de sinal do giroscópio (comando "sinais"): compara a derivada do
   ângulo do acelerômetro com a leitura do giroscópio enquanto o braço é
   balançado à mão. */
static uint32_t sign_test_left;
static float sign_test_sum, sign_test_prev;

static void print_help(void)
{
    tele_printf("# comandos:\r\n"
                "#  a            armar (igual ao botao KEY)\r\n"
                "#  s            parar\r\n"
                "#  m <pct>      ensaio em malha aberta, -45 a 45 %% (s para parar)\r\n"
                "#  k1|k2|k3 <v> muda um ganho      imax <A>  limite de corrente\r\n");
    tele_printf("#  trim <graus> ajusta o angulo de equilibrio   trimg <v> ganho do auto-ajuste (0 desliga)\r\n"
                "#  rate <n>     telemetria a cada n ms (0 desliga)\r\n"
                "#  inv motor|enc|giro|ang   inverte um sinal\r\n"
                "#  sinais       confere o sinal do giroscopio (balance o braco por 3 s)\r\n"
                "#  cfg  diag  ?\r\n");
}

static void print_cfg(void)
{
    char a[16], b[16], c[16], d[16];
    const rwp_config_t *g = &ctl.cfg;
    tele_printf("# K1=%s K2=%s K3=%s imax=%s A\r\n", tele_fixed3(a, g->k1), tele_fixed3(b, g->k2),
                tele_fixed3(c, g->k3), tele_fixed3(d, g->i_max));
    tele_printf("# trim=%s graus  trimg=%s e-6  corte=%s graus  wmax=%s rad/s\r\n",
                tele_fixed3(a, ctl.trim * 57.29578f), tele_fixed3(b, g->trim_gain * 1e6f),
                tele_fixed3(c, g->theta_cut * 57.29578f), tele_fixed3(d, g->w_max));
    tele_printf("# sinais: motor=%d enc=%d giro=%d ang=%d  telemetria a cada %lu ms\r\n", sign_motor, sign_enc,
                sign_gyro, sign_angle, (unsigned long)tele_div);
}

static void print_diag(void)
{
    char a[16], b[16], c[16];
    tele_printf("# relogio: %s  MPU6050 WHO_AM_I=0x%02x erros_i2c=%lu  periodos_perdidos=%lu\r\n",
                board_clock_is_hse() ? "cristal 25 MHz" : "INTERNO (cristal nao partiu)", mpu6050_who_am_i(),
                (unsigned long)mpu6050_error_count(), (unsigned long)board_tick_overruns());
    tele_printf("# acel[g]  x=%s y=%s z=%s\r\n", tele_fixed3(a, imu.acc[0]), tele_fixed3(b, imu.acc[1]),
                tele_fixed3(c, imu.acc[2]));
    tele_printf("# giro[rad/s] x=%s y=%s z=%s\r\n", tele_fixed3(a, imu.gyro[0]), tele_fixed3(b, imu.gyro[1]),
                tele_fixed3(c, imu.gyro[2]));
    tele_printf("# encoder=%ld  vbus=%s V  estado=%s falha=%s\r\n", (long)encoder_count(), tele_fixed3(a, vbus),
                rwp_state_name(ctl.state), rwp_fault_name(ctl.fault));
#if USE_CURRENT_SENSE
    /* IS = I / 8500 sobre 1 k no módulo, depois divisor 10k/10k -> 17 A por volt no pino */
    tele_printf("# corrente  R=%s A  L=%s A (aprox.)\r\n", tele_fixed3(a, board_adc_volts(ADC_RIS_CH) * 17.0f),
                tele_fixed3(b, board_adc_volts(ADC_LIS_CH) * 17.0f));
#endif
}

static void toggle(int *s, const char *name)
{
    *s = -*s;
    tele_printf("# sinal %s = %d (para fixar, mude em include/board.h)\r\n", name, *s);
}

static void handle_command(char *line)
{
    char *arg = strchr(line, ' ');
    float v = 0.0f;
    if (arg != NULL) {
        *arg++ = '\0';
        v = strtof(arg, NULL);
    }

    if (!strcmp(line, "a") || !strcmp(line, "arm")) {
        ev_button = true;
    } else if (!strcmp(line, "s") || !strcmp(line, "stop")) {
        ev_stop = true;
    } else if (!strcmp(line, "m") && arg != NULL) {
        manual_duty = v / 100.0f;
        ev_manual = true;
    } else if (!strcmp(line, "k1") && arg != NULL) {
        ctl.cfg.k1 = v;
    } else if (!strcmp(line, "k2") && arg != NULL) {
        ctl.cfg.k2 = v;
    } else if (!strcmp(line, "k3") && arg != NULL) {
        ctl.cfg.k3 = v;
    } else if (!strcmp(line, "imax") && arg != NULL && v > 0.5f && v <= 20.0f) {
        ctl.cfg.i_max = v;
    } else if (!strcmp(line, "trim") && arg != NULL && fabsf(v) <= 5.0f) {
        ctl.trim = v / 57.29578f;
    } else if (!strcmp(line, "trimg") && arg != NULL) {
        ctl.cfg.trim_gain = v;
    } else if (!strcmp(line, "rate") && arg != NULL && v >= 0.0f && v <= 1000.0f) {
        tele_div = (uint32_t)v;
    } else if (!strcmp(line, "inv") && arg != NULL) {
        if (ctl.state != RWP_IDLE) {
            tele_printf("# so com o controle parado\r\n");
        } else if (!strcmp(arg, "motor")) {
            toggle(&sign_motor, "motor");
        } else if (!strcmp(arg, "enc")) {
            toggle(&sign_enc, "enc");
        } else if (!strcmp(arg, "giro")) {
            toggle(&sign_gyro, "giro");
        } else if (!strcmp(arg, "ang")) {
            toggle(&sign_angle, "ang");
        }
        return;
    } else if (!strcmp(line, "sinais")) {
        sign_test_left = 3000;
        sign_test_sum = 0.0f;
        sign_test_prev = in.theta_acc;
        tele_printf("# balance o braco com a mao por 3 s...\r\n");
        return;
    } else if (!strcmp(line, "diag")) {
        print_diag();
        return;
    } else if (!strcmp(line, "cfg")) {
        print_cfg();
        return;
    } else {
        print_help();
        return;
    }
    if (line[0] == 'k' || line[0] == 'i' || line[0] == 't') {
        print_cfg();
    }
}

/* Evento único por aperto, com filtro de repique. */
static bool button_event(void)
{
    static uint32_t stable;
    static bool state;
    bool raw = board_key_pressed();
    if (raw == state) {
        stable = 0;
        return false;
    }
    if (++stable < DEBOUNCE_MS) {
        return false;
    }
    state = raw;
    stable = 0;
    return state;
}

/* LED: aceso = equilibrando; piscadas lentas = parado; N piscadas = código da falha. */
static void update_led(uint32_t ms)
{
    bool on;
    switch (out.state) {
    case RWP_IDLE:    on = (ms % 1000u) < 50u; break;
    case RWP_CALIB:   on = (ms % 100u) < 50u; break;
    case RWP_ARMED:   on = (ms % 500u) < 250u; break;
    case RWP_BALANCE: on = true; break;
    case RWP_MANUAL:  on = (ms % 200u) < 100u; break;
    default: {
        uint32_t t = ms % 3000u;
        on = (t / 300u) < (uint32_t)out.fault && (t % 300u) < 150u;
        break;
    }
    }
    board_led(on);
}

static void read_sensors(void)
{
    in.imu_ok = mpu6050_read(&imu);
    if (in.imu_ok) {
        in.theta_acc = (float)sign_angle * atan2f(imu.acc[IMU_ACC_SIDE_AXIS], imu.acc[IMU_ACC_UP_AXIS]);
        in.gyro = (float)sign_gyro * imu.gyro[IMU_GYRO_AXIS];
    }
    in.enc_count = sign_enc * encoder_count();
#if USE_VBUS_SENSE
    vbus = board_adc_volts(ADC_VBUS_CH) * VBUS_DIVIDER;
#else
    vbus = RWP_VBUS_NOM;
#endif
    in.vbus = vbus;
}

static void run_sign_test(void)
{
    if (sign_test_left == 0 || !in.imu_ok) {
        return;
    }
    sign_test_sum += (in.theta_acc - sign_test_prev) * in.gyro;
    sign_test_prev = in.theta_acc;
    if (--sign_test_left == 0) {
        if (fabsf(sign_test_sum) < 1e-4f) {
            tele_printf("# sinais: movimento insuficiente, repita balancando mais\r\n");
        } else if (sign_test_sum > 0.0f) {
            tele_printf("# sinais: giroscopio OK (mesmo sentido do angulo)\r\n");
        } else {
            tele_printf("# sinais: giroscopio INVERTIDO -> use \"inv giro\" e fixe em board.h\r\n");
        }
    }
}

static void send_telemetry(uint32_t ms)
{
    static rwp_state_t last_state = RWP_IDLE;

    if (out.state != last_state) {
        tele_printf("# estado: %s%s%s\r\n", rwp_state_name(out.state), out.state == RWP_FAULT ? " - " : "",
                    out.state == RWP_FAULT ? rwp_fault_name(out.fault) : "");
        if (last_state == RWP_MANUAL && fabsf(manual_duty) > 0.1f && out.omega * manual_duty < -5.0f) {
            tele_printf("# aviso: a roda girou no sentido contrario ao comando -> \"inv enc\"\r\n");
        }
        last_state = out.state;
    }
    if (tele_div != 0u && (ms % tele_div) == 0u) {
        /* D,t_ms,estado,falha,theta[mgrau],vel[mgrau/s],roda[0,1 rpm],u[mV],vbus[mV],trim[mgrau],encoder */
        tele_printf("D,%lu,%d,%d,%ld,%ld,%ld,%ld,%ld,%ld,%ld\r\n", (unsigned long)ms, (int)out.state, (int)out.fault,
                    (long)(out.theta * RAD2MDEG), (long)(out.theta_dot * RAD2MDEG), (long)(out.omega * RADS2DRPM),
                    (long)(out.u * 1000.0f), (long)(vbus * 1000.0f), (long)(out.trim * RAD2MDEG),
                    (long)in.enc_count);
    }
}

int main(void)
{
    char line[48];
    uint32_t ms = 0;

    HAL_Init();
    board_init();
    motor_apply(false, false, 0.0f, sign_motor);
    tele_init();

    rwp_config_t cfg = rwp_config_default();
    rwp_init(&ctl, &cfg);

    tele_printf("\r\n# Pendulo invertido com roda de reacao\r\n");
    if (!mpu6050_init()) {
        tele_printf("# ERRO: MPU6050 nao respondeu (confira SCL=PB6, SDA=PB7, 3V3, GND)\r\n");
    }
    print_diag();
    print_cfg();
    print_help();

    board_watchdog_start();
    board_tick_start();

    for (;;) {
        if (tele_get_line(line, sizeof(line))) {
            handle_command(line);
        }
        if (!board_tick_take()) {
            continue;
        }
        ms++;

        read_sensors();
        in.button = button_event() || ev_button;
        in.stop = ev_stop;
        in.manual_req = ev_manual;
        in.manual_duty = manual_duty;
        ev_button = ev_stop = ev_manual = false;

        rwp_step(&ctl, &in, &out);
        motor_apply(out.enable, out.brake, out.duty, sign_motor);

        run_sign_test();
        update_led(ms);
        send_telemetry(ms);
        board_watchdog_kick();
    }
}
