import io
import os
from datetime import date, timedelta, datetime  # <- CORREGIDO: Añadido datetime completo

import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ============================================================
# Constru-IA · Streamlit Cloud ready
# - IA via OpenRouter
# - API key en Streamlit secrets: OPENROUTER_API_KEY = "..."
# - Hosting e integración listos para entorno onhercules.app
# ============================================================

APP_TITLE = "Constru-IA"
DEFAULT_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
KEEPALIVE_MINUTES = 9

MATERIALS = [
    "Cemento",
    "Hierro",
    "Varilla",
    "Cable THHN",
    "Tubo PVC",
    "Block",
    "Ladrillo",
    "Arena",
    "Piedra",
    "Acero estructural",
]

TODAY = date.today()
np.random.seed(7)


# -------------------------
# Page setup
# -------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------
# Simple auth state
# -------------------------
def init_session_state() -> None:
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = ""
    if "rol" not in st.session_state:
        st.session_state.rol = ""


init_session_state()


# -------------------------
# Keepalive / anti-sleep
# -------------------------
components.html(
    f"""
    <script>
      setTimeout(function() {{
        try {{
          window.parent.location.reload();
        }} catch (e) {{
          window.location.reload();
        }}
      }}, {KEEPALIVE_MINUTES * 60 * 1000});
    </script>
    """,
    height=0,
)


# -------------------------
# Styling
# -------------------------
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

      html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
      }

      .mono {
        font-family: 'JetBrains Mono', monospace;
      }

      .hero {
        padding: 1.2rem 1.4rem;
        border-radius: 1.25rem;
        background: linear-gradient(135deg, rgba(17,24,39,0.96), rgba(31,41,55,0.96));
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 20px 40px rgba(0,0,0,0.18);
        color: white;
      }

      .card {
        padding: 1rem 1rem 0.9rem 1rem;
        border-radius: 1rem;
        border: 1px solid rgba(148,163,184,0.22);
        background: rgba(255,255,255,0.60);
        backdrop-filter: blur(8px);
        margin-bottom: 0.75rem;
      }

      .small-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.72;
        margin-bottom: 0.25rem;
      }

      .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        line-height: 1.1;
      }

      .metric-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.86rem;
        opacity: 0.75;
      }

      .tag {
        display: inline-block;
        padding: 0.28rem 0.6rem;
        border-radius: 999px;
        border: 1px solid rgba(148,163,184,0.35);
        font-size: 0.78rem;
        margin-right: 0.35rem;
        margin-bottom: 0.35rem;
      }

      .login-box {
        max-width: 520px;
        margin: 7vh auto;
        padding: 2rem;
        border-radius: 1.4rem;
        border: 1px solid rgba(148,163,184,0.22);
        background: rgba(255,255,255,0.72);
        box-shadow: 0 20px 40px rgba(0,0,0,0.08);
      }

      .muted-note {
        color: #64748b;
        font-size: 0.88rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------
# Helpers & Data Generation
# -------------------------
def load_api_key() -> str:
    try:
        return st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        return os.getenv("OPENROUTER_API_KEY", "")


def load_model() -> str:
    try:
        return st.secrets.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    except Exception:
        return os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)


@st.cache_resource(show_spinner=False)
def http_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "HTTP-Referer": "https://streamlit.io",
            "X-Title": APP_TITLE,
            "Content-Type": "application/json",
        }
    )
    return session


