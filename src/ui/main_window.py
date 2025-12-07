import json
import re
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QListWidget, 
                             QInputDialog, QMessageBox, QSplitter, QMenu, 
                             QScrollArea, QProgressBar, QApplication, 
                             QListWidgetItem, QAbstractItemView, QGroupBox, 
                             QRadioButton, QButtonGroup, QComboBox)
from PyQt6.QtCore import Qt, QRectF, QTime
from PyQt6.QtGui import QAction, QColor, QImage, QPixmap, QIcon, QBrush

from src.utils.image_loader import ImageLoader
from src.utils.config_manager import ConfigManager
from src.ui.canvas import AnnotationCanvas
from src.ui.batch_dialog import BatchDialog
from src.ui.category_dialog import CategoryManagerDialog
from src.ui.edit_dialog import EditEventDialog  # <--- 新增
from PyQt6.QtGui import QKeySequence, QShortcut # 增加 QKeySequence, QShortcut

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker")
        self.resize(1600, 950) 
        
        # === 数据状态 ===
        self.root_dir = None        
        self.current_folder_path = None 
        
        self.image_paths = []
        self.image_map = {} 
        self.current_idx = 0
        
        # 1. 事件数据 (内存中)
        self.annotations = {}
        # 2. 质量数据
        self.quality_map = {} 
        
        self.current_event_id = None
        
        # === 坐标计算核心 ===
        self.original_size = (1, 1) # (w, h)
        self.current_pixmap_size = (1, 1) # (w, h)
        self.downsample_ratio = 1.0
        
        self.config = ConfigManager()

        # 加载错误原因配置
        self.error_reasons = self.load_error_config()
        
        self.create_menu_bar()
        self.init_ui()
        self.setup_shortcuts()

    def setup_shortcuts(self):
        # 上一张：左箭头 或 上箭头
        QShortcut(QKeySequence(Qt.Key.Key_Left), self).activated.connect(self.prev_frame)
        QShortcut(QKeySequence(Qt.Key.Key_Up), self).activated.connect(self.prev_frame)
        
        # 下一张：右箭头 或 下箭头
        QShortcut(QKeySequence(Qt.Key.Key_Right), self).activated.connect(self.next_frame)
        QShortcut(QKeySequence(Qt.Key.Key_Down), self).activated.connect(self.next_frame)


    def load_error_config(self):
        """读取 config/error_reasons.json"""
        try:
            base_dir = Path(__file__).resolve().parent.parent.parent
            config_path = base_dir / "config" / "error_reasons.json"
            
            default_reasons = ["框不贴合 (Box Loose)", "类别错误 (Wrong Label)", "遮挡严重 (Occluded)", "其他 (Other)"]
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("reasons", default_reasons)
            return default_reasons
        except Exception:
            return ["框不贴合", "类别错误", "其他"]

    def create_menu_bar(self):
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("🛠️ 设置 (Settings)")
        act_cats = QAction("管理类别 (Manage Categories)", self)
        act_cats.triggered.connect(lambda: CategoryManagerDialog(self, self.config).exec())
        settings_menu.addAction(act_cats)

    

    # === [关键逻辑] 质量评价与自动保存 ===

    def update_qc_ui_from_data(self, eid):
        """根据当前选中的 Event ID 更新评价面板 UI"""
        if eid not in self.annotations:
            self.qc_group.setEnabled(False)
            return
            
        self.qc_group.setEnabled(True)
        data = self.annotations[eid]
        
        status = data.get("quality_status", "good")
        reason = data.get("reject_reason", "")
        
        self.rb_good.blockSignals(True)
        self.rb_bad.blockSignals(True)
        self.combo_reason.blockSignals(True)
        
        if status == "bad":
            self.rb_bad.setChecked(True)
            self.combo_reason.setEnabled(True)
            idx = self.combo_reason.findText(reason)
            if idx != -1:
                self.combo_reason.setCurrentIndex(idx)
            else:
                if reason:
                    self.combo_reason.addItem(reason)
                    self.combo_reason.setCurrentText(reason)
        else:
            self.rb_good.setChecked(True)
            self.combo_reason.setEnabled(False)
            
        self.rb_good.blockSignals(False)
        self.rb_bad.blockSignals(False)
        self.combo_reason.blockSignals(False)

    def on_qc_changed(self):
        """Good/Bad 切换时触发"""
        if not self.current_event_id or self.current_event_id not in self.annotations:
            return
            
        is_bad = self.rb_bad.isChecked()
        self.combo_reason.setEnabled(is_bad)
        
        # 更新数据
        self.annotations[self.current_event_id]["quality_status"] = "bad" if is_bad else "good"
        if is_bad:
            self.annotations[self.current_event_id]["reject_reason"] = self.combo_reason.currentText()
        else:
            self.annotations[self.current_event_id]["reject_reason"] = None
        
        # 1. 强制刷新列表 (更新红色的❌)
        self.refresh_list()
        # 2. 保持选中状态
        self.select_by_id(self.current_event_id)
        # 3. 自动保存
        self.save_all(silent=True) 

    def on_reason_changed(self, text):
        """原因修改 -> 自动保存"""
        if self.current_event_id and self.rb_bad.isChecked():
            self.annotations[self.current_event_id]["reject_reason"] = text
            self.save_all(silent=True)

    # === 1. 精准坐标计算 ===
    
    def update_status_bar(self, x, y):
        orig_w, orig_h = self.original_size
        pix_w, pix_h = self.current_pixmap_size
        if pix_w > 0:
            real_x = int(x * (orig_w / pix_w))
            real_y = int(y * (orig_h / pix_h))
            self.lbl_coords.setText(f"X: {real_x}, Y: {real_y}")

    def rect_to_real(self, rect):
        orig_w, orig_h = self.original_size
        pix_w, pix_h = self.current_pixmap_size
        if pix_w == 0: return [0,0,0,0]
        sx = orig_w / pix_w
        sy = orig_h / pix_h
        return [rect.x() * sx, rect.y() * sy, rect.width() * sx, rect.height() * sy]

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
        
        # === 修改点 1: 连接点击选中信号 ===
        self.canvas.event_selected.connect(self.select_by_id) 
        # ================================
        
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
        
        # A. Events List
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
        
        # B. Folders List
        w_folders = QWidget()
        l_folders = QVBoxLayout(w_folders)
        l_folders.setContentsMargins(0,0,0,0)
        l_folders.addWidget(QLabel("📁 Sub-Folders / Datasets:"))
        self.folder_list = QListWidget()
        self.folder_list.setStyleSheet("""
            QListWidget { background-color: #FFFFFF; color: #000000; font-size: 10pt; border: 1px solid #ccc; }
            QListWidget::item { padding: 5px; border-bottom: 1px solid #eee; }
            QListWidget::item:selected { background-color: #007ACC; color: white; }
        """)
        self.folder_list.itemClicked.connect(self.change_dataset_folder)
        self.folder_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        l_folders.addWidget(self.folder_list)
        
        v_splitter.addWidget(w_events)
        v_splitter.addWidget(w_folders)
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 2)
        
        right_layout.addWidget(btn_load)
        right_layout.addWidget(v_splitter) 

        # ==================== 质量评价面板 ====================
        self.qc_group = QGroupBox("选中事件评价 (Event Quality)")
        self.qc_group.setEnabled(False)
        self.qc_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid gray; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        
        qc_layout = QVBoxLayout(self.qc_group)
        qc_layout.setSpacing(5)
        
        # 单选按钮
        rb_layout = QHBoxLayout()
        self.rb_good = QRadioButton("✅ 合格 (Good)")
        self.rb_bad = QRadioButton("❌ 劣质 (Bad)")
        self.rb_good.setChecked(True)
        
        self.qc_btn_group = QButtonGroup(self)
        self.qc_btn_group.addButton(self.rb_good)
        self.qc_btn_group.addButton(self.rb_bad)
        
        rb_layout.addWidget(self.rb_good)
        rb_layout.addWidget(self.rb_bad)
        qc_layout.addLayout(rb_layout)
        
        # 原因选择
        qc_layout.addWidget(QLabel("劣质原因 (Reason):"))
        self.combo_reason = QComboBox()
        self.combo_reason.addItems(self.error_reasons)
        self.combo_reason.setEnabled(False)
        qc_layout.addWidget(self.combo_reason)
        
        # 连接信号
        self.rb_good.toggled.connect(self.on_qc_changed)
        self.rb_bad.toggled.connect(self.on_qc_changed)
        self.combo_reason.currentTextChanged.connect(self.on_reason_changed)
        
        right_layout.addWidget(self.qc_group)
        # ==========================================================

        # Bottom Status
        self.lbl_status = QLabel("Status: Idle")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #E06C75; font-weight: bold;")
        
        btn_save = QPushButton("💾 Save All Data (Manual)")
        btn_save.clicked.connect(lambda: self.save_all(silent=False))
        btn_save.setStyleSheet("height: 40px; font-weight: bold; background-color: #007ACC; color: white;")
        
        right_layout.addWidget(self.lbl_status)
        right_layout.addWidget(btn_save)
        
        splitter = QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        
        self.frame_btns = []

    def render_annotations(self):
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
                label = f"ID {eid}: {data['category']}"
                if data.get("quality_status") == "bad":
                    label += " (BAD)"
                    
                # === 修改点 2: 传递 eid 给画布，用于点击识别 ===
                # 结构: (rect, color, label, is_sel, eid)
                to_draw.append((rect, self.get_color(eid), label, is_sel, eid))
                # ============================================
                
        self.canvas.set_annotations(to_draw)

    # === 2. 核心增删改逻辑 (含自动保存) ===

    def on_geometry_changed(self, rect, is_new):
        # 1. 坐标修正（防止负数或超出）
        real_box = self.rect_to_real(rect)
        rx, ry, rw, rh = real_box
        orig_w, orig_h = self.original_size
        
        # 限制坐标在图片范围内 (Clamp)
        x1 = max(0, min(rx, orig_w))
        y1 = max(0, min(ry, orig_h))
        x2 = max(0, min(rx + rw, orig_w))
        y2 = max(0, min(ry + rh, orig_h))
        
        # 更新修正后的 box
        real_box = [x1, y1, x2 - x1, y2 - y1]
        
        # 如果框太小（无效框），直接重绘并退出
        if real_box[2] < 1 or real_box[3] < 1:
            self.render_annotations()
            return

        if is_new:
            # 准备数据给弹窗
            existing = {eid: {'category': d.get('category',''), 'caption': d.get('caption','')} 
                        for eid, d in self.annotations.items()}
            
            dlg = BatchDialog(self, self.config.categories, self.current_idx, len(self.image_paths), existing)
            
            # === 只有点击了 OK (dlg.exec() 为 True) 才执行下面的逻辑 ===
            if dlg.exec():
                data = dlg.result_data
                # 确保在这里定义 target_id
                target_id = data["target_id"] 
                end_idx = data["end_idx"]
                new_indices = set(range(self.current_idx, end_idx + 1))

                if target_id != -1:
                    # 追加到已有事件 (Append)
                    if target_id in self.annotations:
                        self.annotations[target_id]["frame_indices"].update(new_indices)
                        self.annotations[target_id]["box"] = real_box # 使用修正后的 box
                        self.refresh_list()
                        self.select_by_id(target_id)
                        self.lbl_status.setText(f"Appended to ID {target_id}.")
                else:
                    # 创建新事件 (New)
                    group = data["group"]
                    sub_cat = data["sub_category"]
                    caption = data["caption"]
                    
                    self.config.add_category(group, sub_cat)
                    
                    new_id = max(self.annotations.keys(), default=0) + 1
                    self.annotations[new_id] = {
                        "category": sub_cat, 
                        "caption": caption, 
                        "box": real_box, # 使用修正后的 box
                        "frame_indices": new_indices,
                        "quality_status": "good",
                        "reject_reason": None
                    }
                    self.refresh_list()
                    self.select_by_id(new_id)
                    self.lbl_status.setText(f"Created New Event {new_id}.")
                
                # 只有数据改变了才保存
                self.save_all(silent=True)
            
            # 无论是否取消，都需要重绘（如果取消，要清除刚才画的临时框）
            self.render_annotations()
            
        else:
            # 修改已有框 (Modify)
            if self.current_event_id:
                self.annotations[self.current_event_id]["box"] = real_box # 使用修正后的 box
                self.render_annotations()
                self.lbl_status.setText(f"Updated ID {self.current_event_id}.")
                self.save_all(silent=True)

    # === 3. 核心保存加载 (含 Silent 模式) ===

    def save_all(self, silent=False):
        """
        :param silent: True=自动保存(不弹窗), False=手动保存(弹窗)
        """
        if not self.image_paths: return
        folder = Path(self.image_paths[0]).parent
        
        # === 修改点 1: 获取文件夹名称作为 JSON 文件名 ===
        json_filename = f"{folder.name}.json"
        save_path = folder / json_filename
        # ============================================
        
        # 1. 校验 (自动保存时不阻断，只打印)
        for eid, data in self.annotations.items():
            if not data.get("caption", "").strip():
                if not silent:
                    QMessageBox.warning(self, "Error", f"Event ID {eid} missing caption!")
                else:
                    print(f"[Auto-Save] Skipped: Event ID {eid} missing caption")
                return

        # 2. 构建 events 字典
        events_dict = {}
        for eid, data in self.annotations.items():
            frames_indices = sorted(list(data["frame_indices"]))
            frames_names = []
            for idx in frames_indices:
                if 0 <= idx < len(self.image_paths):
                    frames_names.append(Path(self.image_paths[idx]).name)
            
            x, y, w, h = data["box"]
            x2 = x + w
            y2 = y + h
            
            events_dict[eid] = {
                "category": data["category"],
                "caption": data["caption"],
                "box_2d": [x, y, x2, y2], 
                "involved_frames": frames_names,
                "quality_status": data.get("quality_status", "good"),
                "reject_reason": data.get("reject_reason", None)
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
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(final_json, f, indent=4, ensure_ascii=False)
            
            if not silent:
                report = (f"✅ 保存成功!\n\n"
                        f"📂 文件: {json_filename}\n"
                        f"📝 事件数量: {len(events_dict)}")
                QMessageBox.information(self, "Save Report", report)
            else:
                # 状态栏闪烁提示
                t_str = QTime.currentTime().toString("HH:mm:ss")
                self.lbl_status.setText(f"💾 Auto-saved to {json_filename} at {t_str}")

            # 更新列表文件夹颜色
            curr_items = self.folder_list.selectedItems()
            if curr_items:
                item = curr_items[0]
                txt = item.text()
                if "✅" not in txt:
                    new_txt = txt.replace("⬜", "✅")
                    item.setText(new_txt)
                    item.setForeground(QBrush(QColor("#008000")))
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Save Error", str(e))
            else:
                print(f"[Auto-Save] Failed: {e}")

    def load_annotations(self, folder):
        folder_path = Path(folder)
        
        # === 修改点 2: 优先读取 {folder}.json，兼容 annotations.json ===
        target_path = folder_path / f"{folder_path.name}.json"
        legacy_path = folder_path / "annotations.json"
        
        load_path = None
        if target_path.exists():
            load_path = target_path
        elif legacy_path.exists():
            load_path = legacy_path
            print(f"Warning: Loaded legacy file 'annotations.json'. Next save will convert to '{folder_path.name}.json'.")
        # ==========================================================

        self.annotations = {}
        self.quality_map = {}
        
        if load_path and load_path.exists():
            try:
                with open(load_path, 'r', encoding='utf-8') as f: 
                    raw = json.load(f)
                
                events_src = raw.get("events", {})
                self.quality_map = raw.get("image_quality", {})

                for eid_str, dat in events_src.items():
                    eid = int(eid_str)
                    idx_set = set()
                    for fname in dat.get("involved_frames", []):
                        if fname in self.image_map: idx_set.add(self.image_map[fname])
                    
                    if "box_2d" in dat:
                        x1, y1, x2, y2 = dat["box_2d"]
                        box_xywh = [x1, y1, x2-x1, y2-y1]
                    else:
                        box_xywh = dat.get("box", [0,0,0,0])

                    self.annotations[eid] = {
                        "category": dat.get("category", "Unk"),
                        "caption": dat.get("caption", ""),
                        "box": box_xywh,
                        "frame_indices": idx_set,
                        "quality_status": dat.get("quality_status", "good"),
                        "reject_reason": dat.get("reject_reason", None)
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
        path = Path(path)
        
        # === 修改点 3: 检查两种文件是否存在 ===
        new_json = path / f"{path.name}.json"
        old_json = path / "annotations.json"
        has_json = new_json.exists() or old_json.exists()
        # ==================================
        
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

    # === 5. 辅助功能 (含自动保存) ===

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
        # [自动保存]
        self.save_all(silent=True)

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
            
            display_text = f"ID {eid}: {cat} [{rng}]"
            # 如果是 bad，增加标记
            if d.get("quality_status") == "bad":
                display_text += " ❌"
                
            item = QListWidgetItem(display_text)
            # 如果是 bad，标红
            if d.get("quality_status") == "bad":
                item.setForeground(QBrush(QColor("red")))
                
            self.event_list.addItem(item)

    def show_context_menu(self, pos):
        item = self.event_list.itemAt(pos)
        if not item: return
        eid = int(item.text().split(":")[0].replace("ID ", ""))
        menu = QMenu()
        act_edit = QAction("✏️ Edit Event Info (Category/Caption)", self)
        act_edit.triggered.connect(lambda: self.edit_event_info(eid))
        menu.addAction(act_edit)
        menu.addSeparator()

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
                self.save_all(silent=True) # [自动保存]

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
        self.save_all(silent=True) # [自动保存]

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
        self.save_all(silent=True) # [自动保存]

    def delete_event(self, eid):
        if eid in self.annotations: 
            del self.annotations[eid]
            self.current_event_id = None
            self.qc_group.setEnabled(False) 
            self.refresh_list(); self.render_annotations()
            self.save_all(silent=True) # [自动保存]

    def select_event(self, item):
        try: 
            eid = int(item.text().split(":")[0].replace("ID ", ""))
            self.current_event_id = eid
            self.render_annotations()
            self.update_qc_ui_from_data(eid)
        except: pass

    def select_by_id(self, eid):
        self.current_event_id = eid
        for i in range(self.event_list.count()):
            if self.event_list.item(i).text().startswith(f"ID {eid}:"): 
                self.event_list.setCurrentRow(i); break
        self.render_annotations()
        self.update_qc_ui_from_data(eid)

    def get_color(self, eid): return QColor.fromHsv(int((eid * 137.5) % 360), 200, 255)
    
    def setup_frame_bar(self):
            while self.frame_layout.count():
                child = self.frame_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.frame_btns = []
            for i in range(len(self.image_paths)):
                btn = QPushButton(str(i+1))
                btn.setFixedSize(30, 30)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
    # def keyPressEvent(self, event):
    #     if event.key() in [Qt.Key.Key_Left, Qt.Key.Key_Up]: self.prev_frame()
    #     elif event.key() in [Qt.Key.Key_Right, Qt.Key.Key_Down]: self.next_frame()
    #     else: super().keyPressEvent(event)
    def edit_event_info(self, eid):
        """编辑已有事件的属性"""
        if eid not in self.annotations: return
        
        data = self.annotations[eid]
        old_cat = data.get("category", "")
        old_cap = data.get("caption", "")
        
        # 弹出编辑对话框
        dlg = EditEventDialog(self, self.config.categories, old_cat, old_cap)
        if dlg.exec():
            res = dlg.result_data
            new_group = res["group"]
            new_cat = res["category"]
            new_cap = res["caption"]
            
            # 1. 更新内存数据
            self.annotations[eid]["category"] = new_cat
            self.annotations[eid]["caption"] = new_cap
            
            # 2. 如果是新类别，保存到配置
            self.config.add_category(new_group, new_cat)
            
            # 3. 刷新界面
            self.refresh_list()
            self.lbl_status.setText(f"Updated info for Event {eid}.")