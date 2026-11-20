# Testes de bancada

Faça as etapas **na ordem**. Cada uma só depende das anteriores, e qualquer
problema aparece quando ainda é barato de achar. Guarde todos os logs: eles
viram os gráficos do relatório.

**Segurança**: óculos de proteção sempre que a roda estiver montada. Proteção de
policarbonato no lugar. Nos primeiros testes com motor, deixe o terminal pronto para mandar `s`
ou o dedo no botão KEY da placa.

## Comandos que você vai usar

```bash
source .venv/bin/activate
cd firmware && pio run -t upload && cd ..       # grava pelo ST-Link
python tools/telemetry_log.py --porta /dev/ttyUSB0   # terminal + gravação em logs/
python tools/plot_log.py logs/ARQUIVO.csv            # gráfico de um log
```

No terminal do `telemetry_log.py`: `?` lista os comandos, `diag` mostra os sensores,
`cfg` mostra ganhos e sinais, `s` para tudo.

---

## Etapa 1: placa, gravação e telemetria (sem 12 V)

Black Pill alimentada só pelo ST-Link (3,3 V). Nada mais ligado.

1. `pio run -t upload` deve terminar com `Verified OK`.
2. LED: uma piscada curta por segundo (PARADO).
3. No `telemetry_log.py` aparece o cabeçalho e `diag` responde. A linha do relógio
   deve dizer `cristal 25 MHz`. Se disser `INTERNO`, o cristal não partiu: funciona,
   mas avise no relatório.
4. Ainda sem o MPU6050, `diag` reclama do MPU6050: é esperado.

## Etapa 2: MPU6050

Ligue o MPU6050 (3V3, GND, PB6, PB7) e monte-o no braço.

1. `diag` com o braço em pé e parado: aceleração no eixo **y ≈ +1 g** e as outras perto de 0.
   Se for outro eixo, a montagem está diferente da prevista: ajuste `IMU_ACC_UP_AXIS`,
   `IMU_ACC_SIDE_AXIS` e `IMU_GYRO_AXIS` em `include/board.h`.
2. `erros_i2c` deve ficar parado em 0.
3. Comando `sinais` e balance o braço com a mão por 3 s: o firmware diz se o
   giroscópio concorda com o ângulo. Se não, `inv giro` e depois fixe em `board.h`.
4. Encoste o braço no batente da esquerda e no da direita: a coluna `theta_graus`
   deve marcar ~±22° a ±25°.

## Etapa 3: encoder óptico (roda girada com a mão)

1. Gire a roda devagar com a mão: os LEDs dos dois módulos piscam.
2. Faça uma marca na roda e dê **uma volta exata**: a coluna `encoder` deve mudar
   **160 ± 2** contagens. Volte: deve voltar ao valor inicial.
3. Se muda só 40 ou 80 ou anda e volta, os sensores não estão em quadratura: deslize um
   deles nos rasgos da prateleira (alguns décimos de mm) e repita.
4. Com o analisador lógico (PulseView, canais em PA15 e PB3): ondas quadradas com
   defasagem de ~90° e sem repiques nas bordas.

## Etapa 4: motor sem roda, PWM baixo

Retire a roda (fica só o flange). Ligue os 12 V com o terminal pronto para mandar `s`.

1. `diag`: `vbus` perto de 12 V. Se der 0, confira o divisor em PA4.
2. `m 10`: o motor gira devagar. `s` para. `m -10`: gira ao contrário.
3. `m 30` por alguns segundos e `diag`: **`erros_i2c` não pode subir**. Se subir, o ruído
   do motor está chegando no I2C: capacitores no motor, fios do motor trançados e longe
   dos fios do MPU6050.

## Etapa 5: identificação do motor

Recoloque a roda. Prenda o braço (sargento ou a mão firme) na vertical.

1. Meça a resistência do motor com o multímetro nos terminais do motor, em 4 posições
   do eixo; use a **menor** leitura (desconte a resistência das pontas do multímetro).
2. Grave um log com `m 10`, espera 4 s, `m 20`, 4 s, `m 30`, 4 s, `m 40`, 4 s, `s`.
3. A roda deve girar no sentido que faz `roda_rpm` ficar **positivo**. Se ficar negativo,
   `inv enc` (o firmware avisa) e fixe em `board.h`.
4. `python tools/identify.py motor logs/ARQUIVO.csv --R 0.8` (com o R medido).
5. Coloque os valores em `sim/params.py` e regenere:
   `python -m sim.export_gains && pytest sim/tests && cd firmware && pio test -e native && pio run -t upload`.

## Etapa 6: pêndulo pendurado (confere massa e atrito)

Prenda a base **de cabeça para baixo** na borda da mesa, com o braço pendurado e livre.

1. Com o controle parado, afaste o braço ~10° e solte. Grave 20 s.
2. `python tools/identify.py pendulo logs/ARQUIVO.csv`
3. Se `Mgl/J` diferir mais de 10 % do modelo, pese as peças de novo e confira `l_w`.
   Coloque o `b_p` medido em `sim/params.py` e regenere.

## Etapa 7: sentido do ângulo e primeiro equilíbrio

Base de volta na posição normal.

**Conferência de sentido (obrigatória antes de equilibrar):** com `m 20` a roda gira num
sentido (veja de frente). Pare (`s`). Agora incline o braço com a mão **no mesmo sentido em
que a roda girou**: `theta_graus` tem que **aumentar**. Se diminuir, `inv ang` **e**
`inv giro` (os dois juntos) e fixe em `board.h`. Com o sentido errado o controle empurra o
pêndulo para o chão.

Primeiro equilíbrio, com corrente limitada:

1. `imax 4`
2. Braço encostado no batente e parado: aperte KEY (ou `a`). LED pisca rápido por 1 s
   (calibração do giroscópio), depois pisca médio (ARMADO).
3. Leve o braço devagar até a vertical e segure de leve: a menos de 3° e parado, o
   controle assume (LED aceso). Solte.
4. Se equilibrar, `imax 7` e depois `imax 10`.

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| empurra o braço para o chão na hora | sentido do ângulo invertido | conferência de sentido acima |
| vibra rápido / zumbido | ganho de velocidade alto para o ruído do giroscópio | `k2` com 20 % menos módulo |
| oscila devagar e cada vez mais | ganho de ângulo baixo | `k1` com 20 % mais módulo |
| equilibra, mas a roda acelera até cortar (falha 2) | ângulo de equilíbrio errado | espere o auto-ajuste (~10 s); se não bastar, `trim` com o valor que estabiliza |
| cai sempre para o mesmo lado | MPU6050 torto | `trim <graus>` e depois corrija a montagem |
| falha 3 durante o equilíbrio | ruído no I2C | etapa 4, item 3 |

Mudanças de ganho pela serial são perdidas ao desligar. Quando achar os valores bons,
coloque-os em `sim/controlador.py` (pesos do LQR) ou documente no relatório.

## Etapa 8: ensaios para o relatório

Grave cada ensaio num log separado e compare com a simulação (`python -m sim.lqr_design`
gera os mesmos gráficos do modelo em `sim/out/`).

1. **Equilíbrio parado**: 30 s sem tocar. Medir desvio RMS do ângulo e da roda.
2. **Peteleco**: toques no braço com intensidade crescente. Achar o maior que ele aguenta.
3. **Recuperação**: soltar de inclinações crescentes (5°, 10°, 15°). O modelo prevê até ~20°.
4. **Peso extra**: prender 20 g no topo do braço e repetir o equilíbrio (robustez).
5. **Erro de montagem**: `trim 2` e mostrar o auto-ajuste corrigindo sozinho.
