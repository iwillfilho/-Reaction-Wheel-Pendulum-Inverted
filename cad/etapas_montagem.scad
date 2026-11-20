// Imagens passo a passo para o guia de montagem (plano/montagem_fisica.tex).
//   openscad -D etapa=3 etapas_montagem.scad
// Cada etapa mostra o conjunto até aquele passo. As figuras são geradas por
// cad/etapas_montagem.sh em plano/figuras/.
//
//  1 braço com os 2 rolamentos        5 sensores ópticos e MPU6050
//  2 motor no braço (vista de trás)   6 base, almofadas e bandeja
//  3 flange no eixo                   7 pivô: barra entrando pela frente
//  4 roda com os 12 parafusos M8      8 conjunto completo com a proteção

include <derivados.scad>
use <montagem.scad>
use <braco.scad>
use <roda.scad>
use <suporte_sensores.scad>
use <base.scad>
use <bandeja.scad>

etapa = 8;   // [1:8]

module rolamentos() {
    color("Silver") for (y = [0, -tubo_comp + rol_esp])
        translate([0, y, 0]) rotate([90, 0, 0]) difference() {
            cylinder(d = rol_d, h = rol_esp);
            translate([0, 0, -1]) cylinder(d = barra_d, h = rol_esp + 2);
        }
}

module roda_completa() {
    color("Orange") translate([0, y_roda_frente, l_w]) rotate([90, 0, 0]) roda();
    parafusos_m8();
}

// braço e tudo o que vai nele, até a etapa e (máximo 5)
module pendulo_ate(e) {
    color("SteelBlue") rotate([90, 0, 0]) braco();
    rolamentos();
    if (e >= 2) motor_775();
    if (e >= 3) flange();
    if (e >= 4) roda_completa();
    if (e >= 5) {
        color("Gold") suporte_sensores();
        sensores();
        mpu6050();
    }
}

module almofadas() {
    x_tpu = larg_cauda / 2 + tpu_esp / 2;
    for (m = [0, 1]) mirror([m, 0, 0])
        color("Black") rotate([0, angulo_batente, 0])
            translate([-larg_cauda / 2 - tpu_esp, -12, (z_base + 2 - x_tpu * sin(angulo_batente)) / cos(angulo_batente)])
                cube([tpu_esp, tpu_larg, tpu_comp]);
}

module base_bandeja() {
    color("LightSlateGray") base();
    color("DarkSlateGray") translate([0, y_bandeja, z_base + bandeja_altura]) bandeja();
    almofadas();
}

// barra e colares; a barra pode ser desenhada puxada para a frente (+Y)
module barra_colares(recuo = 0) {
    color("Silver") {
        translate([0, y_mancal_tras - 3 + recuo, 0]) rotate([-90, 0, 0]) cylinder(d = barra_d, h = barra_comp);
        for (y = [0, -tubo_comp - colar_esp]) translate([0, y, 0]) rotate([-90, 0, 0]) cylinder(d = colar_d, h = colar_esp);
    }
}

if (etapa <= 5) {
    pendulo_ate(etapa);
} else if (etapa == 6) {
    base_bandeja();
} else if (etapa == 7) {
    base_bandeja();
    pendulo_ate(5);
    barra_colares(recuo = 110);
} else {
    base_bandeja();
    barra_colares();
    pendulo_ate(5);
    color("LightCyan", 0.35) translate([-prot_larg / 2, prot_y - 1.5, z_base]) cube([prot_larg, 3, prot_alt]);
}
