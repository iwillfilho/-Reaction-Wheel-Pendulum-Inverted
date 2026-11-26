function r = rwp_simular(p, g, lei, varargin)
%RWP_SIMULAR Malha fechada com a planta não linear e sensores ideais.
%   r = rwp_simular(p, g, 'lqr')             solto a 5 graus, 5 s
%   r = rwp_simular(p, g, 'lqi', 'theta0', deg2rad(8), 'T', 4)
%   r = rwp_simular(p, g, 'pid', 'disturbios', [1.0 1.5; 3.5 -2.5])
%   r = rwp_simular(p, g, 'lqr', 'planta', rwp_params('motor_R', 1.12))
%
%   lei: 'lqr', 'lqi' ou 'pid'. Mesma sequência de sim/simulacao.py com
%   realista=False: o controlador roda a cada p.ts com o estado verdadeiro, a
%   planta é integrada por RK4 no mesmo passo, a tensão é limitada pela
%   corrente máxima e pela tensão do barramento, e o pêndulo cai (motor
%   desligado) se passar do batente de 25 graus.
%
%   Opções: 'theta0' [rad], 'T' [s], 'disturbios' [instante, degrau em theta'
%   (rad/s)] por linha (um peteleco no braço), 'planta' (parâmetros
%   "verdadeiros", diferentes dos usados no projeto).
%   Saída: r.t, r.theta, r.theta_dot, r.omega, r.u, r.i, r.ref, r.caiu

o = struct('theta0', deg2rad(5), 'T', 5, 'disturbios', zeros(0,2), 'planta', p);
for k = 1:2:numel(varargin), o.(varargin{k}) = varargin{k+1}; end
pl = o.planta;
lei = lower(lei);
if ~any(strcmp(lei, {'lqr', 'lqi', 'pid'})), error('lei desconhecida: %s', lei); end

ts = g.ts; n = round(o.T/ts);
x = [o.theta0; 0; 0]; phi = 0;
dist = sortrows(o.disturbios, 1);
st = struct('phi_ref', 0, 'i_e', 0, 'ref', 0, 'saturou', false, 'z_ant', 0);
r.t = (0:n-1)'*ts;
[r.theta, r.theta_dot, r.omega, r.u, r.i, r.ref] = deal(zeros(n,1));
caiu = false;
f = @(xx, V) rwp_planta(xx, V, pl);
for k = 1:n
    t = (k-1)*ts;
    while ~isempty(dist) && dist(1,1) <= t
        x(2) = x(2) + dist(1,2); dist(1,:) = [];
    end
    [u, st] = rwp_lei(lei, g, x(1), x(2), x(3), phi, p.v_bus, st);
    if caiu, u = 0; end
    r.theta(k) = x(1); r.theta_dot(k) = x(2); r.omega(k) = x(3);
    r.u(k) = u; r.i(k) = (u - pl.ke*x(3))/pl.motor_R; r.ref(k) = st.ref;
    % RK4
    k1 = f(x, u); k2 = f(x + 0.5*ts*k1, u); k3 = f(x + 0.5*ts*k2, u); k4 = f(x + ts*k3, u);
    xn = x + ts/6*(k1 + 2*k2 + 2*k3 + k4);
    phi = phi + 0.5*(x(3) + xn(3))*ts;   % ângulo da roda (o encoder conta isto)
    x = xn;
    if abs(x(1)) > deg2rad(25), caiu = true; end
end
r.caiu = caiu;
end
