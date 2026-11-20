// Grandezas calculadas a partir de params.scad. As mesmas contas estão em
// cad/folgas.py, que confere as folgas sem precisar do OpenSCAD.

include <params.scad>

// eixo do motor para fora da face da frente do braço
eixo_fora = motor_eixo_comp + motor_ressalto_h - esp_face_motor;

// pilha no eixo, medida a partir da face da frente do braço (Y)
y_roda_frente = y_roda + esp_roda;              // face da frente da roda (lado das cabeças M8)
y_alma        = y_roda_frente - esp_alma;       // face de trás do cubo da roda = onde o flange encosta
y_flange      = y_alma - flange_esp;            // disco do flange
y_cubo        = y_flange - flange_cubo_comp;    // ponta do cubo do flange (lado do motor)
y_aleta       = y_roda_frente - esp_aleta / 2;  // plano médio do anel dentado

// sensores: as torres apontam para o centro da roda
r_feixe       = r_aleta - sens_penetra + sens_feixe;                   // raio onde o feixe corta os dentes
h_prateleira  = l_w - (r_aleta - sens_penetra + sens_torre_h + sens_pcb);  // topo da prateleira acima do pivô
// dois sensores defasados de 1 + 1/4 de passo -> sinais em quadratura
ang_quadratura = 1.25 * 360 / n_ranhuras;
dist_sensores  = 2 * r_feixe * sin(ang_quadratura / 2);
sup_larg       = dist_sensores + 2 * (sens_comp - sens_cabeca / 2) + 6;
sup_prof       = y_aleta + sens_larg / 2 + 2;

// posições ao longo do pivô (Y) dos suportes da barra
y_mancal_frente = colar_esp + 1;                  // depois do colar da frente
y_mancal_tras   = -(tubo_comp + colar_esp + 1) - mancal_esp;

// suporte dos sensores
z_prat_base   = h_prateleira - sup_esp;
aba_topo      = sup_furos_h + sup_rasgo / 2 + 3.5;
aba_larg      = sup_furos_dist + 12;

// base
z_base        = -h_pivo;                 // tampo da base
y_bandeja     = -base_y_tras + 4 + bandeja_y / 2;

// almofada de TPU: cobre a face inclinada do batente
tpu_comp      = (batente_topo - z_base) / cos(angulo_batente) - 3;
tpu_larg      = 16;

// barra: do suporte de trás ao da frente, 3 mm para fora de cada lado
barra_comp    = (y_mancal_frente + mancal_esp) - y_mancal_tras + 6;
