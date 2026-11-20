/*
 * Testes da lógica de controle no PC:  pio test -e native
 *
 * Conferem o código C contra a referência em Python (vectors.h, gerado por
 * sim/export_gains.py) e exercitam a máquina de estados contra um modelo da
 * planta, sem precisar de hardware.
 */
#include <math.h>
#include <stdint.h>
#include <unity.h>

#include "lqr_gains.h"
#include "rwp_control.h"
#include "vectors.h"

#define DEG (3.14159265358979f / 180.0f)

static rwp_t c;
static rwp_config_t cfg;

void setUp(void)
{
    cfg = rwp_config_default();
    rwp_init(&c, &cfg);
}

void tearDown(void) {}

/* ------------------------------------------------------------------------- */
/* Modelo da planta (mesmas equações de sim/model.py, indutância desprezada)  */
/* ------------------------------------------------------------------------- */
typedef struct {
    double th, thd, om, phi;
} plant_t;

/* hold != 0: braço preso (na mão ou no batente); só a roda se move. */
static void plant_deriv(const plant_t *x, double v, int hold, double *dth, double *dthd, double *dom)
{
    double i = (v - PLANT_KE * x->om) / PLANT_R;
    double tau = PLANT_KT * i - (PLANT_TAU_C * tanh(x->om) + PLANT_B * x->om);
    if (hold) {
        *dth = 0.0;
        *dthd = 0.0;
        *dom = tau / PLANT_IW;
        return;
    }
    double thdd = (PLANT_MGL * sin(x->th) - PLANT_BP * x->thd - tau) / PLANT_J;
    *dth = x->thd;
    *dthd = thdd;
    *dom = tau / PLANT_IW - thdd;
}

/* Tensão que o motor realmente vê: ponte desligada = corrente zero; freio = curto. */
static double motor_voltage(double v, double om, int brake, int enabled)
{
    if (!enabled) {
        return PLANT_KE * om;
    }
    return brake ? 0.0 : v;
}

/* Um período de 1 ms em 4 subpassos de ponto médio. */
static void plant_step(plant_t *x, double v, int brake, int enabled, int hold)
{
    const double dt = RWP_TS / 4.0;
    for (int k = 0; k < 4; k++) {
        double a, b, d, a2, b2, d2;
        plant_t m = *x;
        plant_deriv(x, motor_voltage(v, x->om, brake, enabled), hold, &a, &b, &d);
        m.th += 0.5 * dt * a;
        m.thd += 0.5 * dt * b;
        m.om += 0.5 * dt * d;
        plant_deriv(&m, motor_voltage(v, m.om, brake, enabled), hold, &a2, &b2, &d2);
        x->th += dt * a2;
        x->thd += dt * b2;
        x->phi += dt * m.om;
        x->om += dt * d2;
    }
}

static rwp_inputs_t sense(const plant_t *x)
{
    rwp_inputs_t in = {0};
    in.theta_acc = (float)x->th;
    in.gyro = (float)x->thd;
    in.enc_count = (int32_t)floor(x->phi / RWP_RAD_PER_COUNT);
    in.vbus = RWP_VBUS_NOM;
    in.imu_ok = true;
    return in;
}

/* Roda a malha fechada por n períodos. hold != 0: braço preso, só a roda se move. */
static rwp_outputs_t run(plant_t *x, int n, int hold)
{
    rwp_outputs_t out = {0};
    for (int k = 0; k < n; k++) {
        rwp_inputs_t in = sense(x);
        rwp_step(&c, &in, &out);
        plant_step(x, out.duty * RWP_VBUS_NOM, out.brake, out.enable, hold);
    }
    return out;
}

static void press_button(plant_t *x)
{
    rwp_inputs_t in = sense(x);
    rwp_outputs_t out;
    in.button = true;
    rwp_step(&c, &in, &out);
}

/* Liga, calibra parado no batente e leva à vertical: termina equilibrando. */
static void start_balancing(plant_t *x)
{
    x->th = 22.0 * DEG;                 /* encostado no batente */
    press_button(x);
    TEST_ASSERT_EQUAL(RWP_CALIB, c.state);
    run(x, 1100, 1);
    TEST_ASSERT_EQUAL(RWP_ARMED, c.state);
    x->thd = -21.0 * DEG / 0.4;         /* mão levando até 1 grau da vertical em 0,4 s */
    for (int k = 0; k < 400; k++) {
        x->th += x->thd * RWP_TS;
        run(x, 1, 1);
    }
    x->thd = 0.0;
    run(x, 300, 1);                     /* segura parado: o controle assume */
    TEST_ASSERT_EQUAL(RWP_BALANCE, c.state);
}

