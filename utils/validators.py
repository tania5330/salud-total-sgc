# ============================================================
# utils/validators.py — Validadores de entrada reutilizables
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
import re
from datetime import date
from typing import Optional


def validar_dni(dni: str, longitud: int = 8) -> tuple[bool, str]:
    """
    Validar formato de DNI peruano (8 dígitos numéricos).
    Retorna (es_valido, mensaje_error).
    """
    if not dni:
        return False, "El DNI es requerido."
    if not dni.isdigit():
        return False, "El DNI debe contener solo dígitos."
    if len(dni) != longitud:
        return False, f"El DNI debe tener {longitud} dígitos."
    return True, ""


def validar_email(email: str) -> tuple[bool, str]:
    """Validar formato de email."""
    if not email:
        return True, ""  # Email es opcional en muchos formularios
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(patron, email):
        return False, "El formato del email no es válido."
    return True, ""


def validar_telefono(telefono: str) -> tuple[bool, str]:
    """Validar que el teléfono contenga solo dígitos, espacios y guiones."""
    if not telefono:
        return True, ""  # Teléfono es opcional
    limpio = re.sub(r'[\s\-\(\)]', '', telefono)
    if not limpio.isdigit():
        return False, "El teléfono solo debe contener dígitos, espacios y guiones."
    if len(limpio) < 7 or len(limpio) > 15:
        return False, "El teléfono debe tener entre 7 y 15 dígitos."
    return True, ""


def validar_fecha_nacimiento(fecha: date) -> tuple[bool, str]:
    """Validar que la fecha de nacimiento sea lógica."""
    hoy = date.today()
    if fecha > hoy:
        return False, "La fecha de nacimiento no puede ser futura."
    if (hoy - fecha).days > 365 * 130:
        return False, "La fecha de nacimiento indica una edad mayor a 130 años."
    return True, ""


def validar_rango_fechas(desde: date, hasta: date) -> tuple[bool, str]:
    """Validar que el rango de fechas sea lógico."""
    if desde > hasta:
        return False, "La fecha de inicio no puede ser posterior a la fecha de fin."
    if (hasta - desde).days > 365 * 2:
        return False, "El rango de fechas no puede superar los 2 años."
    return True, ""


def validar_precio(precio: float, nombre_campo: str = "Precio") -> tuple[bool, str]:
    """Validar que un precio sea positivo."""
    if precio is None:
        return False, f"{nombre_campo} es requerido."
    if precio < 0:
        return False, f"{nombre_campo} no puede ser negativo."
    if precio > 999999.99:
        return False, f"{nombre_campo} excede el valor máximo permitido."
    return True, ""


def validar_contrasena(password: str) -> tuple[bool, list[str]]:
    """
    Validar fortaleza de contraseña.
    Retorna (es_valida, lista_de_errores).
    """
    errores = []
    if len(password) < 8:
        errores.append("Mínimo 8 caracteres.")
    if not re.search(r'[A-Z]', password):
        errores.append("Al menos una letra mayúscula.")
    if not re.search(r'[a-z]', password):
        errores.append("Al menos una letra minúscula.")
    if not re.search(r'\d', password):
        errores.append("Al menos un dígito.")
    return len(errores) == 0, errores


def sanitizar_texto(texto: str, max_len: int = 500) -> Optional[str]:
    """
    Sanitizar texto: eliminar caracteres peligrosos y truncar.
    Retorna None si el texto está vacío.
    """
    if not texto:
        return None
    # Eliminar caracteres de control peligrosos
    limpio = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texto)
    limpio = limpio.strip()
    return limpio[:max_len] if limpio else None


def validar_codigo(codigo: str, max_len: int = 20) -> tuple[bool, str]:
    """Validar que un código sea alfanumérico sin espacios."""
    if not codigo:
        return False, "El código es requerido."
    if len(codigo) > max_len:
        return False, f"El código no puede superar {max_len} caracteres."
    if not re.match(r'^[A-Za-z0-9\-_]+$', codigo):
        return False, "El código solo puede contener letras, números, guiones y guiones bajos."
    return True, ""


def validar_numero_hc(numero_hc: str) -> tuple[bool, str]:
    """Validar formato de número de historia clínica."""
    if not numero_hc:
        return False, "El número de HC es requerido."
    if not re.match(r'^HC-\d{6}$', numero_hc.upper()):
        return False, "Formato de HC inválido. Debe ser: HC-000001"
    return True, ""
