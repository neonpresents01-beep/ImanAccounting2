# utils/shamsi_date.py
# -*- coding: utf-8 -*-

"""
ویجت تقویم شمسی مستقل برای استفاده در پروژه اصلی
کاملاً جدا از QDateEdit و بدون تداخل میلادی
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from persiantools.jdatetime import JalaliDate
from datetime import datetime


# ============================================================
# توابع تبدیل تاریخ
# ============================================================

def shamsi_to_gregorian(shamsi_date: str) -> str:
    """تبدیل تاریخ شمسی به میلادی
    ورودی: '1404/06/07'  ->  خروجی: '2025-08-29'
    """
    if not shamsi_date:
        return datetime.now().strftime("%Y-%m-%d")
    
    try:
        shamsi_date = shamsi_date.replace('-', '/')
        parts = shamsi_date.split('/')
        if len(parts) == 3:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            
            # بررسی اینکه سال شمسی است یا میلادی
            if 1300 <= year <= 1500:
                jalali = JalaliDate(year, month, day)
                gregorian = jalali.to_gregorian()
                return gregorian.strftime("%Y-%m-%d")
            else:
                return f"{year:04d}-{month:02d}-{day:02d}"
    except Exception as e:
        print(f"⚠️ خطا در تبدیل شمسی به میلادی: {e}")
    
    return shamsi_date


def gregorian_to_shamsi(gregorian_date: str) -> str:
    """تبدیل تاریخ میلادی به شمسی
    ورودی: '2025-08-29'  ->  خروجی: '1404/06/07'
    """
    if not gregorian_date:
        return get_today_jalali()
    
    try:
        gregorian_date = gregorian_date.replace('/', '-')
        parts = gregorian_date.split('-')
        if len(parts) == 3:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            
            # بررسی اینکه سال میلادی است یا شمسی
            if 1900 <= year <= 2100:
                gregorian = datetime(year, month, day)
                jalali = JalaliDate.to_jalali(gregorian)
                return f"{jalali.year:04d}/{jalali.month:02d}/{jalali.day:02d}"
            else:
                return f"{year:04d}/{month:02d}/{day:02d}"
    except Exception as e:
        print(f"⚠️ خطا در تبدیل میلادی به شمسی: {e}")
    
    return gregorian_date


def safe_display_date(date_value) -> str:
    """نمایش ایمن تاریخ"""
    if not date_value:
        return ""
    
    date_str = str(date_value)
    
    # اگر تاریخ شمسی است
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            try:
                year = int(parts[0])
                if 1300 <= year <= 1500:
                    return date_str
            except:
                pass
    
    # اگر تاریخ میلادی است، تبدیل به شمسی کن
    return gregorian_to_shamsi(date_str)


def get_today_jalali() -> str:
    """دریافت تاریخ امروز به صورت شمسی"""
    try:
        today = JalaliDate.today()
        return f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
    except:
        return datetime.now().strftime("%Y/%m/%d")


# ============================================================
# ویجت تقویم شمسی
# ============================================================

class ShamsiCalendar(QDialog):
    """دیالوگ تقویم شمسی"""
    
    dateSelected = pyqtSignal(str)
    
    def __init__(self, parent=None, initial_date=None):
        super().__init__(parent)
        self.setWindowTitle("انتخاب تاریخ شمسی")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        today = JalaliDate.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_day = today.day
        
        if initial_date:
            try:
                if '/' in initial_date:
                    parts = initial_date.split('/')
                    if len(parts) == 3:
                        self.current_year = int(parts[0])
                        self.current_month = int(parts[1])
                        self.selected_day = int(parts[2])
            except:
                pass
        
        self.init_ui()
        self.show_month()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # header
        header = QHBoxLayout()
        
        prev_year_btn = QPushButton("<<")
        prev_year_btn.clicked.connect(self.prev_year)
        header.addWidget(prev_year_btn)
        
        prev_month_btn = QPushButton("<")
        prev_month_btn.clicked.connect(self.prev_month)
        header.addWidget(prev_month_btn)
        
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header.addWidget(self.month_label)
        
        next_month_btn = QPushButton(">")
        next_month_btn.clicked.connect(self.next_month)
        header.addWidget(next_month_btn)
        
        next_year_btn = QPushButton(">>")
        next_year_btn.clicked.connect(self.next_year)
        header.addWidget(next_year_btn)
        
        layout.addLayout(header)
        
        # days header
        days_layout = QHBoxLayout()
        weekdays = ["ش", "ی", "د", "س", "چ", "پ", "ج"]
        for day in weekdays:
            label = QLabel(day)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold; color: #666; font-size: 12pt;")
            days_layout.addWidget(label)
        layout.addLayout(days_layout)
        
        # calendar grid
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(5)
        layout.addLayout(self.calendar_grid)
        
        # buttons
        btn_layout = QHBoxLayout()
        
        today_btn = QPushButton("📅 امروز")
        today_btn.clicked.connect(self.go_today)
        btn_layout.addWidget(today_btn)
        
        btn_layout.addStretch()
        
        select_btn = QPushButton("✅ انتخاب")
        select_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 20px;")
        select_btn.clicked.connect(self.select_date)
        btn_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setFixedSize(450, 420)
    
    def show_month(self):
        """نمایش ماه جاری"""
        for i in reversed(range(self.calendar_grid.count())):
            widget = self.calendar_grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        self.month_label.setText(f"{month_names[self.current_month - 1]} {self.current_year}")
        
        first_day = JalaliDate(self.current_year, self.current_month, 1)
        start_weekday = first_day.weekday()
        
        if self.current_month in [1, 2, 3, 4, 5, 6]:
            days_in_month = 31
        elif self.current_month in [7, 8, 9, 10, 11]:
            days_in_month = 30
        else:
            days_in_month = 30 if JalaliDate.is_leap(self.current_year) else 29
        
        row, col = 0, start_weekday
        today = JalaliDate.today()
        
        for day in range(1, days_in_month + 1):
            btn = QPushButton(str(day))
            btn.setFixedSize(45, 45)
            btn.clicked.connect(lambda checked, d=day: self.select_day(d))
            
            if day == self.selected_day:
                btn.setStyleSheet("background-color: #2196F3; color: white; border-radius: 22px; font-weight: bold;")
            elif day == today.day and self.current_year == today.year and self.current_month == today.month:
                btn.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 22px; font-weight: bold;")
            else:
                btn.setStyleSheet("background-color: #f5f5f5; border-radius: 22px;")
            
            self.calendar_grid.addWidget(btn, row, col)
            
            col += 1
            if col >= 7:
                col = 0
                row += 1
    
    def select_day(self, day):
        self.selected_day = day
        self.show_month()
    
    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.show_month()
    
    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.show_month()
    
    def prev_year(self):
        self.current_year -= 1
        self.show_month()
    
    def next_year(self):
        self.current_year += 1
        self.show_month()
    
    def go_today(self):
        today = JalaliDate.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_day = today.day
        self.show_month()
    
    def select_date(self):
        date_str = f"{self.current_year:04d}/{self.current_month:02d}/{self.selected_day:02d}"
        self.dateSelected.emit(date_str)
        self.accept()


# ============================================================
# ویجت ورودی تاریخ شمسی
# ============================================================

class ShamsiDateEdit(QWidget):
    """ویجت ورودی تاریخ شمسی - جایگزین QDateEdit"""
    
    dateChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_valid_date = None
        self.init_ui()
        
        today = JalaliDate.today()
        self.set_date(f"{today.year:04d}/{today.month:02d}/{today.day:02d}")
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("1403/01/01")
        self.date_input.setAlignment(Qt.AlignCenter)
        self.date_input.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 5px; background-color: white; font-size: 11pt;")
        self.date_input.returnPressed.connect(self.validate_input)
        layout.addWidget(self.date_input)
        
        self.calendar_btn = QPushButton("📅")
        self.calendar_btn.setMaximumWidth(40)
        self.calendar_btn.setToolTip("انتخاب از تقویم")
        self.calendar_btn.clicked.connect(self.open_calendar)
        layout.addWidget(self.calendar_btn)
    
    def validate_input(self):
        text = self.date_input.text().strip()
        if self.is_valid_shamsi_date(text):
            self._last_valid_date = text
            self.dateChanged.emit(text)
        else:
            QMessageBox.warning(self, "خطا", "فرمت تاریخ نامعتبر است!\nمثال صحیح: 1403/01/01")
            if self._last_valid_date:
                self.date_input.setText(self._last_valid_date)
    
    def is_valid_shamsi_date(self, date_str):
        if not date_str or '/' not in date_str:
            return False
        parts = date_str.split('/')
        if len(parts) != 3:
            return False
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1300 <= y <= 1500):
                return False
            if not (1 <= m <= 12):
                return False
            if m in [1, 2, 3, 4, 5, 6]:
                return 1 <= d <= 31
            elif m in [7, 8, 9, 10, 11]:
                return 1 <= d <= 30
            else:
                max_day = 30 if JalaliDate.is_leap(y) else 29
                return 1 <= d <= max_day
        except:
            return False
    
    def open_calendar(self):
        dialog = ShamsiCalendar(self, self.get_date())
        dialog.dateSelected.connect(self.set_date)
        dialog.exec_()
    
    def set_date(self, date_str):
        if self.is_valid_shamsi_date(date_str):
            self._last_valid_date = date_str
            self.date_input.setText(date_str)
            self.dateChanged.emit(date_str)
    
    def get_date(self):
        return self.date_input.text()
    
    def get_shamsi(self):
        return self.get_date()
