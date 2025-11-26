import json
import re
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QListWidget, 
                             QInputDialog, QMessageBox, QSplitter, QMenu, 
                             QScrollArea, QProgressBar, QApplication, 
                             QListWidgetItem, QAbstractItemView)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QAction, QColor, QImage, QPixmap, QIcon, QBrush

from src.utils.image_loader import ImageLoader
from src.utils.config_manager import ConfigManager
from src.ui.canvas import AnnotationCanvas
from src.ui.batch_dialog import BatchDialog
from src.ui.category_dialog import CategoryManagerDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker V13 (Final Complete)")
        self.resize(1600, 950) 
        
        # === 数据状态 ===
        self.root_dir = None        
        self.current_folder_path = None 
        
        self.image_paths = []
        self.image_map = {} 
        self.current_idx = 0
        
        # 1. 事件数据 (内存中): { eid: {category, caption, box(xywh), frame_indices(set)} }
        self.annotations = {}
        # 2. 质量数据: { "filename.tif": "poor" / "good" }
        self.quality_map = {} 
        
        self.current_event_id = None
        
        # === 坐标计算核心 ===
        self.original_size = (1, 1) # (w, h)
        self.current_pixmap_size = (1, 1) # (w, h)
        self.downsample_ratio = 1.0 # 仅做备用
        
        self.config = ConfigManager()
        
        self.create_menu_bar()
        self.init_ui()

    def create_menu_bar(self):
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("🛠️ 设置 (Settings)")
        act_cats = QAction("管理类别 (Manage Categories)", self)
        act_cats.triggered.connect(lambda: CategoryManagerDialog(self, self.config).exec())
        settings_menu.addAction(act_cats)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # ==========================
        # === 左侧面板 (画布) ===
        # ==========================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 1. Top Bar
        top_layout = QHBoxLayout()
        self.lbl_info = QLabel("Ready.")
        self.lbl_info.setStyleSheet("font-family: monospace; font-weight: bold; font-size: 10pt;")
        
        self.btn_flag = QPushButton("🚩 标记为劣质 (Mark Poor)")
        self.btn_flag.setCheckable(True)
        self.btn_flag.setStyleSheet("""
            QPushButton { background-color: #444; color: #aaa; padding: 5px; border-radius: 3px; }
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
        
        self.lbl_size = QLabel("Size: -")
        self.lbl_size.setStyleSheet("font-family: monospace; margin-left: 20px; color: black; font-weight: bold;")
        self.lbl_coords = QLabel("Pos: -")
        self.lbl_coords.setStyleSheet("font-family: monospace; margin-left: 20px; color: black; font-weight: bold;")
        
        nav_layout.addWidget(btn_prev)
        nav_layout.addWidget(btn_next)
        nav_layout.addWidget(self.pbar)
        nav_layout.addWidget(self.lbl_size)
        nav_layout.addWidget(self.lbl_coords)
        nav_layout.addStretch()
        
        left_layout.addLayout(top_layout)
        left_layout.addWidget(self.canvas, 1)
        left_layout.addWidget(scroll)
        left_layout.addLayout(nav_layout)
        
        # ==========================
        # === 右侧面板 (控制区) ===
        # ==========================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        btn_load = QPushButton("📂 Open Root Folder")
        btn_load.setStyleSheet("padding: 10px; font-weight: bold; font-size: 11pt; background-color: #e0e0e0;")
        btn_load.clicked.connect(self.open_root_folder)
        
        # --- Splitter ---
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # A. Events List (1/3)
        w_events = QWidget()
        l_events = QVBoxLayout(w_events)
        l_events.setContentsMargins(0,0,0,0)
        l_events.addWidget(QLabel("📝 Events in Current Image:"))
        self.event_list = QListWidget()
        self.event_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.event_list.customContextMenuRequested.connect(self.show_context_menu)
        self.event_list.itemClicked.connect(self.select_event)
        self.event_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        l_events.addWidget(self.event_list)
        
        # B. Folders List (2/3)
        w_folders = QWidget()
        l_folders = QVBoxLayout(w_folders)
        l_folders.setContentsMargins(0,0,0,0)
        l_folders.addWidget(QLabel("📁 Sub-Folders / Datasets:"))
        self.folder_list = QListWidget()
        self.folder_list.setStyleSheet("""
            QListWidget { 
                background-color: #FFFFFF; 
                color: #000000; 
                font-size: 10pt; 
                border: 1px solid #ccc;
            }
            QListWidget::item { 
                padding: 5px; 
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected { 
                background-color: #007ACC; 
                color: white; 
            }
        """)
        self.folder_list.itemClicked.connect(self.change_dataset_folder)
        self.folder_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        l_folders.addWidget(self.folder_list)
        
        v_splitter.addWidget(w_events)
        v_splitter.addWidget(w_folders)
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 2)
        
        # Bottom Status
        self.lbl_status = QLabel("Status: Idle")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #E06C75; font-weight: bold;")
        
        btn_save = QPushButton("💾 Save All Data")
        btn_save.clicked.connect(self.save_all)
        btn_save.setStyleSheet("height: 40px; font-weight: bold; background-color: #007ACC; color: white;")
        
        right_layout.addWidget(btn_load)
        right_layout.addWidget(v_splitter) 
        right_layout.addWidget(self.lbl_status)
        right_layout.addWidget(btn_save)
        
        splitter = QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        
        self.frame_btns = []

    # === 1. 精准坐标计算 ===
    
    def update_status_bar(self, x, y):
        orig_w, orig_h = self.original_size
        pix_w, pix_h = self.current_pixmap_size
        if pix_w > 0:
            # 实时计算，消除累积误差
            real_x = int(x * (orig_w / pix_w))
            real_y = int(y * (orig_h / pix_h))
            self.lbl_coords.setText(f"X: {real_x}, Y: {real_y}")

    def rect_to_real(self, rect):
        """Canvas(Buffer) -> Real(xywh)"""
        orig_w, orig_h = self.original_size
        pix_w, pix_h = self.current_pixmap_size
        if pix_w == 0: return [0,0,0,0]
        
        sx = orig_w / pix_w
        sy = orig_h / pix_h
        
        return [rect.x() * sx, rect.y() * sy, rect.width() * sx, rect.height() * sy]

    def render_annotations(self):
        """Real(xywh) -> Canvas(Buffer)"""
        to_draw = []
        orig_w, orig_h = self.original_size
        pix_w, pix_h = self.current_pixmap_size
        
        if orig_w == 0: return
        inv_sx = pix_w / orig_w
        inv_sy = pix_h / orig_h
        
        for eid, data in self.annotations.items():
            if self.current_idx in data["frame_indices"]:
                rx, ry, rw, rh = data["box"]
                bx = rx * inv_sx
                by = ry * inv_sy
                bw = rw * inv_sx
                bh = rh * inv_sy
                
                rect = QRectF(bx, by, bw, bh)
                is_sel = (eid == self.current_event_id)
                to_draw.append((rect, self.get_color(eid), f"ID {eid}: {data['category']}", is_sel))
        self.canvas.set_annotations(to_draw)

    # === 2. 核心增删改逻辑 ===

    def on_geometry_changed(self, rect, is_new):
        real_box = self.rect_to_real(rect)
        
        if is_new:
            existing = {eid: {'category': d.get('category',''), 'caption': d.get('caption','')} for eid, d in self.annotations.items()}
            
            # 传入字典结构的 categories
            dlg = BatchDialog(self, self.config.categories, self.current_idx, len(self.image_paths), existing)
            
            if dlg.exec():
                data = dlg.result_data
                target_id = data["target_id"]
                end_idx = data["end_idx"]
                new_indices = set(range(self.current_idx, end_idx + 1))

                if target_id != -1:
                    # Append
                    if target_id in self.annotations:
                        self.annotations[target_id]["frame_indices"].update(new_indices)
                        self.annotations[target_id]["box"] = real_box
                        self.refresh_list()
                        self.select_by_id(target_id)
                        self.lbl_status.setText(f"Appended to ID {target_id}.")
                else:
                    # New
                    group = data["group"]
                    sub_cat = data["sub_category"]
                    caption = data["caption"]
                    
                    # 保存新类别
                    self.config.add_category(group, sub_cat)
                    
                    new_id = max(self.annotations.keys(), default=0) + 1
                    self.annotations[new_id] = {
                        "category": sub_cat, 
                        "caption": caption, 
                        "box": real_box,
                        "frame_indices": new_indices
                    }
                    self.refresh_list()
                    self.select_by_id(new_id)
                    self.lbl_status.setText(f"Created New Event {new_id}.")
            self.render_annotations()
        else:
            # Modify
            if self.current_event_id:
                self.annotations[self.current_event_id]["box"] = real_box
                self.render_annotations()
                self.lbl_status.setText(f"Updated ID {self.current_event_id}.")

    # === 3. 核心保存加载 (box_2d xyxy 支持) ===

    def save_all(self):
            if not self.image_paths: return
            folder = Path(self.image_paths[0]).parent
            
            # 1. 校验 Caption
            for eid, data in self.annotations.items():
                if not data.get("caption", "").strip():
                    QMessageBox.warning(self, "Error", f"Event ID {eid} missing caption!")
                    return

            # 2. 构建 events 字典
            events_dict = {}
            for eid, data in self.annotations.items():
                frames_indices = sorted(list(data["frame_indices"]))
                frames_names = []
                for idx in frames_indices:
                    if 0 <= idx < len(self.image_paths):
                        frames_names.append(Path(self.image_paths[idx]).name)
                
                # xywh -> xyxy
                x, y, w, h = data["box"]
                x2 = x + w
                y2 = y + h
                
                events_dict[eid] = {
                    "category": data["category"],
                    "caption": data["caption"],
                    "box_2d": [x, y, x2, y2], 
                    "involved_frames": frames_names
                }
                
            # 3. 构建 image_quality 字典
            quality_dict = {}
            for path_str in self.image_paths:
                fname = Path(path_str).name
                status = self.quality_map.get(fname, "good")
                quality_dict[fname] = status

            final_json = {
                "events": events_dict,
                "image_quality": quality_dict
            }
                
            try:
                save_path = folder / "annotations.json"
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(final_json, f, indent=4, ensure_ascii=False)
                
                # === 修改点：生成详细的报告信息 ===
                report = (f"✅ 保存成功 (Save Successful)!\n\n"
                        f"📂 路径: {save_path}\n"
                        f"----------------------------------\n"
                        f"📝 事件数量 (Events): {len(events_dict)}\n"
                        f"🖼️ 图像标记 (Images): {len(quality_dict)}\n"
                        f"📐 坐标格式: XYXY (Left-Top, Right-Bottom)")
                
                QMessageBox.information(self, "Save Report", report)
                # ======================================
                
                # 更新列表颜色
                curr_items = self.folder_list.selectedItems()
                if curr_items:
                    item = curr_items[0]
                    txt = item.text()
                    if "✅" not in txt:
                        new_txt = txt.replace("⬜", "✅")
                        item.setText(new_txt)
                        item.setForeground(QBrush(QColor("#008000")))
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))

    def load_annotations(self, folder):
        path = Path(folder) / "annotations.json"
        self.annotations = {}
        self.quality_map = {}
        
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f: raw = json.load(f)
                
                events_src = raw.get("events", {})
                self.quality_map = raw.get("image_quality", {})

                for eid_str, dat in events_src.items():
                    eid = int(eid_str)
                    idx_set = set()
                    for fname in dat.get("involved_frames", []):
                        if fname in self.image_map: idx_set.add(self.image_map[fname])
                    
                    # xyxy -> xywh
                    if "box_2d" in dat:
                        x1, y1, x2, y2 = dat["box_2d"]
                        box_xywh = [x1, y1, x2-x1, y2-y1]
                    else:
                        box_xywh = dat.get("box", [0,0,0,0])

                    self.annotations[eid] = {
                        "category": dat.get("category", "Unk"),
                        "caption": dat.get("caption", ""),
                        "box": box_xywh,
                        "frame_indices": idx_set
                    }
                self.refresh_list()
            except Exception as e: print(f"Load Error: {e}")
        else:
            self.refresh_list()

    # === 4. 数据集管理 (Folder List) ===

    def open_root_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Root Folder or Dataset")
        if not folder: return
        self.root_dir = Path(folder)
        self.folder_list.clear(); self.event_list.clear(); self.image_paths = []; self.canvas.set_image(None)
        self.lbl_info.setText("Scanning folders..."); QApplication.processEvents()
        
        if self.has_images(self.root_dir):
            self.add_folder_item(self.root_dir, is_root=True)
            self.folder_list.setCurrentRow(0); self.load_dataset(self.root_dir)
        else:
            subdirs = sorted([d for d in self.root_dir.iterdir() if d.is_dir()], key=lambda x: x.name)
            count = 0
            for d in subdirs:
                if self.has_images(d): self.add_folder_item(d); count += 1
            if count == 0: QMessageBox.warning(self, "Info", "No images found.")
            else: self.lbl_status.setText(f"Found {count} datasets.")

    def has_images(self, folder):
        for ext in ['*.tif', '*.tiff', '*.png', '*.jpg', '*.jpeg']:
            if any(folder.glob(ext)) or any(folder.glob(ext.upper())): return True
        return False

    def add_folder_item(self, path, is_root=False):
        has_json = (path / "annotations.json").exists()
        status = "✅" if has_json else "⬜"
        item = QListWidgetItem(f"{status} {path.name}")
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        item.setForeground(QBrush(QColor("#008000") if has_json else QColor("#555555")))
        self.folder_list.addItem(item)

    def change_dataset_folder(self, item):
        path_str = item.data(Qt.ItemDataRole.UserRole)
        if path_str and Path(path_str) != self.current_folder_path: self.load_dataset(Path(path_str))

    def load_dataset(self, folder_path):
        self.current_folder_path = folder_path
        self.lbl_status.setText(f"Loading: {folder_path.name}...")
        QApplication.processEvents()
        self.load_images_from_dir(folder_path)

    def load_images_from_dir(self, folder):
        exts = ['*.tif', '*.tiff', '*.png', '*.jpg', '*.jpeg']
        files = []
        for ext in exts: files.extend(list(folder.glob(ext))); files.extend(list(folder.glob(ext.upper())))
        files = list(set([str(f) for f in files]))
        def extract_date(filename):
            match = re.search(r'(\d{4})[-_](\d{2})[-_](\d{2})', Path(filename).name)
            return (int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else (9999, 99, 99)
        try: self.image_paths = sorted(files, key=extract_date)
        except: self.image_paths = sorted(files)
        self.image_map = {Path(p).name: i for i, p in enumerate(self.image_paths)}
        
        self.load_annotations(folder)
        
        self.setup_frame_bar(); self.current_idx = 0; self.load_image()
        self.lbl_status.setText(f"Loaded {folder.name}")

    # === 5. 辅助功能 ===

    def load_image(self):
        if not self.image_paths: return
        self.pbar.setVisible(True); QApplication.processEvents()
        path = self.image_paths[self.current_idx]
        img_data, _, (ow, oh) = ImageLoader.load(path)
        if img_data is not None:
            h, w, c = img_data.shape
            self.original_size = (ow, oh)
            self.current_pixmap_size = (w, h)
            q_img = QImage(img_data.tobytes(), w, h, 3*w, QImage.Format.Format_RGB888)
            self.canvas.set_image(QPixmap.fromImage(q_img))
            if self.canvas.view_scale == 1.0: self.canvas.reset_view()
            
            fname = Path(path).name
            self.lbl_info.setText(f"{fname}")
            self.lbl_size.setText(f"Size: {ow} x {oh}")
            self.btn_flag.setEnabled(True)
            self.btn_flag.setChecked(self.quality_map.get(fname, "good") == "poor")
        self.update_frame_bar(); self.render_annotations(); self.pbar.setVisible(False)

    def toggle_quality_flag(self):
        if not self.image_paths: return
        fname = Path(self.image_paths[self.current_idx]).name
        if self.btn_flag.isChecked():
            self.quality_map[fname] = "poor"
            self.lbl_status.setText(f"Marked {fname} as POOR.")
        else:
            self.quality_map[fname] = "good"
            self.lbl_status.setText(f"Marked {fname} as GOOD.")

    def refresh_list(self):
        self.event_list.clear()
        def format_ranges(indices):
            if not indices: return "Empty"
            sorted_idx = sorted([i + 1 for i in indices])
            ranges = []; start = prev = sorted_idx[0]
            for i in sorted_idx[1:]:
                if i == prev + 1: prev = i
                else:
                    ranges.append(f"{start}" if start == prev else f"{start}-{prev}"); start = prev = i
            ranges.append(f"{start}" if start == prev else f"{start}-{prev}")
            return ", ".join(ranges)
        for eid in sorted(self.annotations.keys()):
            d = self.annotations[eid]; rng = format_ranges(d['frame_indices']); cat = d.get("category", "Unk")
            item = QListWidgetItem(f"ID {eid}: {cat} [{rng}]")
            self.event_list.addItem(item)

    def show_context_menu(self, pos):
        item = self.event_list.itemAt(pos)
        if not item: return
        eid = int(item.text().split(":")[0].replace("ID ", ""))
        menu = QMenu()
        menu.addAction("❌ Remove Box from Current Frame", lambda: self.remove_box_on_current(eid))
        menu.addSeparator()
        menu.addAction("⚡ Set Current as START", lambda: self.set_frame_as_start(eid))
        menu.addAction("⚡ Set Current as END", lambda: self.trim_event_after(eid))
        menu.addSeparator()
        menu.addAction("🗑️ Delete Event Completely", lambda: self.delete_event(eid))
        menu.exec(self.event_list.mapToGlobal(pos))

    def remove_box_on_current(self, eid):
        if eid in self.annotations:
            if self.current_idx in self.annotations[eid]["frame_indices"]:
                self.annotations[eid]["frame_indices"].remove(self.current_idx)
                self.refresh_list(); self.render_annotations()

    def trim_event_after(self, eid):
        if eid not in self.annotations: return
        frames = self.annotations[eid]["frame_indices"]; current = self.current_idx
        indices = sorted(list(frames))
        valid_prev = [i for i in indices if i < current]
        if valid_prev:
            for i in range(valid_prev[-1] + 1, current + 1): frames.add(i)
        to_remove = [i for i in list(frames) if i > current]
        for i in to_remove: frames.remove(i)
        self.refresh_list(); self.render_annotations()

    def set_frame_as_start(self, eid):
        if eid not in self.annotations: return
        frames = self.annotations[eid]["frame_indices"]; current = self.current_idx
        indices = sorted(list(frames))
        if not indices: return
        old_start = indices[0]
        if current < old_start:
            for i in range(current, old_start): frames.add(i)
        elif current > old_start:
            to_remove = [i for i in list(frames) if i < current]
            for i in to_remove: frames.remove(i)
        self.refresh_list(); self.render_annotations()

    def delete_event(self, eid):
        if eid in self.annotations: del self.annotations[eid]; self.current_event_id = None; self.refresh_list(); self.render_annotations()

    def select_event(self, item):
        try: eid = int(item.text().split(":")[0].replace("ID ", "")); self.current_event_id = eid; self.render_annotations()
        except: pass
    def select_by_id(self, eid):
        self.current_event_id = eid
        for i in range(self.event_list.count()):
            if self.event_list.item(i).text().startswith(f"ID {eid}:"): self.event_list.setCurrentRow(i); break
        self.render_annotations()
    def get_color(self, eid): return QColor.fromHsv(int((eid * 137.5) % 360), 200, 255)
    def setup_frame_bar(self):
            # 1. 清空旧布局 (标准写法，安全可靠)
            while self.frame_layout.count():
                child = self.frame_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # 2. 重新生成按钮
            self.frame_btns = []
            for i in range(len(self.image_paths)):
                btn = QPushButton(str(i+1))
                btn.setFixedSize(30, 30)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                # 注意 lambda 闭包
                btn.clicked.connect(lambda _, x=i: self.jump_frame(x))
                self.frame_layout.addWidget(btn)
                self.frame_btns.append(btn)
    def update_frame_bar(self):
        for i, b in enumerate(self.frame_btns): b.setStyleSheet("background:#007ACC;color:white" if i==self.current_idx else "background:#444;color:#aaa;border:none")
    def jump_frame(self, idx): 
        if idx!=self.current_idx: self.current_idx=idx; self.load_image()
    def prev_frame(self): 
        if self.current_idx>0: self.jump_frame(self.current_idx-1)
    def next_frame(self): 
        if self.current_idx<len(self.image_paths)-1: self.jump_frame(self.current_idx+1)
    def keyPressEvent(self, event):
        if event.key() in [Qt.Key.Key_Left, Qt.Key.Key_Up]: self.prev_frame()
        elif event.key() in [Qt.Key.Key_Right, Qt.Key.Key_Down]: self.next_frame()
        else: super().keyPressEvent(event)