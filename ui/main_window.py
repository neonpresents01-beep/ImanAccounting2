# ui/main_window.py
# ============================================================
# پنجره اصلی ImanAccount - نسخه 11.0
# ============================================================
# تغییرات v11.0:
# ✅ اضافه شدن FinanceWidget (امور مالی)
# ✅ اضافه شدن AccountingTreeWidget (درختواره)
# ✅ پشتیبانی کامل از tab_index
# ✅ اصلاح bg_alt در ThemeMixin
# ✅ لاگ کامل برای دیباگ
# ============================================================

import sys
import os
import traceback
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

# ============================================================
# sys.path
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
# Imports
# ============================================================

try:
    from error_handler import (
        get_logger, get_error_handler, safe_execute,
        row_to_dict, ValidationError, PermissionError,
    )
    ERROR_HANDLER_OK = True
except ImportError:
    ERROR_HANDLER_OK = False
    import logging
    def get_logger(): return logging.getLogger("ImanAccount")
    def get_error_handler():
        class SH:
            def show_error(self, *a, **k): pass
            def show_warning(self, *a, **k): pass
            def show_info(self, *a, **k): pass
        return SH()
    def safe_execute(f): return f
    def row_to_dict(row):
        if row is None: return {}
        try: return {k: row[k] for k in row.keys()}
        except: return {}
    class ValidationError(Exception): pass
    class PermissionError(Exception): pass


try:
    from menu_registry import (
        get_menu_registry, register_default_menu, MenuRegistry,
    )
    MENU_REGISTRY_OK = True
except ImportError as e:
    print(f"⚠️ menu_registry: {e}")
    MENU_REGISTRY_OK = False
    def get_menu_registry(): return None
    def register_default_menu(): pass
    MenuRegistry = None


try:
    from plugin_menu_bridge import PluginMenuBridge
    PLUGIN_BRIDGE_OK = True
except ImportError:
    PLUGIN_BRIDGE_OK = False
    PluginMenuBridge = None


try:
    from modules_config import (
        ALL_MODULES, get_required_modules,
        get_page_to_module_map, get_module_info, get_module_name,
    )
    MODULES_CONFIG_OK = True
except ImportError:
    MODULES_CONFIG_OK = False
    ALL_MODULES = {}
    def get_required_modules(): return ['accounting']
    def get_page_to_module_map(): return {}
    def get_module_info(k): return {}
    def get_module_name(k): return k


try:
    from screen_utils import WindowResizer, ScreenManager
    SCREEN_UTILS_OK = True
except ImportError:
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
        def __init__(self, w, *a, **k): pass


try:
    from shamsi_date import get_today_jalali, ShamsiDateEdit, safe_display_date
    DATE_OK = True
except ImportError:
    DATE_OK = False
    def get_today_jalali(): return datetime.now().strftime("%Y/%m/%d")
    def safe_display_date(d): return str(d) if d else ""


try:
    from path_utils import get_base_path
except ImportError:
    def get_base_path(): return str(_PROJECT_ROOT)


try:
    from database import DatabaseManager
except ImportError:
    DatabaseManager = None


try:
    from ui.base_widgets import BaseWindow, BaseDialog, ThemeMixin
    BASE_WINDOW_OK = True
except ImportError:
    BASE_WINDOW_OK = False
    BaseWindow = QMainWindow
    BaseDialog = QDialog
    class ThemeMixin:
        def get_theme_colors(self):
            return {
                'bg': "#f5f6fa",
                'bg_alt': "#ffffff",
                'bg_tertiary': "#eef2f5",
                'card': "#ffffff",
                'text': "#1a1a2e",
                'text_secondary': "#5d6d7e",
                'text_tertiary': "#a0a0a0",
                'text_white': "#ffffff",
                'border': "#dcdde1",
                'border_light': "#e5e8ec",
                'hover': "#e8e8e8",
                'selected': "#1976D2",
                'selected_text': "#ffffff",
                'success': "#27ae60",
                'danger': "#e74c3c",
                'warning': "#f39c12",
                'info': "#3498db",
                'purple': "#9C27B0",
                'header_bg': "#e8e8e8",
                'header_text': "#1a1a2e",
                'is_dark': False,
            }


try:
    from ui.login_dialog import (
        LoginDialog, LockScreenDialog, ChangePasswordDialog, UserManager
    )
    LOGIN_OK = True
except ImportError:
    LOGIN_OK = False
    LoginDialog = None
    LockScreenDialog = None
    ChangePasswordDialog = None
    UserManager = None


try:
    from ui.styles.theme_manager import get_theme_manager
    THEME_OK = True
except ImportError:
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
            if cb not in self._observers: self._observers.append(cb)
        def remove_observer(self, cb):
            if cb in self._observers: self._observers.remove(cb)
        def get_available_themes(self):
            return {'light': '☀️ روشن', 'dark': '🌙 تاریک'}
        def is_dark(self): return self._theme_name == 'dark'
        def get_current_theme(self):
            class T: display_name = self._theme_name
            return T()
    _simple_theme = SimpleThemeManager()
    def get_theme_manager(): return _simple_theme


try:
    from core import get_app_core, EventType
    CORE_OK = True
except ImportError:
    CORE_OK = False
    def get_app_core(): return None
    class EventType: pass


logger = get_logger()


# ============================================================
# Splash Screen
# ============================================================

class ImanSplashScreen(QSplashScreen):
    """Splash Screen سفارشی"""
    
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
    """هدر بالای پنجره"""
    
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
            self.date_timer = QTimer()
            self.date_timer.timeout.connect(self.update_date)
            self.date_timer.start(60000)
            
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
        c.setdefault('bg_alt', c.get('card', '#ffffff'))
        c.setdefault('text_secondary', '#666666')
        
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
                color: {c['text_secondary']};
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
        except:
            pass
    
    def toggle_theme(self):
        try:
            if self.core:
                self.core.theme.toggle_theme()
            else:
                self.theme_manager.toggle_theme()
            self.update_theme_button()
        except Exception as e:
            self.logger.error(f"خطا: {e}")
    
    def update_theme_button(self):
        try:
            is_dark = False
            if self.core:
                is_dark = self.core.theme.is_dark()
            else:
                is_dark = self.theme_manager.get_theme_name() == 'dark'
            self.theme_btn.setText("☀️" if is_dark else "🌓")
        except:
            pass


