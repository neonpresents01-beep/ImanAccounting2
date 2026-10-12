# menu_registry.py
# ============================================================
# MenuRegistry — منبع واحد حقیقت برای منو
# نسخه 2.0 (Production-Ready + Finance)
# ============================================================
# 
# ویژگی‌ها:
# ✅ ثبت گروه‌ها (Groups)
# ✅ ثبت آیتم‌ها (Items)
# ✅ ترتیب خودکار (order)
# ✅ پشتیبانی از پلاگین‌ها (plugin_id)
# ✅ سیگنال تغییرات (menu_changed)
# ✅ Singleton Pattern
# ✅ Thread-Safe
# ✅ v2.0: اضافه شدن گروه امور مالی
# ============================================================

import logging
from typing import Dict, List, Optional, Any
from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker

logger = logging.getLogger(__name__)


# ============================================================
# Data Classes
# ============================================================

class MenuGroup:
    """
    یه گروه منو (مثل حسابداری، انبارداری، ...)
    
    Attributes:
        key: کلید یونیک گروه (مثل 'accounting')
        text: متن نمایشی (مثل 'حسابداری')
        icon: آیکون (مثل '📚')
        order: ترتیب در منو (کمتر = بالاتر)
        module: ماژول لایسنس (مثل 'accounting')
        source: 'builtin' یا 'plugin'
        plugin_id: اگه پلاگینیه، شناسه پلاگین
    """
    
    def __init__(self, key, text, icon='📁', order=0,
                 module=None, source='builtin', plugin_id=None):
        self.key = key
        self.text = text
        self.icon = icon
        self.order = order
        self.module = module
        self.source = source
        self.plugin_id = plugin_id
    
    def to_dict(self):
        return {
            'key': self.key,
            'text': self.text,
            'icon': self.icon,
            'order': self.order,
            'module': self.module,
            'source': self.source,
            'plugin_id': self.plugin_id,
        }
    
    def __repr__(self):
        return f"MenuGroup({self.key}, '{self.text}', order={self.order})"


class MenuItem:
    """
    یه آیتم منو
    
    Attributes:
        key: کلید یونیک (مثل 'accounting_vouchers')
        text: متن نمایشی
        icon: آیکون
        group: گروه والد (None = سطح بالا)
        order: ترتیب در گروه
        module: ماژول لایسنس
        widget_key: کلید ویجت مربوطه
        tab_index: ایندکس تب (اگه ادغام در ویجت موجود)
        source: 'builtin' یا 'plugin'
        plugin_id: شناسه پلاگین
        metadata: اطلاعات اضافی
    """
    
    def __init__(self, key, text, icon='📄',
                 group=None, order=0, module=None,
                 widget_key=None, tab_index=None,
                 source='builtin', plugin_id=None,
                 metadata=None):
        self.key = key
        self.text = text
        self.icon = icon
        self.group = group
        self.order = order
        self.module = module
        self.widget_key = widget_key or key
        self.tab_index = tab_index
        self.source = source
        self.plugin_id = plugin_id
        self.metadata = metadata or {}
    
    def to_dict(self):
        return {
            'key': self.key,
            'text': self.text,
            'icon': self.icon,
            'group': self.group,
            'order': self.order,
            'module': self.module,
            'widget_key': self.widget_key,
            'tab_index': self.tab_index,
            'source': self.source,
            'plugin_id': self.plugin_id,
            'metadata': self.metadata,
        }
    
    def __repr__(self):
        return f"MenuItem({self.key}, '{self.text}', group={self.group})"


# ============================================================
# MenuRegistry
# ============================================================

