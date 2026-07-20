from PySide6.QtWidgets import (
    QFrame, QTabWidget, QHBoxLayout, QVBoxLayout, QWidget, 
    QToolButton, QLabel, QStyle, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon

class RibbonGroup(QFrame):
    """A vertical box containing a set of ribbon buttons and a title label at the bottom."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("ribbonGroup")
        self.setStyleSheet("""
            QFrame#ribbonGroup {
                border-right: 1px solid #3c3c46;
                padding: 2px;
                background-color: transparent;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 2)
        layout.setSpacing(4)
        
        # Button container layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(6)
        self.button_layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(self.button_layout)
        
        # Bottom group label
        self.label = QLabel(title)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #8c8c96;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.label)

    def add_button(self, text: str, icon_pixmap=None, standard_icon: QStyle.StandardPixmap = None) -> QToolButton:
        btn = QToolButton(self)
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setIconSize(QSize(28, 28))
        btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        btn.setMinimumWidth(60)
        
        btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: #d2d2d8;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #2c2c36;
                border: 1px solid #4a4a58;
                color: #ffffff;
            }
            QToolButton:pressed {
                background-color: #1a1a24;
            }
            QToolButton:checked {
                background-color: #004d44;
                border: 1px solid #00d2c4;
                color: #00d2c4;
            }
        """)
        
        if standard_icon is not None:
            style = btn.style()
            btn.setIcon(style.standardIcon(standard_icon))
        elif icon_pixmap is not None:
            btn.setIcon(QIcon(icon_pixmap))
            
        self.button_layout.addWidget(btn)
        return btn


class RibbonBar(QFrame):
    """Custom Microsoft Office-style Ribbon Bar containing multiple tabs with functional groups."""
    action_triggered = Signal(str)  # Emits action ID when any ribbon button is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ribbonBar")
        self.setMinimumHeight(135)
        self.setMaximumHeight(145)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border-top: 1px solid #2d2d35;
                background-color: #16161a;
            }
            QTabBar::tab {
                font-weight: 600;
            }
        """)
        layout.addWidget(self.tabs)
        
        self._init_tabs()

    def _init_tabs(self):
        style = self.style()
        
        # ----------------- HOME TAB -----------------
        home_tab = QWidget()
        home_layout = QHBoxLayout(home_tab)
        home_layout.setContentsMargins(6, 4, 6, 4)
        home_layout.setSpacing(0)
        home_layout.setAlignment(Qt.AlignLeft)
        
        # Patient Group
        g_patient = RibbonGroup("PATIENT MANAGEMENT", home_tab)
        self.btn_new_patient = g_patient.add_button("New Patient", standard_icon=QStyle.SP_FileDialogNewFolder)
        self.btn_edit_patient = g_patient.add_button("Edit Patient", standard_icon=QStyle.SP_FileDialogDetailedView)
        home_layout.addWidget(g_patient)
        
        # File Operations Group
        g_file = RibbonGroup("FILE ACQUISITION", home_tab)
        self.btn_import_img = g_file.add_button("Import Image", standard_icon=QStyle.SP_DialogOpenButton)
        self.btn_save_db = g_file.add_button("Save Records", standard_icon=QStyle.SP_DialogSaveButton)
        home_layout.addWidget(g_file)
        
        self.tabs.addTab(home_tab, "Home")

        # ----------------- IMAGE TOOLS TAB -----------------
        img_tab = QWidget()
        img_layout = QHBoxLayout(img_tab)
        img_layout.setContentsMargins(6, 4, 6, 4)
        img_layout.setSpacing(0)
        img_layout.setAlignment(Qt.AlignLeft)
        
        # Image Enhancement Group
        g_enhance = RibbonGroup("FILTERS & ENHANCEMENT", img_tab)
        self.btn_enhance_clahe = g_enhance.add_button("CLAHE filter", standard_icon=QStyle.SP_CommandLink)
        self.btn_enhance_hist = g_enhance.add_button("Equalize", standard_icon=QStyle.SP_BrowserReload)
        self.btn_enhance_sharpen = g_enhance.add_button("Sharpen", standard_icon=QStyle.SP_ArrowUp)
        self.btn_reset_img = g_enhance.add_button("Reset Filter", standard_icon=QStyle.SP_DialogDiscardButton)
        img_layout.addWidget(g_enhance)
        
        # Transform Group
        g_transform = RibbonGroup("TRANSFORM", img_tab)
        self.btn_rot_left = g_transform.add_button("Rotate Left", standard_icon=QStyle.SP_ArrowLeft)
        self.btn_rot_right = g_transform.add_button("Rotate Right", standard_icon=QStyle.SP_ArrowRight)
        img_layout.addWidget(g_transform)
        
        # Calibration Group
        g_calibrate = RibbonGroup("CALIBRATION", img_tab)
        self.btn_calibrate = g_calibrate.add_button("Calibrate", standard_icon=QStyle.SP_CommandLink)
        self.btn_calibrate.setCheckable(True)
        img_layout.addWidget(g_calibrate)
        
        self.tabs.addTab(img_tab, "Image Tools")

        # ----------------- ANALYSIS TAB -----------------
        analysis_tab = QWidget()
        analysis_layout = QHBoxLayout(analysis_tab)
        analysis_layout.setContentsMargins(6, 4, 6, 4)
        analysis_layout.setSpacing(0)
        analysis_layout.setAlignment(Qt.AlignLeft)
        
        # Landmark Group
        g_mode = RibbonGroup("ANALYSIS METHOD", analysis_tab)
        self.btn_manual_mode = g_mode.add_button("Manual Mode", standard_icon=QStyle.SP_TitleBarNormalButton)
        self.btn_manual_mode.setCheckable(True)
        self.btn_manual_mode.setChecked(True)
        
        self.btn_ai_mode = g_mode.add_button("AI Detect", standard_icon=QStyle.SP_ComputerIcon)
        self.btn_clear_landmarks = g_mode.add_button("Clear Points", standard_icon=QStyle.SP_DialogResetButton)
        analysis_layout.addWidget(g_mode)
        
        # Output Group
        g_report = RibbonGroup("CLINICAL OUTPUT", analysis_tab)
        self.btn_generate_report = g_report.add_button("PDF Report", standard_icon=QStyle.SP_FileIcon)
        analysis_layout.addWidget(g_report)
        
        self.tabs.addTab(analysis_tab, "Analysis")

        # ----------------- RESEARCH TAB -----------------
        research_tab = QWidget()
        research_layout = QHBoxLayout(research_tab)
        research_layout.setContentsMargins(6, 4, 6, 4)
        research_layout.setSpacing(0)
        research_layout.setAlignment(Qt.AlignLeft)
        
        # Exports Group
        g_stats = RibbonGroup("RESEARCH MODULE", research_tab)
        self.btn_research_stats = g_stats.add_button("Statistics", standard_icon=QStyle.SP_MessageBoxInformation)
        self.btn_export_excel = g_stats.add_button("Export Excel", standard_icon=QStyle.SP_FileDialogListView)
        self.btn_export_csv = g_stats.add_button("Export CSV", standard_icon=QStyle.SP_FileDialogContentsView)
        research_layout.addWidget(g_stats)
        
        self.tabs.addTab(research_tab, "Research")

        # ----------------- AI TRAINING TAB -----------------
        ai_tab = QWidget()
        ai_layout = QHBoxLayout(ai_tab)
        ai_layout.setContentsMargins(6, 4, 6, 4)
        ai_layout.setSpacing(0)
        ai_layout.setAlignment(Qt.AlignLeft)
        
        # Training Group
        g_ai_train = RibbonGroup("DEEP LEARNING", ai_tab)
        self.btn_annotate_tool = g_ai_train.add_button("Label Tool", standard_icon=QStyle.SP_FileDialogNewFolder)
        self.btn_train_panel = g_ai_train.add_button("Training Panel", standard_icon=QStyle.SP_ToolBarHorizontalExtensionButton)
        self.btn_load_weights = g_ai_train.add_button("Load Model", standard_icon=QStyle.SP_DialogOpenButton)
        ai_layout.addWidget(g_ai_train)
        
        self.tabs.addTab(ai_tab, "AI Training")

        # ----------------- SECURITY & SYSTEM TAB -----------------
        sys_tab = QWidget()
        sys_layout = QHBoxLayout(sys_tab)
        sys_layout.setContentsMargins(6, 4, 6, 4)
        sys_layout.setSpacing(0)
        sys_layout.setAlignment(Qt.AlignLeft)
        
        # Database & Backup Group
        g_sec = RibbonGroup("SECURITY & INTEGRITY", sys_tab)
        self.btn_backup_db = g_sec.add_button("Backup DB", standard_icon=QStyle.SP_DriveHDIcon)
        self.btn_restore_db = g_sec.add_button("Restore DB", standard_icon=QStyle.SP_DriveFDIcon)
        self.btn_admin_panel = g_sec.add_button("User Admin", standard_icon=QStyle.SP_MessageBoxQuestion)
        sys_layout.addWidget(g_sec)
        
        # Session Group
        g_sess = RibbonGroup("THEME / SESSION", sys_tab)
        self.btn_switch_theme = g_sess.add_button("Toggle Theme", standard_icon=QStyle.SP_DesktopIcon)
        self.btn_logout = g_sess.add_button("Log Out", standard_icon=QStyle.SP_DialogCloseButton)
        sys_layout.addWidget(g_sess)
        
        self.tabs.addTab(sys_tab, "System & Security")
        
        # Connect clicked signals to emit generic action strings
        self.btn_new_patient.clicked.connect(lambda: self.action_triggered.emit("new_patient"))
        self.btn_edit_patient.clicked.connect(lambda: self.action_triggered.emit("edit_patient"))
        self.btn_import_img.clicked.connect(lambda: self.action_triggered.emit("import_image"))
        self.btn_save_db.clicked.connect(lambda: self.action_triggered.emit("save_db"))
        
        self.btn_enhance_clahe.clicked.connect(lambda: self.action_triggered.emit("filter_clahe"))
        self.btn_enhance_hist.clicked.connect(lambda: self.action_triggered.emit("filter_equalize"))
        self.btn_enhance_sharpen.clicked.connect(lambda: self.action_triggered.emit("filter_sharpen"))
        self.btn_reset_img.clicked.connect(lambda: self.action_triggered.emit("filter_reset"))
        
        self.btn_rot_left.clicked.connect(lambda: self.action_triggered.emit("rotate_left"))
        self.btn_rot_right.clicked.connect(lambda: self.action_triggered.emit("rotate_right"))
        self.btn_calibrate.clicked.connect(lambda: self.action_triggered.emit("calibrate_scale"))
        
        self.btn_manual_mode.clicked.connect(lambda: self._toggle_mode("manual"))
        self.btn_ai_mode.clicked.connect(lambda: self.action_triggered.emit("ai_detect"))
        self.btn_clear_landmarks.clicked.connect(lambda: self.action_triggered.emit("clear_landmarks"))
        self.btn_generate_report.clicked.connect(lambda: self.action_triggered.emit("generate_report"))
        
        self.btn_research_stats.clicked.connect(lambda: self.action_triggered.emit("show_research"))
        self.btn_export_excel.clicked.connect(lambda: self.action_triggered.emit("export_excel"))
        self.btn_export_csv.clicked.connect(lambda: self.action_triggered.emit("export_csv"))
        
        self.btn_annotate_tool.clicked.connect(lambda: self.action_triggered.emit("open_annotation_tool"))
        self.btn_train_panel.clicked.connect(lambda: self.action_triggered.emit("show_training"))
        self.btn_load_weights.clicked.connect(lambda: self.action_triggered.emit("load_weights"))
        
        self.btn_backup_db.clicked.connect(lambda: self.action_triggered.emit("backup_db"))
        self.btn_restore_db.clicked.connect(lambda: self.action_triggered.emit("restore_db"))
        self.btn_admin_panel.clicked.connect(lambda: self.action_triggered.emit("admin_panel"))
        self.btn_switch_theme.clicked.connect(lambda: self.action_triggered.emit("switch_theme"))
        self.btn_logout.clicked.connect(lambda: self.action_triggered.emit("logout"))

    def _toggle_mode(self, mode):
        if mode == "manual":
            self.btn_manual_mode.setChecked(True)
            self.action_triggered.emit("manual_mode")
