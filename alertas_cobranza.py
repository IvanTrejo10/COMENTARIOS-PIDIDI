# -*- coding: utf-8 -*-
"""
ALERTAS DIARIAS DE RECUPERACIÓN (México + LATAM)
================================================
Lee los PDF "Avance Cobranza y Entregado ... México / LATAM" (exportados de Power BI)
y arma lo que se manda por WhatsApp:

    0) el saludo ("Buen día, le comparto el avance de cobranza de la semana ...")
    y por cada país:
    1) la imagen con los recuadros Bottom / Top
    2) el mensaje ("Presenta una variación negativa en recuperación de ...")
    3) los lunes (PDF que trae la hoja Entregado): imagen y mensaje de trámites

Uso
---
    streamlit run app.py                            (página web: se suben los PDF y se copian los mensajes)
    python alertas_cobranza.py  "ruta\\México.pdf"  "ruta\\LATAM.pdf"
    python alertas_cobranza.py                      (toma los PDF más recientes de carpeta_pdfs)

    Opciones:  --salida CARPETA   --no-abrir   --config RUTA

Salida (carpeta salida\\AAAA-MM-DD del corte)
    alertas.html     página para revisar y copiar imagen / texto de cada país
    mensajes.txt     el saludo y todos los mensajes juntos
    0_saludo.txt     el saludo
    N_Pais.png/.txt  imagen y mensaje de cada país (N_Pais_tramites.* los de trámites)
    alertas.json     lo mismo en formato máquina (para el envío automático)

Requiere PyMuPDF; si falta, el script lo instala solo la primera vez (pip install "pymupdf<2").
"""
from __future__ import annotations

import argparse
import base64
import bisect
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
    "orden": ["México", "Guatemala", "El Salvador", "Honduras", "Nicaragua", "Perú", "Colombia"],
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

    # ── saludo que abre la conversación
    "saludo_avance": "Buen día, le comparto el avance de cobranza de la semana {semana} {anio} correspondiente al cierre {fecha}",
    # corte en domingo = cierre de la semana, que es lo que se manda los lunes
    "saludo_cierre": "Buen día, le comparto el cierre de cobranza de la semana {semana} {anio} correspondiente al cierre {fecha}",

    # ── trámites (hoja Entregado; solo viene en el PDF de los lunes)
    "tram_apertura": "En trámites, registra {creditos} créditos entregados ({var_creditos}), con un desembolso de {monto} ({var_monto}).",
    # país con una sola marca
    "tram_marca_unica_suben": "Ambos indicadores presentan crecimiento respecto a la semana anterior, correspondiente a la marca {marca}.",
    "tram_marca_unica_bajan": "Ambos indicadores presentan disminución respecto a la semana anterior, correspondiente a la marca {marca}.",
    "tram_marca_unica_mixto": "Respecto a la semana anterior, los créditos {creditos} y el desembolso {monto}, correspondiente a la marca {marca}.",
    # volumen (créditos) por marca
    "tram_vol_sube": "El crecimiento en volumen se concentra {principalmente}en {lista}",
    "tram_vol_sube_y_baja": ", mientras que {marca} disminuye {n} créditos",
    "tram_vol_sube_y_bajan": ", mientras que {marcas} disminuyen {n} créditos, respectivamente",
    "tram_vol_baja": "La disminución en volumen se concentra {principalmente}en {lista}",
    "tram_vol_baja_y_sube": ", mientras que {marca} presenta un incremento de {n} créditos",
    "tram_vol_baja_y_suben": ", mientras que {marcas} presentan incrementos de {n} créditos, respectivamente",
    # desembolso por marca
    "tram_des_suben": "En desembolso, los mayores incrementos corresponden a {lista}",
    "tram_des_sube_una": "En desembolso, el incremento corresponde a {lista}",
    "tram_des_ambas_suben": "En desembolso, ambas marcas registran incrementos: {lista}",
    "tram_des_bajan": "En desembolso, las mayores disminuciones corresponden a {lista}",
    "tram_des_baja_una": "En desembolso, la disminución corresponde a {lista}",
    "tram_des_ambas_bajan": "En desembolso, ambas marcas registran disminuciones: {lista}",
    # pocas marcas, unas suben y otras bajan: se dice qué hizo cada una
    "tram_des_gana_la_subida": "En desembolso, {suben}, compensando {bajan}",
    "tram_des_gana_la_bajada": "En desembolso, {suben}, pero {bajan}",
    # muchas marcas: solo se menciona la contraria si pesa
    "tram_des_y_baja": ", mientras que {marca} disminuye {monto}",
    "tram_des_y_sube": ", mientras que {marca} aumenta {monto}",
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
class MarcaEntregado:
    nombre: str
    creditos: float = 0.0      # Entregado Crédito: Créditos
    var_creditos: float = 0.0  # Entregado Crédito: Var Sem Ant
    monto: float = 0.0         # Entregado Monto: Desembolso
    var_monto: float = 0.0     # Entregado Monto: Var sem ant


