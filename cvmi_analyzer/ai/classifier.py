import os
import cv2
import numpy as np

try:
    import torch
    import torchvision.transforms as T
    from PIL import Image
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from cvmi_analyzer.config import DEFAULT_MODEL_PATH
from cvmi_analyzer.ai.training import CVMICNN

class CVMIClassifier:
    def __init__(self, model_path=None):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.classes = ["CS1", "CS2", "CS3", "CS4", "CS5", "CS6"]
        self.device = None
        self.model = None
        
        if HAS_TORCH:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._load_model()
            
    def _load_model(self):
        """Loads model weights if available, otherwise initialized randomly."""
        if not HAS_TORCH:
            return
        
        self.model = CVMICNN(num_classes=6)
        if os.path.exists(self.model_path):
            try:
                # Load weights onto matching device
                state_dict = torch.load(self.model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                print(f"Loaded CVMI Classifier model from: {self.model_path}")
            except Exception as e:
                print(f"Error loading model weights: {e}. Using uninitialized weights.")
        else:
            print("Model weights not found. Running with uninitialized weights (mock mode).")
            
        self.model.to(self.device)
        self.model.eval()

    def predict(self, image_path: str) -> tuple[str, float]:
        """
        Runs model inference on an input image.
        Returns (stage_code, confidence_probability).
        """
        if not HAS_TORCH or self.model is None:
            # Fallback if PyTorch is not available: mock prediction
            return "CS1", 0.50

        try:
            # Preprocess image
            cv_img = cv2.imread(image_path)
            if cv_img is None:
                return "CS1", 0.0
            
            # Prepare tensor
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv_img)
            
            transform = T.Compose([
                T.Resize((224, 224)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            
            img_tensor = transform(pil_img).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(img_tensor)
                probs = torch.softmax(outputs, dim=1)
                conf, idx = torch.max(probs, dim=1)
                
            return self.classes[idx.item()], conf.item()
            
        except Exception as e:
            print(f"Inference error: {e}")
            return "CS1", 0.0

    def generate_gradcam(self, image_path: str, target_stage: str = None) -> np.ndarray:
        """
        Generates a Grad-CAM heatmap overlay for the specified class stage.
        If target_stage is None, uses the model's top prediction.
        Returns an RGB BGR overlay image as a numpy array.
        """
        if not HAS_TORCH or self.model is None:
            # Return original image if no model
            return cv2.imread(image_path)
            
        try:
            # Read image
            orig_img = cv2.imread(image_path)
            if orig_img is None:
                return None
                
            h_orig, w_orig = orig_img.shape[:2]
            
            # Setup hook variables
            gradients = []
            activations = []
            
            def backward_hook(module, grad_input, grad_output):
                gradients.append(grad_output[0])
                
            def forward_hook(module, input, output):
                activations.append(output)
                
            # Register hooks to the last convolutional layer of self.model.features
            # For our CVMICNN, features[-3] is the last Conv2d layer
            target_layer = None
            for layer in reversed(self.model.features):
                if isinstance(layer, torch.nn.Conv2d):
                    target_layer = layer
                    break
                    
            if target_layer is None:
                return orig_img
                
            h_forward = target_layer.register_forward_hook(forward_hook)
            h_backward = target_layer.register_full_backward_hook(backward_hook)
            
            # Preprocess and forward pass
            cv_img = cv2.cvtColor(orig_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv_img)
            transform = T.Compose([
                T.Resize((224, 224)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            img_tensor = transform(pil_img).unsqueeze(0).to(self.device)
            img_tensor.requires_grad = True
            
            outputs = self.model(img_tensor)
            
            # Determine target class index
            if target_stage in self.classes:
                class_idx = self.classes.index(target_stage)
            else:
                class_idx = torch.argmax(outputs, dim=1).item()
                
            # Backward pass
            self.model.zero_grad()
            class_score = outputs[0, class_idx]
            class_score.backward()
            
            # Remove hooks
            h_forward.remove()
            h_backward.remove()
            
            if not gradients or not activations:
                return orig_img
                
            # Grad-CAM calculations
            grads_val = gradients[0].cpu().data.numpy()[0]
            acts_val = activations[0].cpu().data.numpy()[0]
            
            # Global average pool gradients
            weights = np.mean(grads_val, axis=(1, 2))
            
            # Weighted combination of feature maps
            cam = np.zeros(acts_val.shape[1:], dtype=np.float32)
            for i, w in enumerate(weights):
                cam += w * acts_val[i, :, :]
                
            # Apply ReLU
            cam = np.maximum(cam, 0)
            
            # Normalize CAM
            if np.max(cam) > 0:
                cam = cam / np.max(cam)
                
            # Resize heatmap to match original image size
            heatmap = cv2.resize(cam, (w_orig, h_orig))
            heatmap_color = cv2.applyColorMap(np.uint8(255 * heatmap), cv2.COLORMAP_JET)
            
            # Superimpose the heatmap on the original image (50% blend)
            overlay = cv2.addWeighted(orig_img, 0.6, heatmap_color, 0.4, 0)
            return overlay
            
        except Exception as e:
            print(f"Grad-CAM error: {e}")
            import traceback
            traceback.print_exc()
            return cv2.imread(image_path)
