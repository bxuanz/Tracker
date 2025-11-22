# <div align="center">Tracker 🛰️📅</div>

<div align="center">


![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![License](https://img.shields.io/badge/License-MIT-orange)

**专为大尺度遥感影像与时序图像序列设计的轻量级标注工具**

</div>

**Tracker** 解决了传统标注工具（如 LabelImg/LabelMe）在加载超大 GeoTIFF（500MB+）时内存溢出或卡顿的问题，并引入了 **“事件（Event）”** 的概念，支持对同一目标在不同时间相上的持续追踪标注。

> 🚀 **新特性：** 支持批量事件创建、全序列同步修改、键盘导航及自定义类别管理，专为**固定位置的时序变化监测**（如建筑施工、植被生长）打造。

---

## ✨ 核心功能 (Features)

* 🎮 **高效键盘导航**：支持 `↑` `↓` `←` `→` 键快速切换图像，手不离键盘。
* ⚡ **批量事件创建 (Batch Mode)**：画一次框，自动填充该事件在后续 N 帧中的位置，极大提高标注效率。
* 🔄 **全序列同步修改 (Sync Edit)**：发现框的大小不合适？只需修改任意一帧，该事件在所有帧中的框都会自动同步更新。
* 📂 **自定义类别管理**：输入的新类别会自动保存到 `categories.json`，下次直接调用。
* ✂️ **时间轴微调**：通过右键菜单，可随时“结束”或“延长”事件的持续时间。
* 🚀 **大图无压力**：支持 GB 级 GeoTIFF 及普通 JPG/PNG 序列。

## 🛠️ 安装与配置 (Installation)

### 1. 克隆仓库
```bash
git clone -b Tracker_V2 https://github.com/bxuanz/Tracker.git
cd Tracker
```

### 2. 创建环境 (推荐)
```bash
conda create -n tracker_env python=3.9
conda activate tracker_env
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```
*(依赖库包括：`PyQt6`, `numpy`, `rasterio`, `Pillow`)*

## 🏃‍♂️ 操作指南 (User Guide)

### 1. 启动与加载
```bash
python main.py
```
点击 **"Open Folder"** 选择包含图像序列的文件夹。

### 2. 创建固定事件 (Batch Create)
1.  在图上直接按住左键 **画框**。
2.  **自动弹窗**：选择类别（支持输入新类别），并拖动滑块选择**结束帧**。
3.  点击确认，程序会自动在 `[当前帧 -> 结束帧]` 的范围内生成相同的标注框。

### 3. 浏览与修改 (Sync Edit)
* **切换图像**：使用键盘方向键 `←` `→` 或 `↑` `↓`。
* **修改框**：
    * 点击选中图上的框（变为实线）。
    * 拖动边缘调整大小，或拖动内部移动位置。
    * **注意**：修改会立即同步更新到该事件涉及的**所有帧**。

### 4. 时间轴管理 (Timeline)
在右侧事件列表的某个 Item 上 **点击鼠标右键**：
* **Set ... as End Point**：删除当前帧之后的所有标注（用于事件提前结束）。
* **Extend Event to ...**：将事件延长至当前帧（用于事件持续时间比预想的长）。
* **Delete Event**：彻底删除该事件。

## 📂 数据格式 (Output Format)

标注结果保存为 `annotations.json`，Key 为事件 ID，内部自动绑定图像文件名。

```json
{
    "1": {
        "caption": "新建跑道施工",
        "frames": {
            "2024_01_01.tif": [5000, 3000, 200, 200],
            "2024_01_02.tif": [5000, 3000, 200, 200],
            "..." : [5000, 3000, 200, 200]
        }
    },
    "2": {
        "caption": "植被破坏",
        "frames": {
            "img_005.jpg": [100, 100, 50, 50],
            "img_006.jpg": [100, 100, 50, 50]
        }
    }
}
```

## 🤝 贡献 (Contributing)

欢迎提交 Issue 或 Pull Request！

## 📄 许可证 (License)

本项目采用 [MIT License](LICENSE) 开源。