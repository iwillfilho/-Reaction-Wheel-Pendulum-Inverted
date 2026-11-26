# Simulação em MATLAB

Porta da simulação em Python (`sim/`) para MATLAB: mesmos parâmetros, mesmo modelo
não linear, mesmo projeto do LQR, do LQI e do PID e a mesma malha fechada. O
`verificar_python.m` confere tudo contra o Python: ganhos iguais até 1e-12 e
trajetórias iguais até 1e-11.

Precisa do **Control System Toolbox** (`ss`, `c2d`, `dlqr`). Testado no R2026a.

## Como usar

Abra esta pasta no MATLAB e rode:

```matlab
verificar_python   % confere contra o Python (opcional)
exemplo_rwp        % roteiro: modelo, ganhos, respostas e robustez, por seções
```

## Arquivos

| Arquivo | O que faz |
|---|---|
| `rwp_params.m` | parâmetros físicos e grandezas derivadas (J, Iw, Mgl, ke, kt, atritos). `rwp_params('motor_R', 1.0)` troca um valor |
| `rwp_planta.m` | derivada do modelo não linear: `dx = rwp_planta(x, V, p)`, x = [θ; θ'; ω]. Com `true` no fim, inclui a indutância (x tem a corrente) |
| `rwp_linear.m` | `[A, B]` linearizados em torno de θ = 0, entrada = tensão do motor |
| `rwp_projeto.m` | ganhos: `g.K` (LQR discreto), `g.KI` (LQI), `g.kp`, `g.ki`, `g.kd` (PID) e os limites do firmware |
| `rwp_lei.m` | tensão aplicada por uma lei num período, com limite de corrente, de tensão e anti-windup |
| `rwp_simular.m` | malha fechada com sensores ideais: `r = rwp_simular(p, g, 'lqr', 'theta0', deg2rad(8), 'T', 4)` |
| `exemplo_rwp.m` | roteiro de exemplo |
| `verificar_python.m` | comparação com `referencia_python.json` |
| `referencia_python.json` | números do Python, gerados por `python -m sim.export_matlab` |

## Convenções

- θ: ângulo do braço a partir da vertical para cima [rad]; ω: rotação da roda **em relação ao braço** [rad/s], que é o que o encoder mede.
- Tensão positiva acelera a roda (ω > 0) e, por reação, empurra o braço para θ negativo.
- Modelo (Euler-Lagrange): `J θ'' = Mgl sin θ − b_p θ' − τ` e `Iw (θ'' + ω') = τ`, com `τ = kt i − τc tanh(ω) − b ω` e `i = (V − ke ω)/R`.
- O controle roda a 1 kHz (`p.ts`). A tensão é limitada a ±0,95 · 12 V e a corrente a 10 A, como no firmware. O pêndulo cai no batente a ±25°.

## O que não está aqui

A simulação "realista" do Python (`sim/simulacao.py` com `realista=True`) também modela o
ruído e o atraso do MPU6050, o filtro complementar, o estimador de velocidade pelo encoder e
o auto-ajuste do LQR. Esta versão usa sensores ideais, que é o que se usa para projetar e
comparar controladores.

Se os parâmetros mudarem em `sim/params.py`, mude também em `rwp_params.m` e gere a
referência de novo com `python -m sim.export_matlab`.
