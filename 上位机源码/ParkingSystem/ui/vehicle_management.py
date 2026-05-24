# ui/vehicle_management.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class VehicleManagementWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setWindowTitle("车辆管理")
        self.setGeometry(300, 300, 1000, 600)
        self.setStyleSheet("background-color: #050a1e;")

        self.init_ui()
        self.load_current_parking()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("🚗 当前停车车辆")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00d2ff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["车牌号", "车位号", "入场时间", "操作"])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(0,0,0,0.5);
                color: white;
                border: 1px solid #00d2ff;
            }
            QHeaderView::section {
                background-color: #00d2ff;
                color: #ffff00; /* 表头深色已修改为黄色 */
                padding: 5px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_current_parking)
        # 刷新按钮字体也设为黄色
        refresh_btn.setStyleSheet("color: #ffff00; font-weight: bold; padding: 10px; background-color: #00d2ff; border-radius: 5px;")
        layout.addWidget(refresh_btn)

    def load_current_parking(self):
        df = self.db.get_active_records()
        self.table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.table.setItem(i, 0, QTableWidgetItem(row['CarPlate']))
            self.table.setItem(i, 1, QTableWidgetItem(row['SpotNumber']))
            self.table.setItem(i, 2, QTableWidgetItem(row['EntryTime']))

            btn = QPushButton("出场")
            # 这里的系统按钮字体强制设置为黄色
            btn.setStyleSheet("color: #ffff00; font-weight: bold; background-color: rgba(0,210,255,0.2); border: 1px solid #00d2ff; border-radius: 3px;")
            btn.clicked.connect(lambda checked, plate=row['CarPlate']: self.car_exit(plate))
            self.table.setCellWidget(i, 3, btn)

    def car_exit(self, car_plate):
        # 确认 process_car_exit 返回的字典键名
        result, msg = self.db.process_car_exit(car_plate)
        if result:
            # 根据你 db_manager 的实现，可能是 'duration_minutes' 或 'duration'
            # 建议在弹窗时做个兼容处理
            duration = result.get('duration_minutes') or result.get('duration', 0)
            fee = result.get('fee', 0.0)

            QMessageBox.information(self, "成功",
                                    f"车辆 {car_plate} 已出场\n费用: ¥{fee:.2f}\n时长: {duration}分钟")
            self.load_current_parking()
        else:
            QMessageBox.warning(self, "失败", msg)