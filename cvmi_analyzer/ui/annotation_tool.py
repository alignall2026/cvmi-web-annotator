import os
import json
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, 
    QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QGraphicsView, 
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem, 
    QGraphicsSimpleTextItem, QGraphicsItem, QStatusBar, QGraphicsPathItem
)
from PySide6.QtCore import Qt, QPointF, QSize
from PySide6.QtGui import QImage, QPixmap, QBrush, QColor, QPen, QKeySequence, QShortcut, QCursor, QPainter

LANDMARK_ORDER = [
    # C2 Vertebra
    ("C2", "SA", "C2 Superior-Anterior Corner"),
    ("C2", "SP", "C2 Superior-Posterior Corner"),
    ("C2", "IP", "C2 Inferior-Posterior Corner"),
    ("C2", "IM", "C2 Inferior-Middle (Concavity Point)"),
    ("C2", "IA", "C2 Inferior-Anterior Corner"),
    # C3 Vertebra
    ("C3", "SA", "C3 Superior-Anterior Corner"),
    ("C3", "SP", "C3 Superior-Posterior Corner"),
    ("C3", "IP", "C3 Inferior-Posterior Corner"),
    ("C3", "IM", "C3 Inferior-Middle (Concavity Point)"),
    ("C3", "IA", "C3 Inferior-Anterior Corner"),
    # C4 Vertebra
    ("C4", "SA", "C4 Superior-Anterior Corner"),
    ("C4", "SP", "C4 Superior-Posterior Corner"),
    ("C4", "IP", "C4 Inferior-Posterior Corner"),
    ("C4", "IM", "C4 Inferior-Middle (Concavity Point)"),
    ("C4", "IA", "C4 Inferior-Anterior Corner"),
]

VERTEBRA_COLORS = {
    "C2": QColor(255, 80, 80),   # Red-Pink
    "C3": QColor(80, 255, 80),   # Green
    "C4": QColor(80, 180, 255)   # Light Blue
}

class DraggableLandmarkItem(QGraphicsEllipseItem):
    """Draggable handle for adjusting landmark position in the annotation canvas."""
    def __init__(self, vertebra: str, name: str, size=12, color=Qt.red, callback=None):
        super().__init__(-size/2, -size/2, size, size)
        self.vertebra = vertebra
        self.name = name
        self.callback = callback
        
        self.setAcceptHoverEvents(True)
        self.setFlags(
            QGraphicsItem.ItemIsMovable | 
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor(255, 255, 255), 1.5))
        
        # Hover label
        self.label = QGraphicsSimpleTextItem(f"{vertebra}_{name}", self)
        self.label.setBrush(QBrush(QColor(255, 255, 255)))
        self.label.setPos(size, -size)
        self.label.setVisible(False)
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene() and self.callback:
            self.callback(self.vertebra, self.name, value)
        return super().itemChange(change, value)
        
    def hoverEnterEvent(self, event):
        self.setCursor(QCursor(Qt.SizeAllCursor))
        self.label.setVisible(True)
        self.setBrush(QBrush(QColor(255, 255, 0)))  # Highlight yellow on hover
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        self.label.setVisible(False)
        self.setBrush(QBrush(VERTEBRA_COLORS.get(self.vertebra, Qt.red)))
        super().hoverLeaveEvent(event)


