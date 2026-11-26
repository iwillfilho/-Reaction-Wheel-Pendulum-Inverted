function dx = rwp_planta(x, V, p, com_indutancia)
%RWP_PLANTA Derivada do modelo não linear (Euler-Lagrange), mesma de sim/model.py.
%   dx = rwp_planta(x, V, p)        x = [theta; theta'; omega]       (L = 0)
%   dx = rwp_planta(x, V, p, true)  x = [theta; theta'; omega; i]    (com indutância)
%
%   theta : ângulo do pêndulo a partir da vertical para cima [rad]
%   omega : velocidade da roda em relação ao braço [rad/s] (o que o encoder mede)
%   V     : tensão média no motor [V]. V > 0 acelera a roda (omega > 0) e, por
%           reação, empurra o pêndulo no sentido de theta negativo.
%
%   J*theta''              = Mgl*sin(theta) - b_p*theta' - tau
%   Iw*(theta'' + omega')  = tau
%   tau = kt*i - tau_c*tanh(omega/1 rad/s) - b*omega
%   L*di/dt = V - R*i - ke*omega

if nargin < 4, com_indutancia = false; end
om = x(3);
atrito = p.tau_c*tanh(om/1.0) + p.b*om;
if com_indutancia
    i = x(4);
else
    i = (V - p.ke*om)/p.motor_R;
end
tau = p.kt*i - atrito;
thdd = (p.Mgl*sin(x(1)) - p.b_p*x(2) - tau)/p.J;
dx = [x(2); thdd; tau/p.Iw - thdd];
if com_indutancia
    dx(4) = (V - p.motor_R*i - p.ke*om)/p.motor_L;
end
end
