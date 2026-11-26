#include "rwp_control.h"

#include <math.h>
#include <string.h>

#include "lqr_gains.h"

/* Tempos da máquina de estados, em segundos. */
#define T_CALIB          1.0f    /* janela para medir o viés do giroscópio */
#define CALIB_MOTION_MAX 0.05f   /* rad/s pico a pico: mais que isso, o pêndulo se mexeu */
#define T_ENGAGE         0.10f   /* tempo dentro da janela antes de assumir o controle */
#define T_OVERSPEED      0.10f
#define T_IMU_MISS       0.005f
#define T_VBUS_LOW       0.05f
#define T_STALL          1.0f    /* corrente no limite sem parar (a pior recuperação simulada leva 0,25 s) */
#define T_MANUAL         15.0f   /* ensaio em malha aberta se desliga sozinho */
#define W_STOPPED        3.0f    /* rad/s: abaixo disso considera a roda parada */
#define TICKS_MAX        1000000u
#define BASE_MIN         8u      /* períodos: base de tempo mínima do estimador de velocidade */
#define BASE_MAX         100u    /* períodos: não usa contagens mais velhas que isso */

static float clampf(float v, float lo, float hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

/* Ângulo em [-pi, pi]. */
static float wrap_pi(float a)
{
    const float pi = 3.14159265358979f;
    while (a > pi) {
        a -= 2.0f * pi;
    }
    while (a < -pi) {
        a += 2.0f * pi;
    }
    return a;
}

static uint32_t ticks(const rwp_t *c, float seconds)
{
    return (uint32_t)(seconds / c->cfg.ts + 0.5f);
}

rwp_config_t rwp_config_default(void)
{
    rwp_config_t g = {
        .k1 = RWP_K1, .k2 = RWP_K2, .k3 = RWP_K3, .ts = RWP_TS,
        .u_frac = RWP_U_FRAC, .i_max = RWP_I_MAX, .ke = RWP_KE, .r_motor = RWP_R_MOTOR,
        .vbus_min = RWP_VBUS_MIN, .vbus_max = RWP_VBUS_MAX,
        .alpha_cf = RWP_ALPHA_CF, .alpha_w = RWP_ALPHA_W, .rad_per_count = RWP_RAD_PER_COUNT,
        .trim_gain = RWP_TRIM_GAIN, .trim_max = RWP_TRIM_MAX,
        .theta_cut = RWP_THETA_CUT, .theta_engage = RWP_THETA_ENGAGE,
        .thetadot_engage = RWP_THETADOT_ENGAGE, .w_max = RWP_W_MAX,
        .manual_duty_max = 0.45f,   /* em vazio fica abaixo do limite de rotação */
        .law = RWP_LAW_LQR,
        .q1 = RWP_Q1, .q2 = RWP_Q2, .q3 = RWP_Q3, .q4 = RWP_Q4,
        .kp = RWP_PID_KP, .ki = RWP_PID_KI, .kd = RWP_PID_KD, .kw = RWP_PID_KW, .kwi = RWP_PID_KWI,
        .pid_i_max = RWP_PID_I_MAX,
    };
    return g;
}

void rwp_init(rwp_t *c, const rwp_config_t *cfg)
{
    memset(c, 0, sizeof(*c));
    c->cfg = *cfg;
    c->state = RWP_IDLE;
    c->fault = RWP_FAULT_NONE;
    c->ev_n = 1;   /* evento inicial: contagem 0 no instante 0 */
}

float rwp_lqr_law(const rwp_config_t *g, float theta_e, float theta_dot, float omega, float vbus)
{
    float u = -(g->k1 * theta_e + g->k2 * theta_dot + g->k3 * omega);

    /* limite de corrente pelo modelo do motor: i = (u - ke*omega) / R */
    float bemf = g->ke * omega;
    u = clampf(u, bemf - g->r_motor * g->i_max, bemf + g->r_motor * g->i_max);

    /* limite de tensão */
    float um = g->u_frac * vbus;
    return clampf(u, -um, um);
}

/* Anti-windup do integrador da roda [rad]: o efeito dele fica limitado ao mesmo
   ângulo de equilíbrio equivalente do auto-ajuste (trim_max). */
static float phi_max(const rwp_config_t *g)
{
    if (g->law == RWP_LAW_LQI && g->q4 != 0.0f) {
        return g->trim_max * fabsf(g->q1 / g->q4);
    }
    if (g->law == RWP_LAW_PID && g->kwi != 0.0f) {
        return g->trim_max / g->kwi;
    }
    return 1e30f;
}

float rwp_balance_law(rwp_t *c, float theta, float theta_dot, float omega, float phi, float vbus)
{
    const rwp_config_t *g = &c->cfg;
    float z = phi - c->phi_ref;
    if (c->int_sat) {               /* congela: a roda anda, o integrador não */
        z = c->z_prev;
        c->phi_ref = phi - z;
    }
    float zm = phi_max(g);
    if (fabsf(z) > zm) {
        z = copysignf(zm, z);
        c->phi_ref = phi - z;
    }
    c->z_prev = z;

    float u0;
    if (g->law == RWP_LAW_LQI) {
        u0 = -(g->q1 * theta + g->q2 * theta_dot + g->q3 * omega + g->q4 * z);
        c->ref = -g->q4 * z / g->q1;
    } else {
        c->ref = clampf(-(g->kw * omega + g->kwi * z), -g->trim_max, g->trim_max);
        float e = theta - c->ref;
        if (!c->int_sat) {
            c->i_e = clampf(c->i_e + e * g->ts, -g->pid_i_max, g->pid_i_max);
        }
        u0 = g->kp * e + g->ki * c->i_e + g->kd * theta_dot;
    }

    /* mesmos limites de corrente e de tensão do LQR */
    float bemf = g->ke * omega;
    float u = clampf(u0, bemf - g->r_motor * g->i_max, bemf + g->r_motor * g->i_max);
    float um = g->u_frac * vbus;
    u = clampf(u, -um, um);
    c->int_sat = fabsf(u) >= 0.9f * um;
    return u;
}

static void reset_integrators(rwp_t *c)
{
    c->phi_ref = (float)c->cnt_prev * c->cfg.rad_per_count;
    c->z_prev = 0.0f;
    c->i_e = 0.0f;
    c->ref = 0.0f;
    c->int_sat = false;
}

bool rwp_set_law(rwp_t *c, rwp_law_t law)
{
    if (c->state == RWP_BALANCE || (unsigned)law > (unsigned)RWP_LAW_PID) {
        return false;
    }
    c->cfg.law = law;
    reset_integrators(c);
    return true;
}

static void push_event(rwp_t *c, uint32_t tick, int32_t count)
{
    c->ev_head = (uint8_t)((c->ev_head + 1u) % RWP_N_EVENTS);
    c->ev_tick[c->ev_head] = tick;
    c->ev_cnt[c->ev_head] = count;
    if (c->ev_n < RWP_N_EVENTS) {
        c->ev_n++;
    }
}

/* j-ésimo evento mais antigo que o mais recente (j = 0 é o mais recente). */
static unsigned ev_index(const rwp_t *c, unsigned j)
{
    return (c->ev_head + RWP_N_EVENTS - j) % RWP_N_EVENTS;
}

/*
 * Dividir a variação de contagem por um único período daria um trem de pulsos
 * em baixa rotação (chega menos de uma contagem por período). Aqui cada
 * mudança de contagem é guardada com o instante em que ocorreu e a velocidade
 * é a variação entre a mais recente e uma anterior que esteja a pelo menos
 * BASE_MIN períodos de distância. Sem contagens novas, a estimativa é limitada
 * por 1 contagem / tempo decorrido. Mesma lógica de Controlador.velocidade_roda().
 */
float rwp_wheel_speed(rwp_t *c, int32_t count)
{
    const rwp_config_t *g = &c->cfg;
    float w = 0.0f;

    c->now++;
    if (count != c->cnt_prev) {
        c->cnt_prev = count;
        push_event(c, c->now, count);
    }
    if (c->ev_n >= 2) {
        uint32_t t_new = c->ev_tick[c->ev_head];
        unsigned j = 1;
        while (j + 1 <= (unsigned)c->ev_n - 1u) {
            if (t_new - c->ev_tick[ev_index(c, j)] >= BASE_MIN) {
                break;
            }
            if (t_new - c->ev_tick[ev_index(c, j + 1)] > BASE_MAX) {
                break;
            }
            j++;
        }
        unsigned k = ev_index(c, j);
        /* subtrações sem sinal: continuam certas quando os contadores dão a volta */
        int32_t dc = (int32_t)((uint32_t)c->ev_cnt[c->ev_head] - (uint32_t)c->ev_cnt[k]);
        uint32_t dt = t_new - c->ev_tick[k];
        w = (float)dc * g->rad_per_count / ((float)dt * g->ts);

        uint32_t stale = c->now - t_new;
        if (stale > 0) {
            float cap = g->rad_per_count / ((float)stale * g->ts);
            w = clampf(w, -cap, cap);
        }
    }
    c->w_raw = w;
    c->omega += g->alpha_w * (w - c->omega);
    return c->omega;
}

static void enter(rwp_t *c, rwp_state_t s)
{
    c->state = s;
    c->t_state = 0;
    c->n_engage = c->n_overspeed = c->n_vbus_low = c->n_sat = 0;
    if (s == RWP_CALIB) {
        c->n_calib = 0;
        c->calib_sum = 0.0f;
    }
    if (s == RWP_IDLE) {
        c->fault = RWP_FAULT_NONE;
    }
    if (s == RWP_BALANCE) {
        reset_integrators(c);
    }
}

static void fail(rwp_t *c, rwp_fault_t f)
{
    enter(c, RWP_FAULT);
    c->fault = f;
}

/* Falhas que valem sempre que o motor está energizado. Retorna true se falhou. */
static bool check_running_faults(rwp_t *c, const rwp_inputs_t *in)
{
    const rwp_config_t *g = &c->cfg;

    if (in->vbus > g->vbus_max) {
        fail(c, RWP_FAULT_VBUS_HIGH);
        return true;
    }
    c->n_vbus_low = (in->vbus < g->vbus_min) ? c->n_vbus_low + 1 : 0;
    if (c->n_vbus_low > ticks(c, T_VBUS_LOW)) {
        fail(c, RWP_FAULT_VBUS_LOW);
        return true;
    }
    c->n_overspeed = (fabsf(c->omega) > g->w_max) ? c->n_overspeed + 1 : 0;
    if (c->n_overspeed > ticks(c, T_OVERSPEED)) {
        fail(c, RWP_FAULT_OVERSPEED);
        return true;
    }
    return false;
}

void rwp_step(rwp_t *c, const rwp_inputs_t *in, rwp_outputs_t *out)
{
    const rwp_config_t *g = &c->cfg;
    float u = 0.0f, duty = 0.0f;
    bool enable = false, brake = false;

    /* ---- estimadores: rodam em todos os estados ---- */
    float gyro = in->gyro - c->gyro_bias;
    if (in->imu_ok) {
        /* filtro complementar na forma "predição + correção": para ângulos
           pequenos é igual a alpha*(theta + gyro*ts) + (1-alpha)*theta_acc,
           e continua certo perto de +-180 graus (pêndulo pendurado), onde o
           ângulo do acelerômetro dá a volta */
        float pred = c->theta + gyro * g->ts;
        c->theta = wrap_pi(pred + (1.0f - g->alpha_cf) * wrap_pi(in->theta_acc - pred));
        c->theta_dot = gyro;
        c->n_imu_miss = 0;
    } else if (c->n_imu_miss < TICKS_MAX) {
        c->n_imu_miss++;
    }
    rwp_wheel_speed(c, in->enc_count);
    c->t_state++;

    /* ---- máquina de estados ---- */
    switch (c->state) {
    case RWP_IDLE:
        if (!in->imu_ok) {
            /* sem IMU não há ângulo: parte do acelerômetro quando voltar */
        } else if (c->t_state < 3) {
            c->theta = in->theta_acc;
        }
        if (in->button) {
            if (c->n_imu_miss > 0) {
                fail(c, RWP_FAULT_IMU);
            } else if (in->vbus < g->vbus_min) {
                fail(c, RWP_FAULT_VBUS_LOW);
            } else {
                enter(c, RWP_CALIB);
            }
        } else if (in->manual_req) {
            if (in->vbus < g->vbus_min) {
                fail(c, RWP_FAULT_VBUS_LOW);
            } else {
                c->manual_duty = clampf(in->manual_duty, -g->manual_duty_max, g->manual_duty_max);
                enter(c, RWP_MANUAL);
            }
        }
        break;

    case RWP_CALIB:
        if (in->button || in->stop) {
            enter(c, RWP_IDLE);
            break;
        }
        if (!in->imu_ok) {
            if (c->n_imu_miss > ticks(c, T_IMU_MISS)) {
                fail(c, RWP_FAULT_IMU);
            }
            break;
        }
        if (c->n_calib == 0) {
            c->calib_min = c->calib_max = in->gyro;
        }
        c->calib_sum += in->gyro;
        c->calib_min = fminf(c->calib_min, in->gyro);
        c->calib_max = fmaxf(c->calib_max, in->gyro);
        c->n_calib++;
        if (c->calib_max - c->calib_min > CALIB_MOTION_MAX) {
            c->n_calib = 0;          /* mexeu: recomeça a janela */
            c->calib_sum = 0.0f;
        } else if (c->n_calib >= ticks(c, T_CALIB)) {
            c->gyro_bias = c->calib_sum / (float)c->n_calib;
            c->theta = in->theta_acc;   /* parado: o acelerômetro dá o ângulo certo */
            enter(c, RWP_ARMED);
        }
        break;

    case RWP_ARMED:
        if (in->button || in->stop) {
            enter(c, RWP_IDLE);
            break;
        }
        if (c->n_imu_miss > ticks(c, T_IMU_MISS)) {
            fail(c, RWP_FAULT_IMU);
            break;
        }
        if (fabsf(c->theta - c->trim) < g->theta_engage && fabsf(c->theta_dot) < g->thetadot_engage) {
            if (++c->n_engage >= ticks(c, T_ENGAGE)) {
                enter(c, RWP_BALANCE);
            }
        } else {
            c->n_engage = 0;
        }
        break;

    case RWP_BALANCE: {
        if (in->button || in->stop) {
            enter(c, RWP_IDLE);
            break;
        }
        if (c->n_imu_miss > ticks(c, T_IMU_MISS)) {
            fail(c, RWP_FAULT_IMU);
            break;
        }
        if (fabsf(c->theta - c->trim) > g->theta_cut) {
            fail(c, RWP_FAULT_ANGLE);
            break;
        }
        if (check_running_faults(c, in)) {
            break;
        }
        if (g->law == RWP_LAW_LQR) {
            u = rwp_lqr_law(g, c->theta - c->trim, c->theta_dot, c->omega, in->vbus);
        } else {
            u = rwp_balance_law(c, c->theta, c->theta_dot, c->omega,
                                (float)in->enc_count * g->rad_per_count, in->vbus);
        }
        duty = u / in->vbus;
        enable = true;

        bool saturated = fabsf(u) >= 0.9f * g->u_frac * in->vbus;
        float i_model = (u - g->ke * c->omega) / g->r_motor;
        c->n_sat = (fabsf(i_model) > 0.97f * g->i_max) ? c->n_sat + 1 : 0;
        if (c->n_sat > ticks(c, T_STALL)) {
            fail(c, RWP_FAULT_STALL);
            break;
        }
        if (!saturated && g->law == RWP_LAW_LQR) {
            c->trim = clampf(c->trim + g->trim_gain * c->omega * g->ts, -g->trim_max, g->trim_max);
        }
        break;
    }

    case RWP_MANUAL:
        if (in->button || in->stop || c->t_state > ticks(c, T_MANUAL)) {
            enter(c, RWP_IDLE);
            break;
        }
        if (check_running_faults(c, in)) {
            break;
        }
        if (in->manual_req) {
            c->manual_duty = clampf(in->manual_duty, -g->manual_duty_max, g->manual_duty_max);
        }
        duty = c->manual_duty;
        u = duty * in->vbus;
        enable = true;
        break;

    case RWP_FAULT:
    default:
        if (in->button || in->stop) {
            enter(c, RWP_IDLE);
        }
        break;
    }

    /* Em falha (inclusive no período em que ela acontece): tensão zero e freio
       dinâmico até a roda parar. A energia vira calor no motor em vez de
       voltar para a fonte. */
    if (c->state == RWP_FAULT) {
        u = duty = 0.0f;
        brake = fabsf(c->omega) > W_STOPPED;
        enable = brake;
    }

    out->u = u;
    out->duty = clampf(duty, -g->u_frac, g->u_frac);
    out->enable = enable;
    out->brake = brake;
    out->state = c->state;
    out->fault = c->fault;
    out->theta = c->theta;
    out->theta_dot = c->theta_dot;
    out->omega = c->omega;
    out->trim = (g->law == RWP_LAW_LQR) ? c->trim : c->ref;
}

void rwp_test_force_balance(rwp_t *c, float theta0)
{
    c->state = RWP_BALANCE;
    c->fault = RWP_FAULT_NONE;
    c->theta = theta0;
    c->theta_dot = 0.0f;
    c->omega = c->w_raw = 0.0f;
    c->gyro_bias = 0.0f;
    c->trim = 0.0f;
    c->cnt_prev = 0;
    c->now = 0;
    memset(c->ev_tick, 0, sizeof(c->ev_tick));
    memset(c->ev_cnt, 0, sizeof(c->ev_cnt));
    c->ev_head = 0;
    c->ev_n = 1;
    c->t_state = 0;
    c->n_engage = c->n_overspeed = c->n_imu_miss = c->n_vbus_low = c->n_sat = 0;
    reset_integrators(c);
}

const char *rwp_state_name(rwp_state_t s)
{
    static const char *const names[] = {"PARADO", "CALIBRA", "ARMADO", "EQUILIBRA", "MANUAL", "FALHA"};
    return ((unsigned)s < sizeof(names) / sizeof(names[0])) ? names[s] : "?";
}

const char *rwp_law_name(rwp_law_t l)
{
    static const char *const names[] = {"LQR", "LQI", "PID"};
    return ((unsigned)l < sizeof(names) / sizeof(names[0])) ? names[l] : "?";
}

const char *rwp_fault_name(rwp_fault_t f)
{
    static const char *const names[] = {
        "nenhuma", "inclinacao", "rotacao da roda", "MPU6050", "sem tensao", "sobretensao", "motor travado",
    };
    return ((unsigned)f < sizeof(names) / sizeof(names[0])) ? names[f] : "?";
}
