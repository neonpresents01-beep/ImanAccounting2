# ui/main_window.py
# ============================================================
# پنجره اصلی ImanAccount - نسخه 5.0 (Clean + Core-Integrated)
# ============================================================

import sys
import os
import traceback
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

# ============================================================
# ✅ اطمینان از sys.path
# ============================================================

_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ============================================================
# PyQt5
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# ============================================================
# ماژول‌های پروژه (بدون utils)
# ============================================================

# مدیریت خطا
try:
    from error_handler import (
        get_logger,
        get_error_handler,
        safe_execute,
        row_to_dict,
        ValidationError,
        PermissionError,
    )
    ERROR_HANDLER_OK = True
except ImportError as e:
    print(f"⚠️ خطا در import error_handler: {e}")
    ERROR_HANDLER_OK = False
    
    # fallback
    import logging
    def get_logger():
        return logging.getLogger("ImanAccount")
    def get_error_handler():
        class SimpleHandler:
            def show_error(self, *a, **k): pass
            def show_warning(self, *a, **k): pass
            def show_info(self, *a, **k): pass
        return SimpleHandler()
    def safe_execute(f):
        return f
    def row_to_dict(row):
        if row is None:
            return {}
        try:
            return {k: row[k] for k in row.keys()}
        except Exception:
            return {}
    class ValidationError(Exception): pass
    class PermissionError(Exception): pass


# Screen Utils
try:
    from screen_utils import WindowResizer, ScreenManager
    SCREEN_UTILS_OK = True
except ImportError as e:
    print(f"⚠️ خطا در import screen_utils: {e}")
    SCREEN_UTILS_OK = False
    
    class ScreenManager:
        def __init__(self):
            self.width = 1920
            self.height = 1080
            self.scale = 1.0
        def get_scaled(self, v): return v
        def get_font_size(self, s): return s
        def get_spacing(self, v=10): return v
        def get_margin(self, v=10): return v
        def get_padding(self, v=10): return v
        def center_window(self, w): pass
    
    class WindowResizer:
        def __init__(self, window, *a, **k): pass


# تاریخ
try:
    from shamsi_date import get_today_jalali, ShamsiDateEdit, safe_display_date
    DATE_OK = True
except ImportError as e:
    print(f"⚠️ خطا در import shamsi_date: {e}")
    DATE_OK = False
    def get_today_jalali():
        return datetime.now().strftime("%Y/%m/%d")
    def safe_display_date(d):
        return str(d) if d else ""


# مسیر
try:
    from path_utils import get_base_path
except ImportError:
    def get_base_path():
        return str(_PROJECT_ROOT)


# دیتابیس
try:
    from database import DatabaseManager
except ImportError as e:
    print(f"⚠️ خطا در import database: {e}")
    DatabaseManager = None


# BaseWindow
try:
    from ui.base_widgets import BaseWindow, BaseDialog, ThemeMixin
    BASE_WINDOW_OK = True
except ImportError as e:
    print(f"⚠️ خطا در import BaseWindow: {e}")
    BASE_WINDOW_OK = False
    BaseWindow = QMainWindow
    BaseDialog = QDialog
    class ThemeMixin:
        def get_theme_colors(self):
            return {
                'bg': "#f5f6fa", 'text': "#1a1a2e",
                'text_secondary': "#555555", 'card': "#ffffff",
                'border': "#dcdde1", 'hover': "#e8e8e8",
                'selected': "#1976D2", 'selected_text': "#ffffff",
                'is_dark': False,
            }


# Login
try:
    from ui.login_dialog import (
        LoginDialog, LockScreenDialog, ChangePasswordDialog, UserManager
    )
    LOGIN_OK = True
except ImportError as e:
    print(f"⚠️ خطا در import login_dialog: {e}")
    LOGIN_OK = False
    LoginDialog = None
    LockScreenDialog = None
    ChangePasswordDialog = None
    UserManager = None


# تم
try:
    from ui.styles.theme_manager import get_theme_manager
    THEME_OK = True
except ImportError as e:
    print(f"⚠️ خطا در import theme_manager: {e}")
    THEME_OK = False
    
    class SimpleThemeManager:
        _instance = None
        def __new__(cls):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._observers = []
                cls._instance._theme_name = 'light'
            return cls._instance
        def get_stylesheet(self): return ""
        def get_theme_name(self): return self._theme_name
        def set_theme(self, name):
            self._theme_name = name
            for cb in self._observers:
                try: cb(name)
                except: pass
        def toggle_theme(self):
            self.set_theme('dark' if self._theme_name == 'light' else 'light')
        def add_observer(self, cb):
            if cb not in self._observers:
                self._observers.append(cb)
        def remove_observer(self, cb):
            if cb in self._observers:
                self._observers.remove(cb)
        def get_available_themes(self):
            return {'light': '☀️ روشن', 'dark': '🌙 تاریک'}
        def is_dark(self):
            return self._theme_name == 'dark'
        def get_current_theme(self):
            class T:
                display_name = self._theme_name
            return T()
    
    _simple_theme = SimpleThemeManager()
    def get_theme_manager():
        return _simple_theme


# هسته مرکزی
try:
    from core import get_app_core, EventType
    CORE_OK = True
except ImportError as e:
    print(f"⚠️ AppCore در دسترس نیست: {e}")
    CORE_OK = False
    def get_app_core():
        return None
    class EventType:
        pass


# ============================================================
# Logger
# ============================================================

logger = get_logger()


# ============================================================
# Splash Screen
# ============================================================

