# CVMI Analyzer Pro - User & Clinician Manual

Welcome to **CVMI Analyzer Pro**, a professional dental desktop workstation for cervical vertebral maturation index (CVMI) assessments in orthodontic research and clinical diagnosis.

---

## 1. Clinical Background: CVMI Stages (CS1 - CS6)

The cervical vertebral maturation index evaluates somatic maturity using lateral cephalometric radiographs. CVMI Analyzer Pro measures the morphology of the C2, C3, and C4 vertebrae using 5 landmarks per body:

*   **SA**: Superior-Anterior corner
*   **SP**: Superior-Posterior corner
*   **IA**: Inferior-Anterior corner
*   **IP**: Inferior-Posterior corner
*   **IM**: Inferior-Middle (the deepest point of the inferior border, used for concavity evaluation)

### Stages Classification Key
1.  **CS1 (Stage 1 - Maturation Initiation)**:
    *   Inferior borders of C2, C3, C4 are flat.
    *   C3 and C4 vertebral bodies are wedge-shaped (anterior height is significantly shorter than posterior height, $AH/PH \le 0.85$).
2.  **CS2 (Stage 2 - Maturation Acceleration)**:
    *   Inferior border of C2 exhibits concavity (depth $\ge 1.0\text{ mm}$).
    *   C3 and C4 remain rectangular horizontal.
3.  **CS3 (Stage 3 - Maturation Peak)**:
    *   Inferior borders of C2 and C3 exhibit concavity.
    *   C3 and C4 remain rectangular horizontal ($AR \ge 1.15$).
4.  **CS4 (Stage 4 - Maturation Deceleration)**:
    *   Inferior borders of C2, C3, and C4 exhibit concavity.
    *   C3 and C4 remain rectangular horizontal.
5.  **CS5 (Stage 5 - Maturation Completion)**:
    *   Inferior borders of C2, C3, and C4 exhibit concavity.
    *   C3 and C4 are square-shaped ($0.95 \le AR < 1.15$).
6.  **CS6 (Stage 6 - Late Maturation)**:
    *   Inferior borders of C2, C3, and C4 exhibit concavity.
    *   C3 and C4 are rectangular vertical ($AR < 0.95$, height exceeds width).

---

## 2. Quick-Start Guide

### Step 1: Security Log In
1.  Launch the application.
2.  Authenticate using default credentials:
    *   **Username**: `admin`
    *   **Password**: `admin123`
3.  To register new clinical operators, click **Register New**, enter the username, select the role (Clinician or Administrator), and specify a password.

### Step 2: Patient Registration
1.  On the left panel, click **Add**.
2.  Enter the Patient ID, First/Last Name, Date of Birth, Gender, and contact details. Click **Save Patient**.
3.  Double-click the patient name in the registry sidebar list to load their profile.

### Step 3: Importing Cephalograms
1.  With a patient loaded, go to the Ribbon toolbar's **Home** tab.
2.  Click **Import Image**.
3.  Select any standard image format (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`) or medical `.dcm`/`.dicom` file. The image will copy into the local app folder for offline availability.

### Step 4: Scale Calibration
1.  Switch to the **Image Tools** tab on the Ribbon.
2.  Click **Calibrate**.
3.  Click 2 points on the image canvas corresponding to a known physical measurement (e.g. ruler markings on the cephalostat).
4.  In the prompt dialog, enter the distance in millimeters (e.g. `10.0`). The system automatically configures the pixels-per-millimeter scale.

---

## 3. Radiographic Analysis Modes

### Manual Assessment
1.  Go to the Ribbon's **Analysis** tab.
2.  Click **Manual Mode**. Five colored markers will overlay on each of C2, C3, and C4.
    *   **Red markers**: C2
    *   **Green markers**: C3
    *   **Blue markers**: C4
3.  Drag individual markers to align with the anatomical boundaries of the vertebrae.
4.  The system calculates and updates all heights, widths, aspect ratios, concavities, and suggested stages in the right-side table in real-time.
5.  Optionally add clinical comments and click **Save Assessment**.

### AI-Assisted Assessment
1.  On the **Analysis** tab, click **AI Detect**.
2.  The neural network detects vertebrae boundaries and places the landmark markers.
3.  The classifier runs inference to predict the maturation stage and outputs a confidence score (e.g. `CS3 (92%)`).
4.  Grad-CAM activation maps overlay on the image, displaying a heatmap of the structures that influenced the AI model's decision.
5.  If adjustments are needed, click and drag any landmark node to refine coordinates manually.

---

## 4. Research Module & Statistics

Go to the Ribbon's **Research** tab:
*   **Show Statistics**: Opens the research window.
*   **Inter-Examiner Comparison**: Select two examiners from the dropdown lists. Click **Compute Reliability** to calculate:
    *   **Cohen's Kappa**: Overall stage agreement.
    *   **ICC (2,1)**: Reliability index of continuous landmark ratios (aspect ratio of C3).
*   **Fleiss' Kappa**: Evaluates agreement between multiple examiners (3+) assessing the same radiographs.
*   **Data Exports**: Click **Export CSV** or **Export Excel** to save the complete research spreadsheet database locally.

---

## 5. Administrative Features

### AI Retraining Pipeline
Administrators can retrain models on new datasets:
1.  Prepare a folder containing 6 subfolders: `CS1`, `CS2`, `CS3`, `CS4`, `CS5`, `CS6`.
2.  On the **AI Training** tab, click **Training Panel**.
3.  Browse and select the folder, configure hyperparameters (epochs, learning rate), and click **Start Retraining**.
4.  The background thread executes training and graphs performance metrics (ROC curves, Confusion Matrices, Loss curves) inside the panel.

### Security Backups
*   **Backup DB**: Creates an archive copy of the patient database in `~/.cvmi_analyzer/backups/`.
*   **Restore DB**: Restores a selected database backup archive (Administrator only).
