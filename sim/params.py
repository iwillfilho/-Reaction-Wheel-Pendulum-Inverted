"""Parâmetros físicos do pêndulo invertido com roda de reação.

Fonte única de verdade: a simulação, os ganhos do firmware e as dimensões do CAD
saem todos daqui (ver sim/export_gains.py).

Tudo em SI (m, kg, s, rad, V, A). Valores marcados com MEDIR são estimativas
iniciais: troque pelo valor medido na bancada e rode de novo
`python -m sim.export_gains`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

G = 9.81
RHO_PETG = 1270.0  # kg/m³


@dataclass(frozen=True)
class Motor:
    """Motor CC 775 de 12 V. O anúncio só informa "3000-5000 rpm"."""

    v_nom: float = 12.0
    R: float = 0.80           # MEDIR  resistência de armadura [ohm] (multímetro, eixo travado)
    L: float = 0.5e-3         # estimado  indutância [H] (só entra na simulação realista)
    n0_rpm: float = 4000.0    # MEDIR  rotação em vazio a v_nom [rpm] (sensor óptico)
    i0: float = 0.60          # MEDIR  corrente em vazio a v_nom [A]
    J_rotor: float = 1.0e-5   # estimado  inércia do rotor [kg·m²]
    massa: float = 0.350      # MEDIR  [kg]
    raio: float = 0.021       # raio da carcaça [m]
    frac_coulomb: float = 0.7  # fração do atrito em vazio que é seco (escovas)

    @property
    def w0(self) -> float:
        return self.n0_rpm * 2.0 * math.pi / 60.0

    @property
    def ke(self) -> float:
        """Constante de força contraeletromotriz [V·s/rad]."""
        return (self.v_nom - self.R * self.i0) / self.w0

    @property
    def kt(self) -> float:
        """Constante de torque [N·m/A] (igual a ke em SI)."""
        return self.ke

    @property
    def tau_atrito(self) -> float:
        """Torque de atrito total em vazio [N·m]."""
        return self.kt * self.i0

    @property
    def tau_c(self) -> float:
        """Parcela de atrito seco [N·m]."""
        return self.frac_coulomb * self.tau_atrito

    @property
    def b(self) -> float:
        """Parcela de atrito viscoso [N·m·s/rad]."""
        return (1.0 - self.frac_coulomb) * self.tau_atrito / self.w0

    @property
    def b_lin(self) -> float:
        """Atrito viscoso equivalente usado no modelo linear de projeto."""
        return self.tau_atrito / self.w0


@dataclass(frozen=True)
class Roda:
    """Roda de reação impressa em PETG com parafusos M8 na borda."""

    n_parafusos: int = 12
    m_conjunto: float = 0.024     # MEDIR  parafuso M8x25 + porca + 2 arruelas [kg]
    r_parafusos: float = 0.048    # raio do círculo de parafusos [m] (escolhido por sim/sizing.py)
    aro_dentro: float = 0.009     # material do aro para dentro do círculo de parafusos [m]
    aro_fora: float = 0.010       # material do aro para fora [m]
    espessura: float = 0.012      # espessura do aro [m]
    r_cubo: float = 0.017         # raio do cubo central [m]
    esp_alma: float = 0.005       # espessura do cubo e dos raios [m]
    n_raios: int = 6
    larg_raio: float = 0.010
    aleta: float = 0.008          # largura radial do anel dentado do encoder [m]
    esp_aleta: float = 0.002
    n_ranhuras: int = 40          # ranhuras do encoder (x4 em quadratura)
    furo_m8: float = 0.0084
    preenchimento: float = 0.85   # MEDIR  fração de material (pesar a roda impressa)
    m_flange: float = 0.015       # MEDIR  flange metálico de 5 mm [kg]

    @property
    def r_aro_int(self) -> float:
        return self.r_parafusos - self.aro_dentro

    @property
    def r_ext(self) -> float:
        return self.r_parafusos + self.aro_fora

    @property
    def r_aleta(self) -> float:
        return self.r_ext + self.aleta

    @property
    def cpr(self) -> int:
        """Contagens por volta em quadratura."""
        return 4 * self.n_ranhuras

    def _pecas(self) -> list[tuple[float, float]]:
        """Lista (massa, inércia em torno do eixo) de cada parte da roda."""
        rho = RHO_PETG * self.preenchimento
        ro, ri = self.r_ext, self.r_aro_int
        m_aro = rho * math.pi * (ro**2 - ri**2) * self.espessura
        m_furo = rho * math.pi * (self.furo_m8 / 2) ** 2 * self.espessura
        m_aro_liq = m_aro - self.n_parafusos * m_furo
        i_aro = 0.5 * m_aro * (ro**2 + ri**2) - self.n_parafusos * m_furo * self.r_parafusos**2

        comp = ri - self.r_cubo
        m_raio = rho * comp * self.larg_raio * self.esp_alma
        r_cm = self.r_cubo + comp / 2
        i_raios = self.n_raios * m_raio * (comp**2 / 12 + r_cm**2)

        m_cubo = rho * math.pi * self.r_cubo**2 * self.esp_alma
        i_cubo = 0.5 * m_cubo * self.r_cubo**2

        # anel dentado: metade do anel é material (dente = vão)
        ra = self.r_aleta
        m_aleta = 0.5 * rho * math.pi * (ra**2 - ro**2) * self.esp_aleta
        i_aleta = 0.5 * m_aleta * (ra**2 + ro**2)

        m_paraf = self.n_parafusos * self.m_conjunto
        i_paraf = m_paraf * self.r_parafusos**2

        return [
            (m_aro_liq, i_aro),
            (self.n_raios * m_raio, i_raios),
            (m_cubo, i_cubo),
            (m_aleta, i_aleta),
            (m_paraf, i_paraf),
            (self.m_flange, 0.5 * self.m_flange * 0.011**2),
        ]

    @property
    def massa(self) -> float:
        return sum(m for m, _ in self._pecas())

    @property
    def massa_impressa(self) -> float:
        return sum(m for m, _ in self._pecas()[:4])

    @property
    def inercia(self) -> float:
        return sum(i for _, i in self._pecas())


@dataclass(frozen=True)
class Params:
    motor: Motor = field(default_factory=Motor)
    roda: Roda = field(default_factory=Roda)

    l_w: float = 0.096         # distância pivô -> eixo do motor [m] (raio da roda + 30 mm, ver sim/sizing.py)
    m_braco: float = 0.090     # MEDIR  braço impresso + 2 rolamentos + parafusos [kg] (CAD: 89 g)
    frac_cm_braco: float = 0.25  # centro de massa do braço como fração de l_w (CAD: 0,23)
    m_extras: float = 0.030    # MEDIR  sensores ópticos, MPU6050, fiação [kg]
    l_extras: float = 0.030    # altura desses itens acima do pivô [m]
    b_p: float = 5.0e-4        # MEDIR  atrito viscoso do pivô [N·m·s/rad] (decaimento livre)

    v_bus: float = 12.0        # tensão da fonte [V]
    u_frac: float = 0.95       # fração máxima de v_bus aplicada ao motor
    i_max: float = 10.0        # limite de corrente imposto pelo firmware [A]
    w_max: float = 209.4       # limite de rotação da roda [rad/s] (2000 rpm; o pior caso simulado fica abaixo de 1100 rpm)
    ts: float = 1.0e-3         # período da malha de controle [s]

    # --- grandezas derivadas -------------------------------------------------
    @property
    def I_w(self) -> float:
        """Inércia de giro da roda + rotor [kg·m²]."""
        return self.roda.inercia + self.motor.J_rotor

    @property
    def m_w(self) -> float:
        return self.roda.massa

    @property
    def J(self) -> float:
        """Inércia do conjunto em torno do pivô, sem o giro da roda [kg·m²]."""
        m = self.motor
        return (
            (m.massa + self.m_w) * self.l_w**2
            + 0.5 * m.massa * m.raio**2
            + self.m_braco * self.l_w**2 / 3.0
            + self.m_extras * self.l_extras**2
        )

    @property
    def Mgl(self) -> float:
        """Coeficiente do torque gravitacional: tau_g = Mgl * sin(theta) [N·m]."""
        return G * (
            (self.motor.massa + self.m_w) * self.l_w
            + self.m_braco * self.frac_cm_braco * self.l_w
            + self.m_extras * self.l_extras
        )

    @property
    def massa_total(self) -> float:
        return self.motor.massa + self.m_w + self.m_braco + self.m_extras

    @property
    def u_max(self) -> float:
        return self.u_frac * self.v_bus

    @property
    def tau_max(self) -> float:
        """Torque máximo disponível respeitando o limite de corrente [N·m]."""
        return self.motor.kt * min(self.i_max, self.u_max / self.motor.R)

    @property
    def theta_max_estatico(self) -> float:
        """Maior inclinação que o torque máximo ainda segura parado [rad]."""
        return math.asin(min(1.0, self.tau_max / self.Mgl))

    def com(self, **kw) -> "Params":
        """Cópia com campos alterados; aceita 'motor__R=...' e 'roda__r_parafusos=...'."""
        top, mot, rod = {}, {}, {}
        for k, v in kw.items():
            if k.startswith("motor__"):
                mot[k[7:]] = v
            elif k.startswith("roda__"):
                rod[k[6:]] = v
            else:
                top[k] = v
        if mot:
            top["motor"] = replace(self.motor, **mot)
        if rod:
            top["roda"] = replace(self.roda, **rod)
        return replace(self, **top)

    def resumo(self) -> str:
        m, r = self.motor, self.roda
        return "\n".join(
            [
                f"Motor: ke = kt = {m.ke:.4f} V·s/rad | R = {m.R:.2f} ohm | "
                f"corrente de partida = {m.v_nom / m.R:.1f} A | torque de partida = {m.kt * m.v_nom / m.R:.3f} N·m",
                f"Roda:  raio dos parafusos = {r.r_parafusos * 1e3:.0f} mm | diâmetro externo = {2 * r.r_ext * 1e3:.0f} mm "
                f"(com anel do encoder {2 * r.r_aleta * 1e3:.0f} mm)",
                f"       massa = {self.m_w * 1e3:.0f} g (impressa {r.massa_impressa * 1e3:.0f} g) | "
                f"I_w = {self.I_w * 1e3:.3f} g·m²",
                f"Pêndulo: l_w = {self.l_w * 1e3:.0f} mm | massa total = {self.massa_total * 1e3:.0f} g | "
                f"J = {self.J * 1e3:.3f} g·m² | Mgl = {self.Mgl:.3f} N·m",
                f"         polo instável = {math.sqrt(self.Mgl / self.J):.2f} rad/s "
                f"(tempo de queda característico {1e3 / math.sqrt(self.Mgl / self.J):.0f} ms)",
                f"Limites: torque máx = {self.tau_max:.3f} N·m | inclinação estática máx = "
                f"{math.degrees(self.theta_max_estatico):.1f}° | momento angular máx da roda = "
                f"{self.I_w * self.w_max:.3f} N·m·s",
            ]
        )


NOMINAL = Params()

if __name__ == "__main__":
    print(NOMINAL.resumo())
