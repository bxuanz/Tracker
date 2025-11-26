<div align="center">
  <img src="./assets/icon.png" alt="tracker-icon" height="100"/>
</div>

<div align="center">

**English | [简体中文](README.md)**

</div>

<div align="center">

![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![Status](https://img.shields.io/badge/Status-Stable-blue)
![License](https://img.shields.io/badge/License-MIT-orange)

**A Universal Temporal Annotation Tool: From Large-scale Remote Sensing to Standard Images**

</div>

<br/>

**Tracker** is a high-performance, lightweight annotation tool designed to handle everything from **GB-level GeoTIFFs** to **standard small images (JPG/PNG)**.

It solves the memory overflow and lag issues often encountered with LabelImg/LabelMe when loading large geospatial data. Tracker is specifically designed for **"Fixed-Position, Attribute-Changing"** temporal events (e.g., construction progress, vegetation growth, surveillance). It utilizes a **"Draw Once, Sync Everywhere"** logic to significantly boost annotation efficiency.



---

## ✨ Key Features

### 🚀 High Performance
* **Large Image Support**: Uses dynamic downsampling to smoothly load **GB-level** `.tif` / `.tiff` images.
* **Universal Formats**: Fully supports `.png`, `.jpg`, `.jpeg`, and geospatial rasters.
* **Smart Sorting**: Built-in Regex engine automatically extracts dates from filenames (e.g., `2023-10-01`) to ensure strict chronological ordering.

### ⚡ Efficient Temporal Workflow
* **Batch Mode**: Draw a box once, drag the slider, and automatically populate the event across future N frames.
* **Discrete Append**: Supports adding non-continuous time segments to the same event ID (e.g., object appears in frames 1-3, then again in 8-10).
* **Sync Edit**: Modify the box position in *any* frame, and the update automatically syncs to *all* frames for that event (based on the fixed-region assumption).

### 🛡️ Dual-Level Quality Control
* **Image-Level**: Mark an entire image as "Poor" (e.g., fully covered by clouds/fog).
* **Event-Level (NEW)**: Evaluate the quality of specific bounding boxes (Good/Bad). If marked as "Bad", you can select specific reasons (e.g., `Occluded`, `Wrong Label`, `Loose Box`), which are saved directly to the JSON.

---

## 🛠️ Installation

```bash
# 1. Clone Repository
git clone https://github.com/your-repo/Tracker.git
cd Tracker

# 2. Install Dependencies (Conda recommended)
pip install -r requirements.txt
# Core deps: PyQt6, numpy, rasterio, Pillow
```

---

## 🏃‍♂️ User Guide

### 1. Launch & Load

Run `main.py` to start:

```bash
python main.py
```

* Click **"📂 Open Root Folder"** on the top right to select your image directory.
* The timeline navigation bar will generate automatically at the bottom.

### 2. Annotation Workflow

#### A. Create Annotation
1.  **Draw Box**: Drag the Left Mouse Button on the canvas.
2.  **Fill Info**: A dialog appears upon release:
    * **Group/Category**: Select or type a new category.
    * **Caption**: Enter a detailed description.
    * **End Frame**: Drag the slider to set how long this event lasts.
3.  **Confirm**: Click OK to auto-generate continuous annotations.

#### B. Quality Check (QC) - ✨ New in V13
When you find an imperfect annotation (e.g., object blocked by trees, or box not tight enough) but don't want to delete it:

1.  **Select Event**: Click the event in the right-side list (e.g., `ID 1: Vehicle`).
2.  **Check QC Panel**: Look for the **"Event Quality"** section at the bottom right.
3.  **Mark as Bad**:
    * Select **"❌ Bad"**.
    * **Select Reason**: Choose from the dropdown (e.g., `Occluded`, `Loose Box`).
4.  **Visual Feedback**: The item in the list will turn RED with a `❌` mark.

#### C. Append Segment
*Scenario: Object disappears for a few days and reappears.*
1.  Jump to the frame where it reappears.
2.  Draw a box.
3.  In the dropdown, select **"ID x: [Existing Event Name]"**.
4.  Select the end frame. The new segment is merged into the existing ID.

### 3. Context Menu (Right-Click)
Right-click any item in the **Events List**:

| Menu Item | Description |
| :--- | :--- |
| **❌ Remove Box from Current Frame** | Deletes the annotation only on the **current frame** (for temporary occlusion). |
| **⚡ Set Current as START** | Sets current frame as the **Start Point** (crops previous frames). |
| **⚡ Set Current as END** | Sets current frame as the **End Point** (crops subsequent frames). |
| **🗑️ Delete Event Completely** | **Permanently deletes** the event and all history. |

---

## ⌨️ Shortcuts

| Key | Function |
| :--- | :--- |
| `←`  | Previous Frame |
| `→`  | Next Frame |
| `LMB` (Left Click) | Draw / Drag Box |
| `RMB` (Right Click) | Pan Canvas |
| `Wheel` | Zoom Canvas |

---

## 📂 Output Format

Click **"💾 Save All Data"** to generate `annotations.json` in the root folder.

**V13 Format Specs**:
* **Coordinates**: `box_2d` uses `[x1, y1, x2, y2]` (Top-Left, Bottom-Right).
* **Quality Fields**: Added `quality_status` and `reject_reason`.

```json
{
    "events": {
        "1": {
            "category": "Vehicle",
            "caption": "A truck parked by the road",
            "box_2d": [100, 200, 300, 400],  // [x1, y1, x2, y2]
            "involved_frames": [
                "2023-01-01.tif",
                "2023-01-02.tif"
            ],
            "quality_status": "good",         // Default
            "reject_reason": null
        },
        "2": {
            "category": "Construction",
            "caption": "Foundation work under tree shade",
            "box_2d": [500, 600, 700, 800],
            "involved_frames": [ "2023-01-05.tif" ],
            "quality_status": "bad",          // ❌ Marked as Bad
            "reject_reason": "Occluded"       // ⚠️ Specific Reason
        }
    },
    "image_quality": {
        "2023-01-01.tif": "good",
        "2023-01-02.tif": "poor"  // Image marked as Poor (via top flag button)
    }
}
```

---

## ⚙️ Custom Configuration

You can customize dropdown options by editing JSON files in `config/`:

* **`categories.json`**: Define your labeling categories (Group/Sub-category).
* **`error_reasons.json`**: Define reasons for quality rejection (e.g., "Blurry", "Tiny Object").