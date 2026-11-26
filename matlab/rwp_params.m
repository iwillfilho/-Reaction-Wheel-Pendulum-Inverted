function p = rwp_params(varargin)
%RWP_PARAMS Parâmetros físicos do pêndulo invertido com roda de reação.
%   p = rwp_params() devolve os parâmetros nominais (os mesmos de sim/params.py).
%   p = rwp_params('motor_R', 1.0, 'roda_m_conjunto', 0.030, 'm_braco', 0.1)
%   troca valores antes de calcular as grandezas derivadas.
%
%   Tudo em SI (m, kg, s, rad, V, A). Os valores marcados MEDIR são
%   estimativas: troque pelo valor medido na bancada.

g0 = 9.81;
rho_petg = 1270;            % kg/m^3

% --- motor CC 775 de 12 V -------------------------------------------------
p.motor_v_nom = 12.0;
p.motor_R = 0.80;           % MEDIR  resistência de armadura [ohm]
p.motor_L = 0.5e-3;         % estimado  indutância [H]
p.motor_n0_rpm = 4000;      % MEDIR  rotação em vazio a v_nom [rpm]
p.motor_i0 = 0.60;          % MEDIR  corrente em vazio a v_nom [A]
p.motor_J_rotor = 1.0e-5;   % estimado  inércia do rotor [kg m^2]
p.motor_massa = 0.350;      % MEDIR  [kg]
p.motor_raio = 0.021;       % raio da carcaça [m]
p.motor_frac_coulomb = 0.7; % fração do atrito em vazio que é seco (escovas)

% --- roda de reação (PETG + 12 parafusos M8 na borda) ---------------------
p.roda_n_parafusos = 12;
p.roda_m_conjunto = 0.024;  % MEDIR  parafuso + porca + 2 arruelas [kg]
p.roda_r_parafusos = 0.048; % raio do círculo de parafusos [m]
p.roda_aro_dentro = 0.009;
p.roda_aro_fora = 0.010;
p.roda_espessura = 0.012;
p.roda_r_cubo = 0.017;
p.roda_esp_alma = 0.005;
p.roda_n_raios = 6;
p.roda_larg_raio = 0.010;
p.roda_aleta = 0.008;       % anel dentado do encoder [m]
p.roda_esp_aleta = 0.002;
p.roda_n_ranhuras = 40;     % x4 em quadratura = 160 contagens por volta
p.roda_furo_m8 = 0.0084;
p.roda_preenchimento = 0.85; % MEDIR  fração de material (pesar a roda)
p.roda_m_flange = 0.015;    % MEDIR  flange de 5 mm [kg]

% --- pêndulo e acionamento ------------------------------------------------
p.l_w = 0.096;              % pivô -> eixo do motor [m]
p.m_braco = 0.090;          % MEDIR  braço + 2 rolamentos + parafusos [kg]
p.frac_cm_braco = 0.25;     % centro de massa do braço como fração de l_w
p.m_extras = 0.030;         % MEDIR  sensores, MPU6050, fiação [kg]
p.l_extras = 0.030;         % altura desses itens acima do pivô [m]
p.b_p = 5.0e-4;             % MEDIR  atrito viscoso do pivô [N m s/rad]
p.v_bus = 12.0;             % tensão da fonte [V]
p.u_frac = 0.95;            % fração máxima de v_bus aplicada ao motor
p.i_max = 10.0;             % limite de corrente do firmware [A]
p.w_max = 209.4;            % limite de rotação da roda [rad/s] (2000 rpm)
p.ts = 1.0e-3;              % período da malha de controle [s]

% --- substituições pedidas na chamada ------------------------------------
for k = 1:2:numel(varargin)
    if ~isfield(p, varargin{k})
        error('rwp_params:campo', 'parâmetro desconhecido: %s', varargin{k});
    end
    p.(varargin{k}) = varargin{k+1};
end

% --- motor: grandezas derivadas -------------------------------------------
w0 = p.motor_n0_rpm * 2*pi/60;
p.ke = (p.motor_v_nom - p.motor_R*p.motor_i0) / w0;   % V s/rad
p.kt = p.ke;                                          % N m/A (igual a ke em SI)
tau_atrito = p.kt * p.motor_i0;
p.tau_c = p.motor_frac_coulomb * tau_atrito;          % atrito seco [N m]
p.b = (1 - p.motor_frac_coulomb) * tau_atrito / w0;   % atrito viscoso [N m s/rad]
p.b_lin = tau_atrito / w0;                            % viscoso equivalente do modelo linear

% --- roda: massa e inércia peça por peça ------------------------------------
rho = rho_petg * p.roda_preenchimento;
ro = p.roda_r_parafusos + p.roda_aro_fora;            % raio externo do aro
ri = p.roda_r_parafusos - p.roda_aro_dentro;          % raio interno do aro
m_aro = rho*pi*(ro^2 - ri^2)*p.roda_espessura;
m_furo = rho*pi*(p.roda_furo_m8/2)^2*p.roda_espessura;
pecas = zeros(6, 2);                                  % [massa, inércia]
pecas(1,:) = [m_aro - p.roda_n_parafusos*m_furo, ...
              0.5*m_aro*(ro^2 + ri^2) - p.roda_n_parafusos*m_furo*p.roda_r_parafusos^2];
comp = ri - p.roda_r_cubo;
m_raio = rho*comp*p.roda_larg_raio*p.roda_esp_alma;
r_cm = p.roda_r_cubo + comp/2;
pecas(2,:) = [p.roda_n_raios*m_raio, p.roda_n_raios*m_raio*(comp^2/12 + r_cm^2)];
m_cubo = rho*pi*p.roda_r_cubo^2*p.roda_esp_alma;
pecas(3,:) = [m_cubo, 0.5*m_cubo*p.roda_r_cubo^2];
ra = ro + p.roda_aleta;                               % anel dentado: metade é material
m_aleta = 0.5*rho*pi*(ra^2 - ro^2)*p.roda_esp_aleta;
pecas(4,:) = [m_aleta, 0.5*m_aleta*(ra^2 + ro^2)];
m_paraf = p.roda_n_parafusos*p.roda_m_conjunto;
pecas(5,:) = [m_paraf, m_paraf*p.roda_r_parafusos^2];
pecas(6,:) = [p.roda_m_flange, 0.5*p.roda_m_flange*0.011^2];
p.m_w = sum(pecas(:,1));                              % massa da roda [kg]
p.Iw = sum(pecas(:,2)) + p.motor_J_rotor;             % inércia de giro roda + rotor [kg m^2]
p.cpr = 4*p.roda_n_ranhuras;                          % contagens por volta

% --- pêndulo --------------------------------------------------------------
p.J = (p.motor_massa + p.m_w)*p.l_w^2 + 0.5*p.motor_massa*p.motor_raio^2 ...
    + p.m_braco*p.l_w^2/3 + p.m_extras*p.l_extras^2;  % inércia no pivô, sem o giro da roda
p.Mgl = g0*((p.motor_massa + p.m_w)*p.l_w + p.m_braco*p.frac_cm_braco*p.l_w ...
    + p.m_extras*p.l_extras);                         % tau_gravidade = Mgl*sin(theta)
p.massa_total = p.motor_massa + p.m_w + p.m_braco + p.m_extras;
p.u_max = p.u_frac*p.v_bus;
p.tau_max = p.kt*min(p.i_max, p.u_max/p.motor_R);
p.theta_max_estatico = asin(min(1, p.tau_max/p.Mgl));
end
