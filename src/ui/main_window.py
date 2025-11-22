import json
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QListWidget, 
                             QInputDialog, QMessageBox, QSplitter, QMenu, 
                             QScrollArea, QProgressBar, QApplication)  # <--- 这里加了 QApplication
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QAction, QColor, QImage, QPixmap

from src.utils.image_loader import ImageLoader
from src.utils.config_manager import ConfigManager
from src.ui.canvas import AnnotationCanvas
from src.ui.batch_dialog import BatchDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker  (Batch Mode & Sync Edit)")
        self.resize(1400, 900)
        
        # Data
        self.image_paths = []
        self.image_map = {} 
        self.current_idx = 0
        self.annotations = {}
        self.current_event_id = None
        self.downsample_ratio = 1.0
        
        self.config = ConfigManager() # 加载配置
        
        self.init_ui()
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # === Left Panel ===
        left_layout = QVBoxLayout()
        
        # Top Info
        top_layout = QHBoxLayout()
        self.lbl_info = QLabel("Ready. Use keyboard ↑↓←→ to navigate.")
        self.lbl_info.setStyleSheet("font-family: monospace; font-weight: bold;")
        btn_fit = QPushButton("Fit View")
        btn_fit.clicked.connect(lambda: self.canvas.reset_view())
        top_layout.addWidget(self.lbl_info)
        top_layout.addStretch()
        top_layout.addWidget(btn_fit)
        
        # Canvas
        self.canvas = AnnotationCanvas()
        self.canvas.geometry_changed.connect(self.on_geometry_changed)
        
        # Frame Strip
        self.frame_layout = QHBoxLayout()
        frame_container = QWidget()
        frame_container.setLayout(self.frame_layout)
        self.frame_layout.setContentsMargins(0,0,0,0)
        self.frame_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        scroll = QScrollArea()
        scroll.setFixedHeight(50)
        scroll.setWidgetResizable(True)
        scroll.setWidget(frame_container)
        scroll.setStyleSheet("border: none; background: #2b2b2b;")
        
        # Bottom Nav
        nav_layout = QHBoxLayout()
        btn_prev = QPushButton("<< Prev")
        btn_prev.clicked.connect(self.prev_frame)
        btn_next = QPushButton("Next >>")
        btn_next.clicked.connect(self.next_frame)
        self.pbar = QProgressBar(); self.pbar.setVisible(False)
        
        nav_layout.addWidget(btn_prev)
        nav_layout.addWidget(btn_next)
        nav_layout.addWidget(self.pbar)
        nav_layout.addStretch()
        
        left_layout.addLayout(top_layout)
        left_layout.addWidget(self.canvas, 1)
        left_layout.addWidget(scroll)
        left_layout.addLayout(nav_layout)
        
        # === Right Panel ===
        right_layout = QVBoxLayout()
        
        btn_load = QPushButton("Open Folder")
        btn_load.clicked.connect(self.load_folder)
        btn_load.setStyleSheet("padding: 8px; font-weight: bold;")
        
        # 列表
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.select_event)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        self.lbl_status = QLabel("Status: Idle")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #E06C75; font-weight: bold;")
        
        btn_save = QPushButton("Save JSON")
        btn_save.clicked.connect(self.save_json)
        btn_save.setStyleSheet("height: 40px; font-weight: bold;")
        
        right_layout.addWidget(btn_load)
        right_layout.addWidget(QLabel("Events (Right-click to edit timeline):"))
        right_layout.addWidget(self.list_widget)
        right_layout.addWidget(self.lbl_status)
        right_layout.addStretch()
        right_layout.addWidget(btn_save)
        
        splitter = QSplitter()
        w_l = QWidget(); w_l.setLayout(left_layout)
        w_r = QWidget(); w_r.setLayout(right_layout)
        splitter.addWidget(w_l); splitter.addWidget(w_r)
        splitter.setStretchFactor(0, 4)
        layout.addWidget(splitter)
        
        self.frame_btns = []

    # === 1. 键盘控制 ===
    def keyPressEvent(self, event):
        key = event.key()
        if key in [Qt.Key.Key_Left, Qt.Key.Key_Up]:
            self.prev_frame()
        elif key in [Qt.Key.Key_Right, Qt.Key.Key_Down]:
            self.next_frame()
        else:
            super().keyPressEvent(event)

    # === 2. 核心逻辑: 接收画布变化 ===
    def on_geometry_changed(self, rect, is_new):
        real_box = self.rect_to_real(rect)
        
        if is_new:
            # === 新建模式: 批处理 ===
            # 弹出对话框
            dlg = BatchDialog(self, self.config.categories, self.current_idx, len(self.image_paths))
            if dlg.exec():
                data = dlg.result_data
                category = data["category"]
                end_idx = data["end_idx"]
                
                # 保存新类别
                self.config.add_category(category)
                
                # 创建新ID
                new_id = max(self.annotations.keys(), default=0) + 1
                frames_data = {}
                
                # 循环填充中间的帧
                for i in range(self.current_idx, end_idx + 1):
                    frames_data[str(i)] = real_box
                
                self.annotations[new_id] = {"caption": category, "frames": frames_data}
                self.refresh_list()
                self.select_by_id(new_id)
                self.lbl_status.setText(f"Created ID {new_id} across {end_idx - self.current_idx + 1} frames.")
        else:
            # === 编辑模式: 全序列同步 ===
            if not self.current_event_id: return
            
            # 找到当前ID下的所有帧，全部强制更新为新坐标
            event_data = self.annotations[self.current_event_id]
            count = 0
            for frame_key in event_data["frames"].keys():
                event_data["frames"][frame_key] = real_box
                count += 1
            
            self.render_annotations()
            self.lbl_status.setText(f"Updated ID {self.current_event_id}: Synced to all {count} frames.")

    def rect_to_real(self, rect):
        x = rect.x() / self.downsample_ratio
        y = rect.y() / self.downsample_ratio
        w = rect.width() / self.downsample_ratio
        h = rect.height() / self.downsample_ratio
        return [x, y, w, h]

    # === 3. 调整事件时长 (右键菜单) ===
    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        eid = int(item.text().split(":")[0].replace("ID ", ""))
        
        menu = QMenu()
        # 功能1: 在此结束
        act_end = QAction(f"Set Frame {self.current_idx+1} as End Point", self)
        act_end.triggered.connect(lambda: self.trim_event_after(eid))
        menu.addAction(act_end)
        
        # 功能2: 延长至此
        act_ext = QAction(f"Extend Event to Frame {self.current_idx+1}", self)
        act_ext.triggered.connect(lambda: self.extend_event_to_current(eid))
        menu.addAction(act_ext)
        
        menu.addSeparator()
        
        # 功能3: 删除
        act_del = QAction("Delete Event", self)
        act_del.triggered.connect(lambda: self.delete_event(eid))
        menu.addAction(act_del)
        
        menu.exec(self.list_widget.mapToGlobal(pos))

    def trim_event_after(self, eid):
        if eid in self.annotations:
            frames = self.annotations[eid]["frames"]
            keys_to_del = [k for k in frames.keys() if int(k) > self.current_idx]
            for k in keys_to_del: del frames[k]
            self.refresh_list()
            self.render_annotations()
            self.lbl_status.setText(f"Event {eid} trimmed.")

    def extend_event_to_current(self, eid):
        if eid in self.annotations:
            frames = self.annotations[eid]["frames"]
            indices = sorted([int(k) for k in frames.keys()])
            if not indices: return
            last_idx = indices[-1]
            if self.current_idx > last_idx:
                box = frames[str(last_idx)] # 复制最后一帧的框
                for i in range(last_idx + 1, self.current_idx + 1):
                    frames[str(i)] = box
                self.refresh_list()
                self.render_annotations()
                self.lbl_status.setText(f"Event {eid} extended.")

    # === 基础功能 (Load/Render/Nav) ===
    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder: return
        exts = ['*.tif', '*.tiff', '*.png', '*.jpg', '*.jpeg']; files = []
        for ext in exts: 
            files.extend(list(Path(folder).glob(ext)))
            files.extend(list(Path(folder).glob(ext.upper())))
        self.image_paths = sorted(list(set([str(f) for f in files])))
        if not self.image_paths: return
        self.image_map = {Path(p).name: i for i, p in enumerate(self.image_paths)}
        
        self.load_annotations(folder)
        self.setup_frame_bar()
        self.current_idx = 0
        self.load_image()

    def load_image(self):
        if not self.image_paths: return
        self.pbar.setVisible(True); QApplication.processEvents()
        path = self.image_paths[self.current_idx]
        img_data, scale, (ow, oh) = ImageLoader.load(path)
        if img_data is not None:
            self.downsample_ratio = scale
            h, w, c = img_data.shape
            q_img = QImage(img_data.tobytes(), w, h, 3*w, QImage.Format.Format_RGB888)
            self.canvas.set_image(QPixmap.fromImage(q_img))
            if self.canvas.view_scale == 1.0: self.canvas.reset_view()
        
        self.update_frame_bar()
        self.render_annotations()
        self.pbar.setVisible(False)
        self.lbl_info.setText(f"Frame: {self.current_idx+1}/{len(self.image_paths)} | {Path(path).name}")

    def render_annotations(self):
        to_draw = []
        frame_key = str(self.current_idx)
        for eid, data in self.annotations.items():
            if frame_key in data["frames"]:
                rx, ry, rw, rh = data["frames"][frame_key]
                d = self.downsample_ratio
                rect = QRectF(rx*d, ry*d, rw*d, rh*d)
                is_sel = (eid == self.current_event_id)
                to_draw.append((rect, self.get_color(eid), f"ID {eid}: {data['caption']}", is_sel))
        self.canvas.set_annotations(to_draw)

    # === Helper Functions ===
    def get_color(self, eid): return QColor.fromHsv(int((eid * 137.5) % 360), 200, 255)
    
    def refresh_list(self):
        self.list_widget.clear()
        for eid in sorted(self.annotations.keys()):
            d = self.annotations[eid]
            frames = sorted([int(x) for x in d['frames'].keys()])
            rng = f"{min(frames)+1}-{max(frames)+1}" if frames else "None"
            self.list_widget.addItem(f"ID {eid}: {d['caption']} (Frames: {rng})")
    
    def select_event(self, item):
        if not item: return
        try:
            eid = int(item.text().split(":")[0].replace("ID ", ""))
            self.current_event_id = eid
            self.render_annotations()
        except: pass
    
    def select_by_id(self, eid):
        self.current_event_id = eid
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).text().startswith(f"ID {eid}:"):
                self.list_widget.setCurrentRow(i)
                break
        self.render_annotations()
        
    def delete_event(self, eid):
        if eid in self.annotations:
            del self.annotations[eid]
            if self.current_event_id == eid: self.current_event_id = None
            self.refresh_list(); self.render_annotations()

    def setup_frame_bar(self):
        while self.frame_layout.count(): 
            c = self.frame_layout.takeAt(0)
            if c.widget(): c.widget().deleteLater()
        self.frame_btns = []
        for i in range(len(self.image_paths)):
            btn = QPushButton(str(i+1))
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, x=i: self.jump_frame(x))
            self.frame_layout.addWidget(btn)
            self.frame_btns.append(btn)
            
    def update_frame_bar(self):
        for i, btn in enumerate(self.frame_btns):
            btn.setStyleSheet("background: #007ACC; color: white;" if i==self.current_idx else "background: #444; color: #aaa; border: none;")
            
    def jump_frame(self, idx):
        if idx != self.current_idx: self.current_idx = idx; self.load_image()
    def prev_frame(self): 
        if self.current_idx > 0: self.jump_frame(self.current_idx - 1)
    def next_frame(self): 
        if self.current_idx < len(self.image_paths)-1: self.jump_frame(self.current_idx + 1)
        
    def save_json(self):
        if not self.image_paths: return
        save_data = {}
        for eid, data in self.annotations.items():
            frames_named = {}
            for idx_str, box in data["frames"].items():
                idx = int(idx_str)
                if 0 <= idx < len(self.image_paths):
                    name = Path(self.image_paths[idx]).name
                    frames_named[name] = box
            save_data[eid] = {"caption": data["caption"], "frames": frames_named}
        path = Path(self.image_paths[0]).parent / "annotations.json"
        with open(path, 'w', encoding='utf-8') as f: json.dump(save_data, f, indent=4, ensure_ascii=False)
        QMessageBox.information(self, "Saved", f"Saved to:\n{path}")
        
    def load_annotations(self, folder):
        path = Path(folder) / "annotations.json"
        self.annotations = {}
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f: raw = json.load(f)
                for eid_str, dat in raw.items():
                    eid = int(eid_str)
                    frames_idx = {}
                    for k, v in dat["frames"].items():
                        if k in self.image_map: frames_idx[str(self.image_map[k])] = v
                        elif k.isdigit(): frames_idx[k] = v
                    self.annotations[eid] = {"caption": dat["caption"], "frames": frames_idx}
                self.refresh_list()
            except Exception as e: print(e)