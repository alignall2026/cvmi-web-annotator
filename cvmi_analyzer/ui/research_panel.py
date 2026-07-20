import csv
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QLabel, QComboBox, QTabWidget, QWidget, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
from cvmi_analyzer.db.database import Database

class ResearchPanel(QDialog):
    """
    Research module dialog for statistical overview, 
    inter-examiner/intra-examiner reliability metrics (Kappa, ICC),
    and data table exports (CSV/Excel).
    """
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Research Statistics & Reliability Suite")
        self.resize(850, 600)
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header
        title = QLabel("Research Analytics Suite")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # Tabs
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)
        
        # --- TAB 1: Assessment Database ---
        self.tab_data = QWidget()
        data_layout = QVBoxLayout(self.tab_data)
        data_layout.setContentsMargins(8, 8, 8, 8)
        
        self.table_assessments = QTableWidget(self)
        self.table_assessments.setColumnCount(8)
        self.table_assessments.setHorizontalHeaderLabels([
            "ID", "Patient ID", "Radiograph", "Examiner", 
            "Pred Stage", "Final Stage", "Avg Width", "Avg Height"
        ])
        self.table_assessments.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        data_layout.addWidget(self.table_assessments)
        
        # Export buttons under database tab
        export_layout = QHBoxLayout()
        self.btn_csv = QPushButton("Export to CSV", self)
        self.btn_csv.clicked.connect(self.export_csv)
        self.btn_xlsx = QPushButton("Export to Excel", self)
        self.btn_xlsx.clicked.connect(self.export_excel)
        
        export_layout.addStretch()
        export_layout.addWidget(self.btn_csv)
        export_layout.addWidget(self.btn_xlsx)
        data_layout.addLayout(export_layout)
        
        self.tabs.addTab(self.tab_data, "Clinical Records Table")
        
        # --- TAB 2: Reliability Analysis ---
        self.tab_reliability = QWidget()
        rel_layout = QVBoxLayout(self.tab_reliability)
        rel_layout.setSpacing(15)
        
        # Dropdowns for raters selection
        selectors = QHBoxLayout()
        selectors.addWidget(QLabel("Examiner 1:"))
        self.cb_rater1 = QComboBox(self)
        selectors.addWidget(self.cb_rater1)
        
        selectors.addWidget(QLabel("Examiner 2:"))
        self.cb_rater2 = QComboBox(self)
        selectors.addWidget(self.cb_rater2)
        
        self.btn_compute = QPushButton("Compute Reliability", self)
        self.btn_compute.setObjectName("accentButton")
        self.btn_compute.clicked.connect(self.compute_reliability)
        selectors.addWidget(self.btn_compute)
        selectors.addStretch()
        
        rel_layout.addLayout(selectors)
        
        # Scoreboards
        self.lbl_cohen = QLabel("Cohen's Kappa (Categorical Stage Concordance): --")
        self.lbl_cohen.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")
        rel_layout.addWidget(self.lbl_cohen)
        
        self.lbl_icc = QLabel("Intraclass Correlation Coefficient (ICC 2,1 - Landmark Ratios): --")
        self.lbl_icc.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")
        rel_layout.addWidget(self.lbl_icc)
        
        self.lbl_fleiss = QLabel("Fleiss' Kappa (Multi-Examiner Stage Agreement): --")
        self.lbl_fleiss.setStyleSheet("font-size: 14px; color: #a0a0a5;")
        rel_layout.addWidget(self.lbl_fleiss)
        
        # Statistical summary text
        self.lbl_stats_summary = QLabel("Pairing comparison summary will be shown here.")
        self.lbl_stats_summary.setWordWrap(True)
        self.lbl_stats_summary.setStyleSheet("background-color: #1a1a22; padding: 10px; border-radius: 4px; border: 1px solid #2d2d35;")
        rel_layout.addWidget(self.lbl_stats_summary)
        rel_layout.addStretch()
        
        self.tabs.addTab(self.tab_reliability, "Inter-Examiner Reliability")

    def load_data(self):
        """Queries database and builds records list."""
        self.assessments = self.db.get_all_assessments()
        self.table_assessments.setRowCount(len(self.assessments))
        
        for idx, a in enumerate(self.assessments):
            self.table_assessments.setItem(idx, 0, QTableWidgetItem(str(a["id"])))
            self.table_assessments.setItem(idx, 1, QTableWidgetItem(a["patient_id"]))
            self.table_assessments.setItem(idx, 2, QTableWidgetItem(a["image_path"]))
            self.table_assessments.setItem(idx, 3, QTableWidgetItem(a["examiner_name"]))
            self.table_assessments.setItem(idx, 4, QTableWidgetItem(a["predicted_stage"] or "Manual"))
            self.table_assessments.setItem(idx, 5, QTableWidgetItem(a["selected_stage"]))
            
            # Compute width/height means to display
            try:
                c3_w = a["measurements"]["C3"]["W_avg"]
                c3_h = a["measurements"]["C3"]["H_avg"]
                self.table_assessments.setItem(idx, 6, QTableWidgetItem(f"{c3_w:.2f} mm"))
                self.table_assessments.setItem(idx, 7, QTableWidgetItem(f"{c3_h:.2f} mm"))
            except Exception:
                self.table_assessments.setItem(idx, 6, QTableWidgetItem("--"))
                self.table_assessments.setItem(idx, 7, QTableWidgetItem("--"))
                
        # Populate raters dropdowns
        users = self.db.get_users()
        usernames = [u["username"] for u in users]
        
        self.cb_rater1.clear()
        self.cb_rater1.addItems(usernames)
        self.cb_rater2.clear()
        self.cb_rater2.addItems(usernames)
        
        if len(usernames) >= 2:
            self.cb_rater2.setCurrentIndex(1)
            
        self.compute_fleiss_kappa()

    # --- Statistical Calculations (Kappa, ICC) ---
    def compute_reliability(self):
        rater1 = self.cb_rater1.currentText()
        rater2 = self.cb_rater2.currentText()
        
        if rater1 == rater2:
            QMessageBox.warning(self, "Invalid Selection", "Please select two different examiners to compare.")
            return
            
        # Group assessments by radiograph
        paired_stages = []
        paired_ratios = [] # For ICC (using C3 Aspect Ratio as the test metric)
        
        radio_groups = {}
        for a in self.assessments:
            r_pk = a["radiograph_pk"]
            if r_pk not in radio_groups:
                radio_groups[r_pk] = {}
            radio_groups[r_pk][a["examiner_name"]] = a
            
        # Extract matches
        for r_pk, raters in radio_groups.items():
            if rater1 in raters and rater2 in raters:
                a1 = raters[rater1]
                a2 = raters[rater2]
                paired_stages.append((a1["selected_stage"], a2["selected_stage"]))
                try:
                    r1_val = a1["measurements"]["C3"]["AR"]
                    r2_val = a2["measurements"]["C3"]["AR"]
                    paired_ratios.append([r1_val, r2_val])
                except Exception:
                    pass
                    
        n_samples = len(paired_stages)
        if n_samples < 2:
            self.lbl_cohen.setText("Cohen's Kappa: Insufficient paired samples (need >= 2 matches)")
            self.lbl_icc.setText("ICC: Insufficient paired samples")
            self.lbl_stats_summary.setText("No overlapping radiographs evaluated by both selected examiners were found.")
            return
            
        # 1. Compute Cohen's Kappa
        stages = ["CS1", "CS2", "CS3", "CS4", "CS5", "CS6"]
        stage_map = {s: i for i, s in enumerate(stages)}
        
        cm = np.zeros((6, 6), dtype=int)
        for s1, s2 in paired_stages:
            if s1 in stage_map and s2 in stage_map:
                cm[stage_map[s1], stage_map[s2]] += 1
                
        po = np.trace(cm) / n_samples
        
        row_sums = np.sum(cm, axis=1)
        col_sums = np.sum(cm, axis=0)
        pe = np.sum(row_sums * col_sums) / (n_samples ** 2)
        
        kappa = (po - pe) / (1 - pe) if pe < 1.0 else 1.0
        
        # 2. Compute Intraclass Correlation Coefficient ICC(2,1)
        icc_val = 0.0
        if len(paired_ratios) >= 2:
            Y = np.array(paired_ratios) # Shape (N, 2)
            N, k = Y.shape
            
            grand_mean = np.mean(Y)
            row_means = np.mean(Y, axis=1)
            col_means = np.mean(Y, axis=0)
            
            ss_p = k * np.sum((row_means - grand_mean)**2)
            ms_p = ss_p / (N - 1)
            
            ss_j = N * np.sum((col_means - grand_mean)**2)
            ms_j = ss_j / (k - 1)
            
            ss_total = np.sum((Y - grand_mean)**2)
            ss_e = ss_total - ss_p - ss_j
            ms_e = ss_e / ((N - 1) * (k - 1))
            
            # ICC(2,1) Two-way random effects, single rater, absolute agreement
            denom = ms_p + (k - 1)*ms_e + (k / N)*(ms_j - ms_e)
            icc_val = (ms_p - ms_e) / denom if denom != 0 else 0.0
            
        self.lbl_cohen.setText(f"Cohen's Kappa (Categorical Stage): {kappa:.3f}")
        self.lbl_icc.setText(f"ICC (2,1) (C3 Aspect Ratios): {icc_val:.3f}")
        
        # Interpretation text
        kappa_desc = "Poor"
        if kappa > 0.8: kappa_desc = "Almost Perfect"
        elif kappa > 0.6: kappa_desc = "Substantial"
        elif kappa > 0.4: kappa_desc = "Moderate"
        elif kappa > 0.2: kappa_desc = "Fair"
        elif kappa > 0: kappa_desc = "Slight"
        
        icc_desc = "Poor"
        if icc_val > 0.9: icc_desc = "Excellent"
        elif icc_val > 0.75: icc_desc = "Good"
        elif icc_val > 0.5: icc_desc = "Moderate"
        
        self.lbl_stats_summary.setText(
            f"Successfully compared {n_samples} matched radiological records.\n\n"
            f"• Cohen's Kappa: {kappa:.3f} ({kappa_desc} Agreement)\n"
            f"• Intraclass Correlation (ICC): {icc_val:.3f} ({icc_desc} Reliability)\n\n"
            f"Measurements are calculated using the active local pixel-to-millimeter calibration scale factor."
        )

    def compute_fleiss_kappa(self):
        """Computes Fleiss' Kappa across all examiners for all shared radiographs."""
        radio_groups = {}
        for a in self.assessments:
            r_pk = a["radiograph_pk"]
            if r_pk not in radio_groups:
                radio_groups[r_pk] = []
            radio_groups[r_pk].append(a["selected_stage"])
            
        # We need cases where at least 3 ratings are present, or at least 2 rating arrays of equal raters.
        # To compute Fleiss' Kappa, we need a constant number of raters 'n' per item.
        # Let's filter radiographs that have ratings equal to the maximum number of ratings found.
        if not radio_groups:
            self.lbl_fleiss.setText("Fleiss' Kappa: No shared ratings found.")
            return
            
        counts = [len(stages) for stages in radio_groups.values()]
        n_raters = max(counts)
        
        if n_raters < 2:
            self.lbl_fleiss.setText("Fleiss' Kappa: Need multiple ratings per radiograph.")
            return
            
        # Select radiographs with exactly n_raters ratings
        valid_cases = [stages for stages in radio_groups.values() if len(stages) == n_raters]
        N = len(valid_cases)
        
        if N < 2:
            self.lbl_fleiss.setText(f"Fleiss' Kappa: Insufficient fully-crossed cases (need >= 2 cases with {n_raters} raters)")
            return
            
        stages = ["CS1", "CS2", "CS3", "CS4", "CS5", "CS6"]
        stage_map = {s: i for i, s in enumerate(stages)}
        
        # Matrix of dimensions (N, K)
        # N = number of subjects (images), K = number of categories (6 stages)
        table = np.zeros((N, 6), dtype=int)
        for i, ratings in enumerate(valid_cases):
            for r in ratings:
                if r in stage_map:
                    table[i, stage_map[r]] += 1
                    
        # Compute Pi
        p_i = (np.sum(table ** 2, axis=1) - n_raters) / (n_raters * (n_raters - 1))
        po = np.mean(p_i)
        
        # Compute pj
        p_j = np.sum(table, axis=0) / (N * n_raters)
        pe = np.sum(p_j ** 2)
        
        fleiss_kappa = (po - pe) / (1 - pe) if pe < 1.0 else 1.0
        self.lbl_fleiss.setText(f"Fleiss' Kappa (Multi-Examiner Stage Agreement, {n_raters} raters, {N} images): {fleiss_kappa:.3f}")

    # --- Data Export Suite (CSV & Excel) ---
    def export_csv(self):
        if not self.assessments:
            QMessageBox.warning(self, "Export Error", "No assessments available to export.")
            return
            
        path = "cvmi_export.csv"
        try:
            with open(path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Assessment_ID", "Patient_ID", "Radiograph_Path", "Examiner",
                    "Predicted_Stage", "Predicted_Conf", "Selected_Stage", 
                    "C2_Concavity", "C3_Concavity", "C4_Concavity",
                    "C3_Aspect_Ratio", "C4_Aspect_Ratio", "Comments", "Timestamp"
                ])
                for a in self.assessments:
                    writer.writerow([
                        a["id"], a["patient_id"], a["image_path"], a["examiner_name"],
                        a["predicted_stage"] or "", a["predicted_confidence"] or "",
                        a["selected_stage"],
                        a["measurements"].get("C2", {}).get("CD", 0.0),
                        a["measurements"].get("C3", {}).get("CD", 0.0),
                        a["measurements"].get("C4", {}).get("CD", 0.0),
                        a["measurements"].get("C3", {}).get("AR", 0.0),
                        a["measurements"].get("C4", {}).get("AR", 0.0),
                        a["comments"] or "", a["created_at"]
                    ])
            QMessageBox.information(self, "Export Complete", f"Data exported successfully to CSV: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {e}")

    def export_excel(self):
        if not self.assessments:
            QMessageBox.warning(self, "Export Error", "No assessments available to export.")
            return
            
        path = "cvmi_export.xlsx"
        try:
            data = []
            for a in self.assessments:
                data.append({
                    "Assessment ID": a["id"],
                    "Patient ID": a["patient_id"],
                    "Radiograph Path": a["image_path"],
                    "Examiner Name": a["examiner_name"],
                    "AI Predicted Stage": a["predicted_stage"] or "Manual",
                    "AI Confidence": a["predicted_confidence"] or 0.0,
                    "Verified Stage": a["selected_stage"],
                    "C2 Concavity (mm)": a["measurements"].get("C2", {}).get("CD", 0.0),
                    "C3 Concavity (mm)": a["measurements"].get("C3", {}).get("CD", 0.0),
                    "C4 Concavity (mm)": a["measurements"].get("C4", {}).get("CD", 0.0),
                    "C3 Aspect Ratio": a["measurements"].get("C3", {}).get("AR", 0.0),
                    "C4 Aspect Ratio": a["measurements"].get("C4", {}).get("AR", 0.0),
                    "Examiner Notes": a["comments"] or "",
                    "Timestamp": a["created_at"]
                })
            df = pd.DataFrame(data)
            df.to_excel(path, index=False, engine='openpyxl')
            QMessageBox.information(self, "Export Complete", f"Data exported successfully to Excel: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export Excel: {e}")
