import os
import time
import numpy as np

# Set matplotlib backend to Agg for non-GUI thread usage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, random_split
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from cvmi_analyzer.config import APP_DATA_DIR, MODEL_DIR
from cvmi_analyzer.ai.landmark_dataset import CVMILandmarkDataset
from cvmi_analyzer.ai.detector_model import CVMILandmarkUNet

LANDMARK_MODEL_PATH = MODEL_DIR / "cvmi_landmark_detector.pth"

def calculate_pixel_error(predictions, ground_truth):
    """
    Computes the Mean Radial Error (MRE) in pixels.
    predictions: (B, 15, 2) tensor
    ground_truth: (B, 15, 2) tensor
    """
    distances = torch.sqrt(torch.sum((predictions - ground_truth) ** 2, dim=-1)) # (B, 15)
    return torch.mean(distances).item()

def run_detector_training(dataset_dir, epochs=15, batch_size=4, lr=0.001, progress_callback=None):
    """
    Runs the deep learning landmark detection training loop.
    progress_callback: function accepting (epoch, max_epochs, train_loss, val_loss, val_pixel_err, status_text)
    """
    if not HAS_TORCH:
        if progress_callback:
            progress_callback(0, epochs, 0.0, 0.0, 0.0, "Error: PyTorch not installed")
        return False
        
    try:
        # 1. Load dataset
        full_dataset = CVMILandmarkDataset(dataset_dir, img_size=256, is_training=True, augment=True)
        if len(full_dataset) < 4:
            msg = f"Error: Dataset is too small (found {len(full_dataset)} images, need >= 4)"
            if progress_callback:
                progress_callback(0, epochs, 0.0, 0.0, 0.0, msg)
            return False
            
        # 2. Train/Val Split (80/20)
        val_size = max(1, int(0.2 * len(full_dataset)))
        train_size = len(full_dataset) - val_size
        
        train_dataset, val_dataset = random_split(
            full_dataset, 
            [train_size, val_size],
            generator=torch.Generator().manual_seed(42)
        )
        
        # Turn off augmentation for validation dataset
        val_dataset.dataset.augment = False
        
        train_loader = DataLoader(train_dataset, batch_size=min(batch_size, train_size), shuffle=True, drop_last=False)
        val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False)
        
        # 3. Setup device and model
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = CVMILandmarkUNet(num_landmarks=15, img_size=256).to(device)
        
        criterion = nn.SmoothL1Loss() # Huber Loss is robust to outliers
        optimizer = optim.Adam(model.parameters(), lr=lr)
        
        train_losses, val_losses = [], []
        val_pixel_errors = []
        
        if progress_callback:
            progress_callback(0, epochs, 0.0, 0.0, 0.0, f"Starting training on {device} ({train_size} train, {val_size} val images)...")
            
        best_val_error = float('inf')
        
        # 4. Training loop
        for epoch in range(1, epochs + 1):
            model.train()
            running_loss = 0.0
            
            for images, targets in train_loader:
                images, targets = images.to(device), targets.to(device)
                
                optimizer.zero_grad()
                predictions = model(images)
                loss = criterion(predictions, targets)
                loss.backward()
                optimizer.step()
                
                running_loss += loss.item() * images.size(0)
                
            epoch_train_loss = running_loss / len(train_dataset)
            
            # Validation Phase
            model.eval()
            val_loss = 0.0
            total_pixel_err = 0.0
            
            with torch.no_grad():
                for images, targets in val_loader:
                    images, targets = images.to(device), targets.to(device)
                    predictions = model(images)
                    loss = criterion(predictions, targets)
                    
                    val_loss += loss.item() * images.size(0)
                    total_pixel_err += calculate_pixel_error(predictions, targets)
                    
            epoch_val_loss = val_loss / len(val_dataset)
            epoch_pixel_err = total_pixel_err / len(val_dataset)
            
            train_losses.append(epoch_train_loss)
            val_losses.append(epoch_val_loss)
            val_pixel_errors.append(epoch_pixel_err)
            
            status_txt = f"Epoch {epoch}/{epochs} - Train Loss: {epoch_train_loss:.2f} | Val Loss: {epoch_val_loss:.2f} | Mean Error: {epoch_pixel_err:.1f} px"
            if progress_callback:
                progress_callback(epoch, epochs, epoch_train_loss, epoch_val_loss, epoch_pixel_err, status_txt)
                
            # Save checkpoint if it's the best validation error
            if epoch_pixel_err < best_val_error:
                best_val_error = epoch_pixel_err
                torch.save(model.state_dict(), LANDMARK_MODEL_PATH)
                
        # 5. Save training history plots
        plot_dir = APP_DATA_DIR / "training_plots"
        plot_dir.mkdir(parents=True, exist_ok=True)
        
        save_plots_history(train_losses, val_losses, val_pixel_errors, plot_dir / "landmark_history.png")
        
        if progress_callback:
            progress_callback(epochs, epochs, train_losses[-1], val_losses[-1], val_pixel_errors[-1], f"Training Finished. Model saved with best validation error: {best_val_error:.2f} pixels.")
            
        return True
    except Exception as e:
        import traceback
        err_msg = f"Training Error: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        if progress_callback:
            progress_callback(0, epochs, 0.0, 0.0, 0.0, f"Error: {str(e)}")
        return False

def save_plots_history(train_losses, val_losses, val_pixel_errors, filepath):
    """Generates training history curves for losses and landmark pixel accuracy."""
    plt.figure(figsize=(12, 5))
    
    # Loss plot
    plt.subplot(1, 2, 1)
    plt.plot(train_losses, label='Train Huber Loss')
    plt.plot(val_losses, label='Val Huber Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Coordinate Regression Loss')
    plt.legend()
    plt.grid(True)
    
    # Pixel Error plot
    plt.subplot(1, 2, 2)
    plt.plot(val_pixel_errors, label='Val Landmark Error (px)', color='orange')
    plt.xlabel('Epoch')
    plt.ylabel('Error (Pixels)')
    plt.title('Validation Mean Radial Error (MRE)')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.close()
