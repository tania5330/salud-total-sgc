# ============================================================
# app.py — Entry point del Sistema Salud Total
# ============================================================
import streamlit as st
from config import APP_NAME, APP_VERSION
from database.connection import test_connection, init_db
from utils.auth import authenticate_user, create_token, decode_token

# ── Configuración global de la página ──────────────────────
st.set_page_config(
    page_title="Salud Total — SGC",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help":    None,
        "Report a bug": None,
        "About":       f"**{APP_NAME}** v{APP_VERSION}",
    }
)

# ── Cargar CSS responsivo ───────────────────────────────────
with open("assets/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ── Función de Login ────────────────────────────────────────
def render_login():
    """Pantalla de autenticación del sistema."""
    col_izq, col_centro, col_der = st.columns([1, 1.2, 1])
    with col_centro:
        st.markdown("""
            <div class="login-card">
                <div class="login-header">
                    <h1>🏥</h1>
                    <h2>Salud Total</h2>
                    <p>Sistema de Gestión Clínica</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("👤 Usuario", placeholder="Ingrese su usuario")
            password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingrese su contraseña")
            submitted = st.form_submit_button("🔐 Ingresar al Sistema", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Complete todos los campos.")
                return

            with st.spinner("Verificando credenciales..."):
                user = authenticate_user(username, password)

            if user:
                token = create_token(user["id"], user["username"],
                                     [r for r in (user["roles"] or []) if r])
                st.session_state.user  = user
                st.session_state.token = token
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")

        st.caption("© 2024 Clínica Salud Total — Acceso restringido al personal autorizado")


# ── Sidebar de navegación ───────────────────────────────────
def render_sidebar():
    with st.sidebar:
        user = st.session_state.get("user", {})
        roles = user.get("roles") or []
        nombre = f"{user.get('nombre','')} {user.get('apellido','')}"

        st.markdown(f"""
            <div class="user-info">
                <div class="user-avatar">👤</div>
                <div>
                    <strong>{nombre}</strong><br>
                    <small>{' | '.join(r for r in roles if r)}</small>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.divider()

        # Menú principal
        menu_items = {
            "🏠 Dashboard":           "dashboard",
            "👥 Pacientes":           "pacientes",
            "📅 Citas":               "citas",
            "🩺 Atención Clínica":    "clinica",
            "💰 Facturación":         "facturacion",
            "👨‍⚕️ Personal Médico":  "personal",
            "🔧 Mantenedores":        "mantenedores",
            "📄 Reportes":            "reportes",
            "👤 Usuarios":            "usuarios",
            "🔐 Seguridad / Logs":    "seguridad",
            "💾 Backup":              "backup",
        }

        # Filtrar por rol
        rol_menus = {
            "MEDICO":        ["dashboard","pacientes","citas","clinica","reportes"],
            "ENFERMERA":     ["dashboard","pacientes","citas","clinica"],
            "RECEPCIONISTA": ["dashboard","pacientes","citas","facturacion"],
            "CONTADOR":      ["dashboard","facturacion","reportes"],
            "ADMINISTRADOR": list(menu_items.values()),
        }
        allowed = set()
        for rol in roles:
            allowed |= set(rol_menus.get(rol, []))

        selected = st.session_state.get("page", "dashboard")
        for label, key in menu_items.items():
            if key in allowed:
                if st.button(label, key=f"nav_{key}",
                             use_container_width=True,
                             type="primary" if selected == key else "secondary"):
                    st.session_state.page = key
                    st.rerun()

        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# ── Router de páginas ────────────────────────────────────────
def render_page(page: str):
    """Enrutar a la página seleccionada, importando módulo bajo demanda."""
    routes = {
        "dashboard":   ("modules.dashboard.dashboard_ui",   "render_dashboard"),
        "pacientes":   ("modules.pacientes.pacientes_ui",   "render_pacientes"),
        "citas":       ("modules.citas.citas_ui",           "render_citas"),
        "clinica":     ("modules.clinica.clinica_ui",       "render_clinica"),
        "facturacion": ("modules.facturacion.facturacion_ui","render_facturacion"),
        "personal":    ("modules.personal.personal_ui",     "render_personal"),
        "mantenedores":("modules.mantenedores.mant_ui",     "render_mantenedores"),
        "reportes":    ("modules.reportes.reportes_ui",     "render_reportes"),
        "usuarios":    ("modules.usuarios.usuarios_ui",     "render_usuarios"),
        "seguridad":   ("modules.seguridad.seguridad_ui",   "render_seguridad"),
        "backup":      ("modules.backup.backup_ui",         "render_backup"),
    }
    if page not in routes:
        st.error("Página no encontrada.")
        return

    module_path, func_name = routes[page]
    import importlib
    mod  = importlib.import_module(module_path)
    func = getattr(mod, func_name)
    func()


# ── Main ────────────────────────────────────────────────────
def main():
    # Verificar conexión a BD al arrancar
    ok, err_msg = test_connection()
    if not ok:
        st.error("❌ No se pudo conectar a la base de datos. Verifique la configuración.")
        if err_msg:
            st.caption(f"Detalle: {err_msg}")
        with st.expander("Qué revisar"):
            st.markdown("""
            - **Ejecutando en local:** Cree un archivo `.env` con `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` y asegúrese de que PostgreSQL esté corriendo.
            - **En Streamlit Cloud:** En *Manage app → Settings → Secrets* defina `DATABASE_URL` (URL externa de Render) y `SECRET_KEY`.
            - **Render:** Use la **External Database URL** del panel de PostgreSQL (no la interna).
            """)
        st.stop()

    # Inicializar esquemas y tablas si aún no existen (sin mostrar mensaje de éxito)
    try:
        init_db()
    except Exception:
        st.error("❌ Error al inicializar la base de datos. Revise la configuración y los logs del servidor.")
        st.stop()

    # Estado de sesión inicial
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    # Flujo: login o app
    if "user" not in st.session_state or not st.session_state.user:
        render_login()
    else:
        render_sidebar()
        render_page(st.session_state.page)


if __name__ == "__main__":
    main()