# database/db_manager.py
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random


class DatabaseManager:
    def __init__(self, db_path="parking_system.db"):
        self.db_path = db_path
        self.init_database()
        print(f"数据库初始化完成: {db_path}")

    def init_database(self):
        """初始化数据库表并扩充至200个车位"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 1. 车位表：存储当前状态，用于地图联动
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parking_spots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spot_number TEXT UNIQUE NOT NULL,
                    spot_location TEXT,
                    status INTEGER DEFAULT 0,
                    car_plate TEXT,
                    entry_time DATETIME,
                    photo_path TEXT
                )
            ''')

            # 2. 停车记录表：存储所有历史，用于流水监控
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parking_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    car_plate TEXT NOT NULL,
                    spot_number TEXT NOT NULL,
                    entry_time DATETIME NOT NULL,
                    exit_time DATETIME,
                    duration_minutes INTEGER DEFAULT 0,
                    fee REAL DEFAULT 0,
                    photo_path TEXT,
                    status TEXT DEFAULT 'active'
                )
            ''')

            # 3. 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'admin',
                    create_time DATETIME
                )
            ''')

            # 4. 收费配置
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fee_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fee_per_hour REAL DEFAULT 5.0,
                    free_minutes INTEGER DEFAULT 15,
                    max_daily_fee REAL DEFAULT 50.0
                )
            ''')

            # 5. 初始化 200 个车位 (ABCD区)
            cursor.execute("SELECT COUNT(*) FROM parking_spots")
            current_count = cursor.fetchone()[0]

            if current_count < 200:
                print("正在初始化或扩充200个车位数据...")
                zones = ['A', 'B', 'C', 'D']
                spots_per_zone = 50

                for zone in zones:
                    for i in range(1, spots_per_zone + 1):
                        spot_num = f"{zone}{i:02d}"  # 生成 A01, A02... D50
                        location = f"{zone}区{i}号"
                        cursor.execute(
                            "INSERT OR IGNORE INTO parking_spots (spot_number, spot_location, status) VALUES (?, ?, 0)",
                            (spot_num, location)
                        )

            # 6. 初始化默认管理员
            cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin', 'admin')")

            # 统一提交所有更改
            conn.commit()

        except Exception as e:
            print(f"数据库初始化异常: {e}")

        finally:
            # 无论是否发生异常，确保在这里统一安全关闭数据库连接
            if conn:
                conn.close()
    def get_today_records(self):
        """
        核心联动查询：获取今日进出记录。
        确保键名（plate, time, type等）与 UI 代码完全对应。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")

        # 联合查询，确保即使车位变动，记录依然保留位置信息
        query = """
            SELECT 
                car_plate, entry_time, exit_time, photo_path, 
                status, spot_number, duration_minutes, fee
            FROM parking_records 
            WHERE date(entry_time) = ? OR date(exit_time) = ?
            ORDER BY id DESC
        """
        cursor.execute(query, (today, today))
        rows = cursor.fetchall()

        records = []
        for row in rows:
            plate, entry_t, exit_t, path, status, spot, duration, fee = row

            # 入场事件
            records.append({
                "plate": plate,
                "time": entry_t,
                "type": "入口",
                "photo_path": path,
                "spot": spot,
                "duration": f"{duration} 分钟" if exit_t else "计时中...",
                "fee": f"¥{fee:.2f}" if exit_t else "计算中...",
                "status": "在场" if status == 'active' else "已离场"
            })

            # 如果已经出场，增加一条出场记录展示
            if exit_t:
                records.insert(0, {
                    "plate": plate,
                    "time": exit_t,
                    "type": "出口",
                    "photo_path": path,
                    "spot": spot,
                    "duration": f"{duration} 分钟",
                    "fee": f"¥{fee:.2f}",
                    "status": "已离场"
                })

        conn.close()
        return records

    def process_car_entry(self, car_plate, photo_path):
        """处理车辆入场：唯一的数据写入入口"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. 检查是否重复
        cursor.execute("SELECT spot_number FROM parking_spots WHERE car_plate=? AND status=1", (car_plate,))
        if cursor.fetchone():
            conn.close()
            return None, "车辆已在场内"

        # 2. 分配车位
        cursor.execute("SELECT spot_number FROM parking_spots WHERE status = 0 ORDER BY id LIMIT 1")
        res = cursor.fetchone()
        if not res:
            conn.close()
            return None, "车位已满"

        spot_num = res[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3. 同步更新两张表，确保地图(spots)和流水(records)同步
        cursor.execute("UPDATE parking_spots SET status=1, car_plate=?, entry_time=?, photo_path=? WHERE spot_number=?",
                       (car_plate, now, photo_path, spot_num))

        cursor.execute(
            "INSERT INTO parking_records (car_plate, spot_number, entry_time, photo_path, status) VALUES (?, ?, ?, ?, 'active')",
            (car_plate, spot_num, now, photo_path))

        conn.commit()
        conn.close()
        return {'spot_number': spot_num, 'entry_time': now}, "入场成功"

    def process_car_exit(self, car_plate):
        """处理车辆出场，并同步更新地图车位状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. 查找当前停车记录
        cursor.execute(
            "SELECT spot_number, entry_time FROM parking_records WHERE car_plate = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (car_plate,)
        )
        res = cursor.fetchone()

        if not res:
            conn.close()
            return None, "未找到该车入场记录"

        spot_num, entry_t_str = res
        entry_t = datetime.strptime(entry_t_str, "%Y-%m-%d %H:%M:%S")
        exit_t = datetime.now()

        # 2. 计算时长与费用 (默认 5元/小时)
        duration = int((exit_t - entry_t).total_seconds() / 60)
        fee = round(max(0, (duration / 60) * 5), 2)
        now_str = exit_t.strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 3. 更新流水记录表 (使用真实的参数替代之前的省略号)
            cursor.execute(
                "UPDATE parking_records SET status='completed', exit_time=?, duration_minutes=?, fee=? WHERE car_plate=? AND status='active'",
                (now_str, duration, fee, car_plate)
            )

            # 4. 释放车位表 (让地图上的车消失的关键)
            cursor.execute(
                "UPDATE parking_spots SET status=0, car_plate=NULL, entry_time=NULL, photo_path=NULL WHERE car_plate=?",
                (car_plate,)
            )

            conn.commit()
        except Exception as e:
            print(f"数据库执行出场错误: {e}")
        finally:
            conn.close()

        return {'spot_number': spot_num, 'fee': fee, 'duration': duration}, "出场成功"

    def get_statistics(self):
        """主界面仪表盘核心数据源"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM parking_spots")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM parking_spots WHERE status = 1")
        used = cursor.fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COALESCE(SUM(fee), 0) FROM parking_records WHERE date(exit_time) = ?", (today,))
        income = cursor.fetchone()[0]
        conn.close()
        return {
            'total_spots': total,
            'used_spots': used,
            'free_spots': total - used,
            'today_income': income,
            'occupancy_rate': round((used / total) * 100, 1) if total > 0 else 0
        }

    # --- 保持其他查询方法功能不变 ---
    def get_all_spots(self):
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT spot_number as SpotNumber, status as Status, car_plate as CarPlate, entry_time as EntryTime, photo_path as PhotoPath FROM parking_spots",
            conn)
        conn.close()
        return df

    def get_active_records(self):
        """获取当前停车记录"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT car_plate AS CarPlate, spot_number AS SpotNumber,
                   entry_time AS EntryTime, photo_path AS PhotoPath
            FROM parking_records
            WHERE status = 'active'
            ORDER BY entry_time DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def authenticate(self, u, p):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT username, role FROM users WHERE username=? AND password=?", (u, p))
        res = c.fetchone()
        conn.close()
        return res

    def get_all_records(self, limit=100, offset=0, search_plate=""):
        """获取所有记录，确保列名与 RecordQueryWindow 匹配"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT car_plate AS CarPlate, spot_number AS SpotNumber,
                   entry_time AS EntryTime, exit_time AS ExitTime,
                   duration_minutes AS Duration, fee AS Fee, status AS Status
            FROM parking_records
            WHERE 1=1
        """
        params = []
        if search_plate:
            query += " AND car_plate LIKE ?"
            params.append(f"%{search_plate}%")
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

