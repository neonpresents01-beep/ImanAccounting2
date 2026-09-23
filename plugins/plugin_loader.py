# plugins/plugin_loader.py
# ============================================================
# سیستم بارگذاری پلاگین ImanAccount - v4.0
# ============================================================
# 
# ویژگی‌ها:
# ✅ بارگذاری پلاگین‌های رمزنگاری‌شده (.plugin)
# ✅ رمزگشایی خودکار با کلید AES از لایسنس
# ✅ بررسی امضای دیجیتال
# ✅ بررسی ماژول‌های مجاز
# ✅ سازگاری با پلاگین‌های قدیمی
# ✅ پشتیبانی از فایل‌های .py
# ============================================================

import os
import sys
import json
import shutil
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional

# ============================================================
# Import از license_core (همه چیز در یک جا)
# ============================================================
try:
    from license_core import (
        LicenseCore,
        PluginSigner,
        LicenseManager,
        get_license_core
    )
    LICENSE_CORE_AVAILABLE = True
except ImportError as e:
    LICENSE_CORE_AVAILABLE = False
    print(f"⚠️ license_core یافت نشد: {e}")


# ============================================================
# کلاس‌های رویداد
# ============================================================

class PluginEvent:
    """رویدادهای پلاگین"""
    ON_INIT = "on_init"
    ON_CLEANUP = "on_cleanup"
    ON_TAB = "on_tab"
    ON_MENU = "on_menu"
    ON_ACTION = "on_action"
    ON_WIDGET = "on_widget"


# ============================================================
# کلاس Plugin
# ============================================================

class Plugin:
    """نماینده یک پلاگین بارگذاری‌شده"""
    
    def __init__(
        self,
        plugin_id: str,
        name: str,
        version: str,
        author: str,
        module
    ):
        self.id = plugin_id
        self.name = name
        self.version = version
        self.author = author
        self.module = module
        self.events = {}
        self.metadata = {}
        self._register_events()
    
    def _register_events(self):
        """ثبت رویدادهای موجود در ماژول"""
        event_map = {
            PluginEvent.ON_INIT: 'on_init',
            PluginEvent.ON_CLEANUP: 'on_cleanup',
            PluginEvent.ON_TAB: 'on_tab',
            PluginEvent.ON_MENU: 'on_menu',
            PluginEvent.ON_ACTION: 'on_action',
            PluginEvent.ON_WIDGET: 'on_widget',
        }
        
        for event_name, func_name in event_map.items():
            if hasattr(self.module, func_name):
                self.events[event_name] = getattr(self.module, func_name)
    
    def fire(self, event: str, *args, **kwargs):
        """اجرای یک رویداد"""
        if event in self.events:
            try:
                return self.events[event](*args, **kwargs)
            except Exception as e:
                print(f"❌ خطا در رویداد {event} پلاگین {self.id}: {e}")
                import traceback
                traceback.print_exc()
        return None
    
    def has_event(self, event: str) -> bool:
        return event in self.events
    
    def get_tabs(self) -> List[Dict]:
        result = self.fire(PluginEvent.ON_TAB)
        return result if isinstance(result, list) else []
    
    def get_menus(self) -> List[Dict]:
        result = self.fire(PluginEvent.ON_MENU)
        return result if isinstance(result, list) else []
    
    def get_widget(self, widget_id: str):
        return self.fire(PluginEvent.ON_WIDGET, widget_id)
    
    def execute_action(self, action_id: str, **kwargs):
        return self.fire(PluginEvent.ON_ACTION, action_id, **kwargs)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'author': self.author,
            'has_tab': self.has_event(PluginEvent.ON_TAB),
            'has_menu': self.has_event(PluginEvent.ON_MENU),
            'has_action': self.has_event(PluginEvent.ON_ACTION),
            'has_widget': self.has_event(PluginEvent.ON_WIDGET),
        }


# ============================================================
# کلاس اصلی PluginLoader
# ============================================================

