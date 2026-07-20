import sys
from PySide6.QtWidgets import QApplication
from cvmi_analyzer.ui.annotation_tool import AnnotationToolWindow
from cvmi_analyzer.ui.themes import apply_theme

def main():
    app = QApplication(sys.argv)
    apply_theme(app, "dark")
    window = AnnotationToolWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
