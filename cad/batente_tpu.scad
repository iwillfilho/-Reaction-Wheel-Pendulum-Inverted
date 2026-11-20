// Almofada de TPU para a face inclinada dos batentes (imprimir 2).
// TPU 95A, 100 % de preenchimento, devagar (20-30 mm/s). Colar com cola de
// contato ou fita dupla face forte.

include <derivados.scad>

module batente_tpu() {
    linear_extrude(height = tpu_esp)
        offset(r = 2) offset(delta = -2) square([tpu_comp, tpu_larg]);
}

batente_tpu();
