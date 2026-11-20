// Gabarito 2D (1:1) da placa de proteção de policarbonato.
// Exportar em SVG (build.sh faz isso), imprimir em escala 100 %, conferir a
// régua de 100 mm com uma régua de verdade e colar sobre a placa para cortar
// e furar. Furos de 3,5 mm para os parafusos M3 de aperto dos postes.
// A borda de baixo é a que entra nas ranhuras dos postes.

include <derivados.scad>

module gabarito() {
    difference() {
        translate([-prot_larg / 2, 0]) square([prot_larg, prot_alt]);
        for (s = [-1, 1]) translate([s * prot_poste_x, poste_alt / 2]) circle(d = 3.5);
    }
    // cruzes de centro dos furos (para marcar com punção antes de furar)
    for (s = [-1, 1])
        translate([s * prot_poste_x, poste_alt / 2]) {
            square([12, 0.3], center = true);
            square([0.3, 12], center = true);
        }
    // régua de conferência de 100 mm, fora da placa
    translate([-50, -12]) square([100, 1]);
    for (x = [-50, 50]) translate([x - 0.5, -15]) square([1, 7]);
}

gabarito();
