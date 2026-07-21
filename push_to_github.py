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
    run("git add images/2* images/3* images/40* images/410.jpg images/411.jpg images/412.jpg images/413.jpg images/414.jpg")
    run('git commit -m "Add Cephalogram Dataset Part 2 (201-414)"')
    run("git push origin main")

    # 5. Push Image Batch 3 (415.jpg - 445.jpg) & Archive
    print("\n--- PUSHING IMAGE BATCH 3 (415-445) & ARCHIVE ---")
    run("git add images/ archive/")
    run('git commit -m "Add Cephalogram Dataset Part 3 (415-445)"')
    run("git push origin main")
    
    print("\nSUCCESS: ALL CODE & 445 IMAGES PUSHED TO GITHUB!")

if __name__ == "__main__":
    fast_push()
