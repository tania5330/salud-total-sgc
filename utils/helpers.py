# ============================================================
# utils/helpers.py — Funciones auxiliares reutilizables
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
import streamlit as st
from datetime import date, datetime
from typing import Any, Optional
import pandas as pd


def calcular_edad(fecha_nacimiento: date) -> int:
    """Calcular edad en años a partir de la fecha de nacimiento."""
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - (
        (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )


def formatear_moneda(valor: float, simbolo: str = "S/") -> str:
    """Formatear un número como moneda con separadores de miles."""
    return f"{simbolo} {valor:,.2f}"


def formatear_fecha(fecha, formato: str = "%d/%m/%Y") -> str:
    """Formatear una fecha o datetime a string legible."""
    if not fecha:
        return "—"
    if isinstance(fecha, str):
        try:
            fecha = datetime.fromisoformat(fecha)
        except ValueError:
            return fecha
    return fecha.strftime(formato)


def paginar_dataframe(df: pd.DataFrame, page_size: int = 20, key: str = "page") -> pd.DataFrame:
    """
    Implementar paginación manual sobre un DataFrame.
    Retorna el slice de la página actual.
    """
    total = len(df)
    if total <= page_size:
        return df

    total_pages = (total - 1) // page_size + 1
    page_num = st.number_input(
        f"Página (1–{total_pages})", min_value=1, max_value=total_pages,
        value=1, key=f"pager_{key}"
    )
    st.caption(f"Mostrando {page_size} de {total} registros — Página {page_num}/{total_pages}")

    start = (page_num - 1) * page_size
    return df.iloc[start:start + page_size]


def mostrar_kpi_card(titulo: str, valor: Any, subtitulo: str = "",
                      color: str = "#1a5276", icono: str = "") -> None:
    """Renderizar una tarjeta KPI con estilo personalizado en Streamlit."""
    st.markdown(f"""
        <div style="
            background:white; border-radius:12px; padding:1rem;
            box-shadow:0 2px 8px rgba(0,0,0,0.07);
            border-left:4px solid {color}; margin-bottom:0.5rem;
        ">
            <div style="font-size:0.8rem;color:#7f8c8d;font-weight:600;
                        text-transform:uppercase;letter-spacing:0.5px;">
                {icono} {titulo}
            </div>
            <div style="font-size:1.8rem;font-weight:700;color:{color};margin:4px 0;">
                {valor}
            </div>
            <div style="font-size:0.75rem;color:#95a5a6;">{subtitulo}</div>
        </div>
    """, unsafe_allow_html=True)


def confirmar_accion(mensaje: str, key: str) -> bool:
    """
    Mostrar checkbox de confirmación para acciones destructivas.
    Retorna True si el usuario confirma.
    """
    return st.checkbox(f"✅ {mensaje}", key=f"confirm_{key}")


def generar_numero_correlativo(prefijo: str, ultimo_num: int, padding: int = 6) -> str:
    """Generar número correlativo con prefijo y padding de ceros."""
    return f"{prefijo}{(ultimo_num + 1):0{padding}d}"


def estado_badge(estado: str) -> str:
    """Retornar HTML de badge de color según el estado."""
    colores = {
        "PROGRAMADA":  ("#3498db", "white"),
        "CONFIRMADA":  ("#27ae60", "white"),
        "ATENDIDA":    ("#2ecc71", "white"),
        "CANCELADA":   ("#e74c3c", "white"),
        "NO_SHOW":     ("#f39c12", "white"),
        "PENDIENTE":   ("#e67e22", "white"),
        "PAGADA":      ("#27ae60", "white"),
        "ANULADA":     ("#95a5a6", "white"),
        "ACTIVO":      ("#27ae60", "white"),
        "INACTIVO":    ("#e74c3c", "white"),
    }
    bg, fg = colores.get(estado.upper(), ("#bdc3c7", "#2c3e50"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:12px;font-size:0.75rem;font-weight:600;">{estado}</span>'
    )


def truncar_texto(texto: str, max_chars: int = 80) -> str:
    """Truncar texto largo para mostrar en tablas."""
    if not texto:
        return "—"
    return texto[:max_chars] + "..." if len(texto) > max_chars else texto


def exportar_csv(df: pd.DataFrame, nombre_archivo: str) -> None:
    """Botón para exportar DataFrame a CSV."""
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 Exportar a CSV",
        data=csv,
        file_name=f"{nombre_archivo}_{date.today()}.csv",
        mime="text/csv",
    )


def mostrar_spinner_operacion(mensaje: str = "Procesando..."):
    """Context manager helper para operaciones con spinner."""
    return st.spinner(mensaje)


def fecha_relativa(fecha) -> str:
    """Mostrar una fecha como 'Hace N días' o 'Hoy', etc."""
    if not fecha:
        return "—"
    if isinstance(fecha, str):
        try:
            fecha = datetime.fromisoformat(fecha).date()
        except Exception:
            return fecha
    if isinstance(fecha, datetime):
        fecha = fecha.date()

    hoy = date.today()
    delta = (hoy - fecha).days

    if delta == 0:    return "Hoy"
    if delta == 1:    return "Ayer"
    if delta < 7:     return f"Hace {delta} días"
    if delta < 30:    return f"Hace {delta // 7} semana(s)"
    if delta < 365:   return f"Hace {delta // 30} mes(es)"
    return f"Hace {delta // 365} año(s)"
