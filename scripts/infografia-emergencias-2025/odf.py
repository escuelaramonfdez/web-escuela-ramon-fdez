#!/usr/bin/env python3
"""Mini-librería para escribir presentaciones ODF (Impress) a mano.

Se trabaja en píxeles del diseño original (96 ppp) y se convierte a mm al escribir.
"""
import functools
import html
import zipfile
from fontTools.ttLib import TTCollection, TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

MM = 25.4 / 96.0          # 1 px (96 ppp) en mm
PT = 0.75                 # 1 px en pt

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "presentation": "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}
NSDECL = " ".join(f'xmlns:{k}="{v}"' for k, v in NS.items())

# ------------------------------------------------------------------ fuentes
INTER = TTCollection("/usr/share/fonts/inter/Inter.ttc")
FACES = {(400, False): 0, (400, True): 3, (500, False): 10, (500, True): 11,
         (600, False): 12, (600, True): 13, (700, False): 14, (700, True): 15,
         (800, False): 16, (800, True): 17, (900, False): 1, (900, True): 2}
# peso -> (nombre de familia en el sistema, usar negrita)
FONTNAME = {400: ("Inter", False), 500: ("Inter Medium", False), 600: ("Inter SemiBold", False),
            700: ("Inter", True), 800: ("Inter ExtraBold", False), 900: ("Inter Black", False)}
FONT_FACES = ["Inter", "Inter Medium", "Inter SemiBold", "Inter ExtraBold", "Inter Black"]
_met = {}


def _kerning(font):
    """Pares de kerning de la característica 'kern' (GPOS): formato 1 y por clases."""
    if "GPOS" not in font:
        return {}, []
    gpos = font["GPOS"].table
    idx = set()
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == "kern":
            idx.update(fr.Feature.LookupListIndex)
    pairs, classes = {}, []
    for li in sorted(idx):
        lk = gpos.LookupList.Lookup[li]
        for st in lk.SubTable:
            ltype = lk.LookupType
            if ltype == 9:
                ltype, st = st.ExtensionLookupType, st.ExtSubTable
            if ltype != 2:
                continue
            if st.Format == 1:
                for g1, ps in zip(st.Coverage.glyphs, st.PairSet):
                    for r in ps.PairValueRecord:
                        v = getattr(r.Value1, "XAdvance", 0) if r.Value1 else 0
                        if v:
                            pairs.setdefault((g1, r.SecondGlyph), v)
            elif st.Format == 2:
                classes.append((set(st.Coverage.glyphs), st.ClassDef1.classDefs,
                                st.ClassDef2.classDefs, st.Class1Record))
    return pairs, classes


def _kern(k, g1, g2):
    pairs, classes = k
    v = pairs.get((g1, g2))
    if v is not None:
        return v
    for cov, cd1, cd2, recs in classes:
        if g1 in cov:
            val = recs[cd1.get(g1, 0)].Class2Record[cd2.get(g2, 0)].Value1
            return (getattr(val, "XAdvance", 0) or 0) if val else 0
    return 0


def _metrics(w, it):
    if (w, it) not in _met:
        f = INTER.fonts[FACES[(w, it)]]
        _met[(w, it)] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm, _kerning(f))
    return _met[(w, it)]


@functools.lru_cache(maxsize=None)
def tw(s, size, w=400, it=False, ls=0.0):
    """Ancho del texto en px, con el kerning de la fuente."""
    cmap, hm, upm, kern = _metrics(w, it)
    gl = [cmap.get(ord(c), cmap[ord("?")]) for c in s]
    tot = sum(hm[g][0] for g in gl) + sum(_kern(kern, a, b) for a, b in zip(gl, gl[1:]))
    return tot * size / upm + ls * max(len(s) - 1, 0)


NF = TTFont("/usr/share/fonts/TTF/JetBrainsMonoNerdFontPropo-Regular.ttf")
GS = NF.getGlyphSet()


