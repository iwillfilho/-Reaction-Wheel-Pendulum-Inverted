function [A, B] = rwp_linear(p)
%RWP_LINEAR Modelo linearizado em torno de theta = 0, x = [theta; theta'; omega], u = V.
%   [A, B] = rwp_linear(p). Mesmo de Planta.linear() em sim/model.py.
%   No modelo linear o atrito do motor entra todo como viscoso (b_lin).

c = p.kt*p.ke/p.motor_R + p.b_lin;   % d(tau)/d(omega), com o sinal trocado
g = p.kt/p.motor_R;                  % d(tau)/dV
J = p.J; Iw = p.Iw;
A = [0,          1,           0;
     p.Mgl/J,   -p.b_p/J,     c/J;
    -p.Mgl/J,    p.b_p/J,    -c*(1/Iw + 1/J)];
B = [0; -g/J; g*(1/Iw + 1/J)];
end
