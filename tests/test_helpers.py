import unittest
from datetime import date
from utils.helpers import calcular_edad, formatear_moneda, formatear_fecha


class TestHelpers(unittest.TestCase):
    def test_calcular_edad(self):
        nacimiento = date.today().replace(year=date.today().year - 20)
        edad = calcular_edad(nacimiento)
        self.assertTrue(19 <= edad <= 20)

    def test_formatear_moneda(self):
        self.assertIn("S/", formatear_moneda(1234.5))

    def test_formatear_fecha(self):
        self.assertEqual(formatear_fecha(date(2024, 1, 2)), "02/01/2024")
        self.assertEqual(formatear_fecha(None), "—")


if __name__ == "__main__":
    unittest.main()
