// Roda de reação. Imprimir como está: face da FRENTE na mesa, sem suportes.
//
// Na mesa ficam o aro, o cubo, os raios e o anel dentado do encoder. Em cima
// (face de trás, voltada para o braço) ficam os alojamentos sextavados das
// porcas M8 e os furos dos insertos M3 do flange.
//
// PETG, 4 perímetros, preenchimento >= 60 % (o aro pode ser 100 %): a força
// centrífuga dos parafusos é suportada no plano das camadas.

include <derivados.scad>

module dente_vao(r1, r2, meio_ang, h) {
    // setor entre r1 e r2, de -meio_ang a +meio_ang
    linear_extrude(height = h)
        polygon([
            [r1 * cos(-meio_ang), r1 * sin(-meio_ang)],
            [r2 * cos(-meio_ang), r2 * sin(-meio_ang)],
            [r2, 0],
            [r2 * cos(meio_ang), r2 * sin(meio_ang)],
            [r1 * cos(meio_ang), r1 * sin(meio_ang)],
        ]);
}

module anel_encoder() {
    passo = 360 / n_ranhuras;
    difference() {
        cylinder(r = r_aleta, h = esp_aleta);
        translate([0, 0, -1]) cylinder(r = r_ext - 0.5, h = esp_aleta + 2);
        // vãos = metade do passo; abertos na borda, param 1,5 mm antes do aro
        for (i = [0 : n_ranhuras - 1])
            rotate(i * passo)
                translate([0, 0, -1]) dente_vao(r_ext + 1.5, r_aleta + 1, passo / 4, esp_aleta + 2);
    }
}

module roda() {
    difference() {
        union() {
            // aro
            difference() {
                cylinder(r = r_ext, h = esp_roda);
                translate([0, 0, -1]) cylinder(r = r_aro_int, h = esp_roda + 2);
            }
            anel_encoder();
            // cubo e raios
            cylinder(r = r_cubo, h = esp_alma);
            for (i = [0 : n_raios - 1])
                rotate(i * 360 / n_raios)
                    translate([r_cubo - 1, -larg_raio / 2, 0])
                        cube([r_aro_int - r_cubo + 2, larg_raio, esp_alma]);
        }
        // passagem da ponta do eixo
        translate([0, 0, -1]) cylinder(d = motor_eixo_d + 0.6, h = esp_alma + 2);
        // insertos M3 para o flange (entram pela face de cima)
        for (i = [0 : flange_n - 1])
            rotate(i * 360 / flange_n + 45)
                translate([flange_pcd / 2, 0, -1]) cylinder(d = inserto_m3_d, h = esp_alma + 2);
        // parafusos M8, entre os raios
        for (i = [0 : n_parafusos - 1])
            rotate((i + 0.5) * 360 / n_parafusos)
                translate([r_parafusos, 0, 0]) {
                    translate([0, 0, -1]) cylinder(d = furo_m8, h = esp_roda + 2);
                    // porca embutida, com as faces do sextavado viradas para dentro e para fora
                    translate([0, 0, esp_roda - m8_porca_h])
                        rotate(30) cylinder(d = (m8_chave + 0.4) / cos(30), h = m8_porca_h + 1, $fn = 6);
                }
    }
}

roda();
