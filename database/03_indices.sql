-- ============================================================
-- ARCHIVO: 03_indices.sql
-- ============================================================

-- Pacientes
CREATE INDEX idx_pacientes_dni        ON clinica.pacientes(dni);
CREATE INDEX idx_pacientes_numero_hc  ON clinica.pacientes(numero_hc);
CREATE INDEX idx_pacientes_nombre     ON clinica.pacientes USING gin(to_tsvector('spanish', nombre || ' ' || apellido_pat));

-- Citas
CREATE INDEX idx_citas_medico_fecha   ON clinica.citas(medico_id, fecha_cita);
CREATE INDEX idx_citas_paciente       ON clinica.citas(paciente_id);
CREATE INDEX idx_citas_estado         ON clinica.citas(estado);

-- Consultas
CREATE INDEX idx_consultas_paciente   ON clinica.consultas(paciente_id);
CREATE INDEX idx_consultas_medico     ON clinica.consultas(medico_id);
CREATE INDEX idx_consultas_fecha      ON clinica.consultas(fecha_atencion);

-- Facturación
CREATE INDEX idx_facturas_paciente    ON clinica.facturas(paciente_id);
CREATE INDEX idx_facturas_estado      ON clinica.facturas(estado);
CREATE INDEX idx_facturas_fecha       ON clinica.facturas(fecha_emision);

-- Auditoría
CREATE INDEX idx_auditoria_usuario    ON auditoria.log_auditoria(usuario_id);
CREATE INDEX idx_auditoria_fecha      ON auditoria.log_auditoria(fecha_hora);
CREATE INDEX idx_auditoria_modulo     ON auditoria.log_auditoria(modulo);

-- CIE-10 búsqueda por texto
CREATE INDEX idx_cie10_codigo         ON clinica.mantenedor_cie10(codigo);
CREATE INDEX idx_cie10_desc           ON clinica.mantenedor_cie10 USING gin(to_tsvector('spanish', descripcion));