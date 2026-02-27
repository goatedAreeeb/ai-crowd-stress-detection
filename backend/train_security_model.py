"""
=================================================================
 Suspicious Object Detection — YOLOv8m Training Script
=================================================================
 This script trains a YOLOv8m model on the security dataset
 to detect 12 classes of suspicious/dangerous objects.

 BEFORE RUNNING:
   1. Populate security_dataset/images/ and labels/ with your
      annotated data (see README_DATASET.md).
   2. Ensure data.yaml is correctly configured.
   3. Run from the backend directory:
      python train_security_model.py

 REQUIREMENTS:
   pip install ultralytics opencv-python torch
=================================================================
"""

import os
import torch
from ultralytics import YOLO


def get_device():
    """Auto-detect the best available compute device."""
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        print(f"  🟢 GPU detected: {gpu_name}")
        try:
            free_mem, total_mem = torch.cuda.mem_get_info(0)
            print(f"     VRAM: {total_mem / 1e9:.1f} GB")
        except Exception:
            print("     VRAM: (unable to query)")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        print("  🟢 Apple MPS (Metal) detected.")
    else:
        device = "cpu"
        print("  🟡 No GPU found. Training on CPU (will be very slow).")
    return device


def train():
    print("=" * 60)
    print(" SUSPICIOUS OBJECT DETECTION — TRAINING")
    print("=" * 60)

    # -----------------------------------------------------------
    # 1. CONFIGURATION
    # -----------------------------------------------------------
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_YAML = os.path.join(BASE_DIR, "security_dataset", "data.yaml")
    BASE_MODEL = "yolov8m.pt"   # Medium model — good balance of speed & accuracy
    EPOCHS = 100                # 100 epochs for 300-400 images/class
    IMG_SIZE = 640              # Standard YOLO input resolution
    BATCH_SIZE = 8              # 8 for 6GB VRAM GPUs (RTX 4050), use 16 for 8GB+
    WORKERS = 4                 # Dataloader threads

    # -----------------------------------------------------------
    # 2. DEVICE SELECTION
    # -----------------------------------------------------------
    print("\n[1/3] Detecting compute device...")
    device = get_device()

    # -----------------------------------------------------------
    # 3. VERIFY DATASET EXISTS
    # -----------------------------------------------------------
    print("\n[2/3] Checking dataset...")

    train_imgs = os.path.join(BASE_DIR, "security_dataset", "images", "train")
    val_imgs = os.path.join(BASE_DIR, "security_dataset", "images", "val")

    train_count = len([f for f in os.listdir(train_imgs) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]) if os.path.exists(train_imgs) else 0
    val_count = len([f for f in os.listdir(val_imgs) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]) if os.path.exists(val_imgs) else 0

    print(f"  Training images found:   {train_count}")
    print(f"  Validation images found: {val_count}")

    if train_count < 10:
        print("\n  ⚠️  WARNING: Very few training images detected!")
        print("     You need ~3,600-4,800 images (300-400 per class) for good results.")
        print("     See README_DATASET.md for guidance.")
        print("     The training will still start, but results will be poor.\n")

    # -----------------------------------------------------------
    # 4. LOAD & TRAIN
    # -----------------------------------------------------------
    print(f"\n[3/3] Starting training...")
    print(f"  Base model:    {BASE_MODEL}")
    print(f"  Epochs:        {EPOCHS}")
    print(f"  Image size:    {IMG_SIZE}")
    print(f"  Batch size:    {BATCH_SIZE}")
    print(f"  Device:        {device}")
    print(f"  Data config:   {DATA_YAML}")
    print("-" * 60)

    model = YOLO(BASE_MODEL)

    results = model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        device=device,
        workers=WORKERS,
        project="runs/detect",
        name="train",
        exist_ok=True,

        # ============================================
        # KEY AUGMENTATIONS FOR SMALL DATASETS & VIDEO
        # ============================================
        # Mosaic: Combines 4 random images into a single training tile.
        mosaic=1.0,            # Probability of mosaic (1.0 = always on)

        # Mixup: Blends two images together with transparency.
        mixup=0.2,             # Slightly increased for better robustness

        # Video/Motion Robustness Augmentations
        bgr=0.2,               # Adds blur (simulates motion/camera blur) 20% of the time
        degrees=10.0,          # Random rotation ±10 deg (weapons held at weird angles)
        shear=2.0,             # Distorts weapon shapes (helps with perspective changes)
        
        # Standard Data Augmentations
        flipud=0.1,            # Vertical flip (occasional)
        fliplr=0.5,            # Horizontal flip (common)
        scale=0.5,             # Random scaling ±50%
        translate=0.1,         # Random translate ±10%
        hsv_h=0.015,           # Hue shift
        hsv_s=0.7,             # Saturation shift
        hsv_v=0.4,             # Value/brightness shift

        # Optimizer & scheduler
        optimizer="auto",      # auto selects SGD or AdamW
        lr0=0.01,              # Initial learning rate
        lrf=0.01,              # Final learning rate factor
        warmup_epochs=3,       # Warmup for stable start

        # Output
        save=True,
        save_period=10,        # Save checkpoint every 10 epochs
        verbose=True,
    )

    # -----------------------------------------------------------
    # 5. RESULTS
    # -----------------------------------------------------------
    best_path = os.path.join("runs", "detect", "train", "weights", "best.pt")
    print("\n" + "=" * 60)
    print(" TRAINING COMPLETE!")
    print("=" * 60)
    print(f"  ✅ Best model saved to: {best_path}")
    print(f"  📊 Results & metrics:   runs/detect/train/")
    print(f"\n  Next step: Copy best.pt and use it in security_pipeline.py")
    print("=" * 60)

    return results


if __name__ == "__main__":
    train()
