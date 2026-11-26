function g = rwp_projeto(p)
%RWP_PROJETO Ganhos das três leis do equilíbrio (mesmos de sim/controlador.py).
%   g = rwp_projeto(p)
%   g.K   LQR discreto, u = -K*[theta; theta'; omega]
%   g.KI  LQI, u = -KI*[theta; theta'; omega; phi_r] (phi_r = ângulo da roda)
%   g.kp, g.ki, g.kd  PID em theta (polo triplo em -15 rad/s) + malha externa
%                     na roda: theta_ref = -(kw*omega + kwi*phi_r)
%   Precisa do Control System Toolbox (ss, c2d, dlqr).

% pesos de Bryson: 1/(desvio aceitável)^2
d_theta = deg2rad(3.0);   % rad
d_thd   = 0.5;            % rad/s
d_omega = 50.0;           % rad/s
d_u     = 11.4;           % V
d_phi   = 2*pi*3.0;       % rad: o LQI aceita ~3 voltas de roda

[A, B] = rwp_linear(p);
g.ts = p.ts;

% --- LQR ---------------------------------------------------------------------
sd = c2d(ss(A, B, eye(3), zeros(3,1)), p.ts, 'zoh');
g.Ad = sd.A; g.Bd = sd.B;
Q = diag(1./[d_theta d_thd d_omega].^2);
g.K = dlqr(sd.A, sd.B, Q, 1/d_u^2);

% --- LQI: planta aumentada com phi_r' = omega -------------------------------
A4 = zeros(4); A4(1:3,1:3) = A; A4(4,3) = 1;
B4 = [B; 0];
sd4 = c2d(ss(A4, B4, eye(4), zeros(4,1)), p.ts, 'zoh');
g.Ad4 = sd4.A; g.Bd4 = sd4.B;
Q4 = diag(1./[d_theta d_thd d_omega d_phi].^2);
g.KI = dlqr(sd4.A, sd4.B, Q4, 1/d_u^2);

% --- PID por alocação de polos -------------------------------------------------
% Perto da vertical: J*theta'' = Mgl*theta - (kt/R)*u. Com
% u = kp*e + ki*int(e) + kd*theta', a malha fica
% J s^3 + gk kd s^2 + (gk kp - Mgl) s + gk ki = 0  ->  polo triplo em -s.
s = 15.0;  gk = p.kt/p.motor_R;
g.kp = (p.Mgl + 3*s^2*p.J)/gk;
g.ki = s^3*p.J/gk;
g.kd = 3*s*p.J/gk;
g.kw = 1.0e-3;          % rad por rad/s
g.kwi = 2.5e-4;         % rad por rad
g.pid_i_max = 0.02;     % rad s

% --- limites, iguais aos do firmware ------------------------------------------
g.u_frac = p.u_frac; g.i_max = p.i_max; g.ke = p.ke; g.R = p.motor_R;
g.trim_max = deg2rad(4.0);
end
