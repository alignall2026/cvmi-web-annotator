from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, 
    QPushButton, QMessageBox, QDialog, QLabel, QComboBox, QListWidgetItem
)
from PySide6.QtCore import Signal, Qt
from cvmi_analyzer.db.database import Database

class PatientPanel(QFrame):
    """
    Left-hand panel displaying a searchable list of patients,
    with options to add, edit, or delete patient files.
    """
    patient_selected = Signal(int) # Emits patient primary key (pk) when double-clicked or selected
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setObjectName("sidebarFrame")
        self.setFixedWidth(260)
        
        self.init_ui()
        self.refresh_patient_list()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Section Header
        lbl_header = QLabel("Patient Registry")
        lbl_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #00d2c4;")
        layout.addWidget(lbl_header)
        
        # Search Box
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("Search patients...")
        self.txt_search.textChanged.connect(self.refresh_patient_list)
        layout.addWidget(self.txt_search)
        
        # Patient List Widget
        self.list_widget = QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add", self)
        self.btn_add.clicked.connect(self.show_add_patient_dialog)
        
        self.btn_edit = QPushButton("Edit", self)
        self.btn_edit.clicked.connect(self.show_edit_patient_dialog)
        
        self.btn_delete = QPushButton("Delete", self)
        self.btn_delete.setStyleSheet("QPushButton { color: #ff6060; }")
        self.btn_delete.clicked.connect(self.handle_delete)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

    def refresh_patient_list(self):
        """Fetches patients matching the search term, and renders them in the list."""
        self.list_widget.clear()
        query = self.txt_search.text()
        
        patients = self.db.search_patients(query)
        for p in patients:
            # Custom display: e.g. "KANNA, Harish (ID: CVMI-0982)"
            name_text = f"{p['last_name'].upper()}, {p['first_name']} (ID: {p['patient_id']})"
            item = QListWidgetItem(name_text)
            # Store primary key in UserRole for easy lookup
            item.setData(Qt.UserRole, p['id'])
            self.list_widget.addItem(item)

    def _on_item_double_clicked(self, item):
        patient_pk = item.data(Qt.UserRole)
        self.patient_selected.emit(patient_pk)

    def get_selected_patient_pk(self) -> int:
        """Returns the primary key of the currently selected patient, or None."""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].data(Qt.UserRole)

    # --- Patient Creation / Editing Modals ---
    def show_add_patient_dialog(self):
        self._show_patient_dialog(title="Register New Patient")

    def show_edit_patient_dialog(self):
        pk = self.get_selected_patient_pk()
        if pk is None:
            QMessageBox.warning(self, "Selection Error", "Please select a patient from the list to edit.")
            return
        
        patient_data = self.db.get_patient(pk)
        if patient_data:
            self._show_patient_dialog(title="Edit Patient Details", existing_data=patient_data)

    def _show_patient_dialog(self, title: str, existing_data: dict = None):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setFixedSize(340, 360)
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Input fields
        txt_id = QLineEdit(dlg)
        txt_id.setPlaceholderText("Patient ID (e.g. PT-2026-001)")
        layout.addWidget(txt_id)
        
        txt_first = QLineEdit(dlg)
        txt_first.setPlaceholderText("First Name")
        layout.addWidget(txt_first)
        
        txt_last = QLineEdit(dlg)
        txt_last.setPlaceholderText("Last Name")
        layout.addWidget(txt_last)
        
        txt_dob = QLineEdit(dlg)
        txt_dob.setPlaceholderText("Date of Birth (YYYY-MM-DD)")
        layout.addWidget(txt_dob)
        
        cb_gender = QComboBox(dlg)
        cb_gender.addItems(["Male", "Female", "Other"])
        layout.addWidget(cb_gender)
        
        txt_phone = QLineEdit(dlg)
        txt_phone.setPlaceholderText("Phone Number")
        layout.addWidget(txt_phone)
        
        txt_email = QLineEdit(dlg)
        txt_email.setPlaceholderText("Email")
        layout.addWidget(txt_email)
        
        # Populate if editing
        if existing_data:
            txt_id.setText(existing_data["patient_id"])
            txt_first.setText(existing_data["first_name"])
            txt_last.setText(existing_data["last_name"])
            txt_dob.setText(existing_data["dob"])
            cb_gender.setCurrentText(existing_data["gender"])
            txt_phone.setText(existing_data["phone"])
            txt_email.setText(existing_data["email"])
            
        btn_save = QPushButton("Save Patient", dlg)
        btn_save.setObjectName("accentButton")
        layout.addWidget(btn_save)
        
        def save_record():
            pat_id = txt_id.text().strip()
            first = txt_first.text().strip()
            last = txt_last.text().strip()
            dob = txt_dob.text().strip()
            gender = cb_gender.currentText()
            phone = txt_phone.text().strip()
            email = txt_email.text().strip()
            
            if not all([pat_id, first, last, dob]):
                QMessageBox.warning(dlg, "Error", "ID, First Name, Last Name, and DOB are required fields.")
                return
                
            if existing_data:
                success = self.db.update_patient(
                    existing_data["id"], pat_id, first, last, dob, gender, phone, email
                )
            else:
                success = self.db.add_patient(
                    pat_id, first, last, dob, gender, phone, email
                )
                
            if success:
                QMessageBox.information(dlg, "Success", "Patient record saved successfully.")
                self.refresh_patient_list()
                dlg.accept()
            else:
                QMessageBox.critical(dlg, "Database Error", "Failed to save. Patient ID may be already in use.")
                
        btn_save.clicked.connect(save_record)
        dlg.exec()

    def handle_delete(self):
        pk = self.get_selected_patient_pk()
        if pk is None:
            QMessageBox.warning(self, "Selection Error", "Please select a patient to delete.")
            return
            
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to permanently delete this patient record and all associated radiographs and clinical reports?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            self.db.delete_patient(pk)
            self.refresh_patient_list()
            QMessageBox.information(self, "Deleted", "Patient record removed.")
