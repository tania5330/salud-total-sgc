-- ============================================================
-- ARCHIVO: 04_datos_iniciales.sql
-- ============================================================

-- ROLES BASE
INSERT INTO seguridad.roles (nombre, descripcion) VALUES
('ADMINISTRADOR', 'Acceso total al sistema'),
('MEDICO',        'Acceso a historia clínica, consultas y prescripciones'),
('ENFERMERA',     'Acceso a citas, triaje y exámenes'),
('RECEPCIONISTA', 'Gestión de citas, pacientes y facturación básica'),
('CONTADOR',      'Acceso a facturación y reportes financieros');

-- USUARIO ADMINISTRADOR (contraseña: Admin@2024 — cambiar en primer login)
-- Hash bcrypt generado externamente
INSERT INTO seguridad.usuarios (username, email, password_hash, nombre, apellido) VALUES
('admin', 'admin@saludtotal.com',
'$2b$12$RoiLXGTWTfD.Lc1iSz0Rl.bD9sL9G8UMnDtbdc1wMgUCQ4xVE19q2',
-- '$2b$12$placeholder_hash_reemplazar_en_deploy',
 'Administrador', 'Sistema');

INSERT INTO seguridad.usuario_roles (usuario_id, rol_id)
SELECT u.id, r.id FROM seguridad.usuarios u, seguridad.roles r
WHERE u.username = 'admin' AND r.nombre = 'ADMINISTRADOR';

-- ESPECIALIDADES COMUNES
INSERT INTO clinica.especialidades (codigo, nombre) VALUES
('MG',   'Medicina General'),
('CARD', 'Cardiología'),
('DERM', 'Dermatología'),
('GINE', 'Ginecología y Obstetricia'),
('NEUR', 'Neurología'),
('OFTA', 'Oftalmología'),
('ORTO', 'Ortopedia y Traumatología'),
('PEDIA','Pediatría'),
('PSIQ', 'Psiquiatría'),
('PULM', 'Neumología'),
('UROL', 'Urología'),
('ENDO', 'Endocrinología'),
('GAST', 'Gastroenterología');

-- CIE-10 FRECUENTES
INSERT INTO clinica.mantenedor_cie10 (codigo, descripcion, categoria) VALUES
('J06.9', 'Infección aguda de las vías respiratorias superiores, no especificada', 'Respiratorio'),
('J00',   'Rinofaringitis aguda (resfriado común)', 'Respiratorio'),
('K29.7', 'Gastritis, no especificada', 'Digestivo'),
('M54.5', 'Lumbago no especificado', 'Musculoesquelético'),
('I10',   'Hipertensión esencial (primaria)', 'Cardiovascular'),
('E11.9', 'Diabetes mellitus tipo 2 sin complicaciones', 'Endocrino'),
('F32.9', 'Episodio depresivo, no especificado', 'Mental'),
('N39.0', 'Infección de vías urinarias, sitio no especificado', 'Genitourinario'),
('K80.2', 'Colelitiasis con cólico biliar agudo', 'Digestivo'),
('J18.9', 'Neumonía, no especificada', 'Respiratorio'),
('Z00.0', 'Examen médico general', 'Preventivo'),
('A09',   'Diarrea y gastroenteritis de presunto origen infeccioso', 'Digestivo');

-- PARÁMETROS DEL SISTEMA
INSERT INTO clinica.parametros_sistema (clave, valor, descripcion) VALUES
('CLINICA_NOMBRE',    'Salud Total',          'Nombre de la clínica'),
('CLINICA_RUC',       '20123456789',          'RUC de la clínica'),
('CLINICA_DIRECCION', 'Av. Principal 123',    'Dirección fiscal'),
('CLINICA_TELEFONO',  '(01) 555-0000',        'Teléfono de contacto'),
('CLINICA_EMAIL',     'info@saludtotal.com',  'Email institucional'),
('IGV_PORCENTAJE',    '18',                   'Porcentaje de IGV aplicado'),
('CITAS_ANTELACION_MAX_DIAS', '60',           'Días máximos para agendar cita'),
('BACKUP_HORA_AUTO',  '02:00',                'Hora del backup automático'),
('SESSION_TIMEOUT_MIN', '60',                 'Minutos de inactividad antes de cerrar sesión'),
('HC_PREFIJO',        'HC-',                  'Prefijo para número de historia clínica');

