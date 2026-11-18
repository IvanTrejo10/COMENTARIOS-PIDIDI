# -*- coding: utf-8 -*-
"""Identidad visual del panel DATA, alineada con Estructuras RH."""
from html import escape
from pathlib import Path

import streamlit as st


def icon(name, size=22):
    paths = {
        "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
        "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
        "upload": '<path d="M12 16V3m-5 5 5-5 5 5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
        "download": '<path d="M12 3v13m-5-5 5 5 5-5M4 17v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
        "message": '<path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z"/><path d="M8 10h8M8 14h5"/>',
        "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a17 17 0 0 1 0 18 17 17 0 0 1 0-18Z"/>',
        "check": '<path d="m5 12 4 4L19 6"/>',
        "shield": '<path d="M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7Z"/><path d="m8 12 3 3 5-6"/>',
        "spark": '<path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    }
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths[name]}</svg>'


def put(markup):
    st.markdown(markup, unsafe_allow_html=True)


def apply_styles():
    put(f'<style>{(Path(__file__).parent / "assets" / "styles.css").read_text(encoding="utf-8")}</style>')


def brand():
    put(f'<div class="brand"><span class="brand-mark">{icon("grid", 25)}</span><div><div class="brand-title">DATA<span> Alertas</span></div><div class="brand-sub">INTELIGENCIA DE COBRANZA</div></div></div>')


def sidebar_nav():
    put(f'<p class="side-eyebrow">ESPACIO DE TRABAJO</p><nav aria-label="Secciones"><a class="side-nav active" href="#cargar-pdf" target="_self">{icon("file", 19)} Generar mensajes</a><a class="side-nav" href="#resultados" target="_self">{icon("message", 19)} Mensajes y resultados</a></nav><div class="side-divider"></div>')


def session_summary(loaded, messages, cuts):
    cut = " · ".join(cuts) if cuts else "Se detecta desde el PDF"
    put(f'<p class="side-eyebrow">TU SESIÓN</p><div class="session-card"><div><span>Reportes cargados</span><b>{loaded} / 2</b></div><div><span>Mensajes generados</span><b>{messages:02d}</b></div><div class="session-cut"><span>Corte del reporte</span><strong>{escape(cut)}</strong></div></div>')


def sidebar_note():
    put(f'<div class="side-note">{icon("shield", 23)}<h3>Tu reporte, en tu sesión.</h3><p>Los PDF cargados no se guardan en el proyecto. El envío por WhatsApp lo realizas tú.</p></div>')


def topbar():
    put(f'<div class="topbar"><div class="breadcrumb">{icon("grid", 16)} Portal de operaciones <span>/</span> <strong>Recuperación</strong></div><span class="portal-tag">{icon("globe", 15)} México + LATAM</span></div>')


def hero():
    put(f'<header class="hero"><div class="hero-copy"><div class="eyebrow">CENTRO DE ALERTAS · RECUPERACIÓN</div><h1>De tu PDF al mensaje.<br><span class="hero-accent">Listo para compartir.</span></h1><p>Convierte tus reportes de cobranza en imágenes y mensajes por país, listos para WhatsApp.</p><div class="hero-pills"><span>{icon("file", 16)} Reportes Power BI</span><span>{icon("globe", 16)} México y LATAM</span><span>{icon("check", 16)} Imagen + mensaje</span></div></div><div class="hero-preview" aria-hidden="true"><div class="preview-label">UN FLUJO MÁS SIMPLE</div><div class="preview-file">{icon("file", 31)}<div><b>Avance de cobranza</b><small>Reporte del corte · PDF</small></div><span>PDF</span></div><div class="preview-connector"><i></i><span>Procesar y redactar</span></div><div class="preview-message"><div class="preview-msg-title">{icon("message", 18)} Mensaje por país {icon("check", 16)}</div><div class="preview-line long"></div><div class="preview-line"></div><div class="preview-line short"></div><div class="preview-ready">Imagen y texto listos para copiar</div></div></div></header>')


