import streamlit as st
import torch
import torch.nn as nn
import timm
from PIL import Image
import torchvision.transforms as transforms
import numpy as np
import matplotlib.pyplot as plt
import cv2
import os

# Model architecture
class CVMConvNeXt(nn.Module):
    def __init__(self, num_classes=6):
        super(CVMConvNeXt, self).__init__()
        self.convnext = timm.create_model('convnext_small', pretrained=True)

        # Replace classifier
        num_features = self.convnext.head.fc.in_features
        self.convnext.head.fc = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(num_features, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Dropout(0.4),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        return self.convnext(x)


# Add image format check
def check_image_format(image):
    if image.mode == 'RGBA':
        st.warning("RGBA image detected - alpha channel will be removed for processing")
        # Convert RGBA to RGB
        image = image.convert('RGB')
    elif image.mode not in ['RGB', 'L']:
        st.error(f"Unsupported image format: {image.mode}. Please upload an RGB or grayscale image.")
        raise ValueError(f"Unsupported image format: {image.mode}")
    return image


# Simplified preprocessing without training augmentations
def preprocess_image(image):
    # Check and handle image format
    image = check_image_format(image)

    transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=3),
        transforms.Resize((224, 224), antialias=True),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    image = transform(image).unsqueeze(0)  # Add batch dimension
    return image


# Grad-CAM Implementation
def apply_gradcam(model, image, target_layer):
    def forward_hook(module, input, output):
        nonlocal feature_maps
        feature_maps = output

    def backward_hook(module, grad_input, grad_output):
        nonlocal gradients
        gradients = grad_output[0]

    feature_maps = None
    gradients = None

    # Register hooks
    handle_forward = target_layer.register_forward_hook(forward_hook)
    if hasattr(target_layer, 'register_full_backward_hook'):
        handle_backward = target_layer.register_full_backward_hook(backward_hook)
    else:
        handle_backward = target_layer.register_backward_hook(backward_hook)

    # Forward pass
    output = model(image)
    target_class = torch.argmax(output).item()
    class_score = output[0, target_class]

    # Backward pass
    model.zero_grad()
    class_score.backward()

    # Compute Grad-CAM
    weights = torch.mean(gradients, dim=(2, 3), keepdim=True)
    cam = torch.sum(weights * feature_maps, dim=1).squeeze().detach().cpu().numpy()
    cam = np.maximum(cam, 0)  # ReLU
    cam = cv2.resize(cam, (224, 224))
    cam = cam - np.min(cam)
    cam = cam / np.max(cam)

    # Remove hooks
    handle_forward.remove()
    handle_backward.remove()

    return cam, target_class, output


# Model loading
@st.cache_resource  # Cache the model to avoid reloading
def load_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CVMConvNeXt(num_classes=6)

    # Get model path from environment variable or use default path resolved relative to this file's folder
    default_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models', 'best_model_Fine-tuning (Convnextv2).pth'))
    model_path = os.getenv('CVM_MODEL_PATH', default_path)

    if not os.path.exists(model_path):
        st.warning(f"Model weights file not found at '{model_path}'. Running in DEMO/MOCK mode with randomly initialized weights.")
        st.info("To run with trained weights, please download the weights (.pth file) and place them inside the 'models' directory.")
    else:
        try:
            model.load_state_dict(torch.load(model_path, map_location=device))
            st.success(f"Successfully loaded trained weights from: {model_path}")
        except Exception as e:
            st.error(f"Failed to load weights: {e}. Falling back to randomly initialized weights.")
            
    model.to(device)
    model.eval()
    return model


# Prediction function
def predict(model, image):
    with torch.no_grad():
        outputs = model(image)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)
        predicted_class = torch.argmax(outputs, dim=1).item()
        all_confidences = probabilities[0].tolist()
    return predicted_class + 1, all_confidences  # Return all probabilities


# Define class descriptions
class_descriptions = {
    1: "CS1: Initial stage of cervical vertebral maturation",
    2: "CS2: Ascending acceleration of growth",
    3: "CS3: Peak of growth velocity",
    4: "CS4: Initial deceleration of growth velocity",
    5: "CS5: Maturation stage nearing completion",
    6: "CS6: Growth velocity completed"
}

# Streamlit UI
st.set_page_config(page_title="CVM Classification", layout="wide")

st.title("Automatic CVM Classification with AI")

st.markdown("""
This application uses artificial intelligence to classify Cervical Vertebral Maturation (CVM) stages from X-ray images.
Please upload an X-ray image showing the cervical vertebrae region.
""")

uploaded_file = st.file_uploader("Choose an X-ray image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Display the uploaded image
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Original Image")
        image = Image.open(uploaded_file)
        st.image(image, use_column_width=True)

    # Process the image and make prediction
    try:
        model = load_model()
        processed_image = preprocess_image(image)
        cam, predicted_class, output = apply_gradcam(model, processed_image, model.convnext.stages[-1].blocks[-1])

        probabilities = torch.nn.functional.softmax(output, dim=1).squeeze().tolist()

        # Grad-CAM heatmap
        with col2:
            st.subheader("Grad-CAM Heatmap")
            plt.figure(figsize=(5, 5))
            plt.imshow(cam, cmap='jet')
            plt.axis('off')
            st.pyplot(plt)

        # Combined image with heatmap
        with col3:
            st.subheader("Combined View")
            # Convert to RGB first if needed
            image_rgb = image.convert('RGB')
            original = np.array(image_rgb.resize((224, 224))) / 255.0
            # Now original will always be (224,224,3) shape

            heatmap = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
            heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB) / 255.0
            combined = 0.5 * original + 0.5 * heatmap
            plt.figure(figsize=(5, 5))
            plt.imshow(combined)
            plt.axis('off')
            st.pyplot(plt)

        # Prediction result
        st.markdown(f"""
        **Predicted Stage:** CS{predicted_class + 1}  
        **Description:**  
        {class_descriptions[predicted_class + 1]}
        """)

        # Show confidence scores for all classes
        st.subheader("Confidence Scores for All Classes")
        for i, conf in enumerate(probabilities):
            st.markdown(f"**CS{i + 1}**")
            st.progress(conf)
            st.text(f"{conf * 100:.2f}%")

    except Exception as e:
        st.error(f"An error occurred during processing: {str(e)}")

# Add information about the classes
with st.expander("View CVM Stage Descriptions"):
    for class_num, description in class_descriptions.items():
        st.markdown(f"**{description}**")
