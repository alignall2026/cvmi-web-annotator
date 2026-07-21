import os
import sys
import numpy as np
from PIL import Image

# Add streamlit_apps to the path to import local modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'streamlit_apps'))

import torch
import torch.nn as nn
from cvm_convnext2 import CVMConvNeXt, load_model, preprocess_image, apply_gradcam

def test_inference():
    print("--------------------------------------------------")
    print("Verifying CVM-AI-Classifier Pipeline Execution...")
    print("--------------------------------------------------")
    
    # 1. Verify CUDA or CPU device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    
    # 2. Setup mock model path to trigger fallback/mock weights gracefully if needed
    os.environ['CVM_MODEL_PATH'] = 'models/best_model_Fine-tuning (Convnextv2).pth'
    
    # Mock streamlit objects or run function directly
    # We will instantiate CVMConvNeXt directly to test its architecture
    try:
        print("Instantiating ConvNeXt small model structure...")
        model = CVMConvNeXt(num_classes=6).to(device)
        model.eval()
        print("ConvNeXt architecture created successfully.")
    except Exception as e:
        print(f"FAILED to instantiate ConvNeXt model: {e}")
        sys.exit(1)
        
    # 3. Create a dummy image (e.g. 500x500 grayscale X-ray mock)
    print("Generating mock cephalometric radiograph image...")
    dummy_img = Image.fromarray(np.random.randint(0, 255, (500, 500), dtype=np.uint8))
    
    # 4. Preprocess
    try:
        print("Preprocessing image...")
        processed = preprocess_image(dummy_img).to(device)
        print(f"Preprocessed Image Shape: {processed.shape}")
    except Exception as e:
        print(f"FAILED image preprocessing: {e}")
        sys.exit(1)
        
    # 5. Run forward pass and Grad-CAM target stage block hook
    try:
        print("Running forward pass and Grad-CAM feature hooks...")
        target_layer = model.convnext.stages[-1].blocks[-1]
        
        # Test hook registration and forward pass
        cam, target_class, output = apply_gradcam(model, processed, target_layer)
        print(f"Forward Pass Completed Successfully!")
        print(f"Mock Predicted CVMI Stage Index: CS{target_class + 1}")
        print(f"Generated Heatmap Shape: {cam.shape}")
        
        probabilities = torch.nn.functional.softmax(output, dim=1).squeeze().tolist()
        print("\nPredicted Class Confidence Scores:")
        for idx, conf in enumerate(probabilities):
            print(f" - CS{idx + 1}: {conf * 100:.2f}%")
            
        print("\nPipeline Verification: SUCCESS")
        print("--------------------------------------------------")
    except Exception as e:
        print(f"FAILED during pipeline execution/Grad-CAM hooks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_inference()
