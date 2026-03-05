-- ============================================================
-- ARCHIVO: 01_esquemas.sql
-- Sistema de Gestión Clínica "Salud Total"
-- ============================================================

-- Eliminar esquemas si existen (para reinstalación limpia)
DROP SCHEMA IF EXISTS clinica CASCADE;
DROP SCHEMA IF EXISTS seguridad CASCADE;
DROP SCHEMA IF EXISTS auditoria CASCADE;

-- Crear esquemas separados por dominio
CREATE SCHEMA clinica;    -- Datos clínicos y operativos
CREATE SCHEMA seguridad;  -- Usuarios, roles y permisos
CREATE SCHEMA auditoria;  -- Logs de trazabilidad

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Para búsquedas fuzzy
CREATE EXTENSION IF NOT EXISTS "btree_gist"; -- Para restricciones EXCLUDE (no solapamiento)
