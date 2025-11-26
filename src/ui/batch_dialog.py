from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, 
                             QSlider, QSpinBox, QHBoxLayout, QDialogButtonBox,
                             QTextEdit, QGroupBox, QRadioButton, QButtonGroup, 
                             QScrollArea, QWidget, QLineEdit, QToolButton, QSizePolicy, QFrame)
from PyQt6.QtCore import Qt

class BatchDialog(QDialog):
    def __init__(self, parent, categories_dict, current_idx, total_frames, all_events_dict=None):
        super().__init__(parent)
        self.setWindowTitle("标注事件 (Annotate Event)")
        
        self.categories_dict = categories_dict
        
        # === 修改点：动态计算宽度 ===
        # 逻辑：父类数量 * 200，但设定最小宽度 800 以防控件挤压
        calc_width = len(self.categories_dict) * 200
        self.resize(max(800, calc_width), 700) 
        # =========================

        self.result_data = None
        self.start_idx = current_idx
        self.all_events = all_events_dict if all_events_dict else {}
        
        self.btn_group = QButtonGroup(self)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # === 1. 目标事件 ===
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
        main_layout.addWidget(group_event)
        
        # === 2. 类别选择区 ===
        main_layout.addWidget(QLabel("选择类别 (Select Category):"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # scroll高度自适应剩余空间，但给个最小值
        scroll.setMinimumHeight(350) 
        
        self.cat_container_widget = QWidget()
        self.cat_main_layout = QVBoxLayout(self.cat_container_widget) 
        
        # A. 类别列容器
        self.columns_widget = QWidget()
        self.columns_layout = QHBoxLayout(self.columns_widget)
        self.columns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.columns_layout.setSpacing(15) 
        
        self.generate_category_columns()
        
        self.cat_main_layout.addWidget(self.columns_widget)
        
        # B. 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.cat_main_layout.addWidget(line)
        
        # C. 自定义输入区
        self.rb_custom = QRadioButton("➕ 手动输入 / 补充子类 (Custom)")
        self.btn_group.addButton(self.rb_custom)
        self.cat_main_layout.addWidget(self.rb_custom)
        
        custom_layout = QHBoxLayout()
        
        self.input_group = QComboBox()
        self.input_group.setEditable(True)
        self.input_group.setPlaceholderText("选择或输入父类 (Group)")
        self.input_group.addItems(sorted(self.categories_dict.keys()))
        
        self.input_sub = QLineEdit()
        self.input_sub.setPlaceholderText("输入新子类 (New Sub-Category)")
        
        custom_layout.addWidget(self.input_group, 1)
        custom_layout.addWidget(self.input_sub, 1)
        
        custom_w = QWidget(); custom_w.setLayout(custom_layout)
        self.cat_main_layout.addWidget(custom_w)
        
        scroll.setWidget(self.cat_container_widget)
        main_layout.addWidget(scroll)
        
        # === 3. Caption ===
        main_layout.addWidget(QLabel("详细描述 (Caption):"))
        self.txt_caption = QTextEdit()
        self.txt_caption.setPlaceholderText("必填...")
        self.txt_caption.setFixedHeight(50)
        main_layout.addWidget(self.txt_caption)
        
        # === 4. Slider ===
        main_layout.addWidget(QLabel(f"填充范围 (Start: Frame {self.start_idx+1}):"))
        h_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(self.start_idx, total_frames - 1)
        self.slider.setValue(total_frames - 1)
        self.spin = QSpinBox()
        self.spin.setRange(self.start_idx + 1, total_frames)
        self.spin.setValue(total_frames)
        self.slider.valueChanged.connect(lambda v: self.spin.setValue(v + 1))
        self.spin.valueChanged.connect(lambda v: self.slider.setValue(v - 1))
        h_layout.addWidget(self.slider); h_layout.addWidget(self.spin)
        main_layout.addLayout(h_layout)
        
        self.lbl_info = QLabel("")
        self.update_label()
        main_layout.addWidget(self.lbl_info)
        self.slider.valueChanged.connect(self.update_label)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        main_layout.addWidget(self.buttons)

        # Bindings
        self.btn_group.buttonClicked.connect(self.on_category_selected)
        self.combo_event_select.currentIndexChanged.connect(self.on_event_selection_changed)
        self.txt_caption.textChanged.connect(self.check_validity)
        self.input_group.editTextChanged.connect(lambda: self.rb_custom.setChecked(True))
        self.input_sub.textChanged.connect(lambda: self.rb_custom.setChecked(True))
        self.input_group.editTextChanged.connect(self.check_validity)
        self.input_sub.textChanged.connect(self.check_validity)

        self.on_category_selected(None)
        self.check_validity()

    def generate_category_columns(self):
        VISIBLE_LIMIT = 15
        for group_name, sub_list in self.categories_dict.items():
            gb = QGroupBox(group_name)
            gb.setStyleSheet("QGroupBox { font-weight: bold; color: #007ACC; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
            gb.setFixedWidth(180)
            gb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
            
            gb_layout = QVBoxLayout(gb)
            gb_layout.setContentsMargins(5, 15, 5, 5)
            gb_layout.setSpacing(2)
            gb_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            top_widget = QWidget()
            top_vbox = QVBoxLayout(top_widget); top_vbox.setContentsMargins(0,0,0,0); top_vbox.setSpacing(2)
            
            more_widget = QWidget()
            more_vbox = QVBoxLayout(more_widget); more_vbox.setContentsMargins(0,0,0,0); more_vbox.setSpacing(2)
            more_widget.setVisible(False)

            has_more = len(sub_list) > VISIBLE_LIMIT
            
            for i, sub_name in enumerate(sub_list):
                rb = QRadioButton(sub_name)
                rb.setProperty("group_name", group_name)
                rb.setProperty("sub_name", sub_name)
                self.btn_group.addButton(rb)
                
                if i < VISIBLE_LIMIT: top_vbox.addWidget(rb)
                else: more_vbox.addWidget(rb)

            gb_layout.addWidget(top_widget)
            if has_more:
                gb_layout.addWidget(more_widget)
                btn_expand = QToolButton()
                btn_expand.setText(f"▼ 更多 ({len(sub_list) - VISIBLE_LIMIT})")
                btn_expand.setCheckable(True)
                btn_expand.setStyleSheet("QToolButton { border: none; color: #888; font-size: 8pt; } QToolButton:hover { color: #007ACC; }")
                btn_expand.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                def toggle(checked, w=more_widget, b=btn_expand):
                    w.setVisible(checked); b.setText("▲ 收起" if checked else f"▼ 更多")
                btn_expand.toggled.connect(toggle)
                gb_layout.addWidget(btn_expand)
            
            gb_layout.addStretch()
            self.columns_layout.addWidget(gb)
        self.columns_layout.addStretch()

    def on_category_selected(self, btn):
        is_custom = self.rb_custom.isChecked()
        self.input_group.setEnabled(is_custom)
        self.input_sub.setEnabled(is_custom)
        self.check_validity()

    def on_event_selection_changed(self):
        eid = self.combo_event_select.currentData()
        is_new = (eid == -1)
        self.cat_container_widget.setEnabled(is_new)
        self.rb_custom.setEnabled(is_new)
        self.input_group.setEnabled(is_new and self.rb_custom.isChecked())
        self.input_sub.setEnabled(is_new and self.rb_custom.isChecked())
        
        if not is_new:
            data = self.all_events.get(eid, {})
            self.txt_caption.setText(data.get('caption', ''))
            self.txt_caption.setReadOnly(True)
        else:
            self.txt_caption.setReadOnly(False)
            self.txt_caption.clear()
        self.check_validity()

    def check_validity(self):
        if self.combo_event_select.currentData() != -1:
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True); return
        
        cat_selected = False
        if self.rb_custom.isChecked():
            if self.input_group.currentText().strip() and self.input_sub.text().strip(): cat_selected = True
        else:
            if self.btn_group.checkedButton(): cat_selected = True
                
        has_cap = len(self.txt_caption.toPlainText().strip()) > 0
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(cat_selected and has_cap)

    def update_label(self):
        end = self.slider.value()
        self.lbl_info.setText(f"Range: {self.start_idx+1} -> {end+1} ({end-self.start_idx+1} frames)")

    def accept(self):
        eid = self.combo_event_select.currentData()
        group = ""
        sub = ""
        sel = self.btn_group.checkedButton()
        
        if sel == self.rb_custom:
            group = self.input_group.currentText().strip()
            sub = self.input_sub.text().strip()
        elif sel:
            group = sel.property("group_name")
            sub = sel.property("sub_name")
        
        self.result_data = {
            "target_id": eid,
            "group": group,
            "sub_category": sub,
            "caption": self.txt_caption.toPlainText().strip(),
            "end_idx": self.slider.value()
        }
        super().accept()