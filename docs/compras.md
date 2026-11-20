# Lista de compras revisada (Black Pill)

Baseada na planilha *Materiais_trabalho_de_sec*, que foi montada para a
Nucleo-F401RE. Trocar a Nucleo pela Black Pill muda pouca coisa, mas a Black
Pill não tem gravador embutido nem os mesmos conectores.

## 1. Já comprados (conforme a planilha)

Ponte H BTS7960 (IBT-2) · motor 775 · MPU6050 · 2 sensores ópticos de fenda (LM393) ·
mini flange de eixo de 5 mm · 2 rolamentos 608-ZZ · barra de aço de 8 mm × 250 mm ·
2 colares SCC8 · insertos térmicos e parafusos M3 · termo-retrátil · fio de silicone 14 AWG ·
analisador lógico de 8 canais · placa adaptadora de bornes para Arduino Nano.

## 2. Na planilha, ainda sem compra: continuam necessários

| Item | Qtd. | Detalhe que o projeto definiu |
|---|---|---|
| Fonte 12 V ≥ 10 A | 1 | chaveada; a ATX pode desarmar na frenagem |
| Fusível 10 A retardado + porta-fusível | 1 | no positivo, logo depois da fonte |
| Botão de emergência DC ≥ 10 A, **NF** | 1 | corta só o positivo do motor |
| TVS SMBJ15A | 1 | |
| Capacitor eletrolítico 4700 µF / 35 V | 2 | |
| Capacitor cerâmico 100 nF | **6** | era 1: +3 no motor, +1 no PA4, +1 de reserva |
| Resistores | — | 10 k (×2: divisor e pull-down do EN), 2,2 k (×1); opcional 10 k (×4) para R_IS/L_IS |
| Parafusos **M8 × 16** + porcas + arruelas | 12 de cada | **M8 × 16 exatos**: mais compridos batem no braço. Pese e separe conjuntos iguais (±0,5 g) |
| Parafusos **M4 × 8** | 2 | prendem o motor; mais compridos podem tocar o enrolamento |
| Filamento PETG ~0,5 kg + TPU ~50 g | — | as peças somam ~350 g de PETG |
| Placa de policarbonato 2–3 mm | 1 | **230 × 230 mm** |
| Fios de silicone e conectores | — | 22–24 AWG para sinais |
| Placa perfurada + bornes de parafuso | 1 | onde vai a Black Pill |
| Fita isolante | 1 | |

## 3. Novos por causa da Black Pill

**Obrigatórios**

| Item | Qtd. | Por quê |
|---|---|---|
| Black Pill **WeAct STM32F411CEU6** | 1 | prefira a original WeAct (cristal de 25 MHz, botão KEY em PA0) |
| **ST-Link V2** (clone USB serve) | 1 | gravar e depurar; a Nucleo tinha um embutido |
| Barra de pinos fêmea 1 × 20 | 2 | para soquetar a Black Pill na placa perfurada |
| Jumpers fêmea-fêmea | ~10 | ST-Link e testes |
| Cabo USB-C de dados | 1 | só para gravação por DFU, se o ST-Link falhar |

**Recomendados**

| Item | Qtd. | Por quê |
|---|---|---|
| Conversor buck 12 V → 5 V (LM2596 ou MP1584) | 1 | alimenta a placa pela própria fonte de 12 V |
| Adaptador USB-serial **3,3 V** (CP2102 ou CH340) | 1 | telemetria e comandos durante os ensaios |
| Insertos térmicos M3 | 18 no total | 4 roda, 2+2 braço, 4 colunas da bandeja, 2 suportes da barra, 2 postes, 2 de reserva |
| Parafusos M3 sortidos + porcas + espaçadores de náilon 3 mm | kit | M3×8 (flange, bandeja), M3×10 (suporte, sensores), M3×12 (MPU, travas da barra), M3×16 (postes) |
| Cola de contato | 1 | almofadas de TPU nos batentes |
| Trava-rosca médio | 1 | parafusos do flange no eixo do motor |

**Opcional**: encoder magnético AS5600 + ímã, só se o ângulo pelo MPU6050 ficar ruidoso demais.

## 4. Deixam de ser usados

| Item | Motivo |
|---|---|
| STM32 Nucleo-F401RE | substituída pela Black Pill |
| Cabo Mini-USB | a Black Pill usa USB-C |
| Placa de bornes para Arduino Nano (já comprada) | tem 2 × 15 pinos e a Black Pill tem 2 × 20: não encaixa. Pode servir para outro projeto |

## 5. Ferramentas

Paquímetro, multímetro, ferro de solda (também para os insertos), balança de cozinha
(resolução de 1 g), serra para metal (cortar a barra em **82 mm**), lima, chaves Allen.
