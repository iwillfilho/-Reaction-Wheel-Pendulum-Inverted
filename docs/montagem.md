# Montagem mecânica

> Guia completo, com figuras e a parte elétrica: [plano/montagem_fisica.pdf](../plano/montagem_fisica.pdf).

## 1. Antes de imprimir: medir as peças compradas

As medidas em [cad/params.scad](../cad/params.scad) marcadas `CONFERIR` são valores típicos.
Meça com paquímetro, corrija o arquivo e gere as peças de novo (`./cad/build.sh`).

| Peça | O que medir | Variável |
|---|---|---|
| Motor 775 | diâmetro da carcaça; distância entre os 2 furos M4 da face; diâmetro e altura do ressalto do mancal; comprimento do eixo para fora do ressalto | `motor_d`, `motor_furos_dist`, `motor_ressalto_d`, `motor_ressalto_h`, `motor_eixo_comp` |
| Flange de 5 mm | diâmetro e espessura do disco; diâmetro e comprimento do cubo; diâmetro do círculo dos furos | `flange_*` |
| Sensor óptico | altura das torres acima da placa; largura da fenda; distância do topo da torre até a janela do feixe; distância do centro da fenda ao furo da placa | `sens_*` |
| Inserto M3 | diâmetro externo (o furo fica ~0,2 mm menor) | `inserto_m3_d` |
| Parafuso M8 | comprimento abaixo da cabeça | `m8_comp` |

Depois de mudar qualquer medida, rode `python cad/folgas.py`: ele confere ~40 folgas
(eixo no flange, sensores no anel dentado, roda passando livre, batentes, proteção) e
diz exatamente o que bateu.

## 2. Impressão

| Peça | Qtd. | Material | Posição na mesa | Perímetros | Preenchimento |
|---|---|---|---|---|---|
| `roda` | 1 | PETG | face da frente na mesa (como sai do STL) | 4 | ≥ 60 % (aro a 100 % se o fatiador permitir modificador) |
| `braco` | 1 | PETG | face da frente na mesa | 4 | 50 % |
| `suporte_sensores` | 1 | PETG | prateleira na mesa | 4 | 60 % |
| `base` | 1 | PETG | fundo na mesa | 4 | 30 % |
| `bandeja` | 1 | PETG | deitada | 3 | 25 % |
| `batente_tpu` | 2 | TPU 95A | deitada | — | 100 %, 20–30 mm/s |

Nenhuma peça precisa de suporte. Camada de 0,2 mm. A roda é a peça crítica: ela gira até 2000 rpm
com 12 parafusos M8 na borda; não economize em perímetros.

## 3. Insertos

Ferro de solda a ~220 °C, inserto apoiado no furo, empurre devagar e reto até ficar 0,2 mm abaixo
da superfície. Lugares: 4 na roda (lado de trás do cubo, onde encosta o flange), 2 na frente do
braço (suporte dos sensores), 2 atrás do braço (MPU6050), 2 no topo dos suportes da barra,
4 nas colunas da bandeja, 2 na parte de trás dos postes da proteção.

## 4. Sequência de montagem

1. **Base**: cole as almofadas de TPU nas faces inclinadas dos batentes. Prenda a base na mesa
   (furos dos cantos ou dois sargentos).
2. **Barra**: corte com **82 mm**, tire a rebarba com a lima.
3. **Rolamentos**: encaixe os dois 608-ZZ nos assentos do braço (o da frente na face de baixo de
   impressão, o de trás na ponta do tubo). Se ficarem folgados, uma gota de cola no anel externo.
4. **Pivô**: passe a barra pelo suporte da frente, colar da frente, braço, colar de trás e suporte
   de trás. Aperte os parafusos de trava (M3 × 12) dos suportes. Encoste os colares nos anéis
   internos dos rolamentos deixando uma folga de uma folha de papel e aperte. O braço tem que
   cair livre de um lado para o outro até os batentes.
5. **Motor**: carcaça no rebaixo de trás do braço, 2 parafusos M4 × 8 pela frente.
6. **Flange**: no eixo do motor, com o cubo a ~2 mm do ressalto do motor; parafusos de trava
   no lado plano do eixo, com trava-rosca.
7. **Roda**: 12 conjuntos M8 (cabeça e arruela na frente, porca no alojamento de trás), bem
   apertados. Depois prenda a roda no flange com 4 M3 × 8 nos insertos.
8. **Balanceamento**: gire a roda com a mão; ela deve parar em posições aleatórias. Se sempre
   parar com o mesmo lado para baixo, troque parafusos de posição (o mais pesado para o lado
   que fica em cima) até melhorar.
9. **Sensores**: suporte na frente do braço (2 M3 × 10 nos insertos, pelos rasgos verticais);
   sensores deitados na prateleira com as torres para cima (M3 × 10 + porca por baixo).
   Ajuste a altura até o anel dentado ficar centrado na fenda e os LEDs dos módulos piscarem ao
   girar a roda devagar com a mão. Os traços na prateleira marcam a posição nominal de cada sensor.
10. **MPU6050**: atrás do braço, com espaçadores de 3 mm, eixo Y do módulo apontando para o motor.
11. **Eletrônica**: módulos parafusados na bandeja (grade de furos M3), bandeja nas colunas
    da base. Fiação conforme [ligacoes.md](ligacoes.md). Prenda os fios do braço com folga
    suficiente para ele ir de um batente ao outro.
12. **Proteção**: corte e fure o policarbonato com o gabarito (`cad/gabarito_policarbonato.svg`,
    impresso em escala 100 %: confira a régua de 100 mm). Encaixe nas ranhuras dos postes e aperte
    os 2 parafusos M3 × 16.

## 5. Depois de montar: pesar

Pese motor, roda completa, braço com rolamentos e o conjunto de um parafuso M8, e corrija em
[sim/params.py](../sim/params.py) os valores marcados `MEDIR`. Depois:

```bash
python -m sim.export_gains
cd firmware && pio test -e native && pio run -t upload
```
