import kagglehub
import os

print("Downloading WLASL dataset...")
try:
    # Download latest version
    path = kagglehub.dataset_download("risangbaskoro/wlasl-processed")
    print(f"Dataset downloaded to: {path}")
    
    # List contents to verify
    print("Contents of downloaded directory:")
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files[:5]: # Show first 5 files only to avoid clutter
            print(f"{subindent}{f}")
        if len(files) > 5:
            print(f"{subindent}... ({len(files)-5} more files)")

except Exception as e:
    print(f"Error downloading dataset: {e}")
