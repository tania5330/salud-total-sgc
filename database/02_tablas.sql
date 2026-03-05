-- ============================================================
-- ARCHIVO: 02_tablas.sql
-- ============================================================

-- ─────────────────────────────────────────
-- ESQUEMA: seguridad
-- ─────────────────────────────────────────

CREATE TABLE seguridad.roles (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    activo      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE seguridad.permisos (
    id       SERIAL PRIMARY KEY,
    modulo   VARCHAR(80) NOT NULL,
    accion   VARCHAR(50) NOT NULL,  -- CREATE, READ, UPDATE, DELETE
    descripcion TEXT,
    UNIQUE(modulo, accion)
);

CREATE TABLE seguridad.rol_permisos (
    rol_id     INTEGER REFERENCES seguridad.roles(id) ON DELETE CASCADE,
    permiso_id INTEGER REFERENCES seguridad.permisos(id) ON DELETE CASCADE,
    PRIMARY KEY (rol_id, permiso_id)
);

CREATE TABLE seguridad.usuarios (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(120) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    nombre          VARCHAR(100) NOT NULL,
    apellido        VARCHAR(100) NOT NULL,
    foto_perfil     BYTEA,
    activo          BOOLEAN DEFAULT TRUE,
    ultimo_acceso   TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    created_by      INTEGER REFERENCES seguridad.usuarios(id)
);

CREATE TABLE seguridad.usuario_roles (
    usuario_id INTEGER REFERENCES seguridad.usuarios(id) ON DELETE CASCADE,
    rol_id     INTEGER REFERENCES seguridad.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, rol_id)
);

CREATE TABLE seguridad.sesiones (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id  INTEGER NOT NULL REFERENCES seguridad.usuarios(id),
    token_hash  VARCHAR(255) NOT NULL,
    ip_address  VARCHAR(45),
    user_agent  TEXT,
    creado_en   TIMESTAMP DEFAULT NOW(),
    expira_en   TIMESTAMP NOT NULL,
    activo      BOOLEAN DEFAULT TRUE
);

-- ─────────────────────────────────────────
-- ESQUEMA: auditoria
-- ─────────────────────────────────────────

CREATE TABLE auditoria.log_auditoria (
    id          BIGSERIAL PRIMARY KEY,
    usuario_id  INTEGER REFERENCES seguridad.usuarios(id),
    username    VARCHAR(50),
    accion      VARCHAR(20) NOT NULL,  -- INSERT, UPDATE, DELETE, SELECT
    modulo      VARCHAR(80) NOT NULL,
    tabla       VARCHAR(80),
    registro_id VARCHAR(50),
    datos_antes JSONB,
    datos_despues JSONB,
    ip_address  VARCHAR(45),
    fecha_hora  TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- ESQUEMA: clinica — MANTENEDORES
-- ─────────────────────────────────────────

CREATE TABLE clinica.especialidades (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(10) NOT NULL UNIQUE,
    nombre      VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activo      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),
    created_by  INTEGER REFERENCES seguridad.usuarios(id)
);

CREATE TABLE clinica.mantenedor_cie10 (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(10) NOT NULL UNIQUE,
    descripcion TEXT NOT NULL,
    categoria   VARCHAR(100),
    activo      BOOLEAN DEFAULT TRUE
);