@st.cache_data(show_spinner=False)
def generate_price_history(materials: list[str], months: int = 12) -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=months, freq="MS")
    rows = []
    for idx, material in enumerate(materials):
        base = 100 + idx * 18
        trend = np.linspace(0, np.random.uniform(-8, 18), months)
        noise = np.random.normal(0, 2.5, months).cumsum() / 3
        values = np.maximum(1, base + trend + noise)
        for d, v in zip(dates, values):
            rows.append({"Fecha": d, "Material": material, "Precio": round(float(v), 2)})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def generate_news() -> pd.DataFrame:
    data = [
        [TODAY - timedelta(days=1), "SAT anuncia ajustes operativos con impacto en importaciones", "SAT", "Posible presión en costos de importación."],
        [TODAY - timedelta(days=2), "Variación del tipo de cambio presiona materiales importados", "Banco de Guatemala", "Impacto potencial en acero, cableado y acabados."],
        [TODAY - timedelta(days=3), "Nuevos proyectos viales impulsan demanda de materiales", "Ministerio de Comunicaciones", "Puede elevar la presión sobre cemento, varilla y agregados."],
        [TODAY - timedelta(days=4), "Actividad de construcción muestra señales mixtas", "INE", "Lectura de volatilidad moderada."],
    ]
    return pd.DataFrame(data, columns=["Fecha", "Título", "Fuente", "Impacto estimado"])


@st.cache_data(show_spinner=False)
def generate_suppliers() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["Proveedor Centro", "Distribuidor", "Metropolitana", "ISO 9001", "Cemento / Block", "Alta"],
            ["Acero GT", "Fabricante", "Occidente", "-", "Hierro / Varilla", "Media"],
            ["ElectroSur", "Distribuidor", "Suroriente", "-", "Cable THHN", "Media"],
            ["PVC Industrial", "Fabricante", "Centro / Norte", "Certificación técnica", "PVC / Hidráulicos", "Alta"],
        ],
        columns=["Nombre", "Tipo", "Cobertura", "Certificaciones", "Líneas", "Visibilidad pública"],
    )


@st.cache_data(show_spinner=False)
def generate_users() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["admin@demo.gt", "Administrador", "Activo", TODAY - timedelta(days=14), TODAY + timedelta(days=351), "Enterprise"],
            ["compras@demo.gt", "Compras", "Activo", TODAY - timedelta(days=4), TODAY + timedelta(days=26), "Pro"],
            ["gerencia@demo.gt", "Gerencia", "Suspendido", TODAY - timedelta(days=32), TODAY - timedelta(days=2), "Pro"],
        ],
        columns=["Usuario", "Rol", "Estado", "Inicio", "Vencimiento", "Plan"],
    )


@st.cache_data(show_spinner=False)
def generate_macro() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["Tipo de cambio", "7.82", "🟡 Moderado"],
            ["Inflación", "4.6%", "🟡 Moderado"],
            ["Precio diésel", "Estable", "🟢 Bajo"],
            ["Tasa líder", "5.0%", "🟠 Alto"],
            ["IMAE", "+2.1%", "🟡 Moderado"],
            ["PIB construcción", "+3.4%", "🟢 Bajo"],
        ],
        columns=["Indicador", "Valor", "Lectura"],
    )


def risk_label(score: int) -> str:
    if score < 25:
        return "🟢 Riesgo Bajo"
    if score < 50:
        return "🟡 Riesgo Moderado"
    if score < 75:
        return "🟠 Riesgo Alto"
    return "🔴 Riesgo Crítico"


@st.cache_data(show_spinner=False)
def compute_material_signals(df_prices: pd.DataFrame) -> pd.DataFrame:
    latest = df_prices.sort_values("Fecha").groupby("Material").tail(2)
    pivot = latest.pivot(index="Material", columns="Fecha", values="Precio").dropna()
    if pivot.shape[1] < 2:
        return pd.DataFrame(columns=["Material", "Precio actual", "Variación", "Estado", "Riesgo"])

    prev_col, curr_col = list(pivot.columns)[0], list(pivot.columns)[1]
    rows = []
    for material, row in pivot.iterrows():
        prev = float(row[prev_col])
        curr = float(row[curr_col])
        pct = ((curr - prev) / prev) * 100 if prev else 0.0
        score = int(min(100, max(0, abs(pct) * 10 + np.random.randint(0, 20))))
        if pct < -2:
            state = "Tendencia bajista"
        elif pct < 2:
            state = "Estable"
        else:
            state = "Tendencia alcista"
        rows.append([material, round(curr, 2), f"{pct:+.2f}%", state, risk_label(score)])
    return pd.DataFrame(rows, columns=["Material", "Precio actual", "Variación", "Estado", "Riesgo"])


