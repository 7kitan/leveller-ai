import os
import urllib.request
import zipfile
import shutil

# Poppler for Windows (oschwartz10612)
POPPLER_URL = "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
TARGET_DIR = os.path.join(os.getcwd(), "bin", "poppler")
ZIP_PATH = "poppler.zip"

def setup_poppler():
    if not os.path.exists("bin"):
        os.makedirs("bin")
    
    if os.path.exists(TARGET_DIR):
        print(f"Poppler already exists in {TARGET_DIR}")
        return

    print(f"Downloading Poppler from {POPPLER_URL}...")
    try:
        urllib.request.urlretrieve(POPPLER_URL, ZIP_PATH)
        print("Download complete. Extracting...")
        
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall("bin/temp_poppler")
        
        # The zip usually contains a single folder like 'poppler-24.08.0'
        temp_dir = os.path.join("bin", "temp_poppler")
        subfolders = [f for f in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, f))]
        
        if subfolders:
            source = os.path.join(temp_dir, subfolders[0])
            shutil.move(source, TARGET_DIR)
            print(f"Poppler installed to {TARGET_DIR}")
        else:
            print("Failed to find extracted folder.")
            
    except Exception as e:
        print(f"Error during Poppler setup: {e}")
    finally:
        if os.path.exists(ZIP_PATH):
            os.remove(ZIP_PATH)
        if os.path.exists("bin/temp_poppler"):
            shutil.rmtree("bin/temp_poppler")

if __name__ == "__main__":
    setup_poppler()