@dataclass
class Entregado:
    """Hoja de trámites (tablas Entregado Monto y Entregado Crédito), última semana."""
    pagina: int                                  # base 1
    semana: Optional[int] = None
    marcas: list = field(default_factory=list)   # MarcaEntregado, sin el Total
    total: Optional[MarcaEntregado] = None
    recorte: object = None                       # rectángulo con las dos tablas para la imagen
    avisos: list = field(default_factory=list)


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
    semana: Optional[int] = None                    # semana en curso (tabla Trámites Total)
    entregado: Optional[Entregado] = None           # hoja de trámites, si el PDF la trae


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


# ── hojas que siguen a la de Recuperación de cada país ─────────────────────────────────────
def _renglones(pals: list[Palabra]) -> list[list[Palabra]]:
    """Agrupa las palabras por renglón; cada renglón va ordenado de izquierda a derecha."""
    out: list[list[Palabra]] = []
    for p in sorted(pals, key=lambda p: (p.cy, p.x0)):
        if out and abs(p.cy - out[-1][0].cy) <= 3.0:
            out[-1].append(p)
        else:
            out.append([p])
    for r in out:
        r.sort(key=lambda p: p.x0)
    return out


def _titulo_doble(pals: list[Palabra], primera: str, segunda: str):
    """Título de dos palabras ('Trámites Total', 'Entregado Monto'). Devuelve (palabra1, palabra2) o None."""
    for a in pals:
        if sin_acentos(a.txt) == primera:
            for b in pals:
                if (b is not a and abs(b.y0 - a.y0) < 2.5 and 0 <= b.x0 - a.x1 < 0.8 * (a.y1 - a.y0)
                        and sin_acentos(b.txt) == segunda):
                    return a, b
    return None


def _semana_en_curso(pals: list[Palabra]) -> Optional[int]:
    """Última semana de la tabla 'Trámites Total' (hoja Trámites/Efectividad): la semana del corte."""
    tit = _titulo_doble(pals, "tramites", "total")
    if tit is None:
        return None
    a = tit[0]
    semana = None
    for r in _renglones([p for p in pals if p.cy > a.y1]):
        if sin_acentos(r[0].txt) == "tramites":  # título de la tabla siguiente
            break
        if (r[0].x0 < a.x0 - 50 and re.fullmatch(r"\d{1,2}", r[0].txt) and 1 <= int(r[0].txt) <= 53
                and len(r) >= 3 and a_numero(r[1].txt) is not None):
            semana = int(r[0].txt)
    return semana


def _celdas(palabras: list[Palabra], alto: float, inicios: tuple = ()) -> list:
    """Junta las palabras de un renglón de encabezado en celdas -> [[texto, x0, x1], ...]"""
    celdas: list = []
    for p in palabras:
        if not celdas or p.x0 - celdas[-1][2] >= 0.45 * alto or sin_acentos(p.txt) in inicios:
            celdas.append([p.txt, p.x0, p.x1])
        else:
            celdas[-1][0] += " " + p.txt
            celdas[-1][2] = p.x1
    return celdas


