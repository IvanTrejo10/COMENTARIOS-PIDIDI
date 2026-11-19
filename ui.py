# -*- coding: utf-8 -*-
"""Sistema visual Noir Liquid Aurora para DATA · Alertas de recuperación."""
from __future__ import annotations

from html import escape
from pathlib import Path
import unicodedata

import streamlit as st


def _norm(texto: str) -> str:
    limpio = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in limpio if not unicodedata.combining(c)).strip().lower()


def icon(name: str, size: int = 20) -> str:
    paths = {
        "grid": '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
        "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
        "upload": '<path d="M12 16V4m-5 4 5-5 5 5M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
        "download": '<path d="M12 3v13m-5-5 5 5 5-5M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>',
        "message": '<path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z"/><path d="M8 10h8M8 14h5"/>',
        "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18Z"/>',
        "check": '<path d="m5 12.5 4.2 4.2L19 7"/>',
        "check_double": '<path d="m2.5 12.5 4 4L15 8"/><path d="m9.5 15.5 2 2L21 8"/>',
        "shield": '<path d="M12 3 4 6.5V12c0 5 8 9 8 9s8-4 8-9V6.5Z"/><path d="m8.8 12.2 2.2 2.3 4.5-5"/>',
        "spark": '<path d="m12 2.8 2.2 6.2L20.5 11l-6.3 2.1L12 19.5l-2.2-6.4L3.5 11l6.3-2Z"/><path d="M19 3v3M20.5 4.5h-3"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
        "calendar": '<rect x="3" y="4.5" width="18" height="16.5" rx="2.5"/><path d="M8 2.5v4M16 2.5v4M3 9.5h18"/>',
        "layers": '<path d="m12 3 9 4.8-9 4.8-9-4.8Z"/><path d="m3 12.5 9 4.8 9-4.8"/><path d="m3 17.2 9 4.8 9-4.8"/>',
        "zap": '<path d="M13 2 4.5 13H12l-1 9 8.5-11H12Z"/>',
        "trend_up": '<path d="m4 17 6-6 4 4 6-7"/><path d="M15 8h5v5"/>',
        "trend_down": '<path d="m4 7 6 6 4-4 6 7"/><path d="M15 16h5v-5"/>',
        "trend_flat": '<path d="M4 12h16"/><path d="m16 8 4 4-4 4"/>',
        "arrow_right": '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
        "send": '<path d="M21 3 10 14"/><path d="m21 3-7 18-4-7-7-4Z"/>',
        "activity": '<path d="M3 12h4l2.5-7 5 14 2.5-7h4"/>',
    }
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{paths[name]}</svg>'
    )


