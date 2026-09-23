# ui/base_widgets.py
# ============================================================
# کلاس‌های پایه — نسخه 3.0 (Core-Integrated + Auto-Theme)
# ============================================================

import sys
from pathlib import Path

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# ============================================================
# اطمینان از sys.path
# ============================================================

_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ============================================================
# Imports با try/except
# ============================================================

try:
    from screen_utils import WindowResizer, ScreenManager
    SCREEN_OK = True
except ImportError:
    SCREEN_OK = False
    
    class ScreenManager:
        def __init__(self):
            self.scale = 1.0
        def get_scaled(self, v): return v
        def get_font_size(self, s): return s
        def get_spacing(self, v=10): return v
        def get_margin(self, v=10): return v
        def get_padding(self, v=10): return v
        def center_window(self, w): pass
        def resize_window(self, w, *a, **k): pass
        def is_small_screen(self): return False
        def is_medium_screen(self): return True
        def is_large_screen(self): return False
    
    class WindowResizer:
        def __init__(self, w, *a, **k): pass


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
    
    _sm = SimpleThemeManager()
    def get_theme_manager():
        return _sm


try:
    from core import get_app_core
    CORE_OK = True
except ImportError:
    CORE_OK = False
    def get_app_core():
        return None


# ============================================================
# ThemeMixin
# ============================================================

class ThemeMixin:
    """Mixin برای تم و Core"""
    
    def _is_dark(self) -> bool:
        try:
            if hasattr(self, 'core') and self.core:
                return self.core.theme.is_dark()
            if hasattr(self, 'theme_manager') and self.theme_manager:
                return self.theme_manager.get_theme_name() == 'dark'
        except Exception:
            pass
        return False
    
    def get_theme_colors(self) -> dict:
        is_dark = self._is_dark()
        
        if is_dark:
            return {
                'bg': "#0f0f23", 'bg_alt': "#1a1a2e", 'bg_tertiary': "#16213e",
                'card': "#1a1a2e", 'text': "#e8e8e8", 'text_secondary': "#a0a0a0",
                'text_tertiary': "#666666", 'text_white': "#ffffff",
                'border': "#0f3460", 'border_light': "#2a2a4a",
                'hover': "#2a2a4a", 'selected': "#e94560", 'selected_text': "#ffffff",
                'success': "#27ae60", 'danger': "#e74c3c", 'warning': "#f39c12",
                'info': "#3498db", 'purple': "#9C27B0",
                'header_bg': "#0f3460", 'header_text': "#ffffff",
                'is_dark': True,
            }
        else:
            return {
                'bg': "#f5f6fa", 'bg_alt': "#ffffff", 'bg_tertiary': "#eef2f5",
                'card': "#ffffff", 'text': "#1a1a2e", 'text_secondary': "#5d6d7e",
                'text_tertiary': "#a0a0a0", 'text_white': "#ffffff",
                'border': "#dcdde1", 'border_light': "#e5e8ec",
                'hover': "#e8e8e8", 'selected': "#1976D2", 'selected_text': "#ffffff",
                'success': "#27ae60", 'danger': "#e74c3c", 'warning': "#f39c12",
                'info': "#3498db", 'purple': "#9C27B0",
                'header_bg': "#e8e8e8", 'header_text': "#1a1a2e",
                'is_dark': False,
            }
    
    def _on_theme_signal(self, theme_name: str = None):
        try:
            if hasattr(self, 'theme_manager') and self.theme_manager:
                stylesheet = self.theme_manager.get_stylesheet()
                if stylesheet:
                    self.setStyleSheet(stylesheet)
            
            if hasattr(self, '_apply_widget_theme'):
                try:
                    self._apply_widget_theme()
                except Exception as e:
                    print(f"⚠️ خطا در _apply_widget_theme: {e}")
        except Exception as e:
            print(f"⚠️ خطا در _on_theme_signal: {e}")
    
    # ============================================================
    # Helper Stylesheets
    # ============================================================
    
    def get_table_stylesheet(self) -> str:
        c = self.get_theme_colors()
        return f"""
            QTableWidget {{
                background: {c['card']}; color: {c['text']};
                gridline-color: {c['border']}; border: 1px solid {c['border']};
                border-radius: 8px; alternate-background-color: {c['bg_alt']};
            }}
            QTableWidget::item {{
                color: {c['text']}; padding: 5px;
            }}
            QTableWidget::item:selected {{
                background: {c['selected']}; color: {c['selected_text']};
            }}
            QHeaderView::section {{
                background: {c['bg_tertiary']}; color: {c['text']};
                padding: 8px; border: none; font-weight: bold;
            }}
        """
    
    def get_textedit_stylesheet(self) -> str:
        c = self.get_theme_colors()
        return f"""
            QTextEdit {{
                background: {c['bg_alt']}; color: {c['text']};
                border: 1px solid {c['border']}; border-radius: 8px;
                padding: 10px; font-family: Tahoma; font-size: 10pt;
            }}
        """
    
    def get_label_info_stylesheet(self) -> str:
        c = self.get_theme_colors()
        return f"""
            font-weight: bold; padding: 8px 12px;
            background: {c['bg_alt']}; border: 1px solid {c['border']};
            border-radius: 6px; color: {c['text']};
        """
    
    def get_group_stylesheet(self) -> str:
        c = self.get_theme_colors()
        return f"""
            QGroupBox {{
                color: {c['text']}; border: 1px solid {c['border']};
                border-radius: 8px; margin-top: 12px;
                padding-top: 10px; font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 10px;
                padding: 0 10px; color: {c['selected']};
                background: {c['bg']};
            }}
        """
    
    def get_combo_stylesheet(self) -> str:
        c = self.get_theme_colors()
        return f"""
            QComboBox {{
                background: {c['bg_alt']}; color: {c['text']};
                border: 1px solid {c['border']}; border-radius: 6px;
                padding: 6px 10px; min-height: 28px;
            }}
            QComboBox:focus {{
                border-color: {c['selected']};
            }}
            QComboBox QAbstractItemView {{
                background: {c['bg_alt']}; color: {c['text']};
                selection-background-color: {c['selected']};
                selection-color: {c['selected_text']};
            }}
        """
    
    def get_lineedit_stylesheet(self) -> str:
        c = self.get_theme_colors()
        return f"""
            QLineEdit {{
                background: {c['bg_alt']}; color: {c['text']};
                border: 1px solid {c['border']}; border-radius: 6px;
                padding: 6px 10px; min-height: 28px;
            }}
            QLineEdit:focus {{
                border-color: {c['selected']};
            }}
        """
    
    def _auto_theme_children(self):
        """اعمال خودکار تم روی همه فرزندان"""
        try:
            for table in self.findChildren(QTableWidget):
                table.setStyleSheet(self.get_table_stylesheet())
            
            for te in self.findChildren(QTextEdit):
                te.setStyleSheet(self.get_textedit_stylesheet())
            
            for gb in self.findChildren(QGroupBox):
                gb.setStyleSheet(self.get_group_stylesheet())
            
            for cb in self.findChildren(QComboBox):
                cb.setStyleSheet(self.get_combo_stylesheet())
            
            for le in self.findChildren(QLineEdit):
                le.setStyleSheet(self.get_lineedit_stylesheet())
        except Exception as e:
            print(f"⚠️ خطا در _auto_theme_children: {e}")


