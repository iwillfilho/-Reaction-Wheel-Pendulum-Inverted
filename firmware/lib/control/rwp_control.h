/*
 * Controle do pêndulo invertido com roda de reação.
 *
 * C puro, sem dependência de hardware: o mesmo código roda no STM32 e nos
 * testes de PC (pio test -e native). Espelha sim/controlador.py.
 *
 * Unidades: rad, rad/s, V, A, s.
 * Sinais:   u > 0 acelera a roda no sentido positivo do encoder e empurra o
 *           pêndulo no sentido negativo de theta.
 */
#ifndef RWP_CONTROL_H
#define RWP_CONTROL_H

#include <stdbool.h>
#include <stdint.h>

#define RWP_N_EVENTS 16   /* mudanças de contagem guardadas pelo estimador de velocidade */

/* Lei usada no equilíbrio. Troca pelo comando "lei" com o controle fora de EQUILIBRA. */
typedef enum {
    RWP_LAW_LQR = 0,   /* LQR + auto-ajuste do ângulo de equilíbrio */
    RWP_LAW_LQI,       /* LQR com o ângulo da roda como quarto estado */
    RWP_LAW_PID        /* PID em theta + malha externa PI na roda */
} rwp_law_t;

typedef struct {
    /* lei de controle: u = -(k1*theta + k2*theta_dot + k3*omega) */
    float k1, k2, k3;
    float ts;
    /* limites elétricos */
    float u_frac;        /* fração máxima da tensão do barramento */
    float i_max;         /* A */
    float ke;            /* V.s/rad */
    float r_motor;       /* ohm */
    float vbus_min, vbus_max;
    /* estimadores */
    float alpha_cf;      /* filtro complementar */
    float alpha_w;       /* passa-baixa da velocidade da roda */
    float rad_per_count;
    /* auto-ajuste do ângulo de equilíbrio */
    float trim_gain;
    float trim_max;
    /* segurança */
    float theta_cut;         /* acima disso desliga */
    float theta_engage;      /* janela para começar a equilibrar */
    float thetadot_engage;
    float w_max;             /* limite de rotação da roda */
    float manual_duty_max;   /* limite do modo de ensaio em malha aberta */
    /* lei do equilíbrio */
    rwp_law_t law;
    /* LQI: u = -(q1*theta + q2*theta_dot + q3*omega + q4*phi_r), phi_r = ângulo da roda */
    float q1, q2, q3, q4;
    /* PID: u = kp*e + ki*int(e) + kd*theta_dot, e = theta - theta_ref,
            theta_ref = -(kw*omega + kwi*phi_r), |theta_ref| <= trim_max */
    float kp, ki, kd, kw, kwi;
    float pid_i_max;         /* rad.s: limite da integral de e */
} rwp_config_t;

typedef enum {
    RWP_IDLE = 0,    /* motor desligado, esperando o botão */
    RWP_CALIB,       /* medindo o viés do giroscópio (pêndulo parado) */
    RWP_ARMED,       /* esperando o pêndulo ser levado à vertical */
    RWP_BALANCE,     /* equilibrando */
    RWP_MANUAL,      /* ensaio em malha aberta (identificação do motor) */
    RWP_FAULT        /* falha: freia a roda e desliga */
} rwp_state_t;

typedef enum {
    RWP_FAULT_NONE = 0,
    RWP_FAULT_ANGLE,       /* 1: inclinação além do limite */
    RWP_FAULT_OVERSPEED,   /* 2: roda acima do limite de rotação */
    RWP_FAULT_IMU,         /* 3: MPU6050 parou de responder */
    RWP_FAULT_VBUS_LOW,    /* 4: sem tensão no barramento (fonte fraca, mau contato) */
    RWP_FAULT_VBUS_HIGH,   /* 5: sobretensão (frenagem devolvendo energia) */
    RWP_FAULT_STALL        /* 6: corrente no limite por tempo demais */
} rwp_fault_t;

