
# main2.py
# ============================================================
# ImanAccount - نقطه ورود (v11.0 - Fixed Menu + Wizard)
# ============================================================
# تغییرات v11.0:
# ✅ رفع مشکل منوی خالی (register_default_menu قبل از Sidebar)
# ✅ لاگ دیباگ کامل برای MenuRegistry
# ✅ ساختار تمیزتر و قابل نگهداری
# ✅ مدیریت خطای بهتر
# ============================================================
# ترتیب اجرا:
#   1. Logging
#   2. Exception Hook
#   3. QApplication
#   4. AppCore
#   5. LicenseCore
#   6. First-Run Check → Wizard (اگه لازمه)
#   7. License Check
#   8. Database Init
#   9. MenuRegistry Init ← مهم!
#   10. MainWindow
# ============================================================

import sys
import os
import importlib
from pathlib import Path

# ============================================================
# sys.path
# ============================================================

_PROJECT_ROOT = Path(__file__).parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

importlib.invalidate_caches()
print(f"✅ PROJECT_ROOT: {_PROJECT_ROOT}")


# ============================================================
# Logging — همیشه اول از همه
# ============================================================

from logging_config import (
    setup_logging,
    install_exception_hook,
    get_log_file_path,
    get_log_dir_path,
    generate_diagnostic_report,
    read_recent_logs,
)

LOG_FILE = setup_logging(level=20)  # INFO=20
install_exception_hook()

import logging
logger = logging.getLogger(__name__)
logger.info(f"🚀 شروع ImanAccount v11.0")
logger.info(f"📁 لاگ: {LOG_FILE}")


# ============================================================
# بقیه imports
# ============================================================

import traceback
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMessageBox, QDialog, QVBoxLayout, QLabel,
    QPushButton, QLineEdit, QHBoxLayout, QWizard
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer


# ✅ error handler
from error_handler import get_error_handler, ErrorHandler
error_handler = get_error_handler()


# ============================================================
# ثابت‌ها
# ============================================================

APP_NAME = "ImanAccount"
APP_VERSION = "11.0.0"


# ============================================================
# مسیرهای امن
# ============================================================

def _get_user_data_dir() -> Path:
    if os.name == 'nt':
        appdata = os.environ.get('APPDATA')
        if appdata and os.path.isdir(appdata):
            base = Path(appdata) / "ImanAccount"
        else:
            base = Path.home() / ".imanaccount"
    else:
        base = Path.home() / ".config" / "imanaccount"
    
    base.mkdir(parents=True, exist_ok=True)
    return base


USER_DATA_DIR = _get_user_data_dir()
LICENSE_FILE = USER_DATA_DIR / "license.key"
TRIAL_MARKER_FILE = USER_DATA_DIR / ".trial_used"
LOGS_DIR = USER_DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Trial Management
# ============================================================

def _is_trial_used() -> bool:
    if os.name == 'nt':
        try:
            import winreg
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\ImanAccount", 0, winreg.KEY_READ
                )
            except (FileNotFoundError, OSError):
                return False
            
            try:
                value, _ = winreg.QueryValueEx(key, "TrialUsed")
                winreg.CloseKey(key)
                return value == 1
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            pass
    
    return TRIAL_MARKER_FILE.exists()


def _mark_trial_used():
    if os.name == 'nt':
        try:
            import winreg
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\ImanAccount")
            winreg.SetValueEx(key, "TrialUsed", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "TrialDate", 0, winreg.REG_SZ, datetime.now().isoformat())
            winreg.CloseKey(key)
            logger.info("✅ Trial در Registry علامت‌گذاری شد")
            return
        except Exception as e:
            logger.warning(f"⚠️ خطا در Registry: {e}")
    
    try:
        TRIAL_MARKER_FILE.write_text(datetime.now().isoformat())
    except Exception:
        pass


# ============================================================
# دیالوگ لایسنس
# ============================================================

