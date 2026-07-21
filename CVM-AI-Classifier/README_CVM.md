# CVM-AI-Classifier Documentation & User Guide

This guide describes how to run and use the **CVM-AI-Classifier** Streamlit web interface to classify Cervical Vertebrae Maturation (CVM) stages (CS1–CS6) using deep learning, and how to interpret explainability heatmaps.

---

## 🚀 Step-by-Step Setup & Run Guide

### 1. Verification of Environment
Before running, confirm your Python version:
```powershell
python --version
# Expected Output: Python 3.8.x or higher (e.g. Python 3.14.6)
```

### 2. Cloned Repository structure
Ensure you are inside the `CVM-AI-Classifier` project directory:
```powershell
cd CVM-AI-Classifier
```

### 3. Dependencies Installation
Install required libraries (Pillow, timm, torch, streamlit, matplotlib, opencv-python):
```powershell
pip install -r requirements.txt
```

### 4. Running the Web Interface
To launch the Streamlit server bypass local shell `PATH` executable limitations by running the module directly:
```powershell
python -m streamlit run streamlit_apps/cvm_convnext2.py --server.port 5000
```

**Expected Terminal Console Output:**
```text
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:5000
  Network URL: http://10.24.21.116:5000
```
Open [http://localhost:5000](http://localhost:5000) in your web browser.

---

## 📂 Web Interface Workflow

1. **Upload Cephalometric Image**: 
   - Click the **"Browse files"** button or drag and drop a lateral cephalometric X-ray (`.jpg`, `.jpeg`, or `.png`).
2. **AI Analysis Processing**:
   - The system automatically resizes the image to 224x224 and feeds it to the ConvNeXt model.
   - It runs backward feature hooks to construct the Grad-CAM maps.
3. **Review Results Panels**:
   - **Original Image**: Displays the raw X-ray input.
   - **Grad-CAM Heatmap**: Displays focus grids highlighting the diagnostic features.
   - **Combined View**: Overlays the heatmap transparency directly onto the X-ray structure.
   - **Maturation Verdict**: Displays the predicted stage (CS1–CS6) and its clinical definition.
   - **Confidence Bars**: Displays the percentage confidence across all 6 stages.

---

## 🔍 How to Interpret the Output

### A. Cervical Vertebral Maturation Stages (CS1 - CS6)
*   **CS1**: Initial stage. Peak mandibular growth is 2 years away.
*   **CS2**: Acceleration. Peak mandibular growth is 1 year away.
*   **CS3**: Growth spurt peak. Peak mandibular growth occurs during this stage.
*   **CS4**: Deceleration. Peak growth ended 1 year ago.
*   **CS5**: Maturation nearing completion. Peak growth ended 2 years ago.
*   **CS6**: Growth completed. Skeletal maturity reached.

### B. Confidence Scores
- The model outputs a probability distribution across all six classes (represented by progressing loading bars in the UI).
- A higher confidence score (e.g. `> 75.0%`) indicates a strong diagnostic consensus. If scores are split between two adjacent stages (e.g. `35.0% CS3` and `40.0% CS4`), the patient is transitioning between stages.

### C. Grad-CAM Heatmaps (Explainability)
- **What they represent**: Grad-CAM (Gradient-weighted Class Activation Mapping) calculates the gradients of the target class score with respect to the final convolutional feature maps.
- **How to read them**:
  - **Red/Orange Regions**: Areas of maximum focus. The AI model's decision was heavily influenced by these regions. In a correct CVM diagnosis, the red peak **MUST** overlay the bodies and inferior borders of the **C2, C3, and C4 vertebrae**.
  - **Blue/Green Regions**: Areas of low/neutral focus.
  - **Clinical Audit**: If the red focus area is located on the teeth, skull base, or background instead of the vertebrae, the AI prediction is likely compromised, and the clinician should override the verdict.

---

## 🛠️ Troubleshooting & Setup Diagnoses

### 1. `streamlit : The term 'streamlit' is not recognized...`
*   **Cause**: The pip script path is not registered in your Windows Environment `PATH` variable.
*   **Fix**: Always launch Streamlit by passing it as a module command:
    ```powershell
    python -m streamlit run streamlit_apps/cvm_convnext2.py --server.port 5000
    ```

### 2. Model Weight Warnings (`Model weights file not found...`)
*   **Cause**: The pre-trained weights file (`best_model_Fine-tuning (Convnextv2).pth`) is missing from the `models/` directory due to GitHub repository file size limits.
*   **Fix**:
    1. We have added a safe fallback inside `cvm_convnext2.py` so the app doesn't crash. It runs in **Demo Mode** using uninitialized random weights, outputting mock predictions.
    2. To run with actual clinical weights: Download the weights `.pth` file from the [link in models/README.md](https://drive.google.com/file/d/1fnHZKQP_qeRWQiBYeO-E3fWasgTCCv7M/view?usp=drive_link) and paste it inside the `CVM-AI-Classifier/models` directory.
