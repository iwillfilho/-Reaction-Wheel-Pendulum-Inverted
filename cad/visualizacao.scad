// Peças da montagem separadas por grupo, para a visualização 3D em HTML
// (plano/visualizacao_projeto.html, gerada por tools/gerar_visualizacao.py).
//
//   openscad -o roda.stl -D 'parte="roda"' visualizacao.scad
//   openscad -o cotas.echo -D 'parte="cotas"' visualizacao.scad
//
// Tudo no referencial de cad/montagem.scad, com o braço em pé (inclinação 0) e a
// roda sem giro. Sem color(): as cores ficam na página.
//   estático: base, bandeja, tpu, barra_colares, protecao
//   braço (gira em Y, no pivô): braco, suporte_sensores, motor, sensores, mpu, rolamentos
//   roda (gira em Y, no eixo do motor, z = l_w): roda, flange, parafusos_m8

include <derivados.scad>
use <montagem.scad>
use <braco.scad>
use <roda.scad>
use <suporte_sensores.scad>
use <base.scad>
use <bandeja.scad>

parte = "cotas";

if (parte == "base") base();
if (parte == "bandeja") translate([0, y_bandeja, z_base + bandeja_altura]) bandeja();
if (parte == "tpu") {
    x_tpu = larg_cauda / 2 + tpu_esp / 2;
    for (m = [0, 1]) mirror([m, 0, 0])
        rotate([0, angulo_batente, 0])
            translate([-larg_cauda / 2 - tpu_esp, -12, (z_base + 2 - x_tpu * sin(angulo_batente)) / cos(angulo_batente)])
                cube([tpu_esp, tpu_larg, tpu_comp]);
}
if (parte == "barra_colares") {
    translate([0, y_mancal_tras - 3, 0]) rotate([-90, 0, 0]) cylinder(d = barra_d, h = barra_comp);
    for (y = [0, -tubo_comp - colar_esp]) translate([0, y, 0]) rotate([-90, 0, 0]) cylinder(d = colar_d, h = colar_esp);
}
if (parte == "protecao") translate([-prot_larg / 2, prot_y - 1.5, z_base]) cube([prot_larg, 3, prot_alt]);

if (parte == "braco") rotate([90, 0, 0]) braco();
if (parte == "suporte_sensores") suporte_sensores();
if (parte == "motor") motor_775();
if (parte == "sensores") sensores();
if (parte == "mpu") mpu6050();
if (parte == "rolamentos")
    for (y = [0, -tubo_comp + rol_esp])
        translate([0, y, 0]) rotate([90, 0, 0]) difference() {
            cylinder(d = rol_d, h = rol_esp);
            translate([0, 0, -1]) cylinder(d = barra_d, h = rol_esp + 2);
        }

if (parte == "roda") translate([0, y_roda_frente, l_w]) rotate([90, 0, 0]) roda();
if (parte == "flange") flange();
if (parte == "parafusos_m8") parafusos_m8();

// cotas lidas pelo gerador (ECHO: nome = valor)
if (parte == "cotas") {
    echo(l_w = l_w);
    echo(z_base = z_base);
    echo(h_pivo = h_pivo);
    echo(y_bandeja = y_bandeja);
    echo(bandeja_x = bandeja_x);
    echo(bandeja_y = bandeja_y);
    echo(bandeja_esp = bandeja_esp);
    echo(bandeja_altura = bandeja_altura);
    echo(base_x = base_x);
    echo(base_y_frente = base_y_frente);
    echo(base_y_tras = base_y_tras);
    echo(mpu_h = mpu_h);
    echo(esp_braco = esp_braco);
    echo(esp_face_motor = esp_face_motor);
    echo(motor_d = motor_d);
    echo(motor_comp = motor_comp);
    echo(y_aleta = y_aleta);
    echo(y_roda_frente = y_roda_frente);
    echo(h_prateleira = h_prateleira);
    echo(dist_sensores = dist_sensores);
    echo(sens_comp = sens_comp);
    echo(sens_cabeca = sens_cabeca);
    echo(prot_y = prot_y);
    echo(prot_alt = prot_alt);
    echo(angulo_batente = angulo_batente);
    echo(tubo_comp = tubo_comp);
    echo(r_pivo = r_pivo);
}
