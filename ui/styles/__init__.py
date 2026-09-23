# ui/styles/__init__.py
# مدیریت تم‌ها

from .theme_manager import ThemeManager, get_theme_manager
from .dark_theme import DarkTheme
from .light_theme import LightTheme
from .base_theme import BaseTheme

__all__ = [
    'ThemeManager',
    'get_theme_manager',
    'DarkTheme',
    'LightTheme',
    'BaseTheme'
]