# ============================================================
# BaseWindow
# ============================================================

class BaseWindow(QMainWindow, ThemeMixin):
    """کلاس پایه پنجره‌های اصلی"""
    
    def __init__(self, parent=None,
                 base_width=None, base_height=None,
                 scale_factor=1.0, center=True, max_size=None):
        super().__init__(parent)
        
        self.screen_manager = ScreenManager()
        self.theme_manager = get_theme_manager()
        
        self.core = None
        if CORE_OK:
            try:
                self.core = get_app_core()
            except Exception:
                pass
        
        if base_width is None or base_height is None:
            base_width = 1200
            base_height = 800
        
        try:
            self.resizer = WindowResizer(
                self, base_width, base_height, scale_factor, center, max_size
            )
        except Exception:
            self.setMinimumSize(base_width, base_height)
        
        self.setWindowFlags(Qt.Window)
        self._setup_common_style()
        
        try:
            if self.core:
                self.core.event_bus.theme_changed.connect(self._on_theme_signal)
            else:
                self.theme_manager.add_observer(self._on_theme_signal)
        except Exception:
            pass
    
    def _setup_common_style(self):
        """استایل پایه"""
        try:
            stylesheet = self.theme_manager.get_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
        except Exception as e:
            print(f"⚠️ خطا در _setup_common_style: {e}")
    
    def on_theme_changed(self, theme_name: str = None):
        self._on_theme_signal(theme_name)
    
    def apply_theme(self):
        self._on_theme_signal(self.theme_manager.get_theme_name())
    
    def center(self):
        try:
            self.screen_manager.center_window(self)
        except Exception:
            pass
    
    def closeEvent(self, event):
        try:
            if self.core:
                self.core.event_bus.theme_changed.disconnect(self._on_theme_signal)
        except Exception:
            pass
        event.accept()


