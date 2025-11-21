import json
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QListWidget, 
                             QInputDialog, QMessageBox, QSplitter, QMenu, 
                             QScrollArea, QProgressBar)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QAction, QColor, QImage, QPixmap

from src.utils.image_loader import ImageLoader
from src.ui.canvas import AnnotationCanvas

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RS-Tracker Pro (Geospatial & Generic)")
        self.resize(1400, 900)
        
        # Data
        self.image_paths = []
        self.image_map = {} # filename -> index
        self.current_idx = 0
        self.annotations = {}
        self.current_event_id = None
        self.downsample_ratio = 1.0
        
        self.init_ui()
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # === Left: Canvas Area ===
        left_layout = QVBoxLayout()
        
        # Top Bar
        top_layout = QHBoxLayout()
        self.lbl_info = QLabel("Ready")
        self.lbl_info.setStyleSheet("color: #aaa; font-family: monospace;")
        btn_fit = QPushButton("Fit View")
        btn_fit.clicked.connect(lambda: self.canvas.reset_view())
        top_layout.addWidget(self.lbl_info)
        top_layout.addStretch()
        top_layout.addWidget(btn_fit)
        
        # Canvas
        self.canvas = AnnotationCanvas()
        self.canvas.box_created.connect(self.on_box_created)
        
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
        self.pbar = QProgressBar()
        self.pbar.setFixedWidth(100)
        self.pbar.setVisible(False)
        
        nav_layout.addWidget(btn_prev)
        nav_layout.addWidget(btn_next)
        nav_layout.addWidget(self.pbar)
        nav_layout.addStretch()
        
        left_layout.addLayout(top_layout)
        left_layout.addWidget(self.canvas, 1)
        left_layout.addWidget(scroll)
        left_layout.addLayout(nav_layout)
        
        # === Right: Control Panel ===
        right_layout = QVBoxLayout()
        
        btn_load = QPushButton("Open Folder")
        btn_load.clicked.connect(self.load_folder)
        btn_load.setStyleSheet("padding: 8px; font-weight: bold;")
        
        btn_add = QPushButton("New Event")
        btn_add.setStyleSheet("background-color: #007ACC; color: white;")
        btn_add.clicked.connect(self.add_event)
        
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.select_event)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        self.lbl_status = QLabel("No Selection")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #E06C75; font-weight: bold;")
        
        btn_save = QPushButton("Save JSON")
        btn_save.clicked.connect(self.save_json)
        btn_save.setStyleSheet("height: 40px; font-weight: bold;")
        
        right_layout.addWidget(btn_load)
        right_layout.addWidget(QLabel("Events:"))
        right_layout.addWidget(self.list_widget)
        right_layout.addWidget(btn_add)
        right_layout.addWidget(self.lbl_status)
        right_layout.addStretch()
        right_layout.addWidget(btn_save)
        
        # Splitter
        splitter = QSplitter()
        w_l = QWidget(); w_l.setLayout(left_layout)
        w_r = QWidget(); w_r.setLayout(right_layout)
        splitter.addWidget(w_l)
        splitter.addWidget(w_r)
        splitter.setStretchFactor(0, 4)
        layout.addWidget(splitter)
        
        self.frame_btns = []

    # === Logic ===
    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder: return
        
        # 支持更多格式
        exts = ['*.tif', '*.tiff', '*.png', '*.jpg', '*.jpeg', '*.bmp']
        files = []
        for ext in exts:
            files.extend(list(Path(folder).glob(ext)))
            # 兼容大小写
            files.extend(list(Path(folder).glob(ext.upper())))
            
        self.image_paths = sorted(list(set([str(f) for f in files]))) # 去重并排序
        if not self.image_paths: return
        
        self.image_map = {Path(p).name: i for i, p in enumerate(self.image_paths)}
        self.load_annotations(folder)
        self.setup_frame_bar()
        self.current_idx = 0
        self.load_image()

    def load_image(self):
        if not self.image_paths: return
        self.pbar.setVisible(True)
        path = self.image_paths[self.current_idx]
        
        # Use ImageLoader
        img_data, scale, (orig_w, orig_h) = ImageLoader.load(path)
        
        if img_data is not None:
            self.downsample_ratio = scale
            h, w, c = img_data.shape
            bytes_per_line = 3 * w
            q_img = QImage(img_data.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.canvas.set_image(QPixmap.fromImage(q_img))
            
            name = Path(path).name
            self.lbl_info.setText(f"{name} | Orig: {orig_w}x{orig_h} | View: {w}x{h}")
            
            if self.canvas.view_scale == 1.0: # Reset only on first load or manual
                self.canvas.reset_view()
        
        self.update_frame_bar()
        self.render_annotations()
        self.pbar.setVisible(False)

    def on_box_created(self, rect):
        if not self.current_event_id: 
            QMessageBox.warning(self, "Tip", "Please select an Event first.")
            return
        
        # Canvas coords (buffer) -> Real coords
        x = rect.x() / self.downsample_ratio
        y = rect.y() / self.downsample_ratio
        w = rect.width() / self.downsample_ratio
        h = rect.height() / self.downsample_ratio
        
        # Save
        if self.current_event_id not in self.annotations: return
        self.annotations[self.current_event_id]["frames"][str(self.current_idx)] = [x, y, w, h]
        
        self.render_annotations()
        self.refresh_list()

    def render_annotations(self):
        """准备数据传给 Canvas 绘制"""
        to_draw = []
        frame_key = str(self.current_idx)
        
        for eid, data in self.annotations.items():
            if frame_key in data["frames"]:
                real_box = data["frames"][frame_key]
                # Real -> Canvas coords
                rx, ry, rw, rh = real_box
                d = self.downsample_ratio
                rect = QRectF(rx*d, ry*d, rw*d, rh*d)
                
                color = self.get_color(eid)
                is_sel = (eid == self.current_event_id)
                label = f"ID {eid}"
                to_draw.append((rect, color, label, is_sel))
        
        self.canvas.set_annotations(to_draw)
        self.update_status()

    # === Annotation Management ===
    def add_event(self):
        text, ok = QInputDialog.getText(self, "New Event", "Caption:")
        if ok and text:
            new_id = max(self.annotations.keys(), default=0) + 1
            self.annotations[new_id] = {"caption": text, "frames": {}}
            self.refresh_list()
            self.list_widget.setCurrentRow(self.list_widget.count()-1)
            self.select_event(self.list_widget.currentItem())

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
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=4, ensure_ascii=False)
        QMessageBox.information(self, "Saved", f"Saved to:\n{path}")

    def load_annotations(self, folder):
        path = Path(folder) / "annotations.json"
        self.annotations = {}
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                for eid_str, dat in raw.items():
                    eid = int(eid_str)
                    frames_idx = {}
                    for k, v in dat["frames"].items():
                        if k in self.image_map:
                            frames_idx[str(self.image_map[k])] = v
                        elif k.isdigit(): # legacy support
                            frames_idx[k] = v
                    self.annotations[eid] = {"caption": dat["caption"], "frames": frames_idx}
                self.refresh_list()
            except Exception as e:
                print(e)

    # === Helpers ===
    def get_color(self, eid):
        return QColor.fromHsv(int((eid * 137.5) % 360), 200, 255)

    def refresh_list(self):
        self.list_widget.clear()
        for eid in sorted(self.annotations.keys()):
            d = self.annotations[eid]
            cnt = len(d['frames'])
            self.list_widget.addItem(f"ID {eid}: {d['caption']} ({cnt} frames)")

    def select_event(self, item):
        if not item: return
        try:
            eid = int(item.text().split(":")[0].replace("ID ", ""))
            self.current_event_id = eid
            self.render_annotations()
        except: pass

    def update_status(self):
        if self.current_event_id in self.annotations:
            marked = "YES" if str(self.current_idx) in self.annotations[self.current_event_id]["frames"] else "NO"
            self.lbl_status.setText(f"Current: ID {self.current_event_id} | Marked: {marked}")
        else:
            self.lbl_status.setText("No Selection")

    # === Nav & Frame Bar ===
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
            if i == self.current_idx:
                btn.setStyleSheet("background: #007ACC; color: white; border: 1px solid #fff;")
            else:
                btn.setStyleSheet("background: #444; color: #aaa; border: none;")

    def jump_frame(self, idx):
        if idx != self.current_idx:
            self.current_idx = idx
            self.load_image()

    def prev_frame(self):
        if self.current_idx > 0: self.jump_frame(self.current_idx - 1)
    def next_frame(self):
        if self.current_idx < len(self.image_paths)-1: self.jump_frame(self.current_idx + 1)

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        menu = QMenu()
        act = QAction("Delete Event", self)
        act.triggered.connect(lambda: self.delete_event(item))
        menu.addAction(act)
        menu.exec(self.list_widget.mapToGlobal(pos))

    def delete_event(self, item):
        eid = int(item.text().split(":")[0].replace("ID ", ""))
        del self.annotations[eid]
        if self.current_event_id == eid: self.current_event_id = None
        self.refresh_list()
        self.render_annotations()