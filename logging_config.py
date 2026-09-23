# logging_config.py
# ============================================================
# راه‌اندازی سیستم Logging حرفه‌ای
# نسخه 1.0 (Production-Ready)
# ============================================================
# ویژگی‌ها:
# ✅ Rotating File Handler (جلوگیری از فایل‌های بزرگ)
# ✅ لاگ‌های جداگانه برای error و debug
# ✅ Console output در development
# ✅ Formatter با timestamp کامل
# ✅ Global exception hook
# ============================================================

import os
import sys
import logging
import traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


# ============================================================
# ========== ثابت‌ها ==========
# ============================================================

LOG_MAX_BYTES = 5 * 1024 * 1024   # 5 MB
LOG_BACKUP_COUNT = 10              # 10 فایل نگه‌داری

LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# مسیر لاگ
def _get_log_dir() -> Path:
    """مسیر پوشه لاگ"""
    if os.name == 'nt':
        appdata = os.environ.get('APPDATA')
        if appdata:
            base = Path(appdata) / 'ImanAccount' / 'logs'
        else:
            base = Path.home() / '.imanaccount' / 'logs'
    else:
        base = Path.home() / '.config' / 'imanaccount' / 'logs'
    
    base.mkdir(parents=True, exist_ok=True)
    return base


LOG_DIR = _get_log_dir()
LOG_FILE = LOG_DIR / 'imanaccount.log'
ERROR_LOG_FILE = LOG_DIR / 'errors.log'


# ============================================================
# ========== Formatter ==========
# ============================================================

