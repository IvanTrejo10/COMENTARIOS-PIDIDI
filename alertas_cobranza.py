# -*- coding: utf-8 -*-
"""
ALERTAS DIARIAS DE RECUPERACIÓN (México + LATAM)
================================================
Lee los PDF "Avance Cobranza y Entregado ... México / LATAM" (exportados de Power BI)
y arma, por cada país, lo que se manda por WhatsApp:

    1) la imagen con los recuadros Bottom / Top
    2) el mensaje ("Presenta una variación negativa en recuperación de ...")

Uso
---
    streamlit run app.py                            (página web: se suben los PDF y se copian los mensajes)
    python alertas_cobranza.py  "ruta\\México.pdf"  "ruta\\LATAM.pdf"
    python alertas_cobranza.py                      (toma los PDF más recientes de carpeta_pdfs)

    Opciones:  --salida CARPETA   --no-abrir   --config RUTA

Salida (carpeta salida\\AAAA-MM-DD del corte)
    alertas.html     página para revisar y copiar imagen / texto de cada país
    mensajes.txt     todos los mensajes juntos
    N_Pais.png/.txt  imagen y mensaje de cada país
    alertas.json     lo mismo en formato máquina (para el envío automático)

Requiere PyMuPDF; si falta, el script lo instala solo la primera vez (pip install "pymupdf<2").
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import re
import sys
import unicodedata
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _cargar_pymupdf():
    """Importa PyMuPDF; si falta, lo instala con el mismo Python que está corriendo este script."""
    def _intentar():
        try:
            import pymupdf as m
            return m
        except ImportError:
            pass
        try:  # versiones viejas de PyMuPDF
            import fitz as m  # type: ignore
            return m if hasattr(m, "open") and hasattr(m, "Rect") else None
        except ImportError:
            return None

    mod = _intentar()
    if mod is not None:
        return mod

    import importlib
    import subprocess
    print("Falta la librería PyMuPDF; la instalo (solo pasa la primera vez)...", flush=True)
    try:
        ok = subprocess.call([sys.executable, "-m", "pip", "install", "pymupdf>=1.24,<2"]) == 0
    except OSError:
        ok = False
    if ok:
        importlib.invalidate_caches()
        mod = _intentar()
        if mod is not None:
            print("PyMuPDF instalado.\n", flush=True)
            return mod
    sys.exit("\nNo se pudo instalar PyMuPDF con este Python:\n"
             f"    {sys.executable}\n"
             "Corre esto y revisa el error que marque:\n"
             f'    "{sys.executable}" -m pip install "pymupdf<2"')


pymupdf = _cargar_pymupdf()

AQUI = Path(__file__).resolve().parent

# ════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN POR DEFECTO  (lo que pongas en config_alertas.json la reemplaza)
# ════════════════════════════════════════════════════════════════════════════
CONFIG_DEFECTO = {
    # Carpeta donde caen los PDF del día. Vacío = subcarpeta "pdfs" junto a este script o, si no
    # existe, la misma carpeta del script. (La página web no la usa: ahí se suben los PDF.)
    "carpeta_pdfs": "",
    "patron_pdf": "Avance*Cobranza*.pdf",
    # Vacío = subcarpeta "salida" junto a este script.
    "carpeta_salida": "",
    "abrir_al_terminar": True,
    # Cuántas zonas / sucursales se mencionan.
    "top_n": 3,
    # Si |variación| / recuperación semana anterior es menor a este %, se dice "ligeramente".
    # (El Salvador -212 = 0.04 % sí lo lleva; México -163,086 = 0.19 % ya no.)
    "umbral_ligera_pct": 0.1,
    # Países con todo en 0 (ej. Nicaragua) no generan mensaje.
    "omitir_sin_movimiento": True,
    "paises_excluidos": [],
    # True = "Veracruz Presico P-PC" -> "Veracruz Presico" (así van en los mensajes)
    "quitar_claves_sucursal": True,
    "dpi_imagen": 150,
    "orden": ["Guatemala", "El Salvador", "Honduras", "Nicaragua", "Perú", "Colombia", "México"],
    "paises": {
        "México": {"bandera": "🇲🇽", "moneda": "$"},
        "Guatemala": {"bandera": "🇬🇹", "moneda": "Q"},
        "El Salvador": {"bandera": "🇸🇻", "moneda": "$"},
        "Honduras": {"bandera": "🇭🇳", "moneda": "L"},
        "Nicaragua": {"bandera": "🇳🇮", "moneda": "C$"},
        "Perú": {"bandera": "🇵🇪", "moneda": "S/"},
        "Colombia": {"bandera": "🇨🇴", "moneda": "$"},
    },
    # El tablero trae los nombres sin acento; aquí se corrigen palabra por palabra.
    "acentos": {
        "Pacifico": "Pacífico", "Peninsula": "Península",
        "Tonala": "Tonalá", "Andres": "Andrés", "Martinez": "Martínez", "Comitan": "Comitán",
        "Cristobal": "Cristóbal", "Escarcega": "Escárcega", "Culiacan": "Culiacán",
        "Constitucion": "Constitución", "Juarez": "Juárez", "Jose": "José",
        "Siquinala": "Siquinalá", "Poptun": "Poptún", "Ixcan": "Ixcán", "Malacatan": "Malacatán",
        "Sayaxche": "Sayaxché", "Solola": "Sololá", "Tecun": "Tecún", "Uman": "Umán",
        "Usulutan": "Usulután", "Ahuachapan": "Ahuachapán", "Cuscatlan": "Cuscatlán",
        "Metapan": "Metapán", "Union": "Unión",
        "Intibuca": "Intibucá", "Barbara": "Bárbara", "Leon": "León",
        "Huanuco": "Huánuco", "Huaycan": "Huaycán", "Camana": "Camaná", "Jaen": "Jaén",
        "Cajica": "Cajicá", "Ibague": "Ibagué",
    },
}

# ════════════════════════════════════════════════════════════════════════════
#  REDACCIÓN  (aquí se cambia el texto de los mensajes)
# ════════════════════════════════════════════════════════════════════════════
FRASES = {
    "apertura": "Presenta una variación {tipo} en recuperación de {monto} respecto a la semana anterior.",
    "sin_variacion": "No presenta variación en recuperación respecto a la semana anterior.",
    # zonas: dos o más a la baja
    "zonas": "Las principales disminuciones se concentran en las zonas {lista}.",
    "zonas_total_positivo": "Sin embargo, las principales disminuciones se concentran en las zonas {lista}.",
    # zonas: solo una a la baja
    "zona_unica": "La disminución se concentra en la zona {zona} ({monto})",
    "zona_unica_y_un_incremento": ", mientras que {zona} registra un incremento de {monto}",
    "zona_unica_y_varios_incrementos": ", mientras que el mayor incremento se registra en {zona} ({monto})",
    "zona_unica_total_positivo": "Sin embargo, la zona {zona} registra una disminución de {monto}.",
    # sucursales
    "sucursales": "A nivel sucursal, las mayores caídas se registran en {lista}.",
    "sucursal": "A nivel sucursal, la mayor caída se registra en {lista}.",
    "sucursales_zona_unica": "A nivel sucursal, las principales caídas se presentan en {lista}.",
    "sucursal_zona_unica": "A nivel sucursal, la principal caída se presenta en {lista}.",
    "sucursales_total_positivo": "A nivel sucursal persisten disminuciones en {lista}.",
    "sucursal_total_positivo": "A nivel sucursal persiste una disminución en {lista}.",
}


# ════════════════════════════════════════════════════════════════════════════
#  UTILIDADES DE TEXTO
# ════════════════════════════════════════════════════════════════════════════
def limpiar(txt: str) -> str:
    """Quita los glifos de iconos de Power BI (flechas de orden) y caracteres de control."""
    return "".join(
        c for c in txt if not (0xE000 <= ord(c) <= 0xF8FF) and unicodedata.category(c)[0] != "C"
    ).strip()


def sin_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()


def a_numero(tok: str) -> Optional[float]:
    """'-96,146' -> -96146.0 ; '(1,234)' -> -1234.0 ; '42.22%' o texto -> None"""
    t = tok.strip()
    if not t or t.endswith("%"):
        return None
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1]
    if t[:1] in "-−–":
        neg, t = True, t[1:]
    t = t.lstrip("$")
    if not re.fullmatch(r"\d[\d.,]*", t):
        return None
    if "," in t and "." in t:  # el último separador es el decimal
        i = max(t.rfind(","), t.rfind("."))
        val = float(re.sub(r"[.,]", "", t[:i]) + "." + t[i + 1:])
    elif "," in t or "." in t:
        sep = "," if "," in t else "."
        partes = t.split(sep)
        if 1 <= len(partes[0]) <= 3 and all(len(p) == 3 for p in partes[1:]):
            val = float("".join(partes))  # separador de miles
        elif len(partes) == 2:
            val = float(partes[0] + "." + partes[1])  # decimal
        else:
            return None
    else:
        val = float(t)
    return -val if neg else val


def lista_es(items: list[str]) -> str:
    """['A','B','C'] -> 'A, B y C'  (usa 'e' si lo que sigue empieza con sonido i)"""
    if len(items) == 1:
        return items[0]
    conj = "e" if re.match(r"h?i(?![aeou])", sin_acentos(items[-1])) else "y"
    return ", ".join(items[:-1]) + f" {conj} " + items[-1]


def nombre_archivo(s: str) -> str:
    base = unicodedata.normalize("NFD", s)
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")


# ════════════════════════════════════════════════════════════════════════════
#  LECTURA DEL PDF
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class Palabra:
    x0: float
    y0: float
    x1: float
    y1: float
    txt: str

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Titulo:
    tipo: str  # zona | sucursal | marca | territorio | subdireccion | faltas
    x0: float
    y0: float
    x1: float
    y1: float
    seccion: str = ""  # resumen | bottom | top


@dataclass
class Fila:
    nombre: str
    rec: float  # Recuperación
    ant: float  # Recuperación sem ant
    var: float  # Var Rec Sem Ant


@dataclass
class Pais:
    nombre: str
    archivo: str
    pagina: int  # base 1
    corte: Optional[dt.date]
    total: Optional[Fila] = None
    zonas: list = field(default_factory=list)       # Bottom + Top, sin repetir
    sucursales: list = field(default_factory=list)  # Bottom + Top, sin repetir
    recorte: object = None                          # rectángulo Bottom+Top para la imagen
    avisos: list = field(default_factory=list)


TIPOS_TABLA = {"zona", "sucursal", "marca", "territorio", "subdireccion"}


def _palabras(page) -> list[Palabra]:
    out = []
    for x0, y0, x1, y1, txt, *_ in page.get_text("words"):
        t = limpiar(txt)
        if t:
            out.append(Palabra(x0, y0, x1, y1, t))
    return out


def _marcos(page) -> list:
    """Rectángulos grandes con borde dibujados en la página (los marcos rojo y azul)."""
    return [d["rect"] for d in page.get_drawings()
            if d.get("color") and d["rect"].width > page.rect.width * 0.5 and d["rect"].height > 80]


def _secciones(page, pals: list[Palabra], tits: list[Titulo]):
    """Ubica Bottom y Top. Devuelve (rect_bottom, rect_top, exacto) o None si la página no los trae.

    Bottom y Top son las dos filas de títulos que traen 'Recuperación Sucursal' (la de más arriba es
    Bottom; las tablas de resumen no la traen). El marco de cada una es el rectángulo dibujado que la
    contiene; si el tablero ya no trae marcos, se usa una división aproximada.
    """
    grupos: list[list[Titulo]] = []
    for t in sorted((t for t in tits if t.tipo in ("faltas", "zona", "sucursal")), key=lambda t: t.y0):
        if grupos and t.y0 - grupos[-1][0].y0 <= 12:
            grupos[-1].append(t)
        else:
            grupos.append([t])
    grupos = [g for g in grupos if any(t.tipo == "sucursal" for t in g)]
    if len(grupos) < 2:
        return None
    g_bottom, g_top = grupos[0], grupos[1]
    for t in tits:
        t.seccion = "bottom" if t in g_bottom else "top" if t in g_top else "resumen"

    marcos = _marcos(page)

    def marco_de(g):
        dentro = [r for r in marcos
                  if all(r.x0 <= t.x0 and t.x1 <= r.x1 and r.y0 <= t.y0 and t.y1 <= r.y1 for t in g)]
        return min(dentro, key=lambda r: r.get_area()) if dentro else None

    r_bottom, r_top = marco_de(g_bottom), marco_de(g_top)
    if r_bottom is not None and r_top is not None and r_bottom != r_top:
        return r_bottom, r_top, True

    y_b, y_t = min(t.y0 for t in g_bottom), min(t.y0 for t in g_top)
    fin = max((p.y1 for p in pals if p.cy > y_t), default=y_t + 200)
    x0, x1 = page.rect.x0 + 40, page.rect.x1 - 40
    return pymupdf.Rect(x0, y_b - 12, x1, y_t - 14), pymupdf.Rect(x0, y_t - 11, x1, fin + 12), False


def _titulos(pals: list[Palabra]) -> list[Titulo]:
    """Títulos 'Recuperación Zona', 'Recuperación Sucursal', ... y 'Faltas'."""
    tits = []
    for a in pals:
        if sin_acentos(a.txt) == "recuperacion":
            alto = a.y1 - a.y0
            for b in pals:
                if (b is not a and abs(b.y0 - a.y0) < 2.5 and 0 <= b.x0 - a.x1 < 0.8 * alto
                        and sin_acentos(b.txt) in TIPOS_TABLA):
                    tits.append(Titulo(sin_acentos(b.txt), a.x0, a.y0, b.x1, max(a.y1, b.y1)))
        elif sin_acentos(a.txt) == "faltas":  # solo sirve para saber dónde acaba la tabla de al lado
            tits.append(Titulo("faltas", a.x0, a.y0, a.x1, a.y1))
    return tits


def _filas_tabla(pals: list[Palabra], t: Titulo, vecinos: list[Titulo], x_max: float, y_max: float):
    """Filas (nombre, rec, ant, var) de la tabla que está debajo del título t."""
    a_la_derecha = [v.x0 for v in vecinos if v is not t and v.x0 > t.x0 + 20]
    x_izq = t.x0 - 12
    x_der = (min(a_la_derecha) - 12) if a_la_derecha else x_max
    dentro = [p for p in pals if x_izq <= p.cx < x_der and t.y1 - 1 < p.cy <= y_max]
    dentro.sort(key=lambda p: (p.cy, p.x0))

    renglones: list[list[Palabra]] = []
    for p in dentro:
        if renglones and abs(p.cy - renglones[-1][0].cy) <= 3.0:
            renglones[-1].append(p)
        else:
            renglones.append([p])

    filas, incompletas = [], []
    for r in renglones:
        r.sort(key=lambda p: p.x0)
        nums = [a_numero(p.txt) for p in r]
        if len(r) >= 4 and all(n is not None for n in nums[-3:]):
            nombre = " ".join(p.txt for p in r[:-3] if not p.txt.endswith("%")).strip()
            if nombre:
                filas.append(Fila(nombre, nums[-3], nums[-2], nums[-1]))
        elif len(r) >= 3 and nums[-1] is not None and nums[-2] is not None and a_numero(r[0].txt) is None:
            incompletas.append(" ".join(p.txt for p in r))
    return filas, incompletas


def leer_pdf(ruta: Path) -> list[Pais]:
    """Devuelve un Pais por cada página de 'Recuperación' (las de Trámites/Efectividad se saltan)."""
    paises = []
    doc = pymupdf.open(str(ruta))
    for i, page in enumerate(doc):
        pals = _palabras(page)
        tits = _titulos(pals)
        secciones = _secciones(page, pals, tits)
        if secciones is None:
            continue  # página de Trámites / Efectividad
        rojo, azul, exacto = secciones

        avisos = []
        if not exacto:
            avisos.append("No encontré los marcos Bottom/Top; la imagen usa un recorte aproximado.")

        # ── nombre del país (texto más grande arriba a la izquierda) y fecha de corte
        nombre, tam = "", 0.0
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for s in ln["spans"]:
                    txt = limpiar(s["text"])
                    if (txt and s["size"] >= 20 and s["size"] > tam and s["bbox"][3] < 110
                            and s["bbox"][0] < page.rect.width * 0.5
                            and not sin_acentos(txt).startswith("corte")):
                        nombre, tam = txt, s["size"]
        m = re.search(r"Corte\s+(\d{1,2})/(\d{1,2})/(\d{4})", page.get_text())
        corte = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None

        pais = Pais(nombre or f"Página {i + 1}", ruta.name, i + 1, corte, avisos=avisos)
        limites = {"resumen": (page.rect.x1, rojo.y0), "bottom": (rojo.x1, rojo.y1), "top": (azul.x1, azul.y1)}

        totales = []
        for sec in ("resumen", "bottom", "top"):
            de_sec = [t for t in tits if t.seccion == sec]
            for t in de_sec:
                if t.tipo == "faltas":
                    continue
                x_max, y_max = limites[sec]
                filas, incompletas = _filas_tabla(pals, t, de_sec, x_max, y_max)
                for inc in incompletas:
                    pais.avisos.append(f"Fila incompleta en 'Recuperación {t.tipo}' ({sec}): {inc}")
                if sec == "resumen":
                    totales += [(t.tipo, f) for f in filas if sin_acentos(f.nombre) == "total"]
                    continue
                destino = pais.zonas if t.tipo == "zona" else pais.sucursales if t.tipo == "sucursal" else None
                if destino is None:
                    continue
                ya = {sin_acentos(f.nombre) for f in destino}
                for f in filas:
                    if sin_acentos(f.nombre) == "total" or sin_acentos(f.nombre) in ya:
                        continue
                    if abs((f.rec - f.ant) - f.var) > 2:
                        pais.avisos.append(
                            f"Revisar '{f.nombre}': {f.rec:,.0f} - {f.ant:,.0f} no da {f.var:,.0f}")
                    destino.append(f)
                    ya.add(sin_acentos(f.nombre))

        if totales:
            # La variación del mensaje es el Total de "Recuperación Territorio"; si el país no trae
            # esa tabla (El Salvador, Honduras, Perú...), el Total de la primera que haya.
            totales.sort(key=lambda tf: tf[0] != "territorio")
            pais.total = totales[0][1]
            if any(abs(f.var - pais.total.var) > 1 for _, f in totales[1:]):
                pais.avisos.append("Los totales de las tablas de arriba no coinciden entre sí.")
        else:
            pais.avisos.append("No encontré la fila Total de recuperación.")

        # Recorte al ras de los marcos (el borde se dibuja hacia adentro), para no agarrar
        # pedazos de las tablas de arriba.
        pais.recorte = (min(rojo.x0, azul.x0), min(rojo.y0, azul.y0),
                        max(rojo.x1, azul.x1), max(rojo.y1, azul.y1))
        paises.append(pais)
    doc.close()
    return paises


def guardar_imagen(ruta_pdf: Path, pais: Pais, destino: Path, dpi: int) -> None:
    doc = pymupdf.open(str(ruta_pdf))
    page = doc[pais.pagina - 1]
    clip = pymupdf.Rect(*pais.recorte) & page.rect
    page.get_pixmap(clip=clip, dpi=dpi, alpha=False).save(str(destino))
    doc.close()


# ════════════════════════════════════════════════════════════════════════════
#  REDACCIÓN DEL MENSAJE
# ════════════════════════════════════════════════════════════════════════════
def redactar(pais: Pais, cfg: dict) -> tuple[Optional[str], str]:
    """Devuelve (mensaje, motivo). Si mensaje es None, motivo dice por qué se omitió."""
    if sin_acentos(pais.nombre) in {sin_acentos(x) for x in cfg["paises_excluidos"]}:
        return None, "excluido en la configuración"
    if pais.total is None:
        return None, "no se pudo leer el total de recuperación"

    info = next((v for k, v in cfg["paises"].items() if sin_acentos(k) == sin_acentos(pais.nombre)), None)
    if info is None:
        info = {"bandera": "", "moneda": "$"}
        pais.avisos.append(f"'{pais.nombre}' no está en la configuración: sin bandera y con moneda $.")
    moneda, top_n = info["moneda"], int(cfg["top_n"])

    def monto(v: float) -> str:
        n = int(round(abs(v)))
        signo = "-" if v < 0 and n else "+" if v > 0 and n else ""
        return f"{signo}{moneda}{n:,}"

    def nom(f: Fila) -> str:
        n = f.nombre
        if cfg["quitar_claves_sucursal"]:
            n = re.sub(r"\s+[A-Z]{1,2}(?:-[A-Z]{1,2})+$", "", n)
        return " ".join(cfg["acentos"].get(w, w) for w in n.split())

    total = int(round(pais.total.var))
    z_neg = sorted((z for z in pais.zonas if round(z.var) < 0), key=lambda f: f.var)
    z_pos = sorted((z for z in pais.zonas if round(z.var) > 0), key=lambda f: -f.var)
    s_neg = sorted((s for s in pais.sucursales if round(s.var) < 0), key=lambda f: f.var)

    sin_mov = (round(pais.total.rec) == 0 and round(pais.total.ant) == 0
               and not z_neg and not z_pos and not s_neg)
    if sin_mov and cfg["omitir_sin_movimiento"]:
        return None, "sin movimiento, todo en 0"

    # 1) apertura
    if total == 0:
        partes = [FRASES["sin_variacion"]]
    else:
        pct = abs(pais.total.var) / abs(pais.total.ant) * 100 if pais.total.ant else None
        ligera = pct is not None and pct < float(cfg["umbral_ligera_pct"])
        tipo = ("ligeramente " if ligera else "") + ("negativa" if total < 0 else "positiva")
        partes = [FRASES["apertura"].format(tipo=tipo, monto=monto(pais.total.var))]

    # 2) zonas (solo si el país tiene más de una zona)
    forma_zona = ""
    if len(pais.zonas) >= 2 and z_neg:
        if len(z_neg) >= 2:
            lista = lista_es([f"{nom(z)} ({monto(z.var)})" for z in z_neg[:top_n]])
            partes.append(FRASES["zonas_total_positivo" if total >= 0 else "zonas"].format(lista=lista))
            forma_zona = "varias"
        elif total >= 0:
            partes.append(FRASES["zona_unica_total_positivo"].format(zona=nom(z_neg[0]), monto=monto(z_neg[0].var)))
            forma_zona = "varias"
        else:
            txt = FRASES["zona_unica"].format(zona=nom(z_neg[0]), monto=monto(z_neg[0].var))
            if len(z_pos) == 1:
                txt += FRASES["zona_unica_y_un_incremento"].format(zona=nom(z_pos[0]), monto=monto(z_pos[0].var))
            elif len(z_pos) > 1:
                txt += FRASES["zona_unica_y_varios_incrementos"].format(zona=nom(z_pos[0]), monto=monto(z_pos[0].var))
            partes.append(txt + ".")
            forma_zona = "unica"

    # 3) sucursales
    if s_neg:
        items = [f"{nom(s)} ({monto(s.var)})" for s in s_neg[:top_n]]
        plural = "es" if len(items) > 1 else ""
        if not forma_zona and total >= 0:
            clave = f"sucursal{plural}_total_positivo"
        elif forma_zona == "unica":
            clave = f"sucursal{plural}_zona_unica"
        else:
            clave = f"sucursal{plural}"
        partes.append(FRASES[clave].format(lista=lista_es(items)))

    encabezado = f"{pais.nombre} {info['bandera']}".strip()
    return encabezado + "\n" + " ".join(partes), ""


# ════════════════════════════════════════════════════════════════════════════
#  PÁGINA DE REVISIÓN
# ════════════════════════════════════════════════════════════════════════════
PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alertas de recuperación · Corte __CORTE__</title>
<style>
  :root { --fondo:#f3f5f8; --tarjeta:#fff; --texto:#15202b; --tenue:#5b6875; --linea:#dde3ea;
          --acento:#0b3fb3; --ok:#12805c; --aviso:#8a5a00; --aviso-fondo:#fff6dd; }
  @media (prefers-color-scheme: dark) {
    :root { --fondo:#11161c; --tarjeta:#1a2129; --texto:#e8edf2; --tenue:#9aa7b4; --linea:#2c3742;
            --acento:#7da6ff; --ok:#4fd1a1; --aviso:#ffd27a; --aviso-fondo:#3a2f12; } }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--fondo); color:var(--texto);
         font: 15px/1.5 "Segoe UI", system-ui, -apple-system, sans-serif; }
  header { padding: 26px 32px 6px; max-width: 1180px; margin: 0 auto; }
  h1 { margin: 0; font-size: 22px; font-weight: 650; letter-spacing: -.01em; }
  header p { margin: 4px 0 0; color: var(--tenue); font-size: 13.5px; }
  main { max-width: 1180px; margin: 0 auto; padding: 14px 32px 48px; display: grid; gap: 16px; }
  .nota { background: var(--aviso-fondo); color: var(--aviso); border-radius: 10px; padding: 10px 14px; font-size: 13.5px; }
  .nota ul { margin: 4px 0 0; padding-left: 18px; }
  article { background: var(--tarjeta); border: 1px solid var(--linea); border-radius: 14px;
            display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); overflow: hidden; }
  @media (max-width: 860px) { article { grid-template-columns: 1fr; } }
  .img { background: #fff; border-right: 1px solid var(--linea); display: flex; align-items: center; }
  .img img { width: 100%; height: auto; display: block; }
  .txt { padding: 16px 18px; display: flex; flex-direction: column; gap: 12px; }
  .txt pre { margin: 0; white-space: pre-wrap; word-wrap: break-word; font: inherit; flex: 1; }
  .txt pre::first-line { font-weight: 650; font-size: 16px; }
  .bot { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  button { font: inherit; font-size: 13.5px; font-weight: 600; padding: 8px 14px; border-radius: 9px; cursor: pointer;
           border: 1px solid var(--acento); background: var(--acento); color: #fff; }
  button.sec { background: transparent; color: var(--acento); }
  @media (prefers-color-scheme: dark) { button { color: #0d1117; } button.sec { color: var(--acento); } }
  button.listo { background: var(--ok); border-color: var(--ok); color: #fff; }
  .pista { font-size: 12.5px; color: var(--tenue); }
</style></head><body>
<header>
  <h1>Alertas de recuperación · Corte __CORTE__</h1>
  <p>__RESUMEN__ · Para WhatsApp: <b>Copiar imagen</b> → pegar en el chat → <b>Copiar texto</b> → pegar como comentario → enviar.</p>
</header>
<main>
__NOTAS__
__TARJETAS__
</main>
<script>
function marcar(btn, texto) {
  const antes = btn.dataset.txt || (btn.dataset.txt = btn.textContent);
  btn.textContent = texto; btn.classList.add('listo');
  setTimeout(() => { btn.textContent = antes; btn.classList.remove('listo'); }, 1600);
}
async function copiarTexto(id, btn) {
  const t = document.getElementById(id).textContent;
  try { await navigator.clipboard.writeText(t); }
  catch (e) {
    const a = document.createElement('textarea'); a.value = t; document.body.appendChild(a);
    a.select(); document.execCommand('copy'); a.remove();
  }
  marcar(btn, 'Texto copiado');
}
async function copiarImagen(id, btn) {
  try {
    const b64 = document.getElementById(id).src.split(',')[1];
    const bin = atob(b64), bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': new Blob([bytes], { type: 'image/png' }) })]);
    marcar(btn, 'Imagen copiada');
  } catch (e) {
    btn.parentElement.querySelector('.pista').textContent =
      'No se pudo copiar aquí: clic derecho sobre la imagen → Copiar imagen (o usa el .png de la carpeta).';
  }
}
</script>
</body></html>
"""


