function [u, st] = rwp_lei(lei, g, theta, theta_dot, omega, phi, vbus, st)
%RWP_LEI Tensão do motor [V] por uma das leis do equilíbrio, um período.
%   [u, st] = rwp_lei('lqr'|'lqi'|'pid', g, theta, theta_dot, omega, phi, vbus, st)
%   st guarda os integradores entre chamadas; comece com
%   st = struct('phi_ref', phi0, 'i_e', 0, 'ref', 0, 'saturou', false, 'z_ant', 0).
%   Mesma sequência de lei_controle() e Integradores.passo() em
%   sim/controlador.py e de rwp_balance_law() no firmware em C.

switch lei
    case 'lqr'
        u = limita(-g.K*[theta; theta_dot; omega], omega, vbus, g);
        st.ref = 0;
        return
    case 'lqi'
        phi_max = g.trim_max*abs(g.KI(1)/g.KI(4));
    case 'pid'
        phi_max = g.trim_max/g.kwi;
end

% ângulo da roda desde a entrada no equilíbrio, com anti-windup:
% congela enquanto a tensão está saturada e nunca pede mais que trim_max
z = phi - st.phi_ref;
if st.saturou
    z = st.z_ant; st.phi_ref = phi - z;
end
if abs(z) > phi_max
    z = sign(z)*phi_max; st.phi_ref = phi - z;
end
st.z_ant = z;

if strcmp(lei, 'lqi')
    u0 = -g.KI*[theta; theta_dot; omega; z];
    st.ref = -g.KI(4)*z/g.KI(1);
else
    st.ref = min(max(-(g.kw*omega + g.kwi*z), -g.trim_max), g.trim_max);
    e = theta - st.ref;
    if ~st.saturou
        st.i_e = min(max(st.i_e + e*g.ts, -g.pid_i_max), g.pid_i_max);
    end
    u0 = g.kp*e + g.ki*st.i_e + g.kd*theta_dot;
end
u = limita(u0, omega, vbus, g);
st.saturou = abs(u) >= 0.9*g.u_frac*vbus;
end

function u = limita(u, omega, vbus, g)
% limite de corrente (em torno da força contraeletromotriz) e de tensão
fcem = g.ke*omega;
u = min(max(u, fcem - g.R*g.i_max), fcem + g.R*g.i_max);
um = g.u_frac*vbus;
u = min(max(u, -um), um);
end