/* ------------------------------------------------------------------------- */
/* C contra a referência em Python                                            */
/* ------------------------------------------------------------------------- */
static void test_lei_de_controle_igual_ao_python(void)
{
    for (int k = 0; k < N_LAW; k++) {
        const float *v = LAW_VEC[k];
        float u = rwp_lqr_law(&cfg, v[0], v[1], v[2], v[3]);
        TEST_ASSERT_FLOAT_WITHIN(2e-3f, v[4], u);
    }
}

static void test_sequencia_em_malha_fechada_igual_ao_python(void)
{
    rwp_outputs_t out;
    float pior = 0.0f;
    rwp_test_force_balance(&c, SEQ_THETA0);
    for (int k = 0; k < N_SEQ; k++) {
        rwp_inputs_t in = {0};
        in.theta_acc = SEQ_VEC[k][0];
        in.gyro = SEQ_VEC[k][1];
        in.enc_count = SEQ_COUNT[k];
        in.vbus = SEQ_VBUS;
        in.imu_ok = true;
        rwp_step(&c, &in, &out);
        TEST_ASSERT_EQUAL(RWP_BALANCE, out.state);
        float erro = fabsf(out.u - SEQ_VEC[k][2]);
        if (erro > pior) {
            pior = erro;
        }
    }
    /* estimadores + lei + auto-ajuste: diferença só de arredondamento float/double */
    TEST_ASSERT_FLOAT_WITHIN(0.02f, 0.0f, pior);
}

/* ------------------------------------------------------------------------- */
/* Estimador de velocidade                                                     */
/* ------------------------------------------------------------------------- */
static void test_velocidade_da_roda(void)
{
    const float alvos[] = {1.0f, 3.0f, 20.0f, 30.0f, 47.0f, 150.0f, -80.0f, -200.0f};
    for (unsigned a = 0; a < sizeof(alvos) / sizeof(alvos[0]); a++) {
        double phi = 0.0;
        float w = 0.0f;
        rwp_init(&c, &cfg);
        for (int k = 0; k < 3000; k++) {
            phi += alvos[a] * RWP_TS;
            w = rwp_wheel_speed(&c, (int32_t)floor(phi / RWP_RAD_PER_COUNT));
        }
        TEST_ASSERT_FLOAT_WITHIN(fabsf(alvos[a]) * 0.08f + 0.5f, alvos[a], w);
    }
}

static void test_velocidade_decai_com_a_roda_parada(void)
{
    double phi = 0.0;
    float w = 0.0f;
    for (int k = 0; k < 500; k++) {
        phi += 30.0 * RWP_TS;
        w = rwp_wheel_speed(&c, (int32_t)floor(phi / RWP_RAD_PER_COUNT));
    }
    TEST_ASSERT_FLOAT_WITHIN(3.0f, 30.0f, w);
    int32_t parado = (int32_t)floor(phi / RWP_RAD_PER_COUNT);
    for (int k = 0; k < 1500; k++) {
        w = rwp_wheel_speed(&c, parado);
    }
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 0.0f, w);
}

static void test_contador_de_32_bits_dando_a_volta(void)
{
    int32_t cnt = INT32_MAX - 20;
    float w = 0.0f;
    c.cnt_prev = cnt;
    c.ev_cnt[c.ev_head] = cnt;
    for (int k = 0; k < 400; k++) {
        cnt = (int32_t)((uint32_t)cnt + 1u);   /* passa de INT32_MAX para INT32_MIN */
        w = rwp_wheel_speed(&c, cnt);
    }
    TEST_ASSERT_FLOAT_WITHIN(1.0f, RWP_RAD_PER_COUNT / RWP_TS, w);
}