def _matriz_entregado(pals: list[Palabra], titulo):
    """Lee la tabla que está bajo un título 'Entregado ...': por marca, valor y variación de cada semana.

    Devuelve (marcas, ultima, semana, caja) o None si no reconoce la tabla:
      marcas  nombres en el orden de la tabla (el último es 'Total')
      ultima  {marca: (valor, variación)} de la última semana; vacío si la tabla no trae datos
      semana  número de esa última semana
      caja    (x0, y0, x1, y1) de la tabla con su título
    """
    a, b = titulo
    alto = a.y1 - a.y0
    abajo = _renglones([p for p in pals if p.cy > max(a.y1, b.y1)])
    i = next((k for k, r in enumerate(abajo) if sin_acentos(r[0].txt) == "marca"), None)
    if (i is None or abajo[i][0].cy - a.cy > 4 * alto or i + 1 >= len(abajo)
            or sin_acentos(abajo[i + 1][0].txt) != "ano"):
        return None
    marcas = [c[0] for c in _celdas(abajo[i][1:], alto)]
    medidas = _celdas(abajo[i + 1][1:], alto, inicios=("desembolso", "creditos", "var"))
    if not marcas or len(medidas) != 2 * len(marcas):
        return None
    centros = [(c[1] + c[2]) / 2 for c in medidas]  # los valores van alineados a la derecha de su columna

    usadas = abajo[i] + abajo[i + 1]
    ultima, semana = {}, None
    for r in abajo[i + 2:]:
        nums = [a_numero(p.txt) for p in r]
        if any(n is None for n in nums):
            break  # ya no es la tabla
        usadas = usadas + r
        if len(r) == 1:
            continue  # renglón del año
        fila, etiqueta = {}, None
        for p, n in zip(r, nums):
            col = bisect.bisect_right(centros, p.x1) - 1
            if col < 0:
                etiqueta = int(n)  # columna Año: número de semana
            else:
                fila[col] = n
        if fila:
            ultima = {m: (fila.get(2 * k), fila.get(2 * k + 1)) for k, m in enumerate(marcas)}
            semana = etiqueta
    caja = (min(p.x0 for p in usadas + [a]), a.y0, max(p.x1 for p in usadas + [b]), max(p.y1 for p in usadas))
    return marcas, ultima, semana, caja


def _leer_entregado(page, pals: list[Palabra], pagina: int) -> Optional[Entregado]:
    """Hoja de trámites (Entregado Monto + Entregado Crédito). None si la página no es esa hoja."""
    t_monto = _titulo_doble(pals, "entregado", "monto")
    t_cred = _titulo_doble(pals, "entregado", "credito")
    if t_monto is None or t_cred is None:
        return None
    ent = Entregado(pagina)
    monto, cred = _matriz_entregado(pals, t_monto), _matriz_entregado(pals, t_cred)
    if monto is None or cred is None:
        ent.avisos.append("No pude leer las tablas Entregado Monto / Entregado Crédito.")
        return ent

    # Imagen: las dos tablas con su barra de título (la barra es un poco más ancha que la tabla)
    cajas = [monto[3], cred[3]]
    dibujos = page.get_drawings()
    for a, b in (t_monto, t_cred):
        cajas += [tuple(d["rect"]) for d in dibujos
                  if d.get("fill") and d["rect"].height < 3 * (a.y1 - a.y0)
                  and d["rect"].x0 <= a.x0 and d["rect"].x1 >= b.x1 and d["rect"].y0 <= a.cy <= d["rect"].y1]
    derecha = min(max(c[2] for c in cajas), max(monto[3][2], cred[3][2]) + 30)  # sin la cola de la barra
    ent.recorte = (min(c[0] for c in cajas) - 8, min(c[1] for c in cajas) - 8,
                   derecha + 8, max(c[3] for c in cajas) + 10)

    marcas, ult_c, sem_c, _ = cred
    marcas_m, ult_m, sem_m, _ = monto
    ent.semana = sem_c or sem_m
    if not ult_c or not ult_m:
        return ent  # la hoja viene sin datos (p. ej. Nicaragua)
    por_marca_m = {sin_acentos(k): v for k, v in ult_m.items()}
    if [sin_acentos(x) for x in marcas] != [sin_acentos(x) for x in marcas_m]:
        ent.avisos.append("Entregado Monto y Entregado Crédito no traen las mismas marcas.")
    if sem_c != sem_m:
        ent.avisos.append(f"Entregado Crédito llega a la semana {sem_c} y Entregado Monto a la {sem_m}.")
    for nombre in marcas:
        cr, dcr = ult_c.get(nombre, (None, None))
        mo, dmo = por_marca_m.get(sin_acentos(nombre), (None, None))
        m = MarcaEntregado(nombre, cr or 0.0, dcr or 0.0, mo or 0.0, dmo or 0.0)
        if sin_acentos(nombre) == "total":
            ent.total = m
        else:
            ent.marcas.append(m)
    if ent.total and ent.marcas:
        tol = len(ent.marcas) + 1
        if (abs(sum(m.var_creditos for m in ent.marcas) - ent.total.var_creditos) > tol
                or abs(sum(m.var_monto for m in ent.marcas) - ent.total.var_monto) > tol):
            ent.avisos.append("La suma por marca no da el total de la hoja de trámites.")
    return ent


