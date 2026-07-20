import torch
import torch.nn as nn
import torchvision.models as models

class SoftArgmax2D(nn.Module):
    """
    Differentiable spatial soft-argmax layer.
    Converts 2D heatmaps of shape (B, C, H, W) to sub-pixel coordinates of shape (B, C, 2)
    relative to the target input image size (e.g. 256x256).
    """
    def __init__(self, img_size=256, heatmap_size=64, beta=50.0):
        super().__init__()
        self.img_size = img_size
        self.heatmap_size = heatmap_size
        self.beta = beta
        
        # Create coordinate grids
        # coordinates range from 0 to img_size
        y_grid, x_grid = torch.meshgrid(
            torch.arange(heatmap_size, dtype=torch.float32),
            torch.arange(heatmap_size, dtype=torch.float32),
            indexing='ij'
        )
        
        # Scale indices to input image pixel coordinates
        x_grid = x_grid * (img_size / (heatmap_size - 1.0))
        y_grid = y_grid * (img_size / (heatmap_size - 1.0))
        
        # Flatten and register as buffers
        self.register_buffer('x_grid', x_grid.view(-1))
        self.register_buffer('y_grid', y_grid.view(-1))

    def forward(self, x):
        # x is the logits heatmap: (B, C, H, W)
        B, C, H, W = x.shape
        # Flatten spatial dimensions: (B, C, H*W)
        flat_x = x.view(B, C, H * W)
        # Spatial softmax
        probs = torch.softmax(self.beta * flat_x, dim=-1)
        # Expectation
        x_coords = torch.sum(probs * self.x_grid, dim=-1)
        y_coords = torch.sum(probs * self.y_grid, dim=-1)
        # Concat to (B, C, 2)
        return torch.stack([x_coords, y_coords], dim=-1)


class DecoderBlock(nn.Module):
    """Convolutional decoder block with upsampling and skip-connection concatenation."""
    def __init__(self, in_channels, skip_channels, out_channels):
        super().__init__()
        self.upsample = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = nn.Sequential(
            nn.Conv2d((in_channels // 2) + skip_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x, skip):
        x = self.upsample(x)
        # Pad if dimensions mismatch slightly due to odd resolutions
        diff_h = skip.size()[2] - x.size()[2]
        diff_w = skip.size()[3] - x.size()[3]
        if diff_h > 0 or diff_w > 0:
            x = nn.functional.pad(x, [diff_w // 2, diff_w - diff_w // 2,
                                     diff_h // 2, diff_h - diff_h // 2])
        x = torch.cat([x, skip], dim=1)
        return self.conv(x)


class CVMILandmarkUNet(nn.Module):
    """
    U-Net Landmark Regression model.
    Uses pretrained ResNet-18 as an encoder, a custom decoder,
    and a Soft-Argmax coordinate regression output head.
    """
    def __init__(self, num_landmarks=15, img_size=256):
        super().__init__()
        self.img_size = img_size
        
        # Load pre-trained ResNet-18 backbone
        resnet = models.resnet18(pretrained=True)
        
        # Encoder stages
        self.init_conv = nn.Sequential(
            resnet.conv1,
            resnet.bn1,
            resnet.relu
        ) # Output: (B, 64, 128, 128)
        self.maxpool = resnet.maxpool # Output: (B, 64, 64, 64)
        
        self.layer1 = resnet.layer1   # Output: (B, 64, 64, 64)
        self.layer2 = resnet.layer2   # Output: (B, 128, 32, 32)
        self.layer3 = resnet.layer3   # Output: (B, 256, 16, 16)
        self.layer4 = resnet.layer4   # Output: (B, 512, 8, 8)
        
        # Decoder stages
        self.decoder3 = DecoderBlock(in_channels=512, skip_channels=256, out_channels=256) # 8x8 -> 16x16
        self.decoder2 = DecoderBlock(in_channels=256, skip_channels=128, out_channels=128) # 16x16 -> 32x32
        self.decoder1 = DecoderBlock(in_channels=128, skip_channels=64, out_channels=64)   # 32x32 -> 64x64
        
        # Output layers (64x64)
        self.final_conv = nn.Conv2d(64, num_landmarks, kernel_size=1)
        
        # Soft-argmax decoder maps heatmaps back to coordinate coordinates
        self.soft_argmax = SoftArgmax2D(img_size=img_size, heatmap_size=64)

    def forward(self, x):
        # --- Encoder ---
        x0 = self.init_conv(x)   # (B, 64, 128, 128)
        x1 = self.maxpool(x0)    # (B, 64, 64, 64)
        
        x1 = self.layer1(x1)     # (B, 64, 64, 64)
        x2 = self.layer2(x1)     # (B, 128, 32, 32)
        x3 = self.layer3(x2)     # (B, 256, 16, 16)
        x4 = self.layer4(x3)     # (B, 512, 8, 8)
        
        # --- Decoder ---
        d3 = self.decoder3(x4, x3)  # (B, 256, 16, 16)
        d2 = self.decoder2(d3, x2)  # (B, 128, 32, 32)
        d1 = self.decoder1(d2, x1)  # (B, 64, 64, 64)
        
        # Heatmap logits (B, 15, 64, 64)
        heatmaps = self.final_conv(d1)
        
        # Coordinates (B, 15, 2)
        coords = self.soft_argmax(heatmaps)
        
        return coords
