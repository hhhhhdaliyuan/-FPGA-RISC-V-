# ui/record_query_window.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd
from datetime import datetime


class RecordQueryWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setWindowTitle("收费查询")
        self.setGeometry(200, 200, 1200, 700)
        self.setStyleSheet("background-color: #050a1e;")

        self.current_page = 0
        self.page_size = 20

        self.init_ui()
        self.load_records()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("📋 收费查询")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00d2ff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 查询条件区域
        search_frame = QFrame()
        search_frame.setStyleSheet("background-color: rgba(10,30,60,180); border-radius: 10px; padding: 10px;")
        search_layout = QHBoxLayout(search_frame)

        # 修改：搜索标签设为黄色
        search_label = QLabel("车牌号:")
        search_label.setStyleSheet("color: #ffff00; font-weight: bold; font-size: 14px;")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入车牌号查询")
        self.search_input.setStyleSheet("padding: 8px; border-radius: 5px; color: white;")
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("🔍 查询")
        self.search_btn.clicked.connect(self.search_records)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d2ff;
                color: #ffff00; 
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00f2ff;
            }
        """)
        search_layout.addWidget(self.search_btn)

        self.reset_btn = QPushButton("🔄 重置")
        self.reset_btn.clicked.connect(self.reset_search)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #7000ff;
                color: white; 
                padding: 8px 20px;
                border-radius: 5px;
            }
        """)
        search_layout.addWidget(self.reset_btn)

        search_layout.addStretch()
        layout.addWidget(search_frame)

        # 统计信息栏
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: rgba(10,30,60,180); border-radius: 10px; padding: 10px;")
        stats_layout = QHBoxLayout(stats_frame)

        self.stats_labels = {}
        stats = [("总记录数", "total"), ("今日入场", "today_entry"), ("今日收入", "today_income")]
        for name, key in stats:
            frame = QFrame()
            frame.setStyleSheet("background-color: rgba(0,0,0,0.3); border-radius: 5px; padding: 5px;")
            f_layout = QVBoxLayout(frame)

            # 修改：将这里的统计标题也设置为黄色发光字体
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #ffff00; font-weight: bold; font-size: 14px;")
            name_label.setAlignment(Qt.AlignCenter)
            f_layout.addWidget(name_label)

            label = QLabel("0")
            label.setStyleSheet("font-size: 20px; font-weight: bold; color: #00d2ff;")
            label.setAlignment(Qt.AlignCenter)
            f_layout.addWidget(label)
            stats_layout.addWidget(frame)
            self.stats_labels[key] = label

        stats_layout.addStretch()
        layout.addWidget(stats_frame)

        # 记录表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["车牌号", "车位号", "入场时间", "出场时间", "时长(分钟)", "费用(元)", "状态"])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(0,0,0,0.5);
                color: white;
                border: 1px solid #00d2ff;
                border-radius: 5px;
                gridline-color: #1a2a4a;
            }
            QHeaderView::section {
                background-color: #00d2ff;
                color: #ffff00; 
                padding: 8px;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #00d2ff;
                color: #ffff00; 
            }
        """)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # 分页控制
        page_frame = QFrame()
        page_layout = QHBoxLayout(page_frame)
        page_layout.addStretch()

        self.prev_btn = QPushButton("◀ 上一页")
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        self.prev_btn.setStyleSheet("color: white;")
        page_layout.addWidget(self.prev_btn)

        self.page_label = QLabel("第 1 页")
        self.page_label.setStyleSheet("color: #ffff00; font-weight: bold; padding: 5px 15px;")  # 顺手把页码也变成黄色
        page_layout.addWidget(self.page_label)

        self.next_btn = QPushButton("下一页 ▶")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setStyleSheet("color: white;")
        page_layout.addWidget(self.next_btn)

        page_layout.addStretch()
        layout.addWidget(page_frame)

        # 导出按钮
        export_btn = QPushButton("📊 导出Excel")
        export_btn.clicked.connect(self.export_to_excel)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d2ff;
                color: #ffff00; 
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        layout.addWidget(export_btn)

    def load_records(self):
        """加载记录"""
        df = self.db.get_all_records(self.page_size, self.current_page * self.page_size,
                                     self.search_text if hasattr(self, 'search_text') else "")
        self.display_records(df)
        self.update_stats()

    def search_records(self):
        """搜索记录"""
        self.search_text = self.search_input.text().strip()
        self.current_page = 0
        self.load_records()

    def reset_search(self):
        """重置搜索"""
        self.search_input.clear()
        self.search_text = ""
        self.current_page = 0
        self.load_records()

    def display_records(self, df):
        """显示记录"""
        self.table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.table.setItem(i, 0, QTableWidgetItem(str(row['CarPlate'])))
            self.table.setItem(i, 1, QTableWidgetItem(str(row['SpotNumber'])))
            self.table.setItem(i, 2, QTableWidgetItem(str(row['EntryTime'])))
            self.table.setItem(i, 3, QTableWidgetItem(str(row['ExitTime']) if pd.notna(row['ExitTime']) else '进行中'))
            self.table.setItem(i, 4, QTableWidgetItem(str(row['Duration']) if pd.notna(row['Duration']) else '-'))
            self.table.setItem(i, 5, QTableWidgetItem(f"¥{row['Fee']:.2f}" if pd.notna(row['Fee']) else '-'))

            status_item = QTableWidgetItem("🟢 进行中" if row['Status'] == 'active' else "✅ 已完成")
            if row['Status'] == 'active':
                status_item.setForeground(QColor(0, 210, 255))
            else:
                status_item.setForeground(QColor(0, 255, 0))
            self.table.setItem(i, 6, status_item)

        # 调整列宽
        self.table.resizeColumnsToContents()

    def update_stats(self):
        """更新统计信息，增加安全检查"""
        try:
            stats = self.db.get_statistics()
            # 这里调用 get_all_records(1) 只是为了快速获取总数，不建议加载10000条
            all_data_count = len(self.db.get_all_records(100000))
            self.stats_labels['total'].setText(str(all_data_count))
            self.stats_labels['today_entry'].setText(str(stats.get('today_entries', 0)))
            self.stats_labels['today_income'].setText(f"¥{stats.get('today_income', 0):.2f}")
        except Exception as e:
            print(f"统计更新失败: {e}")

    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_records()
            self.update_page_buttons()

    def next_page(self):
        """下一页"""
        self.current_page += 1
        self.load_records()
        self.update_page_buttons()

    def update_page_buttons(self):
        """更新分页按钮状态"""
        self.page_label.setText(f"第 {self.current_page + 1} 页")
        self.prev_btn.setEnabled(self.current_page > 0)

    def export_to_excel(self):
        """导出到Excel"""
        try:
            # 导出时不分页
            df = self.db.get_all_records(100000, 0)
            if df.empty:
                QMessageBox.warning(self, "提示", "当前没有记录可供导出")
                return
            filename = f"停车记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            QMessageBox.information(self, "导出成功", f"已导出到: {filename}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"请确保已安装 openpyxl 库: {e}")