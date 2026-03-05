# ============================================================
# database/models.py — Modelos SQLAlchemy ORM
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, Numeric,
    Date, Time, DateTime, SmallInteger, ForeignKey,
    BigInteger, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database.connection import Base
import uuid


# ─────────────────────────────────────────────────────────────
# ESQUEMA: seguridad
# ─────────────────────────────────────────────────────────────

class Rol(Base):
    __tablename__  = "roles"
    __table_args__ = {"schema": "seguridad"}

    id          = Column(Integer, primary_key=True)
    nombre      = Column(String(50), nullable=False, unique=True)
    descripcion = Column(Text)
    activo      = Column(Boolean, default=True)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Permiso(Base):
    __tablename__  = "permisos"
    __table_args__ = {"schema": "seguridad"}

    id          = Column(Integer, primary_key=True)
    modulo      = Column(String(80), nullable=False)
    accion      = Column(String(50), nullable=False)
    descripcion = Column(Text)


class Usuario(Base):
    __tablename__  = "usuarios"
    __table_args__ = {"schema": "seguridad"}

    id             = Column(Integer, primary_key=True)
    username       = Column(String(50), nullable=False, unique=True)
    email          = Column(String(120), nullable=False, unique=True)
    password_hash  = Column(String(255), nullable=False)
    nombre         = Column(String(100), nullable=False)
    apellido       = Column(String(100), nullable=False)
    foto_perfil    = Column(Text)  # Base64
    activo         = Column(Boolean, default=True)
    ultimo_acceso  = Column(DateTime)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by     = Column(Integer, ForeignKey("seguridad.usuarios.id"))


class UsuarioRol(Base):
    __tablename__  = "usuario_roles"
    __table_args__ = {"schema": "seguridad"}

    usuario_id = Column(Integer, ForeignKey("seguridad.usuarios.id", ondelete="CASCADE"), primary_key=True)
    rol_id     = Column(Integer, ForeignKey("seguridad.roles.id", ondelete="CASCADE"), primary_key=True)


class Sesion(Base):
    __tablename__  = "sesiones"
    __table_args__ = {"schema": "seguridad"}

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id  = Column(Integer, ForeignKey("seguridad.usuarios.id"), nullable=False)
    token_hash  = Column(String(255), nullable=False)
    ip_address  = Column(String(45))
    user_agent  = Column(Text)
    creado_en   = Column(DateTime, server_default=func.now())
    expira_en   = Column(DateTime, nullable=False)
    activo      = Column(Boolean, default=True)


# ─────────────────────────────────────────────────────────────
# ESQUEMA: clinica — Mantenedores
# ─────────────────────────────────────────────────────────────

class Especialidad(Base):
    __tablename__  = "especialidades"
    __table_args__ = {"schema": "clinica"}

    id          = Column(Integer, primary_key=True)
    codigo      = Column(String(10), nullable=False, unique=True)
    nombre      = Column(String(100), nullable=False)
    descripcion = Column(Text)
    activo      = Column(Boolean, default=True)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by  = Column(Integer, ForeignKey("seguridad.usuarios.id"))

    medicos = relationship("Medico", back_populates="especialidad")


class MantenedorCIE10(Base):
    __tablename__  = "mantenedor_cie10"
    __table_args__ = {"schema": "clinica"}

    id          = Column(Integer, primary_key=True)
    codigo      = Column(String(10), nullable=False, unique=True)
    descripcion = Column(Text, nullable=False)
    categoria   = Column(String(100))
    activo      = Column(Boolean, default=True)


class MantenedorMedicamento(Base):
    __tablename__  = "mantenedor_medicamentos"
    __table_args__ = {"schema": "clinica"}

    id               = Column(Integer, primary_key=True)
    nombre_generico  = Column(String(200), nullable=False)
    nombre_comercial = Column(String(200))
    presentacion     = Column(String(100))
    concentracion    = Column(String(100))
    via_admin        = Column(String(80))
    activo           = Column(Boolean, default=True)
    created_at       = Column(DateTime, server_default=func.now())


