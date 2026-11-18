# -*- coding: utf-8 -*-
"""Panel local de recuperación: México y LATAM, con generación explícita."""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import logging
import tempfile
import zipfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import alertas_cobranza as motor
import ui

st.set_page_config(page_title="DATA · Alertas de recuperación", page_icon=":material/mark_chat_unread:",
                   layout="wide", initial_sidebar_state="expanded")
ui.apply_styles()


def fingerprint(sources: dict, cfg_json: str) -> str:
    digest = hashlib.sha256(cfg_json.encode("utf-8"))
    for region, source in sources.items():
        digest.update(region.encode())
        if source is not None:
            name, data = source
            digest.update(name.encode("utf-8"))
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
    return digest.hexdigest()


@st.cache_data(show_spinner=False, ttl=3600, max_entries=10)
def generar(region: str, nombre: str, datos: bytes, cfg_json: str) -> dict:
    cfg = json.loads(cfg_json)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        ruta = base / Path(nombre).name
        ruta.write_bytes(datos)
        read_error = False
        try:
            paises = motor.leer_pdf(ruta)
        except Exception:
            # Liberar el traceback de PyMuPDF antes de limpiar el temporal en Windows.
            read_error = True
        if read_error:
            raise motor.ErrorAlertas("No se pudo leer el PDF. Revisa que abra correctamente y vuelve a cargarlo.")
        if not paises:
            raise motor.ErrorAlertas("Este PDF no contiene páginas de Recuperación con tablas Bottom / Top. Revisa el archivo del corte.")
        mexico = [p for p in paises if motor.sin_acentos(p.nombre) == "mexico"]
        if region == "mexico" and len(mexico) != len(paises):
            raise motor.ErrorAlertas("Este archivo contiene países de LATAM. Cárgalo en la tarjeta LATAM y usa el PDF de México aquí.")
        if region == "latam" and mexico:
            raise motor.ErrorAlertas("Este archivo contiene México. Cárgalo en la tarjeta México y usa el PDF de LATAM aquí.")
        res = motor.procesar([ruta], cfg, base / "salida", por_fecha=False, con_pagina=False)
        for alerta in res["alertas"]:
            alerta["png"] = Path(alerta.pop("imagen_ruta")).read_bytes()
            alerta["region"] = region
    return {k: res[k] for k in ("corte_txt", "alertas", "lecturas", "omitidos", "avisos")}


def merge_results(results: list[dict]) -> dict:
    merged = {k: [] for k in ("alertas", "lecturas", "omitidos", "avisos")}
    for result in results:
        for key in merged:
            merged[key].extend(result[key])
    merged["avisos"] = list(dict.fromkeys(merged["avisos"]))
    merged["cortes"] = sorted({a["corte"] for a in merged["alertas"]}, key=lambda c: c.split("/")[::-1])
    return merged


def bundle(alertas: list[dict]) -> tuple[bytes, str]:
    mensajes = "\n\n".join(a["mensaje"] for a in alertas) + "\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archivo:
        for n, alerta in enumerate(alertas, 1):
            # Prefijo único incluso cuando ambos PDF usan el mismo orden interno.
            raiz = f"{n:02d}_{motor.nombre_archivo(alerta['pais'])}_{alerta['corte'].replace('/', '-')}"
            archivo.writestr(raiz + ".png", alerta["png"])
            archivo.writestr(raiz + ".txt", alerta["mensaje"])
        archivo.writestr("mensajes.txt", mensajes)
    return buffer.getvalue(), mensajes


def mostrar_tarjeta(alerta: dict) -> None:
    variacion = alerta["variacion_total"]
    moneda = motor.CONFIG_DEFECTO["paises"].get(alerta["pais"], {}).get("moneda", "$")
    signo = "−" if variacion < 0 else "+" if variacion > 0 else ""
    contenido = ui.result_card(
        pais=html.escape(alerta["pais"]), corte=html.escape(alerta["corte"]),
        archivo=html.escape(alerta["archivo"]), pagina=int(alerta["pagina"]),
        mensaje=html.escape(alerta["mensaje"]), imagen=base64.b64encode(alerta["png"]).decode("ascii"),
        variacion=f"{signo}{html.escape(moneda)}{abs(variacion):,}",
        tendencia="negative" if variacion < 0 else "positive" if variacion > 0 else "neutral",
    )
    if hasattr(st, "iframe"):
        st.iframe(contenido, height="content")
    else:
        components.html(contenido, height=610, scrolling=True)


with st.sidebar:
    ui.brand()
    ui.sidebar_nav()
    sidebar_status = st.empty()
    with st.expander("Cómo preparar tus alertas", expanded=False):
        st.markdown("1. **Carga los PDF** de México, LATAM o ambos.\n"
                    "2. Pulsa **Generar mensajes**.\n"
                    "3. Revisa cada país y **copia imagen y texto**.\n"
                    "4. Pega ambos en tu conversación de WhatsApp.")
    ui.sidebar_note()

ui.topbar()
ui.hero()
workflow_slot = st.empty()
ui.section("cargar-pdf", "Carga tus reportes", "Dos espacios, un mismo flujo. Puedes trabajar con una región o con ambas.", "upload")

