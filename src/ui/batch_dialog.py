from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, 
                             QSlider, QSpinBox, QHBoxLayout, QDialogButtonBox,
                             QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt

class BatchDialog(QDialog):
    def __init__(self, parent, categories_dict, current_idx, total_frames, all_events_dict=None):
        """
        categories_dict: { "Group": ["Sub1", "Sub2"] }
        """
        super().__init__(parent)
        self.setWindowTitle("标注事件 (Annotate Event)")
        self.resize(450, 500)
        
        self.categories_dict = categories_dict
        self.result_data = None
        self.start_idx = current_idx
        self.all_events = all_events_dict if all_events_dict else {}
        
        layout = QVBoxLayout(self)
        
        # 1. 目标事件选择
        group_event = QGroupBox("目标事件 (Target Event)")
        v_layout = QVBoxLayout()
        self.combo_event_select = QComboBox()
        self.combo_event_select.addItem("✨ 创建新事件 (Create New Event)", -1)
        
        for eid, data in self.all_events.items():
            cat = data.get('category', 'Unk')
            cap = data.get('caption', '')[:15] + "..."
            self.combo_event_select.addItem(f"ID {eid}: {cat} | {cap}", eid)
            
        v_layout.addWidget(self.combo_event_select)
        group_event.setLayout(v_layout)
        layout.addWidget(group_event)
        
        layout.addSpacing(10)

        # 2. 类别选择 (二级联动)
        cat_layout = QHBoxLayout()
        
        # 父类 Combo
        v_cat_1 = QVBoxLayout()
        v_cat_1.addWidget(QLabel("父类别 (Group):"))
        self.combo_group = QComboBox()
        self.combo_group.setEditable(True) # 允许新建组
        self.combo_group.addItems(sorted(self.categories_dict.keys()))
        v_cat_1.addWidget(self.combo_group)
        
        # 子类 Combo
        v_cat_2 = QVBoxLayout()
        v_cat_2.addWidget(QLabel("子类别 (Sub-Category):"))
        self.combo_sub = QComboBox()
        self.combo_sub.setEditable(True) # 允许新建子类
        v_cat_2.addWidget(self.combo_sub)
        
        cat_layout.addLayout(v_cat_1)
        cat_layout.addLayout(v_cat_2)
        layout.addLayout(cat_layout)
        
        # 3. Caption
        layout.addWidget(QLabel("详细描述 (Caption):"))
        self.txt_caption = QTextEdit()
        self.txt_caption.setPlaceholderText("必填: 描述变化细节...")
        self.txt_caption.setFixedHeight(60)
        layout.addWidget(self.txt_caption)
        
        layout.addSpacing(10)
        
        # 4. Slider
        layout.addWidget(QLabel(f"批量填充范围 (Start: Frame {self.start_idx+1}):"))
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

        # 信号绑定
        self.combo_group.currentTextChanged.connect(self.update_sub_combo)
        self.combo_event_select.currentIndexChanged.connect(self.on_event_selection_changed)
        self.txt_caption.textChanged.connect(self.check_validity)
        
        # 初始化
        self.update_sub_combo(self.combo_group.currentText())
        self.check_validity()

    def update_sub_combo(self, group_text):
        """根据父类更新子类"""
        current_sub = self.combo_sub.currentText()
        self.combo_sub.clear()
        
        if group_text in self.categories_dict:
            self.combo_sub.addItems(self.categories_dict[group_text])
        else:
            # 如果是新输入的组，子类列表为空，但允许用户输入
            pass
            
        # 如果之前有值且不是列表里的，可能要保留（简化处理：清空）

    def on_event_selection_changed(self):
        eid = self.combo_event_select.currentData()
        if eid == -1:
            self.combo_group.setEnabled(True)
            self.combo_sub.setEnabled(True)
            self.txt_caption.setReadOnly(False)
            self.txt_caption.clear()
        else:
            data = self.all_events.get(eid, {})
            full_cat = data.get('category', '')
            # 尝试解析 "Group - Sub" 格式，或者直接填入Sub
            # 这里简化处理：只填入文字，不再反向解析父子关系，因为已经锁定了
            self.combo_group.setEnabled(False)
            self.combo_sub.setEnabled(False)
            self.combo_sub.setEditText(full_cat) # 显示完整类别名
            
            self.txt_caption.setText(data.get('caption', ''))
            self.txt_caption.setReadOnly(True)
        self.check_validity()

    def check_validity(self):
        if self.combo_event_select.currentData() != -1:
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            return
        text = self.txt_caption.toPlainText().strip()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(len(text) > 0)

    def update_label(self):
        end = self.slider.value()
        self.lbl_info.setText(f"Range: {self.start_idx+1} -> {end+1} ({end-self.start_idx+1} frames)")

    def accept(self):
        # 组合最终类别名称，例如 "建筑施工" 或者 "人工设施-建筑施工"
        # 你的需求是子类别很多，所以建议存子类别，或者 "父-子"
        # 这里我们存 "子类别"，因为父类别只是为了方便筛选
        group = self.combo_group.currentText().strip()
        sub = self.combo_sub.currentText().strip()
        
        self.result_data = {
            "target_id": self.combo_event_select.currentData(),
            "group": group,
            "sub_category": sub,
            "caption": self.txt_caption.toPlainText().strip(),
            "end_idx": self.slider.value()
        }
        super().accept()