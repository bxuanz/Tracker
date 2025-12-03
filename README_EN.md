<div align="center">
  <img src="./assets/icon.png" alt="tracker-icon" height="120"/>

  # Tracker V13

  **High-Performance Universal Temporal Annotation Tool**

  [![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
  [![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
  [![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)
  [![Status](https://img.shields.io/badge/Status-Stable-brightgreen.svg)]()

  **English | [简体中文](README.md)**

</div>

<br/>

**Tracker** is a lightweight, high-performance annotation tool designed specifically for **"Fixed-Position, Attribute-Changing"** temporal events (e.g., construction progress, vegetation growth, surveillance monitoring).

It is optimized for **GB-level Remote Sensing Imagery (`.tif`)** as well as standard images, solving the memory overflow and lag issues often encountered with traditional tools. Version 13 introduces a **Multi-dimensional Quality Control System** and **Auto-Save mechanisms**, significantly boosting the efficiency and quality of dataset construction.

---

## ✨ Key Features

### 🚀 Extreme Performance
* **Large Image Support**: Utilizes dynamic downsampling and viewport caching to smoothly load and render **GB-level** `.tif` / `.tiff` geospatial images.
* **Universal Compatibility**: Natively supports `.png`, `.jpg`, `.jpeg`, `.tif`, and other common formats.
* **Smart Chronology**: Built-in Regex engine automatically extracts dates from filenames (e.g., `2023-10-01`) to build a precise timeline, rather than relying on simple ASCII sorting.

### ⚡ Efficient Workflow
* **Batch Population**: **"Draw Once, Sync Everywhere"**. Draw a box on the start frame and drag the slider to automatically populate the event across future N frames.
* **Discrete Append**: Supports non-continuous time segments. (e.g., An object appears on days 1-3, then again on days 8-10. You can append the new segment to the existing ID without creating a duplicate.)
* **Global Sync**: Based on the "Fixed Region Assumption," modifying the box coordinates in *any* frame automatically updates that ID's coordinates across *all* involved frames.
* **Auto-Save**: Every operation (create, modify, evaluate) is written to the disk in real-time, preventing data loss from crashes.

### 🛡️ Dual-Level Quality Control
* **Image-Level QC**: Flag an entire image as "Poor" (e.g., corrupted data or full cloud cover) with a single click.
* **Event-Level QC**: **New in V13**. Evaluate individual annotation instances:
    * **Good**: Valid sample.
    * **Bad**: Invalid/Low-quality sample. Supports selecting specific reasons (e.g., `Occluded`, `Wrong Label`, `Loose Box`). This data is saved to JSON for dataset cleaning.

---

## 🛠️ Installation

### Requirements
* Python 3.10+
* Conda environment (Recommended)

### Steps

```bash
# 1. Clone Repository
git clone [https://github.com/your-repo/Tracker.git](https://github.com/your-repo/Tracker.git)
cd Tracker

# 2. Create and Activate Environment (Optional but recommended)
conda create -n tracker python=3.10
conda activate tracker

# 3. Install Dependencies
pip install -r requirements.txt
# Core libs: PyQt6, numpy, rasterio, Pillow
```

---

## 🏃‍♂️ User Guide

### 1. Launch & Load
Run the main script:
```bash
python main.py
```
* Click **"📂 Open Root Folder"** on the top right.
* Select the directory containing your image sequence.
* The tool will scan, sort, and index the images. A timeline navigation bar will appear at the bottom.

### 2. Annotation Workflow

#### A. Create New Event
1.  **Draw**: Drag the Left Mouse Button on the canvas to draw a bounding box.
2.  **Input Attributes**: A dialog appears upon release:
    * **Group/Category**: Select from the list or type a new category.
    * **Caption**: Enter a detailed natural language description.
    * **End Frame**: Drag the slider to visually set the duration of this event.
3.  **Confirm**: Click OK. The system generates continuous annotations for the selected range.

#### B. Quality Check (QC) ✨
*When you find an imperfect annotation (e.g., object partially blocked by trees) but wish to keep the record:*

1.  **Select Event**: Click the target event in the right-side **Events List** (e.g., `ID 1: Construction`).
2.  **QC Panel**: Locate the **"Event Quality"** section at the bottom right.
3.  **Mark as Bad**:
    * Switch the toggle to **"❌ Bad"**.
    * **Select Reason**: Choose a specific reason from the dropdown (e.g., `Occluded`, `Loose Box`).
4.  **Feedback**: The item in the list will turn RED with a `❌` mark.

#### C. Append Segment
*Scenario: An object disappears for a while and reappears at the same location.*
1.  Navigate to the frame where the object reappears.
2.  Draw a box at the location.
3.  In the **Target Event** dropdown of the dialog, select **"ID x: [Existing Event Name]"**.
4.  The system merges the new timeframe into the existing ID.

### 3. Advanced Editing (Context Menu)

Right-click any item in the **Events List** to access advanced functions:

| Menu Item | Description |
| :--- | :--- |
| **❌ Remove Box from Current Frame** | Removes the annotation only from the **current frame** (useful for temporary occlusion or disappearance). |
| **⚡ Set Current as START** | Sets the current frame as the **New Start Point** (automatically crops/deletes all previous history for this ID). |
| **⚡ Set Current as END** | Sets the current frame as the **New End Point** (automatically crops/deletes all subsequent history for this ID). |
| **🗑️ Delete Event Completely** | **Permanently deletes** the event ID and all its history across the entire timeline. |

---

## ⌨️ Shortcuts

Master these shortcuts to maximize your speed:

| Key | Function |
| :--- | :--- |
| `←` / `↑` | Previous Frame |
| `→` / `↓` | Next Frame |
| `Left Click` | Draw / Select Box / Resize |
| `Right Click` | Pan Canvas |
| `Scroll Wheel` | Zoom Canvas |

---

## 📂 Output Format

Upon clicking **"💾 Save All Data"** (or triggering Auto-Save), an `annotations.json` file is generated in the image directory.

### JSON Structure

```json
{
    "events": {
        "1": {
            "category": "Vehicle",
            "caption": "A truck parked by the road",
            "box_2d": [100, 200, 300, 400],  // Format: [x1, y1, x2, y2] (Absolute Pixels)
            "involved_frames": [
                "2023-01-01.tif",
                "2023-01-02.tif"
            ],
            "quality_status": "good",         // Default is 'good'
            "reject_reason": null
        },
        "2": {
            "category": "Construction",
            "caption": "Foundation work under tree shade",
            "box_2d": [500, 600, 700, 800],
            "involved_frames": [ "2023-01-05.tif" ],
            "quality_status": "bad",          // ❌ Marked as bad/poor quality
            "reject_reason": "Occluded"       // ⚠️ Specific reason recorded
        }
    },
    "image_quality": {
        "2023-01-01.tif": "good",
        "2023-01-02.tif": "poor"  // Image marked as poor via the top 'Flag' button
    }
}
```

---

## ⚙️ Configuration

You can customize the UI options by editing the JSON files in the `config/` directory without modifying the code:

1.  **`config/categories.json`**
    * Define the hierarchy of categories (Group -> Sub-category) for the creation dialog.
2.  **`config/error_reasons.json`**
    * Define the list of "Rejection Reasons" (e.g., Blurry, Truncated, Occluded) for the QC panel.

