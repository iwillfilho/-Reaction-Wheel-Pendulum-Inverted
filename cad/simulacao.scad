// Simulação animada do pêndulo (trajetória calculada por sim/animacao.py).
//
// No OpenSCAD: View > Animate, FPS = 25, Steps = n_quadros (ver o console).
// Para gerar de novo com outros parâmetros: python -m sim.animacao
//
// A roda gira de verdade na animação (marca branca no aro); acima de ~375 rpm
// o giro a 25 quadros por segundo começa a parecer mais lento do que é.

use <montagem.scad>
include <derivados.scad>
include <animacao_dados.scad>

quadro = -1;   // >= 0: mostra um quadro fixo; -1: segue a animação ($t)

k = quadro >= 0 ? min(quadro, n_quadros - 1) : min(n_quadros - 1, floor($t * n_quadros));
echo(str("Quadros: ", n_quadros, " (use Steps = ", n_quadros, ", FPS = ", anim_fps, ")"));

montagem(anim_theta[k], anim_giro[k], false);

// legenda de frente para a câmera
color("Black")
    for (i = [0 : 3])
        translate([prot_larg / 2 - 10, prot_y, l_w + r_aleta + 70 - 14 * i])   // vista de frente: +X fica à esquerda
            rotate([90, 0, 180])
                linear_extrude(height = 0.5) text(anim_legenda[k][i], size = 9, halign = "left");
