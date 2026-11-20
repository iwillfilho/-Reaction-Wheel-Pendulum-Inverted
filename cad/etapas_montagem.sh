#!/usr/bin/env bash
# Gera as figuras passo a passo do guia de montagem em plano/figuras/.
#
#   ./cad/etapas_montagem.sh
#
# Usa cad/etapas_montagem.scad (variável "etapa") e copia algumas prévias de
# cad/previews/ (gere-as antes com ./cad/build.sh, se tiver mudado o CAD).
set -euo pipefail
cd "$(dirname "$0")"

OPENSCAD="${OPENSCAD:-openscad}"
DEST=../plano/figuras
mkdir -p "$DEST"
RENDER=()
if [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null 2>&1; then
    RENDER=(xvfb-run -a)
fi

FRENTE="0,0,0,65,0,215,0"   # lado da roda
TRAS="0,0,0,65,0,35,0"      # lado do motor e da eletrônica

render() {  # nome etapa câmera
    echo "== $1"
    "${RENDER[@]}" "$OPENSCAD" --hardwarnings -o "$DEST/$1.png" --imgsize=1200,1000 \
        --viewall --autocenter --colorscheme=Tomorrow --camera="$3" -D "etapa=$2" etapas_montagem.scad
}

render etapa1_rolamentos 1 "$FRENTE"
render etapa2_motor      2 "$TRAS"
render etapa3_flange     3 "$FRENTE"
render etapa4_roda       4 "$FRENTE"
render etapa5_sensores   5 "0,0,0,80,0,200,0"
render etapa5_mpu        5 "$TRAS"
render etapa6_base       6 "0,0,0,50,0,200,0"
render etapa7_pivo       7 "$FRENTE"
render etapa8_completo   8 "$FRENTE"

for p in montagem_lado montagem_25graus_frente roda braco base suporte_sensores bandeja; do
    cp "previews/$p.png" "$DEST/$p.png"
done

echo "== cortando as margens vazias"
"${PY:-../.venv/bin/python}" - "$DEST" <<'EOF'
import sys
from pathlib import Path
from PIL import Image, ImageChops

for f in sorted(Path(sys.argv[1]).glob("*.png")):
    img = Image.open(f).convert("RGB")
    fundo = Image.new("RGB", img.size, img.getpixel((0, 0)))
    caixa = ImageChops.difference(img, fundo).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    if caixa:
        l, t, r, b = caixa
        m = 16
        img.crop((max(0, l - m), max(0, t - m), min(img.width, r + m), min(img.height, b + m))).save(f)
EOF
