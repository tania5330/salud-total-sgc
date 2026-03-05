# Salud Total — Sistema de Gestión Clínica

Aplicación web construida con **Streamlit** y **SQLAlchemy** para la gestión clínica integral (pacientes, citas, facturación, auditoría, etc.).

## Requisitos

- Python 3.10+ (recomendado)
- PostgreSQL 13+ (local o en la nube)

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Configuración de variables de entorno

La app usa `python-dotenv` y variables de entorno estándar.

### Opción A: URL completa (ideal para Render PostgreSQL)

Define una variable de entorno:

- `DATABASE_URL` — URL completa de conexión PostgreSQL.

Ejemplo (Render / proveedores similares):

```bash
DATABASE_URL=postgresql+psycopg2://usuario:password@host:puerto/nombre_bd
```

Si tu proveedor expone una URL que empieza por `postgres://`, la app la convertirá automáticamente a `postgresql+psycopg2://` para que funcione con SQLAlchemy.

### Opción B: Parámetros individuales (entorno local)

Usa un archivo `.env` (basado en `.env.example`) o variables de entorno:

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `SECRET_KEY`

## Inicialización automática de la base de datos

Al arrancar la aplicación:

1. Se verifica la conexión a PostgreSQL.
2. Se crean (si no existen) los **esquemas** `seguridad`, `clinica` y `auditoria`.
3. SQLAlchemy crea todas las **tablas** definidas en `database/models.py`.

Este proceso es **idempotente** y no muestra ningún mensaje de “base de datos inicializada” en la interfaz de Streamlit.

## Ejecución local

```bash
streamlit run app.py
```

## Despliegue en Streamlit Cloud

1. Sube este proyecto a un repositorio en GitHub.
2. En Streamlit Cloud, crea una nueva app apuntando a ese repositorio.
3. En **Advanced settings → Secrets** define al menos:
   - `DATABASE_URL` (la URL de tu base de datos PostgreSQL en Render)
   - `SECRET_KEY`

## Base de datos en Render (PostgreSQL)

1. Crea un servicio de base de datos PostgreSQL en Render.
2. Copia la URL de conexión que Render entrega.
3. Pégala en:
   - Render (si usas un backend allí), o
   - Streamlit Cloud (en **Secrets**) como `DATABASE_URL`.

La app se encargará de crear los esquemas y tablas al primer arranque exitoso.

# README.md — Sistema de Gestión Clínica "Salud Total"

## 🏥 Descripción
Sistema de información integral para la Clínica Salud Total, desarrollado con
Python + Streamlit + PostgreSQL.

## 📋 Requisitos previos
- Python 3.11+
- PostgreSQL 15+
- pip

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-org/salud-total.git
cd salud-total
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con las credenciales de tu BD
```

Contenido mínimo del `.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=salud_total
DB_USER=postgres
DB_PASSWORD=tu_password_seguro
SECRET_KEY=clave-secreta-muy-larga-y-aleatoria
JWT_EXPIRE_HOURS=8
BACKUP_DIR=./backups
DEBUG=false
```

### 4. Crear la base de datos y ejecutar scripts DDL
```bash
psql -U postgres -c "CREATE DATABASE salud_total;"
psql -U postgres -d salud_total -f database/01_esquemas.sql
psql -U postgres -d salud_total -f database/02_tablas.sql
psql -U postgres -d salud_total -f database/03_indices.sql
psql -U postgres -d salud_total -f database/04_datos_iniciales.sql
```

### 5. Actualizar el hash de contraseña del admin
```python
python -c "import bcrypt; print(bcrypt.hashpw(b'admin', bcrypt.gensalt(12)).decode())"
# Copiar el hash y actualizar en BD:
# UPDATE seguridad.usuarios SET password_hash='hash_copiado' WHERE username='admin';
```

### 6. Ejecutar la aplicación
```bash
streamlit run app.py
```

Acceder en: **http://localhost:8501**

## 🗂️ Estructura del proyecto
```
salud_total/
├── app.py                    # Entry point
├── config.py                 # Configuración
├── .env                      # Variables de entorno (NO commitear)
├── requirements.txt
├── database/
│   ├── 01_esquemas.sql
│   ├── 02_tablas.sql
│   ├── 03_indices.sql
│   ├── 04_datos_iniciales.sql
│   ├── connection.py
│   └── models.py
├── modules/                  # Módulos del sistema
├── utils/                    # Utilidades compartidas
├── assets/styles.css
└── backups/                  # Directorio de backups
```

## 👤 Acceso inicial
| Campo | Valor |
|-------|-------|
| Usuario | `admin` |
| Contraseña | La que configuraste en paso 5 |

⚠️ **Cambiar la contraseña en el primer acceso.**

## 🔐 Roles del sistema
| Rol | Acceso |
|-----|--------|
| ADMINISTRADOR | Total |
| MÉDICO | Pacientes, Citas, Historia Clínica, Reportes |
| ENFERMERA | Pacientes, Citas, Triaje |
| RECEPCIONISTA | Pacientes, Citas, Facturación básica |
| CONTADOR | Facturación completa, Reportes financieros |

## 🚀 Despliegue en producción
- Usar Nginx como reverse proxy
- Configurar SSL/TLS con Let's Encrypt
- Ejecutar con `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`
- Configurar servicio systemd para inicio automático
- Activar backup automático configurando cron con `pg_dump`
```

---

## 📊 Arquitectura del sistema
```
┌─────────────────────────────────────────────────────────────────┐
│                    SALUD TOTAL — ARQUITECTURA                    │
└─────────────────────────────────────────────────────────────────┘

  CLIENTE (Browser / Móvil)
  └─── HTTP/HTTPS ──────────────────────────────────────────────►
                                                                  │
  ┌───────────────────────────────────────────────────────────────┤
  │                   STREAMLIT APP (Python)                       │
  │                                                               │
  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
  │  │  auth/  │  │dashboard/│  │pacientes/│  │   citas/     │  │
  │  └────┬────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
  │       │            │             │                │           │
  │  ┌────▼────────────▼─────────────▼────────────────▼───────┐  │
  │  │              utils/ (auth, audit, pdf, validators)      │  │
  │  └────────────────────────────┬────────────────────────────┘  │
  │                               │                               │
  │  ┌────────────────────────────▼────────────────────────────┐  │
  │  │           database/ (SQLAlchemy + psycopg2)             │  │
  │  └────────────────────────────┬────────────────────────────┘  │
  └───────────────────────────────┼───────────────────────────────┘
                                  │
  ┌───────────────────────────────▼───────────────────────────────┐
  │                  PostgreSQL 15+                                │
  │                                                               │
  │  Schema: clinica          Schema: seguridad   Schema: audit   │
  │  ┌─────────────────────┐  ┌─────────────────┐ ┌───────────┐  │
  │  │ pacientes           │  │ usuarios        │ │log_audit  │  │
  │  │ historias_clinicas  │  │ roles           │ │           │  │
  │  │ citas               │  │ permisos        │ └───────────┘  │
  │  │ consultas           │  │ sesiones        │               │
  │  │ diagnosticos        │  └─────────────────┘               │
  │  │ facturas / pagos    │                                     │
  │  │ medicos             │                                     │
  │  └─────────────────────┘                                     │
  └───────────────────────────────────────────────────────────────┘