import sys
import os

# 将项目根目录添加到 Python 路径（确保能正确导入 ui 模块）
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtCore import Qt  # <--- 新增导入 Qt
from PyQt5.QtWidgets import QApplication
from ui.welcome_window import WelcomeWindow


def main():
    # === 解决 WebEngine 报错的核心代码 ===
    # 必须在实例化 QApplication 之前，允许共享 OpenGL 上下文
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 显示欢迎窗口
    welcome = WelcomeWindow()
    welcome.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()