/* ------------------------------------------------------------------------- */
/* Máquina de estados contra a planta                                          */
/* ------------------------------------------------------------------------- */
static void test_filtro_continuo_perto_de_180_graus(void)
{
    /* pêndulo pendurado oscilando em torno de 180 graus: o acelerômetro dá a
       volta entre +179 e -179 e a estimativa não pode pular para perto de zero */
    rwp_outputs_t out;
    float pior = 0.0f;
    for (int k = 0; k < 4000; k++) {
        double t = k * RWP_TS;
        double th = 3.14159265358979 + 0.15 * sin(9.0 * t);
        rwp_inputs_t in = {0};
        in.theta_acc = (float)atan2(sin(th), cos(th));
        in.gyro = (float)(0.15 * 9.0 * cos(9.0 * t));
        in.vbus = RWP_VBUS_NOM;
        in.imu_ok = true;
        rwp_step(&c, &in, &out);
        if (k > 100) {
            float erro = fabsf(remainderf(out.theta - in.theta_acc, 6.2831853f));
            if (erro > pior) {
                pior = erro;
            }
        }
    }
    TEST_ASSERT_TRUE(pior < 0.02f);
    TEST_ASSERT_TRUE(fabsf(out.theta) > 2.9f);
}

static void test_parado_nao_energiza_o_motor(void)
{
    plant_t x = {.th = 22.0 * DEG};
    rwp_outputs_t out = run(&x, 500, 1);
    TEST_ASSERT_EQUAL(RWP_IDLE, out.state);
    TEST_ASSERT_FALSE(out.enable);
    TEST_ASSERT_EQUAL_FLOAT(0.0f, out.duty);
}

static void test_calibra_arma_e_equilibra(void)
{
    plant_t x = {0};
    start_balancing(&x);
    rwp_outputs_t out = run(&x, 4000, 0);     /* 4 s solto */
    TEST_ASSERT_EQUAL(RWP_BALANCE, out.state);
    TEST_ASSERT_TRUE(out.enable);
    TEST_ASSERT_TRUE(fabs(x.th) < 1.0 * DEG);
    TEST_ASSERT_TRUE(fabs(x.thd) < 0.2);
    TEST_ASSERT_TRUE(fabs(x.om) < RWP_W_MAX);
}

static void test_calibracao_espera_o_pendulo_parar(void)
{
    plant_t x = {.th = 22.0 * DEG};
    press_button(&x);
    for (int k = 0; k < 3000; k++) {          /* 3 s balançando na mão */
        x.thd = 0.5 * sin(k * 0.02);
        run(&x, 1, 1);
    }
    TEST_ASSERT_EQUAL(RWP_CALIB, c.state);
    x.thd = 0.0;
    run(&x, 1100, 1);
    TEST_ASSERT_EQUAL(RWP_ARMED, c.state);
}

static void test_calibracao_remove_o_vies_do_giroscopio(void)
{
    rwp_outputs_t out;
    rwp_inputs_t in = {.theta_acc = 0.3f, .gyro = 0.02f, .vbus = RWP_VBUS_NOM, .imu_ok = true};
    in.button = true;
    rwp_step(&c, &in, &out);
    in.button = false;
    for (int k = 0; k < 1100; k++) {
        rwp_step(&c, &in, &out);
    }
    TEST_ASSERT_EQUAL(RWP_ARMED, out.state);
    TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.02f, c.gyro_bias);
    TEST_ASSERT_FLOAT_WITHIN(1e-3f, 0.0f, out.theta_dot);
    TEST_ASSERT_FLOAT_WITHIN(1e-3f, 0.3f, out.theta);
}

static void test_nao_assume_o_controle_longe_da_vertical(void)
{
    plant_t x = {.th = 22.0 * DEG};
    press_button(&x);
    run(&x, 1100, 1);
    TEST_ASSERT_EQUAL(RWP_ARMED, c.state);
    x.th = 8.0 * DEG;
    rwp_outputs_t out = run(&x, 2000, 1);
    TEST_ASSERT_EQUAL(RWP_ARMED, out.state);
    TEST_ASSERT_FALSE(out.enable);
}

static void test_rejeita_peteleco(void)
{
    plant_t x = {0};
    start_balancing(&x);
    run(&x, 1000, 0);
    x.thd += 2.0;
    rwp_outputs_t out = run(&x, 4000, 0);
    TEST_ASSERT_EQUAL(RWP_BALANCE, out.state);
    TEST_ASSERT_TRUE(fabs(x.th) < 1.5 * DEG);
}

