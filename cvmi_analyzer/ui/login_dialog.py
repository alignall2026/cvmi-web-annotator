from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
from cvmi_analyzer.db.database import Database

class LoginDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.authenticated_user = None
        
        self.setWindowTitle("CVMI Analyzer Pro - Security Login")
        self.setFixedSize(380, 260)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("CVMI Analyzer Pro")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d2c4; margin-bottom: 5px;")
        layout.addWidget(title)
        
        # Username Input
        self.txt_username = QLineEdit(self)
        self.txt_username.setPlaceholderText("Username")
        layout.addWidget(self.txt_username)
        
        # Password Input
        self.txt_password = QLineEdit(self)
        self.txt_password.setPlaceholderText("Password")
        self.txt_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.txt_password)
        
        # Buttons Row
        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("Log In", self)
        self.btn_login.setObjectName("accentButton")
        self.btn_login.clicked.connect(self.handle_login)
        
        self.btn_register = QPushButton("Register New", self)
        self.btn_register.clicked.connect(self.handle_register_dialog)
        
        btn_layout.addWidget(self.btn_register)
        btn_layout.addWidget(self.btn_login)
        layout.addLayout(btn_layout)
        
        # System status label
        self.lbl_status = QLabel("Secure local authentication active")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #72727a; font-size: 11px;")
        layout.addWidget(self.lbl_status)

    def handle_login(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "Please provide both username and password.")
            return
            
        user = self.db.authenticate_user(username, password)
        if user:
            self.authenticated_user = user
            self.accept()
        else:
            QMessageBox.critical(self, "Access Denied", "Invalid username or password.")

    def handle_register_dialog(self):
        """Displays registration dialog to create a new user profile."""
        reg_dialog = QDialog(self)
        reg_dialog.setWindowTitle("User Registration")
        reg_dialog.setFixedSize(320, 240)
        
        reg_layout = QVBoxLayout(reg_dialog)
        reg_layout.setContentsMargins(15, 15, 15, 15)
        reg_layout.setSpacing(10)
        
        txt_reg_user = QLineEdit(reg_dialog)
        txt_reg_user.setPlaceholderText("New Username")
        reg_layout.addWidget(txt_reg_user)
        
        txt_reg_pass = QLineEdit(reg_dialog)
        txt_reg_pass.setPlaceholderText("New Password")
        txt_reg_pass.setEchoMode(QLineEdit.Password)
        reg_layout.addWidget(txt_reg_pass)
        
        cb_role = QComboBox(reg_dialog)
        cb_role.addItems(["Clinician", "Administrator"])
        reg_layout.addWidget(cb_role)
        
        btn_save = QPushButton("Register Account", reg_dialog)
        btn_save.setObjectName("accentButton")
        
        def do_register():
            user_val = txt_reg_user.text().strip()
            pass_val = txt_reg_pass.text()
            role_val = "admin" if cb_role.currentText() == "Administrator" else "clinician"
            
            if not user_val or len(pass_val) < 6:
                QMessageBox.warning(reg_dialog, "Error", "Username cannot be empty, and password must be at least 6 characters.")
                return
                
            success = self.db.add_user(user_val, pass_val, role_val)
            if success:
                QMessageBox.information(reg_dialog, "Success", f"User {user_val} registered successfully.")
                reg_dialog.accept()
            else:
                QMessageBox.critical(reg_dialog, "Error", "Username already exists in the database.")
                
        btn_save.clicked.connect(do_register)
        reg_layout.addWidget(btn_save)
        
        reg_dialog.exec()
