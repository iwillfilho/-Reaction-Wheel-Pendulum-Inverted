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

/* LQI: u = -(Q1*theta + Q2*theta_dot + Q3*omega + Q4*phi_r)  [V], phi_r = ângulo da roda */
#define RWP_Q1            (-289.249534f)   /* V/rad      */
#define RWP_Q2            (-30.0903435f)   /* V/(rad/s)  */
#define RWP_Q3            (-0.668524126f)   /* V/(rad/s)  */
#define RWP_Q4            (-0.569270606f)   /* V/rad      */

/* PID: u = KP*e + KI*int(e) + KD*theta_dot, e = theta - theta_ref,
        theta_ref = -(KW*omega + KWI*phi_r)  (malha externa na roda) */
#define RWP_PID_KP        (161.438643f)   /* V/rad      */
#define RWP_PID_KI        (702.182125f)   /* V/(rad.s)  */
#define RWP_PID_KD        (9.36242833f)   /* V/(rad/s)  */
#define RWP_PID_KW        (0.001f)   /* rad por rad/s */
#define RWP_PID_KWI       (0.00025f)   /* rad por rad   */
#define RWP_PID_I_MAX     (0.02f)   /* rad.s */

/* Segurança */
#define RWP_THETA_CUT     (0.34906585f)   /* rad (20 graus) */
#define RWP_THETA_ENGAGE  (0.0523598776f)   /* rad (3 graus) */
#define RWP_THETADOT_ENGAGE (0.5f) /* rad/s */
#define RWP_W_MAX         (209.4f)   /* rad/s (2000 rpm) */

#endif /* LQR_GAINS_H */
