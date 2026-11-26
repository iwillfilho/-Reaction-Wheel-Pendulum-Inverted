%EXEMPLO_RWP Roteiro de simulação do pêndulo invertido com roda de reação.
%   Rode por partes (Ctrl+Enter em cada seção) ou inteiro (F5).
%   Precisa do Control System Toolbox.

%% 1. Parâmetros e modelo linear
p = rwp_params();
fprintf('massa total %.0f g | J = %.3f g m^2 | Iw = %.3f g m^2 | Mgl = %.3f N m\n', ...
    1e3*p.massa_total, 1e3*p.J, 1e3*p.Iw, p.Mgl);
fprintf('torque máximo %.3f N m | inclinação estática máxima %.1f°\n', p.tau_max, rad2deg(p.theta_max_estatico));

[A, B] = rwp_linear(p);
sys = ss(A, B, eye(3), zeros(3,1), ...
    'StateName', {'theta', 'theta_dot', 'omega'}, 'InputName', 'V');
fprintf('polos de malha aberta (rad/s): %s\n', mat2str(eig(A)', 4));
fprintf('controlável: %d estados de 3\n', rank(ctrb(A, B)));

% função de transferência tensão -> ângulo
G_theta = zpk(sys(1,1))

%% 2. Projeto das três leis
g = rwp_projeto(p);
fprintf('LQR  K  = %s\n', mat2str(g.K, 5));
fprintf('LQI  KI = %s\n', mat2str(g.KI, 5));
fprintf('PID  kp = %.2f  ki = %.1f  kd = %.3f\n', g.kp, g.ki, g.kd);
z = eig(g.Ad - g.Bd*g.K);
fprintf('polos de malha fechada do LQR (rad/s): %s\n', mat2str(log(z)'/p.ts, 4));

%% 3. Pêndulo solto a 8° com o LQR
r = rwp_simular(p, g, 'lqr', 'theta0', deg2rad(8), 'T', 4);
figure('Name', 'LQR: solto a 8°');
tiledlayout(4, 1, 'TileSpacing', 'compact');
nexttile; plot(r.t, rad2deg(r.theta)); ylabel('\theta (°)'); grid on; title('Pêndulo solto a 8° da vertical');
nexttile; plot(r.t, r.omega*60/(2*pi)); ylabel('roda (rpm)'); grid on;
nexttile; plot(r.t, r.u); ylabel('tensão (V)'); grid on; yline([-1 1]*p.u_max, '--');
nexttile; plot(r.t, r.i); ylabel('corrente (A)'); grid on; yline([-1 1]*p.i_max, '--'); xlabel('tempo (s)');

%% 4. As três leis com dois petelecos no braço
figure('Name', 'Comparação das leis');
leis = {'lqr', 'lqi', 'pid'};
for k = 1:3
    r = rwp_simular(p, g, leis{k}, 'theta0', 0, 'T', 6, 'disturbios', [1.0 1.5; 3.5 -2.5]);
    subplot(2,1,1); hold on; plot(r.t, rad2deg(r.theta), 'DisplayName', upper(leis{k}));
    subplot(2,1,2); hold on; plot(r.t, r.omega*60/(2*pi), 'DisplayName', upper(leis{k}));
end
subplot(2,1,1); ylabel('\theta (°)'); grid on; legend; title('Petelecos de +1,5 rad/s e -2,5 rad/s');
subplot(2,1,2); ylabel('roda (rpm)'); xlabel('tempo (s)'); grid on; legend;

%% 5. Robustez: ganhos nominais com a planta "real" diferente
casos = {'nominal', {}; 'resistência +40 %', {'motor_R', 1.4*0.80}; ...
         'motor a 5000 rpm', {'motor_n0_rpm', 5000}; 'M8 +25 %', {'roda_m_conjunto', 1.25*0.024}; ...
         'braço +50 %', {'m_braco', 1.5*0.090}; 'atrito do pivô x4', {'b_p', 4*5e-4}};
fprintf('\n%-22s %10s %12s\n', 'planta real', 'caiu?', 'pico roda');
for k = 1:size(casos, 1)
    planta_real = rwp_params(casos{k, 2}{:});
    r = rwp_simular(p, g, 'lqr', 'theta0', deg2rad(5), 'T', 6, 'planta', planta_real);
    fprintf('%-22s %10s %8.0f rpm\n', casos{k, 1}, sim_nao(r.caiu), ...
        max(abs(r.omega))*60/(2*pi));
end

function s = sim_nao(v)
if v, s = 'SIM'; else, s = 'não'; end
end