class AnnotationCanvas(QGraphicsView):
    """Interactive canvas for plotting and adjusting landmarks."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.pixmap_item = None
        self.parent_win = parent
        self.landmark_items = {}  # { (vert, name): DraggableLandmarkItem }
        self.contour_lines = []
        
        self.zoom_factor = 1.15
        self.current_zoom = 1.0
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.setStyleSheet("background-color: #121214; border: 1px solid #2d2d35;")
        self.setDragMode(QGraphicsView.NoDrag)
        
    def wheelEvent(self, event):
        if self.pixmap_item is None:
            return
            
        zoom_in_factor = self.zoom_factor
        zoom_out_factor = 1.0 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
            self.current_zoom *= zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            self.current_zoom *= zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)
        
    def mousePressEvent(self, event):
        # Enable panning with right-click drag
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.viewport().setCursor(Qt.ClosedHandCursor)
            
        elif event.button() == Qt.LeftButton and self.pixmap_item:
            # Intercept left click to place a landmark ONLY if we are still in click-placement sequence
            if self.parent_win.active_landmark_idx < len(LANDMARK_ORDER):
                pos = self.mapToScene(event.pos())
                rect = self.pixmap_item.boundingRect()
                if rect.contains(pos):
                    self.parent_win.handle_canvas_click(pos.x(), pos.y())
                    return
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)
        
    def clear_canvas(self):
        self.scene.clear()
        self.pixmap_item = None
        self.landmark_items.clear()
        self.contour_lines.clear()

    def set_image(self, pixmap):
        self.clear_canvas()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.pixmap_item.setZValue(-10)  # Always at back
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def draw_landmark(self, vertebra, name, x, y, callback):
        key = (vertebra, name)
        if key in self.landmark_items:
            self.scene.removeItem(self.landmark_items[key])
            
        color = VERTEBRA_COLORS.get(vertebra, Qt.red)
        item = DraggableLandmarkItem(vertebra, name, size=12, color=color, callback=callback)
        item.setPos(x, y)
        item.setZValue(10)  # Handles on top
        self.scene.addItem(item)
        self.landmark_items[key] = item
        self.draw_contours()

    def remove_landmark(self, vertebra, name):
        key = (vertebra, name)
        if key in self.landmark_items:
            self.scene.removeItem(self.landmark_items[key])
            del self.landmark_items[key]
            self.draw_contours()

    def draw_contours(self):
        # Clear existing paths
        for line in self.contour_lines:
            self.scene.removeItem(line)
        self.contour_lines.clear()
        
        from PySide6.QtWidgets import QGraphicsPathItem
        from PySide6.QtGui import QPainterPath
        
        for vert in ["C2", "C3", "C4"]:
            keys = [(vert, name) for name in ["SA", "SP", "IP", "IM", "IA"]]
            if not all(k in self.landmark_items for k in keys):
                continue
                
            p_SA = self.landmark_items[(vert, "SA")].pos()
            p_SP = self.landmark_items[(vert, "SP")].pos()
            p_IP = self.landmark_items[(vert, "IP")].pos()
            p_IM = self.landmark_items[(vert, "IM")].pos()
            p_IA = self.landmark_items[(vert, "IA")].pos()
            
            path = QPainterPath()
            path.moveTo(p_IP)
            
            # 1. Inferior border (IP -> IM -> IA): draw a smooth curve passing through IM
            ctrl1_x = (p_IP.x() + p_IM.x()) / 2.0
            ctrl1_y = p_IM.y()
            ctrl2_x = (p_IM.x() + p_IA.x()) / 2.0
            ctrl2_y = p_IM.y()
            path.cubicTo(QPointF(ctrl1_x, ctrl1_y), QPointF(ctrl2_x, ctrl2_y), p_IA)
            
            # 2. Anterior border (IA -> SA): straight line
            path.lineTo(p_SA)
            
            # 3. Superior border (SA -> SP)
            if vert == "C2":
                # For C2, draw the odontoid process peak!
                body_h = abs(p_SA.y() - p_IA.y())
                peak_x = (p_SA.x() + p_SP.x()) / 2.0
                peak_y = min(p_SA.y(), p_SP.y()) - body_h * 1.1
                path.quadTo(QPointF((p_SA.x() + peak_x)/2.0, peak_y), QPointF(peak_x, peak_y))
                path.quadTo(QPointF((p_SP.x() + peak_x)/2.0, peak_y), p_SP)
            else:
                path.lineTo(p_SP)
                
            # 4. Posterior border (SP -> IP): straight line
            path.lineTo(p_IP)
            
            color = VERTEBRA_COLORS.get(vert, Qt.red)
            pen = QPen(color, 2.5, Qt.SolidLine)
            brush = QBrush(QColor(color.red(), color.green(), color.blue(), 45)) # 18% opacity fill
            
            path_item = QGraphicsPathItem(path)
            path_item.setPen(pen)
            path_item.setBrush(brush)
            path_item.setZValue(5)
            self.scene.addItem(path_item)
            self.contour_lines.append(path_item)


class AnnotationToolWindow(QMainWindow):
    """Main Annotation Tool application window."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CVMI Cephalometric X-Ray Annotation Tool")
        self.resize(1300, 850)
        
        # State
        self.current_folder = ""
        self.image_files = []
        self.current_index = -1
        self.current_landmarks = {}  # { "C2": { "SA": (x,y), ... }, ... }
        self.active_landmark_idx = 0
        
        from cvmi_analyzer.ai.detector import CVMIDetector
        self.detector = CVMIDetector()
        
        self.init_ui()
        self.setup_shortcuts()
        self.update_ui_state()

    def init_ui(self):
        # Central widget
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # --- Left Panel: Controls & Landmarks list ---
        left_panel = QWidget(self)
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # Open Directory Button
        self.btn_open = QPushButton("Load Image Directory", self)
        self.btn_open.setMinimumHeight(40)
        self.btn_open.setStyleSheet("""
            QPushButton {
                background-color: #00d2c4;
                color: #0d0d0f;
                font-weight: bold;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00f2e4;
            }
        """)
        self.btn_open.clicked.connect(self.select_folder)
        left_layout.addWidget(self.btn_open)
        
        # Image list label
        self.lbl_folder = QLabel("No folder loaded.", self)
        self.lbl_folder.setWordWrap(True)
        self.lbl_folder.setStyleSheet("color: #8c8c96; font-size: 11px;")
        left_layout.addWidget(self.lbl_folder)
        
        # Images List Widget
        left_layout.addWidget(QLabel("Images in Directory:", self))
        self.list_images = QListWidget(self)
        self.list_images.setStyleSheet("""
            QListWidget {
                background-color: #1a1a20;
                border: 1px solid #2d2d35;
                color: #d2d2d8;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #004d44;
                color: #00d2c4;
                border-left: 3px solid #00d2c4;
            }
        """)
        self.list_images.currentRowChanged.connect(self.select_image_by_index)
        left_layout.addWidget(self.list_images)
        
        # Progress indicator
        self.lbl_progress = QLabel("0 / 0 Images Labeled", self)
        self.lbl_progress.setAlignment(Qt.AlignCenter)
        self.lbl_progress.setStyleSheet("font-weight: bold; color: #a0a0a5;")
        left_layout.addWidget(self.lbl_progress)
        
        # Landmarks instruction block
        left_layout.addWidget(QLabel("Landmarks Sequence (15 Points):", self))
        self.list_landmarks = QListWidget(self)
        self.list_landmarks.setStyleSheet("""
            QListWidget {
                background-color: #1a1a20;
                border: 1px solid #2d2d35;
                color: #d2d2d8;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #2b2b35;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        # Populate landmarks
        for vert, label, desc in LANDMARK_ORDER:
            item = QListWidgetItem(f"[{vert}] {label} - {desc}")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable) # Disallow manual list select for placement logic
            self.list_landmarks.addItem(item)
            
        self.list_landmarks.currentRowChanged.connect(self.change_active_landmark)
        left_layout.addWidget(self.list_landmarks)
        
        # Instruction status label
        self.lbl_instruction = QLabel("Please load a folder to start.", self)
        self.lbl_instruction.setStyleSheet("""
            QLabel {
                background-color: #2c1a1a; 
                color: #ff8080; 
                padding: 8px; 
                border-radius: 4px;
                border: 1px solid #5c2a2a;
                font-weight: bold;
            }
        """)
        self.lbl_instruction.setWordWrap(True)
        left_layout.addWidget(self.lbl_instruction)
        
        # Action Buttons
        actions_layout = QHBoxLayout()
        self.btn_reset = QPushButton("Reset Points", self)
        self.btn_reset.clicked.connect(self.reset_current_annotations)
        self.btn_reset.setStyleSheet("background-color: #3e3e4a; color: #ffffff;")
        
        self.btn_save = QPushButton("Save", self)
        self.btn_save.clicked.connect(self.save_annotations)
        self.btn_save.setStyleSheet("background-color: #004d44; color: #00d2c4; font-weight: bold;")
        
        actions_layout.addWidget(self.btn_reset)
        actions_layout.addWidget(self.btn_save)
        left_layout.addLayout(actions_layout)
        
        main_layout.addWidget(left_panel)
        
        # --- Right Panel: Interactive Canvas & Paging Buttons ---
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # Canvas
        self.canvas = AnnotationCanvas(self)
        right_layout.addWidget(self.canvas)
        
        # Bottom Paging buttons
        paging_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Previous (PageUp)", self)
        self.btn_prev.setMinimumHeight(35)
        self.btn_prev.clicked.connect(self.prev_image)
        
        self.btn_next = QPushButton("Next (PageDown) ▶", self)
        self.btn_next.setMinimumHeight(35)
        self.btn_next.clicked.connect(self.next_image)
        
        paging_layout.addWidget(self.btn_prev)
        paging_layout.addWidget(self.btn_next)
        right_layout.addLayout(paging_layout)
        
        main_layout.addWidget(right_panel)
        
        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Load an image folder to begin hand-labeling.")

    def setup_shortcuts(self):
        # Keyboard shortcuts for quick paging
        self.shortcut_prev = QShortcut(QKeySequence(Qt.Key_PageUp), self)
        self.shortcut_prev.activated.connect(self.prev_image)
        
        self.shortcut_next = QShortcut(QKeySequence(Qt.Key_PageDown), self)
        self.shortcut_next.activated.connect(self.next_image)
        
        # Shortcuts for shifting all landmarks simultaneously
        self.sc_shift_up = QShortcut(QKeySequence("Ctrl+Up"), self)
        self.sc_shift_up.activated.connect(lambda: self.shift_all_landmarks(0, -10))
        self.sc_shift_down = QShortcut(QKeySequence("Ctrl+Down"), self)
        self.sc_shift_down.activated.connect(lambda: self.shift_all_landmarks(0, 10))
        self.sc_shift_left = QShortcut(QKeySequence("Ctrl+Left"), self)
        self.sc_shift_left.activated.connect(lambda: self.shift_all_landmarks(-10, 0))
        self.sc_shift_right = QShortcut(QKeySequence("Ctrl+Right"), self)
        self.sc_shift_right.activated.connect(lambda: self.shift_all_landmarks(10, 0))

        # Fine shifting
        self.sc_fshift_up = QShortcut(QKeySequence("Ctrl+Shift+Up"), self)
        self.sc_fshift_up.activated.connect(lambda: self.shift_all_landmarks(0, -2))
        self.sc_fshift_down = QShortcut(QKeySequence("Ctrl+Shift+Down"), self)
        self.sc_fshift_down.activated.connect(lambda: self.shift_all_landmarks(0, 2))
        self.sc_fshift_left = QShortcut(QKeySequence("Ctrl+Shift+Left"), self)
        self.sc_fshift_left.activated.connect(lambda: self.shift_all_landmarks(-2, 0))
        self.sc_fshift_right = QShortcut(QKeySequence("Ctrl+Shift+Right"), self)
        self.sc_fshift_right.activated.connect(lambda: self.shift_all_landmarks(2, 0))
        
        # Overall Scaling (size of everything around the global center)
        self.sc_scale_up = QShortcut(QKeySequence("Ctrl+="), self)
        self.sc_scale_up.activated.connect(lambda: self.scale_all_landmarks(1.03))
        self.sc_scale_down = QShortcut(QKeySequence("Ctrl+-"), self)
        self.sc_scale_down.activated.connect(lambda: self.scale_all_landmarks(0.97))

        # Block Spacing Adjustment (vertical gap between C2, C3, and C4)
        self.sc_spacing_up = QShortcut(QKeySequence("Ctrl+Shift+="), self)
        self.sc_spacing_up.activated.connect(lambda: self.adjust_vertebra_spacing(1.04))
        self.sc_spacing_down = QShortcut(QKeySequence("Ctrl+Shift+-"), self)
        self.sc_spacing_down.activated.connect(lambda: self.adjust_vertebra_spacing(0.96))

        # Individual Box Width Scaling
        self.sc_box_w_down = QShortcut(QKeySequence("Ctrl+["), self)
        self.sc_box_w_down.activated.connect(lambda: self.scale_landmarks_width_height(0.97, 1.0))
        self.sc_box_w_up = QShortcut(QKeySequence("Ctrl+]"), self)
        self.sc_box_w_up.activated.connect(lambda: self.scale_landmarks_width_height(1.03, 1.0))

        # Individual Box Height Scaling
        self.sc_box_h_down = QShortcut(QKeySequence("Ctrl+Shift+["), self)
        self.sc_box_h_down.activated.connect(lambda: self.scale_landmarks_width_height(1.0, 0.97))
        self.sc_box_h_up = QShortcut(QKeySequence("Ctrl+Shift+]"), self)
        self.sc_box_h_up.activated.connect(lambda: self.scale_landmarks_width_height(1.0, 1.03))

    def shift_all_landmarks(self, dx: float, dy: float):
        if not self.current_landmarks:
            return
        for vert in self.current_landmarks:
            for name in list(self.current_landmarks[vert].keys()):
                x, y = self.current_landmarks[vert][name]
                self.current_landmarks[vert][name] = (x + dx, y + dy)
        self.redraw_all_landmarks()

    def scale_all_landmarks(self, factor: float):
        if not self.current_landmarks:
            return
        xs = []
        ys = []
        for vert in self.current_landmarks:
            for name in self.current_landmarks[vert]:
                x, y = self.current_landmarks[vert][name]
                xs.append(x)
                ys.append(y)
        if not xs:
            return
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        
        for vert in self.current_landmarks:
            for name in list(self.current_landmarks[vert].keys()):
                x, y = self.current_landmarks[vert][name]
                new_x = cx + (x - cx) * factor
                new_y = cy + (y - cy) * factor
                self.current_landmarks[vert][name] = (new_x, new_y)
        self.redraw_all_landmarks()

    def adjust_vertebra_spacing(self, factor: float):
        if not self.current_landmarks or "C2" not in self.current_landmarks or "C3" not in self.current_landmarks or "C4" not in self.current_landmarks:
            return
        
        c2_ys = [y for name, (x, y) in self.current_landmarks["C2"].items()]
        c3_ys = [y for name, (x, y) in self.current_landmarks["C3"].items()]
        c4_ys = [y for name, (x, y) in self.current_landmarks["C4"].items()]
        if not c2_ys or not c3_ys or not c4_ys:
            return
        
        # Use C3 center as anchor, push C2 and C4 further or closer relative to it
        c3_cy = sum(c3_ys) / len(c3_ys)
        
        for name in list(self.current_landmarks["C2"].keys()):
            x, y = self.current_landmarks["C2"][name]
            self.current_landmarks["C2"][name] = (x, c3_cy + (y - c3_cy) * factor)
            
        for name in list(self.current_landmarks["C4"].keys()):
            x, y = self.current_landmarks["C4"][name]
            self.current_landmarks["C4"][name] = (x, c3_cy + (y - c3_cy) * factor)
            
        self.redraw_all_landmarks()

    def scale_landmarks_width_height(self, w_factor: float, h_factor: float):
        if not self.current_landmarks:
            return
        # Scale each box independently relative to its own center
        for vert in self.current_landmarks:
            pts = self.current_landmarks[vert]
            xs = [x for name, (x, y) in pts.items()]
            ys = [y for name, (x, y) in pts.items()]
            if not xs:
                continue
            vc_x = sum(xs) / len(xs)
            vc_y = sum(ys) / len(ys)
            
            for name in list(pts.keys()):
                x, y = pts[name]
                new_x = vc_x + (x - vc_x) * w_factor
                new_y = vc_y + (y - vc_y) * h_factor
                self.current_landmarks[vert][name] = (new_x, new_y)
        self.redraw_all_landmarks()

    def redraw_all_landmarks(self):
        for vert, pts in self.current_landmarks.items():
            for name, (x, y) in pts.items():
                key = (vert, name)
                if key in self.canvas.landmark_items:
                    self.canvas.landmark_items[key].setPos(x, y)
        self.canvas.draw_contours()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Directory")
        if not folder:
            return
            
        self.current_folder = folder
        self.lbl_folder.setText(f"Folder: {os.path.basename(folder)}")
        
        # Scan images
        self.image_files = []
        for name in os.listdir(folder):
            ext = os.path.splitext(name)[1].lower()
            if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]:
                self.image_files.append(name)
                
        self.image_files.sort()
        
        self.list_images.clear()
        for name in self.image_files:
            # Check if already has a landmark json
            json_path = os.path.join(self.current_folder, f"{name}_landmarks.json")
            suffix = " (Annotated)" if os.path.exists(json_path) else ""
            self.list_images.addItem(name + suffix)
            
        if self.image_files:
            self.current_index = 0
            self.list_images.setCurrentRow(0)
        else:
            self.current_index = -1
            self.canvas.clear_canvas()
            QMessageBox.warning(self, "No Images", "No supported image files found in that directory.")
            
        self.update_progress_lbl()

    def select_image_by_index(self, index):
        if index < 0 or index >= len(self.image_files):
            return
            
        # Auto save previous before switching
        if self.current_index >= 0 and self.current_landmarks:
            self.save_annotations(silent=True)
            
        self.current_index = index
        image_name = self.image_files[index]
        image_path = os.path.join(self.current_folder, image_name)
        
        # Load image
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.status_bar.showMessage(f"Failed to load image: {image_name}")
            return
            
        self.canvas.set_image(pixmap)
        
        # Load existing landmarks if they exist
        json_path = os.path.join(self.current_folder, f"{image_name}_landmarks.json")
        self.current_landmarks = {}
        self.active_landmark_idx = 0
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    self.current_landmarks = data.get("landmarks", {})
                    # Restore landmarks to canvas
                    for vert, pts in self.current_landmarks.items():
                        for name, (x, y) in pts.items():
                            self.canvas.draw_landmark(vert, name, x, y, self.handle_landmark_drag)
                            
                # Since all are loaded, set active to the end (index 15) so it shows "complete"
                self.active_landmark_idx = len(LANDMARK_ORDER)
                self.status_bar.showMessage(f"Loaded existing annotations for {image_name}")
            except Exception as e:
                self.status_bar.showMessage(f"Error loading JSON annotation: {e}")
        else:
            # Auto-place pre-aligned default landmarks using the Sobel neck detector/default templates
            try:
                default_pts = self.detector.detect_landmarks(image_path)
                self.current_landmarks = default_pts
                for vert, pts in default_pts.items():
                    for name, (x, y) in pts.items():
                        self.canvas.draw_landmark(vert, name, x, y, self.handle_landmark_drag)
                # Since all are pre-placed, set active index to the end (allow immediate drag adjustments & saving)
                self.active_landmark_idx = len(LANDMARK_ORDER)
                self.status_bar.showMessage(f"Loaded image: {image_name}. Default templates placed; drag dots to align.")
            except Exception as e:
                self.status_bar.showMessage(f"Loaded image: {image_name}. Please click to place the 15 points manually.")
            
        self.update_ui_state()

    def handle_canvas_click(self, x, y):
        if self.active_landmark_idx >= len(LANDMARK_ORDER):
            # All landmarks are already placed. Do nothing.
            return
            
        vert, name, desc = LANDMARK_ORDER[self.active_landmark_idx]
        
        # Store in dict
        if vert not in self.current_landmarks:
            self.current_landmarks[vert] = {}
        self.current_landmarks[vert][name] = (x, y)
        
        # Draw on canvas
        self.canvas.draw_landmark(vert, name, x, y, self.handle_landmark_drag)
        
        # Advance index
        self.active_landmark_idx += 1
        self.update_ui_state()

    def handle_landmark_drag(self, vertebra, name, qpoint):
        if getattr(self, "is_updating_landmarks", False):
            return
            
        from PySide6.QtWidgets import QApplication
        is_shift_held = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)
        
        if is_shift_held and vertebra in self.current_landmarks:
            self.is_updating_landmarks = True
            try:
                key = (vertebra, name)
                if key in self.canvas.landmark_items:
                    old_pos = self.canvas.landmark_items[key].pos()
                    delta_x = qpoint.x() - old_pos.x()
                    delta_y = qpoint.y() - old_pos.y()
                    
                    for pt_name in list(self.current_landmarks[vertebra].keys()):
                        x, y = self.current_landmarks[vertebra][pt_name]
                        new_x = x + delta_x
                        new_y = y + delta_y
                        self.current_landmarks[vertebra][pt_name] = (new_x, new_y)
                        
                        k = (vertebra, pt_name)
                        if k in self.canvas.landmark_items:
                            self.canvas.landmark_items[k].setPos(new_x, new_y)
            finally:
                self.is_updating_landmarks = False
        else:
            if vertebra in self.current_landmarks:
                self.current_landmarks[vertebra][name] = (qpoint.x(), qpoint.y())
            
        # Redraw lines
        self.canvas.draw_contours()

    def reset_current_annotations(self):
        self.current_landmarks = {}
        self.active_landmark_idx = 0
        self.canvas.clear_canvas()
        if self.current_index >= 0:
            image_name = self.image_files[self.current_index]
            image_path = os.path.join(self.current_folder, image_name)
            self.canvas.set_image(QPixmap(image_path))
        self.update_ui_state()

    def save_annotations(self, silent=False):
        if self.current_index < 0:
            return
            
        # Verify if all 15 points are placed
        total_pts = sum(len(pts) for pts in self.current_landmarks.values())
        if total_pts < 15:
            if not silent:
                QMessageBox.warning(self, "Save Warning", f"You have only placed {total_pts} of 15 landmarks. Please click to place all 15 before saving.")
            return
            
        image_name = self.image_files[self.current_index]
        json_path = os.path.join(self.current_folder, f"{image_name}_landmarks.json")
        
        save_data = {
            "image_path": image_name,
            "landmarks": self.current_landmarks
        }
        
        try:
            with open(json_path, 'w') as f:
                json.dump(save_data, f, indent=4)
                
            # Update list widget items suffix
            item = self.list_images.item(self.current_index)
            if item and not item.text().endswith(" (Annotated)"):
                item.setText(image_name + " (Annotated)")
                
            self.update_progress_lbl()
            if not silent:
                self.status_bar.showMessage(f"Annotations saved successfully to: {os.path.basename(json_path)}")
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Save Error", f"Failed to save annotations: {e}")

    def update_progress_lbl(self):
        if not self.image_files:
            self.lbl_progress.setText("0 / 0 Images Labeled")
            return
            
        labeled_count = 0
        for name in self.image_files:
            json_path = os.path.join(self.current_folder, f"{name}_landmarks.json")
            if os.path.exists(json_path):
                labeled_count += 1
                
        self.lbl_progress.setText(f"{labeled_count} / {len(self.image_files)} Images Labeled")

    def prev_image(self):
        if self.current_index > 0:
            self.list_images.setCurrentRow(self.current_index - 1)

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.list_images.setCurrentRow(self.current_index + 1)

    def change_active_landmark(self, row):
        pass # Handle when row changes, but we manage selection programmatically

    def update_ui_state(self):
        # Enable/disable buttons based on state
        has_images = len(self.image_files) > 0
        self.btn_prev.setEnabled(has_images and self.current_index > 0)
        self.btn_next.setEnabled(has_images and self.current_index < len(self.image_files) - 1)
        self.btn_reset.setEnabled(has_images)
        self.btn_save.setEnabled(has_images)
        
        if not has_images:
            self.lbl_instruction.setText("Please load a folder containing X-ray images first.")
            self.lbl_instruction.setStyleSheet("background-color: #2c1a1a; color: #ff8080; padding: 8px; border-radius: 4px;")
            return

        # Select matching item in landmark list
        self.list_landmarks.setCurrentRow(min(self.active_landmark_idx, len(LANDMARK_ORDER) - 1))
        
        if self.active_landmark_idx < len(LANDMARK_ORDER):
            vert, name, desc = LANDMARK_ORDER[self.active_landmark_idx]
            self.lbl_instruction.setText(f"Click on the image to place landmark:\n→ {vert} {name}\n({desc})")
            self.lbl_instruction.setStyleSheet("background-color: #1a2c1a; color: #80ff80; padding: 8px; border-radius: 4px; border: 1px solid #2a5c2a;")
        else:
            self.lbl_instruction.setText("All 15 landmarks placed!\nAdjust coordinate dots by dragging them on the image, then press Save or page to next image.")
            self.lbl_instruction.setStyleSheet("background-color: #1a242c; color: #80d2ff; padding: 8px; border-radius: 4px; border: 1px solid #2a4c5c;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Refit image if view resized
        if hasattr(self.canvas, "pixmap_item") and self.canvas.pixmap_item:
            self.canvas.fitInView(self.canvas.pixmap_item, Qt.KeepAspectRatio)
