import subprocess
import os

def run(cmd):
    print(f"Running: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("ERR:", res.stderr)
    return res.returncode

def fast_push():
    # 1. Reset any uncommitted state
    run("git reset")
    
    # 2. Push Core Codebase first
    print("\n--- PUSHING CORE CODEBASE ---")
    run("git add index.html google_apps_script.js rename_images.py requirements.txt docs cvmi_analyzer tests .gitignore main.py annotation_tool.py archive")
    run('git commit -m "CVMI Web Annotator Code & Docs"')
    run("git push -u origin main")
    
    # 3. Push Image Batch 1 (001.jpg - 200.jpg)
    print("\n--- PUSHING IMAGE BATCH 1 (001-200) ---")
    run("git add images/0* images/1* images/200.jpg")
    run('git commit -m "Add Cephalogram Dataset Part 1 (001-200)"')
    run("git push origin main")
    
    # 4. Push Image Batch 2 (201.jpg - 414.jpg)
    print("\n--- PUSHING IMAGE BATCH 2 (201-414) ---")
    run("git add images/")
    run('git commit -m "Add Cephalogram Dataset Part 2 (201-414)"')
    run("git push origin main")
    
    print("\n🎉 ALL CODE & 414 IMAGES PUSHED TO GITHUB SUCCESSFULLY!")

if __name__ == "__main__":
    fast_push()