class ColoredFormatter(logging.Formatter):
    """Formatter رنگی برای Console"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # اگه تو console رنگی نباشه، رنگی نکن
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return super().format(record)
        
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


# ============================================================
# ========== Setup ==========
# ============================================================

def setup_logging(
    level: int = logging.INFO,
    console: bool = True,
    colored: bool = True,
) -> Path:
    """
    راه‌اندازی سیستم logging
    
    Args:
        level: سطح لاگ (DEBUG/INFO/WARNING/ERROR)
        console: نمایش در console
        colored: لاگ رنگی در console
    
    Returns:
        Path: مسیر فایل لاگ اصلی
    """
    # ===== Root Logger =====
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    
    # حذف handlerهای قبلی
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # ===== 1. File Handler (همه لاگ‌ها) =====
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8',
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    root.addHandler(file_handler)
    
    # ===== 2. Error File Handler (فقط error و بالاتر) =====
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8',
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    root.addHandler(error_handler)
    
    # ===== 3. Console Handler =====
    if console:
        # بررسی اگه stdout در دسترسه
        if sys.stdout is not None:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            
            if colored:
                formatter = ColoredFormatter(
                    '%(levelname)-8s | %(message)s'
                )
            else:
                formatter = logging.Formatter(
                    '%(levelname)-8s | %(message)s'
                )
            
            console_handler.setFormatter(formatter)
            root.addHandler(console_handler)
    
    # ===== کاهش noise کتابخانه‌های ثالث =====
    logging.getLogger('passlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('reportlab').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return LOG_FILE


# ============================================================
# ========== Exception Hook ==========
# ============================================================

_original_excepthook = sys.excepthook
_exception_handler_func = None


def set_exception_handler(handler_func):
    """
    ثبت handler برای exceptionهای نگرفته
    
    Args:
        handler_func: تابع با امضای (exctype, value, tb)
    """
    global _exception_handler_func
    _exception_handler_func = handler_func


def exception_hook(exctype, value, tb):
    """Global exception hook"""
    # لاگ
    logger = logging.getLogger('CRASH')
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"❌ UNCAUGHT EXCEPTION:\n{error_msg}")
    
    # ✅ تلاش برای backup اضطراری
    try:
        from migrations import create_manual_backup
        backup = create_manual_backup()
        if backup:
            logger.info(f"✅ بکاپ اضطراری: {backup}")
    except Exception as e:
        logger.error(f"❌ خطا در بکاپ اضطراری: {e}")
    
    # ✅ اطلاع به handler
    if _exception_handler_func:
        try:
            _exception_handler_func(exctype, value, tb)
        except Exception:
            pass
    
    # ✅ Exception اصلی
    _original_excepthook(exctype, value, tb)


def install_exception_hook():
    """نصب global exception hook"""
    sys.excepthook = exception_hook
    return True


# ============================================================
# ========== Utility Functions ==========
# ============================================================

def get_log_file_path() -> Path:
    """مسیر فایل لاگ اصلی"""
    return LOG_FILE


def get_error_log_path() -> Path:
    """مسیر فایل error log"""
    return ERROR_LOG_FILE


def get_log_dir_path() -> Path:
    """مسیر پوشه لاگ"""
    return LOG_DIR


def read_recent_logs(lines: int = 100) -> str:
    """
    خواندن آخرین N خط از لاگ
    
    برای نمایش تو دیالوگ پشتیبانی
    """
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return ''.join(recent)
    except Exception as e:
        return f"خطا در خواندن لاگ: {e}"


def clear_old_logs(keep_days: int = 30):
    """
    حذف لاگ‌های قدیمی‌تر از N روز
    
    Args:
        keep_days: تعداد روز برای نگه‌داری
    """
    from datetime import timedelta
    
    try:
        cutoff = datetime.now() - timedelta(days=keep_days)
        removed = 0
        
        for log_file in LOG_DIR.glob("*.log.*"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    log_file.unlink()
                    removed += 1
            except Exception:
                pass
        
        if removed:
            logging.getLogger(__name__).info(
                f"🗑️ {removed} فایل لاگ قدیمی حذف شد"
            )
    except Exception as e:
        logging.getLogger(__name__).warning(f"⚠️ خطا: {e}")


# ============================================================
# ========== Diagnostic Report ==========
# ============================================================

def generate_diagnostic_report() -> str:
    """
    ساخت گزارش تشخیصی برای پشتیبانی
    
    Returns:
        Path: مسیر فایل zip حاوی گزارش
    """
    import zipfile
    import platform
    import json
    
    try:
        # پوشه خروجی
        output_dir = LOG_DIR.parent / 'diagnostic_reports'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_path = output_dir / f"diagnostic_{timestamp}.zip"
        
        # ===== اطلاعات سیستم =====
        info = {
            'generated_at': datetime.now().isoformat(),
            'os': f"{platform.system()} {platform.release()}",
            'python': platform.python_version(),
            'machine': platform.machine(),
            'hostname': platform.node(),
            'user': os.environ.get('USERNAME', ''),
        }
        
        # ===== نسخه برنامه =====
        try:
            from main2 import APP_VERSION, APP_NAME
            info['app_version'] = APP_VERSION
            info['app_name'] = APP_NAME
        except Exception:
            pass
        
        # ===== HWID =====
        try:
            from registry_guard import get_short_machine_id
            info['hwid'] = get_short_machine_id()
        except Exception:
            pass
        
        # ===== اطلاعات دیتابیس =====
        try:
            from database import DB_NAME
            import os
            info['db_path'] = DB_NAME
            info['db_size_mb'] = os.path.getsize(DB_NAME) / (1024 * 1024)
            info['db_exists'] = os.path.exists(DB_NAME)
        except Exception:
            pass
        
        # ===== لاگ‌ها =====
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # info.json
            zf.writestr(
                'system_info.json',
                json.dumps(info, indent=2, ensure_ascii=False)
            )
            
            # main log
            if LOG_FILE.exists():
                zf.write(LOG_FILE, 'imanaccount.log')
            
            # error log
            if ERROR_LOG_FILE.exists():
                zf.write(ERROR_LOG_FILE, 'errors.log')
            
            # backup logs
            for log_file in LOG_DIR.glob("*.log.*"):
                try:
                    zf.write(log_file, log_file.name)
                except Exception:
                    pass
        
        return str(zip_path)
    
    except Exception as e:
        logging.getLogger(__name__).error(f"❌ خطا در گزارش: {e}")
        raise


# ============================================================
# ========== تست ==========
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 تست Logging System")
    print("=" * 60)
    
    # Setup
    log_file = setup_logging(level=logging.INFO)
    print(f"\n📁 فایل لاگ: {log_file}")
    print(f"📁 پوشه لاگ: {get_log_dir_path()}\n")
    
    # تست لاگ‌ها
    logger = logging.getLogger('test')
    logger.debug("🟦 این یک debug است (نمی‌بینی در console)")
    logger.info("🟩 این یک info است")
    logger.warning("🟨 این یک warning است")
    logger.error("🟥 این یک error است")
    
    print(f"\n📊 لاگ اصلی: {get_log_file_path()}")
    print(f"📊 لاگ خطاها: {get_error_log_path()}")
    
    print("\n📖 آخرین ۵ خط لاگ:")
    print(read_recent_logs(5))
    
    # تست diagnostic
    print("\n📦 ساخت گزارش تشخیصی...")
    try:
        report = generate_diagnostic_report()
        print(f"✅ گزارش ساخته شد: {report}")
    except Exception as e:
        print(f"❌ خطا: {e}")
    
    print("\n" + "=" * 60)
    print("✅ تست کامل شد")
    print("=" * 60)
