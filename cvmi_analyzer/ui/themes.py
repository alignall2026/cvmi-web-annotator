from PySide6.QtWidgets import QApplication

DARK_QSS = """
QMainWindow {
    background-color: #121214;
    color: #e2e2e7;
}

/* Central widget and generic containers */
QWidget {
    background-color: #121214;
    color: #e2e2e7;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QFrame {
    border: none;
}

/* Sidebar and Panel Containers */
QFrame#sidebarFrame, QFrame#panelFrame {
    background-color: #1a1a1e;
    border: 1px solid #2a2a30;
    border-radius: 8px;
}

/* Custom Ribbon Bar styling */
QFrame#ribbonBar {
    background-color: #18181c;
    border-bottom: 2px solid #2d2d35;
}

QTabWidget::pane {
    border: 1px solid #2c2c34;
    background-color: #1a1a1e;
    top: -1px;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #151518;
    color: #a0a0a5;
    padding: 8px 16px;
    border: 1px solid #24242a;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}

QTabBar::tab:hover {
    background-color: #1d1d22;
    color: #e2e2e7;
}

QTabBar::tab:selected {
    background-color: #1a1a1e;
    color: #00d2c4; /* Teal Accent */
    border-top: 2px solid #00d2c4;
    border-bottom: 1px solid #1a1a1e;
}

/* Inputs: Text fields & Spinboxes */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #202026;
    color: #f0f0f3;
    border: 1px solid #32323d;
    border-radius: 4px;
    padding: 5px 8px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #00d2c4;
}

/* Buttons */
QPushButton {
    background-color: #24242c;
    color: #e2e2e7;
    border: 1px solid #363643;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #2f2f3a;
    border-color: #4a4a5a;
}

QPushButton:pressed {
    background-color: #1c1c22;
}

/* Prominent / Accent Button */
QPushButton#accentButton {
    background-color: #00a89d;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#accentButton:hover {
    background-color: #00d2c4;
}

QPushButton#accentButton:pressed {
    background-color: #008f86;
}

/* Table and Lists */
QListWidget, QTableWidget, QTreeView {
    background-color: #1a1a1e;
    color: #e2e2e7;
    border: 1px solid #2a2a32;
    border-radius: 4px;
    gridline-color: #282830;
}

QListWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #222228;
    border-radius: 4px;
}

QListWidget::item:hover {
    background-color: #24242c;
}

QListWidget::item:selected {
    background-color: #003632;
    color: #00d2c4;
    font-weight: 600;
}

QHeaderView::section {
    background-color: #222228;
    color: #a0a0a5;
    padding: 6px;
    border: 1px solid #1a1a1e;
    font-weight: bold;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #121214;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #32323c;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #444452;
}

QScrollBar:horizontal {
    background-color: #121214;
    height: 10px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #32323c;
    min-width: 20px;
    border-radius: 5px;
}

/* Dialogs */
QDialog {
    background-color: #16161a;
    border: 1px solid #2a2a30;
}

QLabel {
    color: #e2e2e7;
}

QLabel#titleLabel {
    font-size: 16px;
    font-weight: bold;
    color: #00d2c4;
}

QStatusBar {
    background-color: #121214;
    border-top: 1px solid #222228;
    color: #a0a0a5;
}
"""

LIGHT_QSS = """
QMainWindow {
    background-color: #f6f6f9;
    color: #1e1e24;
}

QWidget {
    background-color: #f6f6f9;
    color: #1e1e24;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QFrame {
    border: none;
}

QFrame#sidebarFrame, QFrame#panelFrame {
    background-color: #ffffff;
    border: 1px solid #dcdce6;
    border-radius: 8px;
}

QFrame#ribbonBar {
    background-color: #ffffff;
    border-bottom: 2px solid #e2e2ea;
}

QTabWidget::pane {
    border: 1px solid #dcdce6;
    background-color: #ffffff;
    top: -1px;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #eaeaea;
    color: #5c5c64;
    padding: 8px 16px;
    border: 1px solid #dcdce6;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}

QTabBar::tab:hover {
    background-color: #f0f0f5;
    color: #1e1e24;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0f62fe; /* Cobalt Blue Accent */
    border-top: 2px solid #0f62fe;
    border-bottom: 1px solid #ffffff;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #1e1e24;
    border: 1px solid #b8b8c4;
    border-radius: 4px;
    padding: 5px 8px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #0f62fe;
}

QPushButton {
    background-color: #ffffff;
    color: #1e1e24;
    border: 1px solid #b8b8c4;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #f0f0f5;
    border-color: #8c8c9c;
}

QPushButton:pressed {
    background-color: #e0e0ea;
}

QPushButton#accentButton {
    background-color: #0f62fe;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#accentButton:hover {
    background-color: #0043ce;
}

QPushButton#accentButton:pressed {
    background-color: #002d9c;
}

QListWidget, QTableWidget, QTreeView {
    background-color: #ffffff;
    color: #1e1e24;
    border: 1px solid #dcdce6;
    border-radius: 4px;
    gridline-color: #e8e8f0;
}

QListWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #f0f0f5;
    border-radius: 4px;
}

QListWidget::item:hover {
    background-color: #f2f2f7;
}

QListWidget::item:selected {
    background-color: #e5f0ff;
    color: #0f62fe;
    font-weight: 600;
}

QHeaderView::section {
    background-color: #f2f2f7;
    color: #5c5c64;
    padding: 6px;
    border: 1px solid #eaeaea;
    font-weight: bold;
}

QScrollBar:vertical {
    background-color: #f6f6f9;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #c8c8d0;
    min-height: 20px;
    border-radius: 5px;
}

QDialog {
    background-color: #ffffff;
    border: 1px solid #b8b8c4;
}

QLabel {
    color: #1e1e24;
}

QLabel#titleLabel {
    font-size: 16px;
    font-weight: bold;
    color: #0f62fe;
}

QStatusBar {
    background-color: #f6f6f9;
    border-top: 1px solid #dcdce6;
    color: #5c5c64;
}
"""

def apply_theme(app: QApplication, theme_name: str):
    """Applies either 'dark' or 'light' QSS to the QApplication instance."""
    if theme_name.lower() == "dark":
        app.setStyleSheet(DARK_QSS)
    else:
        app.setStyleSheet(LIGHT_QSS)
