import os
import time
import numpy as np

# Set matplotlib backend to Agg to avoid issues when running in sub-threads of PySide6
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, random_split
    import torchvision.models as models
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from cvmi_analyzer.config import APP_DATA_DIR, DEFAULT_MODEL_PATH, ONNX_MODEL_PATH
from cvmi_analyzer.ai.dataset import CVMIDataset

# 1. Custom CNN Model (Lightweight, robust, trains fast even on CPU)
if HAS_TORCH:
    class CVMICNN(nn.Module):
        def __init__(self, num_classes=6):
            super().__init__()
            self.features = nn.Sequential(
                # Block 1
                nn.Conv2d(3, 32, kernel_size=3, padding=1),
                nn.BatchNorm2d(32),
                nn.ReLU(inplace=True),
                nn.Conv2d(32, 32, kernel_size=3, padding=1),
                nn.BatchNorm2d(32),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),
                nn.Dropout2d(0.2),

                # Block 2
                nn.Conv2d(32, 64, kernel_size=3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.Conv2d(64, 64, kernel_size=3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),
                nn.Dropout2d(0.25),

                # Block 3
                nn.Conv2d(64, 128, kernel_size=3, padding=1),
                nn.BatchNorm2d(128),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),
                nn.Dropout2d(0.3)
            )
            self.classifier = nn.Sequential(
                nn.AdaptiveAvgPool2d((4, 4)),
                nn.Flatten(),
                nn.Linear(128 * 4 * 4, 256),
                nn.ReLU(inplace=True),
                nn.Dropout(0.4),
                nn.Linear(256, num_classes)
            )

        def forward(self, x):
            x = self.features(x)
            x = self.classifier(x)
            return x
else:
    class CVMICNN:
        pass

