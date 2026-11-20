# Pêndulo invertido com roda de reação: Black Pill STM32F411

Trabalho de SEC. Um braço gira livre num pivô; no topo, um motor 775 acelera uma
roda pesada (12 parafusos M8 na borda) e a reação do torque mantém o braço em pé.
Controle LQR a 1 kHz numa WeAct Black Pill STM32F411CEU6.

## Estrutura

```
sim/        modelo físico, dimensionamento, projeto do LQR, testes (Python)
firmware/   PlatformIO + HAL da ST; lib/control é C puro testado no PC
cad/        peças em OpenSCAD paramétrico + verificador de folgas
tools/      gravação de telemetria, gráficos e identificação de parâmetros
docs/       compras, ligações, montagem e roteiro de testes de bancada
relatorio/  relatório técnico em LaTeX (Euler-Lagrange, LQR em variáveis de erro, mecânica, hardware)
```

Tudo sai de **[sim/params.py](sim/params.py)**: `python -m sim.export_gains` gera os
ganhos do firmware (`firmware/lib/control/lqr_gains.h`), os vetores de teste do C e as
dimensões da roda e do braço para o CAD (`cad/dimensoes_geradas.scad`). Um teste falha
se alguém mudar os parâmetros e esquecer de gerar de novo.

## Como rodar

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
source .venv/bin/activate

python -m sim.sizing          # tamanho da roda x inclinação recuperável
python -m sim.lqr_design      # ganhos, robustez e gráficos em sim/out/
python -m sim.export_gains    # depois de mudar sim/params.py
pytest sim/tests              # 34 testes: física, controle, ferramentas, coerência

cd firmware
pio test -e native            # 23 testes da lógica de controle, no PC
pio run                       # compila para a Black Pill
pio run -t upload             # grava pelo ST-Link

python cad/folgas.py          # confere ~40 folgas e interferências do CAD
./cad/build.sh                # STLs, imagens, gabarito e massas das peças
python -m sim.animacao --renderizar   # simulação animada no OpenSCAD -> cad/previews/simulacao.gif
openscad cad/simulacao.scad   # a mesma animação no OpenSCAD: View > Animate, FPS 25, Steps 140
python -m sim.export_relatorio && (cd relatorio && latexmk -pdf relatorio.tex)   # relatório em PDF
```

Instalação das ferramentas: `pipx install platformio` e `sudo apt install openscad`.

## Resultados da simulação (com parâmetros estimados)

| | |
|---|---|
| Roda | Ø 116 mm (132 mm com o anel do encoder), 385 g, 12 × M8 a 48 mm do centro |
| Braço | 96 mm do pivô ao eixo do motor; conjunto completo ~855 g (massa do braço tirada do CAD) |
| Ganhos | K = [−248,9 V/rad, −25,85 V·s/rad, −0,245 V·s/rad] |
| Recuperação | solta de até **19,8°** e volta à vertical (limite físico do torque: 22,4°) |
| Robustez | continua equilibrando com erros de 25 a 50 % na resistência e rotação do motor, nas massas e nos atritos |
| Roda em equilíbrio | ~100 rpm de pico ao soltar de 5°; limite de segurança em 2000 rpm |

Gráficos em [sim/out/](sim/out/) e animação da montagem em [cad/previews/simulacao.gif](cad/previews/simulacao.gif). Os parâmetros do motor 775 são estimativas (o anúncio só
informa "3000–5000 rpm"); os ganhos finais saem depois da identificação na bancada
([docs/testes_bancada.md](docs/testes_bancada.md), etapas 5 e 6).

## Firmware

- Máquina de estados: PARADO → CALIBRA (viés do giroscópio, 1 s parado) → ARMADO →
  EQUILIBRA (assume sozinho quando o braço passa perto da vertical) → FALHA.
- Proteções: inclinação > 20°, roda > 2000 rpm, MPU6050 sem resposta, falta de tensão
  (botão de emergência), sobretensão (energia da frenagem), corrente no limite por 1 s,
  cão de guarda de 100 ms, freio dinâmico ao falhar.
- Limite de corrente pelo modelo do motor (10 A), auto-ajuste do ângulo de equilíbrio,
  estimador de velocidade da roda que funciona de ~10 a 2000 rpm, recuperação automática
  do barramento I2C.
- Telemetria a 200 Hz e comandos pela serial (ganhos, sinais, ensaio em malha aberta).

## Documentação

- [docs/compras.md](docs/compras.md): o que falta comprar, o que muda com a Black Pill.
- [docs/ligacoes.md](docs/ligacoes.md): esquema de alimentação e pinagem.
- [docs/montagem.md](docs/montagem.md): medidas a conferir, impressão e montagem.
- [docs/testes_bancada.md](docs/testes_bancada.md): 8 etapas do primeiro LED ao relatório.
- [plano/montagem_fisica.pdf](plano/montagem_fisica.pdf): guia passo a passo da montagem física,
  das peças em mãos ao pêndulo ligado e conferido (figuras: `./cad/etapas_montagem.sh`).

## Licença

Código sob a licença MIT (ver [LICENSE](LICENSE)).
