# <div align="center">Tracker 🛰️📅</div>

<div align="center">

**English | [简体中文](README.md)**

</div>

<div align="center">


![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![License](https://img.shields.io/badge/License-MIT-orange)

**A Universal Temporal Annotation Tool: From Large-scale Remote Sensing to Standard Images**

</div>

**Tracker** is a high-performance, lightweight annotation tool designed to handle everything from **GB-level GeoTIFFs** to **standard small images (JPG/PNG)**.

It solves the memory overflow and lag issues often encountered with LabelImg/LabelMe when loading large geospatial data. Tracker is specifically designed for **"Fixed-Position, Attribute-Changing"** temporal events (e.g., construction progress, vegetation growth, surveillance). It utilizes a **"Draw Once, Sync Everywhere"** logic to significantly boost annotation efficiency.

---

## ✨ Key Features

### 🚀 High Performance & Compatibility
* **Large Image Support**: Uses intelligent dynamic downsampling and max-texture limits to smoothly load GB-level `.tif` images.
* **Universal Formats**: Fully supports `.tif`, `.tiff`, `.png`, `.jpg`, `.jpeg`.
* **Smart Sorting**: Built-in Regex engine automatically extracts dates from filenames (e.g., `2005-12-20`) to ensure strict chronological ordering.

### ⚡ Efficient Temporal Annotation
* **Batch Mode**: Draw a box once, drag the slider, and automatically populate the event across future N frames.
* **Discrete Append**: Supports adding non-continuous time segments to the same event ID (e.g., object appears in frames 1-3, then again in 8-10).
* **Sync Edit**: Modify the box size or position in *any* frame, and the update automatically syncs to *all* frames for that event (based on the fixed-region assumption).

### 🛠️ Precise Management
* **Dual-Level Description**: Requires both a **Category** (short tag) and a **Caption** (detailed description) to ensure dataset quality.
* **Timeline Fine-tuning**: Right-click menu supports "Set as Start", "Set as End", and "Remove Single Frame" with auto-fill logic.
* **Quality Control**: Built-in **"🚩 Mark Poor Quality"** button to tag blurry or occluded frames directly into the dataset.

---

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone [https://github.com/bxuanz/Tracker.git](https://github.com/bxuanz/Tracker.git)
cd Tracker
```

### 2. Create Environment (Recommended)
```bash
conda create -n tracker_env python=3.9
conda activate tracker_env
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Core deps: `PyQt6`, `numpy`, `rasterio`, `Pillow`)*

---

## 🏃‍♂️ User Guide

### 1. Launch & Load
```bash
python main.py
```
* Click **"Open Folder"** to select your image directory.
* The timeline navigation bar will generate automatically at the bottom.
* **Note**: The status bar displays real-time **Coordinates (X, Y)** and **Image Resolution**.

### 2. Annotation Workflow

#### A. Create New Event
1.  **Draw a box** on the image with Left Mouse Button.
2.  In the popup dialog:
    * Select **"Create New Event"**.
    * Fill in **Category** and **Caption** (Required).
    * Drag the slider to select the **End Frame**.
3.  Click OK to auto-generate continuous annotations.

#### B. Append Discrete Segments
*Scenario: Event exists in frames 1-5, disappears, and reappears in frame 10.*
1.  Jump to frame 10.
2.  Draw a box.
3.  In the popup dropdown, select **"ID x: [Existing Event Name]"**.
4.  Select the end frame for this new segment.
5.  Click OK. The event now covers `[1-5, 10-12]`.

#### C. Modify & Adjust
* **Resize/Move**: Click to select a box (turns solid with cyan handles). Drag handles to resize or drag inside to move. **Changes sync immediately to all frames.**
* **Quality Tag**: For low-quality images, toggle the **"🚩 Mark Poor Quality"** button at the top.

### 3. Timeline Management (Right-Click Menu)
Right-click an item in the event list:

| Menu Item | Description |
| :--- | :--- |
| **❌ Remove Box on Current Frame** | Deletes the box only on the current frame (for occlusion handling). |
| **⚡ Set Current as START** | Sets current frame as start. Auto-fills backwards if current is before old start; Trims if after. |
| **⚡ Set Current as END** | Sets current frame as end. Auto-fills gaps and deletes subsequent frames. |
| **🗑️ Delete Event Completely** | Permanently deletes the event and all its data. |

---

## ⌨️ Shortcuts

| Key | Function |
| :--- | :--- |
| `←` / `↑` | Previous Frame |
| `→` / `↓` | Next Frame |
| `LMB` (Left Click) | Draw / Select / Drag |
| `RMB` (Right Click) | Pan View |
| `Wheel` | Zoom In/Out |

---

## 📂 Output Format

Click "Save Data" to generate `annotations.json` in the image directory.

```json
{
    "1": {
        "category": "Construction",
        "caption": "Excavator digging on the northwest side of the runway",
        "box": [5000, 3000, 250, 250],  // [x, y, w, h] (Fixed Region)
        "frames": [
            {
                "filename": "2024-01-01.tif",
                "quality": "good"
            },
            {
                "filename": "2024-01-02.tif",
                "quality": "poor"  // Marked as poor quality
            }
        ]
    }
}
```

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📄 License

This project is open-sourced under the [MIT License](LICENSE).