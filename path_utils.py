# path_utils.py
import sys
import os
from pathlib import Path

def get_base_path():
    """دریافت مسیر پایه برنامه (برای exe و حالت عادی)"""
    if getattr(sys, 'frozen', False):
        # اجرا به صورت exe
        return sys._MEIPASS
    else:
        # اجرا به صورت اسکریپت
        return os.path.dirname(os.path.abspath(__file__))

def get_data_path():
    """دریافت مسیر ذخیره دیتابیس و تنظیمات (در AppData)"""
    app_data = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / "ImanAccounting"
    app_data.mkdir(parents=True, exist_ok=True)
    return str(app_data)

def get_license_path():
    """دریافت مسیر فایل لایسنس"""
    # اول کنار exe نگاه کن
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
    license_file = os.path.join(exe_dir, "license.key")
    if os.path.exists(license_file):
        return license_file
    # بعد در مسیر داده
    data_license = os.path.join(get_data_path(), "license.key")
    if os.path.exists(data_license):
        return data_license
    return None