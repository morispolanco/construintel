import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# ConstruInteligencia · Streamlit Cloud ready
# - Uses OpenRouter model:
#   nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
# - API key must be stored in Streamlit secrets:
#   OPENROUTER_API_KEY = "..."
# ============================================================

st.set_page_config(
    page_title="ConstruInteligencia",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# Config
# -------------------------
OPENROUTER_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
APP_TITLE = "ConstruInteligencia"
KEEPALIVE_MINUTES = 9  # browser-side refresh while tab remains open

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

SOURCE_SET = [
    "Banco de Guatemala",
    "Instituto Nacional de Estadística",
    "SAT",
    "Ministerio de Economía",
    "Ministerio de Comunicaciones",
    "Cámara Guatemalteca de la Construcción",
    "Diario de Centro América",
    "Medios económicos especializados",
]

TODAY = date.today()
np.random.seed(7)


# -------------------------
# Anti-sleep / keep-alive
# -------------------------
# This helps keep an active browser tab refreshing periodically.
# It cannot guarantee that a cloud host will never hibernate the backend.
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

      .muted-note {
        color: #64748b;
        font-size: 0.88rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------
# Helpers
# -------------------------

def load_api_key() -> str:
    """Prefer Streamlit secrets, then environment variable."""
    try:
        return st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        return os.getenv("OPENROUTER_API_KEY", "")


@st.cache_resource(show_spinner=False)
def http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "HTTP-Referer": "https://streamlit.io",
        "X-Title": APP_TITLE,
        "Content-Type": "application/json",
    })
    return s


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
def build_market_index(material_signals: pd.DataFrame) -> int:
    if material_signals.empty:
        return 35
    avg = material_signals["Variación"].str.replace("%", "", regex=False).astype(float).abs().mean()
    return int(np.clip(22 + avg * 6, 0, 100))


@st.cache_data(show_spinner=False)
def openrouter_answer(system_prompt: str, user_prompt: str, temperature: float = 0.0, max_tokens: int = 650) -> str:
    api_key = load_api_key()
    if not api_key:
        return "Falta configurar OPENROUTER_API_KEY en Streamlit secrets o como variable de entorno."

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "reasoning": {"enabled": True},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-OpenRouter-Metadata": "enabled",
    }

    try:
        response = http_session().post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"Error al consultar OpenRouter: {exc}"


# -------------------------
# Data
# -------------------------
price_history = generate_price_history(MATERIALS, 12)
news_df = generate_news()
suppliers_df = generate_suppliers()
users_df = generate_users()
macro_df = generate_macro()
material_signals = compute_material_signals(price_history)
index_score = build_market_index(material_signals)


# -------------------------
# Sidebar
# -------------------------
st.sidebar.markdown(f"## {APP_TITLE}")
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
st.sidebar.markdown(f"**Índice ConstruInteligencia**  \n<span class='mono'>{index_score}/100</span>", unsafe_allow_html=True)
st.sidebar.progress(index_score / 100)
st.sidebar.caption(
    f"Keepalive del navegador: refresco cada {KEEPALIVE_MINUTES} minutos mientras la pestaña siga abierta."
)

if load_api_key():
    st.sidebar.success(f"OpenRouter listo · {OPENROUTER_MODEL}")
else:
    st.sidebar.warning("Configura OPENROUTER_API_KEY en Secrets.")