class Servicio(Base):
    __tablename__  = "servicios"
    __table_args__ = {"schema": "clinica"}

    id              = Column(Integer, primary_key=True)
    codigo          = Column(String(20), nullable=False, unique=True)
    nombre          = Column(String(150), nullable=False)
    descripcion     = Column(Text)
    especialidad_id = Column(Integer, ForeignKey("clinica.especialidades.id"))
    tipo_servicio   = Column(String(50))
    activo          = Column(Boolean, default=True)
    created_at      = Column(DateTime, server_default=func.now())


class TipoSeguro(Base):
    __tablename__  = "tipos_seguro"
    __table_args__ = {"schema": "clinica"}

    id          = Column(Integer, primary_key=True)
    nombre      = Column(String(100), nullable=False)
    descripcion = Column(Text)
    activo      = Column(Boolean, default=True)


class Seguro(Base):
    __tablename__  = "seguros"
    __table_args__ = {"schema": "clinica"}

    id          = Column(Integer, primary_key=True)
    tipo_id     = Column(Integer, ForeignKey("clinica.tipos_seguro.id"))
    nombre      = Column(String(150), nullable=False)
    ruc         = Column(String(20))
    contacto    = Column(String(100))
    telefono    = Column(String(20))
    email       = Column(String(120))
    activo      = Column(Boolean, default=True)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Tarifario(Base):
    __tablename__  = "tarifarios"
    __table_args__ = {"schema": "clinica"}

    id             = Column(Integer, primary_key=True)
    servicio_id    = Column(Integer, ForeignKey("clinica.servicios.id"), nullable=False)
    seguro_id      = Column(Integer, ForeignKey("clinica.seguros.id"))
    precio         = Column(Numeric(10, 2), nullable=False)
    vigente_desde  = Column(Date, nullable=False)
    vigente_hasta  = Column(Date)
    activo         = Column(Boolean, default=True)
    created_at     = Column(DateTime, server_default=func.now())
    created_by     = Column(Integer, ForeignKey("seguridad.usuarios.id"))


class ParametroSistema(Base):
    __tablename__  = "parametros_sistema"
    __table_args__ = {"schema": "clinica"}

    clave       = Column(String(100), primary_key=True)
    valor       = Column(Text, nullable=False)
    descripcion = Column(Text)
    tipo_dato   = Column(String(20), default="STRING")
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by  = Column(Integer, ForeignKey("seguridad.usuarios.id"))


# ─────────────────────────────────────────────────────────────
# ESQUEMA: clinica — Personal
# ─────────────────────────────────────────────────────────────

class Medico(Base):
    __tablename__  = "medicos"
    __table_args__ = {"schema": "clinica"}

    id              = Column(Integer, primary_key=True)
    usuario_id      = Column(Integer, ForeignKey("seguridad.usuarios.id"))
    dni             = Column(String(20), nullable=False, unique=True)
    cmp             = Column(String(20), nullable=False, unique=True)
    nombre          = Column(String(100), nullable=False)
    apellido        = Column(String(100), nullable=False)
    especialidad_id = Column(Integer, ForeignKey("clinica.especialidades.id"))
    telefono        = Column(String(20))
    email           = Column(String(120))
    activo          = Column(Boolean, default=True)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by      = Column(Integer, ForeignKey("seguridad.usuarios.id"))

    especialidad = relationship("Especialidad", back_populates="medicos")
    horarios     = relationship("HorarioMedico", back_populates="medico")
    citas        = relationship("Cita", back_populates="medico")


class HorarioMedico(Base):
    __tablename__  = "horarios_medicos"
    __table_args__ = {"schema": "clinica"}

    id                = Column(Integer, primary_key=True)
    medico_id         = Column(Integer, ForeignKey("clinica.medicos.id"), nullable=False)
    dia_semana        = Column(SmallInteger, nullable=False)
    hora_inicio       = Column(Time, nullable=False)
    hora_fin          = Column(Time, nullable=False)
    duracion_cita_min = Column(SmallInteger, default=30)
    activo            = Column(Boolean, default=True)

    medico = relationship("Medico", back_populates="horarios")