# 2. Plotting Utilities
def save_confusion_matrix(cm, classes, filepath):
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Validation Confusion Matrix')
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    # Label grid cells
    thresh = cm.max() / 2.
    for i, j in np.ndindex(cm.shape):
        plt.text(j, i, format(cm[i, j], 'd'),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.ylabel('True Stage')
    plt.xlabel('Predicted Stage')
    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.close()

def save_roc_curves(y_true, y_probs, classes, filepath):
    plt.figure(figsize=(8, 6))
    
    # One-vs-Rest ROC curve calculation
    for i, cls in enumerate(classes):
        # Convert to binary
        y_true_binary = (y_true == i).astype(int)
        y_prob_cls = y_probs[:, i]
        
        # Calculate True Positive and False Positive rates manually to avoid heavy sklearn dependency
        thresholds = np.linspace(0, 1, 100)
        tpr = []
        fpr = []
        
        for t in thresholds:
            preds = (y_prob_cls >= t).astype(int)
            tp = np.sum((preds == 1) & (y_true_binary == 1))
            fp = np.sum((preds == 1) & (y_true_binary == 0))
            fn = np.sum((preds == 0) & (y_true_binary == 1))
            tn = np.sum((preds == 0) & (y_true_binary == 0))
            
            tpr.append(tp / (tp + fn) if (tp + fn) > 0 else 0.0)
            fpr.append(fp / (fp + tn) if (fp + tn) > 0 else 0.0)
            
        # Sort values
        sorted_indices = np.argsort(fpr)
        fpr = np.array(fpr)[sorted_indices]
        tpr = np.array(tpr)[sorted_indices]
        
        # Calculate approximate AUC under ROC using trapezoid rule
        auc = np.trapz(tpr, fpr)
        # Handle sign if order was reversed
        auc = abs(auc)
        
        plt.plot(fpr, tpr, label=f'{cls} (AUC = {auc:.2f})')
        
    plt.plot([0, 1], [0, 1], 'k--', label='Chance (AUC = 0.50)')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic (ROC)')
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.close()

def save_training_history(train_losses, val_losses, train_accs, val_accs, filepath):
    plt.figure(figsize=(12, 5))
    
    # Loss plot
    plt.subplot(1, 2, 1)
    plt.plot(train_losses, label='Train Loss')
    plt.plot(val_losses, label='Val Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Training & Validation Loss')
    plt.legend()
    
    # Accuracy plot
    plt.subplot(1, 2, 2)
    plt.plot(train_accs, label='Train Acc')
    plt.plot(val_accs, label='Val Acc')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.title('Training & Validation Accuracy')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.close()

# 3. Model Training Pipeline
def run_training_pipeline(dataset_dir, epochs=10, batch_size=16, lr=0.001, progress_callback=None):
    """
    Runs the CVMI model training process.
    progress_callback is a function that accepts (epoch, max_epochs, train_loss, val_loss, val_acc, status_text)
    """
    if not HAS_TORCH:
        if progress_callback:
            progress_callback(0, epochs, 0.0, 0.0, 0.0, "Error: PyTorch not installed")
        return False
        
    try:
        # Load dataset
        full_dataset = CVMIDataset(dataset_dir, is_training=True)
        if len(full_dataset) < 10:
            if progress_callback:
                progress_callback(0, epochs, 0.0, 0.0, 0.0, "Error: Dataset is too small (need >= 10 images)")
            return False
            
        # Train / Val Split
        val_size = int(0.2 * len(full_dataset))
        train_size = len(full_dataset) - val_size
        
        train_dataset, val_dataset = random_split(
            full_dataset, 
            [train_size, val_size],
            generator=torch.Generator().manual_seed(42)
        )
        
        # Apply validation transform to val dataset
        val_dataset.dataset.is_training = False
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=(train_size > batch_size))
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        # Setup device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Use CVMICNN or ResNet18 if transfer learning is desired
        # Here we use our custom CVMICNN for speed and self-contained weight initialization
        model = CVMICNN(num_classes=6).to(device)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=lr)
        
        train_losses, val_losses = [], []
        train_accs, val_accs = [], []
        
        if progress_callback:
            progress_callback(0, epochs, 0.0, 0.0, 0.0, f"Starting training on {device}...")
            
        for epoch in range(1, epochs + 1):
            model.train()
            running_loss = 0.0
            correct = 0
            total = 0
            
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                
                running_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
                
            epoch_train_loss = running_loss / len(train_dataset)
            epoch_train_acc = correct / total if total > 0 else 0.0
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            
            # For ROC and confusion matrix
            all_preds = []
            all_targets = []
            all_probs = []
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    
                    val_loss += loss.item() * inputs.size(0)
                    _, predicted = outputs.max(1)
                    val_total += targets.size(0)
                    val_correct += predicted.eq(targets).sum().item()
                    
                    probs = torch.softmax(outputs, dim=1)
                    
                    all_preds.extend(predicted.cpu().numpy())
                    all_targets.extend(targets.cpu().numpy())
                    all_probs.extend(probs.cpu().numpy())
                    
            epoch_val_loss = val_loss / len(val_dataset) if len(val_dataset) > 0 else 0.0
            epoch_val_acc = val_correct / val_total if val_total > 0 else 0.0
            
            train_losses.append(epoch_train_loss)
            val_losses.append(epoch_val_loss)
            train_accs.append(epoch_train_acc)
            val_accs.append(epoch_val_acc)
            
            status_txt = f"Epoch {epoch}/{epochs} - Loss: {epoch_train_loss:.4f} | Val Acc: {epoch_val_acc:.2%}"
            if progress_callback:
                progress_callback(epoch, epochs, epoch_train_loss, epoch_val_loss, epoch_val_acc, status_txt)
                
        # --- Post-Training Metrics & Exports ---
        # 1. Save training plot
        plot_dir = APP_DATA_DIR / "training_plots"
        plot_dir.mkdir(parents=True, exist_ok=True)
        
        save_training_history(train_losses, val_losses, train_accs, val_accs, plot_dir / "history.png")
        
        # 2. Confusion Matrix & ROC if validation set contains data
        if len(all_targets) > 0:
            all_preds = np.array(all_preds)
            all_targets = np.array(all_targets)
            all_probs = np.array(all_probs)
            
            classes = ["CS1", "CS2", "CS3", "CS4", "CS5", "CS6"]
            
            # Generate Confusion Matrix
            cm = np.zeros((6, 6), dtype=int)
            for t, p in zip(all_targets, all_preds):
                cm[t, p] += 1
                
            save_confusion_matrix(cm, classes, plot_dir / "confusion_matrix.png")
            save_roc_curves(all_targets, all_probs, classes, plot_dir / "roc_curves.png")
            
        # 3. Save PyTorch weights
        torch.save(model.state_dict(), DEFAULT_MODEL_PATH)
        
        # 4. Export to ONNX for production runtime interoperability
        dummy_input = torch.randn(1, 3, 224, 224, device=device)
        torch.onnx.export(
            model, 
            dummy_input, 
            ONNX_MODEL_PATH, 
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
        )
        
        if progress_callback:
            progress_callback(epochs, epochs, train_losses[-1], val_losses[-1], val_accs[-1], "Training Completed. Model exported successfully!")
            
        return True
    except Exception as e:
        import traceback
        err_msg = f"Training Error: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        if progress_callback:
            progress_callback(0, epochs, 0.0, 0.0, 0.0, f"Error: {str(e)}")
        return False
