# plugin_menu_bridge.py
# ============================================================
# PluginMenuBridge — پل بین PluginLoader و MenuRegistry
# نسخه 1.0 (Production-Ready)
# ============================================================
# 
# این فایل:
# ✅ پلاگین‌های بارگذاری‌شده رو می‌گیره
# ✅ به صورت خودکار به MenuRegistry اضافه می‌کنه
# ✅ نکات ریز رو مدیریت می‌کنه (target_group, order, tab_index)
# ✅ پشتیبانی از حذف خودکار
# ============================================================

import logging
from typing import Optional, Dict, List

from menu_registry import get_menu_registry

logger = logging.getLogger(__name__)


# ============================================================
# PluginMenuBridge
# ============================================================

class PluginMenuBridge:
    """
    اتصال پلاگین‌ها به MenuRegistry
    
    Usage:
        from plugins.plugin_loader import PluginManager
        from plugin_menu_bridge import PluginMenuBridge
        
        pm = PluginManager(license_key='...')
        bridge = PluginMenuBridge(pm)
        bridge.register_all_plugins()
    """
    
    def __init__(self, plugin_manager):
        """
        Args:
            plugin_manager: PluginManager یا PluginLoader
        """
        self.plugin_manager = plugin_manager
        self.registry = get_menu_registry()
        
        # نگهداری آیتم‌های ثبت‌شده هر پلاگین
        self.registered_items: Dict[str, List[str]] = {}
        self.registered_groups: Dict[str, List[str]] = {}
        
        logger.info("🔌 PluginMenuBridge راه‌اندازی شد")
    
    # ═══════════════════════════════════════════════════════
    # ثبت همه پلاگین‌ها
    # ═══════════════════════════════════════════════════════
    
    def register_all_plugins(self) -> Dict:
        """
        ثبت همه پلاگین‌های بارگذاری‌شده در MenuRegistry
        
        Returns:
            {
                'tabs': N,
                'menus': M,
                'groups': K,
                'items': L,
                'plugins': [...],
                'errors': [...],
            }
        """
        logger.info("=" * 60)
        logger.info("🔌 اتصال پلاگین‌ها به MenuRegistry")
        logger.info("=" * 60)
        
        result = {
            'tabs': 0,
            'menus': 0,
            'groups': 0,
            'items': 0,
            'plugins': [],
            'errors': [],
        }
        
        try:
            # ۱. دریافت تب‌ها
            tabs = self.plugin_manager.get_plugin_tabs()
            result['tabs'] = len(tabs)
            logger.info(f"📊 {len(tabs)} تب از پلاگین‌ها")
            
            # ۲. دریافت منوها
            menus = self.plugin_manager.get_plugin_menus()
            result['menus'] = len(menus)
            logger.info(f"📊 {len(menus)} منو از پلاگین‌ها")
            
            # ۳. ثبت تب‌ها
            for tab in tabs:
                try:
                    success = self._register_tab(tab)
                    if success:
                        result['items'] += 1
                        plugin_id = tab.get('plugin_id', '?')
                        if plugin_id not in result['plugins']:
                            result['plugins'].append(plugin_id)
                except Exception as e:
                    error_msg = f"خطا در تب {tab.get('title', '?')}: {e}"
                    logger.error(error_msg, exc_info=True)
                    result['errors'].append(error_msg)
            
            # ۴. ثبت منوها (به عنوان گروه یا آیتم)
            for menu in menus:
                try:
                    groups_added, items_added = self._register_menu(menu)
                    result['groups'] += groups_added
                    result['items'] += items_added
                    plugin_id = menu.get('plugin_id', '?')
                    if plugin_id not in result['plugins']:
                        result['plugins'].append(plugin_id)
                except Exception as e:
                    error_msg = f"خطا در منو {menu.get('title', '?')}: {e}"
                    logger.error(error_msg, exc_info=True)
                    result['errors'].append(error_msg)
            
            # خلاصه
            logger.info("=" * 60)
            logger.info(
                f"✅ اتصال کامل: "
                f"{result['tabs']} تب، "
                f"{result['menus']} منو، "
                f"{result['items']} آیتم"
            )
            logger.info(f"   پلاگین‌های متصل: {', '.join(result['plugins']) or '—'}")
            if result['errors']:
                logger.warning(f"   ⚠️ {len(result['errors'])} خطا")
            logger.info("=" * 60)
            
            return result
        
        except Exception as e:
            logger.error(f"❌ خطا در register_all_plugins: {e}", exc_info=True)
            result['errors'].append(str(e))
            return result
    
    # ═══════════════════════════════════════════════════════
    # ثبت یک تب
    # ═══════════════════════════════════════════════════════
    
    def _register_tab(self, tab: dict) -> bool:
        """
        ثبت یه تب در MenuRegistry
        
        ساختار tab:
        {
            'plugin_id': 'moadian',
            'title': 'صورتحساب مودیان',
            'icon': '🏛️',
            'widget_id': 'moadian_invoice',
            
            # اختیاری:
            'target_group': 'accounting',       # گروه هدف
            'order': 100,                       # ترتیب
            'module': 'accounting',             # ماژول لایسنس
            'widget_key': 'accounting',         # ادغام در ویجت موجود
            'tab_index': 5,                     # ایندکس تب
        }
        
        Returns:
            True اگه ثبت شد
        """
        plugin_id = tab.get('plugin_id')
        title = tab.get('title')
        
        if not plugin_id or not title:
            logger.warning(f"⚠️ تب ناقص: {tab}")
            return False
        
        # ═══════════════════════════════════════════════════
        # استخراج فیلدها
        # ═══════════════════════════════════════════════════
        icon = tab.get('icon', '📄')
        widget_id = tab.get('widget_id') or tab.get('widget')
        target_group = tab.get('target_group')
        order = tab.get('order', 100)
        module = tab.get('module', plugin_id)
        
        # کلید یونیک
        safe_widget_id = (widget_id or 'main').replace('-', '_').replace(' ', '_')
        item_key = f"plugin_{plugin_id}_{safe_widget_id}"
        
        # widget_key و tab_index
        widget_key = tab.get('widget_key')
        tab_index = tab.get('tab_index')
        
        # اگه widget_key نداره → ویجت مستقل
        if not widget_key:
            widget_key = item_key
            tab_index = None
        
        # ═══════════════════════════════════════════════════
        # چک تکراری نبودن
        # ═══════════════════════════════════════════════════
        if self.registry.has_item(item_key):
            logger.debug(f"   ⚠️ آیتم {item_key} قبلاً ثبت شده")
            return False
        
        # ═══════════════════════════════════════════════════
        # اگه target_group مشخص شده، چک کن گروه وجود داره
        # ═══════════════════════════════════════════════════
        if target_group and not self.registry.has_group(target_group):
            logger.warning(
                f"   ⚠️ گروه '{target_group}' وجود ندارد! "
                f"تب '{title}' در سطح بالا قرار می‌گیرد"
            )
            target_group = None
        
        # ═══════════════════════════════════════════════════
        # ثبت
        # ═══════════════════════════════════════════════════
        success = self.registry.register_item(
            key=item_key,
            text=title,
            icon=icon,
            group=target_group,
            order=order,
            module=module,
            widget_key=widget_key,
            tab_index=tab_index,
            source='plugin',
            plugin_id=plugin_id,
            metadata={
                'widget_id': widget_id,
                'original_tab': tab.copy(),
                'kind': 'tab',
            },
        )
        
        if success:
            # ذخیره برای حذف بعدی
            self.registered_items.setdefault(plugin_id, []).append(item_key)
            
            group_info = target_group or "سطح بالا"
            tab_info = f" (tab={tab_index})" if tab_index is not None else ""
            logger.info(
                f"   ✅ تب ثبت: {icon} {title} "
                f"[گروه: {group_info}{tab_info}]"
            )
        
        return success
    
    # ═══════════════════════════════════════════════════════
    # ثبت یک منو
    # ═══════════════════════════════════════════════════════
    
    def _register_menu(self, menu: dict) -> tuple:
        """
        ثبت یه منوی پلاگین
        
        دو حالت:
        🅰️ target_group داره → آیتم توی گروه موجود
        🅱️ target_group نداره → گروه جدید + آیتم‌هایش
        
        Returns:
            (تعداد گروه‌های اضافه‌شده, تعداد آیتم‌های اضافه‌شده)
        """
        plugin_id = menu.get('plugin_id')
        title = menu.get('title')
        
        if not plugin_id or not title:
            logger.warning(f"⚠️ منو ناقص: {menu}")
            return (0, 0)
        
        icon = menu.get('icon', '🔌')
        target_group = menu.get('target_group')
        order = menu.get('order', 80)
        module = menu.get('module', plugin_id)
        
        # ═══════════════════════════════════════════════════
        # حالت ۱: target_group داره → آیتم توی گروه موجود
        # ═══════════════════════════════════════════════════
        if target_group:
            if not self.registry.has_group(target_group):
                logger.warning(
                    f"   ⚠️ گروه '{target_group}' وجود ندارد"
                )
                return (0, 0)
            
            item_key = f"plugin_menu_{plugin_id}"
            
            if self.registry.has_item(item_key):
                logger.debug(f"   ⚠️ منو {item_key} قبلاً ثبت شده")
                return (0, 0)
            
            success = self.registry.register_item(
                key=item_key,
                text=title,
                icon=icon,
                group=target_group,
                order=order,
                module=module,
                widget_key=item_key,
                tab_index=None,
                source='plugin',
                plugin_id=plugin_id,
                metadata={
                    'menu_data': menu.copy(),
                    'kind': 'menu',
                },
            )
            
            if success:
                self.registered_items.setdefault(plugin_id, []).append(item_key)
                logger.info(
                    f"   ✅ منو ثبت: {icon} {title} → {target_group}"
                )
                return (0, 1)
            
            return (0, 0)
        
        # ═══════════════════════════════════════════════════
        # حالت ۲: گروه جدید
        # ═══════════════════════════════════════════════════
        group_key = f"plugin_group_{plugin_id}"
        groups_added = 0
        items_added = 0
        
        # ثبت گروه (اگه قبلاً نبوده)
        if not self.registry.has_group(group_key):
            success = self.registry.register_group(
                key=group_key,
                text=title,
                icon=icon,
                order=order,
                module=module,
                source='plugin',
                plugin_id=plugin_id,
            )
            
            if success:
                groups_added = 1
                self.registered_groups.setdefault(plugin_id, []).append(group_key)
                logger.info(f"   ✅ گروه ثبت: {icon} {title}")
        
        # ثبت آیتم‌های داخل گروه (actions)
        actions = menu.get('actions', [])
        
        if not actions:
            # اگه action نداره، یه آیتم پیش‌فرض به عنوان dashboard
            actions = [{'id': 'main', 'title': title, 'icon': icon}]
        
        for action in actions:
            action_id = action.get('id', 'default')
            action_title = action.get('title', action_id)
            action_icon = action.get('icon', '📄')
            action_order = action.get('order', 100)
            
            safe_action_id = action_id.replace('-', '_').replace(' ', '_')
            item_key = f"plugin_{plugin_id}_{safe_action_id}"
            
            if self.registry.has_item(item_key):
                logger.debug(f"   ⚠️ آیتم {item_key} قبلاً ثبت شده")
                continue
            
            success = self.registry.register_item(
                key=item_key,
                text=action_title,
                icon=action_icon,
                group=group_key,
                order=action_order,
                module=module,
                widget_key=item_key,
                tab_index=None,
                source='plugin',
                plugin_id=plugin_id,
                metadata={
                    'action_id': action_id,
                    'menu_data': menu.copy(),
                    'kind': 'action',
                },
            )
            
            if success:
                items_added += 1
                self.registered_items.setdefault(plugin_id, []).append(item_key)
                logger.info(f"      ├─ {action_icon} {action_title}")
        
        return (groups_added, items_added)
    
    # ═══════════════════════════════════════════════════════
    # حذف پلاگین
    # ═══════════════════════════════════════════════════════
    
    def unregister_plugin(self, plugin_id: str) -> int:
        """
        حذف همه آیتم‌ها و گروه‌های یه پلاگین
        
        Returns:
            تعداد آیتم‌های حذف‌شده
        """
        logger.info(f"🗑️ حذف پلاگین از منو: {plugin_id}")
        
        # حذف از Registry
        removed = self.registry.unregister_by_plugin(plugin_id)
        
        # پاک کردن از حافظه داخلی
        self.registered_items.pop(plugin_id, None)
        self.registered_groups.pop(plugin_id, None)
        
        logger.info(f"   ✅ {removed} آیتم از منو حذف شد")
        return removed
    
    def unregister_all_plugins(self):
        """حذف همه پلاگین‌ها از منو"""
        logger.info("🗑️ حذف همه پلاگین‌ها از منو")
        
        plugin_ids = set(self.registered_items.keys()) | set(self.registered_groups.keys())
        
        for plugin_id in plugin_ids:
            self.unregister_plugin(plugin_id)
        
        self.registry.clear_plugins()
        self.registered_items.clear()
        self.registered_groups.clear()
    
    # ═══════════════════════════════════════════════════════
    # Reload
    # ═══════════════════════════════════════════════════════
    
    def reload_plugins(self):
        """
        بارگذاری مجدد پلاگین‌ها
        
        ⚠️ باید اول Registry رو پاک کنه، بعد دوباره ثبت کنه
        """
        logger.info("🔄 بارگذاری مجدد پلاگین‌ها")
        
        # ۱. پاک کردن
        self.unregister_all_plugins()
        
        # ۲. Reload در PluginManager
        try:
            self.plugin_manager.reload_plugins()
        except Exception as e:
            logger.warning(f"⚠️ خطا در reload PluginManager: {e}")
        
        # ۳. ثبت مجدد
        return self.register_all_plugins()
    
    # ═══════════════════════════════════════════════════════
    # نصب / حذف پلاگین جدید
    # ═══════════════════════════════════════════════════════
    
    def install_and_register(self, plugin_path: str) -> bool:
        """
        نصب یه پلاگین + ثبت خودکار در Registry
        
        Args:
            plugin_path: مسیر فایل .plugin یا .py
        
        Returns:
            True اگه موفق
        """
        logger.info(f"📥 نصب پلاگین: {plugin_path}")
        
        try:
            # ۱. نصب
            success = self.plugin_manager.install_plugin(plugin_path)
            
            if not success:
                logger.error("❌ نصب ناموفق")
                return False
            
            # ۲. پیدا کردن پلاگین تازه‌نصب‌شده
            # (چون PluginManager خودش load می‌کنه)
            # پس فقط کافیه همه رو دوباره register کنیم
            
            # راه ساده: فقط تب‌ها و منوهای جدید رو اضافه کن
            # (چون PluginManager فقط پلاگین‌های جدید رو load کرده)
            
            all_tabs = self.plugin_manager.get_plugin_tabs()
            all_menus = self.plugin_manager.get_plugin_menus()
            
            # ثبت تب‌ها
            for tab in all_tabs:
                self._register_tab(tab)
            
            # ثبت منوها
            for menu in all_menus:
                self._register_menu(menu)
            
            logger.info("✅ نصب + ثبت کامل")
            return True
        
        except Exception as e:
            logger.error(f"❌ خطا در install_and_register: {e}", exc_info=True)
            return False
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """
        حذف پلاگین از دیسک + Registry
        
        Returns:
            True اگه موفق
        """
        logger.info(f"🗑️ حذف پلاگین: {plugin_id}")
        
        try:
            # ۱. حذف از Registry
            self.unregister_plugin(plugin_id)
            
            # ۲. حذف از دیسک
            success = self.plugin_manager.uninstall_plugin(plugin_id)
            
            if success:
                logger.info("✅ حذف کامل")
            else:
                logger.warning("⚠️ حذف از دیسک ناموفق")
            
            return success
        
        except Exception as e:
            logger.error(f"❌ خطا در uninstall_plugin: {e}", exc_info=True)
            return False
    
    # ═══════════════════════════════════════════════════════
    # Query / Debug
    # ═══════════════════════════════════════════════════════
    
    def get_registered_info(self) -> dict:
        """اطلاعات ثبت‌شده"""
        return {
            'plugins': list(self.registered_items.keys()),
            'items_per_plugin': {
                k: len(v) for k, v in self.registered_items.items()
            },
            'groups_per_plugin': {
                k: len(v) for k, v in self.registered_groups.items()
            },
            'total_items': sum(len(v) for v in self.registered_items.values()),
            'total_groups': sum(len(v) for v in self.registered_groups.values()),
        }
    
    def print_registered_info(self):
        """چاپ اطلاعات برای دیباگ"""
        info = self.get_registered_info()
        
        print("\n" + "=" * 60)
        print("🔌 PluginMenuBridge — اطلاعات ثبت‌شده")
        print("=" * 60)
        print(f"   پلاگین‌ها: {len(info['plugins'])}")
        print(f"   مجموع آیتم‌ها: {info['total_items']}")
        print(f"   مجموع گروه‌ها: {info['total_groups']}")
        print("-" * 60)
        
        for plugin_id, count in info['items_per_plugin'].items():
            groups = info['groups_per_plugin'].get(plugin_id, 0)
            print(f"   🔌 {plugin_id}: {count} آیتم، {groups} گروه")
        
        print("=" * 60 + "\n")


