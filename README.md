<div align="center">
  <img src="./assets/icon.png" alt="tracker-icon" height="120"/>

  # Tracker V13
  
  **高性能时序影像事件标注工具 (High-Performance Temporal Event Tracker)**

  [![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
  [![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
  [![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)
  [![Status](https://img.shields.io/badge/Status-Stable-brightgreen.svg)]()

  **[English](README_EN.md) | 简体中文**

</div>

<br/>

**Tracker** 是一款专为 **“位置固定、属性变化”** 的时序事件（如遥感影像中的建筑施工进度、植被生长监测、定点设施监控）设计的轻量级、高性能标注工具。

它针对 **GB 级大尺度遥感影像 (`.tif`)** 进行了深度优化，解决了传统工具在加载多波段、超大分辨率影像时的卡顿问题。V13 版本引入了 **多维质量评价体系**、**智能防遮挡渲染** 与 **全自动保存机制**，显著提升了数据集构建的效率与质量。

---

## ✨ 核心特性 (Key Features)

### 🚀 极致性能 (Performance)
* **超大影像支持**：采用动态降采样与视口缓存技术，流畅加载并渲染 **GB 级** `.tif` / `.tiff` 遥感影像。
* **智能时序排序**：内置正则解析引擎，根据文件名中的日期（如 `2023-10-01`）自动构建时间轴，而非简单的 ASCII 排序。

### ⚡ 高效交互 (Interaction)
* **智能画布**：
    * **防越界系统**：画框与调整大小被严格限制在图像边界内。
    * **防遮挡渲染**：选中对象的标签自动浮于顶层，且智能检测边缘，防止文字跑出屏幕外。
    * **恒定手柄**：调整大小的控制手柄（青色方块）在屏幕上保持固定大小，不受缩放比例影响，易于抓取。
* **全序列同步 (Sync)**：基于“固定区域假设”，修改任意一帧的标注框位置，该 ID 在所有涉及帧上的坐标均会自动同步更新。

### 🛡️ 数据安全与质检 (Safety & QC)
* **自动保存 (Auto-Save)**：采用 **`{文件夹名}.json`** 格式实时保存。所有操作（画框、修改、评价）均即时写入硬盘，无需手动保存。
* **多维质检**：支持 **图像级**（全图废弃）与 **事件级**（单个框 Good/Bad + 原因）的双重质量控制。

---

## 🛠️ 安装 (Installation)

### 环境要求
* Python 3.10+
* 建议使用 Conda 环境

### 安装步骤

```bash
# 1. 克隆仓库
git clone [https://github.com/your-repo/Tracker.git](https://github.com/your-repo/Tracker.git)
cd Tracker

# 2. 创建并激活虚拟环境 (可选)
conda create -n tracker python=3.10
conda activate tracker

# 3. 安装依赖
pip install -r requirements.txt
# 核心依赖库: PyQt6, numpy, rasterio, Pillow
```

---

## 📖 详细操作指南 (Detailed Operations)

### 1. 数据加载与管理
* **打开根目录**：点击右上角 **"📂 Open Root Folder"**，选择包含多个子文件夹的数据集根目录（或单个图片文件夹）。
* **文件夹导航**：右侧 **Sub-Folders / Datasets** 列表显示当前根目录下的所有子文件夹。
    * ✅ **绿色勾选**：表示该文件夹下已存在标注文件（`文件夹名.json` 或旧版 `annotations.json`）。
    * ⬜ **白色方块**：表示该文件夹尚未标注。
    * **点击列表项**：快速切换数据集，无需重新打开文件对话框。

### 2. 视图控制 (View Control)
* **缩放 (Zoom)**：滚动鼠标滚轮。以鼠标指针为中心进行缩放。
* **平移 (Pan)**：按住 **鼠标右键** 拖拽画布。
* **全图适配 (Fit)**：点击左上角的 **"Fit View"** 按钮，重置视图以适应窗口。

### 3. 标注流程 (Annotation Workflow)

#### A. 创建新事件 (Create)
1.  **画框**：在左侧画布上，按住 **鼠标左键** 框选目标。
2.  **属性录入**：松开鼠标后弹出对话框：
    * **Group/Category**：选择预设类别，或点击 "Custom" 手动输入新类别。
    * **Caption**：输入详细的自然语言描述（必填）。
    * **End Frame**：拖动滑块设定结束帧。**默认值为当前帧**（即默认仅标注单帧）。
3.  **确认**：点击 OK，系统自动生成标注，并选中新生成的事件。

#### B. 编辑与调整 (Edit)
* **选中事件**：直接在画布上双击击事件区域，或在右侧列表点击 ID。选中项显示为 **实线**，标签高亮，并带有 **青色调整手柄**。
* **移动位置**：鼠标悬停在框内部（光标变为十字），按住左键拖拽。所有关联帧的坐标同步更新。
* **调整大小**：鼠标悬停在右下角的 **青色方块**（光标变为对角箭头），按住左键拖拽。
* **修改属性**：在右侧列表右键点击事件 -> **"✏️ Edit Event Info"**，可修改类别和描述。

#### C. 追加时间段 (Append)
*场景：目标在第 1-5 帧出现，第 6-9 帧消失，第 10 帧又在同一位置出现。*
1.  跳转到第 10 帧。
2.  在目标位置画框。
3.  在弹窗顶部的 **Target Event** 下拉菜单中，选择 **"ID x: [已有事件名称]"**。
4.  系统会将新的时间段合并到该 ID 中，实现离散时间段的同一 ID 追踪。

### 4. 质量控制 (Quality Control)

#### A. 事件级质检 (Event QC)
*针对单个标注框不够完美，但仍有价值保留的情况。*
1.  选中目标事件。
2.  在右下角 **"选中事件评价"** 面板中：
    * 选择 **"❌ 劣质 (Bad)"**。
    * 在下方下拉框选择具体原因（如：`遮挡严重 (Occluded)`, `边缘截断 (Truncated)`, `框不贴合 (Loose Box)`）。
3.  **结果**：右侧列表中该事件变红并打叉，JSON 中会记录 `quality_status: "bad"` 及 `reject_reason`。

#### B. 图像级质检 (Image QC)
*针对整张图片质量太差（如全云雾覆盖）的情况。*
1.  在左侧顶部栏点击 **"🚩 标记为劣质 (Mark Poor)"** 按钮。
2.  按钮变为红色按下状态，JSON 中该图片会被标记为 `"poor"`。

### 5. 高级时间轴操作 (Context Menu)

在右侧 **Events List** 中 **右键点击** 任意事件：

| 菜单项 (Menu Item) | 功能详解 |
| :--- | :--- |
| **❌ Remove Box from Current Frame** | **仅删除当前帧**的标注。用于处理中间某几帧目标短暂被遮挡或消失的情况。 |
| **⚡ Set Current as START** | **截断开头**。将当前帧设为该事件的起点，自动删除当前帧之前的所有数据。 |
| **⚡ Set Current as END** | **截断结尾**。将当前帧设为该事件的终点，自动删除当前帧之后的所有数据。 |
| **🗑️ Delete Event Completely** | **彻底销毁**。删除该 ID 及其在所有帧上的数据，不可恢复。 |

---

## ⌨️ 快捷键 (Shortcuts)

为了提升标注效率，建议熟练使用以下快捷键（全局生效，无需聚焦画布）：

| 按键 (Key) | 功能 (Function) |
| :--- | :--- |
| `←` / `↑` | **上一帧 (Previous Frame)** |
| `→` / `↓` | **下一帧 (Next Frame)** |
| `鼠标左键` | 画框 (Draw) / 选中框 / 移动框 |
| `鼠标左键拖拽手柄` | 调整大小 (Resize) |
| `鼠标右键` | 拖拽平移画布 (Pan) |
| `鼠标滚轮` | 缩放画布 (Zoom) |

---

## 📂 数据输出格式 (Output Format)

程序采用 **全自动保存** 机制。
数据文件保存在图像所在文件夹内，命名规则为 **`{文件夹名}.json`**。

### JSON 结构示例

```json
{
    "events": {
        "1": {
            "category": "Vehicle",
            "caption": "一辆卡车停在路边",
            "box_2d": [100, 200, 300, 400],  // 格式: [x1, y1, x2, y2] (绝对像素坐标)
            "involved_frames": [
                "2023-01-01.tif",
                "2023-01-02.tif"
            ],
            "quality_status": "good",         // 默认为 good
            "reject_reason": null
        },
        "2": {
            "category": "Construction",
            "caption": "工地正在打地基，但在树荫下",
            "box_2d": [500, 600, 700, 800],
            "involved_frames": [ "2023-01-05.tif" ],
            "quality_status": "bad",          // ❌ 标记为劣质
            "reject_reason": "遮挡严重 (Occluded)" // ⚠️ 具体原因
        }
    },
    "image_quality": {
        "2023-01-01.tif": "good",
        "2023-01-02.tif": "poor"  // 整张图被标记为劣质
    }
}
```

---

## ⚙️ 配置文件 (Configuration)

无需修改代码，直接编辑 `config/` 目录下的 JSON 文件即可定制工具：

1.  **`config/categories.json`**
    * 定制创建弹窗中的类别层级（父类 -> 子类）。
2.  **`config/error_reasons.json`**
    * 定制质量评价面板中的“劣质原因”下拉列表内容。

