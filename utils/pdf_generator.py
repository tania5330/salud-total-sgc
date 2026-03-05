# ============================================================
# utils/pdf_generator.py — Motor de reportes PDF con ReportLab
# ============================================================
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime, date

# Paleta de colores institucional
COLOR_PRIMARY   = colors.HexColor("#1a5276")
COLOR_SECONDARY = colors.HexColor("#2980b9")
COLOR_ACCENT    = colors.HexColor("#27ae60")
COLOR_LIGHT     = colors.HexColor("#eaf4fb")
COLOR_DARK      = colors.HexColor("#1c2833")
COLOR_WHITE     = colors.white
COLOR_GRAY      = colors.HexColor("#bdc3c7")


def _header_footer(canvas, doc, clinica_info: dict):
    """Función de callback para encabezado y pie de página en cada hoja."""
    canvas.saveState()
    w, h = A4

    # ── Encabezado ──
    canvas.setFillColor(COLOR_PRIMARY)
    canvas.rect(0, h - 3*cm, w, 3*cm, fill=True, stroke=False)
    canvas.setFillColor(COLOR_WHITE)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(1.5*cm, h - 1.5*cm, clinica_info.get("nombre", "Clínica Salud Total"))
    canvas.setFont("Helvetica", 9)
    canvas.drawString(1.5*cm, h - 2.2*cm, clinica_info.get("direccion", ""))
    canvas.drawRightString(w - 1.5*cm, h - 1.5*cm, clinica_info.get("telefono", ""))
    canvas.drawRightString(w - 1.5*cm, h - 2.2*cm, clinica_info.get("email", ""))

    # ── Pie de página ──
    canvas.setFillColor(COLOR_PRIMARY)
    canvas.rect(0, 0, w, 1.2*cm, fill=True, stroke=False)
    canvas.setFillColor(COLOR_WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.5*cm, 0.4*cm, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    canvas.drawCentredString(w/2, 0.4*cm, "— Documento confidencial —")
    canvas.drawRightString(w - 1.5*cm, 0.4*cm, f"Página {doc.page}")
    canvas.restoreState()


def _get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Title2", fontSize=14, textColor=COLOR_PRIMARY,
                               fontName="Helvetica-Bold", spaceAfter=6))
    styles.add(ParagraphStyle("SectionHeader", fontSize=11, textColor=COLOR_WHITE,
                               fontName="Helvetica-Bold", backColor=COLOR_SECONDARY,
                               leftIndent=8, spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle("BodySmall", fontSize=9, leading=13))
    styles.add(ParagraphStyle("Label", fontSize=8, textColor=colors.gray,
                               fontName="Helvetica-Bold"))
    return styles


def generar_pdf_historia_clinica(paciente: dict, historia: dict,
                                  consultas: list, clinica_info: dict) -> bytes:
    """Generar PDF de historia clínica completa de un paciente."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=3.5*cm, bottomMargin=1.8*cm,
        leftMargin=1.5*cm, rightMargin=1.5*cm
    )
    styles = _get_styles()
    story = []

    # ── Título ──
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("HISTORIA CLÍNICA", styles["Title2"]))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARY))
    story.append(Spacer(1, 0.3*cm))

    # ── Datos del paciente ──
    story.append(Paragraph("DATOS DEL PACIENTE", styles["SectionHeader"]))
    data_pac = [
        ["N° HC:", paciente.get("numero_hc",""), "DNI:", paciente.get("dni","")],
        ["Nombre:", f"{paciente.get('nombre','')} {paciente.get('apellido_pat','')} {paciente.get('apellido_mat','')}",
         "F. Nacimiento:", str(paciente.get("fecha_nacimiento",""))],
        ["Sexo:", paciente.get("sexo",""), "Grupo:", paciente.get("grupo_sanguineo","")],
        ["Teléfono:", paciente.get("telefono",""), "Email:", paciente.get("email","")],
        ["Dirección:", paciente.get("direccion",""), "Seguro:", paciente.get("seguro","")],
    ]
    t = Table(data_pac, colWidths=[3*cm, 7*cm, 3*cm, 5*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",    (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("BACKGROUND",  (0,0), (-1,-1), COLOR_LIGHT),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [COLOR_LIGHT, COLOR_WHITE]),
        ("GRID",        (0,0), (-1,-1), 0.3, COLOR_GRAY),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    # ── Antecedentes ──
    story.append(Paragraph("ANTECEDENTES", styles["SectionHeader"]))
    antec_data = [
        ["Personales:", historia.get("antecedentes_personales","—")],
        ["Familiares:", historia.get("antecedentes_familiares","—")],
        ["Alergias:", historia.get("alergias","—")],
        ["Medicamentos habituales:", historia.get("medicamentos_habituales","—")],
        ["Cirugías previas:", historia.get("cirugias_previas","—")],
    ]
    t2 = Table(antec_data, colWidths=[5*cm, 13*cm])
    t2.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",    (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("GRID",        (0,0), (-1,-1), 0.3, COLOR_GRAY),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [COLOR_LIGHT, COLOR_WHITE]),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.4*cm))

    # ── Consultas recientes ──
    if consultas:
        story.append(Paragraph("CONSULTAS REGISTRADAS", styles["SectionHeader"]))
        for c in consultas[-5:]:  # Últimas 5 consultas
            story.append(Spacer(1, 0.2*cm))
            fa = c.get("fecha_atencion")
            if isinstance(fa, (datetime, date)):
                fa_str = fa.strftime("%Y-%m-%d")
            else:
                fa_str = str(fa)[:10] if fa else ""
            story.append(Paragraph(f"📅 {fa_str}  —  Dr. {c.get('medico','')}", styles["BodySmall"]))
            cons_data = [
                ["Motivo:", c.get("motivo","—")],
                ["Diagnóstico:", c.get("diagnostico","—")],
                ["Tratamiento:", c.get("tratamiento","—")],
            ]
            tc = Table(cons_data, colWidths=[4*cm, 14*cm])
            tc.setStyle(TableStyle([
                ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
                ("FONTSIZE",  (0,0), (-1,-1), 8),
                ("GRID",      (0,0), (-1,-1), 0.2, COLOR_GRAY),
                ("TOPPADDING",(0,0), (-1,-1), 3),
            ]))
            story.append(tc)

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, clinica_info),
              onLaterPages=lambda c, d: _header_footer(c, d, clinica_info))
    return buffer.getvalue()


def generar_pdf_receta(paciente: dict, medico: dict,
                        prescripciones: list, clinica_info: dict) -> bytes:
    """Generar PDF de receta médica oficial."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             topMargin=3.5*cm, bottomMargin=1.8*cm,
                             leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = _get_styles()
    story = []

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("RECETA MÉDICA", styles["Title2"]))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARY))
    story.append(Spacer(1, 0.3*cm))

    # Médico y paciente
    info = [
        [Paragraph(f"<b>Médico:</b> Dr. {medico.get('nombre','')} {medico.get('apellido','')}", styles["BodySmall"]),
         Paragraph(f"<b>CMP:</b> {medico.get('cmp','')}", styles["BodySmall"])],
        [Paragraph(f"<b>Especialidad:</b> {medico.get('especialidad','')}", styles["BodySmall"]),
         Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", styles["BodySmall"])],
        [Paragraph(f"<b>Paciente:</b> {paciente.get('nombre','')} {paciente.get('apellido_pat','')}", styles["BodySmall"]),
         Paragraph(f"<b>DNI:</b> {paciente.get('dni','')}", styles["BodySmall"])],
    ]
    ti = Table(info, colWidths=[10*cm, 8*cm])
    ti.setStyle(TableStyle([
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID",     (0,0), (-1,-1), 0.3, COLOR_GRAY),
        ("BACKGROUND", (0,0), (-1,-1), COLOR_LIGHT),
        ("TOPPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(ti)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("MEDICAMENTOS PRESCRITOS", styles["SectionHeader"]))
    story.append(Spacer(1, 0.2*cm))

    for i, p in enumerate(prescripciones, 1):
        med_data = [
            [f"{i}.", Paragraph(f"<b>{p.get('medicamento','')}</b>", styles["BodySmall"]),
             p.get("dosis",""), p.get("frecuencia",""), p.get("duracion","")],
            ["",  Paragraph(f"<i>Instrucciones: {p.get('instrucciones','—')}</i>",
                            styles["BodySmall"]), "", "", ""],
        ]
        tm = Table(med_data, colWidths=[0.7*cm, 7*cm, 3*cm, 4*cm, 3.5*cm])
        tm.setStyle(TableStyle([
            ("FONTSIZE",   (0,0), (-1,-1), 9),
            ("SPAN",       (1,1), (-1,1)),
            ("GRID",       (0,0), (-1,-1), 0.3, COLOR_GRAY),
            ("BACKGROUND", (0,0), (-1,0), COLOR_LIGHT),
            ("TOPPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(tm)
        story.append(Spacer(1, 0.2*cm))

    # Firma
    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width=6*cm, thickness=1, color=COLOR_DARK))
    story.append(Paragraph(
        f"Dr. {medico.get('nombre','')} {medico.get('apellido','')}  |  CMP: {medico.get('cmp','')}",
        styles["BodySmall"]
    ))

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, clinica_info),
              onLaterPages=lambda c, d: _header_footer(c, d, clinica_info))
    return buffer.getvalue()


def generar_pdf_reporte_gestion(titulo: str, subtitulo: str,
                                  datos: list, columnas: list,
                                  clinica_info: dict,
                                  resumen: dict = None) -> bytes:
    """Generar PDF de reporte de gestión genérico con tabla de datos y resumen."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                             topMargin=3.5*cm, bottomMargin=1.8*cm,
                             leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = _get_styles()
    story = []

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(titulo.upper(), styles["Title2"]))
    story.append(Paragraph(subtitulo, styles["BodySmall"]))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARY))
    story.append(Spacer(1, 0.3*cm))

    # Resumen ejecutivo si se provee
    if resumen:
        res_data = [[k, str(v)] for k, v in resumen.items()]
        tr = Table(res_data, colWidths=[8*cm, 6*cm])
        tr.setStyle(TableStyle([
            ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 9),
            ("BACKGROUND", (0,0), (-1,-1), COLOR_LIGHT),
            ("GRID",       (0,0), (-1,-1), 0.3, COLOR_GRAY),
            ("TOPPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(tr)
        story.append(Spacer(1, 0.4*cm))

    # Tabla de datos
    if datos:
        col_w = [(landscape(A4)[0] - 3*cm) / len(columnas)] * len(columnas)
        table_data = [columnas] + [[str(row.get(c,"")) for c in columnas] for row in datos]
        td = Table(table_data, colWidths=col_w, repeatRows=1)
        td.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), COLOR_PRIMARY),
            ("TEXTCOLOR",   (0,0), (-1,0), COLOR_WHITE),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [COLOR_LIGHT, COLOR_WHITE]),
            ("GRID",        (0,0), (-1,-1), 0.3, COLOR_GRAY),
            ("ALIGN",       (0,0), (-1,-1), "LEFT"),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ]))
        story.append(td)

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, clinica_info),
              onLaterPages=lambda c, d: _header_footer(c, d, clinica_info))
    return buffer.getvalue()
