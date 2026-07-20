import unittest
import os
import tempfile
from cvmi_analyzer.db.database import Database

class TestDatabase(unittest.TestCase):
    
    def setUp(self):
        # Initialize an isolated temporary file-based database for each test run
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp()
        self.db = Database(db_path=self.temp_db_path)

    def tearDown(self):
        self.db.close()
        os.close(self.temp_db_fd)
        os.remove(self.temp_db_path)

    def test_default_admin_seeded(self):
        # Verify admin user exists
        user = self.db.authenticate_user("admin", "admin123")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "admin")

    def test_user_management(self):
        # Add new user
        success = self.db.add_user("clinician1", "securepass12", "clinician")
        self.assertTrue(success)
        
        # Verify authentication
        user = self.db.authenticate_user("clinician1", "securepass12")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "clinician")
        
        # Verify double insert failure
        fail_insert = self.db.add_user("clinician1", "anotherpass", "clinician")
        self.assertFalse(fail_insert)

    def test_patient_management(self):
        # Create Patient
        pk = self.db.add_patient(
            patient_id="PT-TEST-001",
            first_name="Harish",
            last_name="Kanna",
            dob="1998-10-15",
            gender="Male",
            phone="+91-9988776655",
            email="harish@example.com"
        )
        self.assertIsNotNone(pk)
        
        # Retrieve and verify decryption
        patient = self.db.get_patient(pk)
        self.assertIsNotNone(patient)
        self.assertEqual(patient["patient_id"], "PT-TEST-001")
        self.assertEqual(patient["first_name"], "Harish")
        self.assertEqual(patient["last_name"], "Kanna")
        self.assertEqual(patient["dob"], "1998-10-15")
        self.assertEqual(patient["gender"], "Male")
        
        # Search patient
        search_res = self.db.search_patients("harish")
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0]["id"], pk)
        
        # Search case-insensitivity and sub-strings
        search_res2 = self.db.search_patients("KANNA")
        self.assertEqual(len(search_res2), 1)
        
        # Update Patient
        update_success = self.db.update_patient(
            pk, "PT-TEST-001", "Harish Kumar", "Kanna", "1998-10-15", "Male", "+91-0000000000", "harish.k@example.com"
        )
        self.assertTrue(update_success)
        
        updated_patient = self.db.get_patient(pk)
        self.assertEqual(updated_patient["first_name"], "Harish Kumar")
        self.assertEqual(updated_patient["phone"], "+91-0000000000")
        
        # Delete Patient
        self.db.delete_patient(pk)
        self.assertIsNone(self.db.get_patient(pk))

if __name__ == "__main__":
    unittest.main()
