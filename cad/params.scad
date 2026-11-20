// Medidas das peças compradas e escolhas de projeto. Unidades: mm.
//
// CONFERIR = medir com paquímetro na peça real antes de imprimir; os valores
// abaixo são os típicos desses componentes. Este arquivo só tem números
// (nada de expressões): cad/folgas.py lê estes valores para conferir as folgas.
//
// Eixos do conjunto montado: origem no eixo do pivô; Z para cima (ao longo do
// braço); Y ao longo do pivô, positivo para o lado da roda; X lateral.

include <dimensoes_geradas.scad>

$fn = 72;
folga = 0.25;              // folga de impressão em encaixes

// ---- Motor 775 (CONFERIR) ----
motor_d          = 44.5;   // diâmetro da carcaça (há versões de 42)
motor_comp       = 67;     // comprimento da carcaça
motor_ressalto_d = 17.5;   // ressalto do mancal na face
motor_ressalto_h = 4.6;
motor_furos_dist = 29;     // distância entre os 2 furos M4 da face
motor_parafuso_d = 4.4;    // passagem do M4
motor_eixo_d     = 5;
motor_eixo_comp  = 17;     // eixo para fora do ressalto

// ---- Flange metálico de 5 mm (CONFERIR) ----
flange_d         = 22;     // diâmetro do disco
flange_esp       = 3;      // espessura do disco
flange_cubo_d    = 10;     // diâmetro do cubo (parte com os parafusos de trava)
flange_cubo_comp = 9;      // comprimento do cubo
flange_pcd       = 16;     // diâmetro do círculo dos furos
flange_n         = 4;      // número de furos

// ---- Fixadores ----
inserto_m3_d     = 4.0;    // furo para inserto térmico M3 (CONFERIR no seu inserto)
inserto_m3_prof  = 5;
passagem_m3      = 3.4;
m8_chave         = 13;     // porca M8, entre faces
m8_porca_h       = 6.5;
m8_cabeca_h      = 5.3;
m8_arruela_h     = 1.6;
m8_comp          = 16;     // parafuso M8x16 (mais comprido bate no braço)
m4_cabeca_h      = 3;      // cabeça do M4 que prende o motor

// ---- Rolamento 608-ZZ, barra e colar ----
rol_d            = 22;
rol_esp          = 7;
rol_ombro_d      = 15;     // furo entre os assentos: encosta só no anel externo
barra_d          = 8;
colar_d          = 14;     // colar SCC8 8-14-8
colar_esp        = 8;

// ---- Sensor óptico de fenda com LM393 (CONFERIR) ----
sens_comp        = 32;     // placa
sens_larg        = 14;
sens_pcb         = 1.6;
sens_torre_h     = 10.8;   // altura das torres acima da placa
sens_feixe       = 2.8;    // distância do topo das torres ao feixe
sens_fenda       = 5;      // vão entre as torres
sens_cabeca      = 6;      // comprimento do bloco do sensor ao longo da placa
sens_penetra     = 6.5;    // quanto o anel dentado entra na fenda
sens_furo_pos    = 22;     // do centro óptico ao furo de fixação da placa
sens_furo_d      = 2.6;    // furo guia para parafuso M3 direto no plástico

// ---- MPU6050 (GY-521) ----
mpu_furos_dist   = 15.2;
mpu_h            = 48;     // altura dos furos acima do pivô

// ---- Braço ----
esp_braco        = 8;      // espessura da placa
esp_face_motor   = 3.5;    // parede que sobra onde o motor é parafusado
r_pivo           = 18;     // raio do contorno em volta do pivô
tubo_d           = 32;     // tubo dos rolamentos
tubo_comp        = 34;
cauda            = 40;     // prolongamento abaixo do pivô que bate nos batentes
larg_cauda       = 14;
y_roda           = 8;      // da face da frente do braço até a face de trás da roda
sup_furos_dist   = 24;     // insertos do suporte dos sensores
sup_furos_h      = 33;     // altura desses insertos acima do pivô

// ---- Suporte dos sensores ----
sup_esp          = 4;      // espessura da prateleira
sup_aba_esp      = 3;      // espessura da aba parafusada no braço
sup_aba_alt      = 18;
sup_rasgo        = 8;      // curso do ajuste de altura

// ---- Base ----
h_pivo           = 50;     // altura do pivô acima do tampo da base
base_x           = 170;
base_y_frente    = 45;     // quanto a base avança para o lado da roda
base_y_tras      = 140;    // quanto avança para trás (eletrônica)
base_esp         = 6;
mancal_larg      = 26;     // suportes da barra
mancal_esp       = 12;
mancal_topo      = 11;     // material acima do centro da barra
batente_topo     = -13;    // altura do topo dos batentes (abaixo do pivô)
tpu_esp          = 3;      // almofada de TPU colada no batente

// ---- Bandeja da eletrônica ----
bandeja_x        = 150;
bandeja_y        = 66;
bandeja_esp      = 3;
bandeja_passo    = 10;     // grade de furos M3 para prender os módulos
bandeja_altura   = 8;      // colunas na base (fios passam por baixo)

// ---- Proteção de policarbonato (placa em pé na frente da roda) ----
prot_larg        = 230;
prot_alt         = 230;
prot_rasgo       = 3.4;    // ranhura para placa de 2 a 3 mm
prot_y           = 39;     // plano da placa
prot_poste_x     = 60;     // posição dos dois postes
poste_larg       = 16;
poste_prof       = 14;
poste_alt        = 40;

// ---- Fixação da base na mesa ----
furo_fixacao     = 4.5;
