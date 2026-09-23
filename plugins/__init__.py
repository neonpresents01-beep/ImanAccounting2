# plugins/__init__.py

"""
سیستم پلاگین نرم‌افزار حسابداری - نسخه رویدادمحور

این ماژول سیستم مدیریت پلاگین‌ها را ارائه می‌دهد که بر اساس رویدادها کار می‌کند.
پلاگین‌ها می‌توانند رویدادهای زیر را پیاده‌سازی کنند:

- on_init(): مقداردهی اولیه پلاگین
- on_cleanup(): پاکسازی پلاگین
- on_tab(): دریافت تب‌های پلاگین
- on_menu(): دریافت منوهای پلاگین
- on_widget(widget_id): دریافت ویجت بر اساس شناسه
- on_action(action_id, **kwargs): اجرای اکشن

هر پلاگین باید حداقل PLUGIN_ID و PLUGIN_NAME را داشته باشد.
"""

from .plugin_loader import PluginLoader, PluginManager, Plugin, PluginEvent

__all__ = [
    'PluginLoader',
    'PluginManager', 
    'Plugin',
    'PluginEvent'
]

__version__ = '2.0.0'

__plugin_system_info__ = {
    'version': __version__,
    'type': 'event_driven',
    'events': ['on_init', 'on_cleanup', 'on_tab', 'on_menu', 'on_widget', 'on_action']
}
