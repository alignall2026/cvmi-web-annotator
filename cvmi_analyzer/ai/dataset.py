import os
import cv2
import numpy as np
from PIL import Image

# We wrap PyTorch imports inside try-except blocks to allow the application to launch 
# and fall back to manual calculations even if PyTorch is not installed in the environment.
try:
    import torch
    from torch.utils.data import Dataset
    import torchvision.transforms as T
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    # Define a stub Dataset class for linting safety
    class Dataset:
        pass
    HAS_TORCH = False

class CVMIDataset(Dataset):
    """
    Custom PyTorch Dataset for CVMI Classification.
    Expects dataset_path to have subdirectories: CS1, CS2, CS3, CS4, CS5, CS6.
    """
    def __init__(self, dataset_path, img_size=224, is_training=True, transform=None):
        self.dataset_path = dataset_path
        self.img_size = img_size
        self.is_training = is_training
        self.transform = transform
        
        self.classes = ["CS1", "CS2", "CS3", "CS4", "CS5", "CS6"]
        self.class_to_idx = {cls: idx for idx, cls in enumerate(self.classes)}
        
        self.image_paths = []
        self.labels = []
        
        if os.path.exists(dataset_path):
            self._load_dataset()
            
        if self.transform is None and HAS_TORCH:
            self.transform = self._get_default_transforms()

    def _load_dataset(self):
        for cls in self.classes:
            cls_dir = os.path.join(self.dataset_path, cls)
            if not os.path.isdir(cls_dir):
                continue
            for fname in os.listdir(cls_dir):
                fpath = os.path.join(cls_dir, fname)
                # Check extension
                ext = os.path.splitext(fname)[1].lower()
                if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]:
                    self.image_paths.append(fpath)
                    self.labels.append(self.class_to_idx[cls])

    def _get_default_transforms(self):
        if self.is_training:
            return T.Compose([
                T.Resize((self.img_size, self.img_size)),
                T.RandomRotation(15),
                T.RandomAffine(degrees=0, translate=(0.05, 0.05), scale=(0.95, 1.05)),
                T.ColorJitter(brightness=0.2, contrast=0.2),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
        else:
            return T.Compose([
                T.Resize((self.img_size, self.img_size)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        if not HAS_TORCH:
            raise RuntimeError("PyTorch is not installed. AI training is unavailable.")
            
        img_path = self.image_paths[idx]
        label = self.labels[idx]
        
        # Load using OpenCV to handle possible image errors, convert to RGB
        cv_img = cv2.imread(img_path)
        if cv_img is None:
            # Create a blank fallback image if image is corrupted
            img = Image.fromarray(np.zeros((self.img_size, self.img_size, 3), dtype=np.uint8))
        else:
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv_img)
            
        if self.transform:
            img_tensor = self.transform(img)
        else:
            img_tensor = T.ToTensor()(img)
            
        return img_tensor, label