class MenuRegistry(QObject):
    """
    رجیستری منو — Singleton Thread-Safe
    
    Usage:
        registry = get_menu_registry()
        
        # ثبت گروه
        registry.register_group(
            key='accounting',
            text='حسابداری',
            icon='📚',
            order=10,
            module='accounting',
        )
        
        # ثبت آیتم
        registry.register_item(
            key='accounting_vouchers',
            text='ثبت اسناد',
            icon='📄',
            group='accounting',
            order=10,
            module='accounting',
            widget_key='accounting',
            tab_index=0,
        )
    """
    
    # ═══════════════════════════════════════════════════════
    # Signals
    # ═══════════════════════════════════════════════════════
    
    menu_changed = pyqtSignal()           # هر تغییری
    item_added = pyqtSignal(str)          # آیتم جدید
    item_removed = pyqtSignal(str)        # آیتم حذف شد
    item_updated = pyqtSignal(str)        # آیتم آپدیت شد
    group_added = pyqtSignal(str)         # گروه جدید
    group_removed = pyqtSignal(str)       # گروه حذف شد
    registry_cleared = pyqtSignal()       # همه پاک شد
    
    # ═══════════════════════════════════════════════════════
    # Singleton
    # ═══════════════════════════════════════════════════════
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        
        # داده‌ها
        self.groups: Dict[str, MenuGroup] = {}
        self.items: Dict[str, MenuItem] = {}
        
        # Thread-Safety
        self._mutex = QMutex()
        
        # آمار
        self._change_count = 0
        
        logger.info("📋 MenuRegistry راه‌اندازی شد")
    
    # ═══════════════════════════════════════════════════════
    # Groups
    # ═══════════════════════════════════════════════════════
    
    def register_group(self, key: str, text: str, icon: str = '📁',
                       order: int = 0, module: str = None,
                       source: str = 'builtin',
                       plugin_id: str = None) -> bool:
        """
        ثبت یه گروه
        
        Args:
            key: کلید یونیک
            text: متن نمایشی
            icon: آیکون
            order: ترتیب
            module: ماژول لایسنس
            source: 'builtin' یا 'plugin'
            plugin_id: شناسه پلاگین
        
        Returns:
            True اگه ثبت شد، False اگه تکراری بود
        """
        lock = QMutexLocker(self._mutex)
        
        if key in self.groups:
            logger.debug(f"⚠️ گروه {key} قبلاً ثبت شده")
            return False
        
        self.groups[key] = MenuGroup(
            key=key, text=text, icon=icon,
            order=order, module=module,
            source=source, plugin_id=plugin_id,
        )
        
        self._change_count += 1
        
        # آزاد کردن lock قبل از emit (مهم!)
        lock.unlock()
        
        self.group_added.emit(key)
        self.menu_changed.emit()
        
        logger.info(f"✅ گروه ثبت: {key} - '{text}' (order={order})")
        return True
    
    def update_group(self, key: str, **kwargs) -> bool:
        """آپدیت یه گروه موجود"""
        lock = QMutexLocker(self._mutex)
        
        if key not in self.groups:
            logger.warning(f"⚠️ گروه {key} یافت نشد")
            return False
        
        group = self.groups[key]
        
        for field in ('text', 'icon', 'order', 'module'):
            if field in kwargs:
                setattr(group, field, kwargs[field])
        
        self._change_count += 1
        lock.unlock()
        
        self.menu_changed.emit()
        logger.info(f"🔄 گروه آپدیت: {key}")
        return True
    
    def unregister_group(self, key: str, cascade: bool = True) -> bool:
        """
        حذف یه گروه
        
        Args:
            key: کلید گروه
            cascade: اگه True، آیتم‌های زیرشاخه هم حذف شن
        """
        lock = QMutexLocker(self._mutex)
        
        if key not in self.groups:
            return False
        
        # حذف آیتم‌های زیرشاخه
        removed_items = []
        if cascade:
            for item_key in list(self.items.keys()):
                if self.items[item_key].group == key:
                    removed_items.append(item_key)
                    del self.items[item_key]
        
        del self.groups[key]
        self._change_count += 1
        
        lock.unlock()
        
        # Emit signalها
        self.group_removed.emit(key)
        for item_key in removed_items:
            self.item_removed.emit(item_key)
        self.menu_changed.emit()
        
        logger.info(f"🗑️ گروه حذف: {key} ({len(removed_items)} آیتم هم حذف شد)")
        return True
    
    def get_group(self, key: str) -> Optional[MenuGroup]:
        """دریافت یه گروه"""
        return self.groups.get(key)
    
    def has_group(self, key: str) -> bool:
        """بررسی وجود گروه"""
        return key in self.groups
    
    def get_all_groups(self) -> List[MenuGroup]:
        """همه گروه‌ها (مرتب‌شده)"""
        groups = list(self.groups.values())
        groups.sort(key=lambda g: (g.order, g.key))
        return groups
    
    def get_plugin_groups(self, plugin_id: str) -> List[MenuGroup]:
        """گروه‌های یه پلاگین"""
        return [
            g for g in self.groups.values()
            if g.plugin_id == plugin_id
        ]
    
    # ═══════════════════════════════════════════════════════
    # Items
    # ═══════════════════════════════════════════════════════
    
    def register_item(self, key: str, text: str, icon: str = '📄',
                      group: str = None, order: int = 0,
                      module: str = None,
                      widget_key: str = None, tab_index: int = None,
                      source: str = 'builtin', plugin_id: str = None,
                      metadata: dict = None) -> bool:
        """
        ثبت یه آیتم
        
        Args:
            key: کلید یونیک
            text: متن نمایشی
            icon: آیکون
            group: گروه والد (None = سطح بالا)
            order: ترتیب
            module: ماژول لایسنس
            widget_key: کلید ویجت (پیش‌فرض = key)
            tab_index: ایندکس تب (اگه ادغام در ویجت موجود)
            source: 'builtin' یا 'plugin'
            plugin_id: شناسه پلاگین
            metadata: اطلاعات اضافی
        
        Returns:
            True اگه ثبت شد
        """
        lock = QMutexLocker(self._mutex)
        
        if key in self.items:
            logger.debug(f"⚠️ آیتم {key} قبلاً ثبت شده")
            return False
        
        # اگه گروه مشخص شده، چک کن وجود داره
        if group and group not in self.groups:
            logger.warning(
                f"⚠️ گروه '{group}' وجود ندارد! "
                f"آیتم '{key}' در سطح بالا قرار می‌گیرد"
            )
            group = None
        
        self.items[key] = MenuItem(
            key=key, text=text, icon=icon,
            group=group, order=order, module=module,
            widget_key=widget_key or key,
            tab_index=tab_index,
            source=source, plugin_id=plugin_id,
            metadata=metadata,
        )
        
        self._change_count += 1
        lock.unlock()
        
        self.item_added.emit(key)
        self.menu_changed.emit()
        
        logger.info(
            f"✅ آیتم ثبت: {key} - '{text}' "
            f"(group={group}, order={order})"
        )
        return True
    
    def update_item(self, key: str, **kwargs) -> bool:
        """آپدیت یه آیتم موجود"""
        lock = QMutexLocker(self._mutex)
        
        if key not in self.items:
            logger.warning(f"⚠️ آیتم {key} یافت نشد")
            return False
        
        item = self.items[key]
        
        for field in ('text', 'icon', 'group', 'order',
                      'module', 'widget_key', 'tab_index', 'metadata'):
            if field in kwargs:
                setattr(item, field, kwargs[field])
        
        self._change_count += 1
        lock.unlock()
        
        self.item_updated.emit(key)
        self.menu_changed.emit()
        logger.info(f"🔄 آیتم آپدیت: {key}")
        return True
    
    def unregister_item(self, key: str) -> bool:
        """حذف یه آیتم"""
        lock = QMutexLocker(self._mutex)
        
        if key not in self.items:
            return False
        
        del self.items[key]
        self._change_count += 1
        lock.unlock()
        
        self.item_removed.emit(key)
        self.menu_changed.emit()
        
        logger.info(f"🗑️ آیتم حذف: {key}")
        return True
    
    def unregister_by_plugin(self, plugin_id: str) -> int:
        """
        حذف همه آیتم‌ها و گروه‌های یه پلاگین
        
        Returns:
            تعداد آیتم‌های حذف‌شده
        """
        lock = QMutexLocker(self._mutex)
        
        removed_items = []
        removed_groups = []
        
        # آیتم‌ها
        for key in list(self.items.keys()):
            if self.items[key].plugin_id == plugin_id:
                removed_items.append(key)
                del self.items[key]
        
        # گروه‌ها (با آیتم‌هاشون)
        for key in list(self.groups.keys()):
            if self.groups[key].plugin_id == plugin_id:
                # آیتم‌های این گروه رو هم حذف کن
                for item_key in list(self.items.keys()):
                    if self.items[item_key].group == key:
                        if item_key not in removed_items:
                            removed_items.append(item_key)
                        del self.items[item_key]
                
                removed_groups.append(key)
                del self.groups[key]
        
        total_removed = len(removed_items) + len(removed_groups)
        self._change_count += 1
        
        lock.unlock()
        
        # Emit
        for item_key in removed_items:
            self.item_removed.emit(item_key)
        for group_key in removed_groups:
            self.group_removed.emit(group_key)
        
        if total_removed > 0:
            self.menu_changed.emit()
        
        logger.info(
            f"🗑️ پلاگین {plugin_id}: "
            f"{len(removed_items)} آیتم، "
            f"{len(removed_groups)} گروه حذف شد"
        )
        return len(removed_items)
    
    def get_item(self, key: str) -> Optional[MenuItem]:
        """دریافت یه آیتم"""
        return self.items.get(key)
    
    def has_item(self, key: str) -> bool:
        """بررسی وجود آیتم"""
        return key in self.items
    
    def get_items_by_group(self, group_key: Optional[str] = None) -> List[MenuItem]:
        """
        آیتم‌های یه گروه (مرتب‌شده)
        
        Args:
            group_key: کلید گروه (None = آیتم‌های سطح بالا)
        """
        items = [
            item for item in self.items.values()
            if item.group == group_key
        ]
        items.sort(key=lambda i: (i.order, i.key))
        return items
    
    def get_top_items(self) -> List[MenuItem]:
        """آیتم‌های سطح بالا"""
        return self.get_items_by_group(None)
    
    def get_plugin_items(self, plugin_id: str) -> List[MenuItem]:
        """آیتم‌های یه پلاگین"""
        return [
            i for i in self.items.values()
            if i.plugin_id == plugin_id
        ]
    
    def get_items_by_module(self, module: str) -> List[MenuItem]:
        """آیتم‌های یه ماژول"""
        return [
            i for i in self.items.values()
            if i.module == module
        ]
    
    # ═══════════════════════════════════════════════════════
    # Query / Stats
    # ═══════════════════════════════════════════════════════
    
    def get_stats(self) -> dict:
        """آمار رجیستری"""
        return {
            'groups': len(self.groups),
            'items': len(self.items),
            'plugin_groups': sum(
                1 for g in self.groups.values() if g.source == 'plugin'
            ),
            'plugin_items': sum(
                1 for i in self.items.values() if i.source == 'plugin'
            ),
            'builtin_groups': sum(
                1 for g in self.groups.values() if g.source == 'builtin'
            ),
            'builtin_items': sum(
                1 for i in self.items.values() if i.source == 'builtin'
            ),
            'change_count': self._change_count,
        }
    
    def get_all_items(self) -> List[MenuItem]:
        """همه آیتم‌ها (مرتب‌شده)"""
        items = list(self.items.values())
        items.sort(key=lambda i: (i.group or '', i.order, i.key))
        return items
    
    # ═══════════════════════════════════════════════════════
    # Clear
    # ═══════════════════════════════════════════════════════
    
    def clear(self):
        """پاک کردن همه چیز"""
        lock = QMutexLocker(self._mutex)
        
        self.items.clear()
        self.groups.clear()
        self._change_count += 1
        
        lock.unlock()
        
        self.registry_cleared.emit()
        self.menu_changed.emit()
        logger.info("🧹 MenuRegistry پاک شد")
    
    def clear_plugins(self):
        """پاک کردن فقط آیتم‌ها و گروه‌های پلاگین‌ها"""
        lock = QMutexLocker(self._mutex)
        
        # حذف آیتم‌های پلاگین
        removed_items = []
        for key in list(self.items.keys()):
            if self.items[key].source == 'plugin':
                removed_items.append(key)
                del self.items[key]
        
        # حذف گروه‌های پلاگین
        removed_groups = []
        for key in list(self.groups.keys()):
            if self.groups[key].source == 'plugin':
                removed_groups.append(key)
                del self.groups[key]
        
        self._change_count += 1
        lock.unlock()
        
        if removed_items or removed_groups:
            self.menu_changed.emit()
        
        logger.info(
            f"🧹 پلاگین‌ها پاک شدند: "
            f"{len(removed_items)} آیتم، "
            f"{len(removed_groups)} گروه"
        )
    
    # ═══════════════════════════════════════════════════════
    # Export / Import
    # ═══════════════════════════════════════════════════════
    
    def export_structure(self) -> dict:
        """خروجی ساختار برای دیباگ"""
        return {
            'groups': [g.to_dict() for g in self.get_all_groups()],
            'items': [i.to_dict() for i in self.get_all_items()],
            'stats': self.get_stats(),
        }
    
    def print_structure(self):
        """چاپ ساختار (برای دیباگ)"""
        stats = self.get_stats()
        print("\n" + "=" * 70)
        print(f"📋 MenuRegistry Structure")
        print("=" * 70)
        print(f"   Groups: {stats['groups']} "
              f"(builtin: {stats['builtin_groups']}, "
              f"plugin: {stats['plugin_groups']})")
        print(f"   Items:  {stats['items']} "
              f"(builtin: {stats['builtin_items']}, "
              f"plugin: {stats['plugin_items']})")
        print("=" * 70)
        
        # گروه‌ها
        for group in self.get_all_groups():
            source_mark = "🔌" if group.source == 'plugin' else "🏗️"
            print(f"\n{source_mark} {group.icon} {group.text} "
                  f"(key={group.key}, order={group.order})")
            
            items = self.get_items_by_group(group.key)
            for item in items:
                mark = "🔌" if item.source == 'plugin' else "  "
                tab_info = f" tab={item.tab_index}" if item.tab_index is not None else ""
                print(f"   {mark} {item.icon} {item.text} "
                      f"(key={item.key}{tab_info})")
        
        # سطح بالا
        top_items = self.get_top_items()
        if top_items:
            print(f"\n🏠 سطح بالا:")
            for item in top_items:
                mark = "🔌" if item.source == 'plugin' else "  "
                print(f"   {mark} {item.icon} {item.text} (key={item.key})")
        
        print("\n" + "=" * 70 + "\n")


