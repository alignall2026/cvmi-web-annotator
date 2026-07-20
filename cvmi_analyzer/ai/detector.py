import os
import cv2
import numpy as np
from cvmi_analyzer.config import MODEL_DIR

try:
    import torch
    import torchvision.transforms as T
    from PIL import Image
    from cvmi_analyzer.ai.detector_model import CVMILandmarkUNet
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

LANDMARK_KEYS = [
    ("C2", "SA"), ("C2", "SP"), ("C2", "IP"), ("C2", "IM"), ("C2", "IA"),
    ("C3", "SA"), ("C3", "SP"), ("C3", "IP"), ("C3", "IM"), ("C3", "IA"),
    ("C4", "SA"), ("C4", "SP"), ("C4", "IP"), ("C4", "IM"), ("C4", "IA")
]

class CVMIDetector:
    def __init__(self, model_path=None):
        self.model_path = model_path or (MODEL_DIR / "cvmi_landmark_detector.pth")
        self.model = None
        self.device = None
        
        if HAS_TORCH:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._load_model()
            
    def _load_model(self):
        """Attempts to load PyTorch U-Net weights from disk."""
        if not HAS_TORCH:
            return
            
        if os.path.exists(self.model_path):
            try:
                self.model = CVMILandmarkUNet(num_landmarks=15, img_size=256)
                # Load weights onto device
                state_dict = torch.load(self.model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.model.to(self.device)
                self.model.eval()
                print(f"Loaded PyTorch CVMI Landmark U-Net weights from: {self.model_path}")
            except Exception as e:
                print(f"Error loading PyTorch U-Net weights: {e}. Falling back to OpenCV template.")
                self.model = None
        else:
            print("No landmark model checkpoint found. Falling back to OpenCV spine-column profiling.")

    def detect_landmarks(self, image_path: str) -> dict[str, dict[str, tuple[float, float]]]:
        """
        Detects 15 landmarks for C2, C3, and C4 vertebrae.
        If PyTorch model weights are available, uses CNN heatmap regression.
        Otherwise, runs OpenCV Sobel edge profiling to place templates.
        """
        img = cv2.imread(image_path)
        if img is None:
            # Return default template coordinates
            return self._get_default_layout(600, 800)
            
        h_orig, w_orig = img.shape[:2]
        
        # --- Case A: Use PyTorch Deep Learning Model ---
        if HAS_TORCH and self.model is not None:
            try:
                # Preprocess image
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                
                # Setup dataset-matching transformations
                transform = T.Compose([
                    T.Resize((256, 256)),
                    T.ToTensor(),
                    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                ])
                
                img_tensor = transform(pil_img).unsqueeze(0).to(self.device) # Shape (1, 3, 256, 256)
                
                with torch.no_grad():
                    # Predict coordinates in [0, 256] range: shape (1, 15, 2)
                    predicted_coords = self.model(img_tensor).squeeze(0).cpu().numpy()
                
                # Scale landmarks back to original dimensions
                scale_x = w_orig / 256.0
                scale_y = h_orig / 256.0
                
                landmarks = {"C2": {}, "C3": {}, "C4": {}}
                for idx, (vert, key) in enumerate(LANDMARK_KEYS):
                    x_pred = float(predicted_coords[idx, 0] * scale_x)
                    y_pred = float(predicted_coords[idx, 1] * scale_y)
                    landmarks[vert][key] = (x_pred, y_pred)
                    
                return landmarks
            except Exception as e:
                print(f"PyTorch landmark detection failed: {e}. Running OpenCV fallback.")
        
        # --- Case B: Fallback OpenCV Profiler Heuristics ---
        return self._run_sobel_profiler(img, w_orig, h_orig)

    def _run_sobel_profiler(self, img, w, h):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        try:
            # Downsample for profiling
            scale_w = 400.0 / w
            scale_h = 400.0 / h
            small = cv2.resize(gray, (400, 400))
            
            # Filter noise and highlight vertical contours
            filtered = cv2.bilateralFilter(small, 9, 75, 75)
            sobelx = cv2.Sobel(filtered, cv2.CV_64F, 1, 0, ksize=3)
            sobelx = np.absolute(sobelx)
            sobelx = np.uint8(255 * (sobelx / np.max(sobelx)))
            
            _, thresh = cv2.threshold(sobelx, 50, 255, cv2.THRESH_BINARY)
            col_sums = np.sum(thresh, axis=0)
            
            # Spine column lies in the left 12% to 38% region for right-facing cephalograms
            start_col = int(400 * 0.12)
            end_col = int(400 * 0.38)
            
            best_col_small = np.argmax(col_sums[start_col:end_col]) + start_col
            best_col = int(best_col_small / scale_w)
        except Exception:
            best_col = int(w * 0.25)
            
        if best_col < int(w * 0.10) or best_col > int(w * 0.40):
            best_col = int(w * 0.25)
            
        spine_x = best_col + int(w * 0.075)
        stack_y_center = int(h * 0.74)
        
        box_w = int(w * 0.065)
        box_h = int(h * 0.055)
        spacing = int(h * 0.035)
        
        c2_y = stack_y_center - box_h - spacing
        c3_y = stack_y_center
        c4_y = stack_y_center + box_h + spacing
        
        landmarks = {}
        landmarks["C2"] = self._create_vertebra_landmarks(spine_x, c2_y, box_w, box_h, is_c2=True)
        landmarks["C3"] = self._create_vertebra_landmarks(spine_x, c3_y, box_w, box_h, is_c2=False)
        landmarks["C4"] = self._create_vertebra_landmarks(spine_x, c4_y, box_w, box_h, is_c2=False)
        
        return landmarks

    def _create_vertebra_landmarks(self, cx: int, cy: int, bw: int, bh: int, is_c2: bool) -> dict[str, tuple[float, float]]:
        x_left = cx - bw // 2
        x_right = cx + bw // 2
        
        if is_c2:
            # C2 has a sloped superior border (taller posteriorly)
            y_top_left = cy - int(bh * 0.6)
            y_top_right = cy - int(bh * 0.3)
            y_bottom = cy + bh // 2
            y_concave = y_bottom - int(bh * 0.12)
            return {
                "SA": (float(x_right), float(y_top_right)),
                "SP": (float(x_left), float(y_top_left)),
                "IA": (float(x_right), float(y_bottom)),
                "IP": (float(x_left), float(y_bottom)),
                "IM": (float(cx), float(y_concave))
            }
        else:
            y_top = cy - bh // 2
            y_bottom = cy + bh // 2
            y_concave = y_bottom - int(bh * 0.15)
            return {
                "SA": (float(x_right), float(y_top)),
                "SP": (float(x_left), float(y_top)),
                "IA": (float(x_right), float(y_bottom)),
                "IP": (float(x_left), float(y_bottom)),
                "IM": (float(cx), float(y_concave))
            }

    def _get_default_layout(self, h: int, w: int) -> dict[str, dict[str, tuple[float, float]]]:
        cx, cy = int(w * 0.355), int(h * 0.74)
        bw, bh = int(w * 0.065), int(h * 0.055)
        spacing = int(h * 0.035)
        return {
            "C2": self._create_vertebra_landmarks(cx, cy - bh - spacing, bw, bh, True),
            "C3": self._create_vertebra_landmarks(cx, cy, bw, bh, False),
            "C4": self._create_vertebra_landmarks(cx, cy + bh + spacing, bw, bh, False)
        }
