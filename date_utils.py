# utils/date_helper.py
# -*- coding: utf-8 -*-

"""
کمک‌کننده تاریخ با persiantools - جایگزین ساده برای date_utils
"""

from PyQt5.QtWidgets import QDateEdit
from PyQt5.QtCore import QDate, pyqtSignal
from persiantools.jdatetime import JalaliDate
import datetime


class JalaliDateEdit(QDateEdit):
    """ویجت انتخاب تاریخ شمسی با persiantools"""
    
    dateChangedSignal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy/MM/dd")
        today = JalaliDate.today()
        self.setDate(QDate(today.year, today.month, today.day))
        self.dateChanged.connect(self._on_date_changed)
    
    def _on_date_changed(self):
        self.dateChangedSignal.emit()
    
    def get_gregorian(self):
        """دریافت تاریخ میلادی برای ذخیره در دیتابیس"""
        qdate = self.date()
        jalali = JalaliDate(qdate.year(), qdate.month(), qdate.day())
        gregorian = jalali.to_gregorian()
        return gregorian
    
    def get_gregorian_str(self):
        """دریافت تاریخ میلادی به صورت رشته"""
        return self.get_gregorian().strftime("%Y-%m-%d")
    
    def get_display(self):
        """دریافت تاریخ برای نمایش"""
        return self.date().toString("yyyy/MM/dd")
    
    def get_shamsi(self):
        """دریافت تاریخ شمسی برای ذخیره مستقیم"""
        qdate = self.date()
        return f"{qdate.year():04d}/{qdate.month():02d}/{qdate.day():02d}"
    
    def set_from_gregorian(self, gregorian_date_str):
        """تنظیم ویجت از روی تاریخ میلادی"""
        if not gregorian_date_str:
            return
        try:
            gregorian_date_str = gregorian_date_str.replace('/', '-')
            if '-' in gregorian_date_str:
                parts = gregorian_date_str.split('-')
                if len(parts) == 3:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    jalali = JalaliDate.to_jalali(year, month, day)
                    self.setDate(QDate(jalali.year, jalali.month, jalali.day))
        except:
            pass
    
    def set_from_shamsi(self, shamsi_date_str):
        """تنظیم ویجت از روی تاریخ شمسی"""
        if not shamsi_date_str:
            return
        try:
            shamsi_date_str = shamsi_date_str.replace('-', '/')
            if '/' in shamsi_date_str:
                parts = shamsi_date_str.split('/')
                if len(parts) == 3:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    self.setDate(QDate(year, month, day))
        except:
            pass
    
    def today(self):
        """تاریخ امروز (برای سازگاری با کدهای قدیمی)"""
        today = JalaliDate.today()
        return QDate(today.year, today.month, today.day)


def safe_display_date(date_value):
    """تبدیل ایمن تاریخ برای نمایش"""
    if not date_value:
        return ""
    
    date_str = str(date_value).strip()
    
    # حذف زمان
    if 'T' in date_str:
        date_str = date_str.split('T')[0]
    if ' ' in date_str:
        date_str = date_str.split(' ')[0]
    
    # تبدیل خط تیره به اسلش
    date_str = date_str.replace('-', '/')
    
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            try:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                
                # اگر سال میلادی است (1900-2100)
                if 1900 <= year <= 2100:
                    jalali = JalaliDate.to_jalali(year, month, day)
                    return jalali.strftime("%Y/%m/%d")
                # اگر سال شمسی است (1300-1500)
                elif 1300 <= year <= 1500:
                    return f"{year:04d}/{month:02d}/{day:02d}"
            except:
                pass
    
    return date_str


def get_today_jalali():
    """تاریخ امروز شمسی"""
    return JalaliDate.today().strftime("%Y/%m/%d")


def get_today_gregorian():
    """تاریخ امروز میلادی"""
    return datetime.date.today().strftime("%Y-%m-%d")


def convert_jalali_to_gregorian(jalali_str):
    """تبدیل شمسی به میلادی"""
    if not jalali_str:
        return get_today_gregorian()
    try:
        jalali_str = jalali_str.replace('-', '/')
        if '/' in jalali_str:
            parts = jalali_str.split('/')
            if len(parts) == 3:
                jalali = JalaliDate(int(parts[0]), int(parts[1]), int(parts[2]))
                return jalali.to_gregorian().strftime("%Y-%m-%d")
    except:
        pass
    return get_today_gregorian()


def convert_gregorian_to_jalali(gregorian_str):
    """تبدیل میلادی به شمسی"""
    if not gregorian_str:
        return get_today_jalali()
    try:
        gregorian_str = gregorian_str.replace('/', '-')
        if '-' in gregorian_str:
            parts = gregorian_str.split('-')
            if len(parts) == 3:
                jalali = JalaliDate.to_jalali(int(parts[0]), int(parts[1]), int(parts[2]))
                return jalali.strftime("%Y/%m/%d")
    except:
        pass
    return get_today_jalali()


def convert_display_date(date_value):
    """نام مستعار برای safe_display_date"""
    return safe_display_date(date_value)


class DateUtils:
    """کلاس کمکی برای سازگاری با کدهای قدیمی"""
    
    @staticmethod
    def today_jalali_str(format_str="%Y/%m/%d"):
        return get_today_jalali()
    
    @staticmethod
    def get_date_system():
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'date_system'")
                row = c.fetchone()
                return row[0] if row else "شمسی"
        except:
            return "شمسی"
    
    @staticmethod
    def refresh_date_system():
        pass
    
    @staticmethod
    def to_display(date_value):
        return safe_display_date(date_value)
    
    @staticmethod
    def to_jalali_str(gregorian_date, format_str="%Y/%m/%d"):
        if not gregorian_date:
            return ""
        return convert_gregorian_to_jalali(str(gregorian_date))