import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.ui.main_window import MainWindow

# 引入 ctypes 以便在 Windows 任务栏显示正确图标
try:
    import ctypes
    myappid = 'mycompany.tracker.app' # 任意唯一字符串
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # === 设置全局图标 ===
    # 检查 assets/icon.png 是否存在
    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon1.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()