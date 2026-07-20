import unittest
from cvmi_analyzer.core.cvmi import (
    euclidean_distance, calculate_concavity_depth, 
    calculate_vertebra_metrics, determine_cvmi_stage
)

class TestCVMI(unittest.TestCase):
    
    def test_euclidean_distance(self):
        p1 = (0.0, 0.0)
        p2 = (3.0, 4.0)
        self.assertAlmostEqual(euclidean_distance(p1, p2), 5.0)

    def test_calculate_concavity_depth(self):
        # In screen coordinates, y increases downwards.
        # Line from IA (0, 10) to IP (10, 10). Line is horizontal at y=10.
        # Vertebra body lies above this line (towards smaller y).
        # A concavity means the bottom border curves upwards inside the body (smaller y).
        ia = (0.0, 10.0)
        ip = (10.0, 10.0)
        
        # Test case 1: Flat border. IM is exactly on the chord. Depth should be 0.
        im_flat = (5.0, 10.0)
        self.assertAlmostEqual(calculate_concavity_depth(ia, ip, im_flat), 0.0)
        
        # Test case 2: Concavity. IM curves upwards inside body (y=8, less than 10).
        im_concave = (5.0, 8.0)
        self.assertAlmostEqual(calculate_concavity_depth(ia, ip, im_concave), 2.0)
        
        # Test case 3: Convex border. IM curves downwards outside body (y=12, greater than 10).
        im_convex = (5.0, 12.0)
        self.assertAlmostEqual(calculate_concavity_depth(ia, ip, im_convex), -2.0)

    def test_calculate_vertebra_metrics(self):
        # We specify coordinate maps representing a square vertebra (width 10, height 10) with no concavity.
        # Scale = 1.0.
        landmarks = {
            "SA": (10.0, 0.0),   # Superior-Anterior (Anterior is right)
            "SP": (0.0, 0.0),    # Superior-Posterior (Posterior is left)
            "IA": (10.0, 10.0),  # Inferior-Anterior
            "IP": (0.0, 10.0),   # Inferior-Posterior
            "IM": (5.0, 10.0)    # Inferior-Middle (Flat)
        }
        
        metrics = calculate_vertebra_metrics(landmarks, scale=1.0)
        self.assertAlmostEqual(metrics["AH"], 10.0)  # SA to IA (y=0 to y=10)
        self.assertAlmostEqual(metrics["PH"], 10.0)  # SP to IP (y=0 to y=10)
        self.assertAlmostEqual(metrics["SW"], 10.0)  # SA to SP (x=10 to x=0)
        self.assertAlmostEqual(metrics["IW"], 10.0)  # IA to IP (x=10 to x=0)
        self.assertAlmostEqual(metrics["CD"], 0.0)   # Flat concavity
        self.assertAlmostEqual(metrics["AR"], 1.0)   # Width / Height = 10 / 10 = 1.0 (Square)
        self.assertAlmostEqual(metrics["WS"], 1.0)   # AH / PH = 10 / 10 = 1.0 (Not wedged)

    def test_determine_cvmi_stage(self):
        # Helper to generate standard flat/curved metrics dicts
        def make_mock_metrics(concavity_depth=0.0, aspect_ratio=1.5, wedge_factor=1.0):
            return {
                "CD": concavity_depth,
                "AR": aspect_ratio,
                "WS": wedge_factor,
                "AH": 10.0 * wedge_factor,
                "PH": 10.0,
                "H_avg": 10.0,
                "W_avg": 10.0 * aspect_ratio
            }
            
        # Test Case 1: CS1 (All flat, C3/C4 wedge shape)
        c2 = make_mock_metrics(0.0)
        c3 = make_mock_metrics(0.0, wedge_factor=0.8) # Wedged C3
        c4 = make_mock_metrics(0.0, wedge_factor=0.8) # Wedged C4
        stage, _ = determine_cvmi_stage(c2, c3, c4)
        self.assertEqual(stage, "CS1")
        
        # Test Case 2: CS2 (C2 concave, others flat, C3/C4 horizontal)
        c2 = make_mock_metrics(1.2) # Concavity >= 1.0
        c3 = make_mock_metrics(0.0, aspect_ratio=1.3)
        c4 = make_mock_metrics(0.0, aspect_ratio=1.3)
        stage, _ = determine_cvmi_stage(c2, c3, c4)
        self.assertEqual(stage, "CS2")
        
        # Test Case 3: CS3 (C2 and C3 concave, C4 flat)
        c2 = make_mock_metrics(1.2)
        c3 = make_mock_metrics(1.2, aspect_ratio=1.3)
        c4 = make_mock_metrics(0.0, aspect_ratio=1.3)
        stage, _ = determine_cvmi_stage(c2, c3, c4)
        self.assertEqual(stage, "CS3")
        
        # Test Case 4: CS4 (All concave, C3 and C4 rectangular horizontal)
        c2 = make_mock_metrics(1.2)
        c3 = make_mock_metrics(1.2, aspect_ratio=1.3) # AR >= 1.15
        c4 = make_mock_metrics(1.2, aspect_ratio=1.3)
        stage, _ = determine_cvmi_stage(c2, c3, c4)
        self.assertEqual(stage, "CS4")
        
        # Test Case 5: CS5 (All concave, C3 and C4 square)
        c2 = make_mock_metrics(1.2)
        c3 = make_mock_metrics(1.2, aspect_ratio=1.0) # AR 0.95 to 1.15
        c4 = make_mock_metrics(1.2, aspect_ratio=1.0)
        stage, _ = determine_cvmi_stage(c2, c3, c4)
        self.assertEqual(stage, "CS5")
        
        # Test Case 6: CS6 (All concave, C3 and C4 rectangular vertical)
        c2 = make_mock_metrics(1.2)
        c3 = make_mock_metrics(1.2, aspect_ratio=0.8) # AR < 0.95
        c4 = make_mock_metrics(1.2, aspect_ratio=0.8)
        stage, _ = determine_cvmi_stage(c2, c3, c4)
        self.assertEqual(stage, "CS6")

if __name__ == "__main__":
    unittest.main()
