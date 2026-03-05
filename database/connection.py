# ============================================================
# database/connection.py — Pool de conexiones SQLAlchemy
# ============================================================
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging
from config import DATABASE_URL, DEBUG

logger = logging.getLogger(__name__)

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
    try:
        # Importa modelos para que todas las tablas estén registradas en Base.metadata
        import database.models  # noqa: F401

        with engine.begin() as conn:
            # Esquemas usados por los modelos
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS seguridad"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS clinica"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS auditoria"))

            # Crear tablas definidas en los modelos
            Base.metadata.create_all(bind=conn)
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        raise


def test_connection() -> bool:
    """Verificar que la conexión a la BD es exitosa."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Error de conexión a BD: {e}")
        return False