# ─────────────────────────────────────────────────────────────
# ESQUEMA: clinica — Pacientes
# ─────────────────────────────────────────────────────────────

class Paciente(Base):
    __tablename__  = "pacientes"
    __table_args__ = {"schema": "clinica"}

    id                  = Column(Integer, primary_key=True)
    dni                 = Column(String(20), nullable=False, unique=True)
    numero_hc           = Column(String(20), nullable=False, unique=True)
    nombre              = Column(String(100), nullable=False)
    apellido_pat        = Column(String(100), nullable=False)
    apellido_mat        = Column(String(100))
    fecha_nacimiento    = Column(Date, nullable=False)
    sexo                = Column(String(1))
    grupo_sanguineo     = Column(String(5))
    estado_civil        = Column(String(20))
    telefono            = Column(String(20))
    email               = Column(String(120))
    direccion           = Column(Text)
    distrito            = Column(String(80))
    provincia           = Column(String(80))
    departamento        = Column(String(80))
    seguro_id           = Column(Integer, ForeignKey("clinica.seguros.id"))
    numero_poliza       = Column(String(50))
    contacto_emergencia = Column(String(100))
    telefono_emergencia = Column(String(20))
    activo              = Column(Boolean, default=True)
    created_at          = Column(DateTime, server_default=func.now())
    updated_at          = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by          = Column(Integer, ForeignKey("seguridad.usuarios.id"))

    historia_clinica = relationship("HistoriaClinica", back_populates="paciente", uselist=False)
    citas            = relationship("Cita", back_populates="paciente")
    consultas        = relationship("Consulta", back_populates="paciente")
    facturas         = relationship("Factura", back_populates="paciente")


class HistoriaClinica(Base):
    __tablename__  = "historias_clinicas"
    __table_args__ = {"schema": "clinica"}

    id                      = Column(Integer, primary_key=True)
    paciente_id             = Column(Integer, ForeignKey("clinica.pacientes.id"), nullable=False, unique=True)
    antecedentes_personales = Column(Text)
    antecedentes_familiares = Column(Text)
    alergias                = Column(Text)
    medicamentos_habituales = Column(Text)
    cirugias_previas        = Column(Text)
    habitos                 = Column(Text)
    observaciones           = Column(Text)
    created_at              = Column(DateTime, server_default=func.now())
    updated_at              = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by              = Column(Integer, ForeignKey("seguridad.usuarios.id"))

    paciente = relationship("Paciente", back_populates="historia_clinica")


# ─────────────────────────────────────────────────────────────
# ESQUEMA: clinica — Citas y Atención
# ─────────────────────────────────────────────────────────────

class Cita(Base):
    __tablename__  = "citas"
    __table_args__ = {"schema": "clinica"}

    id              = Column(Integer, primary_key=True)
    paciente_id     = Column(Integer, ForeignKey("clinica.pacientes.id"), nullable=False)
    medico_id       = Column(Integer, ForeignKey("clinica.medicos.id"), nullable=False)
    servicio_id     = Column(Integer, ForeignKey("clinica.servicios.id"))
    fecha_cita      = Column(Date, nullable=False)
    hora_inicio     = Column(Time, nullable=False)
    hora_fin        = Column(Time, nullable=False)
    estado          = Column(String(20), default="PROGRAMADA")
    motivo_consulta = Column(Text)
    observaciones   = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by      = Column(Integer, ForeignKey("seguridad.usuarios.id"))

    paciente  = relationship("Paciente", back_populates="citas")
    medico    = relationship("Medico", back_populates="citas")
    consultas = relationship("Consulta", back_populates="cita")


