import json
import os

class ConfigManager:
    def __init__(self, config_path="categories.json"):
        self.config_path = config_path
        self.categories = self.load_categories()

    def load_categories(self):
        # 如果存在配置文件，读取它
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        # 默认类别
        return ["一般变化", "建筑施工", "植被生长", "道路建设"]

    def save_categories(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Save config failed: {e}")

    def add_category(self, cat):
        # 如果是新类别，保存
        if cat and cat not in self.categories:
            self.categories.append(cat)
            self.save_categories()