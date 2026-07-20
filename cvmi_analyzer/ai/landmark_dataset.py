import os
import json
import cv2
import numpy as np
from PIL import Image

try:
    import torch
    from torch.utils.data import Dataset
    import torchvision.transforms as T
    import torchvision.transforms.functional as TF
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    class Dataset:
        pass

# Order of landmarks returned as a flat or structured array
LANDMARK_KEYS = [
    ("C2", "SA"), ("C2", "SP"), ("C2", "IP"), ("C2", "IM"), ("C2", "IA"),
    ("C3", "SA"), ("C3", "SP"), ("C3", "IP"), ("C3", "IM"), ("C3", "IA"),
    ("C4", "SA"), ("C4", "SP"), ("C4", "IP"), ("C4", "IM"), ("C4", "IA")
]

class CVMILandmarkDataset(Dataset):
    """
    Coordinate-aware PyTorch Dataset for CVMI landmark detection.
    Reads images and corresponding '<filename>_landmarks.json' files.
    """
    def __init__(self, dataset_dir, img_size=256, is_training=True, augment=True):
        self.dataset_dir = dataset_dir
        self.img_size = img_size
        self.is_training = is_training
        self.augment = augment
        
        self.samples = []
        if os.path.exists(dataset_dir):
            self._scan_dataset()
            
    def _scan_dataset(self):
        """Scans the directory for image files that have a matching landmark JSON file."""
        for fname in os.listdir(self.dataset_dir):
            ext = os.path.splitext(fname)[1].lower()
            if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]:
                json_name = f"{fname}_landmarks.json"
                json_path = os.path.join(self.dataset_dir, json_name)
                if os.path.exists(json_path):
                    self.samples.append({
                        "image_path": os.path.join(self.dataset_dir, fname),
                        "json_path": json_path
                    })
        print(f"Found {len(self.samples)} annotated CVMI landmark images in: {self.dataset_dir}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        if not HAS_TORCH:
            raise RuntimeError("PyTorch is not installed. AI training is unavailable.")
            
        sample = self.samples[idx]
        img_path = sample["image_path"]
        json_path = sample["json_path"]
        
        # 1. Load image
        img = cv2.imread(img_path)
        if img is None:
            # Fallback blank image
            img = np.zeros((self.img_size, self.img_size, 3), dtype=np.uint8)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
        orig_h, orig_w = img.shape[:2]
        
        # 2. Load landmarks
        with open(json_path, 'r') as f:
            data = json.load(f)
            landmarks_dict = data.get("landmarks", {})
            
        # Parse into standard flat numpy array of shape (15, 2)
        landmarks = []
        for vert, key in LANDMARK_KEYS:
            pt = landmarks_dict.get(vert, {}).get(key, (0.0, 0.0))
            landmarks.append(pt)
        landmarks = np.array(landmarks, dtype=np.float32) # (15, 2)
        
        # 3. Scale landmarks to standard image size [0, img_size]
        scale_x = self.img_size / orig_w
        scale_y = self.img_size / orig_h
        landmarks[:, 0] = landmarks[:, 0] * scale_x
        landmarks[:, 1] = landmarks[:, 1] * scale_y
        
        # Resize image
        img = cv2.resize(img, (self.img_size, self.img_size))
        
        # Convert to PIL Image for torchvision transforms
        pil_img = Image.fromarray(img)
        
        # 4. Apply Augmentations (only if training & augment=True)
        if self.is_training and self.augment:
            # Random Rotation (-10 to +10 degrees)
            if np.random.rand() > 0.5:
                angle = np.random.uniform(-10.0, 10.0)
                pil_img = TF.rotate(pil_img, angle)
                landmarks = self._rotate_landmarks(landmarks, angle, center=(self.img_size/2.0, self.img_size/2.0))
                
            # Random Translation / Scaling
            if np.random.rand() > 0.5:
                tx = np.random.uniform(-0.05, 0.05) * self.img_size
                ty = np.random.uniform(-0.05, 0.05) * self.img_size
                scale = np.random.uniform(0.95, 1.05)
                
                # Apply affine transform
                # TF.affine expects: angle, translate (list), scale, shear
                pil_img = TF.affine(pil_img, 0, [int(tx), int(ty)], scale, 0)
                # Apply translation and scale to landmarks
                landmarks = (landmarks - (self.img_size/2.0)) * scale + (self.img_size/2.0)
                landmarks[:, 0] += tx
                landmarks[:, 1] += ty
                
            # Color Jitter (does not affect coordinates)
            color_jitter = T.ColorJitter(brightness=0.2, contrast=0.2)
            pil_img = color_jitter(pil_img)
            
        # Convert image to tensor and normalize
        image_tensor = TF.to_tensor(pil_img)
        # Normalize with ImageNet stats
        normalize = T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        image_tensor = normalize(image_tensor)
        
        # Convert landmarks to tensor
        landmarks_tensor = torch.tensor(landmarks, dtype=torch.float32) # (15, 2)
        
        return image_tensor, landmarks_tensor

    def _rotate_landmarks(self, landmarks, angle, center):
        """Rotates coordinate points around center (in degrees)."""
        angle_rad = np.radians(-angle) # Negate since screen coords increase downwards
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        
        cx, cy = center
        rotated = []
        for x, y in landmarks:
            tx = x - cx
            ty = y - cy
            rx = tx * cos_a - ty * sin_a
            ry = tx * sin_a + ty * cos_a
            rotated.append((rx + cx, ry + cy))
        return np.array(rotated, dtype=np.float32)