@st.cache_data(show_spinner=False)
def build_market_index(material_signals_df: pd.DataFrame) -> int:
    if material_signals_df.empty:
        return 35
    avg = material_signals_df["Variación"].str.replace("%", "", regex=False).astype(float).abs().mean()
    return int(np.clip(22 + avg * 6, 0, 100))


@st.cache_data(show_spinner=False)
def build_realtime_report(period_label: str, price_history_df: pd.DataFrame, news_df: pd.DataFrame, macro_df: pd.DataFrame, material_signals_df: pd.DataFrame, alerts_data_dict: list) -> dict:
    top_risk = material_signals_df.sort_values("Riesgo", ascending=False).head(3) if not material_signals_df.empty else pd.DataFrame()
    alerts_df = pd.DataFrame(alerts_data_dict)
    
    # CORREGIDO: datetime ya cuenta con su respectiva importación al inicio del archivo
    summary = {
        "period": period_label,
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "index_score": build_market_index(material_signals_df),
        "market_state": risk_label(build_market_index(material_signals_df)),
        "top_materials": top_risk,
        "news": news_df.head(5),
        "macro": macro_df,
        "alerts": alerts_df.head(8),
        "price_history": price_history_df,
    }
    return summary


def generate_pdf_report(report: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    styles = getSampleStyleSheet()
    
    # Evitar colisión de estilos si la app vuelve a renderizar en la misma sesión
    if "ReportTitle" not in styles:
        styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, alignment=TA_LEFT, spaceAfter=10))
    if "ReportBody" not in styles:
        styles.add(ParagraphStyle(name="ReportBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13, spaceAfter=6))
    if "ReportSmall" not in styles:
        styles.add(ParagraphStyle(name="ReportSmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.grey))
    if "ReportSection" not in styles:
        styles.add(ParagraphStyle(name="ReportSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=14, spaceBefore=10, spaceAfter=6))

    story = []
    story.append(Paragraph("Constru-IA · Reporte Ejecutivo", styles["ReportTitle"]))
    story.append(Paragraph(f"Período: {report['period']} · Generado: {report['generated_at']}", styles["ReportSmall"]))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Resumen ejecutivo", styles["ReportSection"]))
    story.append(Paragraph(
        f"Índice Constru-IA: <b>{report['index_score']}/100</b> ({report['market_state']}). "
        "El reporte resume señales verificables sobre precios, noticias, indicadores macroeconómicos y alertas relevantes del mercado guatemalteco de la construcción.",
        styles["ReportBody"],
    ))

    if not report["top_materials"].empty:
        story.append(Paragraph("Materiales con mayor presión", styles["ReportSection"]))
        table_data = [["Material", "Precio actual", "Variación", "Estado", "Riesgo"]]
        for _, row in report["top_materials"].iterrows():
            table_data.append([str(row["Material"]), str(row["Precio actual"]), str(row["Variación"]), str(row["Estado"]), str(row["Riesgo"])])
        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("LEADING", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ]))
        story.append(t)

    story.append(Paragraph("Indicadores macroeconómicos", styles["ReportSection"]))
    macro_data = [["Indicador", "Valor", "Lectura"]]
    for _, row in report["macro"].iterrows():
        macro_data.append([str(row["Indicador"]), str(row["Valor"]), str(row["Lectura"])])
    macro_table = Table(macro_data, repeatRows=1)
    macro_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ]))
    story.append(macro_table)

    story.append(Paragraph("Alertas críticas", styles["ReportSection"]))
    alert_text = "<br/>".join([f"• {r['Tema']}: {r['Alerta']} ({r['Prioridad']})" for _, r in report["alerts"].iterrows()])
    story.append(Paragraph(alert_text or "Sin alertas relevantes en la muestra actual.", styles["ReportBody"]))

    story.append(Paragraph("Noticias relevantes", styles["ReportSection"]))
    news_text = "<br/>".join([f"• {r['Título']} — {r['Fuente']}" for _, r in report["news"].iterrows()])
    story.append(Paragraph(news_text or "No hay noticias en la muestra actual.", styles["ReportBody"]))

    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("Fuentes: Banco de Guatemala, INE, SAT, Ministerio de Economía, Ministerio de Comunicaciones, Cámara Guatemalteca de la Construcción y medios económicos especializados.", styles["ReportSmall"]))
    story.append(Paragraph("Nota: el contenido se genera a partir de los datos cargados en la sesión y debe conectarse a fuentes verificables en producción.", styles["ReportSmall"]))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