static void test_queda_desliga_e_freia_a_roda(void)
{
    plant_t x = {0};
    start_balancing(&x);
    run(&x, 500, 0);
    x.thd += 8.0;                               /* empurrão que não tem volta */
    rwp_outputs_t out = {0};
    for (int k = 0; k < 2000 && c.state == RWP_BALANCE; k++) {
        out = run(&x, 1, 0);
        if (fabs(x.th) > 25.0 * DEG) {          /* batente */
            x.th = copysign(25.0 * DEG, x.th);
            x.thd = 0.0;
        }
    }
    TEST_ASSERT_EQUAL(RWP_FAULT, out.state);
    TEST_ASSERT_EQUAL(RWP_FAULT_ANGLE, out.fault);
    TEST_ASSERT_EQUAL_FLOAT(0.0f, out.duty);
    TEST_ASSERT_TRUE(out.brake);                /* roda ainda girando: freia */
    TEST_ASSERT_TRUE(out.enable);
    x.thd = 0.0;                                /* caiu e ficou no batente */
    out = run(&x, 6000, 1);
    TEST_ASSERT_FALSE(out.enable);              /* roda parada: ponte desligada */
    TEST_ASSERT_TRUE(fabs(x.om) < 5.0);
    press_button(&x);
    TEST_ASSERT_EQUAL(RWP_IDLE, c.state);
    TEST_ASSERT_EQUAL(RWP_FAULT_NONE, c.fault);
}

static void test_botao_para_o_equilibrio(void)
{
    plant_t x = {0};
    start_balancing(&x);
    press_button(&x);
    rwp_outputs_t out = run(&x, 10, 1);
    TEST_ASSERT_EQUAL(RWP_IDLE, out.state);
    TEST_ASSERT_FALSE(out.enable);
}

static void test_falha_do_mpu6050(void)
{
    plant_t x = {0};
    rwp_outputs_t out;
    start_balancing(&x);
    for (int k = 0; k < 20; k++) {
        rwp_inputs_t in = sense(&x);
        in.imu_ok = false;
        rwp_step(&c, &in, &out);
    }
    TEST_ASSERT_EQUAL(RWP_FAULT, out.state);
    TEST_ASSERT_EQUAL(RWP_FAULT_IMU, out.fault);
    TEST_ASSERT_EQUAL_FLOAT(0.0f, out.duty);
}

static void test_uma_leitura_perdida_do_mpu6050_nao_derruba(void)
{
    plant_t x = {0};
    rwp_outputs_t out;
    start_balancing(&x);
    rwp_inputs_t in = sense(&x);
    in.imu_ok = false;
    rwp_step(&c, &in, &out);
    TEST_ASSERT_EQUAL(RWP_BALANCE, out.state);
    out = run(&x, 2000, 0);
    TEST_ASSERT_EQUAL(RWP_BALANCE, out.state);
}

static void test_falta_de_tensao_durante_o_equilibrio(void)
{
    plant_t x = {0};
    rwp_outputs_t out;
    start_balancing(&x);
    for (int k = 0; k < 100; k++) {
        rwp_inputs_t in = sense(&x);
        in.vbus = 0.3f;                         /* a fonte caiu ou o B+ soltou */
        rwp_step(&c, &in, &out);
    }
    TEST_ASSERT_EQUAL(RWP_FAULT_VBUS_LOW, out.fault);
}

static void test_nao_arma_sem_tensao(void)
{
    rwp_outputs_t out;
    rwp_inputs_t in = {.theta_acc = 0.3f, .vbus = 0.2f, .imu_ok = true, .button = true};
    rwp_step(&c, &in, &out);
    TEST_ASSERT_EQUAL(RWP_FAULT, out.state);
    TEST_ASSERT_EQUAL(RWP_FAULT_VBUS_LOW, out.fault);
    TEST_ASSERT_FALSE(out.enable);
}

static void test_sobretensao_desliga_na_hora(void)
{
    plant_t x = {0};
    rwp_outputs_t out;
    start_balancing(&x);
    rwp_inputs_t in = sense(&x);
    in.vbus = 18.0f;
    rwp_step(&c, &in, &out);
    TEST_ASSERT_EQUAL(RWP_FAULT_VBUS_HIGH, out.fault);
    TEST_ASSERT_EQUAL_FLOAT(0.0f, out.duty);
}

