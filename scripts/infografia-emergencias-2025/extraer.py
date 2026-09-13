#!/usr/bin/env python3
"""Extrae el contenido exacto de la infografía SVG a un JSON."""
import json
import re
import sys
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
INK = "http://www.inkscape.org/namespaces/inkscape"
Q = lambda t: f"{{{SVG}}}{t}"


def lab(e):
    return e.get(f"{{{INK}}}label") or ""


def tag(e):
    return e.tag.split("}")[1]


def styleval(e, key):
    m = re.search(rf"{key}:([^;]+)", e.get("style") or "")
    return m.group(1).strip() if m else None


def find_lab(root, name, deep=True):
    it = root.iter() if deep else root
    return next((e for e in it if lab(e) == name), None)


def first_lab(root, *names):
    for n in names:
        e = find_lab(root, n)
        if e is not None:
            return e
    return None


def text_of(el):
    """Reconstruye el texto de un <text>, marcando con ** los tramos en negrita."""
    out = []
    for line in el.findall(Q("tspan")):
        chunks = []
        if line.text:
            chunks.append((line.text, False))
        for sub in line:
            bold = "font-weight:" in (sub.get("style") or "") and \
                   re.search(r"font-weight:(\d+)", sub.get("style") or "").group(1) != "400"
            if sub.text:
                chunks.append((sub.text, bold))
            if sub.tail:
                chunks.append((sub.tail, False))
        out.append(chunks)
    # unir líneas con espacio y fusionar tramos contiguos del mismo estilo
    flat = []
    for i, line in enumerate(out):
        if i:
            flat.append((" ", False))
        flat.extend(line)
    merged = []
    for t, b in flat:
        if merged and merged[-1][1] == b:
            merged[-1] = (merged[-1][0] + t, b)
        else:
            merged.append([t, b])
    s = "".join(f"**{t}**" if b else t for t, b in merged)
    return re.sub(r"\s+", " ", s.replace("** **", " ")).strip()


def icon_names(g):
    return [lab(e)[6:] for e in g.iter() if lab(e).startswith("icono ")]


def main(path, out):
    root = ET.parse(path).getroot()
    pages = []
    for layer in root.findall(Q("g")):
        head = find_lab(layer, "Cabecera")
        idea_g = find_lab(layer, "Idea fuerza")
        foot = find_lab(layer, "Pie")
        p = {
            "label": re.sub(r"^\d+ · ", "", lab(layer)),
            "dark": styleval(find_lab(head, "fondo cabecera"), "fill"),
            "stripe": styleval(find_lab(head, "franja"), "fill"),
            "tint": styleval(idea_g.find(Q("rect")), "fill"),
            "eyebrow": text_of(find_lab(head, "antetítulo")),
            "title": text_of(find_lab(head, "título")),
            "subtitle": text_of(find_lab(head, "subtítulo")),
            "idea": text_of(find_lab(idea_g, "idea fuerza")),
            "motto": text_of(find_lab(foot, "lema")),
            "credits": text_of(first_lab(foot, "créditos", "pie de página")),
            "strategies": [], "actions": [], "tools": [],
            "sec_icons": {},
        }
        for key, name in (("estrategias", "título estrategias"), ("acciones", "título acciones"),
                          ("herramientas", "título herramientas")):
            g = find_lab(layer, name)
            ic = icon_names(g)
            p["sec_icons"][key] = {"icon": ic[0] if ic else None,
                                   "label": text_of(g.findall(Q("text"))[0]),
                                   "sub": text_of(g.findall(Q("text"))[1])}
        for g in layer.iter(Q("g")):
            L = lab(g)
            if L.startswith("estrategia: "):
                p["strategies"].append({"t": text_of(find_lab(g, "título")),
                                        "d": text_of(find_lab(g, "descripción")),
                                        "i": (icon_names(g) or [None])[0]})
            elif re.match(r"^acción \d+$", L):
                txts = [e for e in g.findall(Q("text"))]
                p["actions"].append({"n": int(L.split()[1]), "a": text_of(txts[-1])})
            elif L.startswith("herramienta: "):
                p["tools"].append({"t": text_of(g.findall(Q("text"))[0]),
                                   "i": (icon_names(g) or [None])[0]})
        p["actions"].sort(key=lambda a: a["n"])
        pages.append(p)
    json.dump(pages, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(pages)} páginas")
    for p in pages:
        print(f"  {p['title']}: {len(p['strategies'])} estrategias, "
              f"{len(p['actions'])} acciones, {len(p['tools'])} herramientas")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