def leer_pdf(ruta: Path) -> list[Pais]:
    """Devuelve un Pais por cada página de 'Recuperación'.

    Las hojas que siguen a cada una (Trámites/Efectividad y, los lunes, Entregado) no traen el
    nombre del país: su semana en curso y sus trámites se le cargan al país de la hoja anterior.
    """
    paises = []
    doc = pymupdf.open(str(ruta))
    for i, page in enumerate(doc):
        pals = _palabras(page)
        tits = _titulos(pals)
        secciones = _secciones(page, pals, tits)
        if secciones is None:
            if paises:  # hoja de Trámites/Efectividad o de Entregado del último país leído
                if paises[-1].semana is None:
                    paises[-1].semana = _semana_en_curso(pals)
                if paises[-1].entregado is None:
                    paises[-1].entregado = _leer_entregado(page, pals, i + 1)
            continue
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


def guardar_imagen(ruta_pdf: Path, pagina: int, recorte, destino: Path, dpi: int) -> None:
    """Guarda en PNG el recorte (x0, y0, x1, y1) de la página (base 1)."""
    doc = pymupdf.open(str(ruta_pdf))
    page = doc[pagina - 1]
    clip = pymupdf.Rect(*recorte) & page.rect
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


def redactar_saludo(corte: dt.date, semana: int) -> str:
    """Saludo que abre la conversación. Corte en domingo = cierre de la semana (se manda el lunes)."""
    anio = corte.year
    if semana >= 52 and corte.month == 1:
        anio -= 1
    elif semana == 1 and corte.month == 12:
        anio += 1
    clave = "saludo_cierre" if corte.weekday() == 6 else "saludo_avance"
    return FRASES[clave].format(semana=semana, anio=anio, fecha=corte.strftime("%d/%m/%Y"))


