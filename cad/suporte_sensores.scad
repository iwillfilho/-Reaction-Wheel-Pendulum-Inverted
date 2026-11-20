// Suporte dos 2 sensores ópticos de fenda. Imprimir como está (prateleira na
// mesa, aba para cima), sem suportes.
//
// Desenhado já na posição de montagem: a aba encosta na face da frente do
// braço (Y = 0) e a prateleira fica embaixo da roda. Os sensores ficam deitados
// na prateleira com as torres para cima, abraçando o anel dentado da roda.
//
// Ajustes:
//  - rasgos verticais da aba: altura (quanto o anel entra na fenda);
//  - rasgos dos sensores (ao longo de X): defasagem entre os dois sinais.
//    Os dois precisam ficar a 1 + 1/4 de dente um do outro para dar quadratura.

include <derivados.scad>

module rasgo(p1, p2, d, h) {
    hull() {
        translate(p1) cylinder(d = d, h = h);
        translate(p2) cylinder(d = d, h = h);
    }
}

module suporte_sensores() {
    difference() {
        union() {
            // prateleira
            translate([-sup_larg / 2, 0, z_prat_base]) cube([sup_larg, sup_prof, sup_esp]);
            // aba parafusada no braço
            translate([-aba_larg / 2, 0, z_prat_base]) cube([aba_larg, sup_aba_esp, aba_topo - z_prat_base]);
            // nervuras entre aba e prateleira (fora da área dos sensores)
            for (s = [-1, 1])
                translate([s * (aba_larg / 2 - 1.5) - 1.5, 0, h_prateleira - 0.01])
                    rotate([90, 0, 90])
                        linear_extrude(height = 3)
                            polygon([[sup_aba_esp - 0.01, 0], [sup_aba_esp + 7, 0], [sup_aba_esp - 0.01, 7]]);
        }
        // rasgos verticais da aba (parafusos M3 nos insertos do braço)
        for (s = [-1, 1])
            translate([s * sup_furos_dist / 2, -1, 0])
                rotate([-90, 0, 0])
                    rasgo([0, -(sup_furos_h - sup_rasgo / 2), 0], [0, -(sup_furos_h + sup_rasgo / 2), 0],
                          passagem_m3, sup_aba_esp + 2);
        // rasgos dos sensores: parafuso M3 + porca por baixo
        for (s = [-1, 1]) {
            x = s * (dist_sensores / 2 + sens_furo_pos);
            rasgo([x - 3, y_aleta, z_prat_base - 1], [x + 3, y_aleta, z_prat_base - 1], passagem_m3, sup_esp + 2);
        }
        // marcas da posição nominal do centro óptico de cada sensor
        for (s = [-1, 1])
            translate([s * dist_sensores / 2 - 0.4, sup_prof - 3, h_prateleira - 0.6]) cube([0.8, 4, 1]);
    }
}

suporte_sensores();