def workflow(loaded, generated):
    states = ["done" if loaded else "active", "done" if generated else "active" if loaded else "", "active" if generated else ""]
    steps = [("file", "Carga tus PDF", "México, LATAM o ambos"), ("spark", "Genera tus mensajes", "Lectura y redacción automática"), ("message", "Revisa y comparte", "Copia el texto y la imagen")]
    put('<div class="workflow">' + ''.join(f'<div class="workflow-step {state}"><span class="step-icon">{icon("check" if state == "done" else name, 20)}</span><div><strong>{title}</strong><small>{desc}</small></div></div>' for state, (name, title, desc) in zip(states, steps)) + '</div>')


def section(anchor, title, subtitle, name):
    put(f'<div class="section-heading" id="{anchor}"><span class="section-icon">{icon(name, 22)}</span><div><h2>{title}</h2><p>{subtitle}</p></div></div>')


def upload_heading(region, title, description, scope):
    color = "teal" if region == "mexico" else "blue"
    put(f'<div class="upload-top"><span class="file-icon {color}">{icon("file" if region == "mexico" else "globe", 26)}</span><span class="file-category {color}">{"REPORTE NACIONAL" if region == "mexico" else "REPORTE REGIONAL"}</span></div><h3 class="upload-title">{title}</h3><p class="upload-description">{description}</p><div class="scope-pills">' + ''.join(f'<span>{country}</span>' for country in scope) + '</div>')


def file_status(source):
    if source:
        name, data = source
        size = f"{len(data) / 1024 / 1024:.1f} MB" if len(data) >= 1024 * 1024 else f"{len(data) / 1024:.0f} KB"
        put(f'<div class="file-state ready">{icon("check", 16)}<span title="{escape(name, quote=True)}">{escape(name)}</span><b>{size}</b></div>')
    else:
        put(f'<div class="file-state">{icon("clock", 16)}<span>Pendiente de carga</span><b>PDF · máx. 50 MB</b></div>')


def action_summary(loaded):
    title = "Todo listo para empezar" if not loaded else f'{loaded} {"reporte listo" if loaded == 1 else "reportes listos"} para generar'
    text = "Carga al menos un PDF para habilitar el generador." if not loaded else "Se prepararán las imágenes y los mensajes de los reportes cargados."
    put(f'<div class="action-summary"><span class="action-icon">{icon("spark", 24)}</span><div><h3>{title}</h3><p>{text}</p></div></div>')


def empty_results(title, text):
    put(f'<div class="empty-results"><div class="empty-icon">{icon("message", 31)}</div><h3>{title}</h3><p>{text}</p><div class="empty-pills"><span>Imagen Bottom / Top</span><span>Mensaje por país</span><span>Descarga ZIP y TXT</span></div></div>')


def results_summary(alertas, cuts, files):
    put(f'<div class="results-summary"><div class="result-stat"><span>MENSAJES GENERADOS</span><strong>{len(alertas):02d}</strong><small>Listos para revisar y copiar</small></div><div class="result-stat"><span>REPORTES PROCESADOS</span><strong>{files:02d}</strong><small>México y / o LATAM</small></div><div class="result-stat cut"><span>{"CORTE DEL REPORTE" if len(cuts) == 1 else "CORTES DE LOS REPORTES"}</span><strong>{" · ".join(escape(c) for c in cuts)}</strong><small>Fecha leída desde tus archivos</small></div></div>')


def whatsapp_hint():
    put(f'<div class="whatsapp-hint">{icon("message", 20)}<p><strong>Para compartir en WhatsApp</strong> Copia la imagen, pégala en el chat y agrega el texto como comentario antes de enviar.</p></div>')


def footer():
    put('<footer class="footer"><strong>DATA <span>/</span> Recuperación</strong><span>México + LATAM · Reportes que se convierten en acción.</span></footer>')


def result_card(*, pais, corte, archivo, pagina, mensaje, imagen, variacion, tendencia):
    template = (Path(__file__).parent / "assets" / "result_card.html").read_text(encoding="utf-8")
    for key, value in {"PAIS": pais, "CORTE": corte, "ARCHIVO": archivo, "PAGINA": pagina,
                       "MENSAJE": mensaje, "IMAGEN": imagen, "VARIACION": variacion, "TENDENCIA": tendencia}.items():
        template = template.replace("__" + key + "__", str(value))
    return template
