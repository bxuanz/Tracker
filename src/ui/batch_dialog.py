from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, 
                             QSlider, QSpinBox, QHBoxLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt

class BatchDialog(QDialog):
    def __init__(self, parent, categories, current_idx, total_frames):
        super().__init__(parent)
        self.setWindowTitle("创建固定位置事件 (Batch Create)")
        self.resize(400, 250)
        
        self.result_data = None
        self.total_frames = total_frames
        self.start_idx = current_idx
        
        layout = QVBoxLayout(self)
        
        # 1. 类别选择
        layout.addWidget(QLabel("1. 选择或输入类别 (Category):"))
        self.combo_cat = QComboBox()
        self.combo_cat.setEditable(True) # 允许打字输入新类别
        self.combo_cat.addItems(categories)
        layout.addWidget(self.combo_cat)
        
        layout.addSpacing(15)
        
        # 2. 结束帧选择
        layout.addWidget(QLabel(f"2. 事件结束帧 (当前第 {self.start_idx+1} 帧):"))
        
        h_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(self.start_idx, self.total_frames - 1)
        self.slider.setValue(self.total_frames - 1) # 默认选到最后一张
        
        self.spin = QSpinBox()
        self.spin.setRange(self.start_idx + 1, self.total_frames)
        self.spin.setValue(self.total_frames)
        
        # 绑定滑块和数字框
        self.slider.valueChanged.connect(lambda v: self.spin.setValue(v + 1))
        self.spin.valueChanged.connect(lambda v: self.slider.setValue(v - 1))
        
        h_layout.addWidget(self.slider)
        h_layout.addWidget(self.spin)
        layout.addLayout(h_layout)
        
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: gray; font-size: 9pt;")
        self.update_label()
        layout.addWidget(self.lbl_info)
        
        self.slider.valueChanged.connect(self.update_label)

        # 3. 确认/取消按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_label(self):
        end = self.slider.value()
        count = end - self.start_idx + 1
        self.lbl_info.setText(f"将在 [第 {self.start_idx+1} 帧] 到 [第 {end+1} 帧] 生成相同的框 (共 {count} 张)")

    def accept(self):
        self.result_data = {
            "category": self.combo_cat.currentText(),
            "end_idx": self.slider.value()
        }
        super().accept()