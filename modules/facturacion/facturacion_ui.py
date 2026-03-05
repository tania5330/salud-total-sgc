# ============================================================
# modules/facturacion/facturacion_ui.py
# ============================================================
import streamlit as st
import pandas as pd
from datetime import date
from database.connection import execute_query, get_db
from utils.audit_logger import log_action
from utils.auth import require_auth, has_any_role
from utils.pdf_generator import generar_pdf_reporte_gestion
from sqlalchemy import text


def render_facturacion():
    require_auth()
    if not has_any_role("ADMINISTRADOR","RECEPCIONISTA","CONTADOR"):
        st.error("🔒 Acceso restringido.")
        return

    st.title("💰 Facturación")
    tab1, tab2, tab3 = st.tabs(["📄 Nueva Factura", "📊 Listado", "💳 Registrar Pago"])

    with tab1: _render_nueva_factura()
    with tab2: _render_listado_facturas()
    with tab3: _render_registrar_pago()


def _render_nueva_factura():
    st.subheader("Generar Nueva Factura")
    col1, col2 = st.columns(2)

    with col1:
        dni = st.text_input("DNI del Paciente *")
    with col2:
        tipo = st.selectbox("Tipo", ["Particular","Con Seguro"])

    pac_data = None
    if dni:
        rows = execute_query("""
            SELECT p.id, p.nombre || ' ' || p.apellido_pat AS nombre,
                   p.dni, p.numero_hc, s.nombre AS seguro
            FROM clinica.pacientes p
            LEFT JOIN clinica.seguros s ON s.id = p.seguro_id
            WHERE p.dni = :dni AND p.activo=TRUE
        """, {"dni": dni})
        if rows:
            pac_data = rows[0]
            st.info(f"👤 **{pac_data['nombre']}** — HC: {pac_data['numero_hc']}")

    servicios = execute_query("SELECT id, codigo, nombre, tipo_servicio FROM clinica.servicios WHERE activo=TRUE ORDER BY nombre")
    svc_opts = {f"{s['codigo']} — {s['nombre']}": s["id"] for s in servicios}

    with st.form("form_factura"):
        items = []
        st.write("**Agregar Servicios:**")
        for i in range(1, 6):
            c1, c2, c3 = st.columns([4, 1, 2])
            with c1:
                svc = st.selectbox(f"Servicio {i}", ["— Seleccionar —"] + list(svc_opts.keys()), key=f"svc{i}")
            with c2:
                qty = st.number_input("Cant.", min_value=1, max_value=10, value=1, key=f"qty{i}")
            with c3:
                precio = st.number_input("Precio S/", min_value=0.0, value=0.0, step=0.5, key=f"prc{i}")
            if svc != "— Seleccionar —" and precio > 0:
                items.append({"svc_id": svc_opts[svc], "svc_label": svc, "qty": qty, "precio": precio})

        obs = st.text_input("Observaciones")

        if st.form_submit_button("💾 Generar Factura", use_container_width=True):
            if not pac_data:
                st.error("❌ Ingrese un DNI de paciente válido.")
            elif not items:
                st.error("❌ Agregue al menos un servicio.")
            else:
                _guardar_factura(pac_data["id"], items, obs)


def _guardar_factura(pac_id: int, items: list, obs: str):
    subtotal  = sum(i["qty"] * i["precio"] for i in items)
    igv_pct   = float(execute_query("SELECT valor FROM clinica.parametros_sistema WHERE clave='IGV_PORCENTAJE'")[0]["valor"])
    igv       = round(subtotal * igv_pct / 100, 2)
    total     = round(subtotal + igv, 2)

    try:
        with get_db() as db:
            # Número de factura correlativo
            res = db.execute(text("SELECT COUNT(*) FROM clinica.facturas")).fetchone()
            num_fac = f"F001-{(res[0]+1):06d}"

            r = db.execute(text("""
                INSERT INTO clinica.facturas
                    (numero_factura, paciente_id, subtotal, igv, total, observaciones, created_by)
                VALUES (:nf, :pid, :sub, :igv, :tot, :obs, :uid)
                RETURNING id
            """), {"nf": num_fac, "pid": pac_id, "sub": subtotal,
                   "igv": igv, "tot": total, "obs": obs,
                   "uid": st.session_state.user.get("id")})
            fac_id = r.fetchone()[0]

            for item in items:
                db.execute(text("""
                    INSERT INTO clinica.detalle_facturas
                        (factura_id, servicio_id, descripcion, cantidad, precio_unit, subtotal)
                    VALUES (:fid, :sid, :desc, :qty, :pu, :sub)
                """), {"fid": fac_id, "sid": item["svc_id"], "desc": item["svc_label"],
                       "qty": item["qty"], "pu": item["precio"],
                       "sub": item["qty"] * item["precio"]})

        log_action("INSERT", "FACTURACION", "clinica.facturas", fac_id)
        st.success(f"✅ Factura **{num_fac}** generada. Total: **S/ {total:,.2f}**")
    except Exception as e:
        st.error(f"❌ Error: {e}")