# -------------------------
# Header
# -------------------------
st.markdown(
    """
    <div class="hero">
      <div style="font-size:0.9rem; opacity:0.8;">ConstruInteligencia · Guatemala</div>
      <h1 style="margin:0.15rem 0 0.4rem 0; font-size:2.2rem;">Plataforma de inteligencia de mercado para la construcción</h1>
      <div style="max-width: 900px; font-size:1rem; line-height:1.55; opacity:0.92;">
        Precios, licencias, importaciones, noticias, señales macroeconómicas y recomendaciones con IA.
        El modelo está conectado por OpenRouter y la configuración está pensada para Streamlit Cloud.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# -------------------------
# Pages
# -------------------------
if page == "Panel Ejecutivo":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Índice de riesgo", f"{index_score}/100", delta="mercado actual")
    c2.metric("Alertas activas", "7", delta="2 nuevas")
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
    alerts = pd.DataFrame(
        [
            ["Hierro", "Incremento significativo", "⛔", "Alta", "Hace 2 horas"],
            ["PVC", "Problema de abastecimiento", "⚠️", "Media", "Hace 4 horas"],
            ["Cemento", "Variación por logística", "⚠️", "Media", "Hoy"],
            ["Tipo de cambio", "Presión sobre importados", "⚠️", "Alta", "Hoy"],
            ["Aranceles", "Posible cambio regulatorio", "⛔", "Alta", "Ayer"],
        ],
        columns=["Tema", "Alerta", "Nivel", "Prioridad", "Actualización"],
    )
    st.dataframe(alerts, use_container_width=True, hide_index=True)
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
    st.caption("Resumen diario con lectura del posible impacto para el sector construcción.")

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
    st.caption("Solo información pública, sin precios privados ni datos confidenciales.")

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
    st.info("La IA solo emite conclusiones cuando existe evidencia suficiente.")

elif page == "Búsqueda Inteligente":
    st.subheader("Búsqueda Inteligente")
    st.caption(f"Motor conversacional con el modelo {OPENROUTER_MODEL}.")
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
                "Eres el motor de inteligencia de mercado de ConstruInteligencia. "
                "Responde solo con información verificable, sin inventar datos. "
                "Si faltan evidencias, dilo de forma explícita. "
                "No reveles razonamiento interno. "
                "Enfócate exclusivamente en Guatemala y en el sector construcción."
            )
            with st.spinner("Consultando OpenRouter..."):
                answer = openrouter_answer(system_prompt, query)
            st.success("Respuesta generada")
            st.write(answer)
            st.caption("La respuesta se genera mediante OpenRouter y el modelo configurado en Secrets.")

elif page == "Reportes Ejecutivos":
    st.subheader("Reportes Ejecutivos")
    freq = st.radio("Frecuencia", ["Semanal", "Mensual", "Trimestral"], horizontal=True)
    st.write(f"Generación automática de reporte {freq.lower()} con resumen ejecutivo, alertas, tendencias y fuentes.")
    st.download_button(
        label="Descargar reporte de ejemplo",
        data="Reporte ejecutivo de ConstruInteligencia - versión demo",
        file_name="reporte_construinteligencia.txt",
        mime="text/plain",
    )

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

    st.caption("La lógica real debe conectarse a Convex, Hercules Auth y Hercules Commerce.")

elif page == "Arquitectura y despliegue":
    st.subheader("Arquitectura y despliegue")
    st.markdown(
        f"""
**Stack tecnológico**
- Frontend: React + Vite + Tailwind CSS + shadcn UI
- Backend y base de datos: Convex
- Autenticación: Hercules Auth
- Pagos y suscripciones: Hercules Commerce
- IA: OpenRouter con `{OPENROUTER_MODEL}`

**OpenRouter**
- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Autenticación: `Authorization: Bearer <OPENROUTER_API_KEY>`
- El modelo se llama exactamente `{OPENROUTER_MODEL}`.
- OpenRouter documenta compatibilidad con la API estilo OpenAI.

**Streamlit Cloud**
- Guarda la API key en `Secrets`.
- Usa `st.secrets["OPENROUTER_API_KEY"]`.
- El refresco automático del navegador ayuda mientras la pestaña sigue abierta.
- Streamlit Community Cloud ofrece despliegue y administración en la nube con soporte de secretos.
        """
    )
    st.warning(
        "Nota importante: el anti-sleep incluido aquí es un refresco del navegador; no garantiza que el host nunca hiberne. Para producción 24/7 suele combinarse con un monitor externo de disponibilidad."
    )

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.caption(
    "ConstruInteligencia · Demo Streamlit Cloud · Mantén OPENROUTER_API_KEY en Secrets y despliega el archivo como `streamlit_app.py`."
)