def armar_pagina(alertas: list[dict], omitidos: list[str], avisos: list[str], corte_txt: str, fuentes: list[str]) -> str:
    tarjetas = []
    for n, a in enumerate(alertas, 1):
        b64 = base64.b64encode(Path(a["imagen_ruta"]).read_bytes()).decode("ascii")
        tarjetas.append(
            f'<article><div class="img"><img id="img{n}" alt="Bottom y Top de {html.escape(a["pais"])}" '
            f'src="data:image/png;base64,{b64}"></div>'
            f'<div class="txt"><pre id="txt{n}">{html.escape(a["mensaje"])}</pre>'
            f'<div class="bot"><button onclick="copiarImagen(\'img{n}\', this)">Copiar imagen</button>'
            f'<button class="sec" onclick="copiarTexto(\'txt{n}\', this)">Copiar texto</button>'
            f'<span class="pista"></span></div></div></article>'
        )
    notas = ""
    if omitidos or avisos:
        li = "".join(f"<li>{html.escape(x)}</li>" for x in omitidos + avisos)
        notas = f'<div class="nota"><b>Notas de esta corrida</b><ul>{li}</ul></div>'
    resumen = f"{len(alertas)} mensajes · " + " + ".join(html.escape(f) for f in fuentes)
    return (PAGINA.replace("__CORTE__", html.escape(corte_txt)).replace("__RESUMEN__", resumen)
            .replace("__NOTAS__", notas).replace("__TARJETAS__", "\n".join(tarjetas)))


