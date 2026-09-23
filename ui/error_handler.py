# utils/error_handler.py
# ============================================================
# سیستم مدیریت خطای جامع ImanAccount - نسخه نهایی
# ============================================================

import logging
import traceback
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Any

from PyQt5.QtWidgets import QMessageBox, QApplication, QWidget


# ============================================================
# 1. تنظیمات لاگینگ
# ============================================================

def setup_logging(log_level: str = "DEBUG") -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"imanaccount_{datetime.now().strftime('%Y%m%d')}.log"
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    level = level_map.get(log_level.upper(), logging.DEBUG)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger('ImanAccount')
    logger.info("=" * 60)
    logger.info(f"🚀 ImanAccount شروع به کار کرد - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📁 فایل لاگ: {log_file}")
    logger.info("=" * 60)
    
    return logger


_LOGGER: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = setup_logging()
    return _LOGGER


# ============================================================
# 2. کلاس مدیریت خطا
# ============================================================

class ErrorHandler:
    _instance: Optional['ErrorHandler'] = None
    
    def __new__(cls) -> 'ErrorHandler':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.logger = get_logger()
        self._error_count = 0
        self._warning_count = 0
        self._info_count = 0
        self._observers: list[Callable] = []
        self.logger.debug("✅ ErrorHandler مقداردهی شد")
    
    def add_observer(self, callback: Callable) -> None:
        if callback not in self._observers:
            self._observers.append(callback)
    
    def remove_observer(self, callback: Callable) -> None:
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self, event_type: str, title: str, message: str) -> None:
        for callback in self._observers:
            try:
                callback(event_type, title, message)
            except Exception as e:
                self.logger.warning(f"خطا در observer: {e}")
    
    def show_error(self, parent: Optional[QWidget], title: str, message: str, details: Optional[str] = None, show_dialog: bool = True) -> None:
        self._error_count += 1
        log_msg = f"{title}: {message}"
        if details:
            log_msg += f"\n{details}"
        self.logger.error(log_msg)
        self._notify_observers("error", title, message)
        
        if show_dialog and parent:
            try:
                msg = QMessageBox(parent)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("❌ " + title)
                msg.setText(message)
                if details:
                    msg.setDetailedText(details[:2000])
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
            except Exception as e:
                self.logger.warning(f"خطا در نمایش دیالوگ خطا: {e}")
    
    def show_warning(self, parent: Optional[QWidget], title: str, message: str, show_dialog: bool = True) -> None:
        self._warning_count += 1
        self.logger.warning(f"{title}: {message}")
        self._notify_observers("warning", title, message)
        if show_dialog and parent:
            try:
                QMessageBox.warning(parent, "⚠️ " + title, message)
            except Exception as e:
                self.logger.warning(f"خطا در نمایش دیالوگ هشدار: {e}")
    
    def show_info(self, parent: Optional[QWidget], title: str, message: str, show_dialog: bool = True) -> None:
        self._info_count += 1
        self.logger.info(f"{title}: {message}")
        self._notify_observers("info", title, message)
        if show_dialog and parent:
            try:
                QMessageBox.information(parent, "ℹ️ " + title, message)
            except Exception as e:
                self.logger.warning(f"خطا در نمایش دیالوگ اطلاعات: {e}")
    
    def handle_database_error(self, parent: Optional[QWidget], error: Exception, operation: str = "") -> None:
        error_msg = str(error).lower()
        details = f"عملیات: {operation}\nخطا: {str(error)}\n{traceback.format_exc()}"
        if "database is locked" in error_msg or "database locked" in error_msg:
            self.show_error(parent, "خطای قفل دیتابیس", "دیتابیس قفل شده است!", f"{details}\n\nراه‌حل: لطفاً برنامه را مجدداً اجرا کنید.")
        elif "no such table" in error_msg:
            self.show_error(parent, "خطای ساختار دیتابیس", "جدول مورد نظر وجود ندارد!", f"{details}\n\nراه‌حل: لطفاً با پشتیبانی تماس بگیرید.")
        elif "unique constraint" in error_msg or "UNIQUE constraint" in error_msg:
            self.show_warning(parent, "تکرار اطلاعات", f"این مقدار قبلاً ثبت شده است!\n{operation}")
        elif "foreign key" in error_msg or "FOREIGN KEY" in error_msg:
            self.show_error(parent, "خطای ارتباط دیتابیس", "این رکورد به رکوردهای دیگر متصل است!", f"{details}\n\nراه‌حل: ابتدا رکوردهای وابسته را حذف کنید.")
        elif "timeout" in error_msg:
            self.show_error(parent, "خطای زمان‌آوت دیتابیس", "عملیات دیتابیس زمان‌بر شد!", f"{details}\n\nراه‌حل: مجدداً تلاش کنید.")
        else:
            self.show_error(parent, "خطای دیتابیس", f"خطا در {operation or 'عملیات دیتابیس'}", details)
    
    def handle_ui_error(self, parent: Optional[QWidget], error: Exception, widget_name: str = "", operation: str = "") -> None:
        self.logger.error(f"UI Error in {widget_name}: {error}")
        self.logger.debug(traceback.format_exc())
        details = f"ویجت: {widget_name or 'نامشخص'}\nعملیات: {operation or 'نامشخص'}\n{traceback.format_exc()}"
        self.show_error(parent, "خطای رابط کاربری", f"خطا در {widget_name or 'بارگذاری صفحه'}", f"{details}\n\nراه‌حل: صفحه را مجدداً بارگذاری کنید.")
    
    def handle_import_error(self, parent: Optional[QWidget], error: ImportError, module_name: str) -> None:
        self.logger.error(f"Import Error: {module_name} - {error}")
        self.logger.debug(traceback.format_exc())
        details = f"ماژول: {module_name}\nخطا: {str(error)}\n{traceback.format_exc()}"
        self.show_error(parent, "خطای بارگذاری ماژول", f"ماژول '{module_name}' یافت نشد!", f"{details}\n\nراه‌حل: نرم‌افزار را مجدداً نصب کنید.")
    
    def handle_license_error(self, parent: Optional[QWidget], error: Exception) -> None:
        self.logger.error(f"License Error: {error}")
        self.logger.debug(traceback.format_exc())
        error_msg = str(error).lower()
        details = f"خطا: {str(error)}\n{traceback.format_exc()}"
        if "expired" in error_msg or "منقضی" in error_msg:
            self.show_error(parent, "لایسنس منقضی شده", "لایسنس نرم‌افزار منقضی شده است!", f"{details}\n\nراه‌حل: لایسنس جدید دریافت کنید.")
        elif "invalid" in error_msg or "نامعتبر" in error_msg:
            self.show_error(parent, "لایسنس نامعتبر", "کد لایسنس نامعتبر است!", f"{details}\n\nراه‌حل: کد لایسنس صحیح را وارد کنید.")
        else:
            self.show_error(parent, "خطای لایسنس", "مشکل در تأیید لایسنس!", details)
    
    # ============================================================
    # دکوریتور برای مدیریت خطا (اصلاح شده برای آرگومان‌ها)
    # ============================================================
    
    @staticmethod
    def safe_execute(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            handler = ErrorHandler()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                parent = None
                for arg in args:
                    if hasattr(arg, 'window'):
                        parent = arg.window()
                        break
                    elif hasattr(arg, 'parent'):
                        parent = arg.parent()
                        break
                    elif isinstance(arg, QWidget):
                        parent = arg
                        break
                
                if "database" in str(e).lower() or "sqlite" in str(e).lower():
                    handler.handle_database_error(parent, e, func.__name__)
                elif "import" in str(e).lower():
                    handler.handle_import_error(parent, e, func.__name__)
                elif "license" in str(e).lower() or "لایسنس" in str(e):
                    handler.handle_license_error(parent, e)
                else:
                    handler.show_error(parent, "خطای غیرمنتظره", f"خطا در {func.__name__}", f"{str(e)}\n\n{traceback.format_exc()}")
                return None
        return wrapper
    
    def get_stats(self) -> dict:
        return {
            'errors': self._error_count,
            'warnings': self._warning_count,
            'info': self._info_count,
            'total': self._error_count + self._warning_count + self._info_count
        }
    
    def reset_stats(self) -> None:
        self._error_count = 0
        self._warning_count = 0
        self._info_count = 0
        self.logger.info("آمار خطاها بازنشانی شد")


# ============================================================
# 3. مدیریت خطاهای سراسری
# ============================================================

def global_exception_hook(exc_type, exc_value, exc_traceback):
    logger = get_logger()
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("❌ خطای غیرمنتظره در سراسر برنامه:")
    logger.critical(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    try:
        if QApplication.instance():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("❌ خطای بحرانی")
            msg.setText("یک خطای غیرمنتظره رخ داد!\n\nبرنامه ممکن است ناپایدار شود.")
            msg.setDetailedText(f"{exc_type.__name__}: {exc_value}\n\n" + ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
    except Exception as e:
        logger.error(f"خطا در نمایش دیالوگ خطای بحرانی: {e}")
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


# ============================================================
# 4. کلاس خطاهای سفارشی
# ============================================================

class ImanAccountError(Exception):
    pass


class DatabaseError(ImanAccountError):
    pass


class LicenseError(ImanAccountError):
    pass


class ValidationError(ImanAccountError):
    pass


class PermissionError(ImanAccountError):
    pass


class ImportError(ImanAccountError):
    pass


class ConfigurationError(ImanAccountError):
    pass


# ============================================================
# 5. توابع کمکی
# ============================================================

def validate_not_empty(value: Any, field_name: str) -> bool:
    if value is None:
        raise ValidationError(f"{field_name} نمی‌تواند خالی باشد!")
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{field_name} نمی‌تواند خالی باشد!")
    if isinstance(value, (list, tuple, dict)) and not value:
        raise ValidationError(f"{field_name} نمی‌تواند خالی باشد!")
    return True


def validate_positive_number(value: Any, field_name: str) -> bool:
    try:
        if isinstance(value, str):
            value = value.replace(',', '').strip()
        num = float(value)
        if num <= 0:
            raise ValidationError(f"{field_name} باید بزرگتر از صفر باشد!")
        return True
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} باید یک عدد معتبر باشد!")


def validate_date_format(date_str: str, field_name: str) -> bool:
    if not date_str:
        raise ValidationError(f"{field_name} نمی‌تواند خالی باشد!")
    try:
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]
        for fmt in formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        raise ValidationError(f"فرمت {field_name} نامعتبر است!")
    except Exception as e:
        raise ValidationError(f"خطا در اعتبارسنجی {field_name}: {str(e)}")


def row_to_dict(row) -> dict:
    if row is None:
        return {}
    try:
        if isinstance(row, dict):
            return row
        if hasattr(row, 'keys'):
            return {key: row[key] for key in row.keys()}
        if isinstance(row, (tuple, list)):
            return {f"col_{i}": val for i, val in enumerate(row)}
        if hasattr(row, '__dict__'):
            return row.__dict__
        return {}
    except Exception as e:
        logger = get_logger()
        logger.warning(f"خطا در تبدیل row به dict: {e}")
        return {}


def show_validation_errors(parent: QWidget, errors: list) -> None:
    if not errors:
        return
    handler = ErrorHandler()
    if len(errors) == 1:
        handler.show_warning(parent, "خطای اعتبارسنجی", errors[0])
    else:
        message = "لطفاً موارد زیر را اصلاح کنید:\n\n"
        for i, error in enumerate(errors, 1):
            message += f"{i}. {error}\n"
        handler.show_warning(parent, "خطاهای اعتبارسنجی", message)


def safe_call(func: Callable, *args, **kwargs) -> Any:
    handler = ErrorHandler()
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = get_logger()
        logger.error(f"خطا در safe_call {func.__name__}: {e}")
        logger.debug(traceback.format_exc())
        parent = None
        for arg in args:
            if hasattr(arg, 'window'):
                parent = arg.window()
                break
            elif hasattr(arg, 'parent'):
                parent = arg.parent()
                break
            elif isinstance(arg, QWidget):
                parent = arg
                break
        handler.show_error(parent, "خطا", f"خطا در {func.__name__}", traceback.format_exc())
        return None


# ============================================================
# 6. مقداردهی اولیه
# ============================================================

_error_handler = None


def get_error_handler() -> ErrorHandler:
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


__all__ = [
    'get_logger', 'setup_logging', 'ErrorHandler', 'get_error_handler',
    'global_exception_hook', 'ImanAccountError', 'DatabaseError', 'LicenseError',
    'ValidationError', 'PermissionError', 'ImportError', 'ConfigurationError',
    'validate_not_empty', 'validate_positive_number', 'validate_date_format',
    'row_to_dict', 'show_validation_errors', 'safe_call', 'safe_execute'
]

safe_execute = ErrorHandler.safe_execute
