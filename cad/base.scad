// Base: suportes da barra do pivô, batentes, postes da proteção e colunas da
// bandeja da eletrônica. Imprimir como está (fundo na mesa), sem suportes.
//
// Desenhada na posição de montagem: o pivô é a origem e o tampo fica em
// Z = -h_pivo. A face inclinada de cada batente recebe uma almofada de TPU
// (batente_tpu.scad) colada.
//
// PETG, 4 perímetros, 30 % de preenchimento. Prenda a base na mesa (furos
// dos cantos ou dois sargentos): quando o pêndulo bate no batente, o tranco
// vai para a base.

include <derivados.scad>

module mancal(y0) {
    difference() {
        union() {
            translate([-mancal_larg / 2, y0, z_base - 0.01]) cube([mancal_larg, mancal_esp, h_pivo + mancal_topo + 0.01]);
            // pé alargado até 25 mm abaixo do pivô (não chega perto dos colares)
            hull() {
                translate([-mancal_larg / 2, y0 - 8, z_base - 0.01]) cube([mancal_larg, mancal_esp + 16, 2]);
                translate([-mancal_larg / 2, y0, z_base - 0.01]) cube([mancal_larg, mancal_esp, h_pivo - 25]);
            }
        }
        // barra de 8 mm
        translate([0, y0 - 9, 0]) rotate([-90, 0, 0]) cylinder(d = barra_d + 0.15, h = mancal_esp + 18);
        // parafuso de trava da barra: inserto M3 por cima
        translate([0, y0 + mancal_esp / 2, mancal_topo - inserto_m3_prof]) cylinder(d = inserto_m3_d, h = inserto_m3_prof + 1);
        translate([0, y0 + mancal_esp / 2, 0]) cylinder(d = passagem_m3, h = mancal_topo);
    }
}

// Batente do lado X negativo (pega o braço inclinado de +angulo_batente).
// A face inclinada é paralela à lateral da cauda nessa inclinação e fica a
// tpu_esp dela; a almofada de TPU preenche esse espaço.
module batente() {
    intersection() {
        translate([-base_x / 2 + 5, -14, z_base - 0.01]) cube([base_x / 2 - 5, 20, batente_topo - z_base + 0.01]);
        rotate([0, angulo_batente, 0])
            translate([-larg_cauda / 2 - tpu_esp - 120, -20, -100]) cube([120, 40, 160]);
    }
}

module poste(s) {
    translate([s * prot_poste_x, 0, 0])
        difference() {
            translate([-poste_larg / 2, base_y_frente - poste_prof, z_base - 0.01]) cube([poste_larg, poste_prof, poste_alt + 0.01]);
            // ranhura da placa de policarbonato
            translate([-poste_larg / 2 - 1, prot_y - prot_rasgo / 2, z_base]) cube([poste_larg + 2, prot_rasgo, poste_alt + 1]);
            // parafuso M3 de aperto: passa pela frente, rosca no inserto de trás
            translate([0, base_y_frente + 1, z_base + poste_alt / 2]) rotate([90, 0, 0]) cylinder(d = passagem_m3, h = base_y_frente + 1 - prot_y);
            translate([0, prot_y - prot_rasgo / 2 + 0.01, z_base + poste_alt / 2]) rotate([90, 0, 0]) cylinder(d = inserto_m3_d, h = inserto_m3_prof);
        }
}

function cantos_bandeja() = [for (sx = [-1, 1], sy = [-1, 1]) [sx * (bandeja_x / 2 - 6), y_bandeja + sy * (bandeja_y / 2 - 6)]];

module base() {
    difference() {
        union() {
            translate([-base_x / 2, -base_y_tras, z_base - base_esp]) cube([base_x, base_y_tras + base_y_frente, base_esp]);
            mancal(y_mancal_frente);
            mancal(y_mancal_tras);
            batente();
            mirror([1, 0, 0]) batente();
            poste(-1);
            poste(1);
            for (c = cantos_bandeja()) translate([c[0], c[1], z_base - 0.01]) cylinder(d = 9, h = bandeja_altura + 0.01);
        }
        // insertos das colunas da bandeja
        for (c = cantos_bandeja())
            translate([c[0], c[1], z_base + bandeja_altura - inserto_m3_prof]) cylinder(d = inserto_m3_d, h = inserto_m3_prof + 1);
        // furos de fixação na mesa
        for (sx = [-1, 1], y = [-base_y_tras + 7, base_y_frente - 7])
            translate([sx * (base_x / 2 - 7), y, z_base - base_esp - 1]) cylinder(d = furo_fixacao, h = base_esp + 2);
    }
}

base();
