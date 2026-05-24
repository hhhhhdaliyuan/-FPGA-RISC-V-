import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 尝试导入 3D 引擎
try:
    import pyvista as pv
    from pyvistaqt import QtInteractor
    PVISTA_AVAILABLE = True
except ImportError:
    PVISTA_AVAILABLE = False
    print("警告: pyvista 或 pyvistaqt 未安装，3D 功能将不可用")

# 统一配色方案
C_MAIN_BG = "#0d1b2a"
C_BLUE_GLOW = "#1b263b"
C_ACCENT = "#00f2ff"
C_PURPLE = "#7000ff"
C_PINK = "#ff0066"
C_GLASS_BG = "rgba(255, 255, 255, 12)"
C_GLASS_BORDER = "rgba(255, 255, 255, 25)"
C_TEXT = "#ffffff"


# ========================================================
# 2D 视图组件定义
# ========================================================
class Map2DWidget(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.spots_data = None
        self.setMinimumSize(800, 700)

    def update_data(self, data):
        self.spots_data = data
        self.update()

    def paintEvent(self, event):
        if self.spots_data is None or self.spots_data.empty:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rows, cols = 10, 5
        box_w, box_h = 110, 55
        spacing = 15

        start_x = (self.width() - (box_w + spacing) * cols) // 2
        start_y = (self.height() - (box_h + spacing) * rows) // 2

        for i, row in self.spots_data.iterrows():
            r, c = i // cols, i % cols
            x = start_x + c * (box_w + spacing)
            y = start_y + r * (box_h + spacing)
            rect = QRect(x, y, box_w, box_h)

            is_occ = row['Status'] == 1

            painter.setPen(QPen(QColor(C_ACCENT if not is_occ else C_PINK), 1))
            painter.setBrush(QColor(255, 255, 255, 10) if not is_occ else QColor(255, 0, 102, 30))
            painter.drawRoundedRect(rect, 5, 5)

            painter.setPen(QColor(255, 255, 255, 120))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(rect.adjusted(5, 5, 0, 0), Qt.AlignLeft | Qt.AlignTop, str(row['SpotNumber']))

            if is_occ:
                painter.setPen(QColor(C_TEXT))
                painter.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
                painter.drawText(rect, Qt.AlignCenter, str(row.get('CarPlate', '')))


# ========================================================
# 主地图窗口定义
# ========================================================
class MapWindow(QMainWindow):
    def __init__(self, db_manager, current_zone="A"):
        super().__init__()
        self.db = db_manager
        self.current_zone = current_zone

        self.setWindowTitle(f"实时监控 - {self.current_zone}区")
        self.setMinimumSize(1300, 850)

        self.car_actors = {}
        self.car_colors = {}
        self.spot_locations = {}
        self.car_mesh = None
        self.plotter = None
        self.is_3d_ready = False
        self.is_closing = False

        self.init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)

        if PVISTA_AVAILABLE:
            QTimer.singleShot(1000, self.init_3d_scene)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.central_widget.setObjectName("centralWidget")
        self.central_widget.setStyleSheet(
            f"""
            #centralWidget {{
                background: qradialgradient(
                    cx:0.5, cy:0.5, radius:1.2,
                    fx:0.5, fy:0.5,
                    stop:0 {C_BLUE_GLOW},
                    stop:1 {C_MAIN_BG}
                );
            }}
            """
        )

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(12, 10, 12, 10)
        self.main_layout.setSpacing(12)

        self.control_panel = self.create_control_panel()
        self.main_layout.addWidget(self.control_panel)

        self.view_container = QStackedWidget()
        self.view_container.setStyleSheet(
            f"""
            QStackedWidget {{
                background: {C_GLASS_BG};
                border: 1px solid {C_GLASS_BORDER};
                border-radius: 25px;
            }}
            """
        )

        if PVISTA_AVAILABLE:
            self.plotter_widget = QWidget()
            self.plotter_layout = QVBoxLayout(self.plotter_widget)
            self.plotter_layout.setContentsMargins(0, 0, 0, 0)
            self.view_container.addWidget(self.plotter_widget)

        self.map_2d = Map2DWidget(self.db)
        self.view_container.addWidget(self.map_2d)

        self.main_layout.addWidget(self.view_container, stretch=3)

    def create_control_panel(self):
        panel = QFrame()
        panel.setFixedWidth(300)
        panel.setStyleSheet(
            f"""
            background: {C_GLASS_BG};
            border: 1px solid {C_GLASS_BORDER};
            border-radius: 20px;
            """
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("孪生控制中心")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {C_ACCENT}; border:none;"
        )
        layout.addWidget(title)

        # 3D / 2D 切换
        self.btn_3d = QPushButton("🎮 3D 实时视图")
        self.btn_2d = QPushButton("📐 2D 平面图")

        btn_style = """
        QPushButton {
            background: rgba(255,255,255,10);
            color: white;
            padding: 12px;
            border-radius: 10px;
            border: none;
            font-size: 14px;
        }
        QPushButton:hover {
            background: rgba(0,242,255,20);
        }
        """

        self.btn_3d.setStyleSheet(btn_style)
        self.btn_2d.setStyleSheet(btn_style)

        layout.addWidget(self.btn_3d)
        layout.addWidget(self.btn_2d)

        if PVISTA_AVAILABLE:
            self.btn_3d.clicked.connect(lambda: self.view_container.setCurrentIndex(0))
            self.btn_2d.clicked.connect(lambda: self.view_container.setCurrentIndex(1))
        else:
            self.btn_3d.setEnabled(False)
            self.btn_2d.clicked.connect(lambda: self.view_container.setCurrentIndex(0))

        # 分区按钮
        zone_title = QLabel("区域切换")
        zone_title.setStyleSheet(f"color: {C_ACCENT}; font-size: 16px; font-weight: bold; border:none;")
        layout.addWidget(zone_title)

        zone_btn_style = """
        QPushButton {
            background: rgba(255,255,255,8);
            color: white;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,25);
            font-size: 13px;
            text-align: left;
        }
        QPushButton:hover {
            background: rgba(0,242,255,18);
            border: 1px solid rgba(0,242,255,80);
        }
        """

        self.zone_buttons = {}
        zone_names = {
            "A": "A区（核心停车区）",
            "B": "B区（临时停车区）",
            "C": "C区（长租停车区）",
            "D": "D区（新能源充电区）",
        }

        for z, text in zone_names.items():
            btn = QPushButton(text)
            btn.setStyleSheet(zone_btn_style)
            btn.clicked.connect(lambda _, zone=z: self.switch_zone(zone))
            layout.addWidget(btn)
            self.zone_buttons[z] = btn

        # 统计面板
        self.stats_labels = {}
        for name, key, color in [("已占用", "used", C_PINK), ("空闲中", "free", C_ACCENT)]:
            row = QHBoxLayout()

            label_name = QLabel(name)
            label_name.setStyleSheet("color: white; border:none; font-size: 15px;")

            val = QLabel("0")
            val.setStyleSheet(
                f"color: {color}; font-size: 20px; font-weight: 900; border:none;"
            )

            row.addWidget(label_name)
            row.addStretch()
            row.addWidget(val)

            layout.addLayout(row)
            self.stats_labels[key] = val

        self.zone_tip = QLabel(f"当前区域：{self.current_zone}区")
        self.zone_tip.setStyleSheet(f"color: rgba(255,255,255,0.75); font-size: 13px; border:none;")
        layout.addWidget(self.zone_tip)

        layout.addStretch()
        self.update_zone_button_style()
        return panel

    def update_zone_button_style(self):
        for z, btn in self.zone_buttons.items():
            if z == self.current_zone:
                btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0,242,255,30);
                    color: white;
                    padding: 10px;
                    border-radius: 8px;
                    border: 1px solid rgba(0,242,255,120);
                    font-size: 13px;
                    text-align: left;
                    font-weight: bold;
                }
                """)
            else:
                btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,8);
                    color: white;
                    padding: 10px;
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,25);
                    font-size: 13px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: rgba(0,242,255,18);
                    border: 1px solid rgba(0,242,255,80);
                }
                """)

    def switch_zone(self, zone):
        if zone == self.current_zone:
            return

        self.current_zone = zone
        self.setWindowTitle(f"实时监控 - {zone}区")
        self.zone_tip.setText(f"当前区域：{zone}区")
        self.update_zone_button_style()

        # 重新初始化 3D 视图
        if self.plotter:
            try:
                self.plotter.close()
            except Exception:
                pass
            self.plotter = None

        self.is_3d_ready = False
        self.car_actors.clear()
        self.car_colors.clear()
        self.spot_locations.clear()

        if PVISTA_AVAILABLE:
            QTimer.singleShot(100, self.init_3d_scene)

        self.refresh_data()

    # ========================================================
    # 工具函数
    # ========================================================
    def normalize_spot_number(self, val):
        s = str(val).strip()

        if not s:
            return s

        if s.upper().startswith("A"):
            digits = ''.join(ch for ch in s if ch.isdigit())
            if digits:
                return f"A{int(digits):03d}"
            return s.upper()

        if s.isdigit():
            return f"A{int(s):03d}"

        return s

    def get_car_color(self, spot_id):
        """
        为不同车位分配不同颜色，让车看起来更丰富。
        """
        palette = [
            "#e74c3c",  # 红
            "#3498db",  # 蓝
            "#2ecc71",  # 绿
            "#f1c40f",  # 黄
            "#9b59b6",  # 紫
            "#e67e22",  # 橙
            "#95a5a6",  # 银灰
            "#1abc9c",  # 青绿
            "#ecf0f1",  # 白
            "#34495e",  # 深灰
        ]
        idx = sum(ord(ch) for ch in spot_id) % len(palette)
        return palette[idx]

    def build_parking_spots(self, zone="A"):
        """
        为不同区域生成略有区别的布局。
        目前是演示版：A/B/C/D 区布局风格略不同。
        """
        spots = {}
        spot_idx = 1

        if zone == "A":
            y_zones = [500, 350, 150]
            x_start, x_step, groups = 280, 50, 16

        elif zone == "B":
            y_zones = [520, 340]
            x_start, x_step, groups = 300, 55, 18

        elif zone == "C":
            y_zones = [520, 380, 240, 100]
            x_start, x_step, groups = 260, 48, 14

        else:  # D 区
            y_zones = [470, 290]
            x_start, x_step, groups = 320, 60, 15

        for y_base in y_zones:
            for x_idx in range(groups):
                x_pos = x_start + x_idx * x_step

                s_id = f"A{spot_idx:03d}"
                spots[s_id] = {
                    "pos": (x_pos, y_base + 25, 0),
                    "angle": 0
                }
                spot_idx += 1

                s_id = f"A{spot_idx:03d}"
                spots[s_id] = {
                    "pos": (x_pos, y_base - 25, 0),
                    "angle": 180
                }
                spot_idx += 1

        return spots

    def load_and_prepare_car_model(self, model_path):
        raw_mesh = pv.read(model_path)

        if isinstance(raw_mesh, pv.MultiBlock):
            merged = None
            for block in raw_mesh:
                if block is not None and block.n_points > 0:
                    if merged is None:
                        merged = block.copy()
                    else:
                        merged = merged.merge(block)
            if merged is None:
                raise ValueError("car.obj 读取后为空")
            raw_mesh = merged

        raw_mesh.translate(-np.array(raw_mesh.center), inplace=True)
        raw_mesh.rotate_x(90, inplace=True)
        raw_mesh.rotate_z(180, inplace=True)
        raw_mesh.translate(-np.array(raw_mesh.center), inplace=True)

        b = raw_mesh.bounds
        x_len = b[1] - b[0]
        y_len = b[3] - b[2]
        z_len = b[5] - b[4]
        max_dim = max(x_len, y_len, z_len)

        if max_dim <= 0:
            raise ValueError("车辆模型尺寸异常")

        scale_factor = 30.0 / max_dim
        raw_mesh.scale([scale_factor, scale_factor, scale_factor], inplace=True)

        b = raw_mesh.bounds
        raw_mesh.translate([0, 0, -b[4]], inplace=True)

        return raw_mesh

    def create_fallback_car_model(self):
        body = pv.Cube(center=(0, 0, 6), x_length=26, y_length=14, z_length=8)
        head = pv.Cone(center=(15, 0, 6), direction=(1, 0, 0), height=10, radius=5, resolution=20)
        car = body.merge(head)
        return car

    # ========================================================
    # 3D 场景初始化
    # ========================================================
    def init_3d_scene(self):
        if not PVISTA_AVAILABLE or self.plotter is not None or self.is_closing:
            return

        try:
            self.plotter = QtInteractor(self.plotter_widget)
            self.plotter_layout.addWidget(self.plotter.interactor)
            self.plotter.set_background("#20313d")

            self.car_mesh = None
            model_path = os.path.join("models", "car.obj")

            if os.path.exists(model_path):
                try:
                    self.car_mesh = self.load_and_prepare_car_model(model_path)
                    print(f"成功加载车辆模型: {model_path}")
                except Exception as e:
                    print(f"读取 car.obj 失败，改用备用模型。原因: {e}")

            if self.car_mesh is None:
                self.car_mesh = self.create_fallback_car_model()
                print("使用备用车辆模型")

            # 地面
            ground = pv.Plane(center=(700, 300, 0), i_size=2200, j_size=1600)
            self.plotter.add_mesh(ground, color="#243744", smooth_shading=True)

            # 功能房间（不同区位置稍作区别）
            if self.current_zone == "A":
                room1 = pv.Box(bounds=(140, 240, 200, 400, 0, 50))
                room2 = pv.Box(bounds=(800, 1100, 500, 750, 0, 50))
            elif self.current_zone == "B":
                room1 = pv.Box(bounds=(160, 300, 500, 700, 0, 50))
                room2 = pv.Box(bounds=(950, 1200, 140, 360, 0, 50))
            elif self.current_zone == "C":
                room1 = pv.Box(bounds=(200, 350, 600, 780, 0, 50))
                room2 = pv.Box(bounds=(980, 1180, 450, 680, 0, 50))
            else:
                room1 = pv.Box(bounds=(180, 340, 180, 360, 0, 50))
                room2 = pv.Box(bounds=(900, 1180, 520, 760, 0, 50))

            self.plotter.add_mesh(room1, color="#cfd8dc", opacity=0.68)
            self.plotter.add_mesh(room2, color="#c8d6e5", opacity=0.68)

            self.spot_locations.clear()
            self.car_actors.clear()
            self.car_colors.clear()

            spots = self.build_parking_spots(self.current_zone)

            for s_id, info in spots.items():
                x_pos, y_pos, z_pos = info["pos"]
                angle = info["angle"]

                self.spot_locations[s_id] = (x_pos, y_pos, z_pos)

                rect_outline = pv.Box(
                    bounds=(
                        x_pos - 22, x_pos + 22,
                        y_pos - 24, y_pos + 24,
                        0.5, 1.0
                    )
                ).outline()

                self.plotter.add_mesh(
                    rect_outline,
                    color="white",
                    opacity=0.65,
                    line_width=1
                )

                car = self.car_mesh.copy()
                car.rotate_z(angle, point=(0, 0, 0), inplace=True)
                car.translate([x_pos, y_pos, 1.2], inplace=True)

                car_color = self.get_car_color(s_id)
                actor = self.plotter.add_mesh(
                    car,
                    color=car_color,
                    smooth_shading=True
                )
                actor.SetVisibility(False)
                self.car_actors[s_id] = actor
                self.car_colors[s_id] = car_color

            # 道路黄虚线
            for x_line in range(250, 1250, 100):
                dash = pv.Plane(center=(x_line, 250, 1), i_size=40, j_size=5)
                self.plotter.add_mesh(dash, color="#f1c40f")

            # 减速带
            hump_positions = {
                "A": [260, 750, 1100],
                "B": [320, 860],
                "C": [280, 640, 980],
                "D": [360, 760, 1160],
            }
            for x_hump in hump_positions.get(self.current_zone, [260, 750, 1100]):
                hump = pv.Box(bounds=(x_hump - 12, x_hump + 12, 50, 600, 0, 3))
                self.plotter.add_mesh(hump, color="#d4a017")

            # 摄像机视角
            self.plotter.camera_position = [
                (1550, -200, 900),
                (700, 300, 0),
                (0, 0, 1)
            ]
            self.plotter.camera.zoom(1.15)

            self.is_3d_ready = True
            print(f"{self.current_zone}区 3D 场景初始化完成，共生成 {len(self.car_actors)} 个车位")

            self.timer.start(1500)
            self.refresh_data()

        except Exception as e:
            print(f"3D 场景初始化失败: {e}")

    # ========================================================
    # 数据刷新
    # ========================================================
    def refresh_data(self):
        try:
            df = self.db.get_all_spots()
            stats = self.db.get_statistics()

            self.stats_labels['used'].setText(str(stats.get('used_spots', 0)))
            self.stats_labels['free'].setText(str(stats.get('free_spots', 0)))

            if df is not None:
                self.map_2d.update_data(df)

            if self.is_3d_ready and self.plotter and not self.plotter._closed:
                occupied_spots = set()

                if df is not None and not df.empty:
                    occ_df = df[df['Status'] == 1].copy()

                    for _, row in occ_df.iterrows():
                        sid = self.normalize_spot_number(row['SpotNumber'])
                        occupied_spots.add(sid)

                for s_id, actor in self.car_actors.items():
                    actor.SetVisibility(s_id in occupied_spots)

                self.plotter.update()

        except Exception as e:
            print(f"数据刷新异常: {e}")

    # ========================================================
    # 窗口关闭
    # ========================================================
    def closeEvent(self, event):
        self.is_closing = True
        self.is_3d_ready = False

        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()

        if self.plotter:
            try:
                self.plotter.close()
                self.plotter = None
            except Exception:
                pass

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MapWindow(None, current_zone="A")
    win.show()
    sys.exit(app.exec_())