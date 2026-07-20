import sys
from PySide6.QtWidgets import QApplication
from cvmi_analyzer.config import APP_NAME
from cvmi_analyzer.db.database import Database
from cvmi_analyzer.ui.login_dialog import LoginDialog
from cvmi_analyzer.ui.main_window import MainWindow
from cvmi_analyzer.ui.themes import apply_theme

def main():
    # 1. Initialize PySide6 Application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    # Apply default professional dark theme stylesheet
    apply_theme(app, "dark")
    
    # 2. Boot database schema and migrations
    db = Database()
    
    # 3. Secure authentication gate
    login = LoginDialog(db)
    if login.exec() == LoginDialog.Accepted:
        user_profile = login.authenticated_user
        
        # Spawn main medical workplace
        window = MainWindow(db, user_profile)
        window.show()
        
        # Start application execution loop
        sys.exit(app.exec())
    else:
        # User cancelled authentication dialog
        db.close()
        sys.exit(0)

if __name__ == "__main__":
    main()
