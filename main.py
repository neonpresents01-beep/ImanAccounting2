# main.py - نسخه ساده و کاربردی با دیالوگ کوچک لایسنس

import sys
import os
import traceback
import logging
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QHBoxLayout
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QTimer

from license_core import get_license_core, get_system_hwid
from database import DatabaseManager,DB_NAME

APP_NAME = "ImanAccount"
APP_VERSION = "1.0.0"


# ============================================================
# تنظیمات لاگ‌گیری
# ============================================================

def setup_logging():
    log_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / "ImanAccount" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"imanaccount_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"🚀 {APP_NAME} v{APP_VERSION} شروع شد")
    logging.info(f"📁 فایل لاگ: {log_file}")
    return logging.getLogger(__name__)


logger = setup_logging()


# ============================================================
# دیالوگ کوچک لایسنس
# ============================================================

class LicenseDialog(QDialog):
    """دیالوگ ساده و کوچک برای فعال‌سازی لایسنس"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 فعال‌سازی لایسنس")
        self.setModal(True)
        self.setFixedSize(450, 300)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        # دریافت HWID
        self.hwid = get_system_hwid()
        
        self.setup_ui()
        self.center_on_screen()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # عنوان
        title = QLabel("🔐 ImanAccount")
        title.setStyleSheet("""
            font-size: 18pt; 
            font-weight: bold; 
            color: #e94560;
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # توضیحات
        desc = QLabel("لطفاً کلید لایسنس خود را وارد کنید یا از نسخه آزمایشی استفاده کنید.")
        desc.setStyleSheet("color: #aaa; font-size: 10pt;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # HWID
        hwid_layout = QHBoxLayout()
        hwid_label = QLabel("🖥️ HWID:")
        hwid_label.setStyleSheet("color: #888; font-size: 9pt;")
        hwid_layout.addWidget(hwid_label)
        
        self.hwid_display = QLineEdit(self.hwid)
        self.hwid_display.setReadOnly(True)
        self.hwid_display.setStyleSheet("""
            QLineEdit {
                background: #16213e;
                color: #4CAF50;
                border: 1px solid #0f3460;
                border-radius: 4px;
                padding: 4px 8px;
                font-family: monospace;
                font-size: 9pt;
            }
        """)
        hwid_layout.addWidget(self.hwid_display)
        
        copy_btn = QPushButton("📋")
        copy_btn.setFixedWidth(30)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        copy_btn.clicked.connect(self.copy_hwid)
        hwid_layout.addWidget(copy_btn)
        
        layout.addLayout(hwid_layout)
        
        layout.addSpacing(5)
        
        # ورودی لایسنس
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("کد لایسنس را وارد کنید...")
        self.license_input.setStyleSheet("""
            QLineEdit {
                background: #16213e;
                color: #eee;
                border: 2px solid #0f3460;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 10pt;
                font-family: monospace;
            }
            QLineEdit:focus {
                border-color: #e94560;
            }
        """)
        self.license_input.returnPressed.connect(self.verify_license)
        layout.addWidget(self.license_input)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        verify_btn = QPushButton("✅ تأیید لایسنس")
        verify_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover { background: #388E3C; }
        """)
        verify_btn.clicked.connect(self.verify_license)
        btn_layout.addWidget(verify_btn)
        
        trial_btn = QPushButton("🧪 نسخه آزمایشی")
        trial_btn.setStyleSheet("""
            QPushButton {
                background: #FF9800;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover { background: #E68900; }
        """)
        trial_btn.clicked.connect(self.start_trial)
        btn_layout.addWidget(trial_btn)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("❌ خروج")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # وضعیت
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #FF9800; font-size: 9pt;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
    
    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def copy_hwid(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hwid)
        self.status_label.setText("✅ HWID کپی شد!")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))
    
    def verify_license(self):
        key = self.license_input.text().strip()
        if not key:
            self.status_label.setText("❌ لطفاً کد لایسنس را وارد کنید!")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
            return
        
        core = get_license_core()
        result = core.verify_license(key)
        
        if result.get('valid'):
            # ذخیره لایسنس
            with open("license.key", 'w', encoding='utf-8') as f:
                f.write(key)
            
            self.status_label.setText("✅ لایسنس معتبر است!")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")
            
            # ذخیره اطلاعات در متغیر سراسری
            self.license_data = result.get('data', {})
            self.license_data['days_left'] = result.get('days_left', 0)
            self.license_data['is_trial'] = False
            
            QTimer.singleShot(500, self.accept)
        else:
            error_msg = result.get('message', 'لایسنس نامعتبر است!')
            self.status_label.setText(f"❌ {error_msg}")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
    
    def start_trial(self):
        # بررسی اینکه آیا قبلاً آزمایشی استفاده شده
        if os.path.exists("trial_used.dat"):
            self.status_label.setText("❌ نسخه آزمایشی قبلاً استفاده شده است!")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")
            return
        
        core = get_license_core()
        result = core.create_trial_license()
        
        if result.get('valid'):
            # علامت‌گذاری استفاده از آزمایشی
            with open("trial_used.dat", 'w', encoding='utf-8') as f:
                f.write(f"used_{datetime.now().isoformat()}")
            
            self.license_data = result.get('data', {})
            self.license_data['days_left'] = 30
            self.license_data['is_trial'] = True
            
            self.status_label.setText("✅ نسخه آزمایشی ۳۰ روزه فعال شد!")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")
            
            QTimer.singleShot(500, self.accept)
        else:
            error_msg = result.get('message', 'خطا در فعال‌سازی آزمایشی')
            self.status_label.setText(f"❌ {error_msg}")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 9pt;")


# ============================================================
# کلاس MainApplication
# ============================================================

class MainApplication:
    def __init__(self):
        self.app = None
        self.window = None
        self.license_info = None
        self.license_core = get_license_core()
        self._license_verified = False
    
    def run(self):
        try:
            logger.info("🔄 راه‌اندازی QApplication...")
            self.app = QApplication(sys.argv)
            self.app.setApplicationName(f"{APP_NAME} - نسخه {APP_VERSION}")
            
            self.app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            self.app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
            
            # ========== بررسی لایسنس ==========
            logger.info("🔐 بررسی لایسنس...")
            if not self.handle_license():
                logger.warning("❌ لایسنس تأیید نشد، برنامه بسته می‌شود")
                return
            
            # ========== راه‌اندازی دیتابیس ==========
            logger.info("📂 راه‌اندازی دیتابیس...")
            if not self.init_database():
                logger.error("❌ خطا در راه‌اندازی دیتابیس")
                return
            
            # ========== بارگذاری پنجره اصلی ==========
            logger.info("🖥️ بارگذاری پنجره اصلی...")
            self.load_main_window()
            
            if self.window:
                self.window.show()
                self.window.raise_()
                logger.info("✅ برنامه با موفقیت اجرا شد")
            else:
                logger.error("❌ پنجره اصلی ساخته نشد")
                return
            
            sys.exit(self.app.exec_())
            
        except Exception as e:
            logger.critical(f"❌ خطای بحرانی: {e}")
            logger.critical(traceback.format_exc())
            QMessageBox.critical(None, "خطای بحرانی", 
                f"یک خطای غیرمنتظره رخ داد:\n\n{str(e)}\n\n"
                f"جزئیات کامل در فایل لاگ ذخیره شده است.")
            sys.exit(1)
    
    # ============================================================
    # مدیریت لایسنس
    # ============================================================
    
    def handle_license(self) -> bool:
        try:
            logger.info("=" * 60)
            logger.info(f"🔐 بررسی لایسنس {APP_NAME}")
            logger.info("=" * 60)
            
            hwid = get_system_hwid()
            logger.info(f"🖥️ HWID: {hwid[:20]}...")
            
            # ===== بررسی فایل لایسنس موجود =====
            license_file = Path("license.key")
            if license_file.exists():
                try:
                    with open(license_file, 'r', encoding='utf-8') as f:
                        license_key = f.read().strip()
                    
                    result = self.license_core.verify_license(license_key)
                    if result.get('valid'):
                        logger.info("✅ لایسنس موجود معتبر است")
                        self.license_info = result.get('data', {})
                        self.license_info['days_left'] = result.get('days_left', 0)
                        self.license_info['is_trial'] = False
                        self._license_verified = True
                        self.show_license_info()
                        return True
                    else:
                        logger.warning(f"❌ لایسنس موجود نامعتبر است: {result.get('message', '')}")
                        license_file.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"خطا در خواندن لایسنس: {e}")
            
            # ===== نمایش دیالوگ لایسنس =====
            logger.info("ℹ️ نمایش دیالوگ لایسنس...")
            dialog = LicenseDialog()
            
            if dialog.exec_() != QDialog.Accepted:
                logger.info("❌ کاربر از فعال‌سازی لایسنس انصراف داد")
                return False
            
            # دریافت اطلاعات از دیالوگ
            self.license_info = dialog.license_data
            self._license_verified = True
            self.show_license_info()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در handle_license: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def show_license_info(self):
        try:
            info = self.license_info
            logger.info("📋 اطلاعات لایسنس:")
            logger.info(f"   👤 مشتری: {info.get('customer', 'نامشخص')}")
            logger.info(f"   📦 ماژول‌ها: {', '.join(info.get('modules', []))}")
            logger.info(f"   📅 انقضا: {info.get('expire_date', 'نامحدود')[:10] if info.get('expire_date') else 'نامحدود'}")
            logger.info(f"   ⏰ روزهای باقیمانده: {info.get('days_left', 0)}")
            logger.info(f"   🧪 آزمایشی: {'✅' if info.get('is_trial') else '❌'}")
            logger.info("=" * 60)
        except Exception as e:
            logger.warning(f"خطا در نمایش اطلاعات لایسنس: {e}")
    
    # ============================================================
    # مدیریت دیتابیس
    # ============================================================
    
    def init_database(self) -> bool:
        try:
            logger.info("🔄 مقداردهی اولیه دیتابیس...")
            DatabaseManager.init_db()
            logger.info("✅ دیتابیس با موفقیت راه‌اندازی شد")
            return True
        except Exception as e:
            logger.error(f"❌ خطا در دیتابیس: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(None, "خطا", 
                f"خطا در دیتابیس:\n\n{str(e)}\n\n"
                f"مشاهده جزئیات در فایل لاگ")
            return False
    
    # ============================================================
    # بارگذاری پنجره اصلی
    # ============================================================
    
    def load_main_window(self):
        try:
            logger.info("🔄 بارگذاری پنجره اصلی...")
            from ui.main_window import MainWindow
            
            self.window = MainWindow(self.license_info)
            logger.info("✅ پنجره اصلی ساخته شد")
            
            icon_paths = [Path("Icon.ico"), Path("icon.ico")]
            for path in icon_paths:
                if path.exists():
                    try:
                        self.window.setWindowIcon(QIcon(str(path)))
                        logger.info(f"🖼️ آیکون از {path} بارگذاری شد")
                        break
                    except Exception as e:
                        logger.warning(f"خطا در بارگذاری آیکون: {e}")
            
        except ImportError as e:
            logger.error(f"❌ خطا در import: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(None, "خطا", 
                f"خطا در بارگذاری ماژول:\n\n{str(e)}\n\n"
                f"مطمئن شوید تمام فایل‌های پروژه در مسیر صحیح قرار دارند.")
            sys.exit(1)
            
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری پنجره اصلی: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(None, "خطا", 
                f"خطا در راه‌اندازی پنجره اصلی:\n\n{str(e)}\n\n"
                f"مشاهده جزئیات در فایل لاگ")
            sys.exit(1)


# ============================================================
# نقطه ورود برنامه
# ============================================================

if __name__ == "__main__":
    def exception_hook(exctype, value, tb):
        error_msg = f"❌ خطای غیرمنتظره:\n{''.join(traceback.format_exception(exctype, value, tb))}"
        logger.critical(error_msg)
        QMessageBox.critical(None, "خطای غیرمنتظره", 
            f"{value}\n\n"
            f"جزئیات کامل در فایل لاگ ذخیره شده است.")
    
    sys.excepthook = exception_hook
    
    logger.info("🚀 شروع برنامه...")
    app = MainApplication()
    
    try:
        app.run()
    except Exception as e:
        logger.critical(f"❌ خطای بحرانی در حلقه اصلی: {e}")
        logger.critical(traceback.format_exc())
        QMessageBox.critical(None, "خطای بحرانی", 
            f"یک خطای غیرمنتظره رخ داد:\n\n{str(e)}\n\n"
            f"جزئیات کامل در فایل لاگ ذخیره شده است.")
        sys.exit(1)
