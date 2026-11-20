// Vistas de detalhe para o guia de montagem (plano/montagem_fisica.tex):
// vistas explodidas, com as peças afastadas e setas vermelhas mostrando para
// onde cada uma vai, e os lugares dos insertos em vermelho.
//   openscad -D 'vista="exp_braco"' detalhes_montagem.scad
// As figuras são geradas por cad/etapas_montagem.sh em plano/figuras/.
//
//  ins_roda         insertos da roda (face de trás)
//  ins_braco_frente insertos do braço, face da frente
//  ins_braco_tras   insertos do braço, face de trás
//  ins_base         insertos da base
//  exp_braco        rolamentos, motor, parafusos M4 e flange
//  exp_m8           conjunto M8 entrando na roda
//  exp_roda         roda no flange, com os 4 parafusos M3 por trás
//  exp_sensores     suporte e sensores ópticos
//  sensores_zoom    corte: anel dentado passando no meio da fenda do sensor
//  exp_mpu          MPU6050 com espaçadores, atrás do braço
//  exp_protecao     placa de policarbonato entrando nos postes

include <derivados.scad>
use <montagem.scad>
use <braco.scad>
use <roda.scad>
use <suporte_sensores.scad>
use <base.scad>
use <bandeja.scad>

vista = "exp_braco";

DESTAQUE = "Red";

// ---- peças auxiliares ----------------------------------------------------------

// seta de p até q (a ponta fica em q)
module seta(p, q, d = 2.2) {
    v = q - p;
    L = norm(v);
    ponta = min(4 * d, L / 2);
    color(DESTAQUE) translate(p)
        rotate([0, acos(v[2] / L), atan2(v[1], v[0])]) {
            cylinder(d = d, h = L - ponta, $fn = 24);
            translate([0, 0, L - ponta]) cylinder(d1 = 2.6 * d, d2 = 0, h = ponta, $fn = 24);
        }
}

// parafuso ao longo de +Z, com a cabeça em z = 0 e o corpo para -Z
module parafuso(d, comp, cabeca_d, cabeca_h) {
    color("Silver") {
        cylinder(d = cabeca_d, h = cabeca_h, $fn = 24);
        translate([0, 0, -comp]) cylinder(d = d, h = comp, $fn = 24);
    }
}

module porca_m8() {
    color("Silver") difference() {
        cylinder(d = m8_chave / cos(30), h = m8_porca_h, $fn = 6);
        translate([0, 0, -1]) cylinder(d = 8, h = m8_porca_h + 2, $fn = 24);
    }
}

module inserto_destaque(h = inserto_m3_prof + 1.2) {
    color(DESTAQUE) cylinder(d = inserto_m3_d + 1.2, h = h, $fn = 24);
}

module rolamento() {
    color("Silver") rotate([90, 0, 0]) difference() {
        cylinder(d = rol_d, h = rol_esp);
        translate([0, 0, -1]) cylinder(d = barra_d, h = rol_esp + 2);
    }
}

module braco_azul() { color("SteelBlue") rotate([90, 0, 0]) braco(); }

module roda_laranja() { color("Orange") translate([0, y_roda_frente, l_w]) rotate([90, 0, 0]) roda(); }

// conjunto M8 na posição i da roda, afastado de "sai" mm para fora
module conjunto_m8(i, sai = 0) {
    a = (i + 0.5) * 360 / n_parafusos;
    translate([0, 0, l_w]) rotate([0, a, 0]) translate([r_parafusos, 0, 0]) {
        // cabeça e arruela na frente
        translate([0, sai, 0]) color("Silver") {
            translate([0, y_roda_frente, 0]) rotate([-90, 0, 0]) cylinder(d = 16, h = m8_arruela_h);
            translate([0, y_roda_frente + m8_arruela_h, 0]) rotate([-90, 0, 0])
                cylinder(d = m8_chave / cos(30), h = m8_cabeca_h, $fn = 6);
            translate([0, y_roda_frente + m8_arruela_h - m8_comp, 0]) rotate([-90, 0, 0]) cylinder(d = 8, h = m8_comp);
        }
        // porca no alojamento de trás
        translate([0, y_roda_frente - esp_roda - 2 * sai, 0]) rotate([-90, 0, 0]) rotate(30) porca_m8();
    }
}

