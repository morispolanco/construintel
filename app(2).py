import os
import json
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List

import pandas as pd
import requests
import streamlit as st

APP_TITLE = "ConstruInteligencia"
DB_PATH = os.getenv("DB_PATH", "construinteligencia.db")
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Helpers
# -----------------------------

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            duration_days INTEGER NOT NULL DEFAULT 30,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(plan_id) REFERENCES plans(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_code TEXT,
            item_name TEXT NOT NULL,
            category TEXT,
            unit TEXT,
            quantity REAL NOT NULL DEFAULT 0,
            min_stock REAL DEFAULT 0,
            max_stock REAL DEFAULT 0,
            unit_cost REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            source_file TEXT,
            imported_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            mapping_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()

    # Seed default admin and plan if missing.
    now = datetime.utcnow().isoformat(timespec="seconds")
    admin_user = os.getenv("DEFAULT_ADMIN_USER", "admin")
    admin_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

    if not fetch_one("SELECT id FROM users WHERE username = ?", (admin_user,)):
        execute(
            "INSERT INTO users (username, password, full_name, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (admin_user, admin_pass, "Administrador", "admin", 1, now),
        )

    if not fetch_one("SELECT id FROM plans WHERE name = ?", ("Mensual",)):
        execute(
            "INSERT INTO plans (name, price, duration_days, created_at) VALUES (?, ?, ?, ?)",
            ("Mensual", 0, 30, now),
        )

    conn.close()


def execute(query: str, params: tuple = ()) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    conn.close()


def fetch_all(query: str, params: tuple = ()) -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_one(query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def today_str() -> str:
    return date.today().isoformat()


def add_days(start: str, days: int) -> str:
    dt = datetime.strptime(start, "%Y-%m-%d").date() + timedelta(days=days)
    return dt.isoformat()


def deactivate_expired_subscriptions() -> None:
    today = today_str()
    expired = fetch_all(
        """
        SELECT s.id AS sub_id, s.user_id
        FROM subscriptions s
        WHERE s.active = 1 AND s.end_date < ?
        """,
        (today,),
    )
    for row in expired:
        execute("UPDATE subscriptions SET active = 0 WHERE id = ?", (row["sub_id"],))
        execute("UPDATE users SET active = 0 WHERE id = ?", (row["user_id"],))


def ensure_session_defaults() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("username", None)
    st.session_state.setdefault("role", None)


def login(username: str, password: str) -> bool:
    user = fetch_one(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username.strip(), password),
    )
    if user and user["active"] == 1:
        st.session_state.authenticated = True
        st.session_state.user_id = user["id"]
        st.session_state.username = user["username"]
        st.session_state.role = user["role"]
        return True
    return False


def logout() -> None:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None


def openrouter_chat(messages: List[Dict[str, str]], temperature: float = 0.0, max_tokens: int = 500) -> str:
    api_key = st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
    if not api_key:
        return "Falta configurar OPENROUTER_API_KEY en secrets o variables de entorno."

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://streamlit.io"),
        "X-Title": APP_TITLE,
    }
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"Error consultando OpenRouter: {exc}"


def format_currency(value: float) -> str:
    return f"Q{value:,.2f}"


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    return fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))


def get_mapping_for_user(user_id: int) -> Dict[str, str]:
    row = fetch_one("SELECT mapping_json FROM inventory_mappings WHERE user_id = ?", (user_id,))
    if not row:
        return {}
    try:
        return json.loads(row["mapping_json"])
    except Exception:
        return {}


def save_mapping(user_id: int, mapping: Dict[str, str]) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    existing = fetch_one("SELECT id FROM inventory_mappings WHERE user_id = ?", (user_id,))
    if existing:
        execute(
            "UPDATE inventory_mappings SET mapping_json = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(mapping, ensure_ascii=False), now, user_id),
        )
    else:
        execute(
            "INSERT INTO inventory_mappings (user_id, mapping_json, updated_at) VALUES (?, ?, ?)",
            (user_id, json.dumps(mapping, ensure_ascii=False), now),
        )


