"""Dedução simbólica das equações de movimento por Lagrange (SymPy).

Serve para o relatório e como verificação independente de sim/model.py:
o teste em sim/tests compara numericamente as duas implementações.

Uso:  python -m sim.derivacao
"""
from __future__ import annotations

import sympy as sp


def deduzir():
    """Retorna (theta'', omega') simbólicos e os símbolos usados.

    theta : ângulo do pêndulo a partir da vertical
    phi   : ângulo da roda em relação ao braço  (omega = phi')
    tau   : torque do braço sobre a roda (motor menos atrito)
    """
    t = sp.symbols("t")
    J, Iw, Mgl, bp, tau = sp.symbols("J I_w Mgl b_p tau", real=True)
    th = sp.Function("theta")(t)
    ph = sp.Function("phi")(t)
    thd, phd = th.diff(t), ph.diff(t)

    # Energia cinética: giro do conjunto em torno do pivô + giro absoluto da roda
    T = sp.Rational(1, 2) * J * thd**2 + sp.Rational(1, 2) * Iw * (thd + phd) ** 2
    V = Mgl * sp.cos(th)
    Lg = T - V

    # Forças generalizadas: atrito do pivô em theta; torque do motor em phi.
    # (O torque do motor é interno ao conjunto, por isso não aparece em theta.)
    eq_th = sp.Eq(sp.diff(Lg.diff(thd), t) - Lg.diff(th), -bp * thd)
    eq_ph = sp.Eq(sp.diff(Lg.diff(phd), t) - Lg.diff(ph), tau)

    sol = sp.solve([eq_th, eq_ph], [th.diff(t, 2), ph.diff(t, 2)], dict=True)[0]
    thdd = sp.simplify(sol[th.diff(t, 2)])
    phdd = sp.simplify(sol[ph.diff(t, 2)])

    # troca funções por símbolos simples para uso numérico
    s_th, s_thd, s_om = sp.symbols("theta theta_dot omega", real=True)
    troca = {thd: s_thd, phd: s_om, th: s_th}
    return (
        thdd.subs(troca),
        phdd.subs(troca),
        {"theta": s_th, "theta_dot": s_thd, "omega": s_om, "tau": tau, "J": J, "I_w": Iw, "Mgl": Mgl, "b_p": bp},
    )


def funcao_numerica():
    """f(theta, theta_dot, omega, tau, J, I_w, Mgl, b_p) -> (theta'', omega')."""
    thdd, phdd, s = deduzir()
    args = [s[k] for k in ("theta", "theta_dot", "omega", "tau", "J", "I_w", "Mgl", "b_p")]
    return sp.lambdify(args, [thdd, phdd], "math")


if __name__ == "__main__":
    thdd, phdd, _ = deduzir()
    print("theta'' =", thdd)
    print("omega'  =", phdd)
    print("\nLaTeX:")
    print(r"\ddot\theta =", sp.latex(thdd))
    print(r"\dot\omega  =", sp.latex(phdd))
