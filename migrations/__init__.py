# migrations/__init__.py
# ============================================================
# ثبت خودکار همه Migration ها
# ============================================================
# این فایل فقط import می‌کند — خود فایل‌های Migration در
# زمان import، تابع register_migrations() خودشون رو صدا می‌زنند.
# ============================================================

import logging

logger = logging.getLogger(__name__)


def register_all_migrations():
    """
    import همه ماژول‌های Migration.
    
    هر ماژول در زمان import، خودش Migration هاش رو 
    در MigrationRegistry ثبت می‌کند.
    """
    modules = [
        'migrations.base',        # جداول هسته (companies, settings, users, accounts, vouchers)
        'migrations.parties',     # اشخاص
        'migrations.inventory',   # انبار + انبارگردانی
        'migrations.documents',   # اسناد + برگشتی
        'migrations.finance',     # امور مالی (بانک، صندوق، چک)
        'migrations.payroll',     # حقوق و دستمزد
        'migrations.moadian',     # مودیان
    ]
    
    loaded = []
    failed = []
    
    for module_name in modules:
        try:
            __import__(module_name)
            loaded.append(module_name)
            logger.debug(f"✅ Migration module loaded: {module_name}")
        except ImportError as e:
            failed.append((module_name, str(e)))
            logger.warning(f"⚠️ Migration module not found: {module_name}")
        except Exception as e:
            failed.append((module_name, str(e)))
            logger.error(f"❌ خطا در بارگذاری {module_name}: {e}", exc_info=True)
    
    logger.info(f"📋 {len(loaded)} ماژول Migration بارگذاری شد")
    if failed:
        logger.warning(f"⚠️ {len(failed)} ماژول بارگذاری نشد")
    
    return loaded, failed


__all__ = ['register_all_migrations']