def icon_path(name, box=1000):
    """Contorno del icono MDI en una caja box×box (coordenadas de viewBox, y hacia abajo)."""
    g = GS["md-" + name]
    bp = BoundsPen(GS)
    g.draw(bp)
    x0, y0, x1, y1 = bp.bounds
    s = box / max(x1 - x0, y1 - y0)
    tx, ty = box / 2 - s * (x0 + x1) / 2, box / 2 + s * (y0 + y1) / 2
    sp = SVGPathPen(GS, ntos=lambda v: str(round(v)))
    g.draw(TransformPen(sp, (s, 0, 0, -s, tx, ty)))
    return sp.getCommands()


# ------------------------------------------------------------------ texto
def words_of(md):
    chars, bold, i = [], False, 0
    while i < len(md):
        if md.startswith("**", i):
            bold = not bold
            i += 2
            continue
        chars.append((md[i], bold))
        i += 1
    words, cur = [], []
    for c, b in chars:
        if c == " ":
            if cur:
                words.append(cur)
            cur = []
        else:
            if cur and cur[-1][1] == b:
                cur[-1] = (cur[-1][0] + c, b)
            else:
                cur.append((c, b))
    if cur:
        words.append(cur)
    return words


def nlines(md, maxw, size, w=400, bw=700, it=False, safety=1.0):
    """Nº de líneas que ocupará el texto en una caja de ancho maxw."""
    words = words_of(md)
    ww = lambda wd: sum(tw(t, size, bw if b else w, it) for t, b in wd)
    sp = tw(" ", size, w, it)
    n, curw = 1, 0.0
    for wd in words:
        x = ww(wd) * safety
        if curw and curw + sp + x > maxw:
            n, curw = n + 1, x
        else:
            curw += (sp if curw else 0) + x
    return n


def esc(s):
    return html.escape(s, quote=False)