class LicenseDialog(QDialog):
    """دیالوگ فعال‌سازی لایسنس"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 فعال‌سازی لایسنس")
        self.setModal(True)
        self.setFixedSize(480, 380)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        self.license_data = None
        self.selected_option = None
        
        try:
            from license_core import get_system_hwid
            self.hwid = get_system_hwid()
        except Exception:
            self.hwid = "ERROR"
        
        self.setup_ui()
        self.center_on_screen()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # عنوان
        title = QLabel("🔐 ImanAccount")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #e94560; padding: 5px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # توضیحات
        desc = QLabel("لطفاً کلید لایسنس خود را وارد کنید\nیا از نسخه آزمایشی ۳۰ روزه استفاده کنید.")
        desc.setStyleSheet("color: #aaa; font-size: 10pt;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # HWID
        hwid_label = QLabel("🖥️ شناسه سیستم (HWID):")
        hwid_label.setStyleSheet("color: #888; font-size: 9pt; font-weight: bold;")
        layout.addWidget(hwid_label)
        
        hwid_layout = QHBoxLayout()
        self.hwid_display = QLineEdit(self.hwid)
        self.hwid_display.setReadOnly(True)
        self.hwid_display.setStyleSheet("""
            QLineEdit {
                background: #16213e; color: #4CAF50;
                border: 1px solid #0f3460; border-radius: 4px;
                padding: 6px 10px; font-family: 'Courier New', monospace;
                font-size: 9pt; font-weight: bold;
            }
        """)
        hwid_layout.addWidget(self.hwid_display)
        
        copy_btn = QPushButton("📋 کپی")
        copy_btn.setFixedWidth(70)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #3498db; color: white;
                border: none; border-radius: 4px;
                font-size: 9pt; padding: 6px; font-weight: bold;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        copy_btn.clicked.connect(self.copy_hwid)
        hwid_layout.addWidget(copy_btn)
        
        layout.addLayout(hwid_layout)
        layout.addSpacing(5)
        
        # کد لایسنس
        license_label = QLabel("🔑 کد لایسنس:")
        license_label.setStyleSheet("color: #888; font-size: 9pt; font-weight: bold;")
        layout.addWidget(license_label)
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("کد لایسنس خود را اینجا وارد کنید...")
        self.license_input.setStyleSheet("""
            QLineEdit {
                background: #16213e; color: #eee;
                border: 2px solid #0f3460; border-radius: 6px;
                padding: 10px 14px; font-size: 10pt;
                font-family: 'Courier New', monospace;
            }
            QLineEdit:focus {
                border-color: #e94560; background: #1a2744;
            }
        """)
        self.license_input.returnPressed.connect(self.verify_license)
        layout.addWidget(self.license_input)
        
        layout.addSpacing(10)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        verify_btn = QPushButton("✅ تأیید لایسنس")
        verify_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50; color: white;
                border: none; border-radius: 6px;
                padding: 10px 15px; font-weight: bold; font-size: 10pt;
            }
            QPushButton:hover { background: #388E3C; }
        """)
        verify_btn.clicked.connect(self.verify_license)
        btn_layout.addWidget(verify_btn)
        
        trial_btn = QPushButton("🧪 نسخه آزمایشی")
        trial_btn.setStyleSheet("""
            QPushButton {
                background: #FF9800; color: white;
                border: none; border-radius: 6px;
                padding: 10px 15px; font-weight: bold; font-size: 10pt;
            }
            QPushButton:hover { background: #E68900; }
        """)
        trial_btn.clicked.connect(self.start_trial)
        btn_layout.addWidget(trial_btn)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("❌ خروج")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c; color: white;
                border: none; border-radius: 6px;
                padding: 10px 15px; font-weight: bold; font-size: 10pt;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # وضعیت
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #FF9800; font-size: 9pt; min-height: 25px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        self.license_input.setFocus()
    
    def center_on_screen(self):
        try:
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)
        except Exception:
            pass
    
    def copy_hwid(self):
        try:
            QApplication.clipboard().setText(self.hwid)
            self.status_label.setText("✅ HWID کپی شد!")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")
        except Exception:
            pass
    
    def verify_license(self):
        key = self.license_input.text().strip()
        if not key:
            self.status_label.setText("❌ لطفاً کد لایسنس را وارد کنید!")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
            return
        
        try:
            from license_core import get_license_core
            core = get_license_core()
            result = core.verify_license(key)
            
            if result.get('valid'):
                try:
                    core.save_license(key, str(LICENSE_FILE))
                except Exception:
                    pass
                
                self.status_label.setText("✅ لایسنس معتبر است! در حال ورود...")
                self.status_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")
                
                self.license_data = result.get('data', {}).copy()
                self.license_data['days_left'] = result.get('days_left', 0)
                self.license_data['is_trial'] = False
                self.selected_option = 'official'
                
                QTimer.singleShot(500, self.accept)
            else:
                error_msg = result.get('message', 'لایسنس نامعتبر است!')
                self.status_label.setText(f"❌ {error_msg}")
                self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
                self.license_input.selectAll()
        except Exception as e:
            self.status_label.setText(f"❌ خطا: {str(e)[:100]}")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
    
    def start_trial(self):
        if _is_trial_used():
            QMessageBox.warning(self, "⚠️ نسخه آزمایشی",
                "شما قبلاً از نسخه آزمایشی استفاده کرده‌اید!\n\n"
                "برای ادامه، لطفاً لایسنس خریداری کنید.")
            return
        
        try:
            from license_core import get_license_core
            core = get_license_core()
            result = core.create_trial_license()
            
            if result.get('valid'):
                _mark_trial_used()
                
                self.license_data = result.get('data', {}).copy()
                self.license_data['days_left'] = result.get('days_left', 30)
                self.license_data['is_trial'] = True
                self.selected_option = 'trial'
                
                self.status_label.setText("✅ نسخه آزمایشی ۳۰ روزه فعال شد!")
                self.status_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")
                
                QTimer.singleShot(800, self.accept)
            else:
                self.status_label.setText(f"❌ {result.get('message', 'خطا')}")
                self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
        except Exception as e:
            self.status_label.setText(f"❌ خطا: {str(e)[:100]}")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")