# ════════════════════════════════════════════════════════════════════════════
#  PROCESO COMPLETO  (lo usan la línea de comandos y la página de Streamlit)
# ════════════════════════════════════════════════════════════════════════════
class ErrorAlertas(Exception):
    """Problema que se le explica al usuario tal cual: archivo equivocado, configuración mal escrita..."""


def cargar_config(ruta: Optional[Path] = None) -> dict:
    cfg = json.loads(json.dumps(CONFIG_DEFECTO))
    ruta = ruta or (AQUI / "config_alertas.json")
    if ruta.exists():
        try:
            propio = json.loads(ruta.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            raise ErrorAlertas(
                f"{ruta.name} tiene un error de formato ({e}).\n"
                "Ojo: en las rutas de Windows usa doble diagonal (C:\\\\Users\\\\...) o diagonal normal (C:/Users/...).")
        for k, v in propio.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def buscar_pdfs(cfg: dict) -> list[Path]:
    """Los PDF del corte más reciente.

    Sin carpeta_pdfs en la configuración se buscan en la subcarpeta "pdfs" (si existe) o, si no,
    en la misma carpeta donde está este script.
    """
    if cfg["carpeta_pdfs"]:
        carpeta = Path(cfg["carpeta_pdfs"])
    else:
        carpeta = AQUI / "pdfs" if (AQUI / "pdfs").is_dir() else AQUI
    if not carpeta.is_dir():
        raise ErrorAlertas(f"No existe la carpeta de PDF: {carpeta}\n"
                           "Corrige carpeta_pdfs en config_alertas.json o arrastra los PDF sobre generar_alertas.bat.")
    candidatos = [p for p in carpeta.glob(cfg["patron_pdf"]) if p.is_file()]
    if not candidatos:
        raise ErrorAlertas(f"No hay PDF '{cfg['patron_pdf']}' en {carpeta}\n"
                           "Pon ahí los PDF del día o arrástralos sobre generar_alertas.bat.")

    def fecha(p: Path) -> dt.date:
        m = re.search(r"Cierre[ _-]*(\d{2})(\d{2})(\d{2})", p.name, re.I)
        if m:
            try:
                return dt.date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                pass
        return dt.date.fromtimestamp(p.stat().st_mtime)

    ultima = max(fecha(p) for p in candidatos)
    return sorted(p for p in candidatos if fecha(p) == ultima)


def procesar(rutas: list, cfg: dict, salida: Path, por_fecha: bool = True, con_pagina: bool = True) -> dict:
    """Lee los PDF y deja en la carpeta de salida la imagen y el mensaje de cada país.

    por_fecha   True = guarda en salida/AAAA-MM-DD (fecha del corte); False = directo en salida
    con_pagina  True = además arma alertas.html

    Devuelve un dict con: corte_txt, carpeta, pagina, lecturas [(archivo, páginas)], alertas, omitidos, avisos.
    Cada alerta trae: orden, pais, corte, mensaje, imagen, imagen_ruta, archivo, pagina, variacion_total.
    """
    rutas = [Path(r) for r in rutas]
    faltan = [str(p) for p in rutas if not p.is_file()]
    if faltan:
        raise ErrorAlertas("No encuentro: " + ", ".join(faltan))

    # ── leer
    paises, lecturas = [], []
    for ruta in rutas:
        try:
            encontrados = leer_pdf(ruta)
        except Exception as e:  # archivo dañado o que no es un PDF
            raise ErrorAlertas(f"No pude leer {ruta.name}: {e}")
        lecturas.append((ruta.name, len(encontrados)))
        paises += [(ruta, p) for p in encontrados]
    if not paises:
        raise ErrorAlertas("Ningún PDF trae páginas de Recuperación (Bottom/Top). ¿Son los archivos correctos?")

    orden = [sin_acentos(x) for x in cfg["orden"]]
    paises.sort(key=lambda rp: orden.index(sin_acentos(rp[1].nombre)) if sin_acentos(rp[1].nombre) in orden else 999)

    cortes = sorted({p.corte for _, p in paises if p.corte})
    corte = cortes[-1] if cortes else dt.date.today()
    corte_txt = corte.strftime("%d/%m/%Y")
    salida = Path(salida) / corte.isoformat() if por_fecha else Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    for viejo in salida.iterdir():  # limpia lo de una corrida anterior del mismo corte
        if viejo.is_file() and re.fullmatch(r"\d+_.+\.(png|txt)", viejo.name):
            viejo.unlink()

    # ── redactar + imágenes
    alertas, omitidos, avisos = [], [], []
    if len(cortes) > 1:
        avisos.append("Los PDF traen fechas de corte distintas: " + ", ".join(c.strftime("%d/%m/%Y") for c in cortes))
    for ruta, p in paises:
        mensaje, motivo = redactar(p, cfg)
        avisos += [f"{p.nombre}: {a}" for a in p.avisos]
        if mensaje is None:
            omitidos.append(f"{p.nombre}: no se generó mensaje ({motivo}).")
            continue
        n = len(alertas) + 1
        raiz = f"{n}_{nombre_archivo(p.nombre)}"
        img = salida / f"{raiz}.png"
        guardar_imagen(ruta, p, img, int(cfg["dpi_imagen"]))
        (salida / f"{raiz}.txt").write_text(mensaje, encoding="utf-8")
        alertas.append({"orden": n, "pais": p.nombre,
                        "corte": p.corte.strftime("%d/%m/%Y") if p.corte else corte_txt,
                        "mensaje": mensaje, "imagen": img.name, "imagen_ruta": str(img),
                        "archivo": p.archivo, "pagina": p.pagina,
                        "variacion_total": int(round(p.total.var))})

    (salida / "mensajes.txt").write_text("\n\n".join(a["mensaje"] for a in alertas) + "\n", encoding="utf-8")
    pagina = None
    if con_pagina:
        pagina = salida / "alertas.html"
        pagina.write_text(armar_pagina(alertas, omitidos, avisos, corte_txt, [r.name for r in rutas]), encoding="utf-8")
    (salida / "alertas.json").write_text(json.dumps(
        {"corte": corte_txt, "generado": dt.datetime.now().isoformat(timespec="seconds"),
         "alertas": [{k: v for k, v in a.items() if k != "imagen_ruta"} for a in alertas],
         "omitidos": omitidos, "avisos": avisos}, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"corte_txt": corte_txt, "carpeta": salida, "pagina": pagina, "lecturas": lecturas,
            "alertas": alertas, "omitidos": omitidos, "avisos": avisos}


# ════════════════════════════════════════════════════════════════════════════
#  LÍNEA DE COMANDOS
# ════════════════════════════════════════════════════════════════════════════
def main() -> int:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="Genera las alertas diarias de recuperación a partir de los PDF.")
    ap.add_argument("pdfs", nargs="*", help="PDF de México y/o LATAM (si no se dan, se buscan en carpeta_pdfs)")
    ap.add_argument("--salida", help="carpeta de salida")
    ap.add_argument("--config", help="ruta de config_alertas.json")
    ap.add_argument("--no-abrir", action="store_true", help="no abrir la página al terminar")
    args = ap.parse_args()

    try:
        cfg = cargar_config(Path(args.config) if args.config else None)
        rutas = [Path(p) for p in args.pdfs] if args.pdfs else buscar_pdfs(cfg)
        base = Path(args.salida) if args.salida else (Path(cfg["carpeta_salida"]) if cfg["carpeta_salida"] else AQUI / "salida")
        res = procesar(rutas, cfg, base)
    except ErrorAlertas as e:
        sys.exit(str(e))

    for nombre, n in res["lecturas"]:
        print(f"{nombre}: {n} página(s) de recuperación")
    for a in res["alertas"]:
        print(f"  + {a['pais']}: {a['variacion_total']:+,}")
    for o in res["omitidos"]:
        print(f"  - {o}")
    for a in res["avisos"]:
        print(f"  ! {a}")
    print(f"\nListo: {len(res['alertas'])} mensajes del corte {res['corte_txt']}\n{res['pagina']}")
    if cfg["abrir_al_terminar"] and not args.no_abrir:
        webbrowser.open(res["pagina"].resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