class ImanSplashScreen(QSplashScreen):
    """اسپلش اسکرین"""
    
    def __init__(self):
        self._pixmap = self._create_splash_pixmap()
        super().__init__(self._pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self._progress = 0
        self._message = "⏳ در حال بارگذاری..."
    
    def _create_splash_pixmap(self) -> QPixmap:
        pixmap = QPixmap(520, 300)
        pixmap.fill(QColor(26, 26, 46))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(0, 0, 520, 4, QColor(233, 69, 96))
        
        painter.setPen(QColor(233, 69, 96))
        painter.setFont(QFont("Segoe UI", 30, QFont.Bold))
        painter.drawText(40, 80, "🧠 ImanAccount")
        
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(40, 115, "حسابداری هوشمند با هوش مصنوعی")
        
        painter.setPen(QColor(50, 50, 80))
        painter.drawLine(40, 135, 480, 135)
        
        painter.setPen(QColor(150, 150, 180))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(40, 165, "نسخه ۳.۰.۰")
        painter.drawText(40, 185, "© 2025 ImanAI")
        painter.drawText(40, 205, "🌐 imanai.ir")
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(50, 50, 80))
        painter.drawRoundedRect(40, 240, 440, 6, 3, 3)
        
        painter.setBrush(QColor(233, 69, 96))
        painter.drawRoundedRect(40, 240, 50, 6, 3, 3)
        
        painter.setPen(QColor(150, 150, 180))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(40, 275, "⏳ در حال بارگذاری...")
        
        painter.end()
        return pixmap
    
    def show_message(self, message: str, progress: int = 0):
        self._message = message
        self._progress = min(100, max(0, progress))
        
        new_pixmap = QPixmap(520, 300)
        new_pixmap.fill(QColor(26, 26, 46))
        painter = QPainter(new_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(0, 0, 520, 4, QColor(233, 69, 96))
        
        painter.setPen(QColor(233, 69, 96))
        painter.setFont(QFont("Segoe UI", 30, QFont.Bold))
        painter.drawText(40, 80, "🧠 ImanAccount")
        
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(40, 115, "حسابداری هوشمند با هوش مصنوعی")
        
        painter.setPen(QColor(50, 50, 80))
        painter.drawLine(40, 135, 480, 135)
        
        painter.setPen(QColor(150, 150, 180))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(40, 165, "نسخه ۳.۰.۰")
        painter.drawText(40, 185, "© 2025 ImanAI")
        painter.drawText(40, 205, "🌐 imanai.ir")
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(50, 50, 80))
        painter.drawRoundedRect(40, 240, 440, 6, 3, 3)
        
        progress_width = max(10, int(440 * progress / 100))
        painter.setBrush(QColor(233, 69, 96))
        painter.drawRoundedRect(40, 240, progress_width, 6, 3, 3)
        
        painter.setPen(QColor(150, 150, 180))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(40, 275, message)
        
        painter.end()
        self.setPixmap(new_pixmap)
        self.repaint()
        QApplication.processEvents()


# ============================================================
# HeaderWidget
# ============================================================

class HeaderWidget(QWidget, ThemeMixin):
    """هدر برنامه"""
    
    def __init__(self, license_info: Dict, user_info: Dict = None, parent=None):
        super().__init__(parent)
        self.license_info = license_info
        self.user_info = user_info or {}
        self.setObjectName("header")
        self.setMaximumHeight(70)
        
        self.theme_manager = get_theme_manager()
        self.logger = get_logger()
        self.core = get_app_core() if CORE_OK else None
        
        try:
            self.setup_ui()
            self.update_theme_style()
            
            # تایمر تاریخ
            self.date_timer = QTimer()
            self.date_timer.timeout.connect(self.update_date)
            self.date_timer.start(60000)
            
            # اتصال به سیگنال تم
            if self.core:
                self.core.event_bus.theme_changed.connect(self._on_theme_changed)
            else:
                self.theme_manager.add_observer(self._on_theme_changed)
        except Exception as e:
            self.logger.error(f"خطا در Header: {e}")
    
    def _on_theme_changed(self, theme_name: str = None):
        self.update_theme_style()
        self.update_theme_button()
    
    def update_theme_style(self):
        c = self.get_theme_colors()
        is_dark = c.get('is_dark', False)
        
        self.setStyleSheet(f"""
            QWidget#header {{
                background: {c['card']};
                border-bottom: 2px solid {c['selected']};
                padding: 0 10px;
            }}
            QLabel#headerTitle {{
                color: {c['text']};
                font-size: 16pt;
                font-weight: bold;
                background: transparent;
            }}
            QLabel#headerSubtitle {{
                color: {c.get('text_secondary', '#666')};
                font-size: 10pt;
                background: transparent;
            }}
            QLabel#headerDate {{
                color: {c['text']};
                font-size: 10pt;
                padding: 4px 12px;
                background: rgba(128,128,128,0.15);
                border-radius: 12px;
                font-weight: bold;
            }}
            QLabel#headerUser {{
                color: {c['text']};
                background: rgba(128,128,128,0.15);
                padding: 4px 14px;
                border-radius: 16px;
                font-size: 10pt;
                font-weight: bold;
            }}
            QLabel#headerDays {{
                font-size: 10pt;
                padding: 4px 12px;
                border-radius: 16px;
                font-weight: bold;
                color: white;
            }}
            QPushButton#themeBtn {{
                background: transparent;
                border: 2px solid {c['border']};
                border-radius: 19px;
                font-size: 16pt;
                color: {c['text']};
                padding: 4px;
                min-width: 38px;
                min-height: 38px;
            }}
            QPushButton#themeBtn:hover {{
                background: {c['hover']};
                border-color: {c['selected']};
            }}
        """)
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5)
        layout.setSpacing(10)
        
        logo = QLabel("🧠")
        logo.setStyleSheet("font-size: 28px; background: transparent;")
        layout.addWidget(logo)
        
        title = QLabel("ImanAccount")
        title.setObjectName("headerTitle")
        layout.addWidget(title)
        
        subtitle = QLabel("حسابداری هوشمند")
        subtitle.setObjectName("headerSubtitle")
        layout.addWidget(subtitle)
        
        layout.addStretch()
        
        username = self.user_info.get('full_name') or self.user_info.get('username', '')
        if username:
            level_names = {
                'admin': '🔴 مدیر', 'accountant': '🟢 حسابدار',
                'inventory': '🟡 انباردار', 'viewer': '⚪ کاربر',
                'payroll': '🟣 حقوق'
            }
            level_icon = level_names.get(self.user_info.get('level', 'viewer'), '👤')
            user_label = QLabel(f"{level_icon} {username}")
            user_label.setObjectName("headerUser")
            layout.addWidget(user_label)
        
        self.date_label = QLabel(get_today_jalali())
        self.date_label.setObjectName("headerDate")
        layout.addWidget(self.date_label)
        
        self.theme_btn = QPushButton("🌓")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setToolTip("تغییر تم")
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)
        
        days_left = self.license_info.get('days_left', 0)
        if days_left <= 7:
            bg, icon = "#e74c3c", "⚠️"
        elif days_left <= 30:
            bg, icon = "#f39c12", "⏰"
        else:
            bg, icon = "#27ae60", "✅"
        
        self.days_label = QLabel(f"{icon} {days_left} روز")
        self.days_label.setObjectName("headerDays")
        self.days_label.setStyleSheet(
            f"background-color: {bg}; color: white; padding: 4px 12px; "
            f"border-radius: 16px; font-weight: bold;"
        )
        layout.addWidget(self.days_label)
        
        self.update_theme_button()
    
    def update_date(self):
        try:
            self.date_label.setText(get_today_jalali())
        except Exception:
            pass
    
    def toggle_theme(self):
        try:
            if self.core:
                self.core.theme.toggle_theme()
            else:
                self.theme_manager.toggle_theme()
            self.update_theme_button()
        except Exception as e:
            self.logger.error(f"خطا در تغییر تم: {e}")
    
    def update_theme_button(self):
        try:
            is_dark = False
            if self.core:
                is_dark = self.core.theme.is_dark()
            else:
                is_dark = self.theme_manager.get_theme_name() == 'dark'
            
            self.theme_btn.setText("☀️" if is_dark else "🌓")
        except Exception:
            pass


