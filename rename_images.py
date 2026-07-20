import os
import glob
import shutil
import re

def renumber_and_import(source_dir, target_dir="images"):
    """
    Scans source_dir for new image files and copies them into target_dir
    renumbered sequentially starting after the current highest numbered image (e.g. 401.jpg, 402.jpg...).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(script_dir, target_dir)
    
    if not os.path.exists(target_path):
        os.makedirs(target_path)
        
    # Determine current max index in target folder
    existing_files = os.listdir(target_path)
    max_idx = 0
    for f in existing_files:
        match = re.match(r'^(\d+)\.(jpg|jpeg|png|bmp)$', f, re.IGNORECASE)
        if match:
            idx = int(match.group(1))
            if idx > max_idx:
                max_idx = idx
                
    print(f"Current highest image index in '{target_dir}': {max_idx:03d}.jpg")
    
    # Scan source directory
    valid_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    source_files = [
        os.path.join(source_dir, f) for f in os.listdir(source_dir)
        if f.lower().endswith(valid_exts) and not f.startswith('.')
    ]
    
    if not source_files:
        print(f"No new image files found in '{source_dir}'.")
        return
        
    source_files.sort()
    start_idx = max_idx + 1
    imported_count = 0
    
    print(f"Found {len(source_files)} image(s) to import from '{source_dir}'...")
    
    for i, src_file in enumerate(source_files):
        new_num = start_idx + i
        new_filename = f"{new_num:03d}.jpg"
        dest_file = os.path.join(target_path, new_filename)
        
        shutil.copy2(src_file, dest_file)
        imported_count += 1
        print(f"  [+] Imported: {os.path.basename(src_file)} -> {new_filename}")
        
    print(f"\nSuccessfully imported and renumbered {imported_count} new images!")
    print(f"Dataset size expanded from {max_idx} to {max_idx + imported_count} images.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        source_folder = sys.argv[1]
    else:
        source_folder = input("Enter path to the folder containing new cephalograms: ").strip()
        
    if os.path.exists(source_folder):
        renumber_and_import(source_folder)
    else:
        print(f"Error: Folder '{source_folder}' does not exist.")