# ============================================================
# Singleton Accessor
# ============================================================

_registry_instance: Optional[MenuRegistry] = None


def get_menu_registry() -> MenuRegistry:
    """دریافت نمونه Singleton"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = MenuRegistry()
    return _registry_instance


# ============================================================
# Helper: ثبت منوی پیش‌فرض نرم‌افزار
# ============================================================

def register_default_menu():
    """
    ثبت منوی پیش‌فرض نرم‌افزار
    
    این تابع رو تو main_window._init_ui صدا بزن
    """
    r = get_menu_registry()
    
    # اگه قبلاً ثبت شده، دوباره ثبت نکن
    if r.has_group('accounting'):
        logger.debug("⚠️ منوی پیش‌فرض قبلاً ثبت شده")
        return
    
    # ═══════════════════════════════════════════════════════
    # ۱. گروه‌ها
    # ═══════════════════════════════════════════════════════
    
    r.register_group(
        key='accounting', text='حسابداری', icon='📚',
        order=10, module='accounting', source='builtin',
    )
    
    # ✅ گروه امور مالی (جدید v2.0)
    r.register_group(
        key='finance', text='امور مالی', icon='💰',
        order=15, module='accounting', source='builtin',
    )
    
    r.register_group(
        key='inventory', text='انبارداری', icon='📦',
        order=20, module='inventory', source='builtin',
    )
    
    r.register_group(
        key='payroll', text='حقوق و دستمزد', icon='💵',
        order=30, module='payroll', source='builtin',
    )
    
    r.register_group(
        key='parties', text='اشخاص', icon='👥',
        order=40, module='parties', source='builtin',
    )
    
    r.register_group(
        key='documents', text='خرید و فروش', icon='📄',
        order=50, module='invoice', source='builtin',
    )
    
    r.register_group(
        key='reports', text='گزارشات', icon='📊',
        order=60, module='reports', source='builtin',
    )
    
    r.register_group(
        key='ai', text='هوش مصنوعی', icon='🤖',
        order=70, module='ai', source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۲. داشبورد (سطح بالا)
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='dashboard', text='داشبورد', icon='📊',
        group=None, order=0, module=None,
        widget_key='dashboard', tab_index=None,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۳. حسابداری
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='accounting_vouchers', text='ثبت اسناد', icon='📄',
        group='accounting', order=10, module='accounting',
        widget_key='accounting', tab_index=0,
        source='builtin',
    )
    
    r.register_item(
        key='accounting_journal', text='دفتر روزنامه', icon='📖',
        group='accounting', order=20, module='accounting',
        widget_key='accounting', tab_index=1,
        source='builtin',
    )
    
    r.register_item(
        key='accounting_ledger', text='دفتر کل', icon='📚',
        group='accounting', order=30, module='accounting',
        widget_key='accounting', tab_index=2,
        source='builtin',
    )
    
    r.register_item(
        key='accounting_tree', text='درختواره حساب‌ها', icon='🌳',
        group='accounting', order=40, module='accounting',
        widget_key='accounting_tree', tab_index=None,
        source='builtin',
    )
    
    r.register_item(
        key='accounting_closing', text='بستن حساب‌ها', icon='🔒',
        group='accounting', order=50, module='accounting',
        widget_key='accounting', tab_index=4,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۳.۵. امور مالی (جدید v2.0)
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='finance', text='امور مالی', icon='💰',
        group='finance', order=10, module='accounting',
        widget_key='finance', tab_index=0,
        source='builtin',
    )
    
    r.register_item(
        key='finance_banks', text='بانک‌ها', icon='🏦',
        group='finance', order=20, module='accounting',
        widget_key='finance', tab_index=1,
        source='builtin',
    )
    
    r.register_item(
        key='finance_cash', text='صندوق‌ها', icon='💵',
        group='finance', order=30, module='accounting',
        widget_key='finance', tab_index=2,
        source='builtin',
    )
    
    r.register_item(
        key='finance_checks', text='چک‌ها', icon='📄',
        group='finance', order=40, module='accounting',
        widget_key='finance', tab_index=3,
        source='builtin',
    )
    
    r.register_item(
        key='finance_history', text='تاریخچه', icon='📊',
        group='finance', order=50, module='accounting',
        widget_key='finance', tab_index=4,
        source='builtin',
    )
    
    r.register_item(
        key='finance_reports', text='گزارشات مالی', icon='📈',
        group='finance', order=60, module='accounting',
        widget_key='finance', tab_index=5,
        source='builtin',
    )
    
    r.register_item(
        key='finance_ai', text='دستیار هوشمند مالی', icon='🤖',
        group='finance', order=70, module='accounting',
        widget_key='finance', tab_index=6,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۴. انبارداری
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='inventory_products', text='مدیریت کالاها', icon='📦',
        group='inventory', order=10, module='inventory',
        widget_key='inventory', tab_index=0,
        source='builtin',
    )
    
    r.register_item(
        key='inventory_warehouses', text='انبارها', icon='🏢',
        group='inventory', order=20, module='inventory',
        widget_key='inventory', tab_index=1,
        source='builtin',
    )
    
    r.register_item(
        key='inventory_transactions', text='رسید و حواله', icon='📥',
        group='inventory', order=30, module='inventory',
        widget_key='inventory', tab_index=2,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۵. حقوق و دستمزد
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='payroll_main', text='حقوق و دستمزد', icon='💰',
        group='payroll', order=10, module='payroll',
        widget_key='payroll', tab_index=0,
        source='builtin',
    )
    
    r.register_item(
        key='payroll_items', text='اقلام حقوق', icon='📋',
        group='payroll', order=20, module='payroll',
        widget_key='payroll', tab_index=1,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۶. اشخاص
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='parties_main', text='مدیریت اشخاص', icon='👥',
        group='parties', order=10, module='parties',
        widget_key='parties', tab_index=0,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۷. خرید و فروش
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='document_sales', text='فاکتور فروش', icon='📤',
        group='documents', order=10, module='invoice',
        widget_key='document', tab_index=0,
        source='builtin',
    )
    
    r.register_item(
        key='document_purchase', text='فاکتور خرید', icon='📥',
        group='documents', order=20, module='purchase',
        widget_key='document', tab_index=1,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۸. گزارشات
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='reports_main', text='گزارشات جامع', icon='📊',
        group='reports', order=10, module='reports',
        widget_key='reports', tab_index=0,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۹. هوش مصنوعی
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='ai_chat', text='چت با AI', icon='💬',
        group='ai', order=10, module='ai',
        widget_key='ai', tab_index=0,
        source='builtin',
    )
    
    r.register_item(
        key='ai_analysis', text='تحلیل مالی', icon='🧠',
        group='ai', order=20, module='ai',
        widget_key='ai', tab_index=2,
        source='builtin',
    )
    
    r.register_item(
        key='ai_suggest', text='پیشنهاد حساب', icon='💡',
        group='ai', order=30, module='ai',
        widget_key='ai', tab_index=3,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # ۱۰. ادمین (سطح بالا)
    # ═══════════════════════════════════════════════════════
    
    r.register_item(
        key='settings', text='تنظیمات', icon='⚙️',
        group=None, order=100, module='admin',
        widget_key='settings', tab_index=None,
        source='builtin',
    )
    
    r.register_item(
        key='plugins', text='مدیریت پلاگین‌ها', icon='🧩',
        group=None, order=101, module='admin',
        widget_key='plugins', tab_index=None,
        source='builtin',
    )
    
    r.register_item(
        key='tools', text='ابزارها', icon='🛠️',
        group=None, order=102, module='admin',
        widget_key='tools', tab_index=None,
        source='builtin',
    )
    
    # ═══════════════════════════════════════════════════════
    # خلاصه
    # ═══════════════════════════════════════════════════════
    
    stats = r.get_stats()
    logger.info(
        f"✅ منوی پیش‌فرض ثبت شد: "
        f"{stats['groups']} گروه، {stats['items']} آیتم"
    )


# ============================================================
# Test / Debug
# ============================================================

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
    )
    
    print("=" * 70)
    print("🧪 تست MenuRegistry v2.0")
    print("=" * 70)
    
    # ساخت QApplication (لازم برای QObject)
    app = QApplication(sys.argv)
    
    # ۱. ثبت منوی پیش‌فرض
    print("\n📋 ثبت منوی پیش‌فرض...")
    register_default_menu()
    
    # ۲. چاپ ساختار
    registry = get_menu_registry()
    registry.print_structure()
    
    # ۳. آمار نهایی
    print("\n📊 آمار نهایی:")
    stats = registry.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 70)
    print("✅ تست کامل شد")
    print("=" * 70)
