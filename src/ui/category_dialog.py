from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QPushButton, QLabel, QInputDialog, QMessageBox, QMenu)
from PyQt6.QtCore import Qt

class CategoryManagerDialog(QDialog):
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.setWindowTitle("多级类别管理 (Hierarchy)")
        self.resize(500, 600)
        self.config = config_manager
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("类别层级 (Right-click to add/delete):"))
        
        # 树形列表
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Group / Category"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree)
        
        self.refresh_tree()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_add_group = QPushButton("➕ 新建父类 (Add Group)")
        btn_add_group.clicked.connect(self.add_group)
        btn_close = QPushButton("关闭 (Close)")
        btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_add_group)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def refresh_tree(self):
        self.tree.clear()
        # 重新加载配置
        self.config.load_categories()
        
        for group, subs in self.config.categories.items():
            group_item = QTreeWidgetItem(self.tree)
            group_item.setText(0, group)
            # 设置一点样式区分
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            
            for sub in subs:
                sub_item = QTreeWidgetItem(group_item)
                sub_item.setText(0, sub)
        
        self.tree.expandAll()

    def show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = QMenu()
        
        if item is None:
            # 空白处点击
            act = menu.addAction("➕ Add New Group")
            act.triggered.connect(self.add_group)
        elif item.parent() is None:
            # 点击了父类 (Group)
            act_add = menu.addAction(f"➕ Add Child to '{item.text(0)}'")
            act_add.triggered.connect(lambda: self.add_child(item.text(0)))
            menu.addSeparator()
            act_del = menu.addAction(f"🗑️ Delete Group '{item.text(0)}'")
            act_del.triggered.connect(lambda: self.delete_group(item.text(0)))
        else:
            # 点击了子类
            parent_group = item.parent().text(0)
            sub_cat = item.text(0)
            act_del = menu.addAction(f"🗑️ Delete '{sub_cat}'")
            act_del.triggered.connect(lambda: self.delete_child(parent_group, sub_cat))
            
        menu.exec(self.tree.mapToGlobal(pos))

    def add_group(self):
        text, ok = QInputDialog.getText(self, "新建父类", "Group Name:")
        if ok and text.strip():
            if text.strip() not in self.config.categories:
                self.config.categories[text.strip()] = []
                self.config.save_categories()
                self.refresh_tree()

    def add_child(self, group_name):
        text, ok = QInputDialog.getText(self, "新建子类", f"Add category to '{group_name}':")
        if ok and text.strip():
            if text.strip() not in self.config.categories[group_name]:
                self.config.categories[group_name].append(text.strip())
                self.config.save_categories()
                self.refresh_tree()

    def delete_group(self, group_name):
        confirm = QMessageBox.question(self, "Confirm", f"Delete Group '{group_name}' and ALL its items?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            del self.config.categories[group_name]
            self.config.save_categories()
            self.refresh_tree()

    def delete_child(self, group, sub):
        confirm = QMessageBox.question(self, "Confirm", f"Delete Category '{sub}'?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            if sub in self.config.categories[group]:
                self.config.categories[group].remove(sub)
                self.config.save_categories()
                self.refresh_tree()