class PluginLoader:
    """
    بارگذاری پلاگین‌های ImanAccount
    
    پشتیبانی از:
    - فایل‌های .plugin رمزنگاری‌شده (فرمت جدید)
    - فایل‌های .plugin قدیمی (سازگاری)
    - فایل‌های .py (پلاگین‌های پایتون)
    """
    
    def __init__(
        self,
        plugin_dir: str = "plugins",
        public_key: str = None,
        license_key: str = None,
        license_info: dict = None
    ):
        """
        Args:
            plugin_dir: مسیر پوشه پلاگین‌ها
            public_key: کلید عمومی ImanAI
            license_key: کلید لایسنس مشتری
            license_info: اطلاعات کامل لایسنس (ترجیحاً)
        """
        self.plugin_dir = Path(plugin_dir)
        self.public_key_pem = public_key
        self.license_key = license_key
        self.license_info = license_info or {}
        self.plugins: Dict[str, Plugin] = {}
        
        # ===== LicenseCore =====
        self.license_core = None
        if LICENSE_CORE_AVAILABLE:
            try:
                self.license_core = get_license_core()
            except Exception as e:
                print(f"⚠️ خطا در ایجاد LicenseCore: {e}")
        
        # ===== PluginSigner =====
        self.signer = PluginSigner() if LICENSE_CORE_AVAILABLE else None
        
        # ===== استخراج اطلاعات از لایسنس =====
        if self.license_key and not self.license_info:
            self._load_license_info()
        
        # ===== ایجاد پوشه‌ها =====
        self._create_plugin_directories()
    
    # ============================================================
    # ========== مقداردهی اولیه ==========
    # ============================================================
    
    def _load_license_info(self):
        """بارگذاری اطلاعات لایسنس از کلید"""
        if not LICENSE_CORE_AVAILABLE or not self.license_core:
            print("⚠️ LicenseCore در دسترس نیست!")
            return
        
        try:
            result = self.license_core.verify_license(self.license_key)
            
            if result.get('valid'):
                self.license_info = {
                    'valid': True,
                    'data': result.get('data', {}),
                    'days_left': result.get('days_left', 0),
                    'message': result.get('message', ''),
                }
                
                # استخراج کلید عمومی از لایسنس (اگر داشته باشه)
                data = result.get('data', {})
                if not self.public_key_pem and 'public_key' in data:
                    self.public_key_pem = data['public_key']
                
                print(f"✅ لایسنس معتبر | {result.get('message', '')}")
            else:
                print(f"❌ لایسنس نامعتبر: {result.get('message', '')}")
        
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری لایسنس: {e}")
    
    def _create_plugin_directories(self):
        """ایجاد پوشه‌های موردنیاز"""
        (self.plugin_dir / "official_plugins").mkdir(parents=True, exist_ok=True)
        (self.plugin_dir / "third_party").mkdir(parents=True, exist_ok=True)
        (self.plugin_dir / "__pycache__").mkdir(parents=True, exist_ok=True)
    
    # ============================================================
    # ========== بارگذاری همه پلاگین‌ها ==========
    # ============================================================
    
    def load_all_plugins(self):
        """بارگذاری همه پلاگین‌ها از پوشه‌ها"""
        print("\n" + "=" * 70)
        print("🔍 بارگذاری پلاگین‌ها")
        print("=" * 70)
        
        # ===== ۱. پلاگین‌های رسمی =====
        official_dir = self.plugin_dir / "official_plugins"
        if official_dir.exists():
            print(f"\n📂 پوشه رسمی: {official_dir}")
            self._load_from_directory(official_dir, source="official")
        
        # ===== ۲. پلاگین‌های شخص ثالث =====
        third_party_dir = self.plugin_dir / "third_party"
        if third_party_dir.exists():
            print(f"\n📂 پوشه شخص ثالث: {third_party_dir}")
            self._load_from_directory(third_party_dir, source="third_party")
        
        # ===== خلاصه =====
        print("\n" + "=" * 70)
        print(f"✅ {len(self.plugins)} پلاگین بارگذاری شد")
        print("=" * 70)
        
        for plugin_id, plugin in self.plugins.items():
            info = plugin.to_dict()
            print(f"   📦 {info['name']} v{info['version']}")
            print(f"      - تب: {'✅' if info['has_tab'] else '❌'}")
            print(f"      - منو: {'✅' if info['has_menu'] else '❌'}")
            print(f"      - ویجت: {'✅' if info['has_widget'] else '❌'}")
            print(f"      - اکشن: {'✅' if info['has_action'] else '❌'}")
        
        print("=" * 70 + "\n")
    
    def _load_from_directory(self, directory: Path, source: str):
        """بارگذاری همه پلاگین‌ها از یک پوشه"""
        # فایل‌های .plugin
        plugin_files = list(directory.glob("*.plugin"))
        if plugin_files:
            print(f"\n📄 فایل‌های .plugin: {len(plugin_files)}")
            for file in plugin_files:
                self.load_plugin(str(file), source=source)
        
        # فایل‌های .py
        py_files = [
            f for f in directory.glob("*.py")
            if f.name != "__init__.py"
        ]
        if py_files:
            print(f"\n📄 فایل‌های .py: {len(py_files)}")
            for file in py_files:
                self.load_python_plugin(str(file), source=source)
    
    # ============================================================
    # ========== بارگذاری فایل .plugin ==========
    # ============================================================
    
    def load_plugin(self, plugin_path: str, source: str = "unknown") -> bool:
        """
        بارگذاری فایل .plugin
        
        این تابع به صورت خودکار:
        1. فرمت فایل رو تشخیص می‌ده (جدید/قدیم)
        2. در صورت نیاز رمزگشایی می‌کنه
        3. امضا رو بررسی می‌کنه
        4. کد رو اجرا می‌کنه
        """
        plugin_path = Path(plugin_path)
        print(f"\n   📄 بارگذاری .plugin: {plugin_path.name}")
        
        try:
            # ===== ۱. خواندن فایل =====
            with open(plugin_path, 'rb') as f:
                plugin_data = f.read()
            
            if len(plugin_data) < 8:
                print(f"   ❌ فایل خیلی کوچک است")
                return False
            
            # ============================================================
            # ===== ۲. تشخیص فرمت =====
            # ============================================================
            is_new_format = (
                LICENSE_CORE_AVAILABLE and
                self.license_core and
                LicenseCore.is_encrypted_plugin(plugin_data)
            )
            
            if is_new_format:
                # ===== فرمت جدید: رمزنگاری‌شده =====
                return self._load_encrypted_plugin(plugin_path, plugin_data, source)
            else:
                # ===== فرمت قدیم: بدون رمزنگاری =====
                return self._load_legacy_plugin(plugin_path, plugin_data, source)
        
        except Exception as e:
            print(f"   ❌ خطا در بارگذاری {plugin_path.name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================
    # ========== بارگذاری پلاگین رمزنگاری‌شده (جدید) ==========
    # ============================================================
    
    def _load_encrypted_plugin(
        self,
        plugin_path: Path,
        plugin_data: bytes,
        source: str
    ) -> bool:
        """بارگذاری پلاگین رمزنگاری‌شده"""
        
        # ===== ۱. بررسی LicenseCore =====
        if not self.license_core:
            print(f"   ❌ LicenseCore در دسترس نیست!")
            return False
        
        # ===== ۲. خواندن Header (بدون رمزگشایی) =====
        header = LicenseCore.read_plugin_header(plugin_data)
        
        if not header:
            print(f"   ❌ Header پلاگین نامعتبر است")
            return False
        
        plugin_id = header.get('id', plugin_path.stem)
        plugin_name = header.get('name', plugin_id)
        plugin_type = header.get('type', 'internal')
        
        print(f"   📦 پلاگین: {plugin_name} (v{header.get('version', '?')})")
        print(f"   🏷️ نوع: {plugin_type}")
        
        # ===== ۳. بررسی تکراری نبودن =====
        if plugin_id in self.plugins:
            print(f"   ⚠️ پلاگین {plugin_id} قبلاً بارگذاری شده")
            return False
        
        # ===== ۴. بررسی ماژول‌های موردنیاز =====
        required_modules = header.get('required_modules', [])
        if required_modules:
            print(f"   🔐 ماژول‌های موردنیاز: {required_modules}")
            
            valid, msg = self._check_required_modules(required_modules)
            if not valid:
                print(f"   🔒 {msg}")
                return False
            
            print(f"   ✅ همه ماژول‌ها مجاز هستند")
        
        # ===== ۵. دریافت اطلاعات لایسنس =====
        license_data = self._get_license_data_for_decryption()
        
        if not license_data:
            print(
                f"   ❌ اطلاعات لایسنس برای رمزگشایی موجود نیست!\n"
                f"   این پلاگین رمزنگاری‌شده است و نیاز به لایسنس معتبر دارد."
            )
            return False
        
        # ============================================================
        # ===== ۶. رمزگشایی پلاگین ← قلب سیستم! =====
        # ============================================================
        print(f"   🔓 رمزگشایی پلاگین...")
        
        try:
            manifest, code = self.license_core.decrypt_plugin(
                plugin_data=plugin_data,
                license_data=license_data
            )
        except ValueError as e:
            print(f"   ❌ خطای رمزگشایی:")
            for line in str(e).split('\n'):
                print(f"      {line}")
            return False
        except Exception as e:
            print(f"   ❌ خطای غیرمنتظره در رمزگشایی: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print(f"   ✅ رمزگشایی موفق ({len(code):,} کاراکتر کد)")
        
        # ===== ۷. اجرای کد =====
        return self._execute_plugin_code(
            plugin_id=plugin_id,
            code=code,
            manifest=manifest,
            source=source
        )
    
    # ============================================================
    # ========== بارگذاری پلاگین قدیمی ==========
    # ============================================================
    
    def _load_legacy_plugin(
        self,
        plugin_path: Path,
        plugin_data: bytes,
        source: str
    ) -> bool:
        """بارگذاری پلاگین قدیمی (بدون رمزنگاری)"""
        print(f"   ℹ️ فرمت قدیمی (بدون رمزنگاری)")
        
        try:
            # فرمت قدیم: manifest_len + manifest + sig_len + signature + code
            manifest_len = int.from_bytes(plugin_data[:4], 'big')
            manifest_bytes = plugin_data[4:4+manifest_len]
            manifest = json.loads(manifest_bytes.decode('utf-8'))
            
            offset = 4 + manifest_len
            sig_len = int.from_bytes(plugin_data[offset:offset+4], 'big')
            offset += 4
            signature = plugin_data[offset:offset+sig_len]
            offset += sig_len
            code = plugin_data[offset:]
            
            plugin_id = manifest.get('id', plugin_path.stem)
            
            if plugin_id in self.plugins:
                print(f"   ⚠️ پلاگین {plugin_id} قبلاً بارگذاری شده")
                return False
            
            # ===== بررسی امضا =====
            if self.public_key_pem and self.signer:
                try:
                    code_str = code.decode('utf-8', errors='ignore')
                    signature_str = signature.decode('utf-8', errors='ignore')
                    
                    manifest_json = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
                    data_to_verify = manifest_json + "\n---\n" + code_str
                    
                    is_valid = self.signer.verify_plugin_signature(
                        data_to_verify,
                        signature_str,
                        self.public_key_pem
                    )
                    
                    if not is_valid:
                        print(f"   ❌ امضا نامعتبر است!")
                        return False
                    
                    print(f"   ✅ امضا تأیید شد")
                except Exception as e:
                    print(f"   ⚠️ خطا در بررسی امضا: {e}")
            else:
                print(f"   ⚠️ بدون بررسی امضا")
            
            # ===== اجرای کد =====
            code_str = code.decode('utf-8', errors='ignore')
            
            return self._execute_plugin_code(
                plugin_id=plugin_id,
                code=code_str,
                manifest=manifest,
                source=source
            )
        
        except Exception as e:
            print(f"   ❌ خطا در بارگذاری: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================
    # ========== بارگذاری پلاگین .py ==========
    # ============================================================
    
    def load_python_plugin(self, plugin_path: str, source: str = "unknown") -> bool:
        """بارگذاری پلاگین پایتون (.py)"""
        plugin_path = Path(plugin_path)
        print(f"\n   📄 بارگذاری .py: {plugin_path.name}")
        
        try:
            # ===== بارگذاری ماژول =====
            spec = importlib.util.spec_from_file_location(
                plugin_path.stem,
                str(plugin_path)
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_path.stem] = module
            spec.loader.exec_module(module)
            
            plugin_id = getattr(module, 'PLUGIN_ID', plugin_path.stem)
            
            if plugin_id in self.plugins:
                print(f"   ⚠️ پلاگین {plugin_id} قبلاً بارگذاری شده")
                return False
            
            # ===== بررسی ماژول‌های موردنیاز =====
            required_modules = getattr(module, 'REQUIRED_MODULES', [])
            if required_modules:
                valid, msg = self._check_required_modules(required_modules)
                if not valid:
                    print(f"   🔒 {msg}")
                    return False
            
            # ===== ساخت Plugin =====
            plugin = self._create_plugin(module, plugin_id)
            
            # ذخیره metadata
            plugin.metadata = {
                'source': source,
                'type': getattr(module, 'PLUGIN_TYPE', 'internal'),
                'required_modules': required_modules,
            }
            
            self.plugins[plugin_id] = plugin
            
            print(f"   ✅ پلاگین {plugin_id} بارگذاری شد")
            return True
        
        except Exception as e:
            print(f"   ❌ خطا در بارگذاری {plugin_path.name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================
    # ========== اجرای کد پلاگین ==========
    # ============================================================
    
    def _execute_plugin_code(
        self,
        plugin_id: str,
        code: str,
        manifest: dict,
        source: str
    ) -> bool:
        """اجرای کد پلاگین بعد از رمزگشایی"""
        try:
            # ===== ساخت ماژول =====
            spec = importlib.util.spec_from_loader(
                plugin_id,
                loader=None,
                origin=f"plugin://{plugin_id}"
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_id] = module
            
            # ===== اجرا =====
            exec(code, module.__dict__)
            
            # ===== ساخت Plugin =====
            plugin = self._create_plugin(module, plugin_id)
            
            # ذخیره manifest
            plugin.metadata = manifest.copy()
            plugin.metadata['source'] = source
            
            self.plugins[plugin_id] = plugin
            
            print(f"   ✅ پلاگین {plugin_id} بارگذاری شد")
            return True
        
        except Exception as e:
            print(f"   ❌ خطا در اجرای کد: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================
    # ========== ساخت Plugin از ماژول ==========
    # ============================================================
    
    def _create_plugin(self, module, plugin_id: str) -> Optional[Plugin]:
        """ساخت نمونه Plugin از ماژول"""
        name = getattr(module, 'PLUGIN_NAME', plugin_id)
        version = getattr(module, 'PLUGIN_VERSION', '1.0.0')
        author = getattr(module, 'PLUGIN_AUTHOR', 'Unknown')
        
        plugin = Plugin(plugin_id, name, version, author, module)
        plugin.fire(PluginEvent.ON_INIT)
        
        return plugin
    
    # ============================================================
    # ========== توابع کمکی ==========
    # ============================================================
    
    def _check_required_modules(self, required_modules: List[str]) -> tuple:
        """بررسی ماژول‌های موردنیاز در لایسنس"""
        if not required_modules:
            return True, "✅ نیازی به ماژول خاصی نیست"
        
        # ===== دریافت ماژول‌های لایسنس =====
        license_modules = []
        
        if self.license_info:
            data = self.license_info.get('data', {})
            license_modules = data.get('modules', [])
        
        if not license_modules:
            return False, (
                "❌ ماژول‌های لایسنس یافت نشد!\n"
                "   لطفاً مطمئن شوید لایسنس معتبری نصب کرده‌اید."
            )
        
        # ===== بررسی =====
        missing = [m for m in required_modules if m not in license_modules]
        
        if missing:
            return False, (
                f"❌ ماژول‌های زیر در لایسنس شما فعال نیستند:\n"
                f"   {', '.join(missing)}\n"
                f"   برای فعال‌سازی با پشتیبانی تماس بگیرید."
            )
        
        return True, "✅ همه ماژول‌ها مجاز"
    
    def _get_license_data_for_decryption(self) -> Optional[Dict]:
        """
        دریافت اطلاعات لایسنس برای رمزگشایی
        شامل: machine_id, license_id, plugin_aes_key
        """
        # ===== از license_info =====
        if self.license_info:
            data = self.license_info.get('data', {})
            if data.get('machine_id') and data.get('license_id'):
                return data
        
        # ===== تلاش برای بارگذاری =====
        if self.license_core:
            license_key = self.license_key or self.license_core.load_license()
            
            if license_key:
                try:
                    result = self.license_core.verify_license(license_key)
                    if result.get('valid'):
                        data = result.get('data', {})
                        self.license_info = {
                            'valid': True,
                            'data': data,
                            'days_left': result.get('days_left', 0),
                        }
                        return data
                except Exception as e:
                    print(f"⚠️ خطا در بارگذاری لایسنس: {e}")
        
        return None
    
    # ============================================================
    # ========== API های عمومی ==========
    # ============================================================
    
    def get_plugin_tabs(self) -> List[Dict]:
        """دریافت لیست تب‌های همه پلاگین‌ها"""
        print("\n🔍 دریافت تب‌های پلاگین...")
        tabs = []
        
        for plugin_id, plugin in self.plugins.items():
            if plugin.has_event(PluginEvent.ON_TAB):
                try:
                    plugin_tabs = plugin.get_tabs()
                    if plugin_tabs:
                        for tab in plugin_tabs:
                            tab['plugin_id'] = plugin_id
                            
                            # تعیین widget_id
                            if 'widget' in tab:
                                tab['widget_id'] = tab['widget']
                            elif 'widget_id' in tab:
                                tab['widget_id'] = tab['widget_id']
                            else:
                                tab['widget_id'] = None
                            
                            tabs.append(tab)
                            print(f"   ✅ تب از {plugin_id}: {tab.get('title', 'بدون عنوان')}")
                except Exception as e:
                    print(f"   ❌ {plugin_id}: خطا در دریافت تب: {e}")
        
        print(f"   📊 تعداد کل: {len(tabs)}")
        return tabs
    
    def get_plugin_menus(self) -> List[Dict]:
        """دریافت لیست منوهای همه پلاگین‌ها"""
        print("\n🔍 دریافت منوهای پلاگین...")
        menus = []
        
        for plugin_id, plugin in self.plugins.items():
            if plugin.has_event(PluginEvent.ON_MENU):
                try:
                    plugin_menus = plugin.get_menus()
                    if plugin_menus:
                        for menu in plugin_menus:
                            menu['plugin_id'] = plugin_id
                            menus.append(menu)
                            print(f"   ✅ منو از {plugin_id}: {menu.get('title', 'بدون عنوان')}")
                except Exception as e:
                    print(f"   ❌ {plugin_id}: خطا در دریافت منو: {e}")
        
        print(f"   📊 تعداد کل: {len(menus)}")
        return menus
    
    def get_plugin_widget(self, plugin_id: str, widget_id: str):
        """دریافت ویجت یک پلاگین"""
        print(f"   🔧 دریافت ویجت: {widget_id} از {plugin_id}")
        
        if plugin_id not in self.plugins:
            print(f"   ❌ پلاگین یافت نشد")
            return None
        
        if not widget_id:
            print(f"   ❌ widget_id خالی است")
            return None
        
        plugin = self.plugins[plugin_id]
        
        if plugin.has_event(PluginEvent.ON_WIDGET):
            try:
                widget = plugin.get_widget(widget_id)
                if widget:
                    print(f"   ✅ ویجت دریافت شد")
                    return widget
                else:
                    print(f"   ❌ ویجت پیدا نشد")
            except Exception as e:
                print(f"   ❌ خطا: {e}")
        else:
            print(f"   ⚠️ پلاگین رویداد ON_WIDGET ندارد")
        
        return None
    
    def execute_action(self, plugin_id: str, action_id: str, **kwargs):
        """اجرای اکشن یک پلاگین"""
        if plugin_id not in self.plugins:
            return None
        
        plugin = self.plugins[plugin_id]
        if plugin.has_event(PluginEvent.ON_ACTION):
            try:
                return plugin.execute_action(action_id, **kwargs)
            except Exception as e:
                print(f"   ❌ خطا در اجرای اکشن: {e}")
        
        return None
    
    def get_all_plugins_info(self) -> List[Dict]:
        """اطلاعات همه پلاگین‌ها"""
        return [plugin.to_dict() for plugin in self.plugins.values()]
    
    # ============================================================
    # ========== نصب و حذف ==========
    # ============================================================
    
    def install_plugin(self, source_path: str) -> bool:
        """
        نصب پلاگین از یک فایل
        
        فایل به پوشه third_party کپی می‌شه
        """
        source_path = Path(source_path)
        
        if not source_path.exists():
            print(f"❌ فایل وجود ندارد: {source_path}")
            return False
        
        # ===== تعیین پوشه مقصد =====
        dest_dir = self.plugin_dir / "third_party"
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest = dest_dir / source_path.name
        
        # ===== نام تکراری =====
        counter = 1
        while dest.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            dest = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # ===== کپی =====
        shutil.copy2(source_path, dest)
        print(f"📂 فایل کپی شد به: {dest}")
        
        # ===== بارگذاری =====
        if source_path.suffix == '.plugin':
            return self.load_plugin(str(dest), source="installed")
        elif source_path.suffix == '.py':
            return self.load_python_plugin(str(dest), source="installed")
        
        return False
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """
        حذف کامل پلاگین از حافظه و دیسک
        """
        print(f"\n🗑️ حذف پلاگین: {plugin_id}")
        print("-" * 50)
        
        success = False
        plugin_file_path = None
        
        # ===== ۱. جستجو در پوشه‌ها =====
        search_dirs = [
            self.plugin_dir / "third_party",
            self.plugin_dir / "official_plugins",
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            # فایل‌های .plugin
            for file_path in search_dir.glob("*.plugin"):
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read(200)  # فقط 200 بایت اول
                    
                    header = LicenseCore.read_plugin_header(data)
                    if not header:
                        # فرمت قدیم
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                if data.get('id') == plugin_id:
                                    plugin_file_path = file_path
                                    break
                        except:
                            pass
                    elif header.get('id') == plugin_id:
                        plugin_file_path = file_path
                        print(f"   📁 پیدا شد: {file_path.name}")
                        break
                except Exception as e:
                    print(f"   ⚠️ خطا در خواندن {file_path.name}: {e}")
            
            if plugin_file_path:
                break
            
            # فایل‌های .py
            if not plugin_file_path:
                for file_path in search_dir.glob(f"*.py"):
                    if file_path.stem == plugin_id:
                        plugin_file_path = file_path
                        print(f"   📁 پیدا شد: {file_path.name}")
                        break
        
        # ===== ۲. حذف از حافظه =====
        if plugin_id in self.plugins:
            try:
                plugin = self.plugins[plugin_id]
                plugin.fire(PluginEvent.ON_CLEANUP)
                del self.plugins[plugin_id]
                print(f"   ✅ از حافظه حذف شد")
            except Exception as e:
                print(f"   ⚠️ خطا: {e}")
        
        # ===== ۳. حذف از sys.modules =====
        if plugin_id in sys.modules:
            try:
                del sys.modules[plugin_id]
                print(f"   ✅ از sys.modules حذف شد")
            except Exception as e:
                print(f"   ⚠️ خطا: {e}")
        
        # ===== ۴. حذف فایل =====
        if plugin_file_path and plugin_file_path.exists():
            try:
                os.remove(plugin_file_path)
                print(f"   ✅ فایل {plugin_file_path.name} حذف شد")
                success = True
            except PermissionError:
                print(f"   ❌ فایل در حال استفاده است!")
                return False
            except Exception as e:
                print(f"   ❌ خطا در حذف: {e}")
                return False
        else:
            print(f"   ⚠️ فایل پیدا نشد (شاید قبلاً حذف شده)")
            success = True
        
        # ===== ۵. حذف کش =====
        for search_dir in search_dirs:
            cache_dir = search_dir / "__pycache__"
            if cache_dir.exists():
                for cache_file in cache_dir.glob(f"{plugin_id}*.pyc"):
                    try:
                        os.remove(cache_file)
                        print(f"   ✅ کش حذف شد: {cache_file.name}")
                    except:
                        pass
        
        print("-" * 50)
        print(f"✅ پلاگین {plugin_id} حذف شد")
        return success
    
    def reload_plugins(self):
        """بارگذاری مجدد همه پلاگین‌ها"""
        print("\n🔄 بارگذاری مجدد...")
        
        # Cleanup
        for plugin_id, plugin in self.plugins.items():
            try:
                plugin.fire(PluginEvent.ON_CLEANUP)
            except:
                pass
        
        self.plugins.clear()
        self.load_all_plugins()


# ============================================================
# ========== PluginManager (Singleton) ==========
# ============================================================

class PluginManager:
    """
    مدیریت Singleton پلاگین‌ها
    
    برای دسترسی سراسری از همه جا
    """
    _instance = None
    
    def __new__(
        cls,
        public_key: str = None,
        license_key: str = None,
        license_info: dict = None
    ):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.loader = PluginLoader(
                public_key=public_key,
                license_key=license_key,
                license_info=license_info
            )
            cls._instance.loader.load_all_plugins()
        else:
            # بروزرسانی لایسنس
            updated = False
            
            if license_info:
                cls._instance.loader.license_info = license_info
                updated = True
            elif license_key:
                cls._instance.loader.license_key = license_key
                cls._instance.loader._load_license_info()
                updated = True
            elif public_key:
                cls._instance.loader.public_key_pem = public_key
                updated = True
            
            if updated:
                cls._instance.loader.reload_plugins()
        
        return cls._instance
    
    # ===== API های عمومی =====
    
    def get_all_plugins(self) -> List[Dict]:
        return self.loader.get_all_plugins_info()
    
    def get_plugin_tabs(self) -> List[Dict]:
        return self.loader.get_plugin_tabs()
    
    def get_plugin_widget(self, plugin_id: str, widget_id: str):
        return self.loader.get_plugin_widget(plugin_id, widget_id)
    
    def get_plugin_menus(self) -> List[Dict]:
        return self.loader.get_plugin_menus()
    
    def execute_action(self, plugin_id: str, action_id: str, **kwargs):
        return self.loader.execute_action(plugin_id, action_id, **kwargs)
    
    def reload_plugins(self):
        self.loader.reload_plugins()
    
    def install_plugin(self, plugin_path: str) -> bool:
        return self.loader.install_plugin(plugin_path)
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        return self.loader.uninstall_plugin(plugin_id)