typedef struct {
    float theta_acc;     /* ângulo pelo acelerômetro [rad] */
    float gyro;          /* velocidade angular no eixo do pivô [rad/s] */
    int32_t enc_count;   /* contagem acumulada do encoder da roda */
    float vbus;          /* tensão do barramento [V] */
    bool imu_ok;         /* a leitura do MPU6050 deste período é válida */
    bool button;         /* evento: botão (ou comando "arm") neste período */
    bool stop;           /* evento: comando de parada */
    bool manual_req;     /* evento: pedido de ensaio em malha aberta */
    float manual_duty;   /* ciclo pedido no ensaio [-1, 1] */
} rwp_inputs_t;

typedef struct {
    float duty;          /* [-1, 1] ciclo de trabalho com sinal */
    bool enable;         /* habilita a ponte H */
    bool brake;          /* freio dinâmico: motor em curto pelos transistores de baixo */
    float u;             /* tensão comandada [V] */
    rwp_state_t state;
    rwp_fault_t fault;
    float theta, theta_dot, omega;
    float trim;          /* ângulo de equilíbrio em uso [rad]: auto-ajuste (LQR) ou o equivalente do LQI/PID */
} rwp_outputs_t;

typedef struct {
    rwp_config_t cfg;
    rwp_state_t state;
    rwp_fault_t fault;
    /* estimadores */
    float theta, theta_dot, omega, w_raw;
    float gyro_bias;
    float trim;
    /* integradores do LQI e do PID */
    float phi_ref;       /* ângulo da roda tomado como zero ao entrar em equilíbrio [rad] */
    float z_prev;        /* phi_r do período anterior */
    float i_e;           /* integral do erro de theta (PID) */
    float ref;           /* ângulo de equilíbrio equivalente [rad] */
    bool int_sat;        /* tensão saturada no período anterior: integradores congelados */
    /* estimador de velocidade: instante e valor das últimas mudanças de contagem */
    int32_t cnt_prev;
    uint32_t now;
    uint32_t ev_tick[RWP_N_EVENTS];
    int32_t ev_cnt[RWP_N_EVENTS];
    uint8_t ev_head;     /* índice do evento mais recente */
    uint8_t ev_n;        /* quantos eventos válidos */
    /* contadores de tempo (em períodos) */
    uint32_t t_state;
    uint32_t n_calib;
    float calib_sum, calib_min, calib_max;
    uint32_t n_engage, n_overspeed, n_imu_miss, n_vbus_low, n_sat;
    float manual_duty;
} rwp_t;

/* Configuração padrão a partir de lqr_gains.h (gerado por sim/export_gains.py). */
rwp_config_t rwp_config_default(void);

void rwp_init(rwp_t *c, const rwp_config_t *cfg);

/* Um período de controle. Chamar a cada cfg.ts segundos. */
void rwp_step(rwp_t *c, const rwp_inputs_t *in, rwp_outputs_t *out);

/* Lei de controle com limite de corrente e de tensão. Retorna a tensão [V]. */
float rwp_lqr_law(const rwp_config_t *g, float theta_e, float theta_dot, float omega, float vbus);

/* LQI ou PID (cfg.law), com anti-windup. Atualiza os integradores. Retorna a tensão [V].
   phi = ângulo acumulado da roda [rad]. Mesma sequência de Integradores.passo() em Python. */
float rwp_balance_law(rwp_t *c, float theta, float theta_dot, float omega, float phi, float vbus);

/* Troca a lei do equilíbrio. Recusa (retorna false) durante o equilíbrio. */
bool rwp_set_law(rwp_t *c, rwp_law_t law);

/* Velocidade da roda pelos instantes das últimas contagens + passa-baixa. */
float rwp_wheel_speed(rwp_t *c, int32_t count);

/* Só para testes: entra direto em equilíbrio com a estimativa de ângulo dada. */
void rwp_test_force_balance(rwp_t *c, float theta0);

const char *rwp_state_name(rwp_state_t s);
const char *rwp_fault_name(rwp_fault_t f);
const char *rwp_law_name(rwp_law_t l);

#endif /* RWP_CONTROL_H */
