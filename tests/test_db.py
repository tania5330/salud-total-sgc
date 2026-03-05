import unittest
from database.connection import test_connection, execute_query


class TestDatabaseIntegration(unittest.TestCase):
    def test_connection(self):
        ok = test_connection()
        if not ok:
            self.skipTest("Base de datos no disponible en este entorno de prueba.")
        self.assertTrue(ok)

    def test_simple_select(self):
        if not test_connection():
            self.skipTest("Base de datos no disponible; omitiendo prueba de consulta.")
        rows = execute_query("SELECT 1 AS one")
        self.assertIsInstance(rows, list)
        self.assertGreaterEqual(len(rows), 1)
        self.assertIn("one", rows[0])
        self.assertEqual(rows[0]["one"], 1)


if __name__ == "__main__":
    unittest.main()
