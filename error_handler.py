# error_handler.py
# ============================================================
# سیستم مدیریت خطای جامع ImanAccount
# نسخه 3.0 (Integration با logging_config)
# ============================================================
# تغییرات v3.0:
# ✅ استفاده از logging_config به جای setup_logging داخلی
# ✅ حذف تداخل با builtins.PermissionError
# ✅ بهبود row_to_dict (single source of truth)
# ✅ حفظ backward compatibility
# ============================================================

import logging
import traceback
import hashlib
from datetime import datetime
from typing import Optional, Callable, Any

from PyQt5.QtWidgets import QMessageBox, QApplication, QWidget


# ============================================================
# 1. اتصال به logging_config (اختیاری)
# ============================================================

def get_logger() -> logging.Logger:
    """
    دریافت logger اصلی
    
    ✅ از logging_config.py استفاده می‌کنه اگه موجود باشه
    """
    try:
        # تلاش برای اتصال به logging_config
        from logging_config import LOG_FILE, ERROR_LOG_FILE
        # logging_config قبلاً root logger رو setup کرده
        return logging.getLogger('ImanAccount')
    except ImportError:
        # Fallback: لاگ ساده
        logger = logging.getLogger('ImanAccount')
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                '%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger


# ✅ Backward compatibility
def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Setup logging (backward compatible)
    
    ⚠️ اگه logging_config موجود باشه، از اون استفاده می‌کنه
    """
    try:
        from logging_config import setup_logging as _setup
        level_map = {
            "DEBUG": logging.DEBUG, "INFO": logging.INFO,
            "WARNING": logging.WARNING, "ERROR": logging.ERROR,
        }
        _setup(level=level_map.get(log_level.upper(), logging.INFO))
    except ImportError:
        pass
    
    return get_logger()


# ============================================================
# 2. کلاس‌های خطای سفارشی
# ============================================================
# ⚠️ از import اشتباه با builtins اجتناب کن
# ============================================================

class ImanAccountError(Exception):
    """خطای پایه ImanAccount"""
    def __init__(self, message: str, user_message: str = None, code: str = None):
        super().__init__(message)
        self.user_message = user_message or message
        self.code = code or self._generate_code(message)
    
    @staticmethod
    def _generate_code(message: str) -> str:
        h = hashlib.md5(message.encode()).hexdigest()[:8].upper()
        return f"E-{h}"


class DatabaseError(ImanAccountError):
    """خطای دیتابیس"""
    def __init__(self, message: str, user_message: str = None):
        super().__init__(
            message,
            user_message or "خطا در دسترسی به دیتابیس.",
        )


class LicenseError(ImanAccountError):
    """خطای لایسنس"""
    def __init__(self, message: str, user_message: str = None):
        super().__init__(
            message,
            user_message or "خطا در لایسنس نرم‌افزار.",
        )


class ValidationError(ImanAccountError):
    """خطای اعتبارسنجی"""
    pass


class ImanPermissionError(ImanAccountError):
    """
    ✅ خطای دسترسی
    
    ⚠️ اسمش عوض شد تا با builtins.PermissionError تداخل نکنه
    """
    def __init__(self, message: str = "دسترسی کافی ندارید"):
        super().__init__(
            message,
            "🔒 شما دسترسی لازم برای این عملیات را ندارید.",
        )


class ImportError_(ImanAccountError):
    """خطای import — با علامت _ تا با builtins تداخل نکنه"""
    pass


class ConfigurationError(ImanAccountError):
    """خطای تنظیمات"""
    pass


# ============================================================
# 3. ErrorHandler
# ============================================================

class ErrorHandler:
    """مدیریت مرکزی خطاها — Singleton"""
    
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
        
        # ✅ الگوهای خطا → پیام کاربر پسند
        self.ERROR_PATTERNS = [
            ("database is locked", "⏳ دیتابیس مشغول است. چند لحظه صبر کنید."),
            ("database locked", "⏳ دیتابیس مشغول است. چند لحظه صبر کنید."),
            ("no such table", "❌ خطای ساختاری دیتابیس. لطفاً با پشتیبانی تماس بگیرید."),
            ("UNIQUE constraint failed", "⚠️ این اطلاعات قبلاً ثبت شده است."),
            ("unique constraint", "⚠️ این اطلاعات قبلاً ثبت شده است."),
            ("FOREIGN KEY constraint failed", "⚠️ امکان حذف وجود ندارد (اطلاعات مرتبط موجود است)."),
            ("foreign key", "⚠️ امکان حذف وجود ندارد (اطلاعات مرتبط موجود است)."),
            ("NOT NULL constraint failed", "⚠️ برخی فیلدهای الزامی خالی هستند."),
            ("disk I/O error", "❌ خطا در خواندن دیتابیس. فضای دیسک را بررسی کنید."),
            ("Access is denied", "🔒 دسترسی کافی ندارید."),
            ("Permission denied", "🔒 دسترسی کافی ندارید."),
            ("FileNotFoundError", "❌ فایل مورد نظر یافت نشد."),
            ("No such file", "❌ فایل مورد نظر یافت نشد."),
            ("ConnectionError", "🌐 اتصال برقرار نیست."),
            ("TimeoutError", "⏳ زمان انتظار به پایان رسید."),
            ("MemoryError", "💾 حافظه کافی نیست."),
            ("JSONDecodeError", "❌ خطا در خواندن داده‌ها."),
            ("timeout", "⏳ زمان انتظار به پایان رسید."),
        ]
        
        self.logger.debug("✅ ErrorHandler مقداردهی شد")
    
    # ============================================================
    # Observers
    # ============================================================
    
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
    
    # ============================================================
    # پیام کاربرپسند
    # ============================================================
    
    def get_user_message(self, error: Exception) -> str:
        """تبدیل خطا به پیام کاربرپسند"""
        # اگه خطای سفارشی ماست
        if isinstance(error, ImanAccountError):
            return error.user_message
        
        error_str = str(error)
        
        # بررسی الگوها
        for pattern, message in self.ERROR_PATTERNS:
            if pattern.lower() in error_str.lower():
                return message
        
        # پیش‌فرض
        return f"⚠️ خطای غیرمنتظره رخ داد.\n\n{error_str[:200]}"
    
    def get_error_code(self, error: Exception) -> str:
        """کد خطا"""
        if isinstance(error, ImanAccountError) and error.code:
            return error.code
        
        h = hashlib.md5(
            f"{type(error).__name__}:{str(error)}".encode()
        ).hexdigest()[:8].upper()
        return f"E-{h}"
    
    # ============================================================
    # نمایش خطاها
    # ============================================================
    
    def show_error(
        self,
        parent: Optional[QWidget],
        title: str,
        message: str,
        details: Optional[str] = None,
        show_dialog: bool = True,
    ) -> str:
        """نمایش خطا"""
        self._error_count += 1
        
        # لاگ
        log_msg = f"{title}: {message}"
        if details:
            log_msg += f"\n{details}"
        self.logger.error(log_msg)
        
        # Notify
        self._notify_observers("error", title, message)
        
        # نمایش
        if show_dialog and parent:
            try:
                msg = QMessageBox(parent)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle(f"❌ {title}")
                msg.setText(message)
                
                if details:
                    msg.setDetailedText(details[:2000])
                
                # دکمه کپی
                copy_btn = msg.addButton(
                    "📋 کپی اطلاعات",
                    QMessageBox.ActionRole,
                )
                
                msg.exec_()
                
                if msg.clickedButton() == copy_btn:
                    self._copy_error_info(message, details)
            except Exception as e:
                self.logger.warning(f"خطا در نمایش دیالوگ: {e}")
        
        # کد خطا
        return self.get_error_code(Exception(message))
    
    def show_warning(
        self,
        parent: Optional[QWidget],
        title: str,
        message: str,
        show_dialog: bool = True,
    ) -> None:
        """نمایش هشدار"""
        self._warning_count += 1
        self.logger.warning(f"{title}: {message}")
        self._notify_observers("warning", title, message)
        
        if show_dialog and parent:
            try:
                QMessageBox.warning(parent, f"⚠️ {title}", message)
            except Exception as e:
                self.logger.warning(f"خطا در نمایش هشدار: {e}")
    
    def show_info(
        self,
        parent: Optional[QWidget],
        title: str,
        message: str,
        show_dialog: bool = True,
    ) -> None:
        """نمایش اطلاعات"""
        self._info_count += 1
        self.logger.info(f"{title}: {message}")
        self._notify_observers("info", title, message)
        
        if show_dialog and parent:
            try:
                QMessageBox.information(parent, f"ℹ️ {title}", message)
            except Exception as e:
                self.logger.warning(f"خطا در نمایش اطلاعات: {e}")
    
    # ============================================================
    # Handlerهای خاص
    # ============================================================
    
    def handle_database_error(
        self, parent: Optional[QWidget], error: Exception, operation: str = ""
    ) -> None:
        """خطای دیتابیس"""
        error_msg = str(error).lower()
        details = f"عملیات: {operation}\nخطا: {str(error)}\n{traceback.format_exc()}"
        
        # پیام کاربرپسند
        user_msg = self.get_user_message(error)
        
        title = "خطای دیتابیس"
        if "no such table" in error_msg:
            title = "خطای ساختار دیتابیس"
        elif "unique constraint" in error_msg:
            title = "تکرار اطلاعات"
        elif "foreign key" in error_msg:
            title = "خطای ارتباط دیتابیس"
        
        self.show_error(parent, title, user_msg, details)
    
    def handle_ui_error(
        self, parent: Optional[QWidget], error: Exception,
        widget_name: str = "", operation: str = "",
    ) -> None:
        """خطای رابط کاربری"""
        self.logger.error(f"UI Error in {widget_name}: {error}")
        self.logger.debug(traceback.format_exc())
        
        details = f"ویجت: {widget_name}\nعملیات: {operation}\n{traceback.format_exc()}"
        self.show_error(
            parent, "خطای رابط کاربری",
            f"خطا در {widget_name or 'بارگذاری صفحه'}",
            details,
        )
    
    def handle_import_error(
        self, parent: Optional[QWidget], error: Exception, module_name: str
    ) -> None:
        """خطای import"""
        self.logger.error(f"Import Error: {module_name} - {error}")
        self.logger.debug(traceback.format_exc())
        
        details = f"ماژول: {module_name}\nخطا: {str(error)}\n{traceback.format_exc()}"
        self.show_error(
            parent, "خطای بارگذاری ماژول",
            f"ماژول '{module_name}' یافت نشد!",
            details,
        )
    
    def handle_license_error(
        self, parent: Optional[QWidget], error: Exception
    ) -> None:
        """خطای لایسنس"""
        self.logger.error(f"License Error: {error}")
        self.logger.debug(traceback.format_exc())
        
        error_msg = str(error).lower()
        details = f"خطا: {str(error)}\n{traceback.format_exc()}"
        
        if "expired" in error_msg or "منقضی" in error_msg:
            self.show_error(
                parent, "لایسنس منقضی شده",
                "لایسنس نرم‌افزار منقضی شده است!",
                f"{details}\n\nراه‌حل: لایسنس جدید دریافت کنید.",
            )
        elif "invalid" in error_msg or "نامعتبر" in error_msg:
            self.show_error(
                parent, "لایسنس نامعتبر",
                "کد لایسنس نامعتبر است!",
                f"{details}\n\nراه‌حل: کد صحیح را وارد کنید.",
            )
        else:
            self.show_error(
                parent, "خطای لایسنس",
                "مشکل در تأیید لایسنس!",
                details,
            )
    
    def handle(
        self, error: Exception, parent: Optional[QWidget] = None,
        context: str = None, show_dialog: bool = True, silent: bool = False,
    ) -> str:
        """
        مدیریت خودکار خطا
        
        تشخیص نوع خطا و نمایش مناسب
        """
        error_code = self.get_error_code(error)
        user_message = self.get_user_message(error)
        
        # لاگ
        ctx = f" [{context}]" if context else ""
        self.logger.error(
            f"[{error_code}]{ctx} {type(error).__name__}: {error}",
            exc_info=True,
        )
        
        # نمایش
        if show_dialog and not silent:
            try:
                msg_box = QMessageBox(parent)
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowTitle("خطا")
                msg_box.setText(user_message)
                msg_box.setInformativeText(
                    f"کد خطا: {error_code}\n\n"
                    f"لطفاً این کد را به پشتیبانی اطلاع دهید."
                )
                
                copy_btn = msg_box.addButton(
                    "📋 کپی اطلاعات خطا",
                    QMessageBox.ActionRole,
                )
                
                msg_box.exec_()
                
                if msg_box.clickedButton() == copy_btn:
                    self._copy_full_error(error, error_code, context)
            except Exception as e:
                self.logger.error(f"خطا در نمایش: {e}")
        
        return error_code
    
    # ============================================================
    # Copy
    # ============================================================
    
    def _copy_error_info(self, message: str, details: str = None):
        """کپی اطلاعات خطا"""
        try:
            if QApplication.instance():
                info = f"📝 پیام: {message}\n"
                if details:
                    info += f"\n📋 جزئیات:\n{details}"
                
                QApplication.clipboard().setText(info)
                QMessageBox.information(
                    None, "کپی شد",
                    "✅ اطلاعات در کلیپ‌بورد کپی شد."
                )
        except Exception:
            pass
    
    def _copy_full_error(
        self, error: Exception, error_code: str, context: str = None
    ):
        """کپی اطلاعات کامل خطا"""
        try:
            if not QApplication.instance():
                return
            
            tb = traceback.format_exc()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            info = f"""
