import unittest
from datetime import date, timedelta
from utils.validators import (
    validar_dni, validar_email, validar_telefono,
    validar_fecha_nacimiento, validar_rango_fechas,
    validar_precio, validar_contrasena, sanitizar_texto,
    validar_codigo, validar_numero_hc,
)


class TestValidators(unittest.TestCase):
    def test_validar_dni(self):
        ok, _ = validar_dni("12345678")
        self.assertTrue(ok)
        ok, msg = validar_dni("abc")
        self.assertFalse(ok)
        self.assertIn("dígitos", msg)

    def test_validar_email(self):
        self.assertTrue(validar_email("")[0])
        self.assertTrue(validar_email("user@example.com")[0])
        self.assertFalse(validar_email("invalid@")[0])

    def test_validar_telefono(self):
        self.assertTrue(validar_telefono("987-654-321")[0])
        self.assertFalse(validar_telefono("abc-123")[0])

    def test_fecha_nacimiento(self):
        ok, _ = validar_fecha_nacimiento(date.today() - timedelta(days=365*30))
        self.assertTrue(ok)
        self.assertFalse(validar_fecha_nacimiento(date.today() + timedelta(days=1))[0])

    def test_rango_fechas(self):
        d1 = date(2024, 1, 1)
        d2 = date(2024, 2, 1)
        self.assertTrue(validar_rango_fechas(d1, d2)[0])
        self.assertFalse(validar_rango_fechas(d2, d1)[0])

    def test_validar_precio(self):
        self.assertTrue(validar_precio(10.5)[0])
        self.assertFalse(validar_precio(-1)[0])

    def test_contrasena(self):
        ok, errs = validar_contrasena("Aa123456")
        self.assertTrue(ok)
        self.assertFalse(validar_contrasena("abc")[0])

    def test_sanitizar_texto(self):
        self.assertIsNone(sanitizar_texto(""))
        self.assertEqual(sanitizar_texto("  Hola  "), "Hola")

    def test_codigo(self):
        self.assertTrue(validar_codigo("ABC-123_1")[0])
        self.assertFalse(validar_codigo("con espacios")[0])

    def test_numero_hc(self):
        self.assertTrue(validar_numero_hc("HC-000001")[0])
        self.assertFalse(validar_numero_hc("HC-1")[0])


if __name__ == "__main__":
    unittest.main()
