# ui/styles/theme_manager.py
# ============================================================
# مدیریت تم‌ها در کل برنامه
# نسخه 3.0 — Core-Integrated + Signal-Based + Observer Compatible
# ============================================================

from typing import Dict, Type, Optional, Callable, List

from .base_theme import BaseTheme
from .dark_theme import DarkTheme
from .light_theme import LightTheme


# ============================================================
# تلاش برای استفاده از QObject + Signal
# ============================================================

try:
    from PyQt5.QtCore import QObject, pyqtSignal
    
    _HAS_QT = True
except ImportError:
    _HAS_QT = False


# ============================================================
# ThemeManager
# ============================================================

if _HAS_QT:
    
    class ThemeManager(QObject):
        """
        مدیریت تم‌های برنامه — Singleton با QObject.
        
        سیگنال‌ها:
            theme_changed(str): وقتی تم عوض می‌شه
            theme_changing(str): قبل از تغییر
        """
        
        theme_changed = pyqtSignal(str)
        theme_changing = pyqtSignal(str)
        
        _instance = None
        _initialized = False
        
        def __new__(cls, *args, **kwargs):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
        
        def __init__(self):
            if ThemeManager._initialized:
                return
            
            super().__init__()
            ThemeManager._initialized = True
            
            self._current_theme: Optional[BaseTheme] = None
            self._theme_classes: Dict[str, Type[BaseTheme]] = {}
            self._observers: List[Callable] = []
            
            # ثبت تم‌ها
            self._register_theme('light', LightTheme)
            self._register_theme('dark', DarkTheme)
            
            # تم پیش‌فرض (بدون signal)
            self._current_theme = self._theme_classes['light']()
            
            # ✅ اتصال به AppCore
            self._connect_to_core()
        
        # ============================================================
        # اتصال به AppCore
        # ============================================================
        
        def _connect_to_core(self):
            """اتصال ThemeManager به AppCore.theme (ThemeService)"""
            try:
                from core import get_app_core
                core = get_app_core()
                if core and hasattr(core, 'theme'):
                    core.theme.attach_manager(self)
                    print("✅ ThemeManager به AppCore متصل شد")
            except ImportError:
                # core هنوز لود نشده — مشکلی نیست
                pass
            except Exception as e:
                print(f"⚠️ خطا در اتصال ThemeManager به core: {e}")
        
        # ============================================================
        # ثبت تم
        # ============================================================
        
        def _register_theme(self, name: str, theme_class: Type[BaseTheme]):
            """ثبت یه تم جدید"""
            self._theme_classes[name] = theme_class
        
        def register_custom_theme(self, name: str, theme_class: Type[BaseTheme]):
            """ثبت تم سفارشی"""
            self._register_theme(name, theme_class)
        
        # ============================================================
        # مدیریت تم
        # ============================================================
        
        def set_theme(self, name: str, emit_signal: bool = True):
            """تغییر تم فعلی"""
            if name not in self._theme_classes:
                print(f"⚠️ تم {name} وجود ندارد!")
                return
            
            if emit_signal:
                self.theme_changing.emit(name)
            
            self._current_theme = self._theme_classes[name]()
            new_name = self._current_theme.name
            
            print(f"🎨 تم به {self._current_theme.display_name} تغییر کرد")
            
            if emit_signal:
                # 1. سیگنال اصلی
                self.theme_changed.emit(new_name)
                
                # 2. observers قدیمی
                self._notify_observers()
        
        def get_current_theme(self) -> Optional[BaseTheme]:
            return self._current_theme
        
        def get_stylesheet(self) -> str:
            if self._current_theme:
                return self._current_theme.get_stylesheet()
            return ""
        
        def get_theme_name(self) -> str:
            if self._current_theme:
                return self._current_theme.name
            return "light"
        
        def is_dark(self) -> bool:
            """آیا تم تاریک است؟"""
            return self.get_theme_name() == 'dark'
        
        def toggle_theme(self):
            """تعویض روشن/تاریک"""
            current = self.get_theme_name()
            new_theme = 'dark' if current == 'light' else 'light'
            self.set_theme(new_theme)
        
        def get_available_themes(self) -> Dict[str, str]:
            """لیست تم‌های موجود"""
            result = {}
            for name, cls in self._theme_classes.items():
                try:
                    result[name] = cls().display_name
                except Exception:
                    result[name] = name
            return result
        
        # ============================================================
        # Observer (سازگاری با کد قدیمی)
        # ============================================================
        
        def add_observer(self, callback: Callable):
            """افزودن observer"""
            if callback not in self._observers:
                self._observers.append(callback)
        
        def remove_observer(self, callback: Callable):
            """حذف observer"""
            if callback in self._observers:
                self._observers.remove(callback)
        
        def _notify_observers(self):
            """اطلاع‌رسانی به observers"""
            for callback in self._observers:
                try:
                    callback(self.get_theme_name())
                except Exception as e:
                    print(f"⚠️ خطا در observer: {e}")


else:
    # ============================================================
    # نسخه بدون Qt (فقط برای تست)
    # ============================================================
    
    class ThemeManager:
        """مدیریت تم‌ها — بدون QObject"""
        
        _instance = None
        _initialized = False
        
        def __new__(cls, *args, **kwargs):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
        
        def __init__(self):
            if ThemeManager._initialized:
                return
            
            ThemeManager._initialized = True
            self._current_theme = None
            self._theme_classes = {}
            self._observers = []
            self._signal_observers = []
            
            self._register_theme('light', LightTheme)
            self._register_theme('dark', DarkTheme)
            self._current_theme = self._theme_classes['light']()
            
            self._connect_to_core()
        
        def _connect_to_core(self):
            try:
                from core import get_app_core
                core = get_app_core()
                if core and hasattr(core, 'theme'):
                    core.theme.attach_manager(self)
            except Exception:
                pass
        
        def _register_theme(self, name, theme_class):
            self._theme_classes[name] = theme_class
        
        def set_theme(self, name: str, emit_signal: bool = True):
            if name not in self._theme_classes:
                return
            self._current_theme = self._theme_classes[name]()
            self._notify_observers()
            print(f"🎨 تم به {self._current_theme.display_name} تغییر کرد")
        
        def get_current_theme(self):
            return self._current_theme
        
        def get_stylesheet(self):
            if self._current_theme:
                return self._current_theme.get_stylesheet()
            return ""
        
        def get_theme_name(self):
            if self._current_theme:
                return self._current_theme.name
            return "light"
        
        def is_dark(self):
            return self.get_theme_name() == 'dark'
        
        def toggle_theme(self):
            current = self.get_theme_name()
            self.set_theme('dark' if current == 'light' else 'light')
        
        def get_available_themes(self):
            result = {}
            for name, cls in self._theme_classes.items():
                try:
                    result[name] = cls().display_name
                except Exception:
                    result[name] = name
            return result
        
        def add_observer(self, callback):
            if callback not in self._observers:
                self._observers.append(callback)
        
        def remove_observer(self, callback):
            if callback in self._observers:
                self._observers.remove(callback)
        
        def _notify_observers(self):
            for callback in self._observers:
                try:
                    callback(self.get_theme_name())
                except Exception:
                    pass


# ============================================================
# Singleton
# ============================================================

_theme_manager_instance: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """دریافت نمونه ThemeManager"""
    global _theme_manager_instance
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager()
    return _theme_manager_instance
