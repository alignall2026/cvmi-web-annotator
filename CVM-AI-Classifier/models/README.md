# CVM Classification Models

This directory contains the model architectures and configuration files. Due to size limitations, the trained model weights are not included in the repository.

## Downloading Model Weights

### Available Models
| Model Name | Accuracy | File Size | Download Link |
|------------|----------|------------|---------------|
| ConvNeXt | 54.00% | 190MB | [Download](https://drive.google.com/file/d/1fnHZKQP_qeRWQiBYeO-E3fWasgTCCv7M/view?usp=drive_link) |


### Installation Instructions
1. Download your chosen model weights from the links above
2. Place the .pth file in this directory
3. Ensure the filename matches exactly what's specified in main.py

## Model Performance Details

### ConvNeXt
- Best overall performance
- Recommended for production use
- Balanced speed-accuracy tradeoff

## Usage Notes
- Models expect input images of size 224x224
- Input should be normalized according to ImageNet standards
- For detailed usage instructions, refer to the main README

For any issues with model downloads, please create an issue in the repository.