# ============================================================
# Helper Function
# ============================================================

def attach_plugin_menu(plugin_manager) -> PluginMenuBridge:
    """
    اتصال سریع PluginManager به MenuRegistry
    
    Usage:
        from plugins.plugin_loader import PluginManager
        from plugin_menu_bridge import attach_plugin_menu
        
        pm = PluginManager(license_key='...')
        bridge = attach_plugin_menu(pm)
        # تموم! پلاگین‌ها در منو ظاهر میشن
    """
    bridge = PluginMenuBridge(plugin_manager)
    bridge.register_all_plugins()
    return bridge


# ============================================================
# Test / Debug
# ============================================================

if __name__ == "__main__":
    import sys
    import logging
    from PyQt5.QtWidgets import QApplication
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
    )
    
    print("=" * 60)
    print("🧪 تست PluginMenuBridge")
    print("=" * 60)
    
    # QApplication
    app = QApplication(sys.argv)
    
    # ثبت منوی پیش‌فرض
    from menu_registry import register_default_menu
    register_default_menu()
    
    # شبیه‌سازی PluginManager
    class FakePluginManager:
        def get_plugin_tabs(self):
            return [
                {
                    'plugin_id': 'moadian',
                    'title': 'صورتحساب مودیان',
                    'icon': '🏛️',
                    'widget_id': 'moadian_invoice',
                    'target_group': 'accounting',
                    'order': 100,
                    'module': 'accounting',
                    'widget_key': 'accounting',
                    'tab_index': 5,
                },
                {
                    'plugin_id': 'moadian',
                    'title': 'داشبورد مودیان',
                    'icon': '📊',
                    'widget_id': 'moadian_dashboard',
                    'target_group': None,
                    'order': 80,
                    'module': 'accounting',
                },
            ]
        
        def get_plugin_menus(self):
            return [
                {
                    'plugin_id': 'bar',
                    'title': 'بارکد',
                    'icon': '📊',
                    'actions': [
                        {'id': 'scan', 'title': 'اسکن بارکد'},
                        {'id': 'print', 'title': 'چاپ بارکد'},
                    ],
                },
            ]
        
        def reload_plugins(self):
            pass
        
        def install_plugin(self, path):
            return True
        
        def uninstall_plugin(self, plugin_id):
            return True
    
    # ساخت Bridge
    pm = FakePluginManager()
    bridge = PluginMenuBridge(pm)
    
    # ثبت
    result = bridge.register_all_plugins()
    
    # چاپ
    bridge.print_registered_info()
    
    # چاپ ساختار Registry
    from menu_registry import get_menu_registry
    get_menu_registry().print_structure()
    
    print("\n" + "=" * 60)
    print("✅ تست کامل شد")
    print("=" * 60)
