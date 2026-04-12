import os
import sys
import ctypes

def check_dll():
    dll_path = os.path.join(os.getcwd(), "venv", "Lib", "site-packages", "torch", "lib", "torch_python.dll")
    print(f"Checking DLL: {dll_path}")
    print(f"Exists: {os.path.exists(dll_path)}")
    
    # Try to load it directly
    try:
        # Add torch\lib to path manually
        lib_dir = os.path.join(os.getcwd(), "venv", "Lib", "site-packages", "torch", "lib")
        os.add_dll_directory(lib_dir)
        print(f"Added {lib_dir} to DLL directory.")
        
        ctypes.WinDLL(dll_path)
        print("Successfully loaded DLL via WinDLL!")
    except Exception as e:
        print(f"WinDLL load failed: {e}")

if __name__ == "__main__":
    check_dll()
