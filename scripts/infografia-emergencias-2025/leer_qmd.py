#!/usr/bin/env python3
"""Lee el resumen (.qmd) y lo combina con el estilo de cada fase (colores, lema, etc.)."""
import json
import re
import sys

# El recuento de grupos no se muestra en la presentación (equivale a las estrellas).
RECUENTO = re.compile(r"\s*\((?:todos los grupos|\d+ de \d+ grupos)\)")
CORRECCIONES = {"algún area": "algún área"}


def cap(s):
    return s[:1].upper() + s[1:]


def normaliza(md):
    s = RECUENTO.sub("", md)
    for a, b in CORRECCIONES.items():
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s).strip()
    # la puntuación que cierra el arranque en negrita pasa dentro de la negrita,
    # y si falta (le sigue una frase nueva), se añade un punto
    m = re.match(r"^\*\*(.+?)\*\*(.*)$", s)
    if m:
        lead, rest = m.group(1).strip(), m.group(2)
        if rest[:1] in (".", ":") and lead[-1] not in ".:":
            lead, rest = lead + rest[0], rest[1:]
        elif lead[-1] not in ".:" and re.match(r"^\s+[A-ZÁÉÍÓÚÑ«¿¡]", rest):
            lead += "."
        s = f"**{lead}**{rest}"
    if s and s[-1] not in ".…!?»":
        s += "."
    return s


def lee(path):
    fases, fase, seccion, item = [], None, None, None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        m = re.match(r"^## \d+\.\s*(.+?):\s*(.+)$", line)
        if m:
            fase = {"title": m.group(1).upper(), "subtitle": cap(m.group(2).strip()),
                    "idea": "", "strategies": [], "actions": [], "tools": []}
            fases.append(fase)
            seccion = None
            continue
        if fase is None:
            continue
        m = re.match(r"^\*\*Idea central:\*\*\s*(.+)$", line)
        if m:
            fase["idea"] = cap(m.group(1).strip())
            continue
        m = re.match(r"^### (Estrategias|Acciones|Herramientas)\s*$", line)
        if m:
            seccion = {"Estrategias": "strategies", "Acciones": "actions",
                       "Herramientas": "tools"}[m.group(1)]
            continue
        if seccion is None:
            continue
        if line.startswith("- "):
            item = [line[2:].strip()]
            fase[seccion].append(item)
        elif re.match(r"^\s+- ", line) and item is not None:
            item.append(line.strip()[2:].strip())      # subviñeta: se une al párrafo
    for f in fases:
        for k in ("strategies", "actions", "tools"):
            f[k] = [normaliza(" ".join(it)) for it in f[k]]
    return fases


def main(qmd, estilo, out):
    fases = lee(qmd)
    base = json.load(open(estilo, encoding="utf-8"))
    assert len(fases) == len(base) == 3, (len(fases), len(base))
    pages = []
    for f, b in zip(fases, base):
        p = {k: b[k] for k in ("label", "dark", "tint", "eyebrow", "motto", "credits", "sec_icons")}
        p.update(f)
        pages.append(p)
    json.dump(pages, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for p in pages:
        print(f"  {p['title']}: {len(p['strategies'])} estrategias, {len(p['actions'])} acciones, "
              f"{len(p['tools'])} herramientas")


if __name__ == "__main__":
    main(*sys.argv[1:4])