# ------------------------------------------------------------------ documento
class Doc:
    def __init__(self, w_px, h_px, bg="#ffffff"):
        self.w, self.h, self.bg = w_px, h_px, bg
        self.styles, self.seen = [], {}
        self.pages = []
        self.images = {}          # ruta dentro del zip -> archivo local

    # --- estilos -------------------------------------------------------
    def _style(self, kind, props, family, extra=""):
        key = (kind, props, family, extra)
        if key in self.seen:
            return self.seen[key]
        name = f"{kind}{len(self.seen) + 1}"
        self.seen[key] = name
        self.styles.append(f'<style:style style:name="{name}" style:family="{family}"{extra}>'
                           f"{props}</style:style>")
        return name

    def gstyle(self, fill=None, stroke=None, sw=1.2, dash=None, textbox=False, valign="top"):
        p = []
        p.append(f'draw:fill="solid" draw:fill-color="{fill}"' if fill else 'draw:fill="none"')
        if stroke:
            p.append(f'draw:stroke="{"dash" if dash else "solid"}" svg:stroke-color="{stroke}" '
                     f'svg:stroke-width="{sw * MM:.3f}mm"')
            if dash:
                p.append(f'draw:stroke-dash="{dash}"')
        else:
            p.append('draw:stroke="none"')
        if textbox:
            p.append('draw:auto-grow-height="false" draw:auto-grow-width="false" '
                     'fo:padding-top="0mm" fo:padding-bottom="0mm" fo:padding-left="0mm" '
                     'fo:padding-right="0mm" fo:min-height="0mm" fo:wrap-option="wrap" '
                     f'draw:textarea-vertical-align="{valign}"')
        return self._style("gr", f'<style:graphic-properties {" ".join(p)}/>', "graphic")

    def pstyle(self, size, weight=400, italic=False, color="#000000", lh=1.35,
               align="start", ls=0.0, space_before=0.0):
        fam, bold = FONTNAME[weight]
        t = [f'style:font-name="{fam}"', f'fo:font-size="{size * PT:.2f}pt"',
             f'fo:color="{color}"', f'fo:font-weight="{"bold" if bold else "normal"}"',
             f'fo:font-style="{"italic" if italic else "normal"}"']
        if ls:
            t.append(f'fo:letter-spacing="{ls * MM:.3f}mm"')
        # interlineado fijo: el proporcional de LibreOffice se aplica sobre el alto
        # natural de la fuente (1,25 em en Inter), no sobre el cuerpo de la letra
        props = (f'<style:paragraph-properties fo:line-height="{lh * size * MM:.3f}mm" '
                 f'fo:text-align="{align}" fo:margin-bottom="0mm" '
                 f'fo:margin-top="{space_before * MM:.3f}mm"/>'
                 f'<style:text-properties {" ".join(t)}/>')
        return self._style("P", props, "paragraph")

    def tstyle(self, size, weight, italic=False, color="#000000", ls=0.0):
        fam, bold = FONTNAME[weight]
        t = [f'style:font-name="{fam}"', f'fo:font-size="{size * PT:.2f}pt"',
             f'fo:color="{color}"', f'fo:font-weight="{"bold" if bold else "normal"}"',
             f'fo:font-style="{"italic" if italic else "normal"}"']
        if ls:
            t.append(f'fo:letter-spacing="{ls * MM:.3f}mm"')
        return self._style("T", f'<style:text-properties {" ".join(t)}/>', "text")

    # --- formas --------------------------------------------------------
    def _geo(self, x, y, w, h):
        return (f'svg:x="{x * MM:.3f}mm" svg:y="{y * MM:.3f}mm" '
                f'svg:width="{w * MM:.3f}mm" svg:height="{h * MM:.3f}mm"')

    def rect(self, x, y, w, h, fill, rx=0, name=None, stroke=None, sw=1.2):
        st = self.gstyle(fill=fill, stroke=stroke, sw=sw)
        r = f' draw:corner-radius="{rx * MM:.3f}mm"' if rx else ""
        return (f'<draw:rect draw:style-name="{st}"{self._name(name)} {self._geo(x, y, w, h)}{r}>'
                f"</draw:rect>")

    def ellipse(self, cx, cy, r, fill=None, stroke=None, sw=1.2, name=None):
        st = self.gstyle(fill=fill, stroke=stroke, sw=sw)
        return (f'<draw:ellipse draw:style-name="{st}"{self._name(name)} '
                f"{self._geo(cx - r, cy - r, 2 * r, 2 * r)}></draw:ellipse>")

    def line(self, x1, y1, x2, y2, color, sw=1.5, dash=None, name=None):
        st = self.gstyle(stroke=color, sw=sw, dash=dash)
        return (f'<draw:line draw:style-name="{st}"{self._name(name)} '
                f'svg:x1="{x1 * MM:.3f}mm" svg:y1="{y1 * MM:.3f}mm" '
                f'svg:x2="{x2 * MM:.3f}mm" svg:y2="{y2 * MM:.3f}mm"></draw:line>')

    def icon(self, name, cx, cy, size, fill, box=1000):
        st = self.gstyle(fill=fill)
        d = icon_path(name, box)
        return (f'<draw:path draw:style-name="{st}" draw:name="icono {name}" '
                f'{self._geo(cx - size / 2, cy - size / 2, size, size)} '
                f'svg:viewBox="0 0 {box} {box}" svg:d="{esc(d)}"></draw:path>')

    def image(self, path, x, y, w, h, name=None):
        """Imagen incrustada (PNG) en un marco; se guarda en Pictures/."""
        import os
        ref = "Pictures/" + os.path.basename(path)
        self.images[ref] = path
        st = self.gstyle()
        return (f'<draw:frame draw:style-name="{st}"{self._name(name)} {self._geo(x, y, w, h)}>'
                f'<draw:image xlink:href="{ref}" xlink:type="simple" xlink:show="embed" '
                f'xlink:actuate="onLoad"/></draw:frame>')

    def _name(self, name):
        return f' draw:name="{esc(name)}"' if name else ""

    def textbox(self, x, y, w, h, paras, valign="top", name=None):
        """paras: lista de (markdown, pstyle_name, tstyle_negrita_name)."""
        st = self.gstyle(textbox=True, valign=valign)
        body = []
        for md, ps, ts in paras:
            runs = []
            for word_i, wd in enumerate(words_of(md)):
                if word_i:
                    runs.append((" ", False))
                runs.extend(wd)
            merged = []
            for t, b in runs:
                if merged and merged[-1][1] == b:
                    merged[-1] = [merged[-1][0] + t, b]
                else:
                    merged.append([t, b])
            inner = "".join(f'<text:span text:style-name="{ts}">{esc(t)}</text:span>' if b and ts
                            else esc(t) for t, b in merged)
            body.append(f'<text:p text:style-name="{ps}">{inner}</text:p>')
        return (f'<draw:frame draw:style-name="{st}"{self._name(name)} {self._geo(x, y, w, h)}>'
                f"<draw:text-box>{''.join(body)}</draw:text-box></draw:frame>")

    # --- páginas y escritura -------------------------------------------
    def page(self, name, shapes):
        self.pages.append((name, "".join(shapes)))

    def save(self, path):
        dp = ('<style:style style:name="dp1" style:family="drawing-page">'
              '<style:drawing-page-properties draw:background-size="border" draw:fill="solid" '
              f'draw:fill-color="{self.bg}" presentation:background-objects-visible="true" '
              'presentation:background-visible="true" presentation:display-footer="false" '
              'presentation:display-page-number="false" presentation:display-date-time="false"/>'
              "</style:style>")
        faces = "".join(f'<style:font-face style:name="{f}" svg:font-family="&quot;{f}&quot;" '
                        f'style:font-family-generic="swiss" style:font-pitch="variable"/>'
                        for f in FONT_FACES)
        dashes = ('<draw:stroke-dash draw:name="Punteado" draw:style="round" '
                  'draw:dots1="1" draw:dots1-length="0.15%" draw:distance="0.4%" '
                  'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"/>')
        styles = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles {NSDECL} office:version="1.3">
