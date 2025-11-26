from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QHBoxLayout, 
                             QDialogButtonBox, QTextEdit, QGroupBox, 
                             QRadioButton, QButtonGroup, QScrollArea, 
                             QWidget, QLineEdit, QToolButton, QSizePolicy, QFrame, QMessageBox)
from PyQt6.QtCore import Qt

class EditEventDialog(QDialog):
    def __init__(self, parent, categories_dict, current_category, current_caption):
        super().__init__(parent)
        self.setWindowTitle("编辑事件信息 (Edit Event Info)")
        
        self.categories_dict = categories_dict
        self.current_category = current_category
        self.result_data = None
        
        # === 核心修改：动态宽度 ===
        # 逻辑：父类数量 * 200，最小宽度 800
        calc_width = len(self.categories_dict) * 200
        self.resize(max(800, calc_width), 700)
        # =======================
        
        # 全局单选组
        self.btn_group = QButtonGroup(self)
        
        layout = QVBoxLayout(self)
        
        # === 1. 类别选择区 (平铺直选) ===
        layout.addWidget(QLabel("修改类别 (Change Category):"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(400)
        
        self.cat_container_widget = QWidget()
        self.cat_main_layout = QVBoxLayout(self.cat_container_widget)
        
        # A. 列容器
        self.columns_widget = QWidget()
        self.columns_layout = QHBoxLayout(self.columns_widget)
        self.columns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.columns_layout.setSpacing(15)
        
        # 生成布局
        self.generate_category_columns()
        
        self.cat_main_layout.addWidget(self.columns_widget)
        
        # B. 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.cat_main_layout.addWidget(line)
        
        # C. 自定义输入区
        self.rb_custom = QRadioButton("➕ 改为新类别 (Custom)")
        self.btn_group.addButton(self.rb_custom)
        self.cat_main_layout.addWidget(self.rb_custom)
        
        custom_layout = QHBoxLayout()
        self.input_group = QLineEdit()
        self.input_group.setPlaceholderText("新父类 (Group)")
        self.input_sub = QLineEdit()
        self.input_sub.setPlaceholderText("新子类 (Sub)")
        
        custom_layout.addWidget(self.input_group, 1)
        custom_layout.addWidget(self.input_sub, 1)
        
        custom_w = QWidget(); custom_w.setLayout(custom_layout)
        self.cat_main_layout.addWidget(custom_w)
        
        scroll.setWidget(self.cat_container_widget)
        layout.addWidget(scroll)
        
        # === 2. Caption ===
        layout.addWidget(QLabel("修改描述 (Edit Caption):"))
        self.txt_caption = QTextEdit()
        self.txt_caption.setText(current_caption)
        self.txt_caption.setFixedHeight(60)
        layout.addWidget(self.txt_caption)
        
        # === 3. Buttons ===
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        
        # 绑定交互
        self.btn_group.buttonClicked.connect(self.on_category_selected)
        self.input_group.textChanged.connect(lambda: self.rb_custom.setChecked(True))
        self.input_sub.textChanged.connect(lambda: self.rb_custom.setChecked(True))
        
        # === 核心：自动选中当前类别 ===
        self.pre_select_category()

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
            should_expand = False
            
            for i, sub_name in enumerate(sub_list):
                rb = QRadioButton(sub_name)
                rb.setProperty("group_name", group_name)
                rb.setProperty("sub_name", sub_name)
                self.btn_group.addButton(rb)
                
                # 检查是否是当前类别，如果是且在隐藏区，标记需要展开
                if sub_name == self.current_category:
                    if i >= VISIBLE_LIMIT: should_expand = True
                
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
                
                if should_expand:
                    btn_expand.setChecked(True)
                    
                gb_layout.addWidget(btn_expand)
            
            gb_layout.addStretch()
            self.columns_layout.addWidget(gb)
        self.columns_layout.addStretch()

    def pre_select_category(self):
        """初始化时，找到对应的按钮并选中"""
        for btn in self.btn_group.buttons():
            if btn == self.rb_custom: continue
            if btn.property("sub_name") == self.current_category:
                btn.setChecked(True)
                self.on_category_selected(btn)
                return

    def on_category_selected(self, btn):
        is_custom = self.rb_custom.isChecked()
        self.input_group.setEnabled(is_custom)
        self.input_sub.setEnabled(is_custom)

    def accept(self):
        cap = self.txt_caption.toPlainText().strip()
        if not cap:
            QMessageBox.warning(self, "Warning", "Caption cannot be empty!")
            return
            
        group = ""
        sub = ""
        sel = self.btn_group.checkedButton()
        
        if sel == self.rb_custom:
            group = self.input_group.text().strip()
            sub = self.input_sub.text().strip()
            if not group or not sub:
                QMessageBox.warning(self, "Warning", "Please enter Group and Category!")
                return
        elif sel:
            group = sel.property("group_name")
            sub = sel.property("sub_name")
        else:
            QMessageBox.warning(self, "Warning", "Please select a category!")
            return

        self.result_data = {
            "group": group,
            "category": sub,
            "caption": cap
        }
        super().accept()