# ============================================================
# MainApplication
# ============================================================

class MainApplication:
    """برنامه اصلی ImanAccount"""
    
    def __init__(self):
        self.app = None
        self.window = None
        self.license_info = None
        self.license_core = None
        self.core = None
        self.is_first_run = False
        self.menu_registry = None
    
    # ============================================================
    # Run — نقطه ورود اصلی
    # ============================================================
    
    def run(self):
        try:
            # تنظیمات High DPI
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
            logger.info("✅ High DPI فعال شد")
            
            # ساخت QApplication
            logger.info("🔄 راه‌اندازی QApplication...")
            self.app = QApplication(sys.argv)
            self.app.setApplicationName(f"{APP_NAME} - نسخه {APP_VERSION}")
            
            # ═══════════════════════════════════════════════════
            # 1. AppCore
            # ═══════════════════════════════════════════════════
            logger.info("🚀 راه‌اندازی AppCore...")
            try:
                from core import get_app_core
                self.core = get_app_core()
                self.core.initialize()
                logger.info("✅ AppCore راه‌اندازی شد")
            except Exception as e:
                logger.error(f"⚠️ خطا در AppCore: {e}")
                self.core = None
            
            # ═══════════════════════════════════════════════════
            # 2. LicenseCore
            # ═══════════════════════════════════════════════════
            try:
                from license_core import get_license_core
                self.license_core = get_license_core()
                logger.info("✅ LicenseCore بارگذاری شد")
            except Exception as e:
                logger.critical(f"❌ خطا: {e}")
                QMessageBox.critical(None, "خطا", f"خطا:\n\n{str(e)}")
                return 1
            
            # ═══════════════════════════════════════════════════
            # 3. First-Run Check
            # ═══════════════════════════════════════════════════
            self.is_first_run = self._check_first_run()
            logger.info(f"🔍 اولین اجرا: {self.is_first_run}")
            
            # ═══════════════════════════════════════════════════
            # 4. License Check
            # ═══════════════════════════════════════════════════
            logger.info("🔐 بررسی لایسنس...")
            if not self.handle_license():
                return 0
            
            if self.core:
                try:
                    self.core.event_bus.publish("license.verified", {
                        'customer': self.license_info.get('customer', ''),
                        'days_left': self.license_info.get('days_left', 0),
                    })
                except Exception:
                    pass
            
            # ═══════════════════════════════════════════════════
            # 5. Database Init
            # ═══════════════════════════════════════════════════
            logger.info("📂 راه‌اندازی دیتابیس...")
            if not self.init_database():
                return 1
            
            # ═══════════════════════════════════════════════════
            # 6. First-Run Wizard
            # ═══════════════════════════════════════════════════
            if self.is_first_run:
                logger.info("🚀 اولین اجرا — نمایش Wizard")
                if not self._run_first_run_wizard():
                    logger.warning("⚠️ کاربر Wizard رو لغو کرد")
                    return 0
            
            # ═══════════════════════════════════════════════════
            # 7. ✅ MenuRegistry Init — مهم برای منو!
            # ═══════════════════════════════════════════════════
            logger.info("=" * 60)
            logger.info("📋 راه‌اندازی MenuRegistry...")
            logger.info("=" * 60)
            self._init_menu_registry()
            
            # ═══════════════════════════════════════════════════
            # 8. MainWindow
            # ═══════════════════════════════════════════════════
            logger.info("🖥️ بارگذاری پنجره اصلی...")
            if not self.load_main_window():
                return 1
            
            if self.window:
                self.window.show()
                self.window.raise_()
                self.window.activateWindow()
                logger.info("✅ برنامه با موفقیت اجرا شد")
            else:
                return 1
            
            # اجرا
            exit_code = self.app.exec_()
            
            if self.core:
                try:
                    self.core.shutdown()
                except Exception:
                    pass
            
            logger.info(f"👋 برنامه با کد {exit_code} بسته شد")
            return exit_code
        
        except Exception as e:
            logger.critical(f"❌ خطا: {e}")
            logger.critical(traceback.format_exc())
            QMessageBox.critical(None, "خطا", f"{str(e)}")
            return 1
    
    # ============================================================
    # MenuRegistry Init — گام جدید و مهم
    # ============================================================
    
    def _init_menu_registry(self):
        """راه‌اندازی و ثبت منوی پیش‌فرض"""
        try:
            from menu_registry import get_menu_registry, register_default_menu
            
            # دریافت registry
            self.menu_registry = get_menu_registry()
            
            # آمار قبل
            stats_before = self.menu_registry.get_stats()
            logger.info(
                f"📊 MenuRegistry (قبل): "
                f"groups={stats_before['groups']}, "
                f"items={stats_before['items']}"
            )
            
            # اگه خالی بود، ثبت کن
            if stats_before['groups'] == 0:
                logger.info("📋 MenuRegistry خالی است — ثبت منوی پیش‌فرض...")
                register_default_menu()
                
                # آمار بعد
                stats_after = self.menu_registry.get_stats()
                logger.info(
                    f"✅ MenuRegistry (بعد): "
                    f"groups={stats_after['groups']}, "
                    f"items={stats_after['items']}"
                )
            else:
                logger.info("📋 MenuRegistry از قبل پر است")
            
            # چاپ ساختار (برای دیباگ)
            try:
                self.menu_registry.print_structure()
            except Exception:
                pass
            
            logger.info("=" * 60)
        
        except ImportError as e:
            logger.error(f"❌ menu_registry پیدا نشد: {e}")
        except Exception as e:
            logger.error(f"❌ خطا در MenuRegistry: {e}", exc_info=True)
    
    # ============================================================
    # First-Run Check
    # ============================================================
    
    def _check_first_run(self) -> bool:
        """بررسی آیا این اولین اجراست"""
        try:
            # مسیر دیتابیس
            if os.name == 'nt':
                appdata = os.environ.get('APPDATA')
                db_dir = Path(appdata) / "ImanAccount" if appdata else Path.home() / ".imanaccount"
            else:
                db_dir = Path.home() / ".config" / "imanaccount"
            
            db_path = db_dir / "accounting.db"
            
            # اگه دیتابیس نیست → اولین اجرا
            if not db_path.exists():
                logger.info("🔍 اولین اجرا: دیتابیس وجود ندارد")
                return True
            
            # اگه دیتابیس هست، چک کن کاربر داره یا نه
            import sqlite3
            try:
                conn = sqlite3.connect(str(db_path), timeout=5)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                # چک wizard_completed
                cursor.execute("SELECT value FROM settings WHERE key = 'wizard_completed'")
                row = cursor.fetchone()
                wizard_done = row and row[0] == 'true'
                
                conn.close()
                
                if user_count == 0:
                    logger.info("🔍 اولین اجرا: هیچ کاربری وجود ندارد")
                    return True
                
                if not wizard_done:
                    logger.info("🔍 اولین اجرا: wizard_completed نیست")
                    return True
                
                logger.info(f"✅ قبلاً راه‌اندازی شده ({user_count} کاربر)")
                return False
            
            except Exception as e:
                logger.warning(f"⚠️ خطا در بررسی: {e}")
                return True
        
        except Exception as e:
            logger.error(f"❌ خطا در _check_first_run: {e}")
            return False
    
    # ============================================================
    # First-Run Wizard
    # ============================================================
    
    def _run_first_run_wizard(self) -> bool:
        """اجرای First-Run Wizard"""
        try:
            from ui.first_run_wizard import FirstRunWizard
            
            wizard = FirstRunWizard()
            result = wizard.exec_()
            
            if result == QWizard.Accepted:
                logger.info("✅ Wizard با موفقیت تکمیل شد")
                return True
            else:
                logger.warning("⚠️ کاربر Wizard رو لغو کرد")
                return False
        
        except ImportError as e:
            logger.error(f"❌ first_run_wizard پیدا نشد: {e}")
            logger.warning("⚠️ Wizard رد شد — ادامه بدون اون")
            return True
        
        except Exception as e:
            logger.error(f"❌ خطا در Wizard: {e}", exc_info=True)
            
            QMessageBox.warning(
                None, "خطا",
                f"❌ خطا در راه‌اندازی Wizard:\n\n{str(e)}\n\n"
                f"لطفاً با پشتیبانی تماس بگیرید."
            )
            return False
    
    # ============================================================
    # License Handler
    # ============================================================
    
    def handle_license(self) -> bool:
        """بررسی و مدیریت لایسنس"""
        try:
            # تلاش برای خواندن از فایل
            if LICENSE_FILE.exists():
                try:
                    with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
                        license_key = f.read().strip()
                    
                    if license_key:
                        result = self.license_core.verify_license(license_key)
                        
                        if result.get('valid'):
                            logger.info("✅ لایسنس معتبر است (از فایل)")
                            
                            self.license_info = result.get('data', {}).copy()
                            self.license_info['days_left'] = result.get('days_left', 0)
                            self.license_info['is_trial'] = result.get('data', {}).get('is_trial', False)
                            
                            return True
                        else:
                            # فایل نامعتبر — حذف کن
                            logger.warning("⚠️ لایسنس فایل نامعتبر است — حذف")
                            try:
                                LICENSE_FILE.unlink()
                            except Exception:
                                pass
                except Exception as e:
                    logger.warning(f"⚠️ خطا در خواندن فایل لایسنس: {e}")
            
            # نمایش دیالوگ لایسنس
            dialog = LicenseDialog()
            if dialog.exec_() != QDialog.Accepted:
                return False
            
            self.license_info = dialog.license_data
            return bool(self.license_info)
        
        except Exception as e:
            logger.error(f"❌ خطا در handle_license: {e}")
            return False
    
    # ============================================================
    # Database Init
    # ============================================================
    
    def init_database(self) -> bool:
        """راه‌اندازی دیتابیس"""
        try:
            from database import DatabaseManager, DB_NAME
            DatabaseManager.init_db()
            logger.info(f"✅ دیتابیس: {DB_NAME}")
            
            # Migration رمزهای قدیمی
            try:
                from security import migrate_old_passwords
                result = migrate_old_passwords()
                
                if result['migrated'] > 0:
                    logger.info(
                        f"✅ {result['migrated']} رمز علامت‌گذاری شد برای تغییر"
                    )
                if result['failed'] > 0:
                    logger.warning(f"⚠️ {result['failed']} رمز fail شد")
            except Exception as e:
                logger.warning(f"⚠️ خطا در migration رمزها: {e}")
            
            # Migration ساختار دیتابیس
            try:
                from migrations import run_migrations
                migration_result = run_migrations()
                
                if migration_result.get('failed', 0) > 0:
                    logger.error(
                        f"❌ {migration_result['failed']} migration ناموفق!"
                    )
                elif migration_result.get('ran', 0) > 0:
                    logger.info(
                        f"✅ {migration_result['ran']} migration اجرا شد"
                    )
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"⚠️ خطا در migrations: {e}")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ خطا در init_database: {e}")
            QMessageBox.critical(None, "خطا", f"{str(e)}")
            return False
    
    # ============================================================
    # MainWindow
    # ============================================================
    
    def load_main_window(self) -> bool:
        """بارگذاری پنجره اصلی"""
        try:
            from ui.main_window import MainWindow
            self.window = MainWindow(self.license_info)
            logger.info("✅ پنجره اصلی ساخته شد")
            
            # آیکون
            icon_paths = [
                Path("Icon.ico"),
                Path(__file__).parent / "Icon.ico",
            ]
            for path in icon_paths:
                if path.exists():
                    try:
                        self.window.setWindowIcon(QIcon(str(path)))
                        break
                    except Exception:
                        pass
            
            return True
        
        except Exception as e:
            logger.error(f"❌ خطا در load_main_window: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(None, "خطا", f"{str(e)}")
            return False


# ============================================================
# Exception Hook
# ============================================================

def exception_hook(exctype, value, tb):
    """Hook برای خطاهای غیرمنتظره"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"❌ خطا:\n{error_msg}")
    try:
        QMessageBox.critical(None, "خطا", f"{value}")
    except Exception:
        pass


# ============================================================
# نقطه ورود
# ============================================================

if __name__ == "__main__":
    sys.excepthook = exception_hook
    logger.info("🚀 شروع برنامه...")
    
    app = MainApplication()
    
    try:
        sys.exit(app.run() or 0)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logger.critical(f"❌ {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
