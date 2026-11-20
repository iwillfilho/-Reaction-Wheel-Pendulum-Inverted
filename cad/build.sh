#!/usr/bin/env bash
# Gera os STLs, as imagens de conferência e o gabarito do policarbonato.
#
#   sudo apt install openscad      (uma vez)
#   ./cad/build.sh
#
# Saídas: cad/stl/*.stl, cad/previews/*.png, cad/gabarito_policarbonato.svg
set -euo pipefail
cd "$(dirname "$0")"

OPENSCAD="${OPENSCAD:-openscad}"
PY="${PY:-../.venv/bin/python}"
if ! command -v "$OPENSCAD" >/dev/null 2>&1; then
    echo "OpenSCAD não encontrado. Instale com: sudo apt install openscad" >&2
    exit 1
fi
# imagens PNG precisam de uma tela; sem tela, usa xvfb-run se existir
RENDER=()
if [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null 2>&1; then
    RENDER=(xvfb-run -a)
fi

echo "== conferindo folgas"
"$PY" folgas.py

mkdir -p stl previews
CAMERA_ISO="0,0,0,55,0,25,0"
for p in roda braco suporte_sensores base bandeja batente_tpu; do
    echo "== $p"
    "$OPENSCAD" --hardwarnings -o "stl/$p.stl" "$p.scad"
    "${RENDER[@]}" "$OPENSCAD" --hardwarnings -o "previews/$p.png" --imgsize=1200,900 \
        --viewall --autocenter --colorscheme=Tomorrow --camera="$CAMERA_ISO" "$p.scad"
done

echo "== montagem"
for ang in 0 25; do
    "${RENDER[@]}" "$OPENSCAD" --hardwarnings -o "previews/montagem_${ang}graus_iso.png" --imgsize=1400,1200 \
        --viewall --autocenter --colorscheme=Tomorrow --camera="0,0,0,65,0,35,0" -D "inclinacao=$ang" montagem.scad
    "${RENDER[@]}" "$OPENSCAD" --hardwarnings -o "previews/montagem_${ang}graus_frente.png" --imgsize=1400,1200 \
        --viewall --autocenter --colorscheme=Tomorrow --camera="0,0,0,90,0,180,0" \
        -D "inclinacao=$ang" -D "mostrar_protecao=false" montagem.scad
done
"${RENDER[@]}" "$OPENSCAD" --hardwarnings -o "previews/montagem_lado.png" --imgsize=1400,1200 \
    --viewall --autocenter --colorscheme=Tomorrow --camera="0,0,0,90,0,90,0" -D "mostrar_protecao=false" montagem.scad

echo "== gabarito do policarbonato"
"$OPENSCAD" --hardwarnings -o gabarito_policarbonato.svg gabarito_policarbonato.scad

echo "== massas e inércia das peças impressas"
"$PY" massas.py

echo
echo "Pronto: STLs em cad/stl/, imagens em cad/previews/, gabarito em cad/gabarito_policarbonato.svg"
