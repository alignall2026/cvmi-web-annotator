import os
import shutil
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
    QFileDialog, QMessageBox, QLabel, QListWidget, QStatusBar, QApplication
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QImage, QPixmap

from cvmi_analyzer.config import APP_NAME, ORG_NAME, DEFAULT_CALIBRATION_SCALE, APP_DATA_DIR
from cvmi_analyzer.db.database import Database
from cvmi_analyzer.core.cvmi import calculate_vertebra_metrics, determine_cvmi_stage
from cvmi_analyzer.core.security import create_backup, restore_backup
from cvmi_analyzer.ai.detector import CVMIDetector
from cvmi_analyzer.ai.classifier import CVMIClassifier
from cvmi_analyzer.reports.pdf_generator import generate_pdf_report

from cvmi_analyzer.ui.widgets.ribbon import RibbonBar
from cvmi_analyzer.ui.patient_panel import PatientPanel
from cvmi_analyzer.ui.widgets.canvas import CephCanvas
from cvmi_analyzer.ui.results_panel import ResultsPanel
from cvmi_analyzer.ui.themes import apply_theme

# Import Modals
from cvmi_analyzer.ui.research_panel import ResearchPanel
from cvmi_analyzer.ui.training_panel import TrainingPanel

class MainWindow(QMainWindow):
    """
    Main application shell implementing the Ribbon Toolbar,
    patient registries, interactive radiograph canvas, and AI analysis widgets.
    """
    def __init__(self, db: Database, user_profile: dict):
        super().__init__()
        self.db = db
        self.user = user_profile
        self.current_theme = "dark"
        
        # State variables
        self.current_patient_pk = None
        self.current_radiograph = None
        self.current_landmarks = {}
        self.current_metrics = {}
        self.last_predicted_stage = None
        self.last_predicted_conf = None
        
        # Initialize AI Engines
        self.detector = CVMIDetector()
        self.classifier = CVMIClassifier()
        
        self.setWindowTitle(f"{APP_NAME} - Clinician: {self.user['username']} ({self.user['role'].upper()})")
        self.resize(1280, 800)
        
        self.init_ui()
        self.log_status(f"Welcome, {self.user['username']}. Application initialized successfully.")

    def init_ui(self):
        # 1. Main container widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 2. Add Ribbon Toolbar
        self.ribbon = RibbonBar(self)
        self.ribbon.action_triggered.connect(self.handle_ribbon_action)
        main_layout.addWidget(self.ribbon)
        
        # 3. Add Splitter Panel Layout (Patient list | Canvas | Metrics)
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setStyleSheet("QSplitter::handle { background-color: #2b2b35; width: 4px; }")
        
        # Left Panel (Patients list)
        self.patient_panel = PatientPanel(self.db, self)
        self.patient_panel.patient_selected.connect(self.load_patient_record)
        splitter.addWidget(self.patient_panel)
        
        # Center Viewer Canvas
        self.canvas = CephCanvas(self)
        self.canvas.landmark_moved_signal.connect(self.handle_landmark_move)
        self.canvas.calibration_completed.connect(self.handle_calibration_scale)
        splitter.addWidget(self.canvas)
        
        # Right Results Panel
        self.results_panel = ResultsPanel(self)
        self.results_panel.save_assessment_requested.connect(self.save_assessment)
        splitter.addWidget(self.results_panel)
        
        # Set default stretch factors
        splitter.setStretchFactor(0, 1) # Left
        splitter.setStretchFactor(1, 3) # Center
        splitter.setStretchFactor(2, 1) # Right
        
        main_layout.addWidget(splitter)
        
        # 4. Bottom Status Bar & Log Console
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        
        self.lbl_status_msg = QLabel("Ready")
        self.status_bar.addWidget(self.lbl_status_msg)

    # --- Logging and Status helpers ---
    def log_status(self, text: str):
        """Outputs action status logs to console and status bars."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.lbl_status_msg.setText(f"[{timestamp}] {text}")
        print(f"[{timestamp}] {text}")

    # --- Ribbon Event Orchestration ---
    def handle_ribbon_action(self, action_id: str):
        self.log_status(f"Ribbon Action: {action_id}")
        
        if action_id == "new_patient":
            self.patient_panel.show_add_patient_dialog()
            
        elif action_id == "edit_patient":
            self.patient_panel.show_edit_patient_dialog()
            
        elif action_id == "import_image":
            self.import_patient_radiograph()
            
        elif action_id == "save_db":
            self.log_status("Database records are automatically saved locally.")
            QMessageBox.information(self, "Data Saved", "Local SQLite database commits saved successfully.")
            
        elif action_id == "filter_clahe":
            self.canvas.apply_clahe()
            self.log_status("CLAHE contrast filter applied.")
            
        elif action_id == "filter_equalize":
            self.canvas.apply_equalize_hist()
            self.log_status("Global Histogram Equalization filter applied.")
            
        elif action_id == "filter_sharpen":
            self.canvas.apply_sharpen()
            self.log_status("Edge sharpening filter applied.")
            
        elif action_id == "filter_reset":
            self.canvas.reset_filters()
            self.log_status("Image filters reverted.")
            
        elif action_id == "rotate_left":
            self.canvas.rotate(-90)
            self.log_status("Rotated view 90 degrees counter-clockwise.")
            
        elif action_id == "rotate_right":
            self.canvas.rotate(90)
            self.log_status("Rotated view 90 degrees clockwise.")
            
        elif action_id == "calibrate_scale":
            # Toggle calibration mode in QGraphicsView
            is_checked = self.ribbon.btn_calibrate.isChecked()
            self.canvas.calibration_mode = is_checked
            if is_checked:
                self.log_status("Calibration Ruler active. Click 2 points along ruler to calibrate.")
                QMessageBox.information(
                    self, "Calibration Mode", 
                    "Please click 2 points on the radiograph representing a known clinical distance (e.g. ruler markings)."
                )
            else:
                self.log_status("Calibration Ruler deactivated.")
                
        elif action_id == "manual_mode":
            # Put landmarks standard layout on screen if not present
            self.enable_manual_landmark_placement()
            
        elif action_id == "ai_detect":
            self.run_ai_pipeline()
            
        elif action_id == "clear_landmarks":
            self.canvas.clear_all()
            self.results_panel.clear_ui()
            self.current_landmarks.clear()
            self.current_metrics.clear()
            self.log_status("Landmarks cleared.")
            
        elif action_id == "generate_report":
            self.generate_report_pdf()
            
        elif action_id == "show_research":
            self.open_research_suite()
            
        elif action_id == "export_csv":
            self.open_research_suite(tab_index=0)
            
        elif action_id == "export_excel":
            self.open_research_suite(tab_index=0)
            
        elif action_id == "open_annotation_tool":
            from cvmi_analyzer.ui.annotation_tool import AnnotationToolWindow
            self.annotation_win = AnnotationToolWindow()
            self.annotation_win.show()
            self.log_status("Annotation tool opened.")
            
        elif action_id == "show_training":
            if self.user["role"] != "admin":
                QMessageBox.warning(self, "Security Check", "Access denied. Model retraining requires Administrator permissions.")
                return
            self.open_ai_training()
            
        elif action_id == "load_weights":
            self.load_custom_model_weights()
            
        elif action_id == "backup_db":
            self.trigger_db_backup()
            
        elif action_id == "restore_db":
            if self.user["role"] != "admin":
                QMessageBox.warning(self, "Security Check", "Access denied. Database restoration requires Administrator permissions.")
                return
            self.trigger_db_restore()
            
        elif action_id == "admin_panel":
            self.show_admin_panel()
            
        elif action_id == "switch_theme":
            self.toggle_theme()
            
        elif action_id == "logout":
            self.handle_logout()

    # --- Core Patient & Radiograph Logic ---
    def load_patient_record(self, patient_pk: int):
        self.current_patient_pk = patient_pk
        patient = self.db.get_patient(patient_pk)
        
        if not patient:
            return
            
        self.log_status(f"Patient Record Loaded: {patient['first_name']} {patient['last_name']}")
        
        # Query existing radiographs
        radiographs = self.db.get_radiographs_by_patient(patient_pk)
        if radiographs:
            # Load latest radiograph
            self.current_radiograph = radiographs[0]
            img_loaded = self.canvas.load_image(self.current_radiograph["image_path"])
            
            if img_loaded:
                self.canvas.calibration_scale = self.current_radiograph["calibration_scale"]
                self.log_status(f"Radiograph loaded: {os.path.basename(self.current_radiograph['image_path'])} (Scale: {self.canvas.calibration_scale:.2f} px/mm)")
                
                # Check for existing assessments on this image
                assessments = self.db.get_assessments_by_radiograph(self.current_radiograph["id"])
                if assessments:
                    latest_a = assessments[0]
                    self.current_landmarks = latest_a["landmarks"]
                    self.current_metrics = latest_a["measurements"]
                    
                    self.canvas.set_landmarks(self.current_landmarks)
                    self.results_panel.update_measurements_table(self.current_metrics)
                    self.results_panel.set_ai_prediction(latest_a["predicted_stage"], latest_a["predicted_confidence"])
                    self.results_panel.cb_stage.setCurrentText(latest_a["selected_stage"])
                    self.results_panel.txt_comments.setText(latest_a["comments"])
                    self.log_status("Existing clinical assessment loaded from local database.")
                else:
                    self.results_panel.clear_ui()
                    self.canvas.clear_all()
            else:
                self.log_status("Failed to load radiograph image file.")
        else:
            self.current_radiograph = None
            self.canvas.clear_all()
            self.canvas.scene.clear()
            self.pixmap_item = None
            self.results_panel.clear_ui()
            self.log_status("No radiographs registered for this patient profile.")

    def import_patient_radiograph(self):
        if self.current_patient_pk is None:
            QMessageBox.warning(self, "No Patient Loaded", "Please select or register a patient profile in the registry before importing radiographs.")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Lateral Cephalometric Radiograph", "", 
            "Image Files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.dcm *.dicom)"
        )
        
        if not file_path:
            return
            
        # Copy image file to app data directory to ensure offline integrity
        dest_dir = APP_DATA_DIR / "radiographs"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"pat_{self.current_patient_pk}_{int(datetime.now().timestamp())}_{os.path.basename(file_path)}"
        
        try:
            shutil.copy2(file_path, dest_path)
            # Register in DB
            radio_id = self.db.add_radiograph(self.current_patient_pk, str(dest_path), DEFAULT_CALIBRATION_SCALE)
            
            # Reload patient
            self.load_patient_record(self.current_patient_pk)
            self.log_status(f"Imported radiograph saved offline: {dest_path.name}")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Failed to save and register radiograph: {e}")

    # --- Calibration & Manual Landmarks Recalculation ---
    def handle_calibration_scale(self, scale: float):
        if self.current_radiograph:
            self.db.update_radiograph_calibration(self.current_radiograph["id"], scale)
            self.current_radiograph["calibration_scale"] = scale
            self.log_status(f"Database updated with calibration scale: {scale:.2f} px/mm")
            
            # Recalculate dimensions immediately if landmarks exist
            self.recalculate_dimensions()

    def enable_manual_landmark_placement(self):
        if self.current_radiograph is None:
            QMessageBox.warning(self, "No Image", "Please import and load a patient radiograph first.")
            return
            
        # Retrieve default landmark structure centered on the spine column
        default_pts = self.detector._get_default_layout(self.canvas.scene.height(), self.canvas.scene.width())
        self.current_landmarks = default_pts
        self.canvas.set_landmarks(default_pts)
        self.recalculate_dimensions()
        self.log_status("Default template landmarks placed. You can now drag nodes to align with C2, C3, and C4.")

    def handle_landmark_move(self, vertebra: str, name: str, pos: QPointF):
        if getattr(self, "is_updating_landmarks", False):
            return
            
        from PySide6.QtWidgets import QApplication
        is_shift_held = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)
        
        if is_shift_held and vertebra in self.current_landmarks:
            self.is_updating_landmarks = True
            try:
                if vertebra in self.canvas.landmarks and name in self.canvas.landmarks[vertebra]:
                    old_pos = self.canvas.landmarks[vertebra][name].pos()
                    delta_x = pos.x() - old_pos.x()
                    delta_y = pos.y() - old_pos.y()
                    
                    for pt_name in list(self.current_landmarks[vertebra].keys()):
                        x, y = self.current_landmarks[vertebra][pt_name]
                        new_x = x + delta_x
                        new_y = y + delta_y
                        self.current_landmarks[vertebra][pt_name] = (new_x, new_y)
                        
                        if pt_name in self.canvas.landmarks[vertebra]:
                            self.canvas.landmarks[vertebra][pt_name].setPos(new_x, new_y)
            finally:
                self.is_updating_landmarks = False
        else:
            if vertebra in self.current_landmarks and name in self.current_landmarks[vertebra]:
                self.current_landmarks[vertebra][name] = (pos.x(), pos.y())
                
        # Update contour paths
        self.canvas.update_contour_lines()
        # Calculate and display metrics in real-time
        self.recalculate_dimensions()

    def recalculate_dimensions(self):
        """Computes clinical heights, widths, and concavities using calibration factor."""
        if not self.current_landmarks:
            return
            
        scale = self.canvas.calibration_scale
        
        try:
            c2_m = calculate_vertebra_metrics(self.current_landmarks["C2"], scale)
            c3_m = calculate_vertebra_metrics(self.current_landmarks["C3"], scale)
            c4_m = calculate_vertebra_metrics(self.current_landmarks["C4"], scale)
            
            self.current_metrics = {
                "C2": c2_m,
                "C3": c3_m,
                "C4": c4_m
            }
            
            # Show in table
            self.results_panel.update_measurements_table(self.current_metrics)
            
            # Run heuristic decision tree for manual stage suggestion
            suggested_stage, _ = determine_cvmi_stage(c2_m, c3_m, c4_m)
            self.results_panel.cb_stage.setCurrentText(suggested_stage)
            
        except Exception as e:
            self.log_status(f"Measurements calculation error: {e}")

    # --- AI Pipelines ---
    def run_ai_pipeline(self):
        if self.current_radiograph is None:
            QMessageBox.warning(self, "No Image", "Please import and load a patient radiograph first.")
            return
            
        self.log_status("Initializing AI deep learning analysis...")
        
        image_path = self.current_radiograph["image_path"]
        
        # 1. Run Detector (Vertebral landmark detection)
        self.log_status("Running spinal column landmark localization...")
        try:
            detected_pts = self.detector.detect_landmarks(image_path)
            self.current_landmarks = detected_pts
            self.canvas.set_landmarks(detected_pts)
            self.log_status("AI successfully localized C2, C3, and C4 vertebrae landmarks.")
        except Exception as e:
            self.log_status(f"Landmark detection failed: {e}. Using fallback layout.")
            self.enable_manual_landmark_placement()
            return
            
        # Recalculate geometric metrics from localized points
        self.recalculate_dimensions()
        
        # 2. Determine CVMI stage from the predicted landmarks
        try:
            scale = self.canvas.calibration_scale
            c2_m = calculate_vertebra_metrics(self.current_landmarks["C2"], scale)
            c3_m = calculate_vertebra_metrics(self.current_landmarks["C3"], scale)
            c4_m = calculate_vertebra_metrics(self.current_landmarks["C4"], scale)
            
            predicted_stage, description = determine_cvmi_stage(c2_m, c3_m, c4_m)
            self.last_predicted_stage = predicted_stage
            self.last_predicted_conf = 1.0  # Deterministic staging from predicted landmarks
            
            # Update prediction display in UI
            self.results_panel.lbl_ai_stage.setText(f"Predicted Stage: {predicted_stage}")
            self.results_panel.lbl_ai_conf.setText("Calculated: Landmark-Based Heuristics")
            
            # Set the clinician selection dropdown automatically to match
            idx = self.results_panel.cb_stage.findText(predicted_stage)
            if idx >= 0:
                self.results_panel.cb_stage.setCurrentIndex(idx)
                
            self.log_status(f"AI Stage evaluation complete: {predicted_stage} (Rule-Based)")
            
        except Exception as e:
            self.log_status(f"Stage calculation from predicted landmarks failed: {e}")
            self.results_panel.lbl_ai_stage.setText("Predicted Stage: Error")
            self.results_panel.lbl_ai_conf.setText("Confidence Score: --")

    # --- Assessment Database Persistence & Reports ---
    def save_assessment(self, selected_stage: str, comments: str):
        if self.current_radiograph is None:
            QMessageBox.warning(self, "Save Error", "No loaded radiographic records found to attach assessments to.")
            return
            
        if not self.current_landmarks:
            QMessageBox.warning(self, "Save Error", "Please place or detect anatomical landmarks before saving assessments.")
            return
            
        is_ai_assisted = 1 if self.last_predicted_stage is not None else 0
        
        # Commit to SQL DB
        assessment_id = self.db.add_assessment(
            radiograph_pk=self.current_radiograph["id"],
            user_pk=self.user["id"],
            landmarks=self.current_landmarks,
            measurements=self.current_metrics,
            predicted_stage=self.last_predicted_stage,
            predicted_confidence=self.last_predicted_conf,
            selected_stage=selected_stage,
            comments=comments,
            is_ai_assisted=is_ai_assisted
        )
        
        if assessment_id:
            QMessageBox.information(self, "Assessment Saved", f"Clinical assessment record saved successfully (ID: {assessment_id}).")
            self.log_status("Clinical assessment saved in local encrypted database.")
            # Reload registry log
            self.load_patient_record(self.current_patient_pk)
        else:
            QMessageBox.critical(self, "Save Error", "Database insertion failed.")

    def generate_report_pdf(self):
        if self.current_patient_pk is None or self.current_radiograph is None:
            QMessageBox.warning(self, "Report Error", "Please load a patient record first.")
            return
            
        # Get latest assessment for report
        assessments = self.db.get_assessments_by_radiograph(self.current_radiograph["id"])
        if not assessments:
            QMessageBox.warning(self, "Report Error", "Please perform and SAVE an assessment before generating clinical PDF reports.")
            return
            
        latest_a = assessments[0]
        patient = self.db.get_patient(self.current_patient_pk)
        
        # Save dialog
        pdf_path, _ = QFileDialog.getSaveFileName(self, "Save Professional PDF Report", "", "PDF Files (*.pdf)")
        if not pdf_path:
            return
            
        success = generate_pdf_report(
            pdf_path=pdf_path,
            patient=patient,
            radiograph=self.current_radiograph,
            assessment=latest_a,
            examiner_name=self.user["username"]
        )
        
        if success:
            QMessageBox.information(self, "Report Generated", f"PDF clinical report created successfully: {pdf_path}")
            self.log_status(f"PDF report generated: {os.path.basename(pdf_path)}")
        else:
            QMessageBox.critical(self, "Report Error", "Failed to compile PDF. Check system configurations.")

    # --- UI Panels Activation Modals ---
    def open_research_suite(self, tab_index=0):
        self.log_status("Opening Research statistics dialog...")
        dlg = ResearchPanel(self.db, self)
        dlg.tabs.setCurrentIndex(tab_index)
        dlg.exec()
        # Refresh current registry states in case user modified anything
        self.patient_panel.refresh_patient_list()

    def open_ai_training(self):
        self.log_status("Opening deep learning retraining panel...")
        dlg = TrainingPanel(self)
        dlg.exec()

    def load_custom_model_weights(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Custom PyTorch Model Weights", "", "PyTorch Weights (*.pth *.pt)")
        if file_path:
            self.classifier = CVMIClassifier(model_path=file_path)
            self.log_status(f"Custom AI model loaded from: {file_path}")
            QMessageBox.information(self, "Model Loaded", f"Active classification network reconfigured to: {os.path.basename(file_path)}")

    # --- System & Administrative Controls ---
    def trigger_db_backup(self):
        backup_path = create_backup()
        if backup_path:
            QMessageBox.information(self, "Backup Successful", f"Encrypted local database backed up successfully:\n{backup_path}")
            self.log_status(f"Database backed up: {os.path.basename(backup_path)}")
        else:
            QMessageBox.critical(self, "Backup Failed", "Failed to create database archive.")

    def trigger_db_restore(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Restore Database from Archive", "", "Database Backup (*.db)")
        if not file_path:
            return
            
        confirm = QMessageBox.question(
            self, "Restore Database", 
            "WARNING: Restoring will overwrite all current patient entries. Do you wish to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            success = restore_backup(file_path)
            if success:
                QMessageBox.information(self, "Restore Success", "Local patient registry restored successfully. The application will now reload.")
                self.patient_panel.refresh_patient_list()
                self.canvas.clear_all()
                self.results_panel.clear_ui()
                self.log_status("Database restore complete.")
            else:
                QMessageBox.critical(self, "Restore Failed", "Failed to copy database archive.")

    def show_admin_panel(self):
        """Displays user list for administrators."""
        dlg = QDialog(self)
        dlg.setWindowTitle("System User Administration")
        dlg.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dlg)
        
        list_widget = QListWidget(dlg)
        users = self.db.get_users()
        for u in users:
            list_widget.addItem(f"User: {u['username']} | Role: {u['role'].upper()} (Created: {u['created_at'][:10]})")
            
        layout.addWidget(list_widget)
        
        btn_close = QPushButton("Close", dlg)
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)
        
        dlg.exec()

    def toggle_theme(self):
        """Alternates between light and dark UI stylesheets."""
        app = QApplication.instance()
        if self.current_theme == "dark":
            self.current_theme = "light"
            apply_theme(app, "light")
            self.log_status("UI Theme reconfigured: Professional Light mode")
        else:
            self.current_theme = "dark"
            apply_theme(app, "dark")
            self.log_status("UI Theme reconfigured: Slate Dark mode")

    def handle_logout(self):
        confirm = QMessageBox.question(
            self, "Confirm Logout", 
            "Are you sure you want to end your current orthodontic analysis session?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.log_status("Session terminated.")
            self.close()

    def closeEvent(self, event):
        """Ensure database connections close gracefully on exit."""
        try:
            self.db.close()
        except Exception:
            pass
        event.accept()