class ListaEspera(Base):
    __tablename__  = "lista_espera"
    __table_args__ = {"schema": "clinica"}

    id               = Column(Integer, primary_key=True)
    paciente_id      = Column(Integer, ForeignKey("clinica.pacientes.id"), nullable=False)
    medico_id        = Column(Integer, ForeignKey("clinica.medicos.id"))
    especialidad_id  = Column(Integer, ForeignKey("clinica.especialidades.id"))
    fecha_solicitud  = Column(DateTime, server_default=func.now())
    prioridad        = Column(SmallInteger, default=5)
    estado           = Column(String(20), default="ESPERANDO")
    cita_asignada_id = Column(Integer, ForeignKey("clinica.citas.id"))
    observaciones    = Column(Text)


class Consulta(Base):
    __tablename__  = "consultas"
    __table_args__ = {"schema": "clinica"}

    id                  = Column(Integer, primary_key=True)
    cita_id             = Column(Integer, ForeignKey("clinica.citas.id"))
    paciente_id         = Column(Integer, ForeignKey("clinica.pacientes.id"), nullable=False)
    medico_id           = Column(Integer, ForeignKey("clinica.medicos.id"), nullable=False)
    fecha_atencion      = Column(DateTime, server_default=func.now())
    motivo              = Column(Text, nullable=False)
    anamnesis           = Column(Text)
    examen_fisico       = Column(Text)
    temperatura         = Column(Numeric(4, 1))
    presion_arterial    = Column(String(10))
    frecuencia_cardiaca = Column(SmallInteger)
    saturacion_o2       = Column(SmallInteger)
    peso_kg             = Column(Numeric(5, 2))
    talla_cm            = Column(Numeric(5, 1))
    tratamiento         = Column(Text)
    indicaciones        = Column(Text)
    prox_control        = Column(Date)
    estado              = Column(String(20), default="EN_PROCESO")
    created_at          = Column(DateTime, server_default=func.now())
    updated_at          = Column(DateTime, server_default=func.now(), onupdate=func.now())

    paciente       = relationship("Paciente", back_populates="consultas")
    medico         = relationship("Medico")
    cita           = relationship("Cita", back_populates="consultas")
    diagnosticos   = relationship("Diagnostico", back_populates="consulta")
    prescripciones = relationship("Prescripcion", back_populates="consulta")
    examenes       = relationship("ExamenSolicitado", back_populates="consulta")


class Diagnostico(Base):
    __tablename__  = "diagnosticos"
    __table_args__ = {"schema": "clinica"}

    id          = Column(Integer, primary_key=True)
    consulta_id = Column(Integer, ForeignKey("clinica.consultas.id"), nullable=False)
    cie10_id    = Column(Integer, ForeignKey("clinica.mantenedor_cie10.id"), nullable=False)
    tipo        = Column(String(20), default="DEFINITIVO")
    observacion = Column(Text)
    created_at  = Column(DateTime, server_default=func.now())

    consulta = relationship("Consulta", back_populates="diagnosticos")


class Prescripcion(Base):
    __tablename__  = "prescripciones"
    __table_args__ = {"schema": "clinica"}

    id              = Column(Integer, primary_key=True)
    consulta_id     = Column(Integer, ForeignKey("clinica.consultas.id"), nullable=False)
    medicamento_id  = Column(Integer, ForeignKey("clinica.mantenedor_medicamentos.id"), nullable=False)
    dosis           = Column(String(100), nullable=False)
    frecuencia      = Column(String(100), nullable=False)
    duracion        = Column(String(100))
    instrucciones   = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())

    consulta = relationship("Consulta", back_populates="prescripciones")


