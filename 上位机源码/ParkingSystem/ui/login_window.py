# ui/login_window.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class NeonLoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 600)

        self.init_ui()
        self.drag_position = None

    def init_ui(self):
        # 主框架
        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(20, 20, 460, 560)
        self.main_frame.setObjectName("MainFrame")
        self.main_frame.setStyleSheet("""
            #MainFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0a102a, stop:1 #162040);
                border: 2px solid #00f2ff;
                border-radius: 30px;
            }
        """)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 242, 255, 150))
        shadow.setOffset(0, 0)
        self.main_frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.main_frame)
        layout.setContentsMargins(40, 40, 40, 40)

        # Logo
        logo = QLabel("🚗")
        logo.setFont(QFont("Segoe UI Emoji", 60))
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        # 标题
        title = QLabel("智能停车场管理系统")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00f2ff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(40)

        # 用户名输入
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        self.username_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,10);
                border: 1px solid #00f2ff;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                padding: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #00f2ff;
            }
        """)
        layout.addWidget(self.username_input)

        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,10);
                border: 1px solid #00f2ff;
                border-radius: 10px;
                color: white;
                font-size: 14px;
                padding: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #00f2ff;
            }
        """)
        layout.addWidget(self.password_input)

        layout.addSpacing(30)

        # 登录按钮
        self.login_btn = QPushButton("登录系统")
        self.login_btn.setFixedHeight(50)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #00f2ff, stop:1 #7000ff);
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #7000ff, stop:1 #00f2ff);
            }
        """)
        self.login_btn.clicked.connect(self.login)
        layout.addWidget(self.login_btn)

        # 错误提示
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #ff3366; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)

        layout.addStretch()

        # 底部按钮
        btn_layout = QHBoxLayout()
        test_label = QLabel("测试账号: admin / admin")
        test_label.setStyleSheet("color: #00f2ff; font-size: 10px;")

        close_btn = QPushButton("退出")
        close_btn.setStyleSheet("""
            QPushButton {
                color: #8899aa;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #ff3366;
            }
        """)
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(test_label)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        # 窗口拖动
        self.main_frame.mousePressEvent = self.mouse_press
        self.main_frame.mouseMoveEvent = self.mouse_move

    def mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()

    def mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if username == "admin" and password == "admin":
            self.goto_main(username)
        else:
            self.error_label.setText("❌ 用户名或密码错误")
            self.shake_window()

    def goto_main(self, username):
        """跳转到主界面（功能选择界面）"""
        try:
            from ui.main_window import MainWindow

            user_info = {
                "username": username,
                "role": "管理员"
            }

            self.main_window = MainWindow(user_info)
            self.main_window.show()
            self.close()

        except Exception as e:
            print(f"打开主窗口失败: {e}")
            self.error_label.setText(f"启动失败: {str(e)[:30]}")

    def shake_window(self):
        """窗口震动"""
        original_pos = self.pos()

        def animate(count=0):
            if count > 5:
                self.move(original_pos)
                return
            offset = 3 if count % 2 == 0 else -3
            self.move(original_pos + QPoint(offset, 0))
            QTimer.singleShot(30, lambda: animate(count + 1))

        animate()