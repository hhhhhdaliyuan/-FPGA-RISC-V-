# 数据库配置
DB_CONFIG = {
    'server': 'localhost',  # SQL Server地址
    'database': 'ParkingSystem',
    'username': '',  # 使用Windows认证时留空
    'password': '',  # 使用Windows认证时留空
    'driver': '{ODBC Driver 17 for SQL Server}'
}

# 系统配置
SYSTEM_CONFIG = {
    'hardware_simulator': True,  # 是否使用硬件模拟器
    'auto_refresh_interval': 3000,  # 自动刷新间隔(ms)
    'max_history_days': 90  # 历史数据保留天数
}

# 收费标准配置
PARKING_FEES = {
    'first_hour': 5.0,  # 首小时收费
    'additional_hour': 2.0,  # 续费每小时
    'daily_max': 30.0  # 每日封顶
}