-- SERVICIOS BASE
INSERT INTO clinica.servicios (codigo, nombre, tipo_servicio, especialidad_id) VALUES
('CONS-MG',   'Consulta Medicina General',  'CONSULTA', (SELECT id FROM clinica.especialidades WHERE codigo='MG')),
('CONS-CARD', 'Consulta Cardiología',       'CONSULTA', (SELECT id FROM clinica.especialidades WHERE codigo='CARD')),
('CONS-PEDIA','Consulta Pediatría',         'CONSULTA', (SELECT id FROM clinica.especialidades WHERE codigo='PEDIA')),
('CONS-GINE', 'Consulta Ginecología',       'CONSULTA', (SELECT id FROM clinica.especialidades WHERE codigo='GINE')),
('LAB-HEM',   'Hemograma Completo',         'LABORATORIO', NULL),
('LAB-GLIC',  'Glucosa en Sangre',          'LABORATORIO', NULL),
('IMG-ECO',   'Ecografía Abdominal',        'IMAGEN',    NULL),
('IMG-RX',    'Radiografía Simple',         'IMAGEN',    NULL);

-- TIPOS DE SEGURO
INSERT INTO clinica.tipos_seguro (nombre, descripcion) VALUES
('Privado', 'Aseguradoras privadas'),
('EPS',     'Entidades Prestadoras de Salud'),
('SIS',     'Seguro Integral de Salud');

-- ASEGURADORAS
INSERT INTO clinica.seguros (tipo_id, nombre, ruc, contacto, telefono, email) VALUES
((SELECT id FROM clinica.tipos_seguro WHERE nombre='Privado'), 'Rimac Seguros',  '20123456780', 'Contacto Rimac',  '(01) 555-1111', 'contacto@rimac.pe'),
((SELECT id FROM clinica.tipos_seguro WHERE nombre='Privado'), 'MAPFRE Perú',    '20123456781', 'Atención MAPFRE', '(01) 555-2222', 'atencion@mapfre.pe'),
((SELECT id FROM clinica.tipos_seguro WHERE nombre='EPS'),     'Pacífico EPS',   '20123456782', 'Contacto EPS',    '(01) 555-3333', 'eps@pacifico.pe');

-- MEDICAMENTOS COMUNES
INSERT INTO clinica.mantenedor_medicamentos (nombre_generico, nombre_comercial, presentacion, concentracion, via_admin) VALUES
('Paracetamol', 'Panadol', 'Tabletas', '500 mg', 'VO'),
('Ibuprofeno',  'Motrín',  'Tabletas', '400 mg', 'VO'),
('Omeprazol',   NULL,      'Cápsulas', '20 mg',  'VO'),
('Amoxicilina', NULL,      'Cápsulas', '500 mg', 'VO'),
('Salbutamol',  NULL,      'Inhalador','100 mcg','Inhalatoria');

-- MÉDICOS
INSERT INTO clinica.medicos (dni, cmp, nombre, apellido, especialidad_id, telefono, email, activo, created_by)
VALUES
('12345678', 'CMP-1001', 'Juan',  'Pérez', (SELECT id FROM clinica.especialidades WHERE codigo='MG'),   '(01) 700-1001', 'jperez@saludtotal.com', TRUE, (SELECT id FROM seguridad.usuarios WHERE username='admin')),
('87654321', 'CMP-2001', 'María', 'Gómez', (SELECT id FROM clinica.especialidades WHERE codigo='CARD'), '(01) 700-2001', 'mgomez@saludtotal.com', TRUE, (SELECT id FROM seguridad.usuarios WHERE username='admin'));

-- HORARIOS DE MÉDICOS (0 = Lunes)
INSERT INTO clinica.horarios_medicos (medico_id, dia_semana, hora_inicio, hora_fin, duracion_cita_min, activo)
VALUES
((SELECT id FROM clinica.medicos WHERE cmp='CMP-1001'), 0, '08:00', '12:00', 30, TRUE),
((SELECT id FROM clinica.medicos WHERE cmp='CMP-1001'), 2, '15:00', '19:00', 30, TRUE),
((SELECT id FROM clinica.medicos WHERE cmp='CMP-2001'), 1, '09:00', '13:00', 30, TRUE),
((SELECT id FROM clinica.medicos WHERE cmp='CMP-2001'), 3, '15:00', '19:00', 30, TRUE);

