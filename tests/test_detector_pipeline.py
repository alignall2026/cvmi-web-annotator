import os
import json
import tempfile
import unittest
import numpy as np

try:
    import torch
    from cvmi_analyzer.ai.detector_model import SoftArgmax2D, CVMILandmarkUNet
    from cvmi_analyzer.ai.landmark_dataset import CVMILandmarkDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class TestDetectorPipeline(unittest.TestCase):
    
    @unittest.skipUnless(HAS_TORCH, "PyTorch is required for this test")
    def test_soft_argmax_peaked(self):
        """Verifies that SoftArgmax2D correctly decodes a single peaked pixel to coordinates."""
        img_size = 256
        heatmap_size = 64
        
        # Initialize SoftArgmax layer
        layer = SoftArgmax2D(img_size=img_size, heatmap_size=heatmap_size, beta=100.0)
        
        # Create a batch of shape (1, 1, 64, 64) with a strong peak at (row=32, col=16)
        # Note: 'y' corresponds to row 32, 'x' corresponds to col 16
        logits = torch.zeros(1, 1, heatmap_size, heatmap_size)
        logits[0, 0, 32, 16] = 50.0 # Make this pixel extremely high
        
        coords = layer(logits) # Shape (1, 1, 2)
        
        # Expected coordinates scaled to img_size=256:
        # x_expected = 16 * (256 / 63) = 65.0158
        # y_expected = 32 * (256 / 63) = 130.0317
        expected_x = 16.0 * (img_size / (heatmap_size - 1.0))
        expected_y = 32.0 * (img_size / (heatmap_size - 1.0))
        
        pred_x = coords[0, 0, 0].item()
        pred_y = coords[0, 0, 1].item()
        
        self.assertAlmostEqual(pred_x, expected_x, places=1)
        self.assertAlmostEqual(pred_y, expected_y, places=1)

    @unittest.skipUnless(HAS_TORCH, "PyTorch is required for this test")
    def test_unet_forward_pass(self):
        """Verifies the input-output shapes of the CVMILandmarkUNet model."""
        model = CVMILandmarkUNet(num_landmarks=15, img_size=256)
        model.eval()
        
        # Dummy batch of 1 RGB image: shape (1, 3, 256, 256)
        dummy_input = torch.randn(1, 3, 256, 256)
        
        with torch.no_grad():
            output_coords = model(dummy_input) # Expected shape: (1, 15, 2)
            
        self.assertEqual(output_coords.shape, (1, 15, 2))
        
    @unittest.skipUnless(HAS_TORCH, "PyTorch is required for this test")
    def test_landmark_dataset_loader(self):
        """Verifies dataset scanning, resizing, and coordinates scaling on temporary mockup files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Create a dummy image file (100x100 pixels)
            dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
            img_path = os.path.join(tmp_dir, "test_ceph.png")
            import cv2
            cv2.imwrite(img_path, dummy_img)
            
            # 2. Create matching dummy annotation JSON
            # Put landmarks at (10.0, 20.0), which are scaled during load
            landmarks_data = {}
            for vert in ["C2", "C3", "C4"]:
                landmarks_data[vert] = {}
                for key in ["SA", "SP", "IA", "IP", "IM"]:
                    landmarks_data[vert][key] = (10.0, 20.0)
                    
            json_data = {
                "image_path": "test_ceph.png",
                "landmarks": landmarks_data
            }
            
            json_path = os.path.join(tmp_dir, "test_ceph.png_landmarks.json")
            with open(json_path, 'w') as f:
                json.dump(json_data, f)
                
            # 3. Instantiate Dataset and read sample
            dataset = CVMILandmarkDataset(tmp_dir, img_size=256, is_training=False)
            self.assertEqual(len(dataset), 1)
            
            img_tensor, landmarks_tensor = dataset[0]
            
            # Check tensor shapes
            self.assertEqual(img_tensor.shape, (3, 256, 256))
            self.assertEqual(landmarks_tensor.shape, (15, 2))
            
            # Original landmark (10, 20) on 100x100 image should scale to (25.6, 51.2) on 256x256 image
            expected_x = 10.0 * (256.0 / 100.0)
            expected_y = 20.0 * (256.0 / 100.0)
            
            self.assertAlmostEqual(landmarks_tensor[0, 0].item(), expected_x, places=2)
            self.assertAlmostEqual(landmarks_tensor[0, 1].item(), expected_y, places=2)

if __name__ == "__main__":
    unittest.main()