# ============================================================
# SidebarWidget
# ============================================================

class SidebarWidget(QWidget, ThemeMixin):
    """منوی کناری"""
    
    page_selected = pyqtSignal(str)
    
    def __init__(self, menu_items: list, parent=None):
        super().__init__(parent)
        self.menu_items = menu_items
        self.buttons = {}
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
        
        self.logger = get_logger()
        self.theme_manager = get_theme_manager()
        self.core = get_app_core() if CORE_OK else None
        
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        
        try:
            self.setup_ui()
            self.build_menu()
            self.update_theme_style()
            
            if self.core:
                self.core.event_bus.theme_changed.connect(self._on_theme_changed)
            else:
                self.theme_manager.add_observer(self._on_theme_changed)
        except Exception as e:
            self.logger.error(f"خطا در Sidebar: {e}")
    
    def _on_theme_changed(self, theme_name: str = None):
        self.update_theme_style()
    
    def update_theme_style(self):
        c = self.get_theme_colors()
        
        self.setStyleSheet(f"""
            QWidget#sidebar {{
                background: {c['card']};
                border-right: 1px solid {c['border']};
            }}
            QLabel#sidebarLogo {{
                color: {c['text']};
                font-size: 18pt;
                font-weight: bold;
                padding: 15px 0 10px 0;
            }}
            QFrame#sidebarSeparator {{
                background: {c['border']};
                max-height: 1px;
                margin: 5px 20px;
            }}
            QLabel#sidebarTitle {{
                color: {c.get('text_secondary', '#666')};
                font-size: 10pt;
                font-weight: bold;
                padding: 10px 20px 5px 20px;
            }}
            QPushButton#sidebarBtn {{
                background: transparent;
                color: {c['text']};
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                margin: 2px 10px;
                text-align: left;
                font-size: 11pt;
            }}
            QPushButton#sidebarBtn:hover {{
                background: {c['hover']};
            }}
            QPushButton#sidebarBtn:checked {{
                background: {c['selected']};
                color: {c['selected_text']};
            }}
            QPushButton#sidebarSubBtn {{
                background: transparent;
                color: {c.get('text_secondary', '#666')};
                border: none;
                border-radius: 8px;
                padding: 8px 18px 8px 35px;
                margin: 1px 10px;
                text-align: left;
                font-size: 10pt;
            }}
            QPushButton#sidebarSubBtn:hover {{
                background: {c['hover']};
                color: {c['text']};
            }}
            QPushButton#sidebarSubBtn:checked {{
                background: {c['selected']};
                color: {c['selected_text']};
            }}
            QLabel#sidebarVersion {{
                color: {c.get('text_secondary', '#666')};
                font-size: 9pt;
                padding: 10px;
            }}
        """)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(4)
        
        logo = QLabel("🧠 ImanAccount")
        logo.setObjectName("sidebarLogo")
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)
        
        sep = QFrame()
        sep.setObjectName("sidebarSeparator")
        layout.addWidget(sep)
        
        title = QLabel("📋 منوی اصلی")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)
        
        self.btn_container = QWidget()
        self.btn_layout = QVBoxLayout(self.btn_container)
        self.btn_layout.setContentsMargins(0, 5, 0, 5)
        self.btn_layout.setSpacing(2)
        layout.addWidget(self.btn_container)
        
        layout.addStretch()
        
        version = QLabel("نسخه ۳.۰.۰")
        version.setObjectName("sidebarVersion")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
    
    def build_menu(self):
        try:
            for btn in self.buttons.values():
                self.btn_layout.removeWidget(btn)
                btn.deleteLater()
            self.buttons.clear()
            
            for icon, text, key, is_sub in self.menu_items:
                btn = QPushButton(f"{icon}  {text}")
                btn.setObjectName("sidebarSubBtn" if is_sub else "sidebarBtn")
                btn.setCheckable(True)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked, k=key: self.page_selected.emit(k))
                self.btn_layout.addWidget(btn)
                self.buttons[key] = btn
                self.button_group.addButton(btn)
            
            if 'dashboard' in self.buttons:
                self.buttons['dashboard'].setChecked(True)
        except Exception as e:
            self.logger.error(f"خطا در build_menu: {e}")
    
    def add_plugin_button(self, tab_key: str, title: str, icon: str = "🔌"):
        try:
            if tab_key in self.buttons:
                return self.buttons[tab_key]
            
            btn = QPushButton(f"{icon}  {title}")
            btn.setObjectName("sidebarSubBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=tab_key: self.page_selected.emit(k))
            
            self.btn_layout.addWidget(btn)
            self.buttons[tab_key] = btn
            self.button_group.addButton(btn)
            return btn
        except Exception as e:
            self.logger.error(f"خطا: {e}")
            return None
    
    def remove_plugin_button(self, tab_key: str):
        try:
            if tab_key in self.buttons:
                btn = self.buttons[tab_key]
                self.btn_layout.removeWidget(btn)
                self.button_group.removeButton(btn)
                btn.deleteLater()
                del self.buttons[tab_key]
        except Exception:
            pass
    
    def set_active(self, page_key: str):
        try:
            for key, btn in self.buttons.items():
                btn.setChecked(key == page_key)
        except Exception:
            pass


# ============================================================
# WidgetManager — مدیریت ویجت‌ها
# ============================================================

class WidgetManager(QObject):
    """مدیریت ویجت‌ها"""
    
    def __init__(self, license_info: Dict, user_level: str = 'viewer'):
        super().__init__()
        self.license_info = license_info
        self.user_level = user_level
        self.modules = license_info.get('modules', [])
        self.customer_name = license_info.get('customer', '')
        self.widgets = {}
        self.logger = get_logger()
    
    def is_module_active(self, module_name: str) -> bool:
        if module_name is None:
            return True
        try:
            if module_name not in self.modules:
                return False
            if UserManager:
                return UserManager.has_permission(self.user_level, module_name)
            return True
        except Exception:
            return False
    
    def get_menu_items(self) -> list:
        try:
            items = [('📊', 'داشبورد', 'dashboard', False)]
            
            available_modules = [
                ('📚', 'حسابداری', 'accounting', 'accounting'),
                ('📦', 'انبارداری', 'inventory', 'inventory'),
                ('💰', 'حقوق دستمزد', 'payroll', 'payroll'),
                ('📄', 'خرید و فروش', 'document', 'invoice'),
            ]
            
            for icon, text, key, module in available_modules:
                if self.is_module_active(module):
                    items.append((icon, text, key, True))
            
            if self.user_level != 'viewer' and 'ai' in self.modules:
                items.append(('🤖', 'دستیار هوشمند', 'ai', False))
            
            if UserManager and UserManager.has_permission(self.user_level, 'admin'):
                items.append(('🧩', 'مدیریت پلاگین‌ها', 'plugins', False))
                items.append(('🛠️', 'ابزارها', 'tools', False))
                items.append(('⚙️', 'تنظیمات', 'settings', False))
            
            return items
        except Exception as e:
            self.logger.error(f"خطا در منو: {e}")
            return [('📊', 'داشبورد', 'dashboard', False)]
    
    def get_widget(self, key: str, parent=None):
        if key in self.widgets:
            return self.widgets[key]
        
        try:
            widget = None
            self.logger.debug(f"در حال ساخت ویجت: {key}")
            
            if key == 'dashboard':
                from ui.dashboard_widget import DashboardWidget
                widget = DashboardWidget(user_level=self.user_level, parent=parent)
            elif key == 'accounting':
                from ui.accounting_widget import AccountingWidget
                widget = AccountingWidget(
                    customer_name=self.customer_name,
                    user_level=self.user_level, parent=parent
                )
            elif key == 'inventory':
                from ui.inventory_widget import InventoryWidget
                widget = InventoryWidget(
                    customer_name=self.customer_name,
                    user_level=self.user_level, parent=parent
                )
            elif key == 'payroll':
                from ui.payroll_widget import PayrollWidget
                widget = PayrollWidget(
                    customer_name=self.customer_name,
                    user_level=self.user_level, parent=parent
                )
            elif key == 'document':
                from ui.document_widget import DocumentWidget
                widget = DocumentWidget(
                    customer_name=self.customer_name,
                    user_level=self.user_level, parent=parent
                )
            elif key == 'ai':
                from ui.ai_assistant_widget import AIAssistantWidget
                widget = AIAssistantWidget(parent=parent, user_level=self.user_level)
            elif key == 'plugins':
                from ui.plugin_manager_widget import PluginManagerWidget
                widget = PluginManagerWidget(
                    license_key=self.license_info.get('license_key'),
                    parent=parent, user_level=self.user_level
                )
            elif key == 'tools':
                from ui.tools_widget import ToolsWidget
                widget = ToolsWidget(parent=parent, user_level=self.user_level)
            elif key == 'settings':
                from ui.settings_widget import SettingsWidget
                widget = SettingsWidget(user_level=self.user_level, parent=parent)
            
            if widget:
                self.widgets[key] = widget
                self.logger.info(f"✅ ویجت {key} ساخته شد")
                return widget
            
            raise ValueError(f"صفحه {key} شناسایی نشد")
        except Exception as e:
            self.logger.error(f"خطا در ساخت {key}: {e}")
            return self._create_error_widget(str(e))
    
    def _create_error_widget(self, error: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(50, 50, 50, 50)
        
        icon = QLabel("⚠️")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 48pt;")
        layout.addWidget(icon)
        
        label = QLabel("خطا در بارگذاری صفحه")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #e74c3c;")
        layout.addWidget(label)
        
        detail = QLabel(error[:200])
        detail.setAlignment(Qt.AlignCenter)
        detail.setStyleSheet("color: #888; font-size: 10pt;")
        detail.setWordWrap(True)
        layout.addWidget(detail)
        
        return widget


# ============================================================
# MainWindow
# ============================================================

class MainWindow(BaseWindow, ThemeMixin):
    """پنجره اصلی ImanAccount"""
    
    def __init__(self, license_info: Dict, license_key: str = None):
        self.logger = get_logger()
        self.logger.info("🚀 راه‌اندازی MainWindow...")
        
        self.error_handler = get_error_handler()
        self.theme_manager = get_theme_manager()
        self.core = get_app_core() if CORE_OK else None
        
        self.license_info = license_info
        self.license_key = license_key or license_info.get('license_key')
        self.customer_name = license_info.get('customer', '')
        self.current_user = None
        self.splash = None
        
        self.plugin_manager = None
        self.plugin_widgets = {}
        self.plugin_menus = []
        
        self.idle_timer = None
        self.idle_time = 0
        self.idle_limit = 300
        
        # ✅ ساخت BaseWindow (اگه OK بود، از super استفاده کن)
        if BASE_WINDOW_OK:
            try:
                super().__init__(
                    parent=None, base_width=1400, base_height=900,
                    scale_factor=1.0, center=True
                )
            except Exception as e:
                self.logger.error(f"خطا در BaseWindow: {e}")
                QMainWindow.__init__(self)
                self.setMinimumSize(1400, 900)
        else:
            QMainWindow.__init__(self)
            self.setMinimumSize(1400, 900)
            self.screen_manager = ScreenManager()
        
        self.setWindowTitle(f"🤖 ImanAccount | {self.customer_name}")
        self._set_window_icon()
        
        # اتصال به سیگنال تم
        if self.core:
            self.core.event_bus.theme_changed.connect(self.on_theme_changed)
        else:
            self.theme_manager.add_observer(self.on_theme_changed)
        
        self._init_with_splash()
    
    # ============================================================
    # راه‌اندازی
    # ============================================================
    
    def _init_with_splash(self):
        try:
            self.splash = ImanSplashScreen()
            self.splash.show()
            self.splash.show_message("⏳ بارگذاری...", 10)
            QApplication.processEvents()
            
            self.splash.show_message("📂 راه‌اندازی دیتابیس...", 30)
            self._init_database()
            
            self.splash.show_message("👤 ورود به سیستم...", 60)
            self.splash.hide()
            
            if not self._handle_login():
                self.logger.warning("❌ ورود ناموفق")
                sys.exit(0)
            
            self.splash.show()
            self.splash.show_message("🖥️ راه‌اندازی UI...", 80)
            self._init_ui()
            
            self.splash.show_message("🔒 راه‌اندازی امنیت...", 90)
            self._setup_idle_timer()
            
            self.splash.show_message("📊 آماده‌سازی داشبورد...", 95)
            self._switch_page('dashboard')
            
            self.splash.show_message("✅ آماده!", 100)
            QTimer.singleShot(300, self._finish_splash)
            
            self._show_welcome_message()
            self.logger.info("✅ MainWindow راه‌اندازی شد")
        
        except Exception as e:
            self.logger.critical(f"❌ خطا: {e}")
            self.logger.critical(traceback.format_exc())
            
            if self.splash:
                self.splash.hide()
            
            QMessageBox.critical(
                self, "خطای راه‌اندازی",
                f"خطا در راه‌اندازی:\n\n{str(e)}"
            )
            sys.exit(1)
    
    def _finish_splash(self):
        if self.splash:
            self.splash.hide()
            self.splash = None
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _set_window_icon(self):
        icon_paths = [
            "Icon.ico", "icon.ico",
            os.path.join(os.path.dirname(__file__), "..", "Icon.ico"),
            os.path.join(get_base_path(), "Icon.ico"),
        ]
        for path in icon_paths:
            if os.path.exists(path):
                try:
                    self.setWindowIcon(QIcon(path))
                    return
                except Exception:
                    pass
    
    def _init_database(self):
        try:
            if DatabaseManager:
                DatabaseManager.init_db()
                self.logger.info("✅ دیتابیس راه‌اندازی شد")
        except Exception as e:
            self.logger.error(f"خطا در دیتابیس: {e}")
    
    def _handle_login(self) -> bool:
        try:
            if not LoginDialog:
                self.current_user = {
                    'username': 'admin', 'level': 'admin', 'full_name': 'مدیر'
                }
                if self.core:
                    self.core.user.login(self.current_user)
                return True
            
            login_dialog = LoginDialog(self)
            if login_dialog.exec_() != QDialog.Accepted:
                return False
            
            self.current_user = login_dialog.get_current_user()
            
            if not self.current_user:
                return False
            
            if self.core:
                self.core.user.login(self.current_user)
            
            username = self.current_user.get('full_name') or self.current_user.get('username', 'کاربر')
            level = self.current_user.get('level', 'viewer')
            self.setWindowTitle(f"🤖 ImanAccount | {self.customer_name} | 👤 {username}")
            
            self.logger.info(f"✅ کاربر '{username}' وارد شد | سطح: {level}")
            return True
        except Exception as e:
            self.logger.error(f"خطا در ورود: {e}")
            return False
    
    def _show_welcome_message(self):
        try:
            username = self.current_user.get('full_name') or self.current_user.get('username', '')
            level_names = {
                'admin': 'مدیر سیستم', 'accountant': 'حسابدار',
                'inventory': 'انباردار', 'viewer': 'کاربر عادی',
                'payroll': 'کارشناس حقوق'
            }
            level = self.current_user.get('level', 'viewer')
            level_name = level_names.get(level, level)
            
            self.statusBar().showMessage(
                f"👋 خوش آمدید {username} | سطح: {level_name} | ✅ آماده",
                5000
            )
        except Exception:
            pass
    
    # ============================================================
    # تم
    # ============================================================
    
    def on_theme_changed(self, theme_name: str = None):
        try:
            self.logger.info(f"🎨 تغییر تم به: {theme_name}")
            
            # استایل اصلی
            stylesheet = self.theme_manager.get_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
            
            if hasattr(self, 'header') and self.header:
                self.header._on_theme_changed(theme_name)
            if hasattr(self, 'sidebar') and self.sidebar:
                self.sidebar._on_theme_changed(theme_name)
            
            # ویجت‌های داخل stack
            if hasattr(self, 'content_stack'):
                for i in range(self.content_stack.count()):
                    widget = self.content_stack.widget(i)
                    if widget and hasattr(widget, '_on_theme_signal'):
                        try:
                            widget._on_theme_signal(theme_name)
                        except Exception:
                            pass
        except Exception as e:
            self.logger.warning(f"خطا در on_theme_changed: {e}")
    
    def apply_theme(self):
        try:
            stylesheet = self.theme_manager.get_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
        except Exception:
            pass
    
    # ============================================================
    # UI
    # ============================================================
    
    def _init_ui(self):
        self._create_menu_bar()
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # هدر
        self.header = HeaderWidget(self.license_info, self.current_user)
        main_layout.addWidget(self.header)
        
        # بدنه
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        
        user_level = self.current_user.get('level', 'viewer') if self.current_user else 'viewer'
        self.widget_manager = WidgetManager(self.license_info, user_level)
        
        menu_items = self.widget_manager.get_menu_items()
        self.sidebar = SidebarWidget(menu_items)
        self.sidebar.page_selected.connect(self._switch_page)
        body_layout.addWidget(self.sidebar)
        
        self.content_stack = QStackedWidget()
        body_layout.addWidget(self.content_stack, 1)
        
        empty_widget = self._create_empty_widget()
        self.content_stack.addWidget(empty_widget)
        
        main_layout.addWidget(body, 1)
        self.apply_theme()
        
        # بارگذاری پلاگین‌ها
        self._load_plugins()
    
    def _create_empty_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel("🧠 به ImanAccount خوش آمدید\n\nلطفاً یک بخش را انتخاب کنید")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 16pt; padding: 50px; opacity: 0.6;")
        layout.addWidget(label)
        return widget
    
    # ============================================================
    # Plugins
    # ============================================================
    
    def _load_plugins(self):
        try:
            from plugins.plugin_loader import PluginManager
            
            license_key = self.license_key or self.license_info.get('license_key')
            self.plugin_manager = PluginManager(license_key=license_key)
            
            plugin_tabs = self.plugin_manager.get_plugin_tabs()
            
            for tab_info in plugin_tabs:
                plugin_id = tab_info.get('plugin_id')
                widget_id = tab_info.get('widget_id', tab_info.get('title'))
                title = tab_info.get('title', 'پلاگین')
                icon = tab_info.get('icon', '🔌')
                
                widget = self.plugin_manager.get_plugin_widget(plugin_id, widget_id)
                if widget:
                    tab_key = f"plugin_{plugin_id}_{widget_id}"
                    self.plugin_widgets[tab_key] = widget
                    self.content_stack.addWidget(widget)
                    self.sidebar.add_plugin_button(tab_key, title, icon)
            
            self._load_plugin_menus()
        except Exception as e:
            self.logger.warning(f"خطا در بارگذاری پلاگین‌ها: {e}")
    
    def _load_plugin_menus(self):
        try:
            if not self.plugin_manager:
                return
            
            plugin_menus = self.plugin_manager.get_plugin_menus()
            menubar = self.menuBar()
            
            for menu_info in plugin_menus:
                plugin_id = menu_info.get('plugin_id')
                title = menu_info.get('title', 'پلاگین')
                actions = menu_info.get('actions', [])
                
                plugin_menu = menubar.addMenu(f"🔌 {title}")
                self.plugin_menus.append({
                    'plugin_id': plugin_id, 'menu': plugin_menu, 'title': title
                })
                
                for action_info in actions:
                    action_title = action_info.get('title', 'اکشن')
                    action_id = action_info.get('id')
                    action = QAction(action_title, self)
                    action.triggered.connect(
                        lambda checked, p=plugin_id, a=action_id:
                            self._execute_plugin_action(p, a)
                    )
                    plugin_menu.addAction(action)
        except Exception as e:
            self.logger.error(f"خطا: {e}")
    
    def _execute_plugin_action(self, plugin_id: str, action_id: str):
        try:
            if self.plugin_manager:
                self.plugin_manager.execute_action(plugin_id, action_id)
        except Exception as e:
            self.logger.error(f"خطا: {e}")
    
    # ============================================================
    # Navigation
    # ============================================================
    
    def _switch_page(self, page_key: str):
        try:
            if page_key.startswith("plugin_"):
                widget = self.plugin_widgets.get(page_key)
                if widget:
                    self.sidebar.set_active(page_key)
                    if self.content_stack.indexOf(widget) == -1:
                        self.content_stack.addWidget(widget)
                    self.content_stack.setCurrentWidget(widget)
                return
            
            page_module_map = {
                'accounting': 'accounting', 'inventory': 'inventory',
                'payroll': 'payroll', 'document': 'documents',
                'ai': 'ai', 'plugins': 'admin', 'tools': 'admin',
                'settings': 'admin', 'dashboard': None, 'customers': 'parties',
            }
            
            module = page_module_map.get(page_key)
            user_level = self.current_user.get('level', 'viewer') if self.current_user else 'viewer'
            
            if module and UserManager:
                if not UserManager.has_permission(user_level, module):
                    QMessageBox.warning(self, "دسترسی محدود",
                        "⚠️ شما دسترسی لازم ندارید!")
                    return
            
            self.sidebar.set_active(page_key)
            widget = self.widget_manager.get_widget(page_key, self)
            
            if widget:
                if self.content_stack.indexOf(widget) == -1:
                    self.content_stack.addWidget(widget)
                self.content_stack.setCurrentWidget(widget)
                
                if self.core:
                    self.core.event_bus.page_changed.emit(page_key)
        except Exception as e:
            self.logger.error(f"خطا در switch_page: {e}")
    
    # ============================================================
    # Menu Bar
    # ============================================================
    
    def _create_menu_bar(self):
        menubar = self.menuBar()
        menubar.clear()
        
        user_level = self.current_user.get('level', 'viewer') if self.current_user else 'viewer'
        is_admin = user_level == 'admin'
        is_accountant = user_level in ['admin', 'accountant']
        
        # فایل
        file_menu = menubar.addMenu("📁 فایل")
        file_actions = []
        
        if is_accountant:
            file_actions.append(("📄 سند جدید", "Ctrl+N", self._new_voucher))
            file_actions.append(("🧾 فاکتور فروش", "Ctrl+I", self._new_invoice))
            file_actions.append(("📥 فاکتور خرید", "Ctrl+P", self._new_purchase))
            file_actions.append(None)
        
        file_actions.append(("🔑 تغییر رمز", None, self._change_password))
        file_actions.append(("🔒 قفل کردن", "Ctrl+L", self._lock_screen))
        file_actions.append(None)
        
        if is_admin:
            file_actions.append(("💾 پشتیبان", None, self._backup_database))
            file_actions.append(("📂 بازیابی", None, self._restore_database))
            file_actions.append(None)
        
        file_actions.append(("🚪 خروج", "Ctrl+Q", self.close))
        
        for item in file_actions:
            if item is None:
                file_menu.addSeparator()
            else:
                text, shortcut, func = item
                action = QAction(text, self)
                if shortcut:
                    action.setShortcut(shortcut)
                action.triggered.connect(lambda checked, f=func: f())
                file_menu.addAction(action)
        
        # تنظیمات
        if is_admin:
            settings_menu = menubar.addMenu("⚙️ تنظیمات")
            
            theme_menu = settings_menu.addMenu("🎨 تغییر تم")
            try:
                themes = self.theme_manager.get_available_themes()
                for name, display in themes.items():
                    action = QAction(display, self)
                    action.setCheckable(True)
                    action.setChecked(name == self.theme_manager.get_theme_name())
                    action.triggered.connect(
                        lambda checked, n=name: self._set_theme(n)
                    )
                    theme_menu.addAction(action)
            except Exception:
                pass
            
            settings_menu.addSeparator()
            users_action = QAction("👥 مدیریت کاربران", self)
            users_action.triggered.connect(lambda checked, f=self._manage_users: f())
            settings_menu.addAction(users_action)
        
        # AI
        ai_menu = menubar.addMenu("🤖 هوش مصنوعی")
        ai_actions = [
            ("💬 گفتگو با ImanAI", self._open_ai_chat),
            ("🧠 تحلیل مالی", self._open_ai_analysis),
            ("💰 پیشنهاد حساب", self._open_ai_suggestion),
        ]
        for text, func in ai_actions:
            action = QAction(text, self)
            action.triggered.connect(lambda checked, f=func: f())
            ai_menu.addAction(action)
        
        # پلاگین
        if is_admin:
            plugin_menu = menubar.addMenu("🧩 پلاگین‌ها")
            plugin_action = QAction("📦 مدیریت پلاگین‌ها", self)
            plugin_action.triggered.connect(
                lambda checked: self._switch_page('plugins')
            )
            plugin_menu.addAction(plugin_action)
        
        # راهنما
        help_menu = menubar.addMenu("❓ راهنما")
        help_actions = [
            ("🖥️ HWID", self._show_hwid),
            None,
            ("ℹ️ درباره", self._show_about),
            ("🔑 لایسنس", self._show_license_info),
            ("⌨️ میانبرها", self._show_shortcuts),
        ]
        for item in help_actions:
            if item is None:
                help_menu.addSeparator()
            else:
                text, func = item
                action = QAction(text, self)
                action.triggered.connect(lambda checked, f=func: f())
                help_menu.addAction(action)
    
    def _set_theme(self, theme_name: str):
        try:
            if self.core:
                self.core.theme.set_theme(theme_name)
            else:
                self.theme_manager.set_theme(theme_name)
        except Exception as e:
            self.logger.error(f"خطا: {e}")
    
    # ============================================================
    # Menu Handlers
    # ============================================================
    
    def _open_ai_chat(self, **kwargs):
        self._switch_page('ai')
        widget = self.widget_manager.widgets.get('ai')
        if widget and hasattr(widget, 'tabs'):
            for i in range(widget.tabs.count()):
                if "چت" in widget.tabs.tabText(i):
                    widget.tabs.setCurrentIndex(i)
                    break
    
    def _open_ai_analysis(self, **kwargs):
        self._switch_page('ai')
        widget = self.widget_manager.widgets.get('ai')
        if widget and hasattr(widget, 'tabs'):
            for i in range(widget.tabs.count()):
                if "تحلیل" in widget.tabs.tabText(i):
                    widget.tabs.setCurrentIndex(i)
                    break
    
    def _open_ai_suggestion(self, **kwargs):
        self._switch_page('ai')
        widget = self.widget_manager.widgets.get('ai')
        if widget and hasattr(widget, 'tabs'):
            for i in range(widget.tabs.count()):
                if "پیشنهاد" in widget.tabs.tabText(i):
                    widget.tabs.setCurrentIndex(i)
                    break
    
    def _new_voucher(self, **kwargs):
        self._switch_page('accounting')
        widget = self.widget_manager.widgets.get('accounting')
        if widget and hasattr(widget, 'new_voucher'):
            QTimer.singleShot(100, widget.new_voucher)
    
    def _new_invoice(self, **kwargs):
        self._switch_page('document')
        widget = self.widget_manager.widgets.get('document')
        if widget:
            if hasattr(widget, 'doc_type_combo'):
                widget.doc_type_combo.setCurrentIndex(0)
            if hasattr(widget, 'new_document'):
                QTimer.singleShot(100, widget.new_document)
    
    def _new_purchase(self, **kwargs):
        self._switch_page('document')
        widget = self.widget_manager.widgets.get('document')
        if widget:
            if hasattr(widget, 'doc_type_combo'):
                widget.doc_type_combo.setCurrentIndex(1)
            if hasattr(widget, 'new_document'):
                QTimer.singleShot(100, widget.new_document)
    
    def _manage_users(self, **kwargs):
        try:
            if UserManager:
                from ui.login_dialog import UserManagementDialog
                UserManagementDialog(self).exec_()
        except Exception as e:
            self.error_handler.show_error(self, "خطا", str(e))
    
    def _backup_database(self, **kwargs):
        try:
            from database import DB_NAME
            import shutil
            
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            file_name, _ = QFileDialog.getSaveFileName(
                self, "ذخیره پشتیبان", backup_name, "Database (*.db)"
            )
            if file_name:
                shutil.copy2(DB_NAME, file_name)
                QMessageBox.information(self, "موفق", "✅ پشتیبان ذخیره شد!")
        except Exception as e:
            self.error_handler.show_error(self, "خطا", str(e))
    
    def _restore_database(self, **kwargs):
        try:
            from database import DB_NAME
            import shutil
            
            reply = QMessageBox.question(
                self, "تأیید", "اطلاعات فعلی از دست می‌رود! ادامه؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                file_name, _ = QFileDialog.getOpenFileName(
                    self, "انتخاب پشتیبان", "", "Database (*.db)"
                )
                if file_name:
                    shutil.copy2(file_name, DB_NAME)
                    QMessageBox.information(self, "موفق", "✅ بازیابی شد!")
        except Exception as e:
            self.error_handler.show_error(self, "خطا", str(e))
    
    def _show_hwid(self, **kwargs):
        try:
            from license_core import LicenseCore
            hwid = LicenseCore.get_system_hwid()
            QMessageBox.information(self, "🖥️ HWID", f"HWID:\n\n{hwid}")
        except Exception:
            pass
    
    def _show_about(self, **kwargs):
        QMessageBox.about(self, "درباره ImanAccount", """
        <div style='text-align: center;'>
            <h2>🤖 ImanAccount</h2>
            <p><b>نسخه ۳.۰.۰</b></p>
            <p>نرم‌افزار جامع حسابداری هوشمند</p>
            <hr>
            <p>🧠 ImanAI ✅</p>
            <p>📧 info@imanai.ir</p>
        </div>
        """)
    
    def _show_license_info(self, **kwargs):
        info = self.license_info
        QMessageBox.information(self, "اطلاعات لایسنس", f"""
        <h3>🔑 لایسنس</h3>
        <p><b>مشتری:</b> {info.get('customer', 'N/A')}</p>
        <p><b>انقضا:</b> {info.get('expire_date', 'N/A')}</p>
        <p><b>روز:</b> {info.get('days_left', 0)}</p>
        """)
    
    def _show_shortcuts(self, **kwargs):
        QMessageBox.information(self, "کلیدها", """
        <h3>⌨️ میانبرها</h3>
        <p>Ctrl+N: سند | Ctrl+I: فروش | Ctrl+P: خرید</p>
        <p>Ctrl+L: قفل | Ctrl+Q: خروج</p>
        """)
    
    # ============================================================
    # Idle / Lock
    # ============================================================
    
    def _setup_idle_timer(self):
        try:
            self.idle_timer = QTimer()
            self.idle_timer.timeout.connect(self._check_idle)
            self.idle_timer.start(1000)
            self.installEventFilter(self)
        except Exception:
            pass
    
    def _check_idle(self):
        try:
            self.idle_time += 1
            if self.idle_time >= self.idle_limit:
                self._lock_screen()
        except Exception:
            pass
    
    def eventFilter(self, obj, event):
        try:
            if event.type() in [QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel]:
                self.idle_time = 0
        except Exception:
            pass
        return super().eventFilter(obj, event)
    
    def _lock_screen(self, **kwargs):
        try:
            if not LockScreenDialog:
                return
            if self.idle_timer:
                self.idle_timer.stop()
            
            username = self.current_user.get('username', '') if self.current_user else ''
            lock_dialog = LockScreenDialog(username, self)
            if lock_dialog.exec_() == QDialog.Accepted:
                self.idle_time = 0
                if self.idle_timer:
                    self.idle_timer.start()
            else:
                self.close()
        except Exception:
            pass
    
    def _change_password(self, **kwargs):
        try:
            if not ChangePasswordDialog:
                return
            username = self.current_user.get('username', '') if self.current_user else ''
            ChangePasswordDialog(username, self).exec_()
        except Exception as e:
            self.error_handler.show_error(self, "خطا", str(e))
    
    # ============================================================
    # Close
    # ============================================================
    
    def closeEvent(self, event):
        try:
            reply = QMessageBox.question(
                self, "خروج", "آیا خارج می‌شوید؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.idle_timer:
                    self.idle_timer.stop()
                
                if self.core:
                    try:
                        self.core.shutdown()
                    except Exception:
                        pass
                
                event.accept()
            else:
                event.ignore()
        except Exception:
            event.accept()
