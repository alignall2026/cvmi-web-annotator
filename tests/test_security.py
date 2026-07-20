import unittest
from cvmi_analyzer.core.security import hash_password, verify_password, encrypt_data, decrypt_data

class TestSecurity(unittest.TestCase):
    
    def test_password_hashing(self):
        password = "mySecretPassword123"
        h, salt = hash_password(password)
        
        # Verify hash and salt are returned as hex strings
        self.assertIsInstance(h, str)
        self.assertIsInstance(salt, str)
        self.assertEqual(len(salt), 32) # 16 bytes = 32 hex chars
        
        # Verify matching
        self.assertTrue(verify_password(password, h, salt))
        
        # Verify mismatch
        self.assertFalse(verify_password("wrongPassword", h, salt))

    def test_data_encryption_decryption(self):
        clear_text = "Harish Kanna, 1998-05-12, Male, +91-9876543210"
        encrypted = encrypt_data(clear_text)
        
        # Cipher text must be different and not clear text
        self.assertNotEqual(clear_text, encrypted)
        self.assertIsInstance(encrypted, str)
        
        # Decrypted text must match the clear text
        decrypted = decrypt_data(encrypted)
        self.assertEqual(clear_text, decrypted)

    def test_empty_encryption_handling(self):
        self.assertEqual(encrypt_data(""), "")
        self.assertEqual(decrypt_data(""), "")

if __name__ == "__main__":
    unittest.main()
