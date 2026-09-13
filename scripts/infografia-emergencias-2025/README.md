# Infografía «Emergencias y desastres en comunidad» (Escuela 2025): versión Impress

Estos scripts generan `content/historico/2025/infografia-emergencias-rfd-2025.odp`, la
presentación de Impress (3 diapositivas A3: el antes, el durante y el después).

```sh
scripts/infografia-emergencias-2025/generar.sh
```

## De dónde sale cada cosa

- **Contenido** (título, subtítulo, idea central, estrategias, acciones y herramientas):
  del resumen `content/historico/2025/resumen-escuela-rfd-2025.qmd`. Para cambiar un texto,
  edita el `.qmd` y vuelve a ejecutar `generar.sh`.
- **Estilo de cada fase** (colores, antetítulo, lema del pie, créditos e iconos de sección):
  de la infografía web `infografia-emergencias-rfd-2025.svg`, que se edita en Inkscape.
- **Avatar**: `static/img/avatar.png`, recortado en círculo.

Al leer el `.qmd`, `leer_qmd.py` quita los recuentos «(todos los grupos)», «(4 de 5 grupos)»…,
coloca la puntuación que sigue a la negrita inicial dentro de la negrita y une las
subviñetas en un solo párrafo.

## Cómo se maqueta

- `odf.py` escribe el ODF directamente, sin convertir desde SVG, porque la conversión de
  LibreOffice estropeaba los iconos. Así cada texto es una caja de texto editable y los
  iconos son trazados vectoriales.
- El interlineado es **fijo**. LibreOffice aplica el interlineado proporcional sobre el alto
  natural de la fuente (1,25 em en Inter), no sobre el cuerpo de la letra, y eso descuadraba
  las alturas.
- `construir.py` maqueta en dos pasadas: prevé las líneas de cada elemento (midiendo con el
  kerning de Inter), deja que LibreOffice componga el PDF, lee con `pdftotext` cuántas líneas
  ocupa realmente cada elemento y recoloca con esas cifras. Si con las medidas reales el
  contenido no cabe, reduce el cuerpo de letra de las listas 0,25 px y repite.
- Las dos columnas de cada bloque se reparten por altura, respetando el orden de lectura.

## Requisitos

- Fuentes: Inter (`/usr/share/fonts/inter/Inter.ttc`) y una Nerd Font con los iconos
  Material Design (`/usr/share/fonts/TTF/JetBrainsMonoNerdFontPropo-Regular.ttf`). Las rutas
  están al principio de `odf.py`.
- LibreOffice (`libreoffice`), ImageMagick (`magick`) y Poppler (`pdftotext`).
- Python 3. `generar.sh` crea la primera vez un entorno en `.venv/` con `fonttools`.

La infografía web (SVG, PDF y PNG de `img/`) **no** se genera con estos scripts: se
mantiene a mano en Inkscape.
