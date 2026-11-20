/* ARQUIVO GERADO por sim/export_gains.py - não edite à mão; mude sim/params.py e gere de novo. */
#ifndef LQR_GAINS_H
#define LQR_GAINS_H

/* Lei de controle: u = -(K1*theta + K2*theta_dot + K3*omega)  [V] */
#define RWP_K1            (-248.905239f)   /* V/rad      */
#define RWP_K2            (-25.8485362f)   /* V/(rad/s)  */
#define RWP_K3            (-0.245103063f)   /* V/(rad/s)  */
#define RWP_TS            (0.001f)   /* s          */

/* Limites elétricos */
#define RWP_U_FRAC        (0.95f)   /* fração máxima da tensão do barramento */
#define RWP_I_MAX         (10.0f)   /* A */
#define RWP_KE            (0.0275019742f)   /* V.s/rad  (modelo do motor) */
#define RWP_R_MOTOR       (0.8f)   /* ohm */
#define RWP_VBUS_NOM      (12.0f)   /* V */
#define RWP_VBUS_MIN      (9.0f)
#define RWP_VBUS_MAX      (16.5f)

/* Estimadores */
#define RWP_ALPHA_CF      (0.998003992f)   /* filtro complementar */
#define RWP_ALPHA_W       (0.171795819f)   /* passa-baixa da velocidade da roda */
#define RWP_ENC_CPR       (160)        /* contagens por volta (4 x 40 ranhuras) */
#define RWP_RAD_PER_COUNT (0.0392699082f)

/* Auto-ajuste do ângulo de equilíbrio: trim' = TRIM_GAIN * omega */
#define RWP_TRIM_GAIN     (-0.000108703605f)
#define RWP_TRIM_MAX      (0.0698131701f)   /* rad */

/* Segurança */
#define RWP_THETA_CUT     (0.34906585f)   /* rad (20 graus) */
#define RWP_THETA_ENGAGE  (0.0523598776f)   /* rad (3 graus) */
#define RWP_THETADOT_ENGAGE (0.5f) /* rad/s */
#define RWP_W_MAX         (209.4f)   /* rad/s (2000 rpm) */

#endif /* LQR_GAINS_H */
