import cv2
import numpy as np
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsSimpleTextItem,
    QInputDialog, QMessageBox, QGraphicsItem, QGraphicsPathItem
)
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QImage, QPixmap, QPen, QColor, QBrush, QCursor, QPainter

class LandmarkItem(QGraphicsEllipseItem):
    """Draggable circle representing a vertebra landmark."""
    position_changed = Signal(str, str, QPointF)  # Emits (vertebra_name, landmark_name, new_pos)
    
    def __init__(self, vertebra: str, name: str, parent_view, size=8, color=Qt.red):
        # Center the ellipse on (0,0); we use setPos() to position it
        super().__init__(-size/2, -size/2, size, size)
        self.vertebra = vertebra
        self.name = name
        self.parent_view = parent_view
        
        self.setAcceptHoverEvents(True)
        self.setFlags(
            QGraphicsItem.ItemIsMovable | 
            QGraphicsItem.ItemSendsGeometryChanges
        )
        
        # Color styling
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor(255, 255, 255), 1.5))
        
        # Display label on hover
        self.label = QGraphicsSimpleTextItem(f"{vertebra}_{name}", self)
        self.label.setBrush(QBrush(QColor(255, 255, 255)))
        self.label.setPos(size, -size)
        self.label.setVisible(False)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # Emit coordinates change to trigger live recalculation
            self.parent_view.landmark_moved_signal.emit(self.vertebra, self.name, value)
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self.setCursor(QCursor(Qt.SizeAllCursor))
        self.label.setVisible(True)
        self.setBrush(QBrush(QColor(255, 255, 0))) # Highlight yellow
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.label.setVisible(False)
        self.setBrush(QBrush(self.parent_view.vertebra_colors[self.vertebra]))
        super().hoverLeaveEvent(event)