def flag_svg(country: str, size: int = 16) -> str:
    """Bandera circular vectorial SVG nítida en Windows, macOS y Linux."""
    key = _norm(country)
    flags = {
        "mexico": (
            '<rect width="8" height="24" x="0" y="0" fill="#006847"/>'
            '<rect width="8" height="24" x="8" y="0" fill="#FFFFFF"/>'
            '<rect width="8" height="24" x="16" y="0" fill="#CE1126"/>'
            '<circle cx="12" cy="12" r="2.2" fill="#8B5A2B"/>'
            '<circle cx="12" cy="12.6" r="1.2" fill="#C89D54"/>'
        ),
        "guatemala": (
            '<rect width="8" height="24" x="0" y="0" fill="#4997D0"/>'
            '<rect width="8" height="24" x="8" y="0" fill="#FFFFFF"/>'
            '<rect width="8" height="24" x="16" y="0" fill="#4997D0"/>'
            '<circle cx="12" cy="12" r="2.1" fill="#2E8B57"/>'
            '<circle cx="12" cy="12" r="1" fill="#EAB308"/>'
        ),
        "el salvador": (
            '<rect width="24" height="8" x="0" y="0" fill="#0F47AF"/>'
            '<rect width="24" height="8" x="0" y="8" fill="#FFFFFF"/>'
            '<rect width="24" height="8" x="0" y="16" fill="#0F47AF"/>'
            '<polygon points="12,9.4 14.3,13.8 9.7,13.8" fill="#D4AF37"/>'
        ),
        "honduras": (
            '<rect width="24" height="8" x="0" y="0" fill="#00BCE4"/>'
            '<rect width="24" height="8" x="0" y="8" fill="#FFFFFF"/>'
            '<rect width="24" height="8" x="0" y="16" fill="#00BCE4"/>'
            '<circle cx="12" cy="12" r="1.05" fill="#00BCE4"/>'
            '<circle cx="9.2" cy="10.6" r="0.85" fill="#00BCE4"/>'
            '<circle cx="9.2" cy="13.4" r="0.85" fill="#00BCE4"/>'
            '<circle cx="14.8" cy="10.6" r="0.85" fill="#00BCE4"/>'
            '<circle cx="14.8" cy="13.4" r="0.85" fill="#00BCE4"/>'
        ),
        "nicaragua": (
            '<rect width="24" height="8" x="0" y="0" fill="#0067C6"/>'
            '<rect width="24" height="8" x="0" y="8" fill="#FFFFFF"/>'
            '<rect width="24" height="8" x="0" y="16" fill="#0067C6"/>'
            '<polygon points="12,9.5 14.2,13.7 9.8,13.7" fill="#C9A227"/>'
            '<circle cx="12" cy="12.3" r="0.85" fill="#38BDF8"/>'
        ),
        "peru": (
            '<rect width="8" height="24" x="0" y="0" fill="#D91023"/>'
            '<rect width="8" height="24" x="8" y="0" fill="#FFFFFF"/>'
            '<rect width="8" height="24" x="16" y="0" fill="#D91023"/>'
        ),
        "colombia": (
            '<rect width="24" height="12" x="0" y="0" fill="#FCD116"/>'
            '<rect width="24" height="6" x="0" y="12" fill="#003893"/>'
            '<rect width="24" height="6" x="0" y="18" fill="#CE1126"/>'
        ),
    }
    svg_body = flags.get(key)
    if svg_body is None:
        return f'<span class="flag-circle fallback" style="width:{size}px;height:{size}px">{icon("globe", max(size - 4, 10))}</span>'
    return (
        f'<span class="flag-circle" style="width:{size}px;height:{size}px" aria-hidden="true">'
        f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" preserveAspectRatio="xMidYMid slice">{svg_body}</svg>'
        f'</span>'
    )