<office:font-face-decls>{faces}</office:font-face-decls>
<office:styles>{dashes}</office:styles>
<office:automatic-styles>
<style:page-layout style:name="PM1"><style:page-layout-properties
 fo:page-width="{self.w * MM:.3f}mm" fo:page-height="{self.h * MM:.3f}mm"
 style:print-orientation="portrait" fo:margin-top="0mm" fo:margin-bottom="0mm"
 fo:margin-left="0mm" fo:margin-right="0mm"/></style:page-layout>
{dp}
</office:automatic-styles>
<office:master-styles>
<style:master-page style:name="Predeterminado" style:page-layout-name="PM1" draw:style-name="dp1"/>
</office:master-styles>
</office:document-styles>'''
        pages = "".join(
            f'<draw:page draw:name="{esc(n)}" draw:style-name="dp1" '
            f'draw:master-page-name="Predeterminado">{s}</draw:page>'
            for n, s in self.pages)
        content = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {NSDECL} office:version="1.3">
<office:font-face-decls>{faces}</office:font-face-decls>
<office:automatic-styles>{"".join(self.styles)}{dp}</office:automatic-styles>
<office:body><office:presentation>{pages}</office:presentation></office:body>
</office:document-content>'''
        meta = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta {NSDECL} xmlns:dc="http://purl.org/dc/elements/1.1/" office:version="1.3">
<office:meta><dc:title>Emergencias y desastres en comunidad · Escuela RFD 2025</dc:title>
<meta:generator xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0">Inkscape/ODF</meta:generator>
</office:meta></office:document-meta>'''
        manifest = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
<manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="application/vnd.oasis.opendocument.presentation"/>
<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
<manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
<manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
''' + "".join(f'<manifest:file-entry manifest:full-path="{r}" manifest:media-type="image/png"/>\n'
              for r in self.images) + "</manifest:manifest>"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(zipfile.ZipInfo("mimetype"),
                       "application/vnd.oasis.opendocument.presentation",
                       compress_type=zipfile.ZIP_STORED)
            z.writestr("META-INF/manifest.xml", manifest)
            z.writestr("content.xml", content)
            z.writestr("styles.xml", styles)
            z.writestr("meta.xml", meta)
            for ref, local in self.images.items():
                z.write(local, ref, compress_type=zipfile.ZIP_STORED)
