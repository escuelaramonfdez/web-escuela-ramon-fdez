#!/usr/bin/env python3
"""Construye el ODP con las líneas reales de cada elemento, medidas en LibreOffice.

El corte de líneas de un texto solo depende del texto, del cuerpo de letra y del ancho
de la caja, así que se mide en un documento aparte donde cada texto tiene aire de sobra
(nunca se solapan) y después se maqueta la presentación con esas cifras exactas.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import gen_odp as g
from odf import Doc, nlines

COLW = (g.CW - 36) / 2          # ancho de columna de los bloques de lista
MAXW = COLW - 22                # ancho de la caja de texto (sin la viñeta)
SPARE = 3                       # líneas de aire bajo cada texto en el documento de medida


def to_pdf(odp, tmp):
    r = subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", odp, "--outdir", tmp],
                       capture_output=True, text=True, timeout=300)
    pdf = os.path.join(tmp, os.path.splitext(os.path.basename(odp))[0] + ".pdf")
    if not os.path.exists(pdf):
        raise SystemExit(f"LibreOffice no generó el PDF:\n{r.stderr}")
    return pdf


def line_tops(pdf, page):
    """Posición vertical (px) de cada línea de texto de una página del PDF."""
    xml = subprocess.run(["pdftotext", "-bbox-layout", "-f", str(page + 1), "-l", str(page + 1),
                          pdf, "-"], capture_output=True, text=True).stdout
    ys = sorted(float(m.group(1)) / 0.75 for m in re.finditer(r'<line xMin="[\d.]+" yMin="([\d.]+)"', xml))
    tops = []
    for y in ys:                # tramos de una misma línea (negrita y redonda) cuentan una vez
        if not tops or y - tops[-1] > 3:
            tops.append(y)
    return tops


def measure(pages, size, tmp):
    """{texto: nº de líneas} con el cuerpo dado, compuesto por LibreOffice."""
    texts = []
    for i, p in enumerate(pages):
        for _, items, _ in g.Page(Doc(g.W, g.H, g.PAPER), p, i, size).blocks():
            texts += [md for md in items if md not in texts]
    d = Doc(g.W, g.H, "#ffffff")
    pst = d.pstyle(size, 400, lh=g.Page.LH_ITEM)
    tst = d.tstyle(size, 700)
    pitch = size * g.Page.LH_ITEM
    layout, shapes, cur, y = [], [], [], 40.0
    for md in texts:
        h = (nlines(md, MAXW, size, 400, 700) + SPARE) * pitch
        if cur and y + h > g.H - 40:
            d.page(f"medida {len(layout) + 1}", shapes)
            layout.append(cur)
            shapes, cur, y = [], [], 40.0
        shapes.append(d.textbox(g.M + 22, y, MAXW, h, [(md, pst, tst)]))
        cur.append((md, y))
        y += h + 20
    d.page(f"medida {len(layout) + 1}", shapes)
    layout.append(cur)
    path = os.path.join(tmp, "medida.odp")
    d.save(path)
    pdf = to_pdf(path, tmp)
    result = {}
    for pn, items in enumerate(layout):
        tops = line_tops(pdf, pn)
        for k, (md, top) in enumerate(items):
            end = items[k + 1][1] if k + 1 < len(items) else float("inf")
            n = sum(1 for t in tops if top - 2 <= t < end - 2)
            if n == 0:
                raise SystemExit(f"no se pudo medir el texto: {md[:60]}…")
            result[md] = n
    return result


def verify(odp, tmp, size):
    """Comprueba en el PDF final que cada elemento ocupa sus líneas y no invade el hueco."""
    pdf = to_pdf(odp, tmp)
    pitch = size * g.Page.LH_ITEM
    problems, cache = [], {}
    for page, x, top, n, gap in g.REGISTRO:
        if page not in cache:
            xml = subprocess.run(["pdftotext", "-bbox-layout", "-f", str(page + 1), "-l",
                                  str(page + 1), pdf, "-"], capture_output=True, text=True).stdout
            cache[page] = [(float(a) / 0.75, float(b) / 0.75) for a, b in re.findall(
                r'<line xMin="([\d.]+)" yMin="([\d.]+)"', xml)]
        ys = sorted({round(y) for lx, y in cache[page] if abs(lx - x) < 4})
        inside = sum(1 for y in ys if top - 2 <= y < top + n * pitch - 2)
        spill = sum(1 for y in ys if top + n * pitch - 2 <= y < top + n * pitch + gap - 2)
        if inside != n or spill:
            problems.append(f"pág. {page + 1}, y={top:.0f}px: {inside} líneas de {n}, "
                            f"{spill} en el hueco")
    return problems


def min_free(pages, size):
    return min(g.Page(Doc(g.W, g.H, g.PAPER), p, i, size).free_space() for i, p in enumerate(pages))


def main(src, out):
    pages = json.load(open(src, encoding="utf-8"))
    size = g.best_size(pages, margin=0.0)
    tmp = tempfile.mkdtemp()
    try:
        while True:
            real = measure(pages, size, tmp)
            diff = sum(1 for md, n in real.items() if n != nlines(md, MAXW, size, 400, 700))
            g.MEDIDAS.update({(md, size, round(MAXW, 2)): n for md, n in real.items()})
            free = min_free(pages, size)
            print(f"cuerpo {size:g} px: {len(real)} textos medidos, {diff} con previsión "
                  f"distinta, holgura mínima {free:.0f} px", file=sys.stderr)
            if free >= 0:
                break
            size -= 0.25              # con las medidas reales no cabe: un cuarto de px menos
        d = Doc(g.W, g.H, g.PAPER)
        g.REGISTRO = []
        for i, p in enumerate(pages):
            d.page(f"{i + 1} · {p['label']}", g.Page(d, p, i, size).build())
        candidate = os.path.join(tmp, "presentacion.odp")
        d.save(candidate)
        problems = verify(candidate, tmp, size)
        if problems:
            raise SystemExit("la maquetación no cuadra con LibreOffice; no se instala:\n  "
                             + "\n  ".join(problems))
        print(f"verificación: {len(g.REGISTRO)} elementos, todos con sus líneas exactas y "
              f"sin invadir los huecos", file=sys.stderr)
        shutil.copyfile(candidate, out)
    finally:
        shutil.rmtree(tmp)
    print(f"escrito {out} (cuerpo de las listas: {size:g} px = {size * 0.75:g} pt)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
