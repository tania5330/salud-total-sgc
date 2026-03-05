# ============================================================
# modules/backup/backup_ui.py — Módulo de Backup y Restauración
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
import streamlit as st
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path
from database.connection import execute_query
from utils.auth import require_auth, has_any_role
from utils.audit_logger import log_action
from config import DB_CONFIG, BACKUP_DIR


def render_backup():
    """Renderizar módulo de backup y restauración de la base de datos."""
    require_auth()
    if not has_any_role("ADMINISTRADOR"):
        st.error("🔒 Acceso restringido. Solo Administradores pueden gestionar los backups.")
        return

    st.title("💾 Backup y Restauración")

    # Asegurar que el directorio de backups existe
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

    tab1, tab2, tab3 = st.tabs([
        "📦 Generar Backup",
        "📋 Historial de Backups",
        "⚙️ Configuración",
    ])

    with tab1: _render_generar_backup()
    with tab2: _render_historial_backup()
    with tab3: _render_configuracion_backup()


# ─────────────────────────────────────────────────────────────
# Generar Backup
# ─────────────────────────────────────────────────────────────

def _render_generar_backup():
    st.subheader("📦 Generar Backup Manual")

    col1, col2 = st.columns(2)
    with col1:
        tipo_backup = st.selectbox(
            "Tipo de Backup",
            ["Completo (esquemas + datos)", "Solo estructura (DDL)", "Solo datos"],
        )
    with col2:
        formato = st.selectbox("Formato", ["custom (.dump)", "plain SQL (.sql)"])

    include_schemas = st.multiselect(
        "Esquemas a incluir",
        ["clinica", "seguridad", "auditoria"],
        default=["clinica", "seguridad", "auditoria"],
    )

    st.info("""
    💡 **Información sobre el backup:**
    - El backup se genera usando `pg_dump` de PostgreSQL
    - El archivo se descargará automáticamente en su navegador
    - Los backups se almacenan también en el servidor en el directorio configurado
    """)

    if st.button("🚀 Iniciar Backup", type="primary", use_container_width=True):
        _ejecutar_backup(tipo_backup, formato, include_schemas)