# ============================================================
# SidebarWidget
# ============================================================

class SidebarWidget(QWidget, ThemeMixin):
    """منوی کناری درختی — پویا از MenuRegistry"""
    
    page_selected = pyqtSignal(str)
    
    def __init__(self, license_info: dict = None,
                 user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        
        self.license_info = license_info or {}
        self.user_level = user_level
        self.modules = set(self.license_info.get('modules', []))
        
        try:
            self.REQUIRED = set(get_required_modules())
        except Exception:
            self.REQUIRED = {'accounting'}
        
        self.buttons = {}
        self.group_buttons = {}
        self.group_containers = {}
        self.group_arrows = {}
        self.group_keys = {}
        self.expanded_groups = set()
        
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
        
        self.logger = get_logger()
        self.theme_manager = get_theme_manager()
        self.core = get_app_core() if CORE_OK else None
        
        self.menu_registry = get_menu_registry() if MENU_REGISTRY_OK else None
        
        self.setObjectName("sidebar")
        self.setFixedWidth(260)
        
        try:
            self.setup_ui()
            
            if self.menu_registry:
                stats = self.menu_registry.get_stats()
                self.logger.info(
                    f"📋 MenuRegistry: {stats['groups']} گروه، "
                    f"{stats['items']} آیتم"
                )
                
                if stats['groups'] == 0:
                    self.logger.info("📋 Registry خالی، ثبت منوی پیش‌فرض...")
                    register_default_menu()
                    stats = self.menu_registry.get_stats()
                    self.logger.info(
                        f"📋 بعد از ثبت: {stats['groups']}گ، {stats['items']}آ"
                    )
                
                self.build_menu()
                self.menu_registry.menu_changed.connect(self._on_menu_changed)
            else:
                self.logger.warning("⚠️ MenuRegistry نیست — fallback")
                self._build_fallback_menu()
            
            self.update_theme_style()
            
            if self.core:
                self.core.event_bus.theme_changed.connect(self._on_theme_changed)
            else:
                self.theme_manager.add_observer(self._on_theme_changed)
        
        except Exception as e:
            self.logger.error(f"❌ خطا در Sidebar: {e}")
            import traceback
            traceback.print_exc()
    
    def _has_license(self, module_key: str) -> bool:
        if not module_key:
            return True
        if module_key in self.REQUIRED:
            return True
        if module_key == 'admin':
            return UserManager and UserManager.has_permission(self.user_level, 'admin')
        return module_key in self.modules
    
    def _has_access(self, module_key: str) -> bool:
        if not self._has_license(module_key):
            return False
        if module_key == 'admin':
            return UserManager and UserManager.has_permission(self.user_level, 'admin')
        if UserManager:
            try:
                return UserManager.has_permission(self.user_level, module_key)
            except:
                pass
        return True
    
    def _on_theme_changed(self, theme_name: str = None):
        self.update_theme_style()
    
    def update_theme_style(self):
        c = self.get_theme_colors()
        c.setdefault('bg_alt', c.get('card', '#ffffff'))
        c.setdefault('text_secondary', '#666666')
        
        self.setStyleSheet(f"""
            QWidget#sidebar {{
                background: {c['card']};
                border-right: 1px solid {c['border']};
            }}
            QLabel#sidebarLogo {{
                color: {c['text']};
                font-size: 17pt;
                font-weight: bold;
                padding: 15px 0 10px 0;
                background: transparent;
            }}
            QFrame#sidebarSeparator {{
                background: {c['border']};
                max-height: 1px;
                margin: 5px 20px;
            }}
            QLabel#sidebarTitle {{
                color: {c['text_secondary']};
                font-size: 10pt;
                font-weight: bold;
                padding: 10px 20px 5px 20px;
                background: transparent;
            }}
            QPushButton#sidebarTopBtn {{
                background: transparent;
                color: {c['text']};
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                margin: 2px 8px;
                text-align: left;
                font-size: 11pt;
                font-weight: bold;
            }}
            QPushButton#sidebarTopBtn:hover {{
                background: {c['hover']};
            }}
            QPushButton#sidebarTopBtn:checked {{
                background: {c['selected']};
                color: {c['selected_text']};
            }}
            QPushButton#sidebarGroupBtn {{
                background: transparent;
                color: {c['text']};
                border: none;
                border-radius: 8px;
                padding: 10px 12px;
                text-align: left;
                font-size: 11pt;
                font-weight: bold;
            }}
            QPushButton#sidebarGroupBtn:hover {{
                background: {c['hover']};
            }}
            QPushButton#sidebarGroupBtn[active="true"] {{
                background: rgba(128, 128, 128, 0.15);
                color: {c['selected']};
            }}
            QPushButton#sidebarBtn {{
                background: transparent;
                color: {c['text']};
                border: none;
                border-radius: 6px;
                padding: 7px 12px 7px 30px;
                margin: 1px 8px 1px 20px;
                text-align: left;
                font-size: 10pt;
            }}
            QPushButton#sidebarBtn:hover {{
                background: {c['hover']};
            }}
            QPushButton#sidebarBtn:checked {{
                background: {c['selected']};
                color: {c['selected_text']};
                font-weight: bold;
            }}
            QPushButton#sidebarLockedBtn {{
                background: transparent;
                color: {c['text_secondary']};
                border: 1px dashed {c['border']};
                border-radius: 6px;
                padding: 7px 12px 7px 30px;
                margin: 1px 8px 1px 20px;
                text-align: left;
                font-size: 10pt;
                font-style: italic;
            }}
            QPushButton#sidebarLockedBtn:hover {{
                background: {c['hover']};
                color: {c['text']};
                border-color: {c['selected']};
            }}
            QLabel#groupArrow {{
                color: {c['text_secondary']};
                font-size: 10pt;
                background: transparent;
                padding: 0 8px 0 0;
                font-weight: bold;
            }}
            QLabel#sidebarVersion {{
                color: {c['text_secondary']};
                font-size: 9pt;
                padding: 10px;
                background: transparent;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['border']};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['selected']};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
                background: none;
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
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.menu_container = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(0, 5, 0, 5)
        self.menu_layout.setSpacing(2)
        self.menu_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.menu_container)
        self.scroll_area = scroll
        layout.addWidget(scroll, 1)
        
        version = QLabel("نسخه ۳.۰.۰")
        version.setObjectName("sidebarVersion")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
    
    def _clear_menu_widgets(self):
        while self.menu_layout.count():
            item = self.menu_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        
        self.buttons.clear()
        self.group_buttons.clear()
        self.group_containers.clear()
        self.group_arrows.clear()
        self.group_keys.clear()
        self.expanded_groups.clear()
        
        for btn in self.button_group.buttons():
            self.button_group.removeButton(btn)
    
    def build_menu(self):
        try:
            self.logger.info("🔨 ساخت منو...")
            self._clear_menu_widgets()
            
            if not self.menu_registry:
                self._build_fallback_menu()
                return
            
            # ۱. داشبورد
            top_items = self.menu_registry.get_top_items()
            for item in top_items:
                if item.key == 'dashboard':
                    if self._has_access(item.module):
                        self._create_top_item(item)
            
            # ۲. گروه‌ها
            groups = self.menu_registry.get_all_groups()
            for group in groups:
                if not self._has_license(group.module):
                    continue
                if not self._has_access(group.module):
                    continue
                
                group_items = self.menu_registry.get_items_by_group(group.key)
                visible_items = [
                    item for item in group_items
                    if self._has_access(item.module)
                ]
                if not visible_items:
                    continue
                
                self._create_group(group, visible_items)
                self.logger.info(f"   ✅ {group.key}: {len(visible_items)} آیتم")
            
            # ۳. بقیه سطح بالا
            other_top = [i for i in top_items if i.key != 'dashboard']
            if other_top:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet(
                    "background: rgba(128,128,128,0.2); "
                    "max-height: 1px; margin: 10px 20px;"
                )
                self.menu_layout.addWidget(sep)
                
                for item in other_top:
                    if self._has_access(item.module):
                        self._create_top_item(item)
            
            # ۴. انتخاب داشبورد
            if 'dashboard' in self.buttons:
                self.buttons['dashboard'].setChecked(True)
            
            self.logger.info(
                f"✅ منو: {len(self.buttons)} آیتم، "
                f"{len(self.group_buttons)} گروه"
            )
        
        except Exception as e:
            self.logger.error(f"❌ خطا در build_menu: {e}")
            import traceback
            traceback.print_exc()
            self._build_fallback_menu()
    
    def _create_top_item(self, item):
        btn = QPushButton(f"{item.icon}  {item.text}")
        btn.setObjectName("sidebarTopBtn")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(
            lambda checked, k=item.key: self._on_item_clicked(k)
        )
        
        if item.source == 'plugin':
            btn.setToolTip(f"پلاگین: {item.plugin_id}")
        
        self.menu_layout.addWidget(btn)
        self.buttons[item.key] = btn
        self.button_group.addButton(btn)
    
    def _create_group(self, group, items):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container.setVisible(False)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 5)
        container_layout.setSpacing(1)
        container_layout.setAlignment(Qt.AlignTop)
        
        for item in items:
            if not self._has_license(item.module):
                child_btn = QPushButton(f"{item.icon}  {item.text} 🔒")
                child_btn.setObjectName("sidebarLockedBtn")
                child_btn.setCheckable(True)
                child_btn.setCursor(Qt.PointingHandCursor)
                child_btn.clicked.connect(
                    lambda checked, k=item.key, m=item.module:
                        self._on_locked_clicked(k, m)
                )
            else:
                child_btn = QPushButton(f"{item.icon}  {item.text}")
                child_btn.setObjectName("sidebarBtn")
                child_btn.setCheckable(True)
                child_btn.setCursor(Qt.PointingHandCursor)
                child_btn.clicked.connect(
                    lambda checked, k=item.key: self._on_item_clicked(k)
                )
                if item.source == 'plugin':
                    child_btn.setToolTip(f"پلاگین: {item.plugin_id}")
            
            container_layout.addWidget(child_btn)
            self.buttons[item.key] = child_btn
            self.group_keys[item.key] = group.key
            self.button_group.addButton(child_btn)
        
        # Header
        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 2, 8, 2)
        header_layout.setSpacing(0)
        
        group_btn = QPushButton(f"{group.icon}  {group.text}")
        group_btn.setObjectName("sidebarGroupBtn")
        group_btn.setCursor(Qt.PointingHandCursor)
        group_btn.setCheckable(False)
        group_btn.setProperty("active", False)
        group_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        arrow_label = QLabel("▶")
        arrow_label.setObjectName("groupArrow")
        arrow_label.setFixedWidth(20)
        arrow_label.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(group_btn, 1)
        header_layout.addWidget(arrow_label)
        
        group_btn.clicked.connect(
            lambda checked=False, k=group.key: self._toggle_group(k)
        )
        
        self.menu_layout.addWidget(header_widget)
        self.menu_layout.addWidget(container)
        
        self.group_buttons[group.key] = group_btn
        self.group_arrows[group.key] = arrow_label
        self.group_containers[group.key] = container
    
    def _toggle_group(self, group_key: str):
        container = self.group_containers.get(group_key)
        arrow = self.group_arrows.get(group_key)
        group_btn = self.group_buttons.get(group_key)
        
        if not container or not arrow:
            return
        
        is_expanded = group_key in self.expanded_groups
        
        if is_expanded:
            container.setVisible(False)
            arrow.setText("▶")
            self.expanded_groups.discard(group_key)
            if group_btn:
                group_btn.setProperty("active", False)
                group_btn.style().unpolish(group_btn)
                group_btn.style().polish(group_btn)
        else:
            container.setVisible(True)
            arrow.setText("▼")
            self.expanded_groups.add(group_key)
            if group_btn:
                group_btn.setProperty("active", True)
                group_btn.style().unpolish(group_btn)
                group_btn.style().polish(group_btn)
        
        QTimer.singleShot(10, self._refresh_layout)
    
    def _refresh_layout(self):
        try:
            self.menu_container.updateGeometry()
            self.menu_container.update()
        except:
            pass
    
    def _expand_group(self, group_key: str):
        if group_key not in self.expanded_groups:
            self._toggle_group(group_key)
    
    def _on_item_clicked(self, key: str):
        self.logger.info(f"🎯 item clicked: {key}")
        self.page_selected.emit(key)
    
    def _on_locked_clicked(self, key: str, module_key: str):
        self.page_selected.emit(f"locked_{module_key}")
    
    def _on_menu_changed(self):
        QTimer.singleShot(100, self.build_menu)
    
    def _build_fallback_menu(self):
        self.logger.warning("🔧 Fallback...")
        fallback = [
            ('📊', 'داشبورد', 'dashboard'),
            ('📚', 'حسابداری', 'accounting'),
            ('📦', 'انبارداری', 'inventory'),
            ('💰', 'حقوق و دستمزد', 'payroll'),
            ('👥', 'اشخاص', 'parties'),
            ('📄', 'خرید و فروش', 'document'),
            ('📊', 'گزارشات', 'reports'),
            ('🤖', 'دستیار هوشمند', 'ai'),
        ]
        for icon, text, key in fallback:
            btn = QPushButton(f"{icon}  {text}")
            btn.setObjectName("sidebarTopBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked, k=key: self._on_item_clicked(k)
            )
            self.menu_layout.addWidget(btn)
            self.buttons[key] = btn
            self.button_group.addButton(btn)
        
        if 'dashboard' in self.buttons:
            self.buttons['dashboard'].setChecked(True)
    
    def set_active(self, page_key: str):
        try:
            parent_group = self.group_keys.get(page_key)
            if parent_group:
                self._expand_group(parent_group)
            
            for key, btn in self.buttons.items():
                btn.setChecked(key == page_key)
            
            if page_key in self.buttons:
                self._scroll_to_widget(self.buttons[page_key])
        except Exception as e:
            self.logger.error(f"خطا در set_active: {e}")
    
    def _scroll_to_widget(self, widget):
        try:
            if hasattr(self, 'scroll_area'):
                QTimer.singleShot(
                    50,
                    lambda: self.scroll_area.ensureWidgetVisible(widget, 30, 30)
                )
        except:
            pass
    
    def refresh(self):
        self.build_menu()


# ============================================================
# WidgetManager
# ============================================================

class WidgetManager(QObject):
    """
    مدیریت ویجت‌ها
    
    ✅ v11.0:
       - اضافه شدن accounting_tree
       - اضافه شدن finance (امور مالی)
    """
    
    def __init__(self, license_info: Dict, user_level: str = 'viewer'):
        super().__init__()
        self.license_info = license_info
        self.user_level = user_level
        self.modules = set(license_info.get('modules', []))
        self.customer_name = license_info.get('customer', '')
        self.widgets = {}
        self.logger = get_logger()
        
        self.REQUIRED = set(get_required_modules())
        
        if MODULES_CONFIG_OK:
            self.PAGE_TO_MODULE = get_page_to_module_map()
        else:
            self.PAGE_TO_MODULE = {
                'accounting': 'accounting',
                'accounting_tree': 'accounting',
                'finance': 'accounting',
                'finance_banks': 'accounting',
                'finance_cash': 'accounting',
                'finance_checks': 'accounting',
                'finance_reports': 'accounting',
                'inventory': 'inventory',
                'payroll': 'payroll',
                'document': 'invoice',
                'document_sales': 'invoice',
                'document_purchase': 'purchase',
                'parties': 'parties',
                'reports': 'reports',
                'ai': 'ai',
            }
    
    def has_license(self, module_key: str) -> bool:
        if module_key is None:
            return True
        if module_key in self.REQUIRED:
            return True
        return module_key in self.modules
    
    def has_access(self, module_key: str) -> bool:
        if not self.has_license(module_key):
            return False
        if MODULES_CONFIG_OK:
            info = get_module_info(module_key)
            min_level = info.get('min_level', 'viewer')
            if not self._check_level(min_level):
                return False
        if UserManager:
            try:
                return UserManager.has_permission(self.user_level, module_key)
            except:
                pass
        return True
    
    def _check_level(self, min_level: str) -> bool:
        if min_level == 'viewer':
            return True
        priority = {
            'admin': 5, 'accountant': 4, 'payroll': 3,
            'inventory': 2, 'viewer': 1
        }
        return priority.get(self.user_level, 0) >= priority.get(min_level, 0)
    
    def get_widget(self, key: str, parent=None):
        if key in self.widgets:
            return self.widgets[key]
        
        module_for_page = self.PAGE_TO_MODULE.get(key)
        if module_for_page and not self.has_license(module_for_page):
            return self._create_upgrade_widget(module_for_page)
        
        try:
            widget = self._build_widget(key, parent)
            if widget:
                self.widgets[key] = widget
                return widget
            raise ValueError(f"صفحه {key} شناسایی نشد")
        except Exception as e:
            self.logger.error(f"خطا در ساخت {key}: {e}")
            import traceback
            traceback.print_exc()
            return self._create_error_widget(str(e))
    
    def _build_widget(self, key: str, parent=None):
        """ساخت ویجت بر اساس کلید"""
        widget = None
        
        # ═══════════════════════════════════════════════════════
        # داشبورد
        # ═══════════════════════════════════════════════════════
        if key == 'dashboard':
            from ui.dashboard_widget import DashboardWidget
            widget = DashboardWidget(user_level=self.user_level, parent=parent)
        
        # ═══════════════════════════════════════════════════════
        # ✅ درختواره حساب‌ها (v10)
        # ═══════════════════════════════════════════════════════
        elif key == 'accounting_tree':
            try:
                from ui.accounting_tree_widget import AccountingTreeWidget
                widget = AccountingTreeWidget(
                    user_level=self.user_level,
                    parent=parent,
                )
                self.logger.info("✅ درختواره حساب‌ها ساخته شد")
            except Exception as e:
                self.logger.error(f"❌ خطا در ساخت درختواره: {e}")
                import traceback
                traceback.print_exc()
                return self._create_error_widget(
                    f"خطا در درختواره: {str(e)}"
                )
        
        # ═══════════════════════════════════════════════════════
        # ✅ امور مالی (v11) — جدید
        # ═══════════════════════════════════════════════════════
        elif key == 'finance':
            try:
                from ui.finance_widget import FinanceWidget
                widget = FinanceWidget(
                    customer_name=self.customer_name,
                    user_level=self.user_level,
                    parent=parent,
                )
                self.logger.info("✅ ویجت امور مالی ساخته شد")
            except Exception as e:
                self.logger.error(f"❌ خطا در ساخت امور مالی: {e}")
                import traceback
                traceback.print_exc()
                return self._create_error_widget(
                    f"خطا در امور مالی: {str(e)}"
                )
        
        # ═══════════════════════════════════════════════════════
        # حسابداری
        # ═══════════════════════════════════════════════════════
        elif key == 'accounting':
            from ui.accounting_widget import AccountingWidget
            widget = AccountingWidget(
                customer_name=self.customer_name,
                user_level=self.user_level, parent=parent
            )
        
        # ═══════════════════════════════════════════════════════
        # انبارداری
        # ═══════════════════════════════════════════════════════
        elif key == 'inventory':
            from ui.inventory_widget import InventoryWidget
            widget = InventoryWidget(
                customer_name=self.customer_name,
                user_level=self.user_level, parent=parent
            )
        
        # ═══════════════════════════════════════════════════════
        # حقوق و دستمزد
        # ═══════════════════════════════════════════════════════
        elif key == 'payroll':
            from ui.payroll_widget import PayrollWidget
            widget = PayrollWidget(
                customer_name=self.customer_name,
                user_level=self.user_level, parent=parent
            )
        
        # ═══════════════════════════════════════════════════════
        # خرید و فروش
        # ═══════════════════════════════════════════════════════
        elif key in ('document', 'document_sales', 'document_purchase'):
            from ui.document_widget import DocumentWidget
            widget = DocumentWidget(
                customer_name=self.customer_name,
                user_level=self.user_level, parent=parent
            )
            if hasattr(widget, 'doc_type_combo'):
                idx = 0 if key != 'document_purchase' else 1
                widget.doc_type_combo.setCurrentIndex(idx)
        
        # ═══════════════════════════════════════════════════════
        # اشخاص
        # ═══════════════════════════════════════════════════════
        elif key == 'parties':
            try:
                from ui.parties_widget import PartiesWidget
                widget = PartiesWidget(
                    customer_name=self.customer_name,
                    user_level=self.user_level, parent=parent
                )
            except ImportError:
                return self._create_error_widget("ماژول اشخاص پیاده نشده")
        
        # ═══════════════════════════════════════════════════════
        # گزارشات
        # ═══════════════════════════════════════════════════════
        elif key == 'reports':
            try:
                from ui.reports_widget import ReportsWidget
                widget = ReportsWidget(user_level=self.user_level, parent=parent)
            except ImportError:
                return self._create_error_widget("ماژول گزارشات پیاده نشده")
        
        # ═══════════════════════════════════════════════════════
        # دستیار هوشمند
        # ═══════════════════════════════════════════════════════
        elif key == 'ai':
            from ui.ai_assistant_widget import AIAssistantWidget
            widget = AIAssistantWidget(parent=parent, user_level=self.user_level)
        
        # ═══════════════════════════════════════════════════════
        # پلاگین‌ها
        # ═══════════════════════════════════════════════════════
        elif key == 'plugins':
            from ui.plugin_manager_widget import PluginManagerWidget
            widget = PluginManagerWidget(
                license_key=self.license_info.get('license_key'),
                parent=parent, user_level=self.user_level
            )
        
        # ═══════════════════════════════════════════════════════
        # ابزارها
        # ═══════════════════════════════════════════════════════
        elif key == 'tools':
            from ui.tools_widget import ToolsWidget
            widget = ToolsWidget(parent=parent, user_level=self.user_level)
        
        # ═══════════════════════════════════════════════════════
        # تنظیمات
        # ═══════════════════════════════════════════════════════
        elif key == 'settings':
            from ui.settings_widget import SettingsWidget
            widget = SettingsWidget(user_level=self.user_level, parent=parent)
        
        return widget
    
    def _create_upgrade_widget(self, module_key: str) -> QWidget:
        name = get_module_name(module_key) if MODULES_CONFIG_OK else module_key
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        layout.addStretch()
        
        icon = QLabel("🔒")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 72pt; background: transparent;")
        layout.addWidget(icon)
        
        title = QLabel(f"ماژول «{name}» فعال نیست")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #e74c3c;")
        layout.addWidget(title)
        
        desc = QLabel(
            "این ماژول در لایسنس فعلی شما وجود ندارد.\n"
            "برای فعال‌سازی با پشتیبانی تماس بگیرید."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("font-size: 12pt; color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        contact = QLabel("📱 0912-XXX-XXXX\n🌐 imanai.ir/pricing")
        contact.setAlignment(Qt.AlignCenter)
        contact.setStyleSheet(
            "font-size: 12pt; font-weight: bold; "
            "color: #1976D2; padding: 20px;"
        )
        layout.addWidget(contact)
        
        layout.addStretch()
        return widget
    
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
        
        detail = QLabel(error[:300])
        detail.setAlignment(Qt.AlignCenter)
        detail.setStyleSheet("color: #888; font-size: 10pt;")
        detail.setWordWrap(True)
        layout.addWidget(detail)
        
        return widget


# ============================================================
# MainWindow
# ============================================================

class MainWindow(BaseWindow, ThemeMixin):
    """پنجره اصلی ImanAccount — v11.0"""
    
    def __init__(self, license_info: Dict, license_key: str = None):
        self.logger = get_logger()
        self.logger.info("=" * 60)
        self.logger.info("🚀 راه‌اندازی MainWindow v11.0")
        self.logger.info("=" * 60)
        
        self.error_handler = get_error_handler()
        self.theme_manager = get_theme_manager()
        self.core = get_app_core() if CORE_OK else None
        
        self.license_info = license_info
        self.license_key = license_key or license_info.get('license_key')
        self.customer_name = license_info.get('customer', '')
        self.current_user = None
        self.splash = None
        
        self.plugin_manager = None
        self.plugin_menu_bridge = None
        self.plugin_widgets = {}
        self.plugin_menus = []
        
        self.idle_timer = None
        self.idle_time = 0
        self.idle_limit = 300
        
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
        
        if self.core:
            self.core.event_bus.theme_changed.connect(self.on_theme_changed)
        else:
            self.theme_manager.add_observer(self.on_theme_changed)
        
        self._init_with_splash()
    
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
                sys.exit(0)
            
            self.splash.show()
            self.splash.show_message("🖥️ راه‌اندازی UI...", 70)
            self._init_ui()
            
            self.splash.show_message("🔌 بارگذاری پلاگین‌ها...", 85)
            self._load_plugins()
            
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
            QMessageBox.critical(self, "خطا", f"خطا:\n\n{str(e)}")
            sys.exit(1)
    
    def _finish_splash(self):
        if self.splash:
            self.splash.hide()
            self.splash = None
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _set_window_icon(self):
        for path in ["Icon.ico", "icon.ico"]:
            if os.path.exists(path):
                try:
                    self.setWindowIcon(QIcon(path))
                    return
                except:
                    pass
    
    def _init_database(self):
        try:
            if DatabaseManager:
                DatabaseManager.init_db()
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
            
            username = (
                self.current_user.get('full_name') or
                self.current_user.get('username', 'کاربر')
            )
            self.setWindowTitle(
                f"🤖 ImanAccount | {self.customer_name} | 👤 {username}"
            )
            self.logger.info(f"✅ کاربر: {username}")
            return True
        except Exception as e:
            self.logger.error(f"خطا: {e}")
            return False
    
    def _show_welcome_message(self):
        try:
            username = (
                self.current_user.get('full_name') or
                self.current_user.get('username', '')
            )
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
        except:
            pass
    
    def on_theme_changed(self, theme_name: str = None):
        try:
            stylesheet = self.theme_manager.get_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
            
            if hasattr(self, 'header') and self.header:
                self.header._on_theme_changed(theme_name)
            if hasattr(self, 'sidebar') and self.sidebar:
                self.sidebar._on_theme_changed(theme_name)
            
            if hasattr(self, 'content_stack'):
                for i in range(self.content_stack.count()):
                    widget = self.content_stack.widget(i)
                    if widget and hasattr(widget, '_on_theme_signal'):
                        try:
                            widget._on_theme_signal(theme_name)
                        except:
                            pass
        except Exception as e:
            self.logger.warning(f"خطا: {e}")
    
    def apply_theme(self):
        try:
            stylesheet = self.theme_manager.get_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
        except:
            pass
    
    def _init_ui(self):
        self.logger.info("🎨 ساخت UI...")
        self._create_menu_bar()
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        self.header = HeaderWidget(self.license_info, self.current_user)
        main_layout.addWidget(self.header)
        
        # Body
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        
        user_level = (
            self.current_user.get('level', 'viewer')
            if self.current_user else 'viewer'
        )
        self.widget_manager = WidgetManager(self.license_info, user_level)
        
        # ثبت منوی پیش‌فرض
        if MENU_REGISTRY_OK:
            try:
                self.logger.info("📋 ثبت منوی پیش‌فرض...")
                register_default_menu()
                reg = get_menu_registry()
                stats = reg.get_stats()
                self.logger.info(
                    f"📊 Groups: {stats['groups']}, Items: {stats['items']}"
                )
            except Exception as e:
                self.logger.error(f"❌ خطا در ثبت منو: {e}")
                import traceback
                traceback.print_exc()
        
        # Sidebar
        self.sidebar = SidebarWidget(
            license_info=self.license_info,
            user_level=user_level,
        )
        self.sidebar.page_selected.connect(self._switch_page)
        body_layout.addWidget(self.sidebar)
        self.logger.info("✅ Sidebar ساخته شد")
        
        # Content Stack
        self.content_stack = QStackedWidget()
        body_layout.addWidget(self.content_stack, 1)
        
        empty_widget = self._create_empty_widget()
        self.content_stack.addWidget(empty_widget)
        
        main_layout.addWidget(body, 1)
        self.apply_theme()
        self.logger.info("✅ UI ساخته شد")
    
    def _create_empty_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(
            "🧠 به ImanAccount خوش آمدید\n\n"
            "لطفاً یک بخش را انتخاب کنید"
        )
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 16pt; padding: 50px; opacity: 0.6;")
        layout.addWidget(label)
        return widget
    
    def _load_plugins(self):
        try:
            from plugins.plugin_loader import PluginManager
            
            license_key = self.license_key or self.license_info.get('license_key')
            self.plugin_manager = PluginManager(
                license_key=license_key,
                license_info=self.license_info,
            )
            
            if PLUGIN_BRIDGE_OK and self.plugin_manager and MENU_REGISTRY_OK:
                try:
                    self.plugin_menu_bridge = PluginMenuBridge(self.plugin_manager)
                    self.plugin_menu_bridge.register_all_plugins()
                    self.logger.info("✅ پلاگین‌ها متصل شدند")
                except Exception as e:
                    self.logger.error(f"خطا: {e}")
            
            self._load_plugin_widgets()
            self._load_plugin_menus()
        except Exception as e:
            self.logger.warning(f"خطا در پلاگین‌ها: {e}")
    
    def _load_plugin_widgets(self):
        try:
            if not self.plugin_manager:
                return
            plugin_tabs = self.plugin_manager.get_plugin_tabs()
            for tab in plugin_tabs:
                plugin_id = tab.get('plugin_id')
                widget_id = tab.get('widget_id') or tab.get('widget')
                if not widget_id or tab.get('widget_key'):
                    continue
                
                widget = self.plugin_manager.get_plugin_widget(plugin_id, widget_id)
                if widget:
                    tab_key = f"plugin_{plugin_id}_{widget_id}"
                    self.plugin_widgets[tab_key] = widget
        except Exception as e:
            self.logger.error(f"خطا: {e}")
    
    def _load_plugin_menus(self):
        try:
            if not self.plugin_manager:
                return
            plugin_menus = self.plugin_manager.get_plugin_menus()
            menubar = self.menuBar()
            
            for menu_info in plugin_menus:
                if menu_info.get('target_group'):
                    continue
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
    
    def _switch_page(self, page_key: str):
        try:
            # ماژول قفل
            if page_key.startswith('locked_'):
                module_key = page_key.replace('locked_', '')
                self._show_upgrade_dialog(module_key)
                return
            
            # پلاگین
            if page_key.startswith('plugin_'):
                self._switch_plugin_page(page_key)
                return
            
            # Registry
            if MENU_REGISTRY_OK:
                registry = get_menu_registry()
                item = registry.get_item(page_key)
                if item:
                    self._switch_registry_item(item, page_key)
                    return
            
            # Fallback
            self._switch_fallback(page_key)
        except Exception as e:
            self.logger.error(f"خطا در switch_page: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _switch_plugin_page(self, page_key: str):
        widget = self.plugin_widgets.get(page_key)
        if widget:
            self.sidebar.set_active(page_key)
            if self.content_stack.indexOf(widget) == -1:
                self.content_stack.addWidget(widget)
            self.content_stack.setCurrentWidget(widget)
    
    def _switch_registry_item(self, item, page_key: str):
        if item.module and not self.widget_manager.has_license(item.module):
            self._show_upgrade_dialog(item.module)
            return
        
        if item.module and not self.widget_manager.has_access(item.module):
            QMessageBox.warning(
                self, "دسترسی محدود", "⚠️ دسترسی ندارید!"
            )
            return
        
        self.sidebar.set_active(page_key)
        widget = self.widget_manager.get_widget(item.widget_key, self)
        
        if widget:
            if self.content_stack.indexOf(widget) == -1:
                self.content_stack.addWidget(widget)
            self.content_stack.setCurrentWidget(widget)
            
            # ✅ سوئیچ به تب مورد نظر (tab_index)
            if item.tab_index is not None and hasattr(widget, 'tabs'):
                try:
                    if widget.tabs.count() > item.tab_index:
                        widget.tabs.setCurrentIndex(item.tab_index)
                        self.logger.info(
                            f"   ✅ تب {item.tab_index} فعال شد"
                        )
                except Exception as e:
                    self.logger.warning(f"خطا در سوئیچ تب: {e}")
            
            if self.core:
                self.core.event_bus.page_changed.emit(page_key)
    
    def _switch_fallback(self, page_key: str):
        module_for_page = self.widget_manager.PAGE_TO_MODULE.get(page_key)
        if module_for_page and not self.widget_manager.has_license(module_for_page):
            self._show_upgrade_dialog(module_for_page)
            return
        
        self.sidebar.set_active(page_key)
        widget = self.widget_manager.get_widget(page_key, self)
        
        if widget:
            if self.content_stack.indexOf(widget) == -1:
                self.content_stack.addWidget(widget)
            self.content_stack.setCurrentWidget(widget)
    
    def _show_upgrade_dialog(self, module_key: str):
        name = get_module_name(module_key) if MODULES_CONFIG_OK else module_key
        QMessageBox.information(
            self, "🔒 این ماژول فعال نیست",
            f"<div style='text-align:center; direction:rtl;'>"
            f"<h3>ماژول «{name}»</h3>"
            f"<p>این ماژول در لایسنس فعلی شما وجود ندارد.</p>"
            f"<p>برای فعال‌سازی با پشتیبانی تماس بگیرید:</p>"
            f"<p><b>📱 0912-XXX-XXXX</b></p>"
            f"<p><b>🌐 imanai.ir/pricing</b></p>"
            f"</div>"
        )
    
    def _create_menu_bar(self):
        menubar = self.menuBar()
        menubar.clear()
        
        user_level = (
            self.current_user.get('level', 'viewer')
            if self.current_user else 'viewer'
        )
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
                    action.setChecked(
                        name == self.theme_manager.get_theme_name()
                    )
                    action.triggered.connect(
                        lambda checked, n=name: self._set_theme(n)
                    )
                    theme_menu.addAction(action)
            except:
                pass
            
            settings_menu.addSeparator()
            users_action = QAction("👥 مدیریت کاربران", self)
            users_action.triggered.connect(
                lambda checked, f=self._manage_users: f()
            )
            settings_menu.addAction(users_action)
        
        # AI
        ai_menu = menubar.addMenu("🤖 هوش مصنوعی")
        for text, func in [
            ("💬 گفتگو با ImanAI", self._open_ai_chat),
            ("🧠 تحلیل مالی", self._open_ai_analysis),
            ("💰 پیشنهاد حساب", self._open_ai_suggestion),
        ]:
            action = QAction(text, self)
            action.triggered.connect(lambda checked, f=func: f())
            ai_menu.addAction(action)
        
        # راهنما
        help_menu = menubar.addMenu("❓ راهنما")
        for item in [
            ("🖥️ HWID", self._show_hwid),
            None,
            ("ℹ️ درباره", self._show_about),
            ("🔑 لایسنس", self._show_license_info),
            ("⌨️ میانبرها", self._show_shortcuts),
        ]:
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
    
    def _open_ai_chat(self, **k):
        self._switch_page('ai_chat')
    
    def _open_ai_analysis(self, **k):
        self._switch_page('ai_analysis')
    
    def _open_ai_suggestion(self, **k):
        self._switch_page('ai_suggest')
    
    def _new_voucher(self, **k):
        self._switch_page('accounting_vouchers')
        w = self.widget_manager.widgets.get('accounting')
        if w and hasattr(w, 'new_voucher'):
            QTimer.singleShot(100, w.new_voucher)
    
    def _new_invoice(self, **k):
        self._switch_page('document_sales')
    
    def _new_purchase(self, **k):
        self._switch_page('document_purchase')
    
    def _manage_users(self, **k):
        try:
            if UserManager:
                from ui.login_dialog import UserManagementDialog
                UserManagementDialog(self).exec_()
        except Exception as e:
            self.error_handler.show_error(self, "خطا", str(e))
    
    def _backup_database(self, **k):
        try:
            from database import DB_NAME
            import shutil
            name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            f, _ = QFileDialog.getSaveFileName(
                self, "پشتیبان", name, "Database (*.db)"
            )
            if f:
                shutil.copy2(DB_NAME, f)
                QMessageBox.information(self, "موفق", "✅ ذخیره شد!")
        except Exception as e:
            self.error_handler.show_error(self, "خطا", str(e))
    
    def _restore_database(self, **k):
        try:
            from database import DB_NAME
            import shutil
            r = QMessageBox.question(
                self, "تأیید", "ادامه؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if r == QMessageBox.Yes:
                f, _ = QFileDialog.getOpenFileName(
                    self, "بازیابی", "", "Database (*.db)"
                )
                if f:
                    shutil.copy2(f, DB_NAME)
                    QMessageBox.information(self, "موفق", "✅ بازیابی شد!")
        except Exception as e:
            self.error_handler.show_error(self, "خطا", str(e))
    
    def _show_hwid(self, **k):
        try:
            from license_core import LicenseCore
            QMessageBox.information(
                self, "🖥️ HWID",
                f"HWID:\n\n{LicenseCore.get_system_hwid()}"
            )
        except:
            pass
    
    def _show_about(self, **k):
        QMessageBox.about(self, "درباره ImanAccount", """
        <div style='text-align: center;'>
            <h2>🤖 ImanAccount</h2>
            <p><b>نسخه ۳.۰.۰</b></p>
            <p>نرم‌افزار جامع حسابداری هوشمند</p>
            <hr><p>🧠 ImanAI ✅</p><p>📧 info@imanai.ir</p>
        </div>
        """)
    
    def _show_license_info(self, **k):
        info = self.license_info
        modules = info.get('modules', [])
        modules_display = [
            f"✅ {get_module_name(m)}" for m in modules
        ] if MODULES_CONFIG_OK else [f"✅ {m}" for m in modules]
        modules_text = "<br>".join(modules_display) if modules_display else "—"
        
        QMessageBox.information(self, "اطلاعات لایسنس", f"""
        <h3>🔑 لایسنس</h3>
        <p><b>مشتری:</b> {info.get('customer', 'N/A')}</p>
        <p><b>انقضا:</b> {info.get('expire_date', 'N/A')[:10] if info.get('expire_date') else 'N/A'}</p>
        <p><b>روز باقی‌مانده:</b> {info.get('days_left', 0)}</p>
        <hr>
        <p><b>📦 ماژول‌های فعال:</b></p>
        <p>{modules_text}</p>
        """)
    
    def _show_shortcuts(self, **k):
        QMessageBox.information(self, "کلیدها", """
        <h3>⌨️ میانبرها</h3>
        <p>Ctrl+N: سند | Ctrl+I: فروش | Ctrl+P: خرید</p>
        <p>Ctrl+L: قفل | Ctrl+Q: خروج</p>
        """)
    
    def _setup_idle_timer(self):
        try:
            self.idle_timer = QTimer()
            self.idle_timer.timeout.connect(self._check_idle)
            self.idle_timer.start(1000)
            self.installEventFilter(self)
        except:
            pass
    
    def _check_idle(self):
        try:
            self.idle_time += 1
            if self.idle_time >= self.idle_limit:
                self._lock_screen()
        except:
            pass
    
    def eventFilter(self, obj, event):
        try:
            if event.type() in [
                QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel
            ]:
                self.idle_time = 0
        except:
            pass
        return super().eventFilter(obj, event)
    
    def _lock_screen(self, **k):
        try:
            if not LockScreenDialog:
                return
            if self.idle_timer:
                self.idle_timer.stop()
            
            username = (
                self.current_user.get('username', '')
                if self.current_user else ''
            )
            lock_dialog = LockScreenDialog(username, self)
            if lock_dialog.exec_() == QDialog.Accepted:
                self.idle_time = 0
                if self.idle_timer:
                    self.idle_timer.start()
            else:
                self.close()
        except:
            pass
    
    def _change_password(self, **k):
        try:
            if not ChangePasswordDialog:
                return
            username = (
                self.current_user.get('username', '')
                if self.current_user else ''
            )
            ChangePasswordDialog(username, self).exec_()
        except Exception as e:
            self.error_handler.show_error(self, "خطا", str(e))
    
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
                    except:
                        pass
                
                event.accept()
            else:
                event.ignore()
        except Exception:
            event.accept()