CREATE TABLE clinica.mantenedor_medicamentos (
    id              SERIAL PRIMARY KEY,
    nombre_generico VARCHAR(200) NOT NULL,
    nombre_comercial VARCHAR(200),
    presentacion    VARCHAR(100),
    concentracion   VARCHAR(100),
    via_admin       VARCHAR(80),
    activo          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE clinica.tipos_seguro (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activo      BOOLEAN DEFAULT TRUE
);

CREATE TABLE clinica.seguros (
    id              SERIAL PRIMARY KEY,
    tipo_id         INTEGER REFERENCES clinica.tipos_seguro(id),
    nombre          VARCHAR(150) NOT NULL,
    ruc             VARCHAR(20),
    contacto        VARCHAR(100),
    telefono        VARCHAR(20),
    email           VARCHAR(120),
    activo          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE clinica.servicios (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(20) NOT NULL UNIQUE,
    nombre          VARCHAR(150) NOT NULL,
    descripcion     TEXT,
    especialidad_id INTEGER REFERENCES clinica.especialidades(id),
    tipo_servicio   VARCHAR(50) CHECK (tipo_servicio IN ('CONSULTA','PROCEDIMIENTO','LABORATORIO','IMAGEN','HOSPITALIZACION','OTRO')),
    activo          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE clinica.tarifarios (
    id          SERIAL PRIMARY KEY,
    servicio_id INTEGER NOT NULL REFERENCES clinica.servicios(id),
    seguro_id   INTEGER REFERENCES clinica.seguros(id),  -- NULL = tarifa particular
    precio      NUMERIC(10,2) NOT NULL CHECK (precio >= 0),
    vigente_desde DATE NOT NULL,
    vigente_hasta DATE,
    activo      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW(),
    created_by  INTEGER REFERENCES seguridad.usuarios(id)
);

CREATE TABLE clinica.parametros_sistema (
    clave       VARCHAR(100) PRIMARY KEY,
    valor       TEXT NOT NULL,
    descripcion TEXT,
    tipo_dato   VARCHAR(20) DEFAULT 'STRING',
    updated_at  TIMESTAMP DEFAULT NOW(),
    updated_by  INTEGER REFERENCES seguridad.usuarios(id)
);

-- ─────────────────────────────────────────
-- PERSONAL MÉDICO
-- ─────────────────────────────────────────

CREATE TABLE clinica.medicos (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER REFERENCES seguridad.usuarios(id),
    dni             VARCHAR(20) NOT NULL UNIQUE,
    cmp             VARCHAR(20) NOT NULL UNIQUE,  -- Colegio Médico del Perú
    nombre          VARCHAR(100) NOT NULL,
    apellido        VARCHAR(100) NOT NULL,
    especialidad_id INTEGER REFERENCES clinica.especialidades(id),
    telefono        VARCHAR(20),
    email           VARCHAR(120),
    activo          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    created_by      INTEGER REFERENCES seguridad.usuarios(id)
);

CREATE TABLE clinica.horarios_medicos (
    id          SERIAL PRIMARY KEY,
    medico_id   INTEGER NOT NULL REFERENCES clinica.medicos(id),
    dia_semana  SMALLINT NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),  -- 0=Lunes
    hora_inicio TIME NOT NULL,
    hora_fin    TIME NOT NULL,
    duracion_cita_min SMALLINT DEFAULT 30,
    activo      BOOLEAN DEFAULT TRUE,
    CHECK (hora_fin > hora_inicio)
);

-- ─────────────────────────────────────────
-- PACIENTES
-- ─────────────────────────────────────────

CREATE TABLE clinica.pacientes (
    id              SERIAL PRIMARY KEY,
    dni             VARCHAR(20) NOT NULL UNIQUE,
    numero_hc       VARCHAR(20) NOT NULL UNIQUE,  -- Número de historia clínica
    nombre          VARCHAR(100) NOT NULL,
    apellido_pat    VARCHAR(100) NOT NULL,
    apellido_mat    VARCHAR(100),
    fecha_nacimiento DATE NOT NULL,
    sexo            CHAR(1) CHECK (sexo IN ('M','F','O')),
    grupo_sanguineo VARCHAR(5),
    estado_civil    VARCHAR(20),
    telefono        VARCHAR(20),
    email           VARCHAR(120),
    direccion       TEXT,
    distrito        VARCHAR(80),
    provincia       VARCHAR(80),
    departamento    VARCHAR(80),
    seguro_id       INTEGER REFERENCES clinica.seguros(id),
    numero_poliza   VARCHAR(50),
    contacto_emergencia VARCHAR(100),
    telefono_emergencia VARCHAR(20),
    activo          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    created_by      INTEGER REFERENCES seguridad.usuarios(id)
);

CREATE TABLE clinica.historias_clinicas (
    id              SERIAL PRIMARY KEY,
    paciente_id     INTEGER NOT NULL UNIQUE REFERENCES clinica.pacientes(id),
    antecedentes_personales TEXT,
    antecedentes_familiares TEXT,
    alergias        TEXT,
    medicamentos_habituales TEXT,
    cirugias_previas TEXT,
    habitos         TEXT,
    observaciones   TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    updated_by      INTEGER REFERENCES seguridad.usuarios(id)
);

-- ─────────────────────────────────────────
-- CITAS
-- ─────────────────────────────────────────

CREATE TABLE clinica.citas (
    id              SERIAL PRIMARY KEY,
    paciente_id     INTEGER NOT NULL REFERENCES clinica.pacientes(id),
    medico_id       INTEGER NOT NULL REFERENCES clinica.medicos(id),
    servicio_id     INTEGER REFERENCES clinica.servicios(id),
    fecha_cita      DATE NOT NULL,
    hora_inicio     TIME NOT NULL,
    hora_fin        TIME NOT NULL,
    estado          VARCHAR(20) DEFAULT 'PROGRAMADA'
                    CHECK (estado IN ('PROGRAMADA','CONFIRMADA','ATENDIDA','CANCELADA','NO_SHOW')),
    motivo_consulta TEXT,
    observaciones   TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    created_by      INTEGER REFERENCES seguridad.usuarios(id),
    -- Restricción: no solapamiento de horarios por médico
    CONSTRAINT no_solapamiento EXCLUDE USING gist (
        medico_id WITH =,
        tsrange(fecha_cita + hora_inicio, fecha_cita + hora_fin) WITH &&
    ) WHERE (estado NOT IN ('CANCELADA','NO_SHOW'))
);

CREATE TABLE clinica.lista_espera (
    id              SERIAL PRIMARY KEY,
    paciente_id     INTEGER NOT NULL REFERENCES clinica.pacientes(id),
    medico_id       INTEGER REFERENCES clinica.medicos(id),
    especialidad_id INTEGER REFERENCES clinica.especialidades(id),
    fecha_solicitud TIMESTAMP DEFAULT NOW(),
    prioridad       SMALLINT DEFAULT 5 CHECK (prioridad BETWEEN 1 AND 10),
    estado          VARCHAR(20) DEFAULT 'ESPERANDO'
                    CHECK (estado IN ('ESPERANDO','ASIGNADO','CANCELADO')),
    cita_asignada_id INTEGER REFERENCES clinica.citas(id),
    observaciones   TEXT
);

-- ─────────────────────────────────────────
-- ATENCIÓN CLÍNICA
-- ─────────────────────────────────────────

CREATE TABLE clinica.consultas (
    id              SERIAL PRIMARY KEY,
    cita_id         INTEGER NOT NULL REFERENCES clinica.citas(id),
    paciente_id     INTEGER NOT NULL REFERENCES clinica.pacientes(id),
    medico_id       INTEGER NOT NULL REFERENCES clinica.medicos(id),
    fecha_atencion  TIMESTAMP DEFAULT NOW(),
    motivo          TEXT NOT NULL,
    anamnesis       TEXT,
    examen_fisico   TEXT,
    temperatura     NUMERIC(4,1),
    presion_arterial VARCHAR(10),
    frecuencia_cardiaca SMALLINT,
    saturacion_o2   SMALLINT,
    peso_kg         NUMERIC(5,2),
    talla_cm        NUMERIC(5,1),
    tratamiento     TEXT,
    indicaciones    TEXT,
    prox_control    DATE,
    estado          VARCHAR(20) DEFAULT 'EN_PROCESO'
                    CHECK (estado IN ('EN_PROCESO','FINALIZADA','DERIVADA')),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE clinica.diagnosticos (
    id          SERIAL PRIMARY KEY,
    consulta_id INTEGER NOT NULL REFERENCES clinica.consultas(id),
    cie10_id    INTEGER NOT NULL REFERENCES clinica.mantenedor_cie10(id),
    tipo        VARCHAR(20) DEFAULT 'DEFINITIVO'
                CHECK (tipo IN ('PRESUNTIVO','DEFINITIVO','DESCARTADO')),
    observacion TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE clinica.prescripciones (
    id              SERIAL PRIMARY KEY,
    consulta_id     INTEGER NOT NULL REFERENCES clinica.consultas(id),
    medicamento_id  INTEGER NOT NULL REFERENCES clinica.mantenedor_medicamentos(id),
    dosis           VARCHAR(100) NOT NULL,
    frecuencia      VARCHAR(100) NOT NULL,
    duracion        VARCHAR(100),
    instrucciones   TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE clinica.examenes_solicitados (
    id              SERIAL PRIMARY KEY,
    consulta_id     INTEGER NOT NULL REFERENCES clinica.consultas(id),
    tipo_examen     VARCHAR(50) CHECK (tipo_examen IN ('LABORATORIO','IMAGEN','OTRO')),
    nombre_examen   VARCHAR(200) NOT NULL,
    indicaciones    TEXT,
    urgente         BOOLEAN DEFAULT FALSE,
    resultado       TEXT,
    fecha_resultado TIMESTAMP,
    archivo_resultado BYTEA,
    estado          VARCHAR(20) DEFAULT 'SOLICITADO'
                    CHECK (estado IN ('SOLICITADO','EN_PROCESO','COMPLETADO','CANCELADO')),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- FACTURACIÓN
-- ─────────────────────────────────────────

CREATE TABLE clinica.facturas (
    id              SERIAL PRIMARY KEY,
    numero_factura  VARCHAR(30) NOT NULL UNIQUE,
    paciente_id     INTEGER NOT NULL REFERENCES clinica.pacientes(id),
    consulta_id     INTEGER REFERENCES clinica.consultas(id),
    seguro_id       INTEGER REFERENCES clinica.seguros(id),
    fecha_emision   TIMESTAMP DEFAULT NOW(),
    subtotal        NUMERIC(10,2) NOT NULL DEFAULT 0,
    descuento       NUMERIC(10,2) DEFAULT 0,
    igv             NUMERIC(10,2) DEFAULT 0,
    total           NUMERIC(10,2) NOT NULL DEFAULT 0,
    estado          VARCHAR(20) DEFAULT 'PENDIENTE'
                    CHECK (estado IN ('PENDIENTE','PAGADA','ANULADA','CREDITO')),
    observaciones   TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    created_by      INTEGER REFERENCES seguridad.usuarios(id)
);

CREATE TABLE clinica.detalle_facturas (
    id          SERIAL PRIMARY KEY,
    factura_id  INTEGER NOT NULL REFERENCES clinica.facturas(id),
    servicio_id INTEGER NOT NULL REFERENCES clinica.servicios(id),
    descripcion TEXT NOT NULL,
    cantidad    SMALLINT DEFAULT 1,
    precio_unit NUMERIC(10,2) NOT NULL,
    descuento   NUMERIC(10,2) DEFAULT 0,
    subtotal    NUMERIC(10,2) NOT NULL
);

CREATE TABLE clinica.pagos (
    id              SERIAL PRIMARY KEY,
    factura_id      INTEGER NOT NULL REFERENCES clinica.facturas(id),
    monto           NUMERIC(10,2) NOT NULL CHECK (monto > 0),
    metodo_pago     VARCHAR(30) CHECK (metodo_pago IN ('EFECTIVO','TARJETA','TRANSFERENCIA','SEGURO','OTRO')),
    referencia      VARCHAR(100),
    fecha_pago      TIMESTAMP DEFAULT NOW(),
    usuario_id      INTEGER REFERENCES seguridad.usuarios(id),
    observaciones   TEXT
);