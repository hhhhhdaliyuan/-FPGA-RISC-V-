import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime, timedelta


class SecurityMonitorWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setWindowTitle("安防监控中心 - 实时流水")
        self.setMinimumSize(1100, 800)

        # --- 新增控制变量 ---
        self.all_pending_records = []  # 存放文件夹里预加载的图片数据
        self.current_display_count = 0  # 当前已显示的条数
        self.timer_25s = QTimer(self)
        self.timer_25s.timeout.connect(self.display_new_record)

        self.init_ui()
        # 启动预加载逻辑
        self.load_all_photos()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setStyleSheet("background-color: #0d1b2a;")

        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # =========================
        # 左侧：抓拍预览 + 车辆详情
        # =========================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        self.preview_title = QLabel("📸 实时抓拍预览")
        self.preview_title.setStyleSheet("""
            color: #ffffff;
            font-size: 20px;
            font-weight: bold;
            padding: 4px 2px;
        """)

        self.preview_card = QFrame()
        self.preview_card.setStyleSheet("""
            QFrame {
                background-color: #13283b;
                border: 1px solid #1f3d56;
                border-radius: 10px;
            }
        """)
        preview_card_layout = QVBoxLayout(self.preview_card)
        preview_card_layout.setContentsMargins(10, 10, 10, 10)
        preview_card_layout.setSpacing(10)

        self.img_label = QLabel("等待 25s 信号...")
        self.img_label.setFixedSize(640, 480)
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("""
            QLabel {
                border: 2px solid #00f2ff;
                border-radius: 8px;
                background-color: #000000;
                color: #d9f7ff;
                font-size: 16px;
            }
        """)
        preview_card_layout.addWidget(self.img_label, alignment=Qt.AlignCenter)

        bottom_info_layout = QHBoxLayout()
        bottom_info_layout.setSpacing(12)

        # 左下：车牌局部
        plate_box = QFrame()
        plate_box.setFixedWidth(180)
        plate_box.setStyleSheet("""
            QFrame {
                background-color: #102131;
                border: 1px solid #21445f;
                border-radius: 8px;
            }
        """)
        plate_layout = QVBoxLayout(plate_box)
        plate_layout.setContentsMargins(10, 10, 10, 10)
        plate_layout.setSpacing(8)

        plate_title = QLabel("车牌局部")
        plate_title.setStyleSheet("""
            color: #9adfff;
            font-size: 14px;
            font-weight: bold;
            border: none;
        """)

        self.plate_img_label = QLabel("等待识别")
        self.plate_img_label.setFixedSize(150, 70)
        self.plate_img_label.setAlignment(Qt.AlignCenter)
        self.plate_img_label.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border: 1px solid #355b78;
                border-radius: 6px;
                color: #b8c7d6;
                font-size: 13px;
            }
        """)

        plate_layout.addWidget(plate_title)
        plate_layout.addWidget(self.plate_img_label, alignment=Qt.AlignCenter)
        plate_layout.addStretch()

        # 右下：车辆详情
        info_box = QFrame()
        info_box.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid #21445f;
                border-radius: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_box)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(10)

        info_title = QLabel("车辆详情")
        info_title.setStyleSheet("""
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
            border: none;
        """)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(10)

        label_style = """
            color: #8fb3c9;
            font-size: 14px;
            font-weight: normal;
        """
        value_style = """
            color: #ffffff;
            font-size: 15px;
            font-weight: bold;
        """

        self.value_plate = QLabel("--")
        self.value_spot = QLabel("--")
        self.value_status = QLabel("--")
        self.value_fee = QLabel("--")
        self.value_duration = QLabel("--")
        self.value_time = QLabel("--")

        for v in [self.value_plate, self.value_spot, self.value_status,
                  self.value_fee, self.value_duration, self.value_time]:
            v.setStyleSheet(value_style)
            v.setWordWrap(True)

        grid.addWidget(self._make_label("车牌号：", label_style), 0, 0)
        grid.addWidget(self.value_plate, 0, 1)

        grid.addWidget(self._make_label("停车位置：", label_style), 0, 2)
        grid.addWidget(self.value_spot, 0, 3)

        grid.addWidget(self._make_label("当前状态：", label_style), 1, 0)
        grid.addWidget(self.value_status, 1, 1)

        grid.addWidget(self._make_label("费用：", label_style), 1, 2)
        grid.addWidget(self.value_fee, 1, 3)

        grid.addWidget(self._make_label("停车时长：", label_style), 2, 0)
        grid.addWidget(self.value_duration, 2, 1)

        grid.addWidget(self._make_label("记录时间：", label_style), 2, 2)
        grid.addWidget(self.value_time, 2, 3)

        info_layout.addWidget(info_title)
        info_layout.addLayout(grid)

        bottom_info_layout.addWidget(plate_box)
        bottom_info_layout.addWidget(info_box, 1)

        preview_card_layout.addLayout(bottom_info_layout)

        left_layout.addWidget(self.preview_title)
        left_layout.addWidget(self.preview_card)
        left_layout.addStretch()

        # =========================
        # 右侧：今日进出记录
        # =========================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        self.list_title = QLabel("📜 实时进出记录")
        self.list_title.setStyleSheet("""
            color: #ffffff;
            font-size: 20px;
            font-weight: bold;
            padding: 4px 2px;
        """)

        list_card = QFrame()
        list_card.setStyleSheet("""
            QFrame {
                background-color: #13283b;
                border: 1px solid #1f3d56;
                border-radius: 10px;
            }
        """)
        list_card_layout = QVBoxLayout(list_card)
        list_card_layout.setContentsMargins(10, 10, 10, 10)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                color: #ffffff;
                border: none;
                outline: none;
                font-size: 14px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px 8px;
                margin: 4px 0;
                border-radius: 6px;
                background-color: rgba(255,255,255,0.03);
            }
            QListWidget::item:hover {
                background-color: rgba(0,242,255,0.10);
            }
            QListWidget::item:selected {
                background-color: rgba(0,242,255,0.18);
                border: 1px solid #00f2ff;
            }
        """)

        list_card_layout.addWidget(self.list_widget)

        right_layout.addWidget(self.list_title)
        right_layout.addWidget(list_card)

        main_layout.addWidget(left_widget, 2)
        main_layout.addWidget(right_widget, 1)

    # --- 工具函数 (完整保留) ---
    def _make_label(self, text, style):
        label = QLabel(text)
        label.setStyleSheet(style)
        return label

    def _project_root(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def resolve_image_path(self, raw_path):
        if not raw_path: return None
        raw_path = str(raw_path).strip()
        if os.path.isabs(raw_path) and os.path.exists(raw_path): return raw_path
        project_root = self._project_root()
        candidates = [
            os.path.join(project_root, raw_path),
            os.path.join(project_root, "data", "photos", raw_path),
            os.path.join(project_root, "data", raw_path),
        ]
        for path in candidates:
            if os.path.exists(path): return path
        return None

    def show_image_in_label(self, label, image_path, target_w, target_h, empty_text):
        real_path = self.resolve_image_path(image_path)
        if not real_path:
            label.clear()
            label.setText(empty_text)
            return False
        pixmap = QPixmap(real_path)
        if pixmap.isNull():
            label.clear()
            label.setText("图片加载失败")
            return False
        label.setPixmap(pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return True



    def display_new_record(self):
        """25秒触发一次的加载逻辑"""
        if self.current_display_count >= len(self.all_pending_records):
            self.timer_25s.stop()
            return

        data = self.all_pending_records[self.current_display_count]
        data['time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['spot'] = f"A-{self.current_display_count + 1:02d}"

        # 插入列表顶端
        text = f"[{data['type']}] {data['plate']}  |  {data['time'][-8:]}"
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, data)
        self.list_widget.insertItem(0, item)
        self.list_widget.setCurrentRow(0)

        self.update_ui_with_data(data)
        self.current_display_count += 1

    def update_ui_with_data(self, data):
        """全局界面刷新逻辑，包含增强型的小图模糊匹配"""
        self.value_plate.setText(data.get('plate', '--'))
        self.value_time.setText(data.get('time', '--'))
        self.value_spot.setText(data.get('spot', '--'))
        self.value_status.setText("正常识别")
        self.value_fee.setText("--")
        self.value_duration.setText("--")

        # 1. 大图显示
        self.show_image_in_label(self.img_label, data.get('photo_path'), 640, 480, "未找到大图")

        # 2. 增强型小图匹配逻辑 (忽略空格、大小写、后缀名)
        raw_name = data.get('raw_name', '')
        plate_real_path = None
        photos_dir = os.path.join(self._project_root(), "data", "photos")

        # 目标关键字：plate_ + 原始文件名 (全小写、去空格)
        target_key = f"plate_{raw_name}".lower().replace(" ", "")

        if os.path.exists(photos_dir):
            for filename in os.listdir(photos_dir):
                processed_filename = filename.lower().replace(" ", "")
                if processed_filename.startswith(target_key):
                    plate_real_path = os.path.join(photos_dir, filename)
                    break

        # 显示小图
        self.show_image_in_label(self.plate_img_label, plate_real_path, 150, 70, "暂无车牌图")

    def on_item_clicked(self, item):
        """点击列表条目时同步显示"""
        data = item.data(Qt.UserRole)
        self.update_ui_with_data(data)

    def refresh_data(self):
        """兼容性函数：手动触发刷新"""
        self.current_display_count = 0
        self.load_all_photos()

    def update_realtime(self, plate, photo_path, event_type):
        """主界面推送接口 (保持兼容)"""
        self.refresh_data()