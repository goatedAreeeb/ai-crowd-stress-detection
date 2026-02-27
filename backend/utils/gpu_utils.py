"""
GPU Utility — Auto-detect CUDA and configure for RTX 4050.
"""
import torch


def get_device() -> str:
    """Return best available device string."""
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def setup_gpu():
    """Configure CUDA for maximum throughput on RTX 4050."""
    device = get_device()
    if device == "cuda":
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        print(f"[GPU] {gpu_name} | {vram:.1f} GB VRAM | CUDA {torch.version.cuda}")
        print("[GPU] cuDNN benchmark enabled, TF32 enabled")
    else:
        print("[GPU] No CUDA GPU found — running on CPU")
    return device


def optimize_model(model, device: str):
    """Move model to device, fuse layers, enable half precision if CUDA."""
    model.to(device)
    model.fuse()
    if device == "cuda":
        model.half()
        print(f"[GPU] Model moved to CUDA with FP16 half precision")
    return model