sources = {}
columns = st.columns(2, gap="medium")
for column, region, title, subtitle, scope in (
    (columns[0], "mexico", "México", "Reporte nacional de cobranza y entregado.", ["México"]),
    (columns[1], "latam", "LATAM", "Reporte regional; se genera un mensaje por país.",
     ["Guatemala", "El Salvador", "Honduras", "Nicaragua", "Perú", "Colombia"]),
):
    with column, st.container(key=f"upload_{region}"):
        ui.upload_heading(region, title, subtitle, scope)
        archivo = st.file_uploader(f"PDF de {title}", type=["pdf"], key=f"source_{region}",
                                   label_visibility="collapsed", help="Avance Cobranza y Entregado · PDF de Power BI · Máximo 50 MB")
        sources[region] = (archivo.name, archivo.getvalue()) if archivo is not None else None
        ui.file_status(sources[region])

try:
    cfg = motor.cargar_config()
    cfg_json = json.dumps(cfg, sort_keys=True, ensure_ascii=False)
except motor.ErrorAlertas as exc:
    st.error(str(exc))
    st.stop()

current = fingerprint(sources, cfg_json)
loaded = sum(source is not None for source in sources.values())
with st.container(key="generate_panel"):
    copy_col, button_col = st.columns([2.2, 1], vertical_alignment="center")
    with copy_col:
        ui.action_summary(loaded)
    with button_col:
        create = st.button("Generar mensajes", key="generate", type="primary", icon=":material/auto_awesome:",
                           width="stretch", disabled=not loaded)

if create:
    results, errors = [], []
    with st.spinner("Leyendo reportes y preparando las imágenes y los mensajes…"):
        for region, source in sources.items():
            if source is None:
                continue
            try:
                results.append(generar(region, *source, cfg_json))
            except motor.ErrorAlertas as exc:
                errors.append(("México" if region == "mexico" else "LATAM", str(exc)))
            except Exception:
                logging.exception("Error generando alertas de %s", region)
                errors.append(("México" if region == "mexico" else "LATAM",
                               "No se pudo completar el reporte. Revisa el PDF y vuelve a generar los mensajes."))
    st.session_state["generated"] = {"fingerprint": current, "result": merge_results(results), "errors": errors}

generated = st.session_state.get("generated")
valid = generated is not None and generated["fingerprint"] == current
result = generated["result"] if valid else None
alertas = result["alertas"] if result else []
with workflow_slot.container():
    ui.workflow(loaded, bool(alertas))
with sidebar_status.container():
    ui.session_summary(loaded, len(alertas), result["cortes"] if result else [])

ui.section("resultados", "Mensajes y resultados", "Revisa la imagen del reporte y el texto de cada país antes de compartirlos.", "message")

if generated and not valid:
    st.info("Cambiaste los archivos. Pulsa Generar mensajes para actualizar los resultados y las descargas.")
if valid:
    for region, message in generated["errors"]:
        st.error(f"{region}: {message}")
    for aviso in result["avisos"]:
        st.warning(aviso)
    for name, pages in result["lecturas"]:
        if not pages:
            st.warning(f"{name}: no se encontraron páginas de Recuperación.")
    if result["omitidos"]:
        with st.expander(f"Países sin mensaje · {len(result['omitidos'])}"):
            for note in result["omitidos"]:
                st.write(note)

if alertas:
    ui.results_summary(alertas, result["cortes"], len(result["lecturas"]))
    labels = [f"{a['pais']} · {a['corte']}" for a in alertas]
    selected = st.multiselect("Países a incluir", labels, default=labels, key=f"countries_{current}",
                             placeholder="Elige los países que quieres revisar y descargar")
    visibles = [a for a, label in zip(alertas, labels) if label in selected]
    if visibles:
        paquete, mensajes = bundle(visibles)
        with st.container(key="downloads"):
            zip_col, text_col, info_col = st.columns([1.25, 1.25, 1.5], vertical_alignment="center")
            stamp = result["cortes"][-1].replace("/", "-")
            zip_col.download_button("Descargar paquete ZIP", paquete, f"alertas_{stamp}.zip", "application/zip",
                                    icon=":material/folder_zip:", width="stretch")
            text_col.download_button("Descargar mensajes TXT", mensajes.encode("utf-8"), f"mensajes_{stamp}.txt", "text/plain",
                                     icon=":material/download:", width="stretch")
            info_col.caption(f"{len(visibles)} mensajes con sus imágenes originales del PDF")
        ui.whatsapp_hint()
        for alerta in visibles:
            mostrar_tarjeta(alerta)
    else:
        st.info("Selecciona al menos un país para mostrar sus mensajes y habilitar las descargas.")
elif valid and not generated["errors"]:
    st.info("Los PDF se procesaron, pero ningún país generó mensaje. Revisa los países sin mensaje y la configuración.")
    ui.empty_results("Sin mensajes para este corte", "Los países sin movimiento o excluidos en la configuración no generan mensaje.")
else:
    ui.empty_results("Tus alertas aparecerán aquí", "Carga el PDF de México, el de LATAM o ambos y pulsa Generar mensajes.")

ui.footer()
