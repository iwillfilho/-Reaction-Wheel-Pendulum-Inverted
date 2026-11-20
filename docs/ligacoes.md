# Ligações elétricas

Placa: **WeAct Black Pill STM32F411CEU6**. A fonte de verdade da pinagem é
[firmware/include/board.h](../firmware/include/board.h); a tabela abaixo é
conferida contra ela pelos testes (`pytest sim/tests`).

> **Regras de ouro**
> 1. Toda a lógica é **3,3 V**: MPU6050, sensores ópticos e o VCC lógico do IBT-2 ligam no pino **3V3** da Black Pill. Nenhum conversor de nível é necessário.
> 2. O pino **5V** da Black Pill é ligado direto no 5 V do conector USB-C, sem proteção. **Nunca ligue o USB-C com o conversor buck ligado.** Grave pelo ST-Link e use o adaptador USB-serial para telemetria: assim o USB-C nunca é usado.
> 3. Ajuste o buck em **5,0 V antes** de ligá-lo na placa.
> 4. Ligue o 12 V só depois de conferir tudo com o multímetro (continuidade e ausência de curto entre 12 V e GND).

## Alimentação

```
 Fonte 12 V (+) ── fusível 10 A ──┬── IBT-2 B+
                                  │     ├── 2× 4700 µF/35 V + 100 nF + TVS SMBJ15A ────┐
                                  │     └── divisor 10 k / 2,2 k ── PA4                │
                                  └── buck IN+  ── buck OUT+ (5,0 V) ── Black Pill 5V  │
 Fonte 12 V (−) ── ponto de terra (estrela) no B− do IBT-2 ────────────────────────────┘
                                  ├── buck IN− ;  buck OUT− ── Black Pill GND
```

- **Sem botão de emergência**: o motor é parado pelo firmware (botão KEY, comando `s` e as proteções). Se a tensão no B+ cair (fonte fraca ou mau contato), o firmware vê pelo divisor (falha 4, "sem tensão") e para tudo.
- **Capacitores e TVS** soldados o mais perto possível dos bornes B+ / B− do IBT-2. TVS SMBJ15A: catodo (faixa) no B+. Eletrolíticos: respeite a polaridade.
- **Divisor da tensão do barramento** (no B+ do IBT-2): 10 kΩ de B+ até PA4, 2,2 kΩ de PA4 até GND e um capacitor de 100 nF de PA4 até GND. A 16,5 V o pino fica em 2,97 V, dentro do limite do ADC.
- **Terra**: todos os retornos de potência se encontram num ponto só, no B− do IBT-2. O fio de GND da lógica (Black Pill ↔ conector do IBT-2) vai junto com os fios de sinal.

## Motor 775

- Fios de 14 AWG, curtos e trançados, do M+ / M− do IBT-2 até o motor.
- Solde no motor 3 capacitores cerâmicos de 100 nF: um entre os dois terminais e um de cada terminal até a carcaça. Isso corta a maior parte do ruído que trava o I2C.

## Pinagem da Black Pill

| Pino | Função | Liga em | Observação |
|---|---|---|---|
| **PB0** | IBT-2 RPWM | IBT-2 pino RPWM | TIM3_CH3, PWM 20 kHz |
| **PB1** | IBT-2 LPWM | IBT-2 pino LPWM | TIM3_CH4, PWM 20 kHz |
| **PB10** | IBT-2 R_EN + L_EN (juntos) | IBT-2 R_EN e L_EN unidos | resistor de 10 kΩ deste pino até GND (ponte desligada enquanto a placa reinicia) |
| **PA15** | Sensor óptico A (D0) | saída D0 do sensor A | TIM2_CH1, modo encoder |
| **PB3** | Sensor óptico B (D0) | saída D0 do sensor B | TIM2_CH2, modo encoder |
| **PB6** | MPU6050 SCL | SCL do GY-521 | I2C1, 400 kHz |
| **PB7** | MPU6050 SDA | SDA do GY-521 | I2C1 |
| **PA2** | Telemetria TX | RX do adaptador USB-serial | USART2, 460800 baud |
| **PA3** | Telemetria RX | TX do adaptador USB-serial | USART2 |
| **PA4** | Tensão do barramento | meio do divisor 10 k / 2,2 k | ADC1_IN4 |
| **PA5** | IBT-2 R_IS (opcional) | R_IS por divisor 10 k / 10 k | ADC1_IN5; só com `USE_CURRENT_SENSE 1` |
| **PA6** | IBT-2 L_IS (opcional) | L_IS por divisor 10 k / 10 k | ADC1_IN6; só com `USE_CURRENT_SENSE 1` |
| **PA0** | Botão KEY da placa | já está na placa | armar / parar |
| **PC13** | LED da placa | já está na placa | ver tabela do LED abaixo |

Reservados (não use): PA13/PA14 (SWD do ST-Link), PA11/PA12 (USB), PB2 (BOOT1).

### Alimentação dos módulos

| Módulo | VCC | GND | Observação |
|---|---|---|---|
| IBT-2 (conector de 8 pinos) | 3V3 | GND | as entradas aceitam 3,3 V direto (limiar máximo de 2,15 V) |
| MPU6050 (GY-521) | 3V3 | GND | AD0 em GND ou solto (endereço 0x68); INT não é usado |
| Sensores ópticos (2×) | 3V3 | GND | use a saída **D0**; A0 fica sem ligar |
| Adaptador USB-serial | **não ligar** | GND | só GND, TX e RX; adaptador de 3,3 V (CP2102/CH340) |
| ST-Link V2 | 3V3 só se a placa **não** estiver no buck | GND | SWDIO → DIO, SWCLK → CLK (conector de 4 pinos da Black Pill) |

> Se o IBT-2 não responder com VCC em 3,3 V (alguns lotes vêm com outro buffer), ligue o VCC dele em 5 V e confira com o osciloscópio ou o analisador lógico se os pinos RPWM/LPWM chegam nele.

## LED da placa (PC13)

| LED | Estado |
|---|---|
| uma piscada curta por segundo | PARADO |
| piscando rápido | CALIBRA (deixe o pêndulo parado) |
| piscando médio | ARMADO (leve o braço até a vertical) |
| aceso | EQUILIBRA |
| piscando em 5 Hz | MANUAL (ensaio do motor) |
| N piscadas a cada 3 s | FALHA número N (1 inclinação, 2 rotação da roda, 3 MPU6050, 4 sem tensão, 5 sobretensão, 6 motor travado) |