def _render_listado_facturas():
    col1, col2, col3 = st.columns(3)
    with col1: f_desde = st.date_input("Desde", value=date.today().replace(day=1), key="f_fac_d")
    with col2: f_hasta = st.date_input("Hasta", value=date.today(), key="f_fac_h")
    with col3: estado  = st.multiselect("Estado", ["PENDIENTE","PAGADA","ANULADA","CREDITO"],
                                         default=["PENDIENTE","PAGADA"])

    est_sql = ""
    if estado:
        est_sql = f"AND f.estado IN ({','.join([repr(e) for e in estado])})"

    rows = execute_query(f"""
        SELECT f.numero_factura, DATE(f.fecha_emision) AS fecha,
               p.nombre || ' ' || p.apellido_pat AS paciente,
               f.subtotal, f.igv, f.total, f.estado
        FROM clinica.facturas f
        JOIN clinica.pacientes p ON p.id = f.paciente_id
        WHERE DATE(f.fecha_emision) BETWEEN :fd AND :fh {est_sql}
        ORDER BY f.fecha_emision DESC LIMIT 500
    """, {"fd": f_desde, "fh": f_hasta})

    if rows:
        df = pd.DataFrame(rows)
        total_general = df["total"].sum()
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("💰 Total Período", f"S/ {total_general:,.2f}")

        # Exportar a PDF
        if st.button("📄 Exportar a PDF"):
            clinica_info = {r["clave"]: r["valor"] for r in execute_query(
                "SELECT clave, valor FROM clinica.parametros_sistema WHERE clave LIKE 'CLINICA_%'"
            )}
            pdf_bytes = generar_pdf_reporte_gestion(
                titulo="Reporte de Facturación",
                subtitulo=f"Período: {f_desde} al {f_hasta}",
                datos=rows,
                columnas=["numero_factura","fecha","paciente","subtotal","igv","total","estado"],
                clinica_info={"nombre": clinica_info.get("CLINICA_NOMBRE",""),
                               "direccion": clinica_info.get("CLINICA_DIRECCION",""),
                               "telefono": clinica_info.get("CLINICA_TELEFONO",""),
                               "email": clinica_info.get("CLINICA_EMAIL","")},
                resumen={"Total Facturas": len(rows), "Monto Total": f"S/ {total_general:,.2f}"}
            )
            st.download_button("⬇️ Descargar PDF", pdf_bytes,
                                file_name=f"reporte_facturacion_{f_desde}_{f_hasta}.pdf",
                                mime="application/pdf")


def _render_registrar_pago():
    st.subheader("Registrar Pago")
    num_fac = st.text_input("N° de Factura")
    if not num_fac:
        return

    fac = execute_query("""
        SELECT f.id, f.numero_factura, f.total, f.estado,
               p.nombre || ' ' || p.apellido_pat AS paciente
        FROM clinica.facturas f
        JOIN clinica.pacientes p ON p.id = f.paciente_id
        WHERE f.numero_factura = :nf
    """, {"nf": num_fac})

    if not fac:
        st.warning("Factura no encontrada.")
        return

    f = fac[0]
    if f["estado"] == "PAGADA":
        st.success("✅ Esta factura ya está pagada.")
        return

    st.info(f"📄 Factura: **{f['numero_factura']}** | Paciente: **{f['paciente']}** | Total: **S/ {f['total']:,.2f}**")

    with st.form("form_pago"):
        monto  = st.number_input("Monto a Pagar S/", min_value=0.01, value=float(f["total"]))
        metodo = st.selectbox("Método de Pago", ["EFECTIVO","TARJETA","TRANSFERENCIA","SEGURO"])
        ref    = st.text_input("Referencia / N° Operación")

        if st.form_submit_button("💳 Confirmar Pago"):
            try:
                with get_db() as db:
                    db.execute(text("""
                        INSERT INTO clinica.pagos (factura_id, monto, metodo_pago, referencia, usuario_id)
                        VALUES (:fid, :monto, :met, :ref, :uid)
                    """), {"fid": f["id"], "monto": monto, "met": metodo,
                           "ref": ref, "uid": st.session_state.user.get("id")})
                    db.execute(text("""
                        UPDATE clinica.facturas SET estado='PAGADA', updated_at=NOW()
                        WHERE id=:fid
                    """), {"fid": f["id"]})

                log_action("UPDATE", "FACTURACION", "clinica.pagos", f["id"])
                st.success(f"✅ Pago de S/ {monto:,.2f} registrado correctamente.")
            except Exception as e:
                st.error(f"❌ Error: {e}")