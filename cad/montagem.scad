// Montagem completa, só para visualizar e conferir interferências.
//   openscad montagem.scad                       (em pé)
//   openscad -D inclinacao=25 montagem.scad      (encostado no batente)
// As peças compradas aparecem como formas simples (cinza / transparentes).

include <derivados.scad>
use <roda.scad>
use <braco.scad>
use <suporte_sensores.scad>
use <base.scad>
use <bandeja.scad>

inclinacao = 0;   // [-25:25] graus
giro_roda = 0;    // graus, roda em relação ao braço
mostrar_protecao = true;

module comprado() { color("Silver") children(); }

module motor_775() {
    comprado() {
        // carcaça atrás da face do braço
        translate([0, -esp_face_motor, l_w]) rotate([90, 0, 0]) cylinder(d = motor_d, h = motor_comp);
        translate([0, -esp_face_motor, l_w]) rotate([-90, 0, 0]) cylinder(d = motor_ressalto_d, h = motor_ressalto_h);
        translate([0, -esp_face_motor + motor_ressalto_h, l_w]) rotate([-90, 0, 0]) cylinder(d = motor_eixo_d, h = motor_eixo_comp);
        // parafusos M4 (cabeças na frente do braço)
        for (s = [-1, 1]) translate([s * motor_furos_dist / 2, 0, l_w]) rotate([-90, 0, 0]) cylinder(d = 7, h = m4_cabeca_h);
    }
}

module flange() {
    comprado() translate([0, 0, l_w]) rotate([-90, 0, 0]) {
        translate([0, 0, y_cubo]) cylinder(d = flange_cubo_d, h = flange_cubo_comp);
        translate([0, 0, y_flange]) cylinder(d = flange_d, h = flange_esp);
    }
}

module parafusos_m8() {
    comprado() translate([0, 0, l_w])
        for (i = [0 : n_parafusos - 1]) rotate([0, (i + 0.5) * 360 / n_parafusos, 0])
            translate([r_parafusos, 0, 0]) rotate([-90, 0, 0]) {
                // corpo: da ponta (atrás da roda) até a cabeça
                translate([0, 0, y_roda_frente + m8_arruela_h - m8_comp]) cylinder(d = 8, h = m8_comp);
                translate([0, 0, y_roda_frente]) cylinder(d = 16, h = m8_arruela_h);
                translate([0, 0, y_roda_frente + m8_arruela_h]) cylinder(d = m8_chave / cos(30), h = m8_cabeca_h, $fn = 6);
            }
}

module sensores() {
    color("DimGray")
        for (s = [-1, 1]) translate([s * dist_sensores / 2, y_aleta, h_prateleira]) {
            // placa saindo para fora
            translate([s > 0 ? -sens_cabeca / 2 : -(sens_comp - sens_cabeca / 2), -sens_larg / 2, 0])
                cube([sens_comp, sens_larg, sens_pcb]);
            // torres dos dois lados da fenda
            for (t = [-1, 1])
                translate([-sens_cabeca / 2, t > 0 ? sens_fenda / 2 : -sens_fenda / 2 - 4, sens_pcb])
                    cube([sens_cabeca, 4, sens_torre_h]);
        }
}

module mpu6050() {
    color("RoyalBlue") translate([-10.5, -esp_braco - 4.6, mpu_h - 3]) cube([21, 1.6, 16]);
}

// giro: ângulo da roda em relação ao braço (graus), em torno do eixo do motor
module pendulo(giro = 0) {
    color("SteelBlue") rotate([90, 0, 0]) braco();
    color("Gold") suporte_sensores();
    motor_775();
    sensores();
    mpu6050();
    comprado() for (y = [0, -tubo_comp + rol_esp])
        translate([0, y, 0]) rotate([90, 0, 0]) difference() { cylinder(d = rol_d, h = rol_esp); translate([0, 0, -1]) cylinder(d = barra_d, h = rol_esp + 2); }
    // partes que giram com a roda
    translate([0, 0, l_w]) rotate([0, giro, 0]) translate([0, 0, -l_w]) {
        color("Orange") translate([0, y_roda_frente, l_w]) rotate([90, 0, 0]) roda();
        flange();
        parafusos_m8();
        // marca branca no aro para enxergar o giro
        color("White") translate([0, y_roda_frente + 0.2, l_w + r_parafusos - 7]) rotate([90, 0, 0]) cylinder(d = 5, h = 0.5);
    }
}

module estatico(protecao = true) {
    color("LightSlateGray") base();
    color("DarkSlateGray") translate([0, y_bandeja, z_base + bandeja_altura]) bandeja();
    // almofadas de TPU nas faces dos batentes (no referencial do braço encostado)
    x_tpu = larg_cauda / 2 + tpu_esp / 2;
    for (m = [0, 1]) mirror([m, 0, 0])
        color("Black") rotate([0, angulo_batente, 0])
            translate([-larg_cauda / 2 - tpu_esp, -12, (z_base + 2 - x_tpu * sin(angulo_batente)) / cos(angulo_batente)])
                cube([tpu_esp, tpu_larg, tpu_comp]);
    // barra e colares
    comprado() {
        translate([0, y_mancal_tras - 3, 0]) rotate([-90, 0, 0]) cylinder(d = barra_d, h = barra_comp);
        for (y = [0, -tubo_comp - colar_esp]) translate([0, y, 0]) rotate([-90, 0, 0]) cylinder(d = colar_d, h = colar_esp);
    }
    if (protecao)
        color("LightCyan", 0.35) translate([-prot_larg / 2, prot_y - 1.5, z_base]) cube([prot_larg, 3, prot_alt]);
}

module montagem(ang = 0, giro = 0, protecao = true) {
    estatico(protecao);
    rotate([0, ang, 0]) pendulo(giro);
}

montagem(inclinacao, giro_roda, mostrar_protecao);
