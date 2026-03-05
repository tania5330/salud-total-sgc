import unittest
from utils.auth import hash_password, verify_password, create_token, decode_token


class TestAuth(unittest.TestCase):
    def test_bcrypt_hash_verify(self):
        pwd = "Aa123456!"
        h = hash_password(pwd)
        self.assertTrue(verify_password(pwd, h))
        self.assertFalse(verify_password("wrong", h))

    def test_jwt_encode_decode(self):
        token = create_token(1, "tester", ["ADMINISTRADOR"])
        payload = decode_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("username"), "tester")
        self.assertIn("ADMINISTRADOR", payload.get("roles", []))


if __name__ == "__main__":
    unittest.main()