class ExamenSolicitado(Base):
    __tablename__  = "examenes_solicitados"
    __table_args__ = {"schema": "clinica"}

    id               = Column(Integer, primary_key=True)
    consulta_id      = Column(Integer, ForeignKey("clinica.consultas.id"), nullable=False)
    tipo_examen      = Column(String(50))
    nombre_examen    = Column(String(200), nullable=False)
    indicaciones     = Column(Text)
    urgente          = Column(Boolean, default=False)
    resultado        = Column(Text)
    fecha_resultado  = Column(DateTime)
    archivo_resultado = Column(Text)  # Base64
    estado           = Column(String(20), default="SOLICITADO")
    created_at       = Column(DateTime, server_default=func.now())
    updated_at       = Column(DateTime, server_default=func.now(), onupdate=func.now())

    consulta = relationship("Consulta", back_populates="examenes")


# ─────────────────────────────────────────────────────────────
# ESQUEMA: clinica — Facturación
# ─────────────────────────────────────────────────────────────

class Factura(Base):
    __tablename__  = "facturas"
    __table_args__ = {"schema": "clinica"}

    id              = Column(Integer, primary_key=True)
    numero_factura  = Column(String(30), nullable=False, unique=True)
    paciente_id     = Column(Integer, ForeignKey("clinica.pacientes.id"), nullable=False)
    consulta_id     = Column(Integer, ForeignKey("clinica.consultas.id"))
    seguro_id       = Column(Integer, ForeignKey("clinica.seguros.id"))
    fecha_emision   = Column(DateTime, server_default=func.now())
    subtotal        = Column(Numeric(10, 2), nullable=False, default=0)
    descuento       = Column(Numeric(10, 2), default=0)
    igv             = Column(Numeric(10, 2), default=0)
    total           = Column(Numeric(10, 2), nullable=False, default=0)
    estado          = Column(String(20), default="PENDIENTE")
    observaciones   = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by      = Column(Integer, ForeignKey("seguridad.usuarios.id"))

    paciente = relationship("Paciente", back_populates="facturas")
    detalles = relationship("DetalleFactura", back_populates="factura")
    pagos    = relationship("Pago", back_populates="factura")


class DetalleFactura(Base):
    __tablename__  = "detalle_facturas"
    __table_args__ = {"schema": "clinica"}

    id          = Column(Integer, primary_key=True)
    factura_id  = Column(Integer, ForeignKey("clinica.facturas.id"), nullable=False)
    servicio_id = Column(Integer, ForeignKey("clinica.servicios.id"), nullable=False)
    descripcion = Column(Text, nullable=False)
    cantidad    = Column(SmallInteger, default=1)
    precio_unit = Column(Numeric(10, 2), nullable=False)
    descuento   = Column(Numeric(10, 2), default=0)
    subtotal    = Column(Numeric(10, 2), nullable=False)

    factura = relationship("Factura", back_populates="detalles")


class Pago(Base):
    __tablename__  = "pagos"
    __table_args__ = {"schema": "clinica"}

    id            = Column(Integer, primary_key=True)
    factura_id    = Column(Integer, ForeignKey("clinica.facturas.id"), nullable=False)
    monto         = Column(Numeric(10, 2), nullable=False)
    metodo_pago   = Column(String(30))
    referencia    = Column(String(100))
    fecha_pago    = Column(DateTime, server_default=func.now())
    usuario_id    = Column(Integer, ForeignKey("seguridad.usuarios.id"))
    observaciones = Column(Text)

    factura = relationship("Factura", back_populates="pagos")


# ─────────────────────────────────────────────────────────────
# ESQUEMA: auditoria
# ─────────────────────────────────────────────────────────────

class LogAuditoria(Base):
    __tablename__  = "log_auditoria"
    __table_args__ = {"schema": "auditoria"}

    id            = Column(BigInteger, primary_key=True)
    usuario_id    = Column(Integer, ForeignKey("seguridad.usuarios.id"))
    username      = Column(String(50))
    accion        = Column(String(20), nullable=False)
    modulo        = Column(String(80), nullable=False)
    tabla         = Column(String(80))
    registro_id   = Column(String(50))
    datos_antes   = Column(JSONB)
    datos_despues = Column(JSONB)
    ip_address    = Column(String(45))
    fecha_hora    = Column(DateTime, server_default=func.now())