# ============================================================
# BaseDialog
# ============================================================

class BaseDialog(QDialog, ThemeMixin):
    """کلاس پایه دیالوگ‌ها"""
    
    def __init__(self, parent=None,
                 base_width=None, base_height=None,
                 scale_factor=1.0, center=True, max_size=None,
                 modal=True):
        super().__init__(parent)
        
        self.setModal(modal)
        self.screen_manager = ScreenManager()
        self.theme_manager = get_theme_manager()
        
        self.core = None
        if CORE_OK:
            try:
                self.core = get_app_core()
            except Exception:
                pass
        
        if base_width is None or base_height is None:
            base_width = 600
            base_height = 450
        
        try:
            self.resizer = WindowResizer(
                self, base_width, base_height, scale_factor, center, max_size
            )
        except Exception:
            self.setMinimumSize(base_width, base_height)
        
        self._setup_common_style()
        
        try:
            if self.core:
                self.core.event_bus.theme_changed.connect(self._on_theme_signal)
            else:
                self.theme_manager.add_observer(self._on_theme_signal)
        except Exception:
            pass
    
    def _setup_common_style(self):
        """استایل پایه"""
        try:
            stylesheet = self.theme_manager.get_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
        except Exception as e:
            print(f"⚠️ خطا در _setup_common_style: {e}")
    
    # Helper Methods
    def scaled(self, value: int) -> int:
        try:
            return self.screen_manager.get_scaled(value)
        except Exception:
            return value
    
    def font_size(self, size: int) -> int:
        try:
            return self.screen_manager.get_font_size(size)
        except Exception:
            return size
    
    def spacing(self, value: int = 10) -> int:
        try:
            return self.screen_manager.get_spacing(value)
        except Exception:
            return value
    
    def margin(self, value: int = 10) -> int:
        try:
            return self.screen_manager.get_margin(value)
        except Exception:
            return value
    
    def padding(self, value: int = 10) -> int:
        try:
            return self.screen_manager.get_padding(value)
        except Exception:
            return value
    
    def create_button(self, text: str, object_name: str = "") -> QPushButton:
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        btn.setMinimumHeight(self.scaled(32))
        return btn
    
    def create_table(self, columns: list, stretch_last: bool = True) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        if stretch_last:
            table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setDefaultSectionSize(self.scaled(30))
        return table
    
    def create_input(self, placeholder: str = "") -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setMinimumHeight(self.scaled(32))
        return inp
    
    def on_theme_changed(self, theme_name: str = None):
        self._on_theme_signal(theme_name)
    
    def apply_theme(self):
        self._on_theme_signal(self.theme_manager.get_theme_name())
    
    def center(self):
        try:
            self.screen_manager.center_window(self)
        except Exception:
            pass
    
    def closeEvent(self, event):
        try:
            if self.core:
                self.core.event_bus.theme_changed.disconnect(self._on_theme_signal)
        except Exception:
            pass
        event.accept()


# ============================================================
# BaseWidget — مهم‌ترین کلاس
# ============================================================