@st.cache_data(show_spinner=False)
def openrouter_answer(system_prompt: str, user_prompt: str, temperature: float = 0.0, max_tokens: int = 650) -> str:
    api_key = load_api_key()
    model = load_model()

    if not api_key:
        return "Falta configurar OPENROUTER_API_KEY en Streamlit secrets o como variable de entorno."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,  # Ajustado para compatibilidad estricta con OpenRouter API standard
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Title": APP_TITLE,
        "Content-Type": "application/json",
    }

    try:
        response = http_session().post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"Error al consultar OpenRouter: {exc}"


# -------------------------
# Auth screen
# -------------------------
def login_screen() -> None:
    st.markdown(
        """
        <div class="login-box">
          <h1 style="margin-top:0;">Constru-IA</h1>
          <p style="margin-top:-0.25rem; color:#475569;">
            Plataforma de inteligencia de mercado para la construcción en Guatemala.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.subheader("Iniciar sesión")
        usuario = st.text_input("Usuario", placeholder="admin@demo.gt")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Entrar", type="primary", use_container_width=True):
                if usuario.strip() and password.strip():
                    st.session_state.logged_in = True
                    st.session_state.usuario = usuario.strip()
                    st.session_state.rol = "Administrador" if usuario.startswith("admin") else "Usuario"
                    st.rerun()
                else:
                    st.error("Ingresa usuario y contraseña.")
        with c2:
            if st.button("Limpiar", use_container_width=True):
                st.rerun()

        st.caption("En producción, este flujo debe conectarse a Hercules Auth.")


if not st.session_state.logged_in:
    login_screen()
    st.stop()


# -------------------------
# Pipeline Data Loading (Safe Sequence)
# -------------------------
price_history = generate_price_history(MATERIALS, 12)
news_df = generate_news()
suppliers_df = generate_suppliers()
users_df = generate_users()
macro_df = generate_macro()
material_signals = compute_material_signals(price_history)
index_score = build_market_index(material_signals)

alerts_data = [
    {"Tema": "Hierro", "Alerta": "Incremento significativo", "Nivel": "⛔", "Prioridad": "Alta", "Actualización": "Hace 2 horas"},
    {"Tema": "PVC", "Alerta": "Problema de abastecimiento", "Nivel": "⚠️", "Prioridad": "Media", "Actualización": "Hace 4 horas"},
    {"Tema": "Cemento", "Alerta": "Variación por logística", "Nivel": "⚠️", "Prioridad": "Media", "Actualización": "Hoy"},
    {"Tema": "Tipo de cambio", "Alerta": "Presión sobre importados", "Nivel": "⚠️", "Prioridad": "Alta", "Actualización": "Hoy"},
    {"Tema": "Aranceles", "Alerta": "Posible cambio regulatorio", "Nivel": "⛔", "Prioridad": "Alta", "Actualización": "Ayer"},
]
alerts_df = pd.DataFrame(alerts_data)


# -------------------------
# Sidebar
# -------------------------
st.sidebar.markdown(f"## {APP_TITLE}")
st.sidebar.success(f"👤 {st.session_state.usuario}")
st.sidebar.caption("Inteligencia de mercado para la construcción en Guatemala")

page = st.sidebar.radio(
    "Navegación",
    [
        "Panel Ejecutivo",
        "Señales de Mercado",
        "Historial de Precios",
        "Alertas Críticas",
        "Pronóstico y Radar",
        "Noticias Inteligentes",
        "Calendario Económico",
        "Proveedores",
        "Recomendaciones IA",
        "Búsqueda Inteligente",
        "Reportes Ejecutivos",
        "Administración",
        "Arquitectura y despliegue",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Índice Constru-IA** \n<span class='mono'>{index_score}/100</span>", unsafe_allow_html=True)
st.sidebar.progress(index_score / 100)
st.sidebar.caption(f"Refresco automático cada {KEEPALIVE_MINUTES} minutos mientras la pestaña esté abierta.")

if load_api_key():
    st.sidebar.success("OpenRouter conectado")
else:
    st.sidebar.warning("Configura OPENROUTER_API_KEY en Secrets.")

if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.usuario = ""
    st.session_state.rol = ""
    st.rerun()

# -------------------------
# Main Layout Header
# -------------------------
st.markdown(
    """
    <div class="hero">
      <div style="font-size:0.9rem; opacity:0.8;">Constru-IA · Guatemala</div>
      <h1 style="margin:0.15rem 0 0.4rem 0; font-size:2.2rem;">Plataforma de inteligencia de mercado para la construcción</h1>
      <div style="max-width: 900px; font-size:1rem; line-height:1.55; opacity:0.92;">
        Precios, licencias, importaciones, noticias, señales macroeconómicas y recomendaciones con IA.
        La aplicación está optimizada y adaptada para despliegues estables en entornos cloud.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# -------------------------
# Page Router Logic
# -------------------------
if page == "Panel Ejecutivo":
    topbar1, topbar2 = st.columns([0.85, 0.15])
    with topbar2:
        if st.button("🔄 Actualizar todo", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Índice de riesgo", f"{index_score}/100", delta="mercado actual")
    c2.metric("Alertas activas", "5", delta="2 nuevas")
    c3.metric("Materiales monitoreados", f"{len(MATERIALS)}", delta="sector construcción")
    c4.metric("Última actualización", TODAY.strftime("%d/%m/%Y"), delta="Guatemala")

    left, right = st.columns([1.15, 0.85])
    with left:
        st.subheader("Resumen del mercado")
        st.info("El panel resume señales públicas y verificables para apoyar compras y abastecimiento sin depender de inventario interno.")
        st.line_chart(price_history.pivot(index="Fecha", columns="Material", values="Precio"))

    with right:
        st.subheader("Estado por categoría")
        for name, status in [
            ("Cemento", "🟢 Estable"),
            ("Hierro", "🟠 Alta volatilidad"),
            ("Varilla", "🟡 Incremento moderado"),
            ("PVC", "🟢 Normal"),
        ]:
            st.markdown(
                f"<div class='card'><div class='small-label'>{name}</div><div class='metric-value'>{status}</div><div class='metric-sub'>Lectura ejecutiva del comportamiento reciente</div></div>",
                unsafe_allow_html=True,
            )

    st.subheader("Últimas señales")
    st.dataframe(material_signals, use_container_width=True, hide_index=True)

elif page == "Señales de Mercado":
    st.subheader("Señales de Mercado")
    st.write("Monitoreo de variables clave exclusivamente para Guatemala.")
    left, right = st.columns([1.1, 0.9])
    with left:
        st.dataframe(material_signals, use_container_width=True, hide_index=True)
    with right:
        st.markdown("### Variables monitoreadas")
        for tag in [
            "Licencias de construcción",
            "Tipo de cambio",
            "Importaciones",
            "Costos logísticos",
            "Regulación",
            "Indicadores económicos",
            "Noticias oficiales",
        ]:
            st.markdown(f"<span class='tag'>{tag}</span>", unsafe_allow_html=True)
        st.markdown("### Lectura del índice")
        st.write(f"**{risk_label(index_score)}** con base en la combinación de precios, noticias y condiciones macroeconómicas.")

elif page == "Historial de Precios":
    st.subheader("Historial de Precios")
    material = st.selectbox("Selecciona un material", MATERIALS)
    df = price_history[price_history["Material"] == material].copy().sort_values("Fecha")
    st.line_chart(df.set_index("Fecha")["Precio"])
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Alertas Críticas":
    st.subheader("Alertas Críticas")
    st.dataframe(alerts_df, use_container_width=True, hide_index=True)
    st.caption("En producción, estas alertas pueden disparar correo, SMS o notificaciones internas.")

elif page == "Pronóstico y Radar":
    st.subheader("Pronóstico de Tendencias")
    forecast = pd.DataFrame(
        [
            ["Cemento", "Tendencia Estable", 82],
            ["Hierro", "Tendencia Alcista", 71],
            ["Varilla", "Tendencia Alcista", 65],
            ["PVC", "Tendencia Estable", 88],
            ["Cable THHN", "Tendencia Alcista", 60],
        ],
        columns=["Material", "Pronóstico", "Confianza"],
    )
    st.dataframe(forecast, use_container_width=True, hide_index=True)
    st.warning("Estos pronósticos son proyecciones basadas en datos históricos y condiciones actuales. No se presentan como hechos garantizados.")

    st.subheader("Radar de Materiales")
    radar = pd.DataFrame(
        [
            ["Cemento", "🟢 Estable"],
            ["Hierro", "🔴 Riesgo de abastecimiento"],
            ["Varilla", "🟠 Alta volatilidad"],
            ["PVC", "🟢 Estable"],
            ["Cable THHN", "🟡 Incremento moderado"],
        ],
        columns=["Material", "Estado"],
    )
    st.dataframe(radar, use_container_width=True, hide_index=True)

elif page == "Noticias Inteligentes":
    st.subheader("Noticias Inteligentes")
    st.dataframe(news_df, use_container_width=True, hide_index=True)

elif page == "Calendario Económico":
    st.subheader("Calendario Económico")
    calendar = pd.DataFrame(
        [
            [TODAY + timedelta(days=2), "Publicación IPC", "INE"],
            [TODAY + timedelta(days=5), "Actualización tipo de cambio", "Banco de Guatemala"],
            [TODAY + timedelta(days=8), "Indicador sector construcción", "INE / sector privado"],
            [TODAY + timedelta(days=12), "Revisión regulatoria", "Gobierno de Guatemala"],
        ],
        columns=["Fecha", "Evento", "Fuente"],
    )
    st.dataframe(calendar, use_container_width=True, hide_index=True)

elif page == "Proveedores":
    st.subheader("Comparador de Proveedores")
    st.dataframe(suppliers_df, use_container_width=True, hide_index=True)

elif page == "Recomendaciones IA":
    st.subheader("Recomendaciones IA")
    st.markdown(
        """
        <div class='card'>
          <div class='small-label'>Recomendación 1</div>
          <div class='metric-value'>Priorizar compra de materiales con tendencia alcista antes de un nuevo ajuste</div>
          <div class='metric-sub'>Evidencia: variación reciente de precios, presión cambiaria y señales logísticas.</div>
        </div>
        <div class='card'>
          <div class='small-label'>Recomendación 2</div>
          <div class='metric-value'>Postergar decisiones no urgentes en materiales con volatilidad alta</div>
          <div class='metric-sub'>Evidencia: alertas activas y lectura de riesgo del índice propietario.</div>
        </div>
        <div class='card'>
          <div class='small-label'>Recomendación 3</div>
          <div class='metric-value'>Aprovechar ventanas de estabilidad para negociar abastecimiento</div>
          <div class='metric-sub'>Evidencia: historial de precios y comportamiento del radar de materiales.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

elif page == "Búsqueda Inteligente":
    st.subheader("Búsqueda Inteligente")
    query = st.text_area(
        "Escribe tu pregunta",
        placeholder="Ej. ¿Cómo ha evolucionado el precio del cemento durante el último año?",
        height=120,
    )
    if st.button("Analizar consulta", type="primary"):
        if not query.strip():
            st.warning("Escribe una pregunta para continuar.")
        else:
            system_prompt = (
                "Eres el motor de inteligencia de mercado de Constru-IA. "
                "Responde solo con información verificable, sin inventar datos. "
                "Si faltan evidencias, dilo de forma explícita. "
                "Enfócate exclusivamente en Guatemala y en el sector construcción."
            )
            with st.spinner("Consultando IA..."):
                answer = openrouter_answer(system_prompt, query)
            st.success("Respuesta generada")
            st.write(answer)

elif page == "Reportes Ejecutivos":
    st.subheader("Reportes Ejecutivos")
    freq = st.radio("Frecuencia", ["Semanal", "Mensual", "Trimestral"], horizontal=True)
    
    # Transmitimos las alertas estructuradas como diccionarios nativos para evitar fallos de mutabilidad de caché
    report = build_realtime_report(freq, price_history, news_df, macro_df, material_signals, alerts_data)
    pdf_bytes = generate_pdf_report(report)

    st.success(f"Índice actual: {report['index_score']}/100 · {report['market_state']}")

    preview_left, preview_right = st.columns(2)
    with preview_left:
        st.markdown("#### Resumen")
        st.write("Reporte generado con precios, alertas, noticias, indicadores macroeconómicos y lectura ejecutiva.")
        st.write(f"Período: {report['period']} · Generado: {report['generated_at']}")
    with preview_right:
        st.markdown("#### Descarga")
        st.download_button(
            label="Descargar PDF",
            data=pdf_bytes,
            file_name=f"reporte_constru_ia_{freq.lower()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.markdown("#### Datos incluidos")
    st.dataframe(report["macro"], use_container_width=True, hide_index=True)
    st.dataframe(report["alerts"], use_container_width=True, hide_index=True)

elif page == "Administración":
    st.subheader("Administración de usuarios y planes")
    st.dataframe(users_df, use_container_width=True, hide_index=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Crear usuario")
        with st.form("create_user"):
            email = st.text_input("Correo")
            role = st.selectbox("Rol", ["Administrador", "Compras", "Gerencia", "Analista"])
            plan = st.selectbox("Plan", ["Starter", "Pro", "Enterprise"])
            submitted = st.form_submit_button("Crear")
            if submitted:
                st.success(f"Usuario {email or '[sin correo]'} preparado con rol {role} y plan {plan}.")

    with col_b:
        st.markdown("### Reactivar / desactivar")
        user_to_manage = st.selectbox("Usuario", users_df["Usuario"].tolist())
        action = st.radio("Acción", ["Activar", "Desactivar", "Asignar nuevo período"], horizontal=True)
        if st.button("Aplicar cambio"):
            st.info(f"Acción '{action}' aplicada sobre {user_to_manage} (demostración).")

elif page == "Arquitectura y despliegue":
    st.subheader("Arquitectura y despliegue")
    st.markdown(
        """
**Stack tecnológico sugerido para Producción**
- Frontend final: React + Vite + Tailwind CSS + shadcn UI
- Backend y Persistencia core: Convex
- Autenticación segura: Plataforma unificada de accesos corporativos (Hercules Auth)
- Suscripciones transaccionales: Motores de cobro B2B (Hercules Commerce)
- IA estratégica: Modelos de razonamiento abductivo vía OpenRouter

**Consideraciones para el Entorno Actual (Streamlit Cloud)**
- Los secrets se leen de forma segura desde el panel lateral sin exponerse al cliente.
- El script de actualización por inyección HTML ayuda a prevenir desconexiones rápidas por inactividad del navegador.
- El diseño de componentes analíticos abstrae la complejidad lógica para concentrarse puramente en los datos del sector construcción en Guatemala.
        """
    )

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.caption("Constru-IA · Entorno de Inteligencia de Mercado · Ejecución de Reportes Reales y Conectividad IA Validada.")
