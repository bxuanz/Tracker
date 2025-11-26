import json
import os

class ConfigManager:
    def __init__(self, config_path="categories.json"):
        self.config_path = config_path
        # 默认多级类别结构
        self.default_categories = {
            "自然地理": ["植被生长", "水体变化", "林地破坏", "耕地减少"],
            "人工设施": ["建筑施工", "道路建设", "大棚搭建", "推填土"],
            "军事目标": ["阵地伪装", "车辆集结", "设施损毁"],
            "其他": ["一般变化", "未知"]
        }
        self.categories = {} # 字典结构
        self.load_categories()

    def load_categories(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.categories = data
                        return
            except Exception as e:
                print(f"Config load error: {e}")
        
        # 默认初始化
        self.categories = self.default_categories
        self.save_categories()

    def save_categories(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Save config error: {e}")

    def add_category(self, group, sub_cat):
        """添加类别 (支持新建组或新建子类)"""
        group = group.strip()
        sub_cat = sub_cat.strip()
        if not group or not sub_cat: return

        if group not in self.categories:
            self.categories[group] = []
        
        if sub_cat not in self.categories[group]:
            self.categories[group].append(sub_cat)
            self.save_categories()

    def get_all_flat_categories(self):
        """获取所有扁平化的 '组-子类' 字符串，用于旧逻辑兼容(可选)"""
        res = []
        for group, subs in self.categories.items():
            for sub in subs:
                res.append(f"{group}-{sub}")
        return sorted(res)