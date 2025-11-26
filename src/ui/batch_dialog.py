from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, 
                             QSlider, QSpinBox, QHBoxLayout, QDialogButtonBox,
                             QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt

class BatchDialog(QDialog):
    def __init__(self, parent, categories, current_idx, total_frames, all_events_dict=None):
        """
        all_events_dict: {eid: {'category':..., 'caption':...}} 用于填充下拉列表
        """
        super().__init__(parent)
        self.setWindowTitle("标注事件 (Annotate Event)")
        self.resize(450, 450)
        
        self.result_data = None
        self.start_idx = current_idx
        self.all_events = all_events_dict if all_events_dict else {}
        
        layout = QVBoxLayout(self)
        
        # === 1. 事件选择 (核心修改) ===
        group_event = QGroupBox("目标事件 (Target Event)")
        v_layout = QVBoxLayout()
        
        self.combo_event_select = QComboBox()
        self.combo_event_select.addItem("✨ 创建新事件 (Create New Event)", -1) # UserData: -1
        
        # 填充已存在的事件到下拉列表
        for eid, data in self.all_events.items():
            cat = data.get('category', 'Unk')
            cap = data.get('caption', '')[:15] + "..."
            display_text = f"ID {eid}: {cat} | {cap}"
            self.combo_event_select.addItem(display_text, eid) # UserData: eid
            
        v_layout.addWidget(self.combo_event_select)
        group_event.setLayout(v_layout)
        layout.addWidget(group_event)
        
        layout.addSpacing(10)

        # === 2. 信息输入 ===
        layout.addWidget(QLabel("类别 (Category):"))
        self.combo_cat = QComboBox()
        self.combo_cat.setEditable(True)
        self.combo_cat.addItems(categories)
        layout.addWidget(self.combo_cat)
        
        layout.addSpacing(5)
        
        layout.addWidget(QLabel("详细描述 (Caption):"))
        self.txt_caption = QTextEdit()
        self.txt_caption.setPlaceholderText("必填: 描述事件细节...")
        self.txt_caption.setFixedHeight(60)
        layout.addWidget(self.txt_caption)
        
        layout.addSpacing(10)
        
        # === 3. 范围滑块 ===
        layout.addWidget(QLabel(f"批量填充范围 (从第 {self.start_idx+1} 帧开始):"))
        h_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(self.start_idx, total_frames - 1)
        self.slider.setValue(total_frames - 1)
        
        self.spin = QSpinBox()
        self.spin.setRange(self.start_idx + 1, total_frames)
        self.spin.setValue(total_frames)
        
        self.slider.valueChanged.connect(lambda v: self.spin.setValue(v + 1))
        self.spin.valueChanged.connect(lambda v: self.slider.setValue(v - 1))
        
        h_layout.addWidget(self.slider)
        h_layout.addWidget(self.spin)
        layout.addLayout(h_layout)
        
        self.lbl_info = QLabel("")
        self.update_label()
        layout.addWidget(self.lbl_info)
        self.slider.valueChanged.connect(self.update_label)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        # === 信号绑定 ===
        self.combo_event_select.currentIndexChanged.connect(self.on_event_selection_changed)
        self.txt_caption.textChanged.connect(self.check_validity)
        
        # 初始化检查
        self.check_validity()

    def on_event_selection_changed(self):
        """当用户选择已有ID时，自动填入信息并锁定；选择新建时解锁"""
        idx = self.combo_event_select.currentIndex()
        eid = self.combo_event_select.currentData() # 获取绑定的ID
        
        if eid == -1: # New Event
            self.combo_cat.setEnabled(True)
            self.txt_caption.setReadOnly(False)
            self.txt_caption.clear()
        else: # Existing Event
            data = self.all_events.get(eid, {})
            self.combo_cat.setCurrentText(data.get('category', ''))
            self.combo_cat.setEnabled(False) # 锁定
            self.txt_caption.setText(data.get('caption', ''))
            self.txt_caption.setReadOnly(True) # 锁定
            
        self.check_validity()

    def check_validity(self):
        # 如果是选择已有事件，总是允许OK
        if self.combo_event_select.currentData() != -1:
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            return
            
        # 如果是新建，Caption不能为空
        text = self.txt_caption.toPlainText().strip()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(len(text) > 0)

    def update_label(self):
        end = self.slider.value()
        count = end - self.start_idx + 1
        self.lbl_info.setText(f"将在 [第 {self.start_idx+1} 帧] -> [第 {end+1} 帧] 生成标注 (共 {count} 张)")

    def accept(self):
        target_id = self.combo_event_select.currentData() # -1 means new
        
        self.result_data = {
            "target_id": target_id, # -1 或 具体ID
            "category": self.combo_cat.currentText().strip(),
            "caption": self.txt_caption.toPlainText().strip(),
            "end_idx": self.slider.value()
        }
        super().accept()