// ---- vistas ----------------------------------------------------------------------

module ins_roda() {
    roda_laranja();
    translate([0, 0, l_w]) for (i = [0 : flange_n - 1]) rotate([0, -(i * 360 / flange_n + 45), 0])
        translate([flange_pcd / 2, y_alma + 0.01, 0]) rotate([-90, 0, 0]) translate([0, 0, -1.2]) inserto_destaque();
}

module ins_braco(frente) {
    braco_azul();
    if (frente)
        for (s = [-1, 1]) translate([s * sup_furos_dist / 2, 1.2, sup_furos_h]) rotate([90, 0, 0]) inserto_destaque();
    else
        for (s = [-1, 1]) translate([s * mpu_furos_dist / 2, -esp_braco - 1.2, mpu_h]) rotate([-90, 0, 0]) inserto_destaque();
}

module ins_base() {
    color("LightSlateGray") base();
    // topo dos suportes da barra
    for (y0 = [y_mancal_frente, y_mancal_tras])
        translate([0, y0 + mancal_esp / 2, mancal_topo - inserto_m3_prof]) inserto_destaque();
    // colunas da bandeja
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx * (bandeja_x / 2 - 6), y_bandeja + sy * (bandeja_y / 2 - 6), z_base + bandeja_altura - inserto_m3_prof])
            inserto_destaque();
    // parte de trás dos postes (o parafuso vem pela frente)
    for (s = [-1, 1])
        translate([s * prot_poste_x, prot_y - prot_rasgo / 2 + 1.2, z_base + poste_alt / 2]) rotate([90, 0, 0]) inserto_destaque();
}

module exp_braco() {
    braco_azul();
    // rolamentos: o da frente vem pela frente, o de trás por trás
    translate([0, 30, 0]) rolamento();
    translate([0, -tubo_comp + rol_esp - 30, 0]) rolamento();
    seta([0, 24, 17], [0, 4, 17]);
    seta([0, -tubo_comp - 25, 17], [0, -tubo_comp - 5, 17]);
    // motor por trás
    translate([0, -45, 0]) motor_775_sem_parafusos();
    seta([30, -48, l_w], [30, -12, l_w]);
    // parafusos M4 pela frente
    for (s = [-1, 1]) translate([s * motor_furos_dist / 2, 34, l_w]) rotate([-90, 0, 0]) parafuso(4, 8, 7, m4_cabeca_h);
    for (s = [-1, 1]) seta([s * motor_furos_dist / 2, 50, l_w], [s * motor_furos_dist / 2, 39, l_w], d = 1.6);
    // flange pela frente, no eixo
    translate([0, 70, 0]) flange();
    seta([0, 100, l_w], [0, 88, l_w]);
}

module motor_775_sem_parafusos() {
    color("Silver") {
        translate([0, -esp_face_motor, l_w]) rotate([90, 0, 0]) cylinder(d = motor_d, h = motor_comp);
        translate([0, -esp_face_motor, l_w]) rotate([-90, 0, 0]) cylinder(d = motor_ressalto_d, h = motor_ressalto_h);
        translate([0, -esp_face_motor + motor_ressalto_h, l_w]) rotate([-90, 0, 0]) cylinder(d = motor_eixo_d, h = motor_eixo_comp);
        // terminais
        for (s = [-1, 1]) translate([s * 9, -esp_face_motor - motor_comp - 6, l_w + 12]) cube([2.5, 6, 6]);
    }
}

module exp_m8() {
    roda_laranja();
    for (i = [0 : n_parafusos - 1]) conjunto_m8(i, (i == 2 || i == 3) ? 34 : 0);
    for (i = [2, 3]) {
        a = (i + 0.5) * 360 / n_parafusos;
        translate([0, 0, l_w]) rotate([0, a, 0]) translate([r_parafusos, 0, 0]) {
            seta([0, 52, 0], [0, 40, 0], d = 2);
            seta([0, -46, 0], [0, -30, 0], d = 2);
        }
    }
}

