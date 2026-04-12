import torch
import sys

def debug_torchvision():
    print(f"Python version: {sys.version}")
    print(f"Torch version: {torch.__version__}")
    
    try:
        import torchvision
        print(f"Torchvision version: {torchvision.__version__}")
        
        # Check if C++ ops are registered
        has_nms = hasattr(torch.ops.torchvision, "nms")
        print(f"torchvision::nms registered in torch.ops: {has_nms}")
        
        # Try to import ops explicitly
        try:
            from torchvision import ops
            print("Successfully imported torchvision.ops")
        except Exception as e:
            print(f"Failed to import torchvision.ops: {e}")
            
    except ImportError as e:
        print(f"Failed to import torchvision: {e}")
    except Exception as e:
        print(f"Unexpected error during torchvision debug: {e}")

if __name__ == "__main__":
    debug_torchvision()