-- TARIFARIOS (PARTICULAR Y CON SEGURO)
INSERT INTO clinica.tarifarios (servicio_id, seguro_id, precio, vigente_desde, activo, created_by)
VALUES
((SELECT id FROM clinica.servicios WHERE codigo='CONS-MG'),   NULL,                               60.00, CURRENT_DATE, TRUE, (SELECT id FROM seguridad.usuarios WHERE username='admin')),
((SELECT id FROM clinica.servicios WHERE codigo='CONS-CARD'), NULL,                               90.00, CURRENT_DATE, TRUE, (SELECT id FROM seguridad.usuarios WHERE username='admin')),
((SELECT id FROM clinica.servicios WHERE codigo='CONS-MG'),   (SELECT id FROM clinica.seguros WHERE nombre='Rimac Seguros'), 55.00, CURRENT_DATE, TRUE, (SELECT id FROM seguridad.usuarios WHERE username='admin')),
((SELECT id FROM clinica.servicios WHERE codigo='CONS-CARD'), (SELECT id FROM clinica.seguros WHERE nombre='Rimac Seguros'), 80.00, CURRENT_DATE, TRUE, (SELECT id FROM seguridad.usuarios WHERE username='admin'));

-- PACIENTES INICIALES
INSERT INTO clinica.pacientes
 (dni, numero_hc, nombre, apellido_pat, apellido_mat, fecha_nacimiento, sexo, grupo_sanguineo,
  telefono, email, direccion, distrito, seguro_id, numero_poliza, contacto_emergencia, telefono_emergencia, created_by)
VALUES
('44556677', 'HC-000001', 'Carlos', 'Ramírez', 'Lopez', DATE '1990-05-12', 'M', 'O+', '999111222', 'carlos.ramirez@example.com',
 'Av. Salud 123', 'Lima', NULL, NULL, 'Ana Ramírez', '999333444', (SELECT id FROM seguridad.usuarios WHERE username='admin')),
('55667788', 'HC-000002', 'Lucía',  'Fernández', 'Paz', DATE '1985-10-03', 'F', 'A+', '999222333', 'lucia.fernandez@example.com',
 'Jr. Bienestar 456', 'Lima', (SELECT id FROM clinica.seguros WHERE nombre='Rimac Seguros'), 'RIM-0001', 'José Fernández', '999444555', (SELECT id FROM seguridad.usuarios WHERE username='admin'));

-- HISTORIAS CLÍNICAS
INSERT INTO clinica.historias_clinicas (paciente_id, antecedentes_personales, alergias, medicamentos_habituales, observaciones)
VALUES
((SELECT id FROM clinica.pacientes WHERE numero_hc='HC-000001'), 'Sin antecedentes de importancia', NULL, NULL, 'Primera evaluación'),
((SELECT id FROM clinica.pacientes WHERE numero_hc='HC-000002'), 'Gastritis leve', 'Penicilina', NULL, 'Control anual');

-- CITAS DE PRUEBA (HOY Y MAÑANA)
INSERT INTO clinica.citas (paciente_id, medico_id, servicio_id, fecha_cita, hora_inicio, hora_fin, estado, motivo_consulta, created_by)
VALUES
((SELECT id FROM clinica.pacientes WHERE numero_hc='HC-000001'), (SELECT id FROM clinica.medicos WHERE cmp='CMP-1001'),
 (SELECT id FROM clinica.servicios WHERE codigo='CONS-MG'), CURRENT_DATE, '09:00', '09:30', 'CONFIRMADA', 'Dolor de cabeza', (SELECT id FROM seguridad.usuarios WHERE username='admin')),
((SELECT id FROM clinica.pacientes WHERE numero_hc='HC-000002'), (SELECT id FROM clinica.medicos WHERE cmp='CMP-2001'),
 (SELECT id FROM clinica.servicios WHERE codigo='CONS-CARD'), CURRENT_DATE, '10:00', '10:30', 'PROGRAMADA', 'Chequeo cardiológico', (SELECT id FROM seguridad.usuarios WHERE username='admin')),
((SELECT id FROM clinica.pacientes WHERE numero_hc='HC-000002'), (SELECT id FROM clinica.medicos WHERE cmp='CMP-1001'),
 (SELECT id FROM clinica.servicios WHERE codigo='CONS-MG'), CURRENT_DATE + INTERVAL '1 day', '11:00', '11:30', 'PROGRAMADA', 'Control general', (SELECT id FROM seguridad.usuarios WHERE username='admin'));