def put(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def apply_styles() -> None:
    css = (Path(__file__).parent / "assets" / "styles.css").read_text(encoding="utf-8")
    put(f"<style>{css}</style>")


def brand() -> None:
    put(
        '<div class="brand">'
        f'<span class="brand-mark">{icon("grid", 21)}</span>'
        '<div class="brand-meta">'
        '<div class="brand-title">DATA<span> Alertas</span></div>'
        '<div class="brand-sub"><i class="live-dot"></i>RECUPERACIÓN · STUDIO</div>'
        '</div>'
        '</div>'
    )


def sidebar_nav() -> None:
    put(
        '<p class="side-eyebrow">NAVEGACIÓN</p>'
        '<nav class="side-nav-group" aria-label="Secciones">'
        f'<a class="side-nav active" href="#cargar-pdf" target="_self"><span class="nav-ico">{icon("upload", 16)}</span><span>Cargar reportes</span><span class="nav-arrow">{icon("arrow_right", 13)}</span></a>'
        f'<a class="side-nav" href="#resultados" target="_self"><span class="nav-ico">{icon("message", 16)}</span><span>Resultados y alertas</span><span class="nav-arrow">{icon("arrow_right", 13)}</span></a>'
        '</nav>'
        '<div class="side-divider"></div>'
    )


def session_summary(loaded: int, messages: int, cuts: list[str]) -> None:
    cut = " · ".join(cuts) if cuts else "Esperando archivo"
    pct = int((loaded / 2) * 100)
    status_cls = "ready" if messages else ("loaded" if loaded else "idle")
    status_lbl = (
        "Alertas listas" if messages
        else ("Listo para generar" if loaded else "En espera")
    )
    put(
        '<p class="side-eyebrow">SESIÓN ACTUAL</p>'
        f'<div class="session-card {status_cls}">'
        '<div class="session-head">'
        f'<span class="session-badge"><i class="badge-dot"></i>{status_lbl}</span>'
        f'<span class="session-pct">{pct}%</span>'
        '</div>'
        f'<div class="session-bar"><span style="width:{pct}%"></span></div>'
        '<div class="session-metrics">'
        f'<div class="session-metric"><span>PDFs</span><b>{loaded}<small>/2</small></b></div>'
        f'<div class="session-metric"><span>Alertas</span><b>{messages:02d}</b></div>'
        '</div>'
        '<div class="session-cut">'
        f'<span>{icon("calendar", 13)} Corte</span>'
        f'<strong>{escape(cut)}</strong>'
        '</div>'
        '</div>'
    )


def sidebar_note() -> None:
    put(
        '<div class="side-note">'
        f'<div class="side-note-head"><span class="shield-badge">{icon("shield", 17)}</span><h3>Procesamiento 100% local</h3></div>'
        '<p>Tus reportes se leen únicamente en memoria temporal de tu equipo. Tú decides cuándo copiar y enviar por WhatsApp.</p>'
        '</div>'
    )


def topbar(loaded: int = 0, messages: int = 0, cuts: list[str] | None = None) -> None:
    cuts = cuts or []
    if messages:
        state_cls = "live"
        state_txt = f"{messages:02d} {'alerta lista' if messages == 1 else 'alertas listas'}"
    elif loaded:
        state_cls = "ready"
        state_txt = f"{loaded}/2 PDF listo{'s' if loaded > 1 else ''}"
    else:
        state_cls = "idle"
        state_txt = "Motor local activo"

    cut_pill = (
        f'<span class="nav-cut">{icon("calendar", 13)} {escape(" · ".join(cuts))}</span>'
        if cuts else ""
    )

    put(
        '<nav class="floating-nav anim-reveal" style="--delay:0ms" aria-label="Barra principal">'
        '<div class="nav-brand">'
        f'<span class="nav-jewel">{icon("grid", 16)}</span>'
        '<span class="nav-wordmark">DATA <b>Alertas</b></span>'
        '</div>'
        '<div class="nav-links">'
        f'<a href="#cargar-pdf" target="_self" class="nav-pill active">{icon("upload", 14)}<span>Cargar</span></a>'
        f'<a href="#resultados" target="_self" class="nav-pill">{icon("message", 14)}<span>Resultados</span></a>'
        '</div>'
        '<div class="nav-right">'
        f'{cut_pill}'
        f'<span class="nav-status {state_cls}"><i class="live-dot"></i>{state_txt}</span>'
        '</div>'
        '</nav>'
    )


def hero() -> None:
    put(
        '<header class="hero-stage anim-reveal" style="--delay:60ms">'
        '<div class="hero-aura aura-emerald" aria-hidden="true"></div>'
        '<div class="hero-aura aura-sapphire" aria-hidden="true"></div>'
        '<div class="hero-aura aura-gold" aria-hidden="true"></div>'
        '<svg class="hero-arcs" viewBox="0 0 1160 280" fill="none" aria-hidden="true" preserveAspectRatio="xMidYMid slice">'
        '<defs>'
        '<linearGradient id="arcGrad1" x1="0%" y1="50%" x2="100%" y2="50%">'
        '<stop offset="0%" stop-color="#14B8A6" stop-opacity="0"/>'
        '<stop offset="32%" stop-color="#2DD4BF" stop-opacity="0.55"/>'
        '<stop offset="68%" stop-color="#38BDF8" stop-opacity="0.55"/>'
        '<stop offset="100%" stop-color="#818CF8" stop-opacity="0"/>'
        '</linearGradient>'
        '<linearGradient id="arcGrad2" x1="0%" y1="50%" x2="100%" y2="50%">'
        '<stop offset="0%" stop-color="#38BDF8" stop-opacity="0"/>'
        '<stop offset="50%" stop-color="#5EEAD4" stop-opacity="0.32"/>'
        '<stop offset="100%" stop-color="#38BDF8" stop-opacity="0"/>'
        '</linearGradient>'
        '</defs>'
        '<path class="arc-path arc-1" d="M 40 250 Q 580 -35 1120 250" stroke="url(#arcGrad1)" stroke-width="1.4"/>'
        '<path class="arc-path arc-2" d="M 120 268 Q 580 28 1040 268" stroke="url(#arcGrad2)" stroke-width="1" stroke-dasharray="5 9"/>'
        '<circle class="orbit-spark s1" cx="310" cy="142" r="3" fill="#5EEAD4"/>'
        '<circle class="orbit-spark s2" cx="850" cy="142" r="2.6" fill="#38BDF8"/>'
        '<circle class="orbit-spark s3" cx="580" cy="108" r="2.2" fill="#A5B4FC"/>'
        '</svg>'
        '<div class="hero-inner">'
        '<div class="hero-kicker"><i class="kicker-dot"></i><span>CENTRO DE ALERTAS · MÉXICO &amp; LATAM</span></div>'
        '<h1 class="hero-title">De tu PDF al mensaje<br><span class="hero-gradient">Simple. Instantáneo.</span></h1>'
        '<p class="hero-sub">Convierte tus reportes de cobranza y entregado de Power BI en capturas HD, saludo del día y mensajes listos para WhatsApp.</p>'
        '<div class="hero-chips">'
        f'<span class="hero-chip">{icon("zap", 14)} Recuperación y Trámites</span>'
        f'<span class="hero-chip">{icon("globe", 14)} México + 6 países LATAM</span>'
        f'<span class="hero-chip">{icon("check_double", 14)} Saludo, imagen y texto</span>'
        '</div>'
        '</div>'
        '</header>'
    )


def workflow(loaded: int, generated: bool) -> None:
    s1 = "done" if loaded else "active"
    s2 = "done" if generated else ("active" if loaded else "pending")
    s3 = "active" if generated else "pending"
    c1 = "lit" if loaded else "flow"
    c2 = "lit" if generated else ("flow" if loaded else "dim")

    def _node(num: str, state: str, ico: str, title: str, sub: str) -> str:
        glyph = icon("check", 16) if state == "done" else icon(ico, 16)
        return (
            f'<div class="flow-node {state}">'
            f'<span class="flow-ico">{glyph}</span>'
            '<div class="flow-txt">'
            f'<span class="flow-num">PASO {num}</span>'
            f'<strong>{title}</strong>'
            f'<small>{sub}</small>'
            '</div>'
            '</div>'
        )

    put(
        '<div class="flow-rail anim-reveal" style="--delay:120ms">'
        + _node("01", s1, "upload", "Carga tus PDF", "México, LATAM o ambos")
        + f'<div class="flow-conduit {c1}" aria-hidden="true"><span class="conduit-pulse"></span></div>'
        + _node("02", s2, "spark", "Genera alertas", "Saludo, recuperación y trámites")
        + f'<div class="flow-conduit {c2}" aria-hidden="true"><span class="conduit-pulse"></span></div>'
        + _node("03", s3, "send", "Comparte", "Copia directo a WhatsApp")
        + '</div>'
    )


def section(anchor: str, title: str, subtitle: str, name: str) -> None:
    put(
        f'<div class="section-header anim-reveal" id="{anchor}" style="--delay:150ms">'
        f'<span class="section-badge-ico">{icon(name, 18)}</span>'
        '<div class="section-meta">'
        f'<h2>{title}</h2>'
        f'<p>{subtitle}</p>'
        '</div>'
        '<span class="section-rule" aria-hidden="true"></span>'
        '</div>'
    )


def upload_heading(region: str, title: str, description: str, scope: list[str]) -> None:
    color = "teal" if region == "mexico" else "blue"
    badge = "NACIONAL" if region == "mexico" else "REGIONAL"
    lead_ico = "file" if region == "mexico" else "globe"
    pills = "".join(
        f'<span class="country-pill">{flag_svg(country, 15)}<span>{escape(country)}</span></span>'
        for country in scope
    )
    put(
        '<div class="portal-head">'
        f'<div class="portal-orb {color}">{icon(lead_ico, 22)}</div>'
        f'<span class="portal-tag-pill {color}"><i class="pt-dot"></i>{badge}</span>'
        '</div>'
        f'<h3 class="portal-title">{escape(title)}</h3>'
        f'<p class="portal-desc">{escape(description)}</p>'
        f'<div class="scope-pills">{pills}</div>'
    )


def file_status(source: tuple[str, bytes] | None) -> None:
    if source:
        name, data = source
        size = f"{len(data) / 1024 / 1024:.1f} MB" if len(data) >= 1024 * 1024 else f"{len(data) / 1024:.0f} KB"
        put(
            '<div class="file-state ready">'
            f'<span class="state-ico">{icon("check", 13)}</span>'
            f'<span class="state-name" title="{escape(name, quote=True)}">{escape(name)}</span>'
            f'<b class="state-meta">{size}</b>'
            '</div>'
        )
    else:
        put(
            '<div class="file-state">'
            f'<span class="state-ico">{icon("clock", 13)}</span>'
            '<span class="state-name">Esperando archivo PDF</span>'
            '<b class="state-meta">PDF · máx. 50 MB</b>'
            '</div>'
        )


def action_summary(loaded: int) -> None:
    if not loaded:
        cls = "idle"
        title = "Sube un reporte para comenzar"
        text = "Puedes cargar solo México, solo LATAM o ambos cortes al mismo tiempo."
    else:
        cls = "active"
        plural = "reporte listo para procesar" if loaded == 1 else "reportes listos para procesar"
        title = f"{loaded} {plural}"
        text = "Pulsa el botón para preparar el saludo, las capturas HD y las alertas de cada país."
    put(
        f'<div class="action-summary {cls}">'
        f'<span class="action-orb">{icon("spark", 22)}</span>'
        f'<div class="action-copy"><h3>{title}</h3><p>{text}</p></div>'
        '</div>'
    )


def empty_results(title: str, text: str) -> None:
    put(
        '<div class="empty-stage anim-reveal" style="--delay:180ms">'
        '<div class="empty-orbit" aria-hidden="true">'
        '<svg class="orbit-svg" viewBox="0 0 140 140" fill="none">'
        '<circle class="orbit-r1" cx="70" cy="70" r="62" stroke="url(#oG1)" stroke-width="1.2" stroke-dasharray="6 8"/>'
        '<circle class="orbit-r2" cx="70" cy="70" r="46" stroke="url(#oG2)" stroke-width="1.1" stroke-dasharray="3 6"/>'
        '<defs>'
        '<linearGradient id="oG1" x1="0" y1="0" x2="140" y2="140"><stop stop-color="#2DD4BF" stop-opacity="0.7"/><stop offset="1" stop-color="#38BDF8" stop-opacity="0.15"/></linearGradient>'
        '<linearGradient id="oG2" x1="140" y1="0" x2="0" y2="140"><stop stop-color="#818CF8" stop-opacity="0.6"/><stop offset="1" stop-color="#2DD4BF" stop-opacity="0.15"/></linearGradient>'
        '</defs>'
        '</svg>'
        f'<div class="empty-core">{icon("message", 26)}</div>'
        '</div>'
        f'<h3>{escape(title)}</h3>'
        f'<p>{escape(text)}</p>'
        '<div class="empty-chips">'
        f'<span>{icon("layers", 13)} Capturas Bottom / Top y Entregado</span>'
        f'<span>{icon("message", 13)} Saludo y vista WhatsApp</span>'
        f'<span>{icon("download", 13)} Paquete ZIP y TXT</span>'
        '</div>'
        '</div>'
    )


def results_summary(alertas: list[dict], cuts: list[str], files: int) -> None:
    tramites_cnt = sum(1 for a in alertas if a.get("tipo") == "tramites")
    recup_cnt = len(alertas) - tramites_cnt
    positivas = sum(1 for a in alertas if a.get("variacion_total", 0) > 0)
    negativas = sum(1 for a in alertas if a.get("variacion_total", 0) < 0)
    neutras = len(alertas) - positivas - negativas
    cuts_str = " · ".join(escape(c) for c in cuts) if cuts else "—"

    sub_alertas = (
        f"{recup_cnt} recuperación · {tramites_cnt} trámites"
        if tramites_cnt else "Listas para copiar y enviar"
    )

    chips = []
    if positivas:
        chips.append(f'<span class="bal-chip pos">{icon("trend_up", 13)} {positivas} al alza</span>')
    if negativas:
        chips.append(f'<span class="bal-chip neg">{icon("trend_down", 13)} {negativas} a la baja</span>')
    if neutras:
        chips.append(f'<span class="bal-chip neu">{icon("trend_flat", 13)} {neutras} estable</span>')
    balance_html = "".join(chips) or '<span class="bal-chip neu">Sin cambios</span>'

    put(
        '<div class="kpi-grid anim-reveal" style="--delay:80ms">'
        '<div class="kpi-card kpi-glow">'
        f'<div class="kpi-top"><span>ALERTAS GENERADAS</span><i class="kpi-ico teal">{icon("message", 15)}</i></div>'
        f'<strong class="kpi-val gradient">{len(alertas):02d}</strong>'
        f'<small>{sub_alertas}</small>'
        '</div>'
        '<div class="kpi-card">'
        f'<div class="kpi-top"><span>REPORTES LEÍDOS</span><i class="kpi-ico blue">{icon("file", 15)}</i></div>'
        f'<strong class="kpi-val">{files:02d}</strong>'
        '<small>México y / o LATAM</small>'
        '</div>'
        '<div class="kpi-card">'
        f'<div class="kpi-top"><span>{"CORTE DETECTADO" if len(cuts) == 1 else "CORTES DETECTADOS"}</span><i class="kpi-ico indigo">{icon("calendar", 15)}</i></div>'
        f'<strong class="kpi-val mono">{cuts_str}</strong>'
        '<small>Fecha extraída del PDF</small>'
        '</div>'
        '<div class="kpi-card">'
        f'<div class="kpi-top"><span>BALANCE DE TARJETAS</span><i class="kpi-ico amber">{icon("activity", 15)}</i></div>'
        f'<div class="balance-chips">{balance_html}</div>'
        '<small>Tendencia total detectada</small>'
        '</div>'
        '</div>'
    )


def whatsapp_hint() -> None:
    put(
        '<div class="whatsapp-ribbon anim-reveal" style="--delay:120ms">'
        f'<span class="wa-ico">{icon("send", 16)}</span>'
        '<div class="wa-copy">'
        '<strong>Flujo para WhatsApp</strong>'
        '<div class="wa-steps">'
        '<span><b>1</b> Envía el saludo</span>'
        f'{icon("arrow_right", 13)}'
        '<span><b>2</b> Copia la imagen</span>'
        f'{icon("arrow_right", 13)}'
        '<span><b>3</b> Pégala en el chat</span>'
        f'{icon("arrow_right", 13)}'
        '<span><b>4</b> Añade el texto</span>'
        '</div>'
        '</div>'
        '</div>'
    )


def footer() -> None:
    put(
        '<footer class="studio-footer">'
        '<div class="footer-left"><strong>DATA <span>/</span> Recuperación</strong><span class="f-sep">·</span><span>Procesamiento local seguro</span></div>'
        '<div class="footer-right">México + LATAM · Reportes que se convierten en acción</div>'
        '</footer>'
    )


def result_card(
    *,
    pais: str,
    corte: str,
    archivo: str,
    pagina: int | str,
    mensaje: str,
    imagen: str,
    variacion: str,
    tendencia: str,
    rotulo_variacion: str = "Variación en recuperación",
    rotulo_imagen: str = "IMAGEN DEL REPORTE · BOTTOM / TOP",
    alt: str | None = None,
    descarga: str | None = None,
    modo: str = "",
    region: str = "latam",
    index: int = 0,
) -> str:
    """Tarjeta interactiva de mensaje: recuperación, trámites (modo='tramites') o saludo (modo='saludo')."""
    template = (Path(__file__).parent / "assets" / "result_card.html").read_text(encoding="utf-8")
    trend_icons = {
        "positive": icon("trend_up", 15),
        "negative": icon("trend_down", 15),
        "neutral": icon("trend_flat", 15),
    }

    if modo == "saludo":
        region_class = "saludo"
        region_label = "SALUDO INICIAL"
        tipo_badge = ""
        emblem_html = f'<span class="saludo-ico">{icon("spark", 22)}</span>'
        delay_ms = 0
    else:
        region_class = "mexico" if region == "mexico" else "latam"
        region_label = "MÉXICO" if region == "mexico" else "LATAM"
        tipo_badge = '<span class="tipo-badge">TRÁMITES · ENTREGADO</span>' if modo == "tramites" else ""
        emblem_html = flag_svg(pais, 26)
        delay_ms = min(index * 80, 480)

    replacements = {
        "MODO": modo,
        "ROTULO_VAR": rotulo_variacion,
        "ROTULO_IMG": rotulo_imagen,
        "ALT": alt or f"Tablas Bottom y Top de {pais}",
        "DESCARGA": descarga or f"{pais}_reporte.png",
        "PAIS": pais,
        "CORTE": corte,
        "ARCHIVO": archivo,
        "PAGINA": pagina,
        "MENSAJE": mensaje,
        "IMAGEN": imagen,
        "VARIACION": variacion,
        "TENDENCIA": tendencia,
        "EMBLEM_HTML": emblem_html,
        "TREND_ICON": trend_icons.get(tendencia, trend_icons["neutral"]),
        "REGION_LABEL": region_label,
        "REGION_CLASS": region_class,
        "TIPO_BADGE": tipo_badge,
        "DELAY_MS": delay_ms,
    }
    for key, value in replacements.items():
        template = template.replace("__" + key + "__", str(value))
    return template