def redactar_tramites(pais: Pais, cfg: dict) -> tuple[Optional[str], str]:
    """Mensaje de trámites (hoja Entregado). Devuelve (mensaje, motivo), igual que redactar()."""
    ent = pais.entregado
    if ent is None:
        return None, "el PDF no trae la hoja de trámites"
    if sin_acentos(pais.nombre) in {sin_acentos(x) for x in cfg["paises_excluidos"]}:
        return None, "excluido en la configuración"
    tot, marcas = ent.total, ent.marcas
    if tot is None or not marcas:
        return None, "la hoja de trámites viene sin datos"
    if cfg["omitir_sin_movimiento"] and not any(
            round(v) for v in (tot.creditos, tot.var_creditos, tot.monto, tot.var_monto)):
        return None, "sin trámites, todo en 0"

    info = next((v for k, v in cfg["paises"].items() if sin_acentos(k) == sin_acentos(pais.nombre)),
                {"bandera": "", "moneda": "$"})
    moneda, top_n = info["moneda"], int(cfg["top_n"])

    def _signo(v: float, n: int, con_signo: bool) -> str:
        return ("-" if v < 0 and n else "+" if v > 0 and n else "") if con_signo else ""

    def din(v: float, signo: bool = True) -> str:  # dinero: -Q19,200
        n = int(round(abs(v)))
        return f"{_signo(v, n, signo)}{moneda}{n:,}"

    def num(v: float, signo: bool = True) -> str:  # créditos: +2,070
        n = int(round(abs(v)))
        return f"{_signo(v, n, signo)}{n:,}"

    def nom(m: MarcaEntregado) -> str:
        return " ".join(cfg["acentos"].get(w, w) for w in m.nombre.split())

    d_cred, d_monto = int(round(tot.var_creditos)), int(round(tot.var_monto))
    partes = [FRASES["tram_apertura"].format(
        creditos=num(tot.creditos, signo=False), var_creditos=num(tot.var_creditos) if d_cred else "sin cambio",
        monto=din(tot.monto, signo=False), var_monto=din(tot.var_monto) if d_monto else "sin cambio")]

    if len(marcas) == 1:
        if d_cred > 0 and d_monto > 0:
            partes.append(FRASES["tram_marca_unica_suben"].format(marca=nom(marcas[0])))
        elif d_cred < 0 and d_monto < 0:
            partes.append(FRASES["tram_marca_unica_bajan"].format(marca=nom(marcas[0])))
        else:
            def verbo(d: int, plural: bool) -> str:
                v = "aumenta" if d > 0 else "disminuye" if d < 0 else "se mantiene"
                return v + "n" if plural else v
            partes.append(FRASES["tram_marca_unica_mixto"].format(
                creditos=verbo(d_cred, True), monto=verbo(d_monto, False), marca=nom(marcas[0])))
    else:
        muchas = len(marcas) > top_n  # con muchas marcas (México) solo se nombran las principales

        def contrarias(lista: list, valor, principal: float) -> list:
            """Las que van en sentido contrario: todas si son pocas marcas; si son muchas, solo las de peso."""
            if not muchas:
                return lista
            return [m for m in lista if abs(valor(m)) >= 0.25 * abs(principal)][:2]

        # ── volumen (créditos)
        sube = sorted((m for m in marcas if round(m.var_creditos) > 0), key=lambda m: -m.var_creditos)
        baja = sorted((m for m in marcas if round(m.var_creditos) < 0), key=lambda m: m.var_creditos)
        if d_cred >= 0 and sube:
            txt = FRASES["tram_vol_sube"].format(
                principalmente="principalmente " if len(sube) > top_n else "",
                lista=lista_es([f"{nom(m)} ({num(m.var_creditos)})" for m in sube[:top_n]]))
            otras = contrarias(baja, lambda m: m.var_creditos, sube[0].var_creditos)
            if len(otras) == 1:
                txt += FRASES["tram_vol_sube_y_baja"].format(
                    marca=nom(otras[0]), n=num(otras[0].var_creditos, signo=False))
            elif otras:
                txt += FRASES["tram_vol_sube_y_bajan"].format(
                    marcas=lista_es([nom(m) for m in otras]),
                    n=lista_es([num(m.var_creditos, signo=False) for m in otras]))
            partes.append(txt + ".")
        elif d_cred < 0 and baja:
            txt = FRASES["tram_vol_baja"].format(
                principalmente="principalmente " if len(baja) > top_n else "",
                lista=lista_es([f"{nom(m)} ({num(m.var_creditos)} créditos)" for m in baja[:top_n]]))
            otras = contrarias(sube, lambda m: m.var_creditos, baja[0].var_creditos)
            if len(otras) == 1:
                txt += FRASES["tram_vol_baja_y_sube"].format(
                    marca=nom(otras[0]), n=num(otras[0].var_creditos, signo=False))
            elif otras:
                txt += FRASES["tram_vol_baja_y_suben"].format(
                    marcas=lista_es([nom(m) for m in otras]),
                    n=lista_es([num(m.var_creditos, signo=False) for m in otras]))
            partes.append(txt + ".")

        # ── desembolso
        sube = sorted((m for m in marcas if round(m.var_monto) > 0), key=lambda m: -m.var_monto)
        baja = sorted((m for m in marcas if round(m.var_monto) < 0), key=lambda m: m.var_monto)

        def cada_una(ms: list, verbo: str) -> str:  # "Pistiyo crece Q168,650 y La Casita Q71,050"
            return lista_es([f"{nom(m)} {verbo} {din(m.var_monto, signo=False)}" if k == 0
                             else f"{nom(m)} {din(m.var_monto, signo=False)}" for k, m in enumerate(ms)])

        if sube and baja and not muchas:
            if d_monto >= 0:
                bajan = ("la disminución de " if len(baja) == 1 else "las disminuciones de ") + lista_es(
                    [f"{din(m.var_monto)} en {nom(m)}" for m in baja])
                txt = FRASES["tram_des_gana_la_subida"].format(suben=cada_una(sube, "aumenta"), bajan=bajan)
            else:
                txt = FRASES["tram_des_gana_la_bajada"].format(
                    suben=cada_una(sube, "crece"), bajan=cada_una(baja, "disminuye"))
            partes.append(txt + ".")
        elif sube or baja:
            arriba = bool(sube) and (not baja or d_monto >= 0)
            ms = sube if arriba else baja
            if len(marcas) == 2 and len(ms) == 2:
                clave = "tram_des_ambas_suben" if arriba else "tram_des_ambas_bajan"
            elif len(ms) == 1:
                clave = "tram_des_sube_una" if arriba else "tram_des_baja_una"
            else:
                clave = "tram_des_suben" if arriba else "tram_des_bajan"
            txt = FRASES[clave].format(lista=lista_es([f"{nom(m)} ({din(m.var_monto)})" for m in ms[:top_n]]))
            for m in contrarias(baja if arriba else sube, lambda m: m.var_monto, ms[0].var_monto)[:1]:
                txt += FRASES["tram_des_y_baja" if arriba else "tram_des_y_sube"].format(
                    marca=nom(m), monto=din(m.var_monto, signo=False))
            partes.append(txt + ".")

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
  .img { background: #fff; border-right: 1px solid var(--linea); display: flex; align-items: center; justify-content: center; }
  .img img { max-width: 100%; max-height: 300px; width: auto; height: auto; display: block; }
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
  article.solo { grid-template-columns: 1fr; }
  article.solo pre::first-line { font-weight: inherit; font-size: inherit; }
</style></head><body>
<header>
  <h1>Alertas de recuperación · Corte __CORTE__</h1>
  <p>__RESUMEN__ · Para WhatsApp: <b>Copiar imagen</b> → pegar en el chat → <b>Copiar texto</b> → pegar como comentario → enviar.</p>
</header>
<main>
__NOTAS__
__SALUDO__
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


def armar_pagina(alertas: list[dict], omitidos: list[str], avisos: list[str], corte_txt: str,
                 fuentes: list[str], saludo: str = "") -> str:
    tarjeta_saludo = ""
    if saludo:
        tarjeta_saludo = (
            f'<article class="solo"><div class="txt"><pre id="txt0">{html.escape(saludo)}</pre>'
            f'<div class="bot"><button onclick="copiarTexto(\'txt0\', this)">Copiar texto</button>'
            f'<span class="pista">Saludo: se manda primero.</span></div></div></article>'
        )
    tarjetas = []
    for n, a in enumerate(alertas, 1):
        b64 = base64.b64encode(Path(a["imagen_ruta"]).read_bytes()).decode("ascii")
        que = "Tablas de trámites de" if a.get("tipo") == "tramites" else "Bottom y Top de"
        tarjetas.append(
            f'<article><div class="img"><img id="img{n}" alt="{que} {html.escape(a["pais"])}" '
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
            .replace("__NOTAS__", notas).replace("__SALUDO__", tarjeta_saludo)
            .replace("__TARJETAS__", "\n".join(tarjetas)))


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

    Sin carpeta_pdfs en la configuración se buscan en la subcarpeta "pdfs" y en la misma carpeta
    donde está este script.
    """
    if cfg["carpeta_pdfs"]:
        carpetas = [Path(cfg["carpeta_pdfs"])]
        if not carpetas[0].is_dir():
            raise ErrorAlertas(f"No existe la carpeta de PDF: {carpetas[0]}\n"
                               "Corrige carpeta_pdfs en config_alertas.json o arrastra los PDF sobre generar_alertas.bat.")
    else:
        carpetas = [c for c in (AQUI / "pdfs", AQUI) if c.is_dir()]
    candidatos, vistos = [], set()
    for carpeta in carpetas:
        for p in sorted(carpeta.glob(cfg["patron_pdf"])):
            if p.is_file() and p.name not in vistos:
                vistos.add(p.name)
                candidatos.append(p)
    if not candidatos:
        raise ErrorAlertas(f"No hay PDF '{cfg['patron_pdf']}' en " + " ni en ".join(str(c) for c in carpetas) + "\n"
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

    Devuelve un dict con: corte_txt, semana, saludo, carpeta, pagina, lecturas [(archivo, páginas)],
    alertas, omitidos, avisos. Las alertas van en el orden en que se mandan (por país: recuperación
    y, si el PDF trae la hoja Entregado, trámites) y cada una trae: orden, tipo ("recuperacion" o
    "tramites"), pais, corte, mensaje, imagen, imagen_ruta, archivo, pagina, variacion_total (en
    recuperación, la variación total; en trámites, la variación de créditos) y resumen.
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

    # ── saludo: la semana es la que trae el PDF (tabla Trámites Total); si no la trae, la del
    #    nombre del archivo ("Sem 47"); y si tampoco, la del calendario.
    del_corte = [(r, p) for r, p in paises if p.corte == corte] or paises
    semanas = [p.semana for _, p in del_corte if p.semana]
    if semanas:
        semana = max(set(semanas), key=semanas.count)
    else:
        m = re.search(r"Sem[ _.-]*(\d{1,2})(?!\d)", " ".join(r.name for r, _ in del_corte), re.I)
        semana = int(m.group(1)) if m else corte.isocalendar()[1]
    saludo = redactar_saludo(corte, semana)
    (salida / "0_saludo.txt").write_text(saludo, encoding="utf-8")

    # ── redactar + imágenes (por país: recuperación y, si viene la hoja Entregado, trámites)
    alertas, omitidos, avisos = [], [], []
    if len(cortes) > 1:
        avisos.append("Los PDF traen fechas de corte distintas (" + ", ".join(c.strftime("%d/%m/%Y") for c in cortes)
                      + "); el saludo usa la más reciente.")
    for ruta, p in paises:
        mensaje, motivo = redactar(p, cfg)
        tramites, motivo_t = redactar_tramites(p, cfg)
        avisos += [f"{p.nombre}: {a}" for a in p.avisos]
        if p.entregado is not None:
            avisos += [f"{p.nombre} (trámites): {a}" for a in p.entregado.avisos]
        if mensaje is None:
            omitidos.append(f"{p.nombre}: no se generó mensaje ({motivo}).")
        elif tramites is None and p.entregado is not None:
            omitidos.append(f"{p.nombre}: sin mensaje de trámites ({motivo_t}).")

        partes = []  # (tipo, mensaje, página, recorte, variación que resume la tarjeta, resumen para la consola)
        if mensaje is not None:
            v = int(round(p.total.var))
            partes.append(("recuperacion", mensaje, p.pagina, p.recorte, v, f"{v:+,}"))
        if tramites is not None:
            t = p.entregado.total
            v = int(round(t.var_creditos))
            partes.append(("tramites", tramites, p.entregado.pagina, p.entregado.recorte, v,
                           f"{int(round(t.creditos)):,} créditos ({v:+,})"))
        for tipo, texto, pag, recorte, variacion, resumen in partes:
            n = len(alertas) + 1
            raiz = f"{n}_{nombre_archivo(p.nombre)}" + ("_tramites" if tipo == "tramites" else "")
            img = salida / f"{raiz}.png"
            guardar_imagen(ruta, pag, recorte, img, int(cfg["dpi_imagen"]))
            (salida / f"{raiz}.txt").write_text(texto, encoding="utf-8")
            alertas.append({"orden": n, "tipo": tipo, "pais": p.nombre,
                            "corte": p.corte.strftime("%d/%m/%Y") if p.corte else corte_txt,
                            "mensaje": texto, "imagen": img.name, "imagen_ruta": str(img),
                            "archivo": p.archivo, "pagina": pag,
                            "variacion_total": variacion, "resumen": resumen})

    (salida / "mensajes.txt").write_text(
        "\n\n".join([saludo] + [a["mensaje"] for a in alertas]) + "\n", encoding="utf-8")
    pagina = None
    if con_pagina:
        pagina = salida / "alertas.html"
        pagina.write_text(armar_pagina(alertas, omitidos, avisos, corte_txt, [r.name for r in rutas], saludo),
                          encoding="utf-8")
    (salida / "alertas.json").write_text(json.dumps(
        {"corte": corte_txt, "semana": semana, "saludo": saludo,
         "generado": dt.datetime.now().isoformat(timespec="seconds"),
         "alertas": [{k: v for k, v in a.items() if k != "imagen_ruta"} for a in alertas],
         "omitidos": omitidos, "avisos": avisos}, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"corte_txt": corte_txt, "semana": semana, "saludo": saludo, "carpeta": salida, "pagina": pagina,
            "lecturas": lecturas, "alertas": alertas, "omitidos": omitidos, "avisos": avisos}


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
    print(f"  {res['saludo']}")
    for a in res["alertas"]:
        print(f"  + {a['pais']}{' (trámites)' if a['tipo'] == 'tramites' else ''}: {a['resumen']}")
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
