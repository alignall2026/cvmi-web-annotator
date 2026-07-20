from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QComboBox, QTextEdit, QPushButton, QGroupBox, QHeaderView
)
from PySide6.QtCore import Signal, Qt
from cvmi_analyzer.config import STAGE_DESCRIPTIONS

class ResultsPanel(QFrame):
    """
    Right-hand panel showing AI classification results,
    numerical measurements table, and manual examiner overriding actions.
    """
    save_assessment_requested = Signal(str, str) # Emits (selected_stage, comments)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panelFrame")
        self.setFixedWidth(300)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # --- Group 1: AI Diagnostics ---
        grp_ai = QGroupBox("AI Prediction Module")
        grp_ai.setStyleSheet("QGroupBox { font-weight: bold; color: #00d2c4; }")
        ai_layout = QVBoxLayout(grp_ai)
        ai_layout.setContentsMargins(8, 12, 8, 8)
        ai_layout.setSpacing(6)
        
        self.lbl_ai_stage = QLabel("Predicted Stage: --")
        self.lbl_ai_stage.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        ai_layout.addWidget(self.lbl_ai_stage)
        
        self.lbl_ai_conf = QLabel("Confidence: --")
        self.lbl_ai_conf.setStyleSheet("color: #a0a0a5; font-size: 12px;")
        ai_layout.addWidget(self.lbl_ai_conf)
        
        layout.addWidget(grp_ai)
        
        # --- Group 2: Measurements Table ---
        grp_measure = QGroupBox("Anatomical Measurements")
        grp_measure.setStyleSheet("QGroupBox { font-weight: bold; color: #00d2c4; }")
        measure_layout = QVBoxLayout(grp_measure)
        measure_layout.setContentsMargins(4, 12, 4, 4)
        
        self.table = QTableWidget(3, 4, self)
        self.table.setHorizontalHeaderLabels(["Depth", "W/H Rat", "Wedg", "H_avg"])
        self.table.setVerticalHeaderLabels(["C2", "C3", "C4"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Disable editing
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        
        # Initialize table cells
        for r in range(3):
            for c in range(4):
                item = QTableWidgetItem("--")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)
                
        measure_layout.addWidget(self.table)
        layout.addWidget(grp_measure)
        
        # --- Group 3: Clinical Decision Override ---
        grp_clinical = QGroupBox("Clinical Validation")
        grp_clinical.setStyleSheet("QGroupBox { font-weight: bold; color: #00d2c4; }")
        clinical_layout = QVBoxLayout(grp_clinical)
        clinical_layout.setContentsMargins(8, 12, 8, 8)
        clinical_layout.setSpacing(8)
        
        clinical_layout.addWidget(QLabel("Verified CVMI Stage:"))
        self.cb_stage = QComboBox(self)
        self.cb_stage.addItems(["CS1", "CS2", "CS3", "CS4", "CS5", "CS6"])
        self.cb_stage.currentIndexChanged.connect(self._on_stage_changed)
        clinical_layout.addWidget(self.cb_stage)
        
        # Display the clinical description for the selected stage
        self.lbl_stage_desc = QLabel("")
        self.lbl_stage_desc.setWordWrap(True)
        self.lbl_stage_desc.setStyleSheet("color: #a0a0a5; font-size: 11px; font-style: italic;")
        clinical_layout.addWidget(self.lbl_stage_desc)
        
        clinical_layout.addWidget(QLabel("Examiner Notes / Comments:"))
        self.txt_comments = QTextEdit(self)
        self.txt_comments.setPlaceholderText("Enter notes, anatomical observations, or clinical recommendations...")
        self.txt_comments.setMaximumHeight(80)
        clinical_layout.addWidget(self.txt_comments)
        
        self.btn_save = QPushButton("Save Assessment", self)
        self.btn_save.setObjectName("accentButton")
        self.btn_save.clicked.connect(self._on_save_clicked)
        clinical_layout.addWidget(self.btn_save)
        
        layout.addWidget(grp_clinical)
        
        # Trigger default description
        self._on_stage_changed(0)

    def set_ai_prediction(self, stage: str, confidence: float):
        """Updates the AI diagnostic display panel."""
        if stage:
            self.lbl_ai_stage.setText(f"Predicted Stage: {stage}")
            self.lbl_ai_conf.setText(f"Confidence Score: {confidence:.1%}")
            # Auto-set the clinician confirmation dropdown to the predicted stage by default
            idx = self.cb_stage.findText(stage)
            if idx >= 0:
                self.cb_stage.setCurrentIndex(idx)
        else:
            self.lbl_ai_stage.setText("Predicted Stage: --")
            self.lbl_ai_conf.setText("Confidence Score: --")

    def update_measurements_table(self, metrics: dict):
        """
        Updates the table cells dynamically.
        metrics format:
        {
           "C2": { "CD": val, "AR": val, "WS": val, "H_avg": val },
           "C3": ...
        }
        """
        row_keys = ["C2", "C3", "C4"]
        # Column mapping: 0=Depth, 1=AR, 2=WS, 3=H_avg
        for r_idx, vert in enumerate(row_keys):
            vert_metrics = metrics.get(vert)
            if not vert_metrics:
                continue
            
            # 1. Concavity Depth
            self.table.item(r_idx, 0).setText(f"{vert_metrics['CD']:.2f} mm")
            
            # 2. Aspect Ratio (Width / Height)
            self.table.item(r_idx, 1).setText(f"{vert_metrics['AR']:.2f}")
            
            # 3. Wedge Shape (AH / PH)
            self.table.item(r_idx, 2).setText(f"{vert_metrics['WS']:.2f}")
            
            # 4. Average Height
            self.table.item(r_idx, 3).setText(f"{vert_metrics['H_avg']:.1f} mm")

    def clear_ui(self):
        """Clears all panels back to blank placeholders."""
        self.set_ai_prediction("", 0.0)
        for r in range(3):
            for c in range(4):
                self.table.item(r, c).setText("--")
        self.txt_comments.clear()
        self.cb_stage.setCurrentIndex(0)

    def _on_stage_changed(self, index):
        stage = self.cb_stage.currentText()
        desc = STAGE_DESCRIPTIONS.get(stage, "")
        self.lbl_stage_desc.setText(desc)

    def _on_save_clicked(self):
        stage = self.cb_stage.currentText()
        comments = self.txt_comments.toPlainText().strip()
        self.save_assessment_requested.emit(stage, comments)
