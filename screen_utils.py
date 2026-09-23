# -*- coding: utf-8 -*-
"""
مدیریت تنظیمات صفحه نمایش - نسخه کامل با متدهای get_scaled
"""

from PyQt5.QtWidgets import QApplication, QDesktopWidget
from PyQt5.QtCore import QRect
import sys


class ScreenManager:
    """مدیریت تنظیمات صفحه نمایش"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """مقداردهی اولیه"""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        # دریافت اندازه صفحه
        screen = self.app.primaryScreen()
        if screen:
            self.geometry = screen.geometry()
        else:
            desktop = QDesktopWidget()
            self.geometry = desktop.availableGeometry()
        
        self.width = self.geometry.width()
        self.height = self.geometry.height()
        
        # تنظیمات پایه
        self.base_width = 1366
        self.base_height = 768
        
        # محاسبه اسکیل
        self.scale_x = self.width / self.base_width
        self.scale_y = self.height / self.base_height
        self.scale = min(self.scale_x, self.scale_y, 1.0)
        
        # حداقل اسکیل
        if self.scale < 0.4:
            self.scale = 0.4
        
        # تشخیص نوع دستگاه
        self.device_type = self._detect_device_type()
        
        # ========== متدهای جدید برای سازگاری ==========
        # برای استفاده در accounting_widget.py و سایر ویجت‌ها
    
    def _detect_device_type(self):
        """تشخیص نوع دستگاه بر اساس اندازه صفحه"""
        if self.width >= 1920 and self.height >= 1080:
            return "Full HD (1920x1080)"
        elif self.width >= 1366 and self.height >= 768:
            return "HD (1366x768)"
        elif self.width >= 1024 and self.height >= 600:
            return "Netbook (1024x600)"
        elif self.width >= 800 and self.height >= 480:
            return "Tablet (800x480)"
        elif self.width >= 360 and self.height >= 640:
            return "Mobile (360x640)"
        else:
            return f"Custom ({self.width}x{self.height})"
    
    # ======================== متدهای اصلی ========================
    
    def get_scaled(self, value: int) -> int:
        """
        دریافت مقدار اسکیل شده
        
        Args:
            value: مقدار پایه
            
        Returns:
            مقدار اسکیل شده
        """
        return max(2, int(value * self.scale))
    
    def get_font_size(self, size: int) -> int:
        """
        دریافت سایز فونت اسکیل شده
        
        Args:
            size: سایز پایه
            
        Returns:
            سایز فونت اسکیل شده
        """
        # محدودیت برای دستگاه‌های مختلف
        if self.device_type == "Mobile (360x640)":
            return max(min(size, 12), 8)
        elif self.device_type == "Tablet (800x480)":
            return max(min(size, 14), 10)
        else:
            return max(min(int(size * self.scale), 16), 8)
    
    def get_scaled_size(self, base_width: int, base_height: int, scale_factor: float = 1.0):
        """
        دریافت اندازه اسکیل شده
        
        Args:
            base_width: عرض پایه
            base_height: ارتفاع پایه
            scale_factor: فاکتور اسکیل اضافی
            
        Returns:
            (عرض اسکیل شده, ارتفاع اسکیل شده)
        """
        w = int(base_width * self.scale * scale_factor)
        h = int(base_height * self.scale * scale_factor)
        return max(w, 200), max(h, 150)
    
    def get_spacing(self, base_spacing: int = 10) -> int:
        """
        دریافت فاصله اسکیل شده
        
        Args:
            base_spacing: فاصله پایه
            
        Returns:
            فاصله اسکیل شده
        """
        return max(int(base_spacing * self.scale), 5)
    
    def get_margin(self, base_margin: int = 20) -> int:
        """
        دریافت حاشیه اسکیل شده
        
        Args:
            base_margin: حاشیه پایه
            
        Returns:
            حاشیه اسکیل شده
        """
        return max(int(base_margin * self.scale), 5)
    
    def get_padding(self, base_padding: int = 10) -> int:
        """
        دریافت padding اسکیل شده
        
        Args:
            base_padding: padding پایه
            
        Returns:
            padding اسکیل شده
        """
        return max(int(base_padding * self.scale), 4)
    
    # ======================== متدهای کمکی ========================
    
    def is_small_screen(self) -> bool:
        """آیا صفحه کوچک است؟"""
        return self.width < 1024 or self.height < 600
    
    def is_medium_screen(self) -> bool:
        """آیا صفحه متوسط است؟"""
        return 1024 <= self.width < 1440
    
    def is_large_screen(self) -> bool:
        """آیا صفحه بزرگ است؟"""
        return self.width >= 1440
    
    def center_window(self, window):
        """مرکز کردن پنجره"""
        screen_rect = self.geometry
        window_rect = window.geometry()
        x = screen_rect.x() + (screen_rect.width() - window_rect.width()) // 2
        y = screen_rect.y() + (screen_rect.height() - window_rect.height()) // 2
        window.move(max(screen_rect.x(), x), max(screen_rect.y(), y))
    
    def resize_window(self, window, base_width=None, base_height=None, 
                      scale_factor=1.0, center=True, max_size=None):
        """تغییر اندازه پنجره"""
        if base_width is None or base_height is None:
            current = window.geometry()
            base_width = current.width()
            base_height = current.height()
        
        w, h = self.get_scaled_size(base_width, base_height, scale_factor)
        if max_size:
            w = min(w, max_size[0])
            h = min(h, max_size[1])
        
        window.resize(w, h)
        if center:
            self.center_window(window)
    
    def get_device_info(self) -> dict:
        """دریافت اطلاعات دستگاه"""
        return {
            'width': self.width,
            'height': self.height,
            'scale': self.scale,
            'device_type': self.device_type,
            'is_small': self.is_small_screen(),
            'is_medium': self.is_medium_screen(),
            'is_large': self.is_large_screen()
        }


class WindowResizer:
    """کمک‌کننده برای تغییر اندازه پنجره"""
    
    def __init__(self, window, base_width=None, base_height=None, 
                 scale_factor=1.0, center=True, max_size=None):
        self.window = window
        self.base_width = base_width
        self.base_height = base_height
        self.scale_factor = scale_factor
        self.center = center
        self.max_size = max_size
        self.screen_manager = ScreenManager()
        self.apply()
    
    def apply(self):
        """اعمال تغییرات"""
        self.screen_manager.resize_window(
            self.window, self.base_width, self.base_height,
            self.scale_factor, self.center, self.max_size
        )
        self._adjust_fonts()
        self._adjust_layouts()
    
    def _adjust_fonts(self):
        """تنظیم فونت‌ها"""
        font_size = self.screen_manager.get_font_size(10)
        font = self.window.font()
        font.setPointSize(font_size)
        self.window.setFont(font)
    
    def _adjust_layouts(self):
        """تنظیم layoutها"""
        spacing = self.screen_manager.get_spacing(10)
        margin = self.screen_manager.get_margin(20)
        layout = self.window.layout()
        if layout:
            layout.setSpacing(spacing)
            layout.setContentsMargins(margin, margin, margin, margin)


def setup_dialog(dialog, base_width=None, base_height=None, 
                 scale_factor=1.0, center=True, max_size=None):
    """
    تنظیم سریع دیالوگ
    
    Args:
        dialog: دیالوگ مورد نظر
        base_width: عرض پایه
        base_height: ارتفاع پایه
        scale_factor: فاکتور اسکیل
        center: مرکز کردن
        max_size: حداکثر اندازه (width, height)
    """
    WindowResizer(dialog, base_width, base_height, scale_factor, center, max_size)


def get_screen_manager():
    """دریافت نمونه ScreenManager"""
    return ScreenManager()


def get_scaled(value: int) -> int:
    """راهنمای سریع برای get_scaled"""
    return ScreenManager().get_scaled(value)


def get_font_size(size: int) -> int:
    """راهنمای سریع برای get_font_size"""
    return ScreenManager().get_font_size(size)


# ======================== برای سازگاری با نسخه‌های قدیمی ========================
# این متدها برای سازگاری با کدهای قدیمی اضافه شده‌اند

def get_scaled_size(width, height):
    """سازگاری با نسخه‌های قدیمی"""
    sm = ScreenManager()
    return sm.get_scaled_size(width, height)

def get_spacing(base=10):
    """سازگاری با نسخه‌های قدیمی"""
    return ScreenManager().get_spacing(base)

def get_margin(base=20):
    """سازگاری با نسخه‌های قدیمی"""
    return ScreenManager().get_margin(base)
