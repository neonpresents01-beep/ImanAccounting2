# utils/global_date.py
# -*- coding: utf-8 -*-

"""
سرویس مرکزی تاریخ - دریافت تاریخ از هدر برنامه
تمام تاریخ‌های برنامه از این سرویس گرفته می‌شود
"""

import jdatetime
from datetime import datetime

# متغیرهای سراسری
_current_jalali_date = None
_current_gregorian_date = None


def set_current_date(jalali_date_str=None):
    """
    تنظیم تاریخ جاری (از هدر برنامه)
    این تابع از main_window صدا زده می‌شود
    """
    global _current_jalali_date, _current_gregorian_date
    
    if jalali_date_str:
        _current_jalali_date = jalali_date_str
        # تبدیل به میلادی برای ذخیره در دیتابیس
        try:
            if '/' in jalali_date_str:
                parts = jalali_date_str.split('/')
                if len(parts) == 3:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    jalali = jdatetime.date(year, month, day)
                    gregorian = jalali.togregorian()
                    _current_gregorian_date = gregorian.strftime("%Y-%m-%d")
                else:
                    _current_gregorian_date = datetime.now().strftime("%Y-%m-%d")
            else:
                _current_gregorian_date = datetime.now().strftime("%Y-%m-%d")
        except Exception as e:
            print(f"⚠️ خطا در تبدیل تاریخ: {e}")
            _current_gregorian_date = datetime.now().strftime("%Y-%m-%d")
    else:
        # استفاده از تاریخ امروز
        refresh()


def refresh():
    """به‌روزرسانی تاریخ جاری با تاریخ امروز"""
    global _current_jalali_date, _current_gregorian_date
    _current_jalali_date = jdatetime.date.today().strftime("%Y/%m/%d")
    _current_gregorian_date = datetime.now().strftime("%Y-%m-%d")


def get_current_jalali():
    """دریافت تاریخ جاری شمسی (همون چیزی که در هدر می‌بینیم)"""
    global _current_jalali_date
    if _current_jalali_date is None:
        refresh()
    return _current_jalali_date


def get_current_gregorian():
    """دریافت تاریخ جاری میلادی برای ذخیره در دیتابیس"""
    global _current_gregorian_date
    if _current_gregorian_date is None:
        refresh()
    return _current_gregorian_date


def get_current_for_display(date_system="شمسی"):
    """دریافت تاریخ جاری برای نمایش بر اساس سیستم تاریخ"""
    if date_system == "شمسی":
        return get_current_jalali()
    else:
        return get_current_gregorian()


def convert_to_gregorian_for_db(jalali_date_str):
    """
    تبدیل تاریخ شمسی به میلادی برای ذخیره در دیتابیس
    """
    if not jalali_date_str:
        return get_current_gregorian()
    
    try:
        if '/' in jalali_date_str:
            parts = jalali_date_str.split('/')
            if len(parts) == 3:
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                jalali = jdatetime.date(year, month, day)
                gregorian = jalali.togregorian()
                return gregorian.strftime("%Y-%m-%d")
    except:
        pass
    
    return get_current_gregorian()


def get_today_display():
    """دریافت تاریخ امروز برای نمایش"""
    return jdatetime.date.today().strftime("%Y/%m/%d")


def get_today_for_db():
    """دریافت تاریخ امروز برای ذخیره در دیتابیس"""
    return datetime.now().strftime("%Y-%m-%d")


# راه‌اندازی اولیه
refresh()