class BaseWidget(QWidget, ThemeMixin):
    """
    کلاس پایه همه ویجت‌ها.
    
    ✅ اتصال خودکار به Core
    ✅ اتصال خودکار به theme_changed
    ✅ اتصال خودکار به page_changed
    ✅ اتصال خودکار به data_changed
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.screen_manager = ScreenManager()
        self.theme_manager = get_theme_manager()
        
        # اتصال به core
        self.core = None
        if CORE_OK:
            try:
                self.core = get_app_core()
            except Exception:
                pass
        
        # ✅ این خط خیلی مهمه
        self._setup_common_style()
        
        # ✅ اتصال به سیگنال‌های core
        try:
            if self.core:
                self.core.event_bus.theme_changed.connect(self._on_theme_signal)
                self.core.event_bus.page_changed.connect(self._on_page_changed)
                self.core.event_bus.data_changed.connect(self._on_data_changed)
            else:
                self.theme_manager.add_observer(self._on_theme_signal)
        except Exception as e:
            print(f"⚠️ خطا در اتصال signals: {e}")
        
        # اعمال اولیه تم
        QTimer.singleShot(100, self._initial_theme_apply)
    def apply_theme(self):
        """اعمال تم"""
        self._on_theme_signal(self.theme_manager.get_theme_name())
    
    def on_theme_changed(self, theme_name: str = None):
        """Alias"""
        self._on_theme_signal(theme_name)
    def _setup_common_style(self):
        """
        ✅ استایل پایه — این متد باید وجود داشته باشه.
        """
        try:
            stylesheet = self.theme_manager.get_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
        except Exception as e:
            print(f"⚠️ خطا در _setup_common_style: {e}")
    
    def _initial_theme_apply(self):
        try:
            if hasattr(self, '_apply_widget_theme'):
                self._apply_widget_theme()
        except Exception as e:
            print(f"⚠️ خطا در _initial_theme_apply: {e}")
    
    # ============================================================
    # Overridable Methods
    # ============================================================
    
    def _on_page_changed(self, page_key: str):
        """وقتی صفحه عوض شد"""
        pass
    
    def _on_data_changed(self, entity: str, action: str, data: dict):
        """وقتی داده عوض شد"""
        pass
    
    def _apply_widget_theme(self):
        """اعمال تم روی ویجت"""
        self._auto_theme_children()
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def scaled(self, value: int) -> int:
        try:
            return self.screen_manager.get_scaled(value)
        except Exception:
            return value
    
    def font_size(self, size: int) -> int:
        try:
            return self.screen_manager.get_font_size(size)
        except Exception:
            return size
    
    def spacing(self, value: int = 10) -> int:
        try:
            return self.screen_manager.get_spacing(value)
        except Exception:
            return value
    
    def margin(self, value: int = 10) -> int:
        try:
            return self.screen_manager.get_margin(value)
        except Exception:
            return value
    
    def padding(self, value: int = 10) -> int:
        try:
            return self.screen_manager.get_padding(value)
        except Exception:
            return value
    
    # ============================================================
    # ساخت ویجت
    # ============================================================
    
    def create_table(self, columns: list, stretch_last: bool = True) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        if stretch_last:
            table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setDefaultSectionSize(self.scaled(30))
        return table
    
    def create_button(self, text: str, object_name: str = "") -> QPushButton:
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        btn.setMinimumHeight(self.scaled(32))
        return btn
    
    def create_input(self, placeholder: str = "") -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setMinimumHeight(self.scaled(32))
        return inp
    
    def create_label(self, text: str, object_name: str = "") -> QLabel:
        label = QLabel(text)
        if object_name:
            label.setObjectName(object_name)
        return label
    
    # ============================================================
    # Core Helpers
    # ============================================================
    
    def register_context(self, name: str, provider, priority: int = 5, description: str = ""):
        """ثبت context برای AI"""
        if self.core and hasattr(self.core.ai, 'register_context'):
            try:
                self.core.ai.register_context(
                    name=name,
                    provider=provider,
                    priority=priority,
                    description=description,
                    widget=self
                )
            except Exception as e:
                print(f"⚠️ خطا در register_context {name}: {e}")
    
    def unregister_context(self, name: str):
        """حذف context"""
        if self.core and hasattr(self.core.ai, 'unregister_context'):
            try:
                self.core.ai.unregister_context(name)
            except Exception:
                pass
    
    def notify(self, message: str, level: str = "info"):
        """اطلاع‌رسانی"""
        if self.core and hasattr(self.core, 'notifications'):
            try:
                if level == "success":
                    self.core.notifications.success(message)
                elif level == "warning":
                    self.core.notifications.warning(message)
                elif level == "error":
                    self.core.notifications.error(message)
                else:
                    self.core.notifications.info(message)
            except Exception as e:
                print(f"⚠️ خطا در notify: {e}")
    
    def emit_data_changed(self, entity: str, action: str, data: dict = None):
        """اطلاع‌رسانی تغییر داده"""
        if self.core and hasattr(self.core, 'data'):
            try:
                if action == 'create':
                    self.core.data.created(entity, data)
                elif action == 'update':
                    self.core.data.updated(entity, data)
                elif action == 'delete':
                    self.core.data.deleted(entity, data)
                else:
                    self.core.data.notify_change(entity, action, data)
            except Exception as e:
                print(f"⚠️ خطا در emit_data_changed: {e}")
    
    # ============================================================
    # Close
    # ============================================================
    
    def closeEvent(self, event):
        try:
            if self.core:
                self.core.event_bus.theme_changed.disconnect(self._on_theme_signal)
                self.core.event_bus.page_changed.disconnect(self._on_page_changed)
                self.core.event_bus.data_changed.disconnect(self._on_data_changed)
        except Exception:
            pass
        event.accept()