-- CONSULTA DE PRUEBA (SE VINCULA A LA PRIMERA CITA)
INSERT INTO clinica.consultas
 (cita_id, paciente_id, medico_id, motivo, anamnesis, examen_fisico, temperatura, presion_arterial, frecuencia_cardiaca,
  saturacion_o2, peso_kg, talla_cm, tratamiento, indicaciones, estado)
VALUES
((SELECT id FROM clinica.citas WHERE fecha_cita = CURRENT_DATE AND hora_inicio='09:00'),
 (SELECT id FROM clinica.pacientes WHERE numero_hc='HC-000001'),
 (SELECT id FROM clinica.medicos   WHERE cmp='CMP-1001'),
 'Cefalea tensional', 'Inicio hace 2 días, sin náuseas', 'Normal', 36.8, '120/80', 72, 98, 70.0, 170.0,
 'Paracetamol 500 mg si dolor', 'Reposo relativo e hidratación', 'FINALIZADA');

-- DIAGNÓSTICO PARA LA CONSULTA
INSERT INTO clinica.diagnosticos (consulta_id, cie10_id, tipo, observacion)
VALUES
((SELECT id FROM clinica.consultas ORDER BY id DESC LIMIT 1),
 (SELECT id FROM clinica.mantenedor_cie10 WHERE codigo='J00'), 'DEFINITIVO', 'Resfriado común');

-- PRESCRIPCIÓN PARA LA CONSULTA
INSERT INTO clinica.prescripciones (consulta_id, medicamento_id, dosis, frecuencia, duracion, instrucciones)
VALUES
((SELECT id FROM clinica.consultas ORDER BY id DESC LIMIT 1),
 (SELECT id FROM clinica.mantenedor_medicamentos WHERE nombre_generico='Paracetamol'),
 '500 mg', 'Cada 8 horas', '3 días', 'Tomar después de los alimentos');

-- EXAMEN SOLICITADO
INSERT INTO clinica.examenes_solicitados (consulta_id, tipo_examen, nombre_examen, indicaciones, urgente, estado)
VALUES
((SELECT id FROM clinica.consultas ORDER BY id DESC LIMIT 1), 'LABORATORIO', 'Hemograma Completo', 'Ayuno 8 horas', FALSE, 'SOLICITADO');

-- FACTURA Y DETALLES (PARA PACIENTE HC-000001)
-- Nota: valores consistentes con IGV 18%
INSERT INTO clinica.facturas
 (numero_factura, paciente_id, consulta_id, fecha_emision, subtotal, descuento, igv, total, estado, observaciones, created_by)
VALUES
('F001-000001', (SELECT id FROM clinica.pacientes WHERE numero_hc='HC-000001'),
 (SELECT id FROM clinica.consultas ORDER BY id DESC LIMIT 1),
 NOW(), 100.00, 0.00, 18.00, 118.00, 'PENDIENTE', 'Consulta ambulatoria', (SELECT id FROM seguridad.usuarios WHERE username='admin'));

INSERT INTO clinica.detalle_facturas (factura_id, servicio_id, descripcion, cantidad, precio_unit, descuento, subtotal)
VALUES
((SELECT id FROM clinica.facturas WHERE numero_factura='F001-000001'),
 (SELECT id FROM clinica.servicios WHERE codigo='CONS-MG'),
 'Consulta Medicina General', 1, 100.00, 0.00, 100.00);

-- REGISTRO DE PAGO
INSERT INTO clinica.pagos (factura_id, monto, metodo_pago, referencia, usuario_id, observaciones)
VALUES
((SELECT id FROM clinica.facturas WHERE numero_factura='F001-000001'),
 118.00, 'EFECTIVO', 'CAJA-0001', (SELECT id FROM seguridad.usuarios WHERE username='admin'), 'Pago completo');

-- LISTA DE ESPERA (EJEMPLO)
INSERT INTO clinica.lista_espera (paciente_id, especialidad_id, prioridad, estado, observaciones)
VALUES
((SELECT id FROM clinica.pacientes WHERE numero_hc='HC-000002'),
 (SELECT id FROM clinica.especialidades WHERE codigo='CARD'),
 5, 'ESPERANDO', 'Paciente solicita evaluación prioritaria');
