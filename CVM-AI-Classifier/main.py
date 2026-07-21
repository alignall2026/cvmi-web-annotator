import os
from pathlib import Path


def main():
    print("Cervical Vertebral Maturation (CVM) Model Launcher")
    print("\nThis launcher helps you run different CVM classification models.")

    # Define available apps with their filenames and required model paths
    apps = {
        "1": {
            "name": "cvm_convnext.py",
            "model_file": "best_model_Fine-tuning-3(ConvNeXt-small).pth",
            "description": "ConvNeXt Model for CVM Classification"
        },
        "2": {
            "name": "cvm_convnext2.py",
            "model_file": "best_model_Fine-tuning (Convnextv2).pth",
            "description": "ConvNeXt V2 Model for CVM Classification"
        },
        "3": {
            "name": "cvm_densenet121.py",
            "model_file": "best_model_Fine-tuning (Densenet121_V4).pth",
            "description": "DenseNet121 Model for CVM Classification"
        },
        "4": {
            "name": "efficientnetb1v2.py",
            "model_file": "best_model_Fine-tuning.pth",
            "description": "EfficientNet B1 Model for CVM Classification"
        },
        "5": {
            "name": "mobilenetv2.py",
            "model_file": "best_model_Fine-tuning (mobilenetv2).pth",
            "description": "MobileNetV2 Model for CVM Classification"
        },
        "6": {
            "name": "resnet18.py",
            "model_file": "best_model_Fine-tuning-2(resnet18).pth",
            "description": "resnet18 Model for CVM Classification"
        }
    }

    # Create necessary directory structure if it doesn't exist
    project_root = Path(__file__).parent
    streamlit_dir = project_root / "streamlit_apps"
    models_dir = project_root / "models"

    # Display available options
    print("\nAvailable Models:")
    for key, app_info in apps.items():
        print(f"{key}. {app_info['description']}")

    while True:
        choice = input("\nEnter the number of the model you want to run (or 'q' to quit): ")

        if choice.lower() == 'q':
            print("Exiting launcher...")
            break

        if choice in apps:
            app_info = apps[choice]
            app_path = streamlit_dir / app_info['name']
            model_path = models_dir / app_info['model_file']

            # Verify paths exist
            if not app_path.exists():
                print(f"\nError: Could not find application file at {app_path}")
                print("Please ensure the file exists in the streamlit_apps directory.")
                continue

            if not model_path.exists():
                print(f"\nWarning: Model file not found at {model_path}")
                print("The application might not work correctly without the model file.")
                user_continue = input("Do you want to continue anyway? (y/n): ")
                if user_continue.lower() != 'y':
                    continue

            # Launch the Streamlit app
            print(f"\nLaunching {app_info['description']}...")
            command = f"streamlit run {app_path.as_posix()}"
            print(f"Command: {command}")

            # Set environment variable for model path
            os.environ['CVM_MODEL_PATH'] = str(model_path)
            os.system(command)
            break
        else:
            print("\nInvalid choice! Please enter a number between 1 and 5, or 'q' to quit.")


if __name__ == "__main__":
    main()
