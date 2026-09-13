#!/bin/sh
# Regenera la presentación de Impress a partir del resumen (.qmd) y del estilo de la
# infografía web (.svg). Uso: scripts/infografia-emergencias-2025/generar.sh
set -e

DIR=$(cd "$(dirname "$0")" && pwd)
RAIZ=$(cd "$DIR/../.." && pwd)
BUNDLE="$RAIZ/content/historico/2025"
BUILD="$DIR/build"
mkdir -p "$BUILD"

# Entorno de Python con fontTools (se crea la primera vez)
if [ ! -x "$DIR/.venv/bin/python" ]; then
	python3 -m venv "$DIR/.venv"
	"$DIR/.venv/bin/pip" install -q fonttools
fi
PY="$DIR/.venv/bin/python"

# 1. Estilo de cada fase (colores, antetítulo, lema, créditos, iconos) desde la infografía web
"$PY" "$DIR/extraer.py" "$BUNDLE/infografia-emergencias-rfd-2025.svg" "$BUILD/estilo.json"

# 2. Contenido de cada fase desde el resumen
"$PY" "$DIR/leer_qmd.py" "$BUNDLE/resumen-escuela-rfd-2025.qmd" "$BUILD/estilo.json" \
	"$BUILD/contenido.json"

# 3. Avatar de la web recortado en círculo, con el borde suavizado
magick "$RAIZ/static/img/avatar.png" -filter Lanczos -resize 600x600 \
	\( -size 600x600 xc:black -fill white -draw "circle 299.5,299.5 299.5,1" \) \
	-alpha off -compose CopyOpacity -composite -resize 300x300 -strip \
	"$BUILD/avatar-circulo.png"

# 4. Presentación: se compone, LibreOffice la maqueta, se miden las líneas y se recoloca
AVATAR="$BUILD/avatar-circulo.png" "$PY" "$DIR/construir.py" "$BUILD/contenido.json" \
	"$BUNDLE/infografia-emergencias-rfd-2025.odp"
