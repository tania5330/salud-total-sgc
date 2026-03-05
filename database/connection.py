# ============================================================
# database/connection.py — Pool de conexiones SQLAlchemy
# ============================================================
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging
from config import DATABASE_URL, DEBUG

logger = logging.getLogger(__name__)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Motor con pool de conexiones optimizado para producción
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,   # Reciclar conexiones cada 30 minutos
    echo=DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@contextmanager
def get_db():
    """Context manager para obtener sesión de BD con manejo automático de errores."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error en transacción de BD: {e}")
        raise
    finally:
        session.close()


def execute_query(query: str, params: dict = None):
    """Ejecutar query de solo lectura y retornar resultados como lista de dicts."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return result.mappings().all()
    except Exception as e:
        logger.error(f"Error al ejecutar consulta: {e}")
        raise


def init_db():
    """
    Crear esquemas y tablas si no existen.
    Se puede ejecutar en cada arranque; es idempotente.
    """
    # Importa modelos para que todas las tablas estén registradas en Base.metadata
    import database.models  # noqa: F401

    # Crear esquemas (idempotente)
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS seguridad"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS clinica"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS auditoria"))
    except Exception as e:
        logger.error(f"Error al crear esquemas: {e}")
        raise

    # Crear tablas con el engine para que SQLAlchemy resuelva el orden por FKs
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Error al crear tablas: {e}")
        raise

    # Índices (03) y datos iniciales (04) — solo si la BD está vacía
    try:
        _run_indices_if_needed()
        _run_seed_data_if_needed()
    except Exception as e:
        logger.error(f"Error al cargar índices o datos iniciales: {e}")
        raise


def _run_indices_if_needed():
    """Ejecuta 03_indices.sql usando CREATE INDEX IF NOT EXISTS."""
    path = os.path.join(_THIS_DIR, "03_indices.sql")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # Reemplazar CREATE INDEX por CREATE INDEX IF NOT EXISTS para idempotencia
    content = content.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ")
    statements = [s.strip() for s in content.split(";") if s.strip() and not s.strip().startswith("--")]
    with engine.begin() as conn:
        for stmt in statements:
            if "CREATE INDEX" in stmt:
                try:
                    conn.execute(text(stmt + ";"))
                except Exception as e:
                    logger.debug(f"Índice ya existe o error ignorable: {e}")


def _run_seed_data_if_needed():
    """Ejecuta 04_datos_iniciales.sql solo si no hay usuarios (BD recién creada)."""
    with engine.connect() as conn:
        r = conn.execute(text("SELECT COUNT(*) AS n FROM seguridad.usuarios"))
        row = r.mappings().first()
        n = (row["n"] or 0) if row else 0
    if n > 0:
        return
    path = os.path.join(_THIS_DIR, "04_datos_iniciales.sql")
    if not os.path.isfile(path):
        logger.warning("No se encontró 04_datos_iniciales.sql; no se cargaron datos iniciales.")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # Dividir por ;\n para obtener sentencias (evitar partir dentro de valores)
    statements = []
    for block in content.split(";\n"):
        block = block.strip()
        if not block or block.startswith("--"):
            continue
        # Quitar líneas que son solo comentarios SQL
        lines = [line for line in block.split("\n") if not line.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if stmt and ("INSERT" in stmt or "UPDATE" in stmt or "DELETE" in stmt):
            statements.append(stmt)
    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                logger.error(f"Error en sentencia de datos iniciales: {e}")
                raise


def test_connection():
    """
    Verificar que la conexión a la BD es exitosa.
    Retorna (True, None) si conecta, o (False, mensaje_error) si falla.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        err = str(e).strip()
        logger.error(f"Error de conexión a BD: {e}")
        # Mensaje breve para el usuario (sin exponer contraseñas)
        if "password" in err.lower() or "authentication" in err.lower():
            msg = "Error de autenticación. Revise usuario y contraseña (DB_USER/DB_PASSWORD o DATABASE_URL)."
        elif "connect" in err.lower() or "refused" in err.lower() or "timeout" in err.lower():
            msg = "No se pudo conectar al servidor. Revise host/puerto y que PostgreSQL esté en ejecución."
        elif "does not exist" in err.lower() or "database" in err.lower():
            msg = "La base de datos no existe o el nombre es incorrecto (DB_NAME o en DATABASE_URL)."
        elif "ssl" in err.lower():
            msg = "Error SSL. Si usa Render, la URL debe ser la External Database URL con sslmode."
        else:
            msg = err[:200] if len(err) > 200 else err
        return False, msg