═══════════════════════════════════════════════
            اطلاعات خطا - ImanAccount
═══════════════════════════════════════════════
⏰ زمان: {timestamp}
🔑 کد خطا: {error_code}
📁 Context: {context or 'N/A'}
🚨 نوع خطا: {type(error).__name__}
📝 پیام: {error}

═══════════════════════════════════════════════
                Stack Trace
═══════════════════════════════════════════════
{tb}
═══════════════════════════════════════════════
            لطفاً این اطلاعات را برای پشتیبانی ارسال کنید.
═══════════════════════════════════════════════
"""
            
            QApplication.clipboard().setText(info)
            QMessageBox.information(
                None, "کپی شد",
                "✅ اطلاعات خطا در کلیپ‌بورد کپی شد."
            )
        except Exception as e:
            self.logger.error(f"خطا در کپی: {e}")
    
    # ============================================================
    # Decorator
    # ============================================================
    
    @staticmethod
    def safe_execute(func: Callable) -> Callable:
        """Decorator برای مدیریت خودکار خطا"""
        def wrapper(*args, **kwargs):
            handler = ErrorHandler()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # پیدا کردن parent
                parent = None
                for arg in args:
                    if hasattr(arg, 'window'):
                        try:
                            parent = arg.window()
                            break
                        except Exception:
                            pass
                    elif isinstance(arg, QWidget):
                        parent = arg
                        break
                
                handler.handle(e, parent=parent, context=func.__name__)
                return None
        wrapper.__name__ = func.__name__
        return wrapper
    
    # ============================================================
    # Stats
    # ============================================================
    
    def get_stats(self) -> dict:
        return {
            'errors': self._error_count,
            'warnings': self._warning_count,
            'info': self._info_count,
            'total': self._error_count + self._warning_count + self._info_count,
        }
    
    def reset_stats(self) -> None:
        self._error_count = 0
        self._warning_count = 0
        self._info_count = 0
        self.logger.info("آمار خطاها بازنشانی شد")


# ============================================================
# 4. Global Exception Hook
# ============================================================

def global_exception_hook(exc_type, exc_value, exc_traceback):
    """Hook برای exceptionهای نگرفته"""
    logger = get_logger()
    
    # KeyboardInterrupt → خروج عادی
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical("❌ خطای غیرمنتظره:")
    logger.critical(
        ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    )
    
    # ✅ تلاش برای backup اضطراری
    try:
        from migrations import create_manual_backup
        backup = create_manual_backup()
        if backup:
            logger.info(f"✅ بکاپ اضطراری: {backup}")
    except Exception as e:
        logger.error(f"❌ خطا در بکاپ اضطراری: {e}")
    
    # نمایش
    try:
        if QApplication.instance():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("❌ خطای بحرانی")
            msg.setText("یک خطای غیرمنتظره رخ داد!")
            msg.setDetailedText(
                f"{exc_type.__name__}: {exc_value}\n\n"
                + ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            )
            msg.exec_()
    except Exception:
        pass
    
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


# ============================================================
# 5. توابع کمکی
# ============================================================

def validate_not_empty(value: Any, field_name: str) -> bool:
    """اعتبارسنجی خالی نبودن"""
    if value is None:
        raise ValidationError(f"{field_name} نمی‌تواند خالی باشد!")
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{field_name} نمی‌تواند خالی باشد!")
    if isinstance(value, (list, tuple, dict)) and not value:
        raise ValidationError(f"{field_name} نمی‌تواند خالی باشد!")
    return True


def validate_positive_number(value: Any, field_name: str) -> bool:
    """اعتبارسنجی عدد مثبت"""
    try:
        if isinstance(value, str):
            value = value.replace(',', '').strip()
        num = float(value)
        if num <= 0:
            raise ValidationError(f"{field_name} باید بزرگتر از صفر باشد!")
        return True
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} باید عدد معتبر باشد!")


def validate_date_format(date_str: str, field_name: str) -> bool:
    """اعتبارسنجی فرمت تاریخ"""
    if not date_str:
        raise ValidationError(f"{field_name} نمی‌تواند خالی باشد!")
    
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]
    for fmt in formats:
        try:
            datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            continue
    
    raise ValidationError(f"فرمت {field_name} نامعتبر است!")


def row_to_dict(row) -> dict:
    """
    تبدیل sqlite3.Row به dict
    
    ✅ Single source of truth برای همه پروژه
    """
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
        get_logger().warning(f"خطا در تبدیل row به dict: {e}")
        return {}


def show_validation_errors(parent: QWidget, errors: list) -> None:
    """نمایش خطاهای اعتبارسنجی"""
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
    """اجرای ایمن یک تابع"""
    handler = ErrorHandler()
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = get_logger()
        logger.error(f"خطا در safe_call {func.__name__}: {e}")
        logger.debug(traceback.format_exc())
        
        parent = None
        for arg in args:
            if isinstance(arg, QWidget):
                parent = arg
                break
        
        handler.show_error(
            parent, "خطا",
            f"خطا در {func.__name__}",
            traceback.format_exc(),
        )
        return None


# ============================================================
# 6. Singleton + Exports
# ============================================================

_error_handler = None


def get_error_handler() -> ErrorHandler:
    """دریافت ErrorHandler"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


# ✅ Alias برای backward compatibility
safe_execute = ErrorHandler.safe_execute

PermissionError = ImanPermissionError  # اسم قدیمی احتمالی
PermissionDeniedError = ImanPermissionError  # اسم جایگزین
__all__ = [
    'get_logger', 'setup_logging',
    'ErrorHandler', 'get_error_handler',
    'global_exception_hook',
    # Exception classes
    'ImanAccountError', 'DatabaseError', 'LicenseError',
    'ValidationError', 
    'ImanPermissionError',       # ✅ جدید
    'PermissionError_',          # ✅ alias برای قدیمی
    'PermissionDeniedError',     # ✅ alias دوم
    'ImportError_', 
    'ConfigurationError',
    # Functions
    'validate_not_empty', 'validate_positive_number', 'validate_date_format',
    'row_to_dict', 'show_validation_errors',
    'safe_call', 'safe_execute',
]