def import_inventory_from_dataframe(df: pd.DataFrame, user_id: int, source_file: str) -> int:
    mapping = get_mapping_for_user(user_id)
    if not mapping:
        raise ValueError("No hay mapeo guardado para este usuario.")

    normalized = pd.DataFrame()
    normalized["item_code"] = df[mapping.get("item_code")].astype(str) if mapping.get("item_code") in df.columns else ""
    normalized["item_name"] = df[mapping.get("item_name")].astype(str) if mapping.get("item_name") in df.columns else ""
    normalized["category"] = df[mapping.get("category")].astype(str) if mapping.get("category") in df.columns else ""
    normalized["unit"] = df[mapping.get("unit")].astype(str) if mapping.get("unit") in df.columns else ""
    normalized["quantity"] = pd.to_numeric(df[mapping.get("quantity")], errors="coerce") if mapping.get("quantity") in df.columns else 0
    normalized["min_stock"] = pd.to_numeric(df[mapping.get("min_stock")], errors="coerce") if mapping.get("min_stock") in df.columns else 0
    normalized["max_stock"] = pd.to_numeric(df[mapping.get("max_stock")], errors="coerce") if mapping.get("max_stock") in df.columns else 0
    normalized["unit_cost"] = pd.to_numeric(df[mapping.get("unit_cost")], errors="coerce") if mapping.get("unit_cost") in df.columns else 0

    normalized = normalized.fillna(0)
    normalized["total_cost"] = normalized["quantity"] * normalized["unit_cost"]
    normalized["source_file"] = source_file
    normalized["imported_at"] = datetime.utcnow().isoformat(timespec="seconds")

    inserted = 0
    for _, row in normalized.iterrows():
        if not str(row["item_name"]).strip():
            continue
        execute(
            """
            INSERT INTO inventory (
                user_id, item_code, item_name, category, unit,
                quantity, min_stock, max_stock, unit_cost, total_cost,
                source_file, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                str(row["item_code"]),
                str(row["item_name"]),
                str(row["category"]),
                str(row["unit"]),
                float(row["quantity"]),
                float(row["min_stock"]),
                float(row["max_stock"]),
                float(row["unit_cost"]),
                float(row["total_cost"]),
                source_file,
                row["imported_at"],
            ),
        )
        inserted += 1
    return inserted


# -----------------------------
# UI
# -----------------------------

def render_brand() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem;}
        .hero-box {
            padding: 1.25rem 1.4rem;
            border-radius: 1rem;
            border: 1px solid rgba(120,120,120,.25);
            background: linear-gradient(135deg, rgba(30,30,30,.08), rgba(90,90,90,.04));
        }
        .small-muted {opacity:.75; font-size: .92rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_status() -> None:
    st.sidebar.markdown(f"### {APP_TITLE}")
    st.sidebar.caption("Guatemala | Constructoras | Inteligencia de mercado")
    if st.session_state.authenticated:
        st.sidebar.success(f"Sesión activa: {st.session_state.username}")
        st.sidebar.write(f"Rol: {st.session_state.role}")
        if st.sidebar.button("Cerrar sesión"):
            logout()
            st.rerun()
    else:
        st.sidebar.info("Acceso restringido")

    st.sidebar.divider()
    st.sidebar.caption("Estado de la app: activa")
    st.sidebar.caption("Health check interno: disponible")


def page_login() -> None:
    st.title("🏗️ ConstruInteligencia")
    st.subheader("Acceso a la plataforma")
    st.write("Inicia sesión para ver el panel de inteligencia, inventario y administración.")

    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Usuario")
    with col2:
        password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if login(username, password):
            st.success("Acceso concedido.")
            st.rerun()
        else:
            st.error("Credenciales inválidas o usuario desactivado.")

    with st.expander("Página de ventas"):
        st.markdown(
            """
            **ConstruInteligencia** ayuda a constructoras en Guatemala a:
            - ver señales de mercado,
            - monitorear precios,
            - controlar inventario,
            - recibir recomendaciones basadas en datos reales.
            """
        )


def page_dashboard() -> None:
    st.title("Panel de Inteligencia")
    st.caption("Resumen ejecutivo del mercado guatemalteco")

    inv = fetch_all(
        "SELECT COUNT(*) AS total_items, COALESCE(SUM(total_cost),0) AS total_cost FROM inventory WHERE user_id = ?",
        (st.session_state.user_id,),
    )[0]
    sub = fetch_one(
        """
        SELECT s.start_date, s.end_date, s.active, p.name AS plan_name
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.user_id = ?
        ORDER BY s.id DESC
        LIMIT 1
        """,
        (st.session_state.user_id,),
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Materiales cargados", f"{inv['total_items']}")
    c2.metric("Valor inventario", format_currency(float(inv["total_cost"])))
    if sub:
        c3.metric("Plan activo", sub["plan_name"])
    else:
        c3.metric("Plan activo", "Sin plan")

    st.divider()
    st.subheader("Alertas críticas")
    alerts = [
        "Sin datos suficientes para una alerta real: no se muestran supuestos.",
        "Se requiere información histórica verificada para activar predicciones.",
    ]
    for a in alerts:
        st.warning(a)

    st.subheader("Recomendación IA")
    if st.button("Generar recomendación basada en datos reales"):
        inventory_rows = fetch_all(
            "SELECT item_name, quantity, min_stock, unit_cost FROM inventory WHERE user_id = ? ORDER BY quantity ASC LIMIT 10",
            (st.session_state.user_id,),
        )
        context = "\n".join(
            [f"- {r['item_name']}: qty={r['quantity']}, min={r['min_stock']}, cost={r['unit_cost']}" for r in inventory_rows]
        ) or "No hay inventario cargado."

        prompt = (
            "Actúa como analista de mercado para constructoras en Guatemala. "
            "No inventes datos. Usa solo la información proporcionada. "
            "Si faltan datos, dilo explícitamente. Genera una recomendación breve y accionable.\n\n"
            f"Datos:\n{context}"
        )
        result = openrouter_chat(
            [
                {"role": "system", "content": "Responde con precisión, cero creatividad, sin alucinaciones y sin inventar datos."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=400,
        )
        st.info(result)


def page_inventory() -> None:
    st.title("Control de Inventario")
    st.caption("Carga archivos Excel con el formato que ya usa la empresa.")

    uploaded = st.file_uploader("Subir inventario Excel", type=["xlsx", "xls"])
    if uploaded is not None:
        try:
            df = pd.read_excel(uploaded)
            st.write("Vista previa del archivo:")
            st.dataframe(df.head(20), use_container_width=True)

            st.subheader("Mapeo de columnas")
            columns = ["-- Seleccionar --"] + list(df.columns)
            default_map = get_mapping_for_user(st.session_state.user_id)

            c1, c2, c3 = st.columns(3)
            with c1:
                item_code = st.selectbox("Código", columns, index=columns.index(default_map.get("item_code", "-- Seleccionar --")) if default_map.get("item_code") in columns else 0)
                item_name = st.selectbox("Nombre del producto", columns, index=columns.index(default_map.get("item_name", "-- Seleccionar --")) if default_map.get("item_name") in columns else 0)
                category = st.selectbox("Categoría", columns, index=columns.index(default_map.get("category", "-- Seleccionar --")) if default_map.get("category") in columns else 0)
            with c2:
                unit = st.selectbox("Unidad", columns, index=columns.index(default_map.get("unit", "-- Seleccionar --")) if default_map.get("unit") in columns else 0)
                quantity = st.selectbox("Cantidad", columns, index=columns.index(default_map.get("quantity", "-- Seleccionar --")) if default_map.get("quantity") in columns else 0)
                min_stock = st.selectbox("Stock mínimo", columns, index=columns.index(default_map.get("min_stock", "-- Seleccionar --")) if default_map.get("min_stock") in columns else 0)
            with c3:
                max_stock = st.selectbox("Stock máximo", columns, index=columns.index(default_map.get("max_stock", "-- Seleccionar --")) if default_map.get("max_stock") in columns else 0)
                unit_cost = st.selectbox("Costo unitario", columns, index=columns.index(default_map.get("unit_cost", "-- Seleccionar --")) if default_map.get("unit_cost") in columns else 0)

            mapping = {
                "item_code": None if item_code == "-- Seleccionar --" else item_code,
                "item_name": None if item_name == "-- Seleccionar --" else item_name,
                "category": None if category == "-- Seleccionar --" else category,
                "unit": None if unit == "-- Seleccionar --" else unit,
                "quantity": None if quantity == "-- Seleccionar --" else quantity,
                "min_stock": None if min_stock == "-- Seleccionar --" else min_stock,
                "max_stock": None if max_stock == "-- Seleccionar --" else max_stock,
                "unit_cost": None if unit_cost == "-- Seleccionar --" else unit_cost,
            }
            save_mapping(st.session_state.user_id, mapping)

            if st.button("Importar inventario"):
                count = import_inventory_from_dataframe(df, st.session_state.user_id, uploaded.name)
                st.success(f"Se importaron {count} filas de inventario.")
                st.rerun()
        except Exception as exc:
            st.error(f"No se pudo procesar el archivo: {exc}")

    st.divider()
    st.subheader("Inventario cargado")
    rows = fetch_all(
        "SELECT item_code, item_name, category, unit, quantity, min_stock, max_stock, unit_cost, total_cost FROM inventory WHERE user_id = ? ORDER BY imported_at DESC",
        (st.session_state.user_id,),
    )
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Todavía no hay inventario cargado.")


def page_admin() -> None:
    st.title("Panel Administrativo")
    st.caption("Administración de usuarios, planes y suscripciones")

    tab1, tab2, tab3 = st.tabs(["Usuarios", "Planes", "Suscripciones"])

    with tab1:
        st.subheader("Crear usuario")
        with st.form("create_user_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                username = st.text_input("Usuario")
            with c2:
                password = st.text_input("Contraseña", type="password")
            with c3:
                role = st.selectbox("Rol", ["user", "admin"])
            full_name = st.text_input("Nombre completo")
            submitted = st.form_submit_button("Crear")
            if submitted:
                if not username or not password:
                    st.error("Usuario y contraseña son obligatorios.")
                else:
                    try:
                        execute(
                            "INSERT INTO users (username, password, full_name, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (username.strip(), password, full_name, role, 1, datetime.utcnow().isoformat(timespec="seconds")),
                        )
                        st.success("Usuario creado.")
                    except Exception as exc:
                        st.error(f"No se pudo crear el usuario: {exc}")

        st.subheader("Usuarios existentes")
        users = fetch_all("SELECT id, username, full_name, role, active, created_at FROM users ORDER BY id DESC")
        if users:
            u_df = pd.DataFrame([dict(u) for u in users])
            st.dataframe(u_df, use_container_width=True)
            user_ids = {f"{u['username']} (ID {u['id']})": u['id'] for u in users}
            target = st.selectbox("Usuario a actualizar", list(user_ids.keys()))
            col_a, col_b = st.columns(2)
            with col_a:
                new_role = st.selectbox("Nuevo rol", ["user", "admin"], key="new_role_admin")
            with col_b:
                new_active = st.selectbox("Estado", ["Activo", "Desactivado"], key="new_status_admin")
            if st.button("Actualizar usuario"):
                uid = user_ids[target]
                execute("UPDATE users SET role = ?, active = ? WHERE id = ?", (new_role, 1 if new_active == "Activo" else 0, uid))
                st.success("Usuario actualizado.")
                st.rerun()
        else:
            st.info("No hay usuarios.")

    with tab2:
        st.subheader("Crear plan")
        with st.form("create_plan_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                plan_name = st.text_input("Nombre del plan")
                price = st.number_input("Precio", min_value=0.0, value=0.0, step=1.0)
            with c2:
                duration_days = st.number_input("Duración (días)", min_value=1, value=30, step=1)
            submitted = st.form_submit_button("Crear plan")
            if submitted:
                if not plan_name:
                    st.error("El nombre del plan es obligatorio.")
                else:
                    try:
                        execute(
                            "INSERT INTO plans (name, price, duration_days, created_at) VALUES (?, ?, ?, ?)",
                            (plan_name, price, int(duration_days), datetime.utcnow().isoformat(timespec="seconds")),
                        )
                        st.success("Plan creado.")
                    except Exception as exc:
                        st.error(f"No se pudo crear el plan: {exc}")

        plans = fetch_all("SELECT id, name, price, duration_days, created_at FROM plans ORDER BY id DESC")
        if plans:
            st.dataframe(pd.DataFrame([dict(p) for p in plans]), use_container_width=True)
        else:
            st.info("No hay planes creados.")

    with tab3:
        st.subheader("Asignar plan a usuario")
        users = fetch_all("SELECT id, username, active FROM users ORDER BY username ASC")
        plans = fetch_all("SELECT id, name, duration_days FROM plans ORDER BY name ASC")

        if users and plans:
            user_map = {f"{u['username']} (activo={u['active']})": u['id'] for u in users}
            plan_map = {f"{p['name']} ({p['duration_days']} días)": p for p in plans}
            c1, c2, c3 = st.columns(3)
            with c1:
                selected_user = st.selectbox("Usuario", list(user_map.keys()))
            with c2:
                selected_plan_key = st.selectbox("Plan", list(plan_map.keys()))
            with c3:
                start_dt = st.date_input("Fecha de inicio", value=date.today())

            if st.button("Asignar y activar"):
                uid = user_map[selected_user]
                plan = plan_map[selected_plan_key]
                end_dt = start_dt + timedelta(days=int(plan["duration_days"]))
                execute(
                    "INSERT INTO subscriptions (user_id, plan_id, start_date, end_date, active, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (uid, plan["id"], start_dt.isoformat(), end_dt.isoformat(), 1, st.session_state.user_id, datetime.utcnow().isoformat(timespec="seconds")),
                )
                execute("UPDATE users SET active = 1 WHERE id = ?", (uid,))
                st.success("Plan asignado y usuario activado.")
                st.rerun()

        st.divider()
        subs = fetch_all(
            """
            SELECT s.id, u.username, p.name AS plan_name, s.start_date, s.end_date, s.active
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            JOIN plans p ON p.id = s.plan_id
            ORDER BY s.id DESC
            """
        )
        if subs:
            st.dataframe(pd.DataFrame([dict(s) for s in subs]), use_container_width=True)
            sub_map = {f"ID {s['id']} - {s['username']} / {s['plan_name']}": s['id'] for s in subs}
            chosen = st.selectbox("Suscripción a modificar", list(sub_map.keys()))
            c1, c2 = st.columns(2)
            with c1:
                action = st.selectbox("Acción", ["Activar", "Desactivar"])
            with c2:
                if st.button("Aplicar acción"):
                    sub_id = sub_map[chosen]
                    sub = fetch_one("SELECT user_id FROM subscriptions WHERE id = ?", (sub_id,))
                    execute("UPDATE subscriptions SET active = ? WHERE id = ?", (1 if action == "Activar" else 0, sub_id))
                    execute("UPDATE users SET active = ? WHERE id = ?", (1 if action == "Activar" else 0, sub["user_id"]))
                    st.success("Suscripción actualizada.")
                    st.rerun()
        else:
            st.info("No hay suscripciones.")


def page_health() -> None:
    st.write("ok")
    st.stop()


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    init_db()
    deactivate_expired_subscriptions()
    ensure_session_defaults()
    render_brand()

    # Lightweight health mode for external uptime monitors.
    # Example: add a query parameter ?health=1 and use it in a monitor URL.
    qp = st.query_params
    health_value = qp.get("health")
    if isinstance(health_value, list):
        health_value = health_value[0] if health_value else None
    if health_value == "1":
        page_health()

    sidebar_status()

    if not st.session_state.authenticated:
        page_login()
        return

    pages = ["Dashboard", "Inventario", "Ventas", "IA"]
    if st.session_state.role == "admin":
        pages.append("Administración")

    choice = st.sidebar.radio("Navegación", pages)

    if choice == "Dashboard":
        page_dashboard()
    elif choice == "Inventario":
        page_inventory()
    elif choice == "Ventas":
        st.title("Página de ventas")
        st.markdown(
            """
            ### ConstruInteligencia para constructoras en Guatemala
            - Inteligencia de mercado real
            - Control de inventario adaptable a Excel
            - Alertas críticas
            - Panel administrativo de usuarios y planes
            - IA sin alucinaciones y con temperatura 0
            """
        )
    elif choice == "IA":
        st.title("Señales IA")
        user_prompt = st.text_area("Describe la consulta")
        if st.button("Analizar"):
            if not user_prompt.strip():
                st.warning("Escribe una consulta.")
            else:
                result = openrouter_chat(
                    [
                        {"role": "system", "content": "Eres un analista estricto. No inventes datos ni hagas suposiciones. Si faltan datos, dilo."},
                        {"role": "user", "content": user_prompt.strip()},
                    ],
                    temperature=0.0,
                    max_tokens=500,
                )
                st.write(result)
    elif choice == "Administración" and st.session_state.role == "admin":
        page_admin()
    else:
        st.error("No tienes acceso a esta sección.")


if __name__ == "__main__":
    main()