def _ejecutar_backup(tipo: str, formato: str, schemas: list):
    """Ejecutar pg_dump y ofrecer descarga del archivo generado."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".dump" if "custom" in formato else ".sql"
    filename = f"backup_saludtotal_{timestamp}{ext}"
    filepath = os.path.join(BACKUP_DIR, filename)

    # Construir comando pg_dump
    cmd = [
        "pg_dump",
        f"--host={DB_CONFIG['host']}",
        f"--port={DB_CONFIG['port']}",
        f"--username={DB_CONFIG['user']}",
        f"--dbname={DB_CONFIG['database']}",
        "--no-password",
    ]

    if "custom" in formato:
        cmd += ["--format=custom", "--compress=9"]
    else:
        cmd += ["--format=plain"]

    if tipo == "Solo estructura (DDL)":
        cmd.append("--schema-only")
    elif tipo == "Solo datos":
        cmd.append("--data-only")

    for schema in schemas:
        cmd += [f"--schema={schema}"]

    cmd += [f"--file={filepath}"]

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_CONFIG["password"]

    with st.spinner(f"Generando backup '{filename}'..."):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env, timeout=300
            )

            if result.returncode == 0 and os.path.exists(filepath):
                size_bytes = os.path.getsize(filepath)
                size_str   = _format_size(size_bytes)

                # Registrar en metadatos de backup
                _registrar_backup_metadata(filename, tipo, size_str, "EXITOSO")

                st.success(f"✅ Backup generado exitosamente: **{filename}** ({size_str})")

                # Ofrecer descarga
                with open(filepath, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Descargar {filename}",
                        data=f.read(),
                        file_name=filename,
                        mime="application/octet-stream",
                        use_container_width=True,
                    )

                log_action("INSERT", "BACKUP", "backup", filename)
            else:
                error_msg = result.stderr or "Error desconocido"
                _registrar_backup_metadata(filename, tipo, "0 B", "FALLIDO")
                st.error(f"❌ Error al generar backup:\n```\n{error_msg}\n```")
                st.warning("Verifique que `pg_dump` esté instalado y las credenciales de la BD sean correctas.")

        except subprocess.TimeoutExpired:
            st.error("❌ Timeout: El backup tardó más de 5 minutos.")
        except FileNotFoundError:
            st.error("❌ `pg_dump` no encontrado. Instale PostgreSQL client tools.")
            # Fallback: backup en formato JSON con datos críticos
            _backup_json_fallback(timestamp)
        except Exception as e:
            st.error(f"❌ Error inesperado: {e}")


def _backup_json_fallback(timestamp: str):
    """Backup alternativo en JSON cuando pg_dump no está disponible."""
    st.warning("⚠️ Generando backup alternativo en JSON (datos principales)...")

    backup_data = {
        "timestamp": timestamp,
        "tipo": "JSON_FALLBACK",
        "tablas": {},
    }

    tablas_criticas = [
        ("clinica.pacientes", "SELECT id, dni, numero_hc, nombre, apellido_pat, fecha_nacimiento FROM clinica.pacientes WHERE activo=TRUE"),
        ("clinica.medicos",   "SELECT id, dni, cmp, nombre, apellido FROM clinica.medicos WHERE activo=TRUE"),
        ("seguridad.usuarios", "SELECT id, username, email, nombre, apellido FROM seguridad.usuarios WHERE activo=TRUE"),
    ]

    for tabla, query in tablas_criticas:
        try:
            rows = execute_query(query)
            # Convertir fechas a strings para JSON
            for r in rows:
                for k, v in r.items():
                    if hasattr(v, 'isoformat'):
                        r[k] = v.isoformat()
            backup_data["tablas"][tabla] = rows
        except Exception:
            backup_data["tablas"][tabla] = []

    json_str = json.dumps(backup_data, indent=2, default=str)
    filename = f"backup_json_{timestamp}.json"

    st.download_button(
        label=f"⬇️ Descargar Backup JSON — {filename}",
        data=json_str,
        file_name=filename,
        mime="application/json",
        use_container_width=True,
    )


def _registrar_backup_metadata(filename: str, tipo: str, size: str, estado: str):
    """Guardar metadata del backup en un archivo JSON local."""
    meta_file = os.path.join(BACKUP_DIR, "backup_history.json")
    historia = []

    if os.path.exists(meta_file):
        try:
            with open(meta_file) as f:
                historia = json.load(f)
        except Exception:
            historia = []

    historia.insert(0, {
        "filename":   filename,
        "tipo":       tipo,
        "size":       size,
        "estado":     estado,
        "fecha":      datetime.now().isoformat(),
        "usuario":    st.session_state.get("user", {}).get("username", "sistema"),
    })

    # Mantener solo los últimos 100 registros
    historia = historia[:100]

    try:
        with open(meta_file, "w") as f:
            json.dump(historia, f, indent=2)
    except Exception:
        pass  # No interrumpir si no puede escribir metadata


# ─────────────────────────────────────────────────────────────
# Historial de Backups
# ─────────────────────────────────────────────────────────────

def _render_historial_backup():
    st.subheader("📋 Historial de Backups")

    meta_file = os.path.join(BACKUP_DIR, "backup_history.json")

    if not os.path.exists(meta_file):
        st.info("No hay historial de backups registrado aún.")
        return

    try:
        with open(meta_file) as f:
            historia = json.load(f)
    except Exception:
        st.error("Error al leer el historial de backups.")
        return

    if not historia:
        st.info("El historial de backups está vacío.")
        return

    import pandas as pd
    df = pd.DataFrame(historia)
    df["estado"] = df["estado"].map(
        lambda x: "✅ Exitoso" if x == "EXITOSO" else "❌ Fallido"
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"📊 {len(historia)} backup(s) registrado(s)")

    # Listar archivos en disco
    st.divider()
    st.markdown("**Archivos disponibles en servidor:**")

    archivos = []
    for f in Path(BACKUP_DIR).iterdir():
        if f.is_file() and f.suffix in (".dump", ".sql", ".json") and f.name != "backup_history.json":
            archivos.append({
                "archivo": f.name,
                "tamaño":  _format_size(f.stat().st_size),
                "fecha":   datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })

    if archivos:
        archivos.sort(key=lambda x: x["fecha"], reverse=True)
        df_arch = pd.DataFrame(archivos)
        st.dataframe(df_arch, use_container_width=True, hide_index=True)

        # Descargar archivo existente
        st.divider()
        st.markdown("**Descargar backup existente:**")
        arch_sel = st.selectbox("Seleccionar archivo", [a["archivo"] for a in archivos])
        if st.button("⬇️ Descargar Archivo Seleccionado"):
            filepath = os.path.join(BACKUP_DIR, arch_sel)
            if os.path.exists(filepath):
                with open(filepath, "rb") as fh:
                    st.download_button(
                        "⬇️ Confirmar Descarga",
                        data=fh.read(),
                        file_name=arch_sel,
                        mime="application/octet-stream",
                        use_container_width=True,
                    )
    else:
        st.info("No hay archivos de backup en el servidor.")

    # Limpiar backups antiguos
    st.divider()
    dias_retener = st.number_input("Retener backups de los últimos N días", min_value=1, value=30)
    if st.button("🧹 Limpiar Backups Antiguos", type="secondary"):
        from datetime import timedelta
        limite = datetime.now() - timedelta(days=dias_retener)
        eliminados = 0
        for f in Path(BACKUP_DIR).iterdir():
            if f.is_file() and f.name != "backup_history.json":
                if datetime.fromtimestamp(f.stat().st_mtime) < limite:
                    f.unlink()
                    eliminados += 1
        st.success(f"✅ {eliminados} archivo(s) antiguo(s) eliminado(s).")
        st.rerun()


# ─────────────────────────────────────────────────────────────
# Configuración de Backup
# ─────────────────────────────────────────────────────────────

def _render_configuracion_backup():
    st.subheader("⚙️ Configuración de Backup Automático")

    st.info("""
    **Configuración del Backup Automático con Cron (Linux/macOS)**

    Para programar backups automáticos, ejecute en el servidor:

    ```bash
    crontab -e
    ```

    Luego agregue la siguiente línea para backup diario a las 2:00 AM:

    ```
    0 2 * * * PGPASSWORD=tu_password pg_dump -h localhost -U postgres -d salud_total -F custom -f /ruta/backups/backup_$(date +%Y%m%d).dump
    ```

    **Para Windows** use el Programador de Tareas con el siguiente comando:
    ```bat
    pg_dump -h localhost -U postgres -d salud_total -F custom -f "C:\\backups\\backup_%date%.dump"
    ```
    """)

    # Estado del directorio de backups
    st.divider()
    st.markdown("**Estado del Sistema de Backup:**")

    backup_path = Path(BACKUP_DIR)
    col1, col2, col3 = st.columns(3)

    with col1:
        existe = backup_path.exists()
        st.metric("Directorio", "✅ Existe" if existe else "❌ No existe")

    with col2:
        if existe:
            archivos = [f for f in backup_path.iterdir() if f.is_file() and f.name != "backup_history.json"]
            st.metric("Archivos de Backup", len(archivos))
        else:
            st.metric("Archivos de Backup", 0)

    with col3:
        if existe:
            total_size = sum(f.stat().st_size for f in backup_path.iterdir() if f.is_file())
            st.metric("Espacio Utilizado", _format_size(total_size))
        else:
            st.metric("Espacio Utilizado", "0 B")

    # Configuración desde parámetros del sistema
    st.divider()
    st.markdown("**Parámetros de Backup en Base de Datos:**")
    params = execute_query("""
        SELECT clave, valor, descripcion FROM clinica.parametros_sistema
        WHERE clave LIKE 'BACKUP_%'
        ORDER BY clave
    """)
    if params:
        import pandas as pd
        st.dataframe(pd.DataFrame(params), use_container_width=True, hide_index=True)

    # Crear directorio si no existe
    if not backup_path.exists():
        if st.button("📁 Crear Directorio de Backups"):
            backup_path.mkdir(parents=True, exist_ok=True)
            st.success(f"✅ Directorio creado en: {BACKUP_DIR}")
            st.rerun()


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _format_size(bytes_size: int) -> str:
    """Convertir tamaño en bytes a formato legible."""
    if bytes_size == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"
