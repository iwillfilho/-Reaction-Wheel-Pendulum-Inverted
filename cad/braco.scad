// Braço do pêndulo. Imprimir como está: face da FRENTE (lado da roda) na
// mesa, sem suportes. O tubo dos rolamentos e o rebaixo do motor ficam para cima.
//
// Na peça: X lateral, Y ao longo do braço (pivô em 0, motor em l_w),
// Z = profundidade para trás a partir da face da frente.

include <derivados.scad>

module contorno_braco() {
    hull() {
        circle(r = r_pivo);
        translate([0, l_w]) circle(r = motor_d / 2 + 6);
    }
    // cauda que bate nos batentes da base
    translate([-larg_cauda / 2, -cauda]) square([larg_cauda, cauda]);
}

module braco() {
    difference() {
        union() {
            linear_extrude(height = esp_braco) contorno_braco();
            cylinder(d = tubo_d, h = tubo_comp);
        }

        // ---- pivô: dois rolamentos 608 ----
        translate([0, 0, -1]) cylinder(d = rol_ombro_d, h = tubo_comp + 2);
        // assento da frente (abre na mesa) + chanfro para o ombro imprimir sem suporte
        translate([0, 0, -0.01]) cylinder(d = rol_d + folga, h = rol_esp + 0.01);
        translate([0, 0, rol_esp - 0.01])
            cylinder(d1 = rol_d + folga, d2 = rol_ombro_d, h = (rol_d + folga - rol_ombro_d) / 2);
        // assento de trás (abre em cima)
        translate([0, 0, tubo_comp - rol_esp]) cylinder(d = rol_d + folga, h = rol_esp + 1);

        // ---- motor 775 ----
        translate([0, l_w, 0]) {
            // rebaixo onde a carcaça encaixa (centra o motor)
            translate([0, 0, esp_face_motor]) cylinder(d = motor_d + 2 * folga, h = esp_braco);
            // ressalto do mancal e eixo
            translate([0, 0, -1]) cylinder(d = motor_ressalto_d + 0.6, h = esp_braco + 2);
            // 2 parafusos M4 (entram pela frente)
            for (s = [-1, 1])
                translate([s * motor_furos_dist / 2, 0, -1]) cylinder(d = motor_parafuso_d, h = esp_braco + 2);
        }

        // ---- insertos M3 do suporte dos sensores (face da frente) ----
        for (s = [-1, 1])
            translate([s * sup_furos_dist / 2, sup_furos_h, -0.01])
                cylinder(d = inserto_m3_d, h = inserto_m3_prof + 0.01);

        // ---- insertos M3 do MPU6050 (face de trás) ----
        for (s = [-1, 1])
            translate([s * mpu_furos_dist / 2, mpu_h, esp_braco - inserto_m3_prof])
                cylinder(d = inserto_m3_d, h = inserto_m3_prof + 1);
    }
}

braco();
