import json
import re
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QListWidget, 
                             QInputDialog, QMessageBox, QSplitter, QMenu, 
                             QScrollArea, QProgressBar, QApplication)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QAction, QColor, QImage, QPixmap

from src.utils.image_loader import ImageLoader
from src.utils.config_manager import ConfigManager
from src.ui.canvas import AnnotationCanvas
from src.ui.batch_dialog import BatchDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker (Fixed Region & Quality Tag)")
        self.resize(1400, 900)
        
        self.image_paths = []
        self.image_map = {} 
        self.current_idx = 0
        
        # === 数据结构 ===
        # annotations: { 
        #    eid: { 
        #       "category": str, 
        #       "caption": str, 
        #       "box": [x, y, w, h],  <-- 唯一坐标
        #       "frame_indices": {idx1, idx2, ...} <-- 涉及帧的集合
        #    } 
        # }
        self.annotations = {}
        
        # quality_flags: { "filename.tif": True }
        self.quality_flags = {} 
        
        self.current_event_id = None
        self.downsample_ratio = 1.0
        self.config = ConfigManager()
        
        self.init_ui()
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # === Left Panel ===
        left_layout = QVBoxLayout()
        
        # 1. Top Bar
        top_layout = QHBoxLayout()
        self.lbl_info = QLabel("Ready.")
        self.lbl_info.setStyleSheet("font-family: monospace; font-weight: bold;")
        
        self.btn_flag = QPushButton("🚩 标记图像低质量 (Mark Poor)")
        self.btn_flag.setCheckable(True)
        self.btn_flag.setStyleSheet("""
            QPushButton { background-color: #444; color: #aaa; padding: 5px; }
            QPushButton:checked { background-color: #FF4444; color: white; border: 1px solid red; }
        """)
        self.btn_flag.clicked.connect(self.toggle_quality_flag)
        self.btn_flag.setEnabled(False)

        btn_fit = QPushButton("Fit View")
        btn_fit.clicked.connect(lambda: self.canvas.reset_view())
        
        top_layout.addWidget(self.lbl_info)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_flag)
        top_layout.addWidget(btn_fit)
        
        # 2. Canvas
        self.canvas = AnnotationCanvas()
        self.canvas.geometry_changed.connect(self.on_geometry_changed)
        self.canvas.mouse_moved_info.connect(self.update_status_bar)
        
        # 3. Frame Strip
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
        
        # 4. Bottom Bar
        nav_layout = QHBoxLayout()
        btn_prev = QPushButton("<< Prev")
        btn_prev.clicked.connect(self.prev_frame)
        btn_next = QPushButton("Next >>")
        btn_next.clicked.connect(self.next_frame)
        self.pbar = QProgressBar(); self.pbar.setVisible(False)
        
        nav_layout.addWidget(btn_prev)
        nav_layout.addWidget(btn_next)
        nav_layout.addWidget(self.pbar)
        
        # === 状态栏信息 (黑色字体) ===
        self.lbl_size = QLabel("Size: -")
        self.lbl_size.setStyleSheet("font-family: monospace; margin-left: 20px; color: black; font-weight: bold;")
        nav_layout.addWidget(self.lbl_size)

        self.lbl_coords = QLabel("Pos: -")
        self.lbl_coords.setStyleSheet("font-family: monospace; margin-left: 20px; color: black; font-weight: bold;")
        nav_layout.addWidget(self.lbl_coords)
        
        nav_layout.addStretch()
        
        left_layout.addLayout(top_layout)
        left_layout.addWidget(self.canvas, 1)
        left_layout.addWidget(scroll)
        left_layout.addLayout(nav_layout)
        
        # === Right Panel ===
        right_layout = QVBoxLayout()
        btn_load = QPushButton("Open Folder")
        btn_load.clicked.connect(self.load_folder)
        
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.select_event)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        self.lbl_status = QLabel("Status: Idle")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #E06C75; font-weight: bold;")
        
        btn_save = QPushButton("Save Data")
        btn_save.clicked.connect(self.save_all)
        btn_save.setStyleSheet("height: 40px; font-weight: bold; background-color: #007ACC; color: white;")
        
        right_layout.addWidget(btn_load)
        right_layout.addWidget(QLabel("Events List:"))
        right_layout.addWidget(self.list_widget)
        right_layout.addWidget(self.lbl_status)
        right_layout.addStretch()
        right_layout.addWidget(btn_save)
        
        splitter = QSplitter()
        splitter.addWidget(QWidget()); splitter.widget(0).setLayout(left_layout)
        splitter.addWidget(QWidget()); splitter.widget(1).setLayout(right_layout)
        splitter.setStretchFactor(0, 4)
        layout.addWidget(splitter)
        
        self.frame_btns = []

    def update_status_bar(self, x, y):
        real_x = int(x / self.downsample_ratio)
        real_y = int(y / self.downsample_ratio)
        self.lbl_coords.setText(f"X: {real_x}, Y: {real_y}")

    def toggle_quality_flag(self):
        if not self.image_paths: return
        fname = Path(self.image_paths[self.current_idx]).name
        if self.btn_flag.isChecked():
            self.quality_flags[fname] = True
            self.lbl_status.setText(f"Marked {fname} as POOR.")
        else:
            if fname in self.quality_flags: del self.quality_flags[fname]
            self.lbl_status.setText(f"Unmarked {fname}.")

    # === 核心: 创建/修改 ===
    def on_geometry_changed(self, rect, is_new):
            real_box = self.rect_to_real(rect)
            
            if is_new:
                existing_events = {}
                for eid, data in self.annotations.items():
                    existing_events[eid] = {
                        'category': data.get('category', ''),
                        'caption': data.get('caption', '')
                    }

                dlg = BatchDialog(self, self.config.categories, self.current_idx, len(self.image_paths), existing_events)
                
                if dlg.exec():
                    data = dlg.result_data
                    target_id = data["target_id"]
                    end_idx = data["end_idx"]
                    
                    new_indices = set(range(self.current_idx, end_idx + 1))

                    if target_id != -1:
                        # === 追加模式 (Append) ===
                        if target_id in self.annotations:
                            self.annotations[target_id]["frame_indices"].update(new_indices)
                            self.annotations[target_id]["box"] = real_box 
                            
                            # [修复点]：必须先刷新列表，更新显示的帧范围文本
                            self.refresh_list() 
                            
                            self.select_by_id(target_id)
                            self.lbl_status.setText(f"Appended frames to ID {target_id}.")
                    else:
                        # === 新建模式 (New) ===
                        category = data["category"]
                        caption = data["caption"]
                        self.config.add_category(category)
                        
                        new_id = max(self.annotations.keys(), default=0) + 1
                        self.annotations[new_id] = {
                            "category": category, 
                            "caption": caption, 
                            "box": real_box,
                            "frame_indices": new_indices
                        }
                        self.refresh_list()
                        self.select_by_id(new_id)
                        self.lbl_status.setText(f"Created New Event {new_id}.")
                self.render_annotations()
                
            else:
                # === 修改模式 (Edit) ===
                if not self.current_event_id: return
                self.annotations[self.current_event_id]["box"] = real_box
                self.render_annotations()
                self.lbl_status.setText(f"Updated Box for Event {self.current_event_id}.")

    def render_annotations(self):
        to_draw = []
        for eid, data in self.annotations.items():
            if self.current_idx in data["frame_indices"]:
                rx, ry, rw, rh = data["box"]
                d = self.downsample_ratio
                rect = QRectF(rx*d, ry*d, rw*d, rh*d)
                is_sel = (eid == self.current_event_id)
                to_draw.append((rect, self.get_color(eid), f"ID {eid}: {data['category']}", is_sel))
        self.canvas.set_annotations(to_draw)

    # === 保存逻辑 ===
    def save_all(self):
        if not self.image_paths: return
        folder = Path(self.image_paths[0]).parent
        
        for eid, data in self.annotations.items():
            if not data.get("caption", "").strip():
                QMessageBox.warning(self, "Error", f"Event ID {eid} missing caption!")
                return

        final_json = {}
        for eid, data in self.annotations.items():
            frames_list = []
            sorted_indices = sorted(list(data["frame_indices"]))
            
            for idx in sorted_indices:
                if 0 <= idx < len(self.image_paths):
                    fname = Path(self.image_paths[idx]).name
                    quality = "poor" if fname in self.quality_flags else "good"
                    frames_list.append({
                        "filename": fname,
                        "quality": quality
                    })
            
            final_json[eid] = {
                "category": data["category"],
                "caption": data["caption"],
                "box": data["box"],
                "frames": frames_list
            }
            
        with open(folder / "annotations.json", 'w', encoding='utf-8') as f:
            json.dump(final_json, f, indent=4, ensure_ascii=False)
            
        QMessageBox.information(self, "Saved", f"Data saved to:\n{folder}/annotations.json")

    # === 右键菜单 ===
    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        eid = int(item.text().split(":")[0].replace("ID ", ""))
        
        menu = QMenu()
        
        act_remove = QAction("❌ Remove Box from Current Frame", self)
        act_remove.triggered.connect(lambda: self.remove_box_on_current(eid))
        menu.addAction(act_remove)
        
        menu.addSeparator()
        
        act_start = QAction("⚡ Set Current as START", self)
        act_start.triggered.connect(lambda: self.set_frame_as_start(eid))
        menu.addAction(act_start)
        
        act_end = QAction("⚡ Set Current as END", self)
        act_end.triggered.connect(lambda: self.trim_event_after(eid))
        menu.addAction(act_end)
        
        menu.addSeparator()
        act_del = QAction("🗑️ Delete Event Completely", self)
        act_del.triggered.connect(lambda: self.delete_event(eid))
        menu.addAction(act_del)
        
        menu.exec(self.list_widget.mapToGlobal(pos))

    def remove_box_on_current(self, eid):
        if eid in self.annotations:
            indices = self.annotations[eid]["frame_indices"]
            if self.current_idx in indices:
                indices.remove(self.current_idx)
                self.refresh_list()
                self.render_annotations()
                self.lbl_status.setText(f"Removed frame {self.current_idx+1} from Event {eid}.")

    def trim_event_after(self, eid):
        if eid not in self.annotations: return
        frames = self.annotations[eid]["frame_indices"]
        current = self.current_idx
        
        # 自动补全中间
        indices = sorted(list(frames))
        valid_prev = [i for i in indices if i < current]
        if valid_prev:
            last_valid = valid_prev[-1]
            for i in range(last_valid + 1, current + 1):
                frames.add(i)
        
        # 删除后面
        to_remove = [i for i in list(frames) if i > current]
        for i in to_remove: frames.remove(i)
            
        self.refresh_list()
        self.render_annotations()
        self.lbl_status.setText(f"Event {eid} ended at frame {self.current_idx+1}.")

    def set_frame_as_start(self, eid):
        if eid not in self.annotations: return
        frames = self.annotations[eid]["frame_indices"]
        current = self.current_idx
        
        indices = sorted(list(frames))
        if not indices: return
        old_start = indices[0]
        
        if current < old_start:
            for i in range(current, old_start): frames.add(i)
            msg = f"Extended START to frame {current+1}."
        elif current > old_start:
            to_remove = [i for i in list(frames) if i < current]
            for i in to_remove: frames.remove(i)
            msg = f"Trimmed START to frame {current+1}."
        else:
            msg = "No change."

        self.refresh_list()
        self.render_annotations()
        self.lbl_status.setText(msg)

    # === 基础功能 ===
    def rect_to_real(self, rect):
        x = rect.x() / self.downsample_ratio
        y = rect.y() / self.downsample_ratio
        w = rect.width() / self.downsample_ratio
        h = rect.height() / self.downsample_ratio
        return [x, y, w, h]

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder: return
        exts = ['*.tif', '*.tiff', '*.png', '*.jpg', '*.jpeg']
        files = []
        for ext in exts: 
            files.extend(list(Path(folder).glob(ext)))
            files.extend(list(Path(folder).glob(ext.upper())))
        files = list(set([str(f) for f in files]))
        if not files: return

        # 正则排序
        def extract_date(filename):
            match = re.search(r'(\d{4})[-_](\d{2})[-_](\d{2})', Path(filename).name)
            return (int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else (9999, 99, 99)

        try: self.image_paths = sorted(files, key=extract_date)
        except: self.image_paths = sorted(files)
        
        self.image_map = {Path(p).name: i for i, p in enumerate(self.image_paths)}
        self.load_annotations(folder)
        self.setup_frame_bar()
        self.current_idx = 0
        self.load_image()

    def load_annotations(self, folder):
        path = Path(folder) / "annotations.json"
        self.annotations = {}
        self.quality_flags = {}
        
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f: raw = json.load(f)
                for eid_str, dat in raw.items():
                    eid = int(eid_str)
                    
                    idx_set = set()
                    frames_list = dat.get("frames", [])
                    
                    if isinstance(frames_list, dict): # 兼容旧版
                        for fname in frames_list.keys():
                            if fname in self.image_map: idx_set.add(self.image_map[fname])
                        box = list(frames_list.values())[0] if frames_list else [0,0,0,0]
                    else:
                        for item in frames_list:
                            fname = item["filename"]
                            if item.get("quality") == "poor": self.quality_flags[fname] = True
                            if fname in self.image_map: idx_set.add(self.image_map[fname])
                        box = dat.get("box", [0,0,0,0])

                    self.annotations[eid] = {
                        "category": dat.get("category", "Unknown"),
                        "caption": dat.get("caption", ""),
                        "box": box,
                        "frame_indices": idx_set
                    }
                self.refresh_list()
            except Exception as e: print(f"Load Error: {e}")

    def refresh_list(self):
            self.list_widget.clear()
            
            # 辅助函数：将数字列表转换为范围字符串 (如 [0,1,2,5] -> "1-3, 6")
            def format_ranges(indices):
                if not indices: return "Empty"
                sorted_idx = sorted([i + 1 for i in indices])
                ranges = []
                if not sorted_idx: return "Empty"
                
                start = sorted_idx[0]
                prev = sorted_idx[0]
                
                for i in sorted_idx[1:]:
                    if i == prev + 1:
                        prev = i
                    else:
                        if start == prev: ranges.append(f"{start}")
                        else: ranges.append(f"{start}-{prev}")
                        start = i
                        prev = i
                
                if start == prev: ranges.append(f"{start}")
                else: ranges.append(f"{start}-{prev}")
                
                return ", ".join(ranges)

            for eid in sorted(self.annotations.keys()):
                d = self.annotations[eid]
                indices = d['frame_indices']
                cat = d.get("category", "Unk")
                
                # 1. 计算范围字符串
                range_str = format_ranges(indices)
                
                # 2. === 修复：使用纯文本，移除 HTML ===
                # 格式： ID 1: 建筑施工 [1-5, 8-10]
                plain_text = f"ID {eid}: {cat} [{range_str}]"
                
                # 3. 创建 Item 对象
                from PyQt6.QtWidgets import QListWidgetItem # 确保引用了这个
                item = QListWidgetItem(plain_text)
                
                # (可选) 如果你想让文字显眼一点，可以设置整行颜色，例如亮青色
                # item.setForeground(QColor("#00FFFF")) 
                
                self.list_widget.addItem(item)

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
            
            fname = Path(path).name
            self.lbl_info.setText(f"{fname}")
            self.lbl_size.setText(f"Size: {ow} x {oh}") # 更新大小
            
            self.btn_flag.setEnabled(True)
            self.btn_flag.setChecked(fname in self.quality_flags)
        
        self.update_frame_bar()
        self.render_annotations()
        self.pbar.setVisible(False)

    def setup_frame_bar(self):
        # 修复后的 setup_frame_bar
        while self.frame_layout.count():
            c = self.frame_layout.takeAt(0)
            if c.widget(): c.widget().deleteLater()
        self.frame_btns = []
        for i in range(len(self.image_paths)):
            btn = QPushButton(str(i+1)); btn.setFixedSize(30,30); btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, x=i: self.jump_frame(x))
            self.frame_layout.addWidget(btn); self.frame_btns.append(btn)

    def update_frame_bar(self):
        for i, b in enumerate(self.frame_btns): b.setStyleSheet("background:#007ACC;color:white" if i==self.current_idx else "background:#444;color:#aaa;border:none")
    
    def jump_frame(self, idx): 
        if idx!=self.current_idx: self.current_idx=idx; self.load_image()
    
    def keyPressEvent(self, event):
        key = event.key()
        if key in [Qt.Key.Key_Left, Qt.Key.Key_Up]: self.prev_frame()
        elif key in [Qt.Key.Key_Right, Qt.Key.Key_Down]: self.next_frame()
        else: super().keyPressEvent(event)
    def prev_frame(self): 
        if self.current_idx>0: self.jump_frame(self.current_idx-1)
    def next_frame(self): 
        if self.current_idx<len(self.image_paths)-1: self.jump_frame(self.current_idx+1)
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
                self.list_widget.setCurrentRow(i); break
        self.render_annotations()
    def delete_event(self, eid):
        if eid in self.annotations:
            del self.annotations[eid]
            if self.current_event_id == eid: self.current_event_id = None
            self.refresh_list(); self.render_annotations()
    def get_color(self, eid): return QColor.fromHsv(int((eid * 137.5) % 360), 200, 255)