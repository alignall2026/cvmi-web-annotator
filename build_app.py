import os
import sys
import subprocess

def run_build():
    print("CVMI Analyzer Pro - Installer Build Pipeline")
    print("---------------------------------------------")
    
    # 1. Verify PyInstaller installation
    try:
        import PyInstaller
        print("Found PyInstaller module.")
    except ImportError:
        print("PyInstaller is not installed in the current environment.")
        print("To install, run: pip install pyinstaller")
        sys.exit(1)
        
    # 2. Build configuration command
    entry_point = "main.py"
    app_name = "CVMI_Analyzer_Pro"
    
    cmd = [
        "pyinstaller",
        "--noconsole",           # Do not show command prompt window on boot
        "--clean",               # Clean build cache
        f"--name={app_name}",    # Executable output name
        "--onefile",             # Package into a single file
        # We add imports that PyInstaller might miss due to dynamic mapping
        "--hidden-import=pydicom.encoders.gdcm",
        "--hidden-import=pydicom.encoders.pylibjpeg",
        "--hidden-import=cryptography.fernet",
        "--hidden-import=openpyxl",
        "--hidden-import=pandas",
        "--hidden-import=torch",
        "--hidden-import=torchvision",
        "--hidden-import=scipy.stats",
        entry_point
    ]
    
    print(f"Running build command: {' '.join(cmd)}")
    
    try:
        # Run PyInstaller shell command
        res = subprocess.run(cmd, check=True)
        if res.returncode == 0:
            print("---------------------------------------------")
            print("BUILD COMPLETED SUCCESSFUL!")
            print(f"Executable saved to: {os.path.abspath(os.path.join('dist', app_name + '.exe'))}")
    except subprocess.CalledProcessError as e:
        print(f"Error during compilation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_build()
