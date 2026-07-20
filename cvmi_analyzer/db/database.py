import sqlite3
import json
from datetime import datetime
from cvmi_analyzer.config import DB_PATH, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASS
from cvmi_analyzer.core.security import encrypt_data, decrypt_data, hash_password, verify_password

class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self._seed_default_admin()

    def _init_tables(self):
        """Initializes all database tables."""
        cursor = self.conn.cursor()
        
        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # 2. Patients Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT UNIQUE NOT NULL,
                first_name_enc TEXT NOT NULL,
                last_name_enc TEXT NOT NULL,
                dob_enc TEXT NOT NULL,
                gender_enc TEXT NOT NULL,
                phone_enc TEXT,
                email_enc TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 3. Radiographs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS radiographs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_pk INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                calibration_scale REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (patient_pk) REFERENCES patients(id) ON DELETE CASCADE
            )
        """)
        
        # 4. Assessments Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                radiograph_pk INTEGER NOT NULL,
                user_pk INTEGER NOT NULL,
                landmarks_json TEXT NOT NULL,
                measurements_json TEXT NOT NULL,
                predicted_stage TEXT,
                predicted_confidence REAL,
                selected_stage TEXT NOT NULL,
                comments TEXT,
                is_ai_assisted INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (radiograph_pk) REFERENCES radiographs(id) ON DELETE CASCADE,
                FOREIGN KEY (user_pk) REFERENCES users(id)
            )
        """)
        
        self.conn.commit()

    def _seed_default_admin(self):
        """Seeds default administrator user if users table is empty."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            pw_hash, salt = hash_password(DEFAULT_ADMIN_PASS)
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (DEFAULT_ADMIN_USER, pw_hash, salt, "admin", datetime.now().isoformat())
            )
            self.conn.commit()

    # --- User Management CRUD ---
    def authenticate_user(self, username, password):
        """
        Validates username & password.
        Returns user dictionary if valid, else None.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and verify_password(password, row['password_hash'], row['salt']):
            return dict(row)
        return None

    def add_user(self, username, password, role="clinician"):
        """Adds a new user to the system."""
        cursor = self.conn.cursor()
        try:
            pw_hash, salt = hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, pw_hash, salt, role, datetime.now().isoformat())
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # User already exists

    def get_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, username, role, created_at FROM users")
        return [dict(r) for r in cursor.fetchall()]

    # --- Patient Management CRUD ---
    def add_patient(self, patient_id, first_name, last_name, dob, gender, phone="", email=""):
        """Adds a new patient, automatically encrypting the PHI columns."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        try:
            cursor.execute(
                """INSERT INTO patients 
                (patient_id, first_name_enc, last_name_enc, dob_enc, gender_enc, phone_enc, email_enc, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    patient_id,
                    encrypt_data(first_name),
                    encrypt_data(last_name),
                    encrypt_data(dob),
                    encrypt_data(gender),
                    encrypt_data(phone),
                    encrypt_data(email),
                    now,
                    now
                )
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def update_patient(self, pk, patient_id, first_name, last_name, dob, gender, phone="", email=""):
        """Updates patient demographic data with encryption."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        try:
            cursor.execute(
                """UPDATE patients SET 
                patient_id = ?, first_name_enc = ?, last_name_enc = ?, dob_enc = ?, gender_enc = ?, phone_enc = ?, email_enc = ?, updated_at = ?
                WHERE id = ?""",
                (
                    patient_id,
                    encrypt_data(first_name),
                    encrypt_data(last_name),
                    encrypt_data(dob),
                    encrypt_data(gender),
                    encrypt_data(phone),
                    encrypt_data(email),
                    now,
                    pk
                )
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_patient(self, pk):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM patients WHERE id = ?", (pk,))
        self.conn.commit()
        return True

    def get_patient(self, pk):
        """Retrieves and decrypts a patient's details."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (pk,))
        row = cursor.fetchone()
        if row:
            return self._decrypt_patient_row(row)
        return None

    def get_all_patients(self):
        """Retrieves and decrypts all patient records."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM patients ORDER BY id DESC")
        return [self._decrypt_patient_row(row) for row in cursor.fetchall()]

    def search_patients(self, query):
        """Searches patients locally. Decrypts records in memory to match query."""
        all_patients = self.get_all_patients()
        if not query:
            return all_patients
        
        q = query.lower()
        results = []
        for p in all_patients:
            if (q in p['patient_id'].lower() or
                q in p['first_name'].lower() or
                q in p['last_name'].lower() or
                q in p['phone'].lower() or
                q in p['email'].lower()):
                results.append(p)
        return results

    def _decrypt_patient_row(self, row):
        """Helper to decrypt database row into cleartext patient dict."""
        return {
            "id": row["id"],
            "patient_id": row["patient_id"],
            "first_name": decrypt_data(row["first_name_enc"]),
            "last_name": decrypt_data(row["last_name_enc"]),
            "dob": decrypt_data(row["dob_enc"]),
            "gender": decrypt_data(row["gender_enc"]),
            "phone": decrypt_data(row["phone_enc"]),
            "email": decrypt_data(row["email_enc"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    # --- Radiograph & Calibration CRUD ---
    def add_radiograph(self, patient_pk, image_path, calibration_scale=1.0):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO radiographs (patient_pk, image_path, calibration_scale, created_at) VALUES (?, ?, ?, ?)",
            (patient_pk, image_path, calibration_scale, datetime.now().isoformat())
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_radiograph_calibration(self, radiograph_pk, calibration_scale):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE radiographs SET calibration_scale = ? WHERE id = ?",
            (calibration_scale, radiograph_pk)
        )
        self.conn.commit()
        return True

    def get_radiographs_by_patient(self, patient_pk):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM radiographs WHERE patient_pk = ? ORDER BY id DESC", (patient_pk,))
        return [dict(r) for r in cursor.fetchall()]

    # --- Assessment CRUD ---
    def add_assessment(self, radiograph_pk, user_pk, landmarks, measurements, predicted_stage, predicted_confidence, selected_stage, comments="", is_ai_assisted=0):
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO assessments 
            (radiograph_pk, user_pk, landmarks_json, measurements_json, predicted_stage, predicted_confidence, selected_stage, comments, is_ai_assisted, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                radiograph_pk,
                user_pk,
                json.dumps(landmarks),
                json.dumps(measurements),
                predicted_stage,
                predicted_confidence,
                selected_stage,
                comments,
                is_ai_assisted,
                datetime.now().isoformat()
            )
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_assessments_by_radiograph(self, radiograph_pk):
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT a.*, u.username as examiner_name 
            FROM assessments a 
            JOIN users u ON a.user_pk = u.id 
            WHERE a.radiograph_pk = ? ORDER BY a.id DESC""", 
            (radiograph_pk,)
        )
        results = []
        for r in cursor.fetchall():
            d = dict(r)
            d['landmarks'] = json.loads(d['landmarks_json'])
            d['measurements'] = json.loads(d['measurements_json'])
            results.append(d)
        return results

    def get_all_assessments(self):
        """Returns all assessments in the database with patient details for the research module."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT a.*, u.username as examiner_name, r.image_path, r.calibration_scale, p.patient_id, p.id as patient_pk, p.first_name_enc, p.last_name_enc 
            FROM assessments a 
            JOIN users u ON a.user_pk = u.id 
            JOIN radiographs r ON a.radiograph_pk = r.id
            JOIN patients p ON r.patient_pk = p.id
            ORDER BY a.id DESC"""
        )
        results = []
        for r in cursor.fetchall():
            d = dict(r)
            d['landmarks'] = json.loads(d['landmarks_json'])
            d['measurements'] = json.loads(d['measurements_json'])
            d['first_name'] = decrypt_data(d['first_name_enc'])
            d['last_name'] = decrypt_data(d['last_name_enc'])
            results.append(d)
        return results

    def close(self):
        self.conn.close()