class CephCanvas(QGraphicsView):
    """
    Custom graphics view for lateral cephalogram radiography.
    Supports zooming, panning, scaling calibration, filter adjustments, 
    and interactive coordinate annotation.
    """
    landmark_moved_signal = Signal(str, str, QPointF) # Emitted during landmark drag
    calibration_completed = Signal(float) # Emits the calculated pixels-per-mm ratio
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_view = parent
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        
        # Canvas properties
        self.original_image_path = ""
        self.cv_image = None        # Current cv2 image after filters
        self.display_image = None   # Base cv2 image
        self.pixmap_item = None
        self.calibration_scale = 1.0
        
        # Adjustments values
        self.brightness = 0
        self.contrast = 0
        
        # Interactive features state
        self.calibration_mode = False
        self.calibration_points = []
        self.calibration_line = None
        
        # Landmark storage
        # Struct: { "C2": { "SA": LandmarkItem, ... }, ... }
        self.landmarks = {}
        # Struct: { "C2": [QGraphicsLineItem, ...], ... }
        self.contour_lines = {}
        
        self.vertebra_colors = {
            "C2": QColor(255, 80, 80),   # Red-Pink
            "C3": QColor(80, 255, 80),   # Green
            "C4": QColor(80, 180, 255)   # Light Blue
        }
        
        # Zoom state
        self.zoom_factor = 1.15
        self.current_zoom = 1.0
        
        self.setStyleSheet("background-color: #0c0c0e; border: none;")

    def load_image(self, filepath: str):
        """Loads and displays the radiographic image."""
        self.original_image_path = filepath
        
        # Support DICOM files
        if filepath.lower().endswith(('.dcm', '.dicom')):
            try:
                import pydicom
                ds = pydicom.dcmread(filepath)
                pixel_array = ds.pixel_array
                # Convert to uint8 grayscale
                pixel_array = (pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min()) * 255.0
                gray = pixel_array.astype(np.uint8)
                self.cv_image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            except Exception as e:
                QMessageBox.critical(self, "DICOM Error", f"Failed to parse DICOM: {e}")
                return False
        else:
            self.cv_image = cv2.imread(filepath)
            
        if self.cv_image is None:
            return False
            
        self.display_image = self.cv_image.copy()
        
        # Reset state
        self.brightness = 0
        self.contrast = 0
        self.clear_all()
        
        self._update_pixmap()
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.current_zoom = 1.0
        return True

    def _update_pixmap(self):
        """Updates the graphics scene pixmap using current processed cv_image."""
        if self.cv_image is None:
            return
            
        h, w, ch = self.cv_image.shape
        bytes_per_line = ch * w
        q_img = QImage(self.cv_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        # Convert BGR to RGB
        q_img = q_img.rgbSwapped()
        pixmap = QPixmap.fromImage(q_img)
        
        if self.pixmap_item is None:
            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.pixmap_item)
            # Ensure image is drawn at the bottom layer
            self.pixmap_item.setZValue(-10)
        else:
            self.pixmap_item.setPixmap(pixmap)
            
        self.scene.setSceneRect(0, 0, w, h)

    # --- Landmark UI Draw & Drag ---
    def set_landmarks(self, landmarks_dict: dict):
        """Sets and renders coordinates on the canvas."""
        self.clear_landmarks_ui()
        
        for vert, points in landmarks_dict.items():
            self.landmarks[vert] = {}
            color = self.vertebra_colors.get(vert, Qt.red)
            
            for name, (x, y) in points.items():
                item = LandmarkItem(vert, name, self, size=10, color=color)
                item.setPos(x, y)
                self.scene.addItem(item)
                self.landmarks[vert][name] = item
                
        # Draw vertebral boundary contour lines connecting landmarks
        self.update_contour_lines()

    def get_landmarks(self) -> dict:
        """Extracts current landmark locations as a dictionary."""
        output = {}
        for vert, points in self.landmarks.items():
            output[vert] = {}
            for name, item in points.items():
                pos = item.pos()
                output[vert][name] = (pos.x(), pos.y())
        return output

    def update_contour_lines(self):
        """Re-draws geometric contours connecting C2, C3, C4 nodes."""
        # Clear existing lines/paths
        for vert, items in self.contour_lines.items():
            for item in items:
                self.scene.removeItem(item)
        self.contour_lines.clear()
        
        from PySide6.QtWidgets import QGraphicsPathItem
        from PySide6.QtGui import QPainterPath
        
        for vert, points in self.landmarks.items():
            self.contour_lines[vert] = []
            
            # Check if all 5 points are available
            required = ["SA", "SP", "IP", "IM", "IA"]
            if not all(k in points for k in required):
                continue
                
            p_SA = points["SA"].pos()
            p_SP = points["SP"].pos()
            p_IP = points["IP"].pos()
            p_IM = points["IM"].pos()
            p_IA = points["IA"].pos()
            
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
            
            color = self.vertebra_colors[vert]
            pen = QPen(color, 2.5, Qt.SolidLine)
            brush = QBrush(QColor(color.red(), color.green(), color.blue(), 45)) # 18% opacity fill
            
            path_item = QGraphicsPathItem(path)
            path_item.setPen(pen)
            path_item.setBrush(brush)
            path_item.setZValue(-2) # Put lines below handles but above image
            
            self.scene.addItem(path_item)
            self.contour_lines[vert].append(path_item)

    # --- Mouse Controls: Panning, Zooming, and Calibration ---
    def wheelEvent(self, event):
        """Zooming in/out with the mouse wheel."""
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
        """Manages landmark clicks, calibrations, and pans."""
        if self.calibration_mode and event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            self.calibration_points.append(pos)
            
            # Place calibration marker dot
            dot = self.scene.addEllipse(pos.x()-4, pos.y()-4, 8, 8, QPen(Qt.yellow), QBrush(Qt.yellow))
            dot.setZValue(5)
            
            if len(self.calibration_points) == 2:
                # Complete line drawing
                pt1, pt2 = self.calibration_points
                self.calibration_line = self.scene.addLine(pt1.x(), pt1.y(), pt2.x(), pt2.y(), QPen(Qt.yellow, 2))
                self.calibration_line.setZValue(4)
                
                # Perform distance prompt
                dx = pt2.x() - pt1.x()
                dy = pt2.y() - pt1.y()
                pixel_dist = np.sqrt(dx**2 + dy**2)
                
                val, ok = QInputDialog.getDouble(
                    self, 
                    "Calibration Scale", 
                    "Enter actual length of calibration ruler in millimeters (mm):",
                    10.0, 0.1, 500.0, 2
                )
                
                if ok and val > 0:
                    scale = pixel_dist / val
                    self.calibration_scale = scale
                    self.calibration_completed.emit(scale)
                    QMessageBox.information(
                        self, "Calibration Complete", 
                        f"Scale configured: {scale:.2f} pixels/mm."
                    )
                
                # Exit calibration mode
                self.calibration_mode = False
                self.setDragMode(QGraphicsView.NoDrag)
                
            return
            
        # Panning behavior: hold right-click to drag/pan
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            # Create a fake left-click press to trigger standard drag behavior
            fake_event = QCursor.pos()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    # --- OpenCV Image Enhancements ---
    def apply_brightness_contrast(self, brightness: int, contrast: int):
        """Applies brightness and contrast filters on the loaded image."""
        if self.display_image is None:
            return
            
        self.brightness = brightness
        self.contrast = contrast
        
        # Formula: new_img = img * (contrast/127 + 1) - contrast + brightness
        c_factor = (contrast / 127.0) + 1.0
        buf = cv2.convertScaleAbs(self.display_image, alpha=c_factor, beta=brightness)
        self.cv_image = buf
        self._update_pixmap()

    def apply_clahe(self):
        """Applies Contrast Limited Adaptive Histogram Equalization."""
        if self.display_image is None:
            return
        gray = cv2.cvtColor(self.display_image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        res = clahe.apply(gray)
        self.display_image = cv2.cvtColor(res, cv2.COLOR_GRAY2BGR)
        self.apply_brightness_contrast(self.brightness, self.contrast)

    def apply_equalize_hist(self):
        """Applies standard global histogram equalization."""
        if self.display_image is None:
            return
        gray = cv2.cvtColor(self.display_image, cv2.COLOR_BGR2GRAY)
        res = cv2.equalizeHist(gray)
        self.display_image = cv2.cvtColor(res, cv2.COLOR_GRAY2BGR)
        self.apply_brightness_contrast(self.brightness, self.contrast)

    def apply_sharpen(self):
        """Applies a sharpening filter matrix to enhance bone edges."""
        if self.display_image is None:
            return
        kernel = np.array([[0, -1, 0], 
                           [-1, 5, -1], 
                           [0, -1, 0]])
        self.display_image = cv2.filter2D(self.display_image, -1, kernel)
        self.apply_brightness_contrast(self.brightness, self.contrast)

    def reset_filters(self):
        """Resets image matrix back to original source file."""
        if not self.original_image_path:
            return
        self.load_image(self.original_image_path)

    # --- Canvas Resets ---
    def clear_landmarks_ui(self):
        """Clears GUI landmark nodes and contour lines."""
        for vert, points in self.landmarks.items():
            for pt in points.values():
                self.scene.removeItem(pt)
        self.landmarks.clear()
        
        for vert, lines in self.contour_lines.items():
            for line in lines:
                self.scene.removeItem(line)
        self.contour_lines.clear()

    def clear_all(self):
        """Clears everything except the main image pixmap."""
        self.clear_landmarks_ui()
        if self.calibration_line:
            self.scene.removeItem(self.calibration_line)
            self.calibration_line = None
        self.calibration_points.clear()
        self.calibration_mode = False
