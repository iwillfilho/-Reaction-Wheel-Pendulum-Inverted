// Bandeja da eletrônica: placa com grade de furos M3 (passo de 10 mm) para
// prender qualquer módulo com parafuso, porca e espaçador: placa perfurada
// com a Black Pill, ponte IBT-2, conversor buck, porta-fusível e bornes.
// Fica sobre 4 colunas da base, com espaço por baixo para os fios.
// Imprimir deitada, 3 perímetros, 25 % de preenchimento.

include <derivados.scad>

module bandeja() {
    difference() {
        translate([-bandeja_x / 2, -bandeja_y / 2, 0]) cube([bandeja_x, bandeja_y, bandeja_esp]);
        // furos dos cantos (colunas da base)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * (bandeja_x / 2 - 6), sy * (bandeja_y / 2 - 6), -1]) cylinder(d = passagem_m3, h = bandeja_esp + 2);
        // grade de furos, longe dos cantos
        nx = floor((bandeja_x - 30) / bandeja_passo);
        ny = floor((bandeja_y - 12) / bandeja_passo);
        for (i = [0 : nx], j = [0 : ny])
            translate([(i - nx / 2) * bandeja_passo, (j - ny / 2) * bandeja_passo, -1])
                cylinder(d = passagem_m3, h = bandeja_esp + 2, $fn = 24);
        // passagem central dos fios
        translate([-15, -4, -1]) cube([30, 8, bandeja_esp + 2]);
    }
}

bandeja();