module exp_roda() {
    braco_azul();
    motor_775();
    flange();
    // roda (com os parafusos M8) afastada para a frente
    translate([0, 40, 0]) {
        roda_laranja();
        for (i = [0 : n_parafusos - 1]) conjunto_m8(i);
    }
    seta([0, 75, l_w + 75], [0, 50, l_w + 75], d = 3);
    // 4 parafusos M3 entram por trás do flange, nos insertos da roda
    translate([0, 0, l_w]) for (i = [0 : flange_n - 1]) rotate([0, -(i * 360 / flange_n + 45), 0])
        translate([flange_pcd / 2, y_flange, 0]) rotate([90, 0, 0]) parafuso(3, 8, 5.5, 3);
}

module exp_sensores() {
    braco_azul();
    motor_775();
    flange();
    roda_laranja();
    for (i = [0 : n_parafusos - 1]) conjunto_m8(i);
    translate([0, 35, -20]) {
        color("Gold") suporte_sensores();
        translate([0, 0, 22]) sensores();
    }
    seta([0, 32, h_prateleira - 18], [0, 10, h_prateleira - 18], d = 2.5);
    for (s = [-1, 1]) seta([s * 40, 35 + y_aleta, h_prateleira + 21], [s * 40, 35 + y_aleta, h_prateleira + 4], d = 1.8);
}

module sensores_zoom() {
    intersection() {
        union() {
            braco_azul();
            roda_laranja();
            color("Gold") suporte_sensores();
            sensores();
        }
        // corte no plano do sensor da direita: mostra o anel entre as duas torres
        translate([-60, -14, 14]) cube([60 + dist_sensores / 2, 50, 30]);
    }
}

module exp_mpu() {
    braco_azul();
    motor_775();
    // espaçadores e placa afastados para trás
    for (s = [-1, 1]) {
        color("White") translate([s * mpu_furos_dist / 2, -esp_braco - 12, mpu_h]) rotate([90, 0, 0]) difference() {
            cylinder(d = 6, h = 3, $fn = 24);
            translate([0, 0, -1]) cylinder(d = 3.2, h = 5, $fn = 24);
        }
        translate([s * mpu_furos_dist / 2, -esp_braco - 40, mpu_h]) rotate([90, 0, 0]) parafuso(3, 12, 5.5, 3);
    }
    translate([0, -22, 0]) mpu6050();
    // seta do eixo Y do módulo: para o motor (para cima)
    color("White") translate([0, -esp_braco - 4.6 - 22 - 0.3, mpu_h - 1]) rotate([90, 0, 0]) {
        translate([-0.6, 0, 0]) cube([1.2, 8, 0.6]);
        translate([0, 10, 0]) linear_extrude(0.6) polygon([[-2.5, -2.5], [2.5, -2.5], [0, 1.5]]);
    }
    seta([0, -58, mpu_h + 15], [0, -14, mpu_h + 15]);
}

module exp_protecao() {
    color("LightSlateGray") base();
    color("LightCyan", 0.5) translate([-prot_larg / 2, prot_y - 1.5, z_base + 90]) cube([prot_larg, 3, 110]);
    for (s = [-1, 1]) {
        seta([s * prot_poste_x, prot_y, z_base + 85], [s * prot_poste_x, prot_y, z_base + poste_alt + 4], d = 3);
        translate([s * prot_poste_x, base_y_frente + 18, z_base + poste_alt / 2]) rotate([-90, 0, 0]) parafuso(3, 16, 5.5, 3);
        seta([s * prot_poste_x, base_y_frente + 38, z_base + poste_alt / 2], [s * prot_poste_x, base_y_frente + 23, z_base + poste_alt / 2], d = 1.8);
    }
}

if (vista == "ins_roda") ins_roda();
else if (vista == "ins_braco_frente") ins_braco(true);
else if (vista == "ins_braco_tras") ins_braco(false);
else if (vista == "ins_base") ins_base();
else if (vista == "exp_braco") exp_braco();
else if (vista == "exp_m8") exp_m8();
else if (vista == "exp_roda") exp_roda();
else if (vista == "exp_sensores") exp_sensores();
else if (vista == "sensores_zoom") sensores_zoom();
else if (vista == "exp_mpu") exp_mpu();
else if (vista == "exp_protecao") exp_protecao();
