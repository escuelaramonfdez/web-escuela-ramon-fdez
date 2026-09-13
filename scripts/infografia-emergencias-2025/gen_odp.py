#!/usr/bin/env python3
"""Versión para Impress: los tres bloques en formato de lista (sin numerar, sin estrellas,
sin fondos de color)."""
import json
import os
import sys
from odf import Doc, nlines, tw

W, H = 1122.5197, 1587.4016
M = 60.0
CW = W - 2 * M
INK, MUTED, PAPER, RULE = "#1E252D", "#45505B", "#FBF8F3", "#E2DBD1"
PEACH = "#F2A67E"
AVATAR = os.environ.get("AVATAR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "build", "avatar-circulo.png")
AV_D = 108.0          # diámetro del avatar
MEDIDAS = {}          # (texto, cuerpo, ancho) -> líneas reales medidas en el PDF
REGISTRO = None       # si es una lista, se anota la posición de cada elemento (verificación)


def blend(a, b, t):
    """Mezcla el color a con el b (t = proporción de b)."""
    pa, pb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def base_off(size, lh):
    """Distancia del borde superior de una caja de texto a la primera línea base.

    Con interlineado fijo, LibreOffice apoya la primera línea en el fondo de su
    caja menos el descendente (0,25 em según las métricas Windows de Inter).
    """
    return size * (lh - 0.25)


def line_center(size, lh):
    """Altura del centro visual de la primera línea (para alinear viñetas)."""
    return base_off(size, lh) - 0.35 * size


class Page:
    S_IDEA, LH_IDEA = 21.0, 1.40
    LH_ITEM = 1.40

    def __init__(self, d, p, idx, size=16.5):
        self.d, self.p, self.idx = d, p, idx
        self.dark, self.tint = p["dark"], p["tint"]
        self.S_ITEM = size
        k = size / 16.5
        self.GAP_ITEM = 18.0 * k        # separación entre elementos de una lista
        self.BULLET = 4.6 * k

    # ---------------------------------------------------------------- piezas
    def header(self):
        d, p, dk = self.d, self.p, self.dark
        s = [d.rect(0, 0, W, 200, dk, name="fondo cabecera"),
             d.rect(0, 200, W, 7, PEACH, name="franja")]
        s.append(d.textbox(M, 44, CW, 24, [(p["eyebrow"], d.pstyle(
            13.5, 700, color=blend(dk, "#ffffff", 0.78), ls=2.2, lh=1.3), None)], name="antetítulo"))
        s.append(d.textbox(M - 4, 67, 760, 96, [(p["title"], d.pstyle(
            72, 900, color="#ffffff", lh=1.25, ls=-1), None)], name="título"))
        s.append(d.textbox(M, 156, 760, 34, [(p["subtitle"], d.pstyle(
            23, 500, color=blend(dk, "#ffffff", 0.92), lh=1.3), None)], name="subtítulo"))
        names, step, r, cy = ["ANTES", "DURANTE", "DESPUÉS"], 118, 21, 112
        # avatar recortado en círculo, alineado con los circulitos de las fases
        av_cx = W - M - AV_D / 2
        s.append(d.image(AVATAR, av_cx - AV_D / 2, cy - AV_D / 2, AV_D, AV_D, name="avatar"))
        s.append(d.ellipse(av_cx, cy, AV_D / 2, stroke="#ffffff", sw=3, name="aro avatar"))
        half = tw(names[2], 12.5, 800, ls=1.6) / 2
        last = av_cx - AV_D / 2 - 28 - half
        cxs = [last - (2 - k) * step for k in range(3)]
        s.append(d.line(cxs[0], cy, cxs[2], cy, blend(dk, "#ffffff", 0.45), 2.5, dash="Punteado",
                        name="línea de fases"))
        for k, cx in enumerate(cxs):
            on = k == self.idx
            s.append(d.ellipse(cx, cy, r, fill="#ffffff" if on else dk,
                               stroke="#ffffff" if on else blend(dk, "#ffffff", 0.55), sw=2.5))
            s.append(d.textbox(cx - r, cy - 13, 2 * r, 26, [(str(k + 1), d.pstyle(
                19, 800, color=dk if on else blend(dk, "#ffffff", 0.7), align="center", lh=1.3), None)]))
            s.append(d.textbox(cx - 60, cy + 30, 120, 22, [(names[k], d.pstyle(
                12.5, 800, color=blend(dk, "#ffffff", 1 if on else 0.6), align="center", ls=1.6,
                lh=1.3), None)]))
        return s, 207

    def idea(self, y):
        d, p = self.d, self.p
        size, lh, pad, tx = self.S_IDEA, self.LH_IDEA, 22.0, M + 74
        n = nlines(p["idea"], CW - 74 - 28, size, 500, 800, True)
        h = pad * 2 + n * size * lh
        s = [d.rect(M, y, CW, h, self.tint, rx=14, name="fondo idea fuerza"),
             d.rect(M, y, 8, h, self.dark, name="barra"),
             d.icon("format_quote_open", M + 42, y + h / 2, 34, self.dark),
             d.textbox(tx, y + pad, CW - 74 - 28, h - 2 * pad,
                       [(p["idea"], d.pstyle(size, 500, italic=True, color=INK, lh=lh),
                         d.tstyle(size, 800, italic=True, color=self.dark))], name="idea fuerza")]
        return s, h

    def sec_head(self, y, key):
        d, dk = self.d, self.dark
        info = self.p["sec_icons"][key]
        s = [d.rect(M, y, 42, 42, dk, rx=10), d.icon(info["icon"], M + 21, y + 21, 25, "#ffffff")]
        lw = tw(info["label"], 25, 800, ls=1.8)
        s.append(d.textbox(M + 56, y + 4, lw + 20, 34, [(info["label"], d.pstyle(
            25, 800, color=dk, ls=1.8, lh=1.3), None)], name=f"título {key}"))
        sw = tw(info["sub"], 17, 500, True)
        s.append(d.textbox(M + 56 + lw + 14, y + 11, sw + 24, 26, [(info["sub"], d.pstyle(
            17, 500, italic=True, color=blend(PAPER, dk, 0.8), lh=1.3), None)]))
        x0 = M + 56 + lw + 14 + sw + 16
        s.append(d.line(x0, y + 24, W - M, y + 24, blend(PAPER, dk, 0.3), 2))
        return s, 42

    def item_list(self, x, y, colw, items, *, name):
        """Viñeta + texto (con arranque en negrita) y separadores. Devuelve (formas, alto)."""
        d, s, yy = self.d, [], y
        size, lh, gap = self.S_ITEM, self.LH_ITEM, self.GAP_ITEM
        tx, maxw = x + 22, colw - 22
        for k, md in enumerate(items):
            n = self.lines(md, maxw)
            h = n * size * lh
            if REGISTRO is not None:
                REGISTRO.append((self.idx, tx, yy, n, gap if k < len(items) - 1 else 0.0))
            s.append(d.ellipse(x + 6, yy + line_center(size, lh), self.BULLET, fill=self.dark))
            s.append(d.textbox(tx, yy, maxw, h + 4,
                               [(md, d.pstyle(size, 400, color=INK, lh=lh),
                                 d.tstyle(size, 700, color=self.dark))], name=f"{name} {k + 1}"))
            yy += h
            if k < len(items) - 1:
                s.append(d.line(tx, yy + gap / 2, x + colw, yy + gap / 2, RULE, 1.5))
                yy += gap
        return s, yy - y

    def lines(self, md, maxw):
        """Nº de líneas: la medida real si existe; si no, la previsión tipográfica."""
        key = (md, self.S_ITEM, round(maxw, 2))
        return MEDIDAS.get(key) or nlines(md, maxw, self.S_ITEM, 400, 700)

    def col_height(self, items, colw):
        size, lh = self.S_ITEM, self.LH_ITEM
        if not items:
            return 0.0
        return (sum(self.lines(md, colw - 22) * size * lh for md in items)
                + (len(items) - 1) * self.GAP_ITEM)

    def split_point(self, items, colw):
        """Corte entre columnas que iguala sus alturas, respetando el orden de lectura."""
        return min(range(1, len(items)),
                   key=lambda k: (max(self.col_height(items[:k], colw),
                                      self.col_height(items[k:], colw)), -k))

    def list_block(self, y, key, items, name):
        """Bloque completo: título de sección + dos columnas de elementos."""
        s, hh = self.sec_head(y, key)
        y0 = y + hh + 20
        colw = (CW - 36) / 2
        half = self.split_point(items, colw)
        hs = []
        for c, col in enumerate([items[:half], items[half:]]):
            sh, h = self.item_list(M + c * (colw + 36), y0, colw, col, name=name)
            s += sh
            hs.append(h)
        h = max(hs)
        s.append(self.d.line(M + colw + 18, y0, M + colw + 18, y0 + h, RULE, 1.5))
        return s, hh + 20 + h

    def footer(self):
        """Pie anclado al borde inferior, sobre el papel."""
        d, dk = self.d, self.dark
        h = 92.0
        y = H - h
        s = [d.line(M, y, W - M, y, blend(PAPER, dk, 0.35), 1.5),
             d.textbox(M, y + 20, CW - 140, 40, [(self.p["motto"], d.pstyle(
                 23, 800, italic=True, color=dk, lh=1.3), None)], name="lema"),
             d.textbox(M, y + 60, CW - 140, 24, [(self.p["credits"], d.pstyle(
                 12.5, 500, color=MUTED, lh=1.3), None)], name="créditos"),
             d.textbox(W - M - 120, y + 60, 120, 24, [(f"{self.idx + 1} / 3", d.pstyle(
                 12.5, 700, color=MUTED, align="end", lh=1.3), None)], name="número de página")]
        return s, y

    # ---------------------------------------------------------------- página
    BASE = [26.0, 36.0, 34.0, 34.0, 30.0]   # huecos mínimos entre bloques

    def blocks(self):
        return [("estrategias", self.p["strategies"], "estrategia"),
                ("acciones", self.p["actions"], "acción"),
                ("herramientas", self.p["tools"], "herramienta")]

    def free_space(self):
        """Espacio vertical sobrante con los huecos mínimos (negativo = no cabe)."""
        _, hh = self.header()
        _, foot_y = self.footer()
        _, ih = self.idea(0)
        hs = [self.list_block(0, k, it, n)[1] for k, it, n in self.blocks()]
        return foot_y - hh - ih - sum(hs) - sum(self.BASE)

    def build(self):
        global REGISTRO
        registro, REGISTRO = REGISTRO, None     # las mediciones previas no se anotan
        shapes, hh = self.header()
        foot, _ = self.footer()
        _, ih = self.idea(0)
        hs = [self.list_block(0, k, it, n)[1] for k, it, n in self.blocks()]
        free = self.free_space()
        REGISTRO = registro
        print(f"  {self.p['title']}: cuerpo {self.S_ITEM:g} px, espacio libre = {free:.0f} px",
              file=sys.stderr)
        g = [b + max(0.0, free) / len(self.BASE) for b in self.BASE]
        y = hh + g[0]
        shapes += self.idea(y)[0]
        y += ih + g[1]
        for i, (key, items, name) in enumerate(self.blocks()):
            shapes += self.list_block(y, key, items, name)[0]
            y += hs[i] + g[2 + i]
        return shapes + foot


def best_size(pages, start=16.5, stop=12.0, step=0.25, margin=12.0):
    """Mayor cuerpo de letra con el que las tres páginas caben (el mismo para todas)."""
    size = start
    while size >= stop:
        scratch = Doc(W, H, PAPER)          # documento desechable: solo para medir
        if all(Page(scratch, p, i, size).free_space() >= margin for i, p in enumerate(pages)):
            return size
        size -= step
    raise SystemExit("el contenido no cabe ni con el cuerpo mínimo")


def main(src, out):
    pages = json.load(open(src, encoding="utf-8"))
    size = best_size(pages)
    d = Doc(W, H, PAPER)
    for i, p in enumerate(pages):
        d.page(f"{i + 1} · {p['label']}", Page(d, p, i, size).build())
    d.save(out)
    print(f"escrito {out} (cuerpo de las listas: {size:g} px = {size * 0.75:g} pt)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
