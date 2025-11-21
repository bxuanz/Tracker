# Tracker 🛰️📅

![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)


**Tracker** 是一个专为 **大尺度遥感影像** 和 **时序图像序列** 设计的轻量级标注工具。

它解决了传统标注工具（如 LabelImg/LabelMe）在加载超大 GeoTIFF（500MB+）时内存溢出或卡顿的问题，并引入了 **“事件（Event）”** 的概念，支持对同一目标在不同时间相上的持续追踪标注。

> **适用于：** 遥感变化检测、时序事件监测、建筑施工进度追踪、普通视频抽帧序列标注。

## ✨ 核心功能 (Features)

* **🚀 大图无压力加载**：支持 GB 级别的 GeoTIFF 影像。采用智能动态降采样与最大纹理限制（Max Texture Size）技术，在保证 8K 级高清显示的条件下，显存占用极低。
* **📷 多格式支持**：不仅支持专业 `.tif/.tiff` 格式，也完美支持普通的 `.jpg`, `.png`, `.bmp` 图像，可作为一个通用的序列标注工具。
* **⏱️ 时序追踪 (Temporal Tracking)**：基于“事件 ID”的标注逻辑。同一 ID 可在不同时间帧（图像）中关联不同的边界框，轻松构建时序数据集。
* **🗺️ 专业交互体验**：
    * 鼠标右键拖拽平移 (Pan)。
    * 滚轮以光标为中心缩放 (Zoom In/Out)。
    * 底部数字导航条快速跳帧。
* **💾 稳健的数据存储**：标注结果保存为 JSON，**自动绑定图像文件名**，即使文件夹内文件增删或改名，只要文件名不变，标注依然准确。

## 🛠️ 安装与配置 (Installation)

### 1. 克隆仓库
```bash
git clone https://github.com/bxuanz/Tracker.git
cd Tracker
```
### 2.创建虚拟环境 
```bash
   conda create -n tracker_env python=3.9
   conda activate tracker_env
```
### 3.安装依赖
```bash
  pip install -r requirements.txt
```

## 🏃‍♂️ 快速开始 (Usage)
### 1.启动程序
```bash
 python main.py
 ```
### 2.加载数据
* 点击 "Open Folder"，选择包含图像序列（.tif 或 .jpg）的文件夹。
* 程序会自动扫描并在底部生成导航条。
### 3.创建事件 (Event)：
* 在右侧面板点击 "New Event"。
* 输入描述（Caption），例如“机场扩建区域”。
* 此时该事件会被选中（高亮）。
### 4.进行标注：
* 在画布上按住 鼠标左键 拖出矩形框。
* 切换帧：点击底部数字按钮或使用 "Prev/Next" 切换到下一张图。
* 继续标注：在新的时间点，再次画框。程序会自动记录该 ID 在当前帧的位置。
### 5.保存结果：
* 点击 "Save JSON"，标注文件 annotations.json 将保存在图像文件夹中。

## 📂 数据格式 (Output Format)
```json
{
    "1": {
        "caption": "新建跑道施工",
        "frames": {
            "2024_01_01_GF2.tif": [
                5001.5,  // x (原始分辨率坐标)
                3195.6,  // y
                2376.9,  // w
                1893.9   // h
            ],
            "2024_02_01_GF2.tif": [
                5001.5,
                3195.6,
                2500.0,
                2000.0
            ]
        }
    },
    "2": {
        "caption": "油罐车移动",
        "frames": {
            "frame_005.jpg": [100, 100, 50, 50],
            "frame_006.jpg": [120, 105, 50, 50]
        }
    }
}
```


## 🤝 贡献 (Contributing)
欢迎提交 Issue 或 Pull Request！如果你发现加载某种特殊的 Tiff 格式有问题，请附上报错信息。

