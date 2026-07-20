import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFileDialog, QProgressBar, QTextEdit, QMessageBox, QTabWidget, QWidget, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QPixmap
from cvmi_analyzer.config import APP_DATA_DIR
from cvmi_analyzer.ai.train_detector import run_detector_training

class TrainingThread(QThread):
    """Worker thread to run PyTorch CNN model training in the background."""
    epoch_finished = Signal(int, int, float, float, float, str)  # (epoch, max_epochs, loss, val_loss, val_acc, text)
    training_finished = Signal(bool)
    
    def __init__(self, dataset_dir, epochs, batch_size, lr):
        super().__init__()
        self.dataset_dir = dataset_dir
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr

    def run(self):
        def callback(epoch, max_epochs, loss, val_loss, val_acc, text):
            self.epoch_finished.emit(epoch, max_epochs, loss, val_loss, val_acc, text)
            
        success = run_detector_training(
            dataset_dir=self.dataset_dir,
            epochs=self.epochs,
            batch_size=self.batch_size,
            lr=self.lr,
            progress_callback=callback
        )
        self.training_finished.emit(success)


class TrainingPanel(QDialog):
    """AI Training Support UI panel allowing custom dataset importing and neural net retraining."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Model Training Dashboard")
        self.resize(750, 550)
        self.thread = None
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header
        title = QLabel("AI Training & Retraining Dashboard")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # --- Config Box ---
        cfg_layout = QHBoxLayout()
        
        # Dataset Selection
        cfg_layout.addWidget(QLabel("Dataset Directory:"))
        self.txt_dataset = QLineEdit(self)
        self.txt_dataset.setPlaceholderText("Select folder with images and matching *_landmarks.json files...")
        cfg_layout.addWidget(self.txt_dataset)
        
        self.btn_browse = QPushButton("Browse...", self)
        self.btn_browse.clicked.connect(self.browse_dataset_folder)
        cfg_layout.addWidget(self.btn_browse)
        
        layout.addLayout(cfg_layout)
        
        # Hyperparameters Row
        hparams = QHBoxLayout()
        hparams.addWidget(QLabel("Epochs:"))
        self.spin_epochs = QSpinBox(self)
        self.spin_epochs.setRange(1, 100)
        self.spin_epochs.setValue(10)
        hparams.addWidget(self.spin_epochs)
        
        hparams.addWidget(QLabel("Batch Size:"))
        self.spin_batch = QSpinBox(self)
        self.spin_batch.setRange(2, 256)
        self.spin_batch.setValue(16)
        hparams.addWidget(self.spin_batch)
        
        hparams.addWidget(QLabel("Learning Rate:"))
        self.spin_lr = QDoubleSpinBox(self)
        self.spin_lr.setRange(0.0001, 0.1)
        self.spin_lr.setDecimals(4)
        self.spin_lr.setValue(0.001)
        hparams.addWidget(self.spin_lr)
        
        self.btn_train = QPushButton("Start Retraining", self)
        self.btn_train.setObjectName("accentButton")
        self.btn_train.clicked.connect(self.start_training)
        hparams.addWidget(self.btn_train)
        
        layout.addLayout(hparams)
        
        # --- Progress indicators ---
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # --- Display Tabs ---
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)
        
        # Tab 1: Text logs
        self.tab_logs = QWidget()
        logs_layout = QVBoxLayout(self.tab_logs)
        logs_layout.setContentsMargins(5, 5, 5, 5)
        
        self.txt_logs = QTextEdit(self)
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #0c0c0f; color: #00d2c4; font-family: Consolas, monospace;")
        logs_layout.addWidget(self.txt_logs)
        self.tabs.addTab(self.tab_logs, "Training Logs")
        
        # Tab 2: Accuracy Curves
        self.tab_curves = QWidget()
        curves_layout = QVBoxLayout(self.tab_curves)
        self.lbl_curves = QLabel("Accuracy/Loss charts will be displayed here post training.", self)
        self.lbl_curves.setAlignment(Qt.AlignCenter)
        curves_layout.addWidget(self.lbl_curves)
        self.tabs.addTab(self.tab_curves, "Learning History")
        
        # Tab 3: Confusion Matrix
        self.tab_cm = QWidget()
        cm_layout = QVBoxLayout(self.tab_cm)
        self.lbl_cm = QLabel("Confusion Matrix will be displayed here post training.", self)
        self.lbl_cm.setAlignment(Qt.AlignCenter)
        cm_layout.addWidget(self.lbl_cm)
        self.tabs.addTab(self.tab_cm, "Confusion Matrix")
        
        # Tab 4: ROC curves
        self.tab_roc = QWidget()
        roc_layout = QVBoxLayout(self.tab_roc)
        self.lbl_roc = QLabel("ROC/AUC charts will be displayed here post training.", self)
        self.lbl_roc.setAlignment(Qt.AlignCenter)
        roc_layout.addWidget(self.lbl_roc)
        self.tabs.addTab(self.tab_roc, "ROC Analysis")

    def browse_dataset_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Labeled Dataset Directory")
        if folder:
            self.txt_dataset.setText(folder)

    def start_training(self):
        dataset_dir = self.txt_dataset.text().strip()
        if not dataset_dir or not os.path.exists(dataset_dir):
            QMessageBox.warning(self, "Invalid Directory", "Please select a valid dataset folder first.")
            return
            
        epochs = self.spin_epochs.value()
        batch_size = self.spin_batch.value()
        lr = self.spin_lr.value()
        
        # Disable controls during execution
        self.btn_train.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.txt_dataset.setEnabled(False)
        self.spin_epochs.setEnabled(False)
        self.spin_batch.setEnabled(False)
        self.spin_lr.setEnabled(False)
        
        self.txt_logs.clear()
        self.txt_logs.append("Initializing PyTorch training pipeline...")
        self.progress_bar.setValue(0)
        
        # Start Thread
        self.thread = TrainingThread(dataset_dir, epochs, batch_size, lr)
        self.thread.epoch_finished.connect(self._on_epoch_finished)
        self.thread.training_finished.connect(self._on_training_finished)
        self.thread.start()

    def _on_epoch_finished(self, epoch, max_epochs, loss, val_loss, val_acc, text):
        # Update progress bar
        percentage = int((epoch / max_epochs) * 100) if max_epochs > 0 else 0
        self.progress_bar.setValue(percentage)
        self.txt_logs.append(text)
        
    def _on_training_finished(self, success):
        # Re-enable controls
        self.btn_train.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.txt_dataset.setEnabled(True)
        self.spin_epochs.setEnabled(True)
        self.spin_batch.setEnabled(True)
        self.spin_lr.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Training Successful", "Model weights saved and compiled successfully!")
            self.txt_logs.append("\nModel training finished successfully.")
            self.load_training_plots()
        else:
            QMessageBox.critical(self, "Training Error", "Training process encountered an error. Check logs for details.")
            self.txt_logs.append("\nModel training aborted due to error.")

    def load_training_plots(self):
        """Loads matplotlib PNG files and prints them in the tab widgets."""
        plot_dir = APP_DATA_DIR / "training_plots"
        
        history_path = plot_dir / "landmark_history.png"
        
        if history_path.exists():
            pix = QPixmap(str(history_path))
            self.lbl_curves.setPixmap(pix.scaled(650, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
        self.lbl_cm.setText("Note: Confusion matrix is not applicable for continuous landmark coordinate regression.")
        self.lbl_roc.setText("Note: ROC analysis is not applicable for continuous landmark coordinate regression.")
