from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能停车场管理系统")
        self.setFixedSize(1200, 750)
        # 保持无边框和透明背景
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.init_ui()
        self.start_animations()

    def init_ui(self):
        # 整体布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(50, 50, 50, 50)

        # 核心容器：使用更高级的渐变和边框
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet("""
            #MainContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(15, 20, 35, 230), 
                    stop:1 rgba(30, 40, 70, 240));
                border-radius: 40px;
                border: 1px solid rgba(0, 255, 255, 0.15);
            }
        """)

        # 给容器添加外发光阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 255, 255, 40))
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setAlignment(Qt.AlignCenter)

        # 1. 装饰性背景文字 (增加空间感)
        self.bg_text = QLabel("INTELLIGENT", self.container)
        self.bg_text.setStyleSheet("color: rgba(0, 255, 255, 0.03); font-size: 150px; font-weight: 900;")
        self.bg_text.move(100, 250)

        # 2. Logo 部分 (使用叠加光效)
        self.logo_label = QLabel("🚗")
        self.logo_label.setFont(QFont("Segoe UI Emoji", 90))
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("color: #00ffff; margin-bottom: 10px;")
        container_layout.addWidget(self.logo_label)

        # 3. 标题排版
        self.title_label = QLabel("智能停车场管理系统")
        self.title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 42px;
            font-weight: 300;
            letter-spacing: 8px;
            font-family: 'Microsoft YaHei UI Light';
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("SMART PARKING SYSTEM v3.0")
        self.subtitle_label.setStyleSheet("""
            color: #00ffff;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 4px;
            margin-top: -5px;
        """)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.subtitle_label)

        container_layout.addSpacing(60)

        # 4. 极简进度条
        progress_container = QWidget()
        progress_container.setFixedWidth(500)
        progress_v_layout = QVBoxLayout(progress_container)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(2)  # 极细线条更显高级
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 1px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #0088ff, stop:1 #00ffff);
            }
        """)
        progress_v_layout.addWidget(self.progress_bar)

        self.loading_label = QLabel("SYSTEM INITIALIZING...")
        self.loading_label.setStyleSheet("""
            color: rgba(0, 255, 255, 0.5); 
            font-size: 10px; 
            letter-spacing: 2px;
        """)
        self.loading_label.setAlignment(Qt.AlignCenter)
        progress_v_layout.addWidget(self.loading_label)

        container_layout.addWidget(progress_container, 0, Qt.AlignCenter)
        container_layout.addSpacing(40)

        self.main_layout.addWidget(self.container)

        # 关闭按钮 (右上角悬浮)
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFixedSize(35, 35)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 17px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #ff4444;
                color: white;
            }
        """)
        self.close_btn.clicked.connect(self.close)

    def start_animations(self):
        # 1. 窗口入场渐显动画
        self.opacity_ani = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_ani.setDuration(1000)
        self.opacity_ani.setStartValue(0)
        self.opacity_ani.setEndValue(1)
        self.opacity_ani.start()

        # 2. 容器轻微上移效果
        self.move_ani = QPropertyAnimation(self.container, b"pos")
        self.move_ani.setDuration(1200)
        self.move_ani.setStartValue(QPoint(50, 100))
        self.move_ani.setEndValue(QPoint(50, 50))
        self.move_ani.setEasingCurve(QEasingCurve.OutCubic)
        self.move_ani.start()

        # 3. 进度计时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.progress_val = 0
        self.timer.start(35)

    def update_progress(self):
        self.progress_val += 1
        self.progress_bar.setValue(self.progress_val)

        # 动态改变文字
        stages = [
            (0, "LOADING CORE MODULES..."),
            (30, "ESTABLISHING DATABASE CONNECTION..."),
            (60, "SYNCING HARDWARE SENSORS..."),
            (90, "FINALIZING INTERFACE...")
        ]
        for threshold, text in reversed(stages):
            if self.progress_val >= threshold:
                self.loading_label.setText(text)
                break

        if self.progress_val >= 100:
            self.timer.stop()
            QTimer.singleShot(500, self.goto_login)

    def resizeEvent(self, event):
        self.close_btn.move(self.width() - 80, 80)
        super().resizeEvent(event)

    def goto_login(self):
        # 可以在这里添加一个淡出动画再跳转
        print("System Ready. Navigating to Login...")
        self.close()
        try:
            from ui.login_window import NeonLoginWindow
            self.login_window = NeonLoginWindow()
            self.login_window.show()
        except:
            pass