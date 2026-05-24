import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from jinja2 import Environment, FileSystemLoader

# --- Pyecharts 导入 ---
from pyecharts.charts import Pie, Bar, Line, Grid
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode

# 全局Pyecharts主题配置
CYAN_COLOR = "#00ffff"
DARK_CYAN = "#008080"
TEXT_COLOR = "#fff"


def get_base_opts():
    """返回基础的暗色主题配置"""
    return opts.InitOpts(
        theme="dark",
        bg_color="transparent",
        width="100%",
        height="100%"
    )


# --- Web 与 Python 的通信桥梁 ---
class WebBridge(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    @pyqtSlot()
    def openMap(self):
        self.main_window.open_map_window()

    @pyqtSlot()
    def openVehicle(self):
        self.main_window.open_vehicle_management()

    @pyqtSlot()
    def openRecord(self):
        self.main_window.open_record_query()

    @pyqtSlot()
    def openMonitor(self):
        self.main_window.open_security_monitor()


class MainWindow(QMainWindow):
    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.total_capacity = 200

        # --- 1. 后端与模拟器初始化 (完全保留) ---
        self.init_backend()

        # 窗口设置
        self.setWindowTitle("CYBER PARKING OS - v4.0")
        self.setMinimumSize(1280, 850)

        # --- 2. 界面初始化 (替换为内嵌网页) ---
        self.init_ui()

        # --- 3. 开启全局定时器 (3秒刷新一次主界面数据) ---
        self.dashboard_timer = QTimer(self)
        self.dashboard_timer.timeout.connect(self.update_dashboard_stats)
        self.dashboard_timer.start(3000)

    def init_backend(self):
        """数据库与硬件模拟器核心逻辑"""
        try:
            from database.db_manager import DatabaseManager
            self.db = DatabaseManager()
        except Exception as e:
            print(f"数据库加载失败: {e}")
            self.db = None

        try:
            from hardware.simulator import HardwareSimulator
            self.hardware_simulator = HardwareSimulator(self.db)
            # 连接硬件实时检测信号
           # self.hardware_simulator.car_detected.connect(self.on_car_detected)
            #self.hardware_simulator.start_simulation(interval=25000)
        except Exception as e:
            print(f"模拟器加载失败: {e}")
            self.hardware_simulator = None

    def init_ui(self):
        # 1. 创建内嵌浏览器作为主界面
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        # 2. 建立 WebChannel 通信通道
        self.channel = QWebChannel()
        self.bridge = WebBridge(self)
        self.channel.registerObject("pybridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        # 3. 生成初始图表并加载 HTML
        self.load_web_dashboard()

    def generate_charts(self, stats):
        """生成 Pyecharts HTML 字符串"""
        # A. 停车位统计 圆环图
        occupancy_chart = (
            Pie(init_opts=get_base_opts())
            .add(
                "",
                [("已占用", stats["occupied_spots"]), ("空闲", stats["free_spots"])],
                radius=["65%", "85%"],
                center=["55%", "50%"],
                label_opts=opts.LabelOpts(is_show=False),
            )
            .set_colors([CYAN_COLOR, "#fadb14"])
            .set_global_opts(legend_opts=opts.LegendOpts(is_show=False))
            .render_embed()
        )

        # B. 今日进出车辆次数 折线图
        hours = [str(i) for i in range(0, 25, 2)]
        entries = [100, 150, 300, 500, 650, 400, 200, 150, 100, 80, 50, 30, 20]
        exits = [50, 80, 120, 200, 350, 500, 450, 300, 200, 150, 100, 80, 50]
        line_chart = (
            Line(init_opts=get_base_opts())
            .add_xaxis(hours)
            .add_yaxis("进入", entries, is_smooth=True, color=CYAN_COLOR, label_opts=opts.LabelOpts(is_show=False),
                       areastyle_opts=opts.AreaStyleOpts(opacity=0.3, color=CYAN_COLOR))
            .add_yaxis("离开", exits, is_smooth=True, color="#fadb14", label_opts=opts.LabelOpts(is_show=False),
                       areastyle_opts=opts.AreaStyleOpts(opacity=0.2, color="#fadb14"))
            .set_global_opts(
                legend_opts=opts.LegendOpts(pos_top="2%", pos_right="5%",
                                            textstyle_opts=opts.TextStyleOpts(color=TEXT_COLOR, font_size=10)),
                xaxis_opts=opts.AxisOpts(
                    axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=DARK_CYAN)),
                    axislabel_opts=opts.LabelOpts(color=TEXT_COLOR, font_size=10),
                    axistick_opts=opts.AxisTickOpts(is_show=False)),
                yaxis_opts=opts.AxisOpts(
                    axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=DARK_CYAN)),
                    axislabel_opts=opts.LabelOpts(color=TEXT_COLOR, font_size=10),
                    axistick_opts=opts.AxisTickOpts(is_show=False), splitline_opts=opts.SplitLineOpts(is_show=True,
                                                                                                      linestyle_opts=opts.LineStyleOpts(
                                                                                                          color="rgba(255,255,255,0.05)"))),
            )
        )
        grid_chart = Grid(init_opts=get_base_opts()).add(line_chart,
                                                         grid_opts=opts.GridOpts(pos_left="10%", pos_right="10%",
                                                                                 pos_top="20%", pos_bottom="15%",
                                                                                 is_contain_label=True))
        entry_exit_chart = grid_chart.render_embed()

        # C. 停车场各区车位使用率 横向柱状图
        districts = ["A区", "B区", "C区", "D区", "E区", "F区"]
        usage_rates = [71, 23, 33, 62, 41, 86]
        district_usage_chart = (
            Bar(init_opts=get_base_opts())
            .add_xaxis(districts)
            .add_yaxis("使用率", usage_rates, color=CYAN_COLOR, category_gap="40%",
                       label_opts=opts.LabelOpts(is_show=True, position="right", formatter="{c}%", color=CYAN_COLOR))
            .reversal_axis()
            .set_global_opts(
                legend_opts=opts.LegendOpts(is_show=False),
                xaxis_opts=opts.AxisOpts(max_=100, axislabel_opts=opts.LabelOpts(formatter="{value}%"),
                                         axisline_opts=opts.AxisLineOpts(
                                             linestyle_opts=opts.LineStyleOpts(color=DARK_CYAN))),
                yaxis_opts=opts.AxisOpts(
                    axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=DARK_CYAN))),
            )
            .render_embed()
        )

        # D. 停车场收入分布 饼图
        income_data = [("停车收费", 65), ("充电收费", 20), ("停车收费", 15)]
        income_dist_chart = (
            Pie(init_opts=get_base_opts())
            .add("", income_data, radius=["65%", "85%"], center=["50%", "50%"],
                 label_opts=opts.LabelOpts(is_show=False))
            .set_colors([CYAN_COLOR, "#1890ff", "#722ed1"])
            .set_global_opts(
                legend_opts=opts.LegendOpts(is_show=False),
                title_opts=opts.TitleOpts(title="总收入", subtitle="5,940", pos_left="25%", pos_top="center",
                                          title_textstyle_opts=opts.TextStyleOpts(color=TEXT_COLOR, font_size=15),
                                          subtitle_textstyle_opts=opts.TextStyleOpts(color=CYAN_COLOR, font_size=20,
                                                                                     font_weight="bold"))
            )
            .render_embed()
        )

        # E. 停车场月收入趋势 柱状图
        months = [str(i) for i in range(1, 13)]
        monthly_income = [5, 8, 12, 10, 15, 18, 20, 16, 14, 11, 9, 7]
        monthly_income_chart = (
            Bar(init_opts=get_base_opts())
            .add_xaxis(months)
            .add_yaxis("收入(W)", monthly_income, color=CYAN_COLOR, itemstyle_opts=opts.ItemStyleOpts(color=JsCode(
                "new echarts.graphic.LinearGradient(0, 0, 0, 1, [{offset: 0, color: '#00ffff'}, {offset: 1, color: 'rgba(0, 255, 255, 0.1)'}])")))
            .set_global_opts(
                legend_opts=opts.LegendOpts(is_show=False),
                xaxis_opts=opts.AxisOpts(
                    axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=DARK_CYAN))),
                yaxis_opts=opts.AxisOpts(
                    axisline_opts=opts.AxisLineOpts(linestyle_opts=opts.LineStyleOpts(color=DARK_CYAN))),
            )
            .render_embed()
        )

        return {
            "occupancy_chart": occupancy_chart,
            "entry_exit_chart": entry_exit_chart,
            "district_usage_chart": district_usage_chart,
            "income_dist_chart": income_dist_chart,
            "monthly_income_chart": monthly_income_chart
        }

    def load_web_dashboard(self):
        """使用 Jinja2 渲染 HTML 并加载到浏览器"""
        # 设置模板路径 (假设在项目根目录的 templates 文件夹内)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(base_dir, 'templates')

        env = Environment(loader=FileSystemLoader(template_dir))
        try:
            template = env.get_template('dashboard.html')
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载 HTML 模板: {e}\n请确保 templates/dashboard.html 存在。")
            return

        now = datetime.now()
        db_stats = self.db.get_statistics() if self.db else {}
        stats = {
            "total_spots": db_stats.get("total_spots", self.total_capacity),
            "occupied_spots": db_stats.get("used_spots", 0),
            "free_spots": db_stats.get("free_spots", self.total_capacity)
        }
        charts = self.generate_charts(stats)

        # === 修改这里：从数据库获取真实的最新进出记录 ===
        records = self.db.get_today_records() if self.db else []
        # 获取第一条类型为"入口"和"出口"的记录，找不到则给个默认值
        current_entry = next((r for r in records if r['type'] == '入口'),
                             {"plate": "等待入场...", "spot": "-", "time": "-", "status": "-"})
        current_exit = next((r for r in records if r['type'] == '出口'),
                            {"plate": "等待出场...", "spot": "-", "duration": "-", "fee": "-"})

        # 将入场时间的字符串截取，只保留时分秒 (去掉日期) 让界面更清爽
        if current_entry.get("time") and len(current_entry["time"]) > 10:
            current_entry["time"] = current_entry["time"][-8:]

        alarm_events = [
            {"time": "03-10-2023 01:22", "location": "B区", "info": "摄像机过热", "level": "normal"},
            {"time": "03-11-2023 18:01", "location": "C区", "info": "违规停放", "level": "high"}
        ]

        html_content = template.render(
            current_date=now.strftime("%Y-%m-%d | %A"),
            current_time=now.strftime("%H:%M:%S"),
            stats=stats,
            current_entry=current_entry,
            current_exit=current_exit,
            alarm_events=alarm_events,
            **charts
        )

        # 设置基础路径以加载本地图片 (如 1.png)
        base_url = QUrl.fromLocalFile(template_dir + os.sep)
        self.browser.setHtml(html_content, base_url)

    def update_dashboard_stats(self):
        if not self.db: return
        try:
            stats = self.db.get_statistics()
            total = 200  # 强制总数为 200
            occupied = stats.get('used_spots', 0)
            available = total - occupied

            # === 新增：获取最新进出记录 ===
            records = self.db.get_today_records()
            latest_entry = next((r for r in records if r['type'] == '入口'),
                                {"plate": "-", "spot": "-", "time": "-", "status": "-"})
            latest_exit = next((r for r in records if r['type'] == '出口'),
                               {"plate": "-", "spot": "-", "duration": "-", "fee": "-"})
            entry_time_str = latest_entry.get("time", "-")[-8:] if len(latest_entry.get("time", "-")) > 10 else "-"

            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d | %A")
            current_time = now.strftime("%H:%M:%S")

            js_code = f"""
                            if (document.getElementById('sys_date')) document.getElementById('sys_date').innerText = '{current_date}';
                            if (document.getElementById('sys_time')) document.getElementById('sys_time').innerText = '{current_time}';
                            if (document.getElementById('val_total')) document.getElementById('val_total').innerText = '{total}';
                            if (document.getElementById('val_occ')) document.getElementById('val_occ').innerText = '{occupied}';
                            if (document.getElementById('val_free')) document.getElementById('val_free').innerText = '{available}';

                            // 实时更新入口信息
                            if (document.getElementById('entry_plate')) document.getElementById('entry_plate').innerText = '{latest_entry.get("plate", "-")}';
                            if (document.getElementById('entry_spot')) document.getElementById('entry_spot').innerText = '{latest_entry.get("spot", "-")}';
                            if (document.getElementById('entry_time')) document.getElementById('entry_time').innerText = '{entry_time_str}';
                            if (document.getElementById('entry_status')) document.getElementById('entry_status').innerText = '{latest_entry.get("status", "-")}';

                            // 实时更新出口信息
                            if (document.getElementById('exit_plate')) document.getElementById('exit_plate').innerText = '{latest_exit.get("plate", "-")}';
                            if (document.getElementById('exit_spot')) document.getElementById('exit_spot').innerText = '{latest_exit.get("spot", "-")}';
                            if (document.getElementById('exit_duration')) document.getElementById('exit_duration').innerText = '{latest_exit.get("duration", "-")}';
                            if (document.getElementById('exit_fee')) document.getElementById('exit_fee').innerText = '{latest_exit.get("fee", "-")}';
                        """
            self.browser.page().runJavaScript(js_code)

        except Exception as e:
            print(f"数据更新错误: {e}")

    def on_car_detected(self, plate, photo, event_type):
        """当硬件模拟器检测到车辆时的统一处理入口 (保留原始逻辑)"""
        self.db.process_car_entry(plate, photo)
        self.update_dashboard_stats()

        if hasattr(self, 'monitor_win') and self.monitor_win and self.monitor_win.isVisible():
            self.monitor_win.update_realtime(plate, photo, event_type)

        if hasattr(self, 'map_win') and self.map_win and self.map_win.isVisible():
            self.map_win.refresh_data()

    # --- 窗口跳转逻辑 (保留原始逻辑) ---
    def open_map_window(self):
        if not self.db:
            QMessageBox.warning(self, "错误", "数据库未连接，无法查看地图")
            return

        try:
            # 弹出赛博风格的分区选择框
            items = ["A区 (核心停车区)", "B区 (临时停车区)", "C区 (长租停车区)", "D区 (新能源充电区)"]
            zone_map = {"A区 (核心停车区)": "A", "B区 (临时停车区)": "B", "C区 (长租停车区)": "C",
                        "D区 (新能源充电区)": "D"}

            # 使用 QInputDialog 快速实现选择
            item, ok = QInputDialog.getItem(self, "区域选择", "请选择要巡检的停车场区域:", items, 0, False)

            if ok and item:
                selected_zone = zone_map[item]
                from ui.map_window import MapWindow
                # 打开地图，并将选择的区域传进去
                self.map_win = MapWindow(self.db)
                # 如果你的 MapWindow 已经写好了过滤逻辑，这里就生效了
                self.map_win.setWindowTitle(f"实时监控 - {item}")
                self.map_win.show()

        except Exception as e:
            QMessageBox.critical(self, "跳转失败", f"无法进入地图模块: {e}")
    def open_vehicle_management(self):
        try:
            from ui.vehicle_management import VehicleManagementWindow
            self.v_win = VehicleManagementWindow(self.db)
            self.v_win.show()
        except Exception as e:
            print(e)

    def open_record_query(self):
        try:
            from ui.record_query_window import RecordQueryWindow
            self.record_win = RecordQueryWindow(self.db)
            self.record_win.show()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开统计界面: {e}")

    def open_security_monitor(self):
        try:
            from ui.security_monitor_window import SecurityMonitorWindow
            self.monitor_win = SecurityMonitorWindow(self.db)
            self.monitor_win.show()
        except Exception as e:
            print(f"打开监控失败: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow({"username": "CyberManager"})
    win.show()
    sys.exit(app.exec_())