static void test_motor_travado_desliga(void)
{
    /* braço preso inclinado com o controle ligado: corrente no limite sem parar */
    plant_t x = {0};
    start_balancing(&x);
    x.th = 15.0 * DEG;
    rwp_outputs_t out = {0};
    for (int k = 0; k < 3000 && c.state == RWP_BALANCE; k++) {
        rwp_inputs_t in = sense(&x);
        in.enc_count = 0;                       /* roda travada */
        rwp_step(&c, &in, &out);
    }
    TEST_ASSERT_EQUAL(RWP_FAULT, out.state);
    TEST_ASSERT_EQUAL(RWP_FAULT_STALL, out.fault);
}

static void test_ensaio_manual_limita_e_expira(void)
{
    plant_t x = {.th = 22.0 * DEG};
    rwp_outputs_t out;
    rwp_inputs_t in = sense(&x);
    in.manual_req = true;
    in.manual_duty = 0.9f;                      /* pedido acima do permitido */
    rwp_step(&c, &in, &out);
    TEST_ASSERT_EQUAL(RWP_MANUAL, c.state);
    out = run(&x, 100, 1);
    TEST_ASSERT_TRUE(out.enable);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, cfg.manual_duty_max, out.duty);
    in = sense(&x);
    in.manual_req = true;
    in.manual_duty = 0.25f;                     /* novo pedido durante o ensaio */
    rwp_step(&c, &in, &out);
    out = run(&x, 100, 1);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.25f, out.duty);
    out = run(&x, 16000, 1);                    /* passa do tempo máximo */
    TEST_ASSERT_EQUAL(RWP_IDLE, out.state);
    TEST_ASSERT_FALSE(out.enable);
}

static void test_ensaio_manual_corta_por_rotacao(void)
{
    plant_t x = {.th = 22.0 * DEG};
    rwp_outputs_t out;
    cfg.w_max = 60.0f;                          /* limite baixo para o teste */
    rwp_init(&c, &cfg);
    rwp_inputs_t in = sense(&x);
    in.manual_req = true;
    in.manual_duty = 0.5f;
    rwp_step(&c, &in, &out);
    out = run(&x, 5000, 1);
    TEST_ASSERT_EQUAL(RWP_FAULT, out.state);
    TEST_ASSERT_EQUAL(RWP_FAULT_OVERSPEED, out.fault);
}

static void test_ciclo_nunca_passa_do_limite(void)
{
    plant_t x = {0};
    start_balancing(&x);
    for (int k = 0; k < 3000; k++) {
        if (k % 500 == 100) {
            x.thd += (k % 1000 == 100) ? 2.5 : -2.5;
        }
        rwp_outputs_t out = run(&x, 1, 0);
        TEST_ASSERT_TRUE(fabsf(out.duty) <= cfg.u_frac + 1e-6f);
    }
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_lei_de_controle_igual_ao_python);
    RUN_TEST(test_sequencia_em_malha_fechada_igual_ao_python);
    RUN_TEST(test_velocidade_da_roda);
    RUN_TEST(test_velocidade_decai_com_a_roda_parada);
    RUN_TEST(test_contador_de_32_bits_dando_a_volta);
    RUN_TEST(test_filtro_continuo_perto_de_180_graus);
    RUN_TEST(test_parado_nao_energiza_o_motor);
    RUN_TEST(test_calibra_arma_e_equilibra);
    RUN_TEST(test_calibracao_espera_o_pendulo_parar);
    RUN_TEST(test_calibracao_remove_o_vies_do_giroscopio);
    RUN_TEST(test_nao_assume_o_controle_longe_da_vertical);
    RUN_TEST(test_rejeita_peteleco);
    RUN_TEST(test_queda_desliga_e_freia_a_roda);
    RUN_TEST(test_botao_para_o_equilibrio);
    RUN_TEST(test_falha_do_mpu6050);
    RUN_TEST(test_uma_leitura_perdida_do_mpu6050_nao_derruba);
    RUN_TEST(test_falta_de_tensao_durante_o_equilibrio);
    RUN_TEST(test_nao_arma_sem_tensao);
    RUN_TEST(test_sobretensao_desliga_na_hora);
    RUN_TEST(test_motor_travado_desliga);
    RUN_TEST(test_ensaio_manual_limita_e_expira);
    RUN_TEST(test_ensaio_manual_corta_por_rotacao);
    RUN_TEST(test_ciclo_nunca_passa_do_limite);
    return UNITY_END();
}
