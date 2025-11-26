<div align="center">
  <img src="./assets/icon.png" alt="tracker-icon" height="100"/>

</div>

<div align="center">

**[English](README_en.md) | 简体中文**

</div>

<div align="center">

![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![Status](https://img.shields.io/badge/Status-Stable-blue)
![License](https://img.shields.io/badge/License-MIT-orange)

**一款高性能时序影像事件标注工具：支持大尺度遥感影像与多维质量评价**

</div>

<br/>

**Tracker** 是一个专为 **“位置固定、属性变化”** 的时序事件（如建筑施工进度、植被生长监测、定点监控）设计的轻量级标注工具。它解决了传统工具在加载 GB 级遥感影像时的卡顿问题，并引入了 **“一次画框，全序列同步”** 的逻辑。

---

## ✨ 核心特性 (Key Features)

### 🚀 高性能渲染
* **超大影像支持**：采用动态降采样技术，流畅加载 **GB 级** `.tif` / `.tiff` 遥感影像。
* **多格式兼容**：支持 `.png`, `.jpg`, `.jpeg` 等常见格式。
* **智能时序排序**：内置正则引擎，自动识别文件名中的日期（如 `2023-10-01`），而非简单的字符排序。

### ⚡ 高效时序工作流
* **批量创建 (Batch)**：画一次框，拖动滑块即可自动填充该事件在未来 N 帧中的存在。
* **离散拼接 (Append)**：支持非连续时间段标注（例如：第1-3天出现，第8-10天再次出现，自动合并为同一ID）。
* **全序列同步 (Sync)**：修改任意一帧的框位置，该事件在所有时间点上的框都会自动同步更新（基于固定区域假设）。

### 🛡️ 双重质量控制 (Quality Control)
* **图像级质检**：标记整张图片为“劣质”（如全图云雾遮挡）。
* **事件级质检 (NEW)**：针对具体的标注框，评价其质量（Good/Bad）。若标记为 Bad，可选择具体原因（如 `遮挡严重`、`类别错误`、`框不贴合`），数据将直接写入 JSON。

---

## 🛠️ 安装 (Installation)

```bash
# 1. 克隆仓库
git clone [https://github.com/your-repo/Tracker.git](https://github.com/your-repo/Tracker.git)
cd Tracker

# 2. 安装依赖 (推荐使用 conda 环境)
pip install -r requirements.txt
# 核心依赖: PyQt6, numpy, rasterio, Pillow
```

---

## 🏃‍♂️ 操作指南 (User Guide)

### 1. 启动与加载

运行 `main.py` 启动程序：

```bash
python main.py
```

* 点击右侧面板顶部的 **"📂 Open Root Folder"** 选择包含图像的文件夹。
* 程序会自动扫描并加载图像，底部出现时间轴导航条。

### 2. 标注流程 (Annotation Workflow)

#### A. 创建标注 (Create)
1.  **画框**：在左侧画布上按住鼠标左键拖拽。
2.  **填写信息**：松开鼠标后弹出对话框：
    * **Group/Category**：选择或输入类别。
    * **Caption**：输入详细描述（支持中文）。
    * **End Frame**：拖动滑块选择该事件持续到哪一帧。
3.  **确认**：点击 OK，系统自动生成连续标注。

#### B. 质量评价 (Quality Check) - ✨ V13 新功能
当你发现某个标注有问题（例如物体被树木遮挡，或者框画得不够准），但又不想删除它时：

1.  **选中事件**：在右侧列表点击该事件（如 `ID 1: 建筑施工`）。
2.  **查看右下角面板**：找到 **"选中事件评价 (Event Quality)"** 区域。
3.  **标记劣质**：
    * 点击 **"❌ 劣质 (Bad)"**。
    * **下拉框选择原因**：从列表中选择（如 `遮挡严重`、`框不贴合`）。
4.  **视觉反馈**：右侧列表中的该事件会变红并显示 `❌` 标记，提示该数据已被标记为 Bad。

#### C. 追加片段 (Append)
*场景：物体消失了几天又出现了。*
1.  跳转到物体再次出现的帧。
2.  画框。
3.  在弹窗的下拉菜单中，选择 **"ID x: [已有事件名称]"**。
4.  选择结束帧并确认。该新片段将自动归并到原有 ID 中。

### 3. 右键高级菜单 (Context Menu)
在右侧 **Events List** 中右键点击某个事件：

| 菜单项 (Item) | 功能描述 (Description) |
| :--- | :--- |
| **❌ Remove Box from Current Frame** | 仅删除**当前帧**的标注（用于中间短暂消失或完全遮挡）。 |
| **⚡ Set Current as START** | 将当前帧设为该事件的**起点**（自动裁剪前面的帧）。 |
| **⚡ Set Current as END** | 将当前帧设为该事件的**终点**（自动裁剪后面的帧）。 |
| **🗑️ Delete Event Completely** | **彻底删除**该事件及其所有历史记录。 |

---

## ⌨️ 快捷键 (Shortcuts)

| 按键 (Key) | 功能 (Function) |
| :--- | :--- |
| `←`  | 上一帧 (Previous Frame) |
| `→`  | 下一帧 (Next Frame) |
| `1` ~ `9` | 快速跳转至对应序号的帧 |
| `鼠标左键` | 画框 / 拖拽调整 |
| `鼠标右键` | 拖拽平移画布 (Pan) |
| `鼠标滚轮` | 缩放画布 (Zoom) |

---

## 📂 数据格式 (Output Format)

点击 **"💾 Save All Data"** 后，会在图像同级目录下生成 `annotations.json`。

**V13 格式说明**：
* **坐标格式**：`box_2d` 使用 `[x1, y1, x2, y2]` (左上角, 右下角)。
* **质量字段**：新增 `quality_status` 和 `reject_reason`。

```json
{
    "events": {
        "1": {
            "category": "Vehicle",
            "caption": "一辆卡车停在路边",
            "box_2d": [100, 200, 300, 400],  // [x1, y1, x2, y2]
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
            "quality_status": "bad",          // ❌ 被标记为劣质
            "reject_reason": "遮挡严重 (Occluded)" // ⚠️ 具体原因
        }
    },
    "image_quality": {
        "2023-01-01.tif": "good",
        "2023-01-02.tif": "poor"  // 整张图质量差（通过顶部 Flag 按钮标记）
    }
}
```

---

## ⚙️ 自定义配置 (Custom Configuration)

你可以通过修改 `config/` 目录下的 JSON 文件来自定义下拉选项：

* **`categories.json`**: 自定义标注类别（Group/Sub-category）。
* **`error_reasons.json`**: 自定义质量评价的错误原因列表（如“模糊”、“太小”等）。