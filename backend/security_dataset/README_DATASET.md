# 📦 Security Dataset — Collection Guide

## Overview

This dataset powers the **Suspicious Object Detection** model (YOLOv8m). It is designed to detect **12 classes** of potentially dangerous objects in real-time CCTV/camera feeds.

---

## Target Image Count

| Category | Classes | Images/Class | Subtotal |
|---|---|---|---|
| Firearms | `pistol`, `revolver`, `rifle` | 300–400 | 900–1,200 |
| Bladed Weapons | `kitchen_knife`, `dagger`, `machete`, `large_blade` | 300–400 | 1,200–1,600 |
| Blunt Weapons | `metal_rod`, `bat_or_club` | 300–400 | 600–800 |
| Suspicious Items | `unattended_backpack`, `suspicious_bag`, `large_unusual_object` | 300–400 | 900–1,200 |
| **Grand Total** | **12 classes** | | **3,600–4,800** |

> **Rule of thumb**: 300 images is the *absolute minimum* for a usable class. 400+ is the sweet spot. More is always better.

---

## Annotation Format

All labels must be in **YOLO format** (`.txt` files):

```
<class_id> <x_center> <y_center> <width> <height>
```

- All values are **normalized** (0.0 to 1.0) relative to image dimensions.
- One `.txt` file per image, same filename (e.g., `img_001.jpg` → `img_001.txt`).
- Use [Roboflow](https://roboflow.com), [CVAT](https://cvat.ai), or [LabelImg](https://github.com/HumanSignal/labelImg) for annotation.

---

## Train/Val Split

- **80% Training** → `images/train/` + `labels/train/`
- **20% Validation** → `images/val/` + `labels/val/`

---

## Where to Find Images

| Source | URL | Notes |
|---|---|---|
| Roboflow Universe | https://universe.roboflow.com | Search "weapon detection", "knife detection" |
| Open Images V7 | https://storage.googleapis.com/openimages | Filter for weapon/knife categories |
| Kaggle | https://kaggle.com | Search "weapon dataset", "suspicious object" |
| Google Images | Manual collection | Useful for rare classes like `large_unusual_object` |

> ⚠️ **Important**: Always verify the license of any dataset you download. For production systems, ensure you have rights to use the data.

---

## Data Augmentation (Built Into Training)

The training script already enables **mosaic** and **mixup** augmentation, which effectively multiply your dataset:

- **Mosaic**: Combines 4 images into 1, forcing the model to learn objects at different scales and positions.
- **Mixup**: Blends two images together, improving generalization.
- With 400 real images + these augmentations, the model effectively trains on **~1,500–2,000 unique variations per class**.

---

## Tips for Better Results

1. **Vary backgrounds**: Don't just photograph knives on a table. Include outdoor, indoor, dark, bright scenes.
2. **Vary distances**: Include close-up, medium, and far-away shots of each object.
3. **Include negatives**: Add ~200 images with NO objects (just backgrounds) to reduce false positives.
4. **CCTV angles**: If deploying on CCTV, collect images from similar overhead/angled perspectives.
