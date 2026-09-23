# migrations.py
# ============================================================
# سیستم Migration نسخه‌بندی‌شده
# نسخه 1.0 (Production-Ready)
# ============================================================
# ویژگی‌ها:
# ✅ Backup خودکار قبل از هر migration
# ✅ Transaction-based (rollback خودکار)
# ✅ Version tracking با PRAGMA user_version
# ✅ بازگردانی خودکار در صورت خطا
# ✅ حذف backup‌های قدیمی
# ✅ Logger حرفه‌ای
# ============================================================

import os
import shutil
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Callable, List, Tuple, Optional

logger = logging.getLogger(__name__)


# ============================================================
# ========== ثابت‌ها ==========
# ============================================================

# نسخه فعلی schema
# هر وقت migration جدید اضافه کردی، این عدد رو ۱ زیاد کن
CURRENT_SCHEMA_VERSION = 2

# مسیر backup
BACKUP_DIR_NAME = "migration_backups"
BACKUP_KEEP_DAYS = 30  # نگهداری backup برای ۳۰ روز
BACKUP_KEEP_COUNT = 10  # حداکثر ۱۰ فایل backup


# ============================================================
# ========== Backup Manager ==========
# ============================================================

class BackupManager:
    """مدیریت backup فایل دیتابیس"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.backup_dir = self.db_path.parent / BACKUP_DIR_NAME
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    # ============================================================
    # ========== ساخت Backup ==========
    # ============================================================
    
    def create_backup(self, tag: str = "auto") -> Optional[str]:
        """
        ساخت backup از دیتابیس
        
        Args:
            tag: برچسب برای نام‌گذاری (auto, pre_migration, manual)
        
        Returns:
            str: مسیر فایل backup یا None در صورت خطا
        """
        if not self.db_path.exists():
            logger.warning(f"⚠️ دیتابیس وجود ندارد: {self.db_path}")
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{tag}_{timestamp}.db"
            backup_path = self.backup_dir / backup_name
            
            # ✅ Copy فایل
            shutil.copy2(self.db_path, backup_path)
            
            # ✅ بررسی integrity فایل backup
            if not self._verify_backup(backup_path):
                logger.error(f"❌ Backup خراب است: {backup_path}")
                backup_path.unlink()
                return None
            
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(
                f"✅ Backup ساخته شد: {backup_name} ({size_mb:.2f} MB)"
            )
            
            # ✅ پاک‌سازی backup‌های قدیمی
            self._cleanup_old_backups()
            
            return str(backup_path)
        
        except Exception as e:
            logger.error(f"❌ خطا در ساخت backup: {e}", exc_info=True)
            return None
    
    def _verify_backup(self, backup_path: Path) -> bool:
        """بررسی سلامت فایل backup"""
        try:
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            return result and result[0] == "ok"
        except Exception as e:
            logger.error(f"❌ خطا در بررسی backup: {e}")
            return False
    
    # ============================================================
    # ========== بازگردانی ==========
    # ============================================================
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        بازگردانی از backup
        
        Args:
            backup_path: مسیر فایل backup
        
        Returns:
            bool: موفقیت
        """
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error(f"❌ Backup پیدا نشد: {backup_path}")
            return False
        
        try:
            # ✅ حفظ نسخه فعلی به عنوان backup اضطراری
            if self.db_path.exists():
                emergency_path = self.backup_dir / (
                    f"emergency_{datetime.now():%Y%m%d_%H%M%S}.db"
                )
                shutil.copy2(self.db_path, emergency_path)
                logger.info(f"📦 نسخه فعلی حفظ شد: {emergency_path.name}")
            
            # ✅ بازگردانی
            shutil.copy2(backup_file, self.db_path)
            
            logger.info(f"✅ بازگردانی از {backup_file.name}")
            return True
        
        except Exception as e:
            logger.error(f"❌ خطا در بازگردانی: {e}", exc_info=True)
            return False
    
    # ============================================================
    # ========== پاک‌سازی ==========
    # ============================================================
    
    def _cleanup_old_backups(self):
        """حذف backup‌های قدیمی"""
        try:
            # همه backup‌ها
            backups = sorted(
                self.backup_dir.glob("*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # ✅ فیلتر بر اساس زمان
            cutoff = datetime.now() - timedelta(days=BACKUP_KEEP_DAYS)
            
            removed = 0
            for backup in backups[BACKUP_KEEP_COUNT:]:
                try:
                    mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                    if mtime < cutoff:
                        backup.unlink()
                        removed += 1
                except Exception:
                    pass
            
            if removed:
                logger.info(f"🗑️ {removed} backup قدیمی حذف شد")
        
        except Exception as e:
            logger.warning(f"⚠️ خطا در پاک‌سازی backup‌ها: {e}")
    
    def list_backups(self) -> List[dict]:
        """لیست همه backup‌ها"""
        backups = []
        for backup in sorted(
            self.backup_dir.glob("*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            stat = backup.stat()
            backups.append({
                'name': backup.name,
                'path': str(backup),
                'size_mb': stat.st_size / (1024 * 1024),
                'created_at': datetime.fromtimestamp(stat.st_mtime),
            })
        return backups


# ============================================================
# ========== Migration Runner ==========
# ============================================================

class MigrationRunner:
    """
    اجراکننده migration‌های نسخه‌بندی‌شده
    
    Usage:
        runner = MigrationRunner(DB_NAME)
        runner.register(1, "initial_setup", migrate_func_1)
        runner.register(2, "add_warehouse_stock", migrate_func_2)
        runner.run()
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backup_manager = BackupManager(db_path)
        self.migrations: List[Tuple[int, str, Callable]] = []
    
    def register(self, version: int, name: str, func: Callable):
        """
        ثبت یک migration
        
        Args:
            version: شماره نسخه (باید یکتا و صعودی باشه)
            name: نام migration
            func: تابع migration — امضای (cursor, conn) → None
        """
        self.migrations.append((version, name, func))
        # مرتب‌سازی بر اساس نسخه
        self.migrations.sort(key=lambda x: x[0])
    
    def get_current_version(self) -> int:
        """دریافت نسخه فعلی schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA user_version")
            version = cursor.fetchone()[0]
            conn.close()
            return version
        except Exception as e:
            logger.error(f"❌ خطا در خواندن نسخه: {e}")
            return 0
    
    def set_version(self, version: int):
        """ذخیره نسخه جدید"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA user_version = {version}")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره نسخه: {e}")
    
    # ============================================================
    # ========== اجرای Migration ==========
    # ============================================================
    
    def run(self) -> dict:
        """
        اجرای همه migration‌های لازم
        
        Returns:
            dict: {'ran': N, 'skipped': M, 'failed': X, 'backup': path}
        """
        result = {
            'ran': 0,
            'skipped': 0,
            'failed': 0,
            'backup': None,
            'errors': [],
        }
        
        current_version = self.get_current_version()
        logger.info(f"📊 نسخه فعلی دیتابیس: {current_version}")
        
        # ✅ فیلتر migration‌های لازم
        pending = [
            (v, n, f) for v, n, f in self.migrations
            if v > current_version
        ]
        
        if not pending:
            logger.info("✅ همه migration‌ها اجرا شده‌اند — نیازی به backup نیست")
            result['skipped'] = len(self.migrations)
            return result
        
        logger.info(f"🔄 {len(pending)} migration در انتظار اجرا")
        
        # ✅ Backup قبل از migration
        backup_path = self.backup_manager.create_backup(tag="pre_migration")
        
        if not backup_path:
            logger.error("❌ Backup ساخته نشد — migration لغو شد")
            result['errors'].append("Backup failed")
            result['failed'] = len(pending)
            return result
        
        result['backup'] = backup_path
        
        # ✅ اجرای هر migration
        for version, name, func in pending:
            success = self._run_single_migration(
                version, name, func, backup_path
            )
            
            if success:
                result['ran'] += 1
            else:
                result['failed'] += 1
                result['errors'].append(f"{version}: {name}")
                # توقف در صورت خطا
                break
        
        if result['failed'] == 0:
            logger.info(f"✅ {result['ran']} migration با موفقیت اجرا شد")
        else:
            logger.error(
                f"❌ {result['failed']} migration ناموفق — بازگردانی از backup"
            )
        
        return result
    
    def _run_single_migration(
        self,
        version: int,
        name: str,
        func: Callable,
        backup_path: str,
    ) -> bool:
        """
        اجرای یک migration
        
        Returns:
            bool: موفقیت
        """
        logger.info(f"🔄 اجرای migration {version}: {name}")
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=OFF")
            
            cursor = conn.cursor()
            
            # ✅ Transaction صریح
            cursor.execute("BEGIN")
            
            try:
                # اجرای تابع migration
                func(cursor, conn)
                
                # ذخیره نسخه
                cursor.execute(f"PRAGMA user_version = {version}")
                
                # ✅ Commit
                conn.commit()
                
                logger.info(f"✅ Migration {version} ({name}) انجام شد")
                return True
            
            except Exception as e:
                # ✅ Rollback
                logger.error(f"❌ خطا در migration {version}: {e}", exc_info=True)
                conn.rollback()
                raise
        
        except Exception as e:
            logger.error(
                f"❌ migration {version} ناموفق — بازگردانی از backup...",
                exc_info=True
            )
            
            # ✅ بازگردانی از backup
            if backup_path:
                restored = self.backup_manager.restore_backup(backup_path)
                if restored:
                    logger.info("✅ بازگردانی موفق")
                else:
                    logger.critical("🚨 بازگردانی ناموفق! مشتری باید دستی restore کنه")
            
            return False
        
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


# ============================================================
# ========== Migration Functions ==========
# ============================================================

def migration_v1_initial_setup(cursor: sqlite3.Cursor, conn: sqlite3.Connection):
    """
    Migration 1: راه‌اندازی اولیه
    (نسخه اولیه — همه جداول تو database.py ساخته میشن)
    """
    # این migration کاری انجام نمیده چون جداول تو database.py ساخته شدن
    # فقط نسخه رو ست می‌کنه
    logger.info("  → راه‌اندازی اولیه")


def migration_v2_warehouse_stock(cursor: sqlite3.Cursor, conn: sqlite3.Connection):
    """
    Migration 2: همگام‌سازی products.stock با warehouse_stock
    
    این همون کاریه که قبلاً تو document_widget.py بود
    """
    logger.info("  → همگام‌سازی stock با warehouse_stock")
    
    # 1. پیدا کردن انبار پیش‌فرض
    cursor.execute("""
        SELECT id FROM warehouses
        WHERE is_default = 1 AND is_active = 1
        LIMIT 1
    """)
    row = cursor.fetchone()
    
    if row:
        default_warehouse_id = row['id']
    else:
        cursor.execute("""
            SELECT id FROM warehouses
            WHERE is_active = 1
            ORDER BY id LIMIT 1
        """)
        row = cursor.fetchone()
        default_warehouse_id = row['id'] if row else None
    
    if not default_warehouse_id:
        logger.warning("  ⚠️ هیچ انبار فعالی نیست — migration لغو شد")
        return
    
    # 2. کالاهایی که رکورد warehouse_stock ندارن
    cursor.execute("""
        SELECT p.id, p.code, p.stock
        FROM products p
        WHERE p.stock > 0
          AND NOT EXISTS (
              SELECT 1 FROM warehouse_stock ws
              WHERE ws.product_id = p.id
                AND ws.warehouse_id = ?
          )
    """, [default_warehouse_id])
    
    migrated = 0
    for row in cursor.fetchall():
        cursor.execute("""
            INSERT INTO warehouse_stock
            (product_id, warehouse_id, quantity, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, [row['id'], default_warehouse_id, row['stock']])
        migrated += 1
    
    logger.info(f"  → {migrated} کالا منتقل شد")
    
    # 3. بررسی اختلاف
    cursor.execute("""
        SELECT p.id, p.stock,
               COALESCE(
                   (SELECT SUM(quantity) FROM warehouse_stock WHERE product_id = p.id),
                   0
               ) as ws_total
        FROM products p
        WHERE p.stock > 0
    """)
    
    fixed = 0
    for row in cursor.fetchall():
        diff = row['stock'] - row['ws_total']
        if abs(diff) > 0.01:
            cursor.execute("""
                INSERT INTO warehouse_stock
                (product_id, warehouse_id, quantity, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(product_id, warehouse_id) DO UPDATE SET
                    quantity = quantity + ?,
                    updated_at = CURRENT_TIMESTAMP
            """, [row['id'], default_warehouse_id, diff, diff])
            fixed += 1
    
    logger.info(f"  → {fixed} اختلاف اصلاح شد")


# ============================================================
# ========== Public API ==========
# ============================================================

_runner_cache: Optional[MigrationRunner] = None


def get_migration_runner(db_path: str = None) -> MigrationRunner:
    """دریافت نمونه MigrationRunner"""
    global _runner_cache
    
    if db_path is None:
        from database import DB_NAME
        db_path = DB_NAME
    
    if _runner_cache is None or _runner_cache.db_path != db_path:
        _runner_cache = MigrationRunner(db_path)
        _register_all_migrations(_runner_cache)
    
    return _runner_cache


def _register_all_migrations(runner: MigrationRunner):
    """ثبت همه migration‌ها"""
    runner.register(1, "initial_setup", migration_v1_initial_setup)
    runner.register(2, "warehouse_stock_sync", migration_v2_warehouse_stock)


def run_migrations() -> dict:
    """
    اجرای همه migration‌های لازم
    
    این تابع رو تو main2.py صدا بزن (بعد از init_database)
    
    Returns:
        dict: نتیجه اجرا
    """
    runner = get_migration_runner()
    result = runner.run()
    
    if result['failed'] > 0:
        logger.error(
            f"❌ {result['failed']} migration ناموفق!\n"
            f"بکاپ: {result['backup']}"
        )
    elif result['ran'] > 0:
        logger.info(
            f"✅ {result['ran']} migration با موفقیت اجرا شد\n"
            f"بکاپ قبل از migration: {result['backup']}"
        )
    else:
        logger.info("✅ همه migration‌ها از قبل اجرا شده‌اند")
    
    return result


def list_available_backups() -> List[dict]:
    """لیست backup‌های موجود"""
    from database import DB_NAME
    manager = BackupManager(DB_NAME)
    return manager.list_backups()


def create_manual_backup() -> Optional[str]:
    """ساخت backup دستی (برای دکمه «پشتیبان‌گیری فوری»)"""
    from database import DB_NAME
    manager = BackupManager(DB_NAME)
    return manager.create_backup(tag="manual")


def restore_from_backup(backup_path: str) -> bool:
    """بازگردانی از backup (برای پشتیبانی)"""
    from database import DB_NAME
    manager = BackupManager(DB_NAME)
    return manager.restore_backup(backup_path)


# ============================================================
# ========== تست ==========
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    
    print("=" * 60)
    print("🧪 تست Migration System")
    print("=" * 60)
    
    # 1. اجرای migration‌ها
    print("\n📊 اجرای migration‌ها...")
    result = run_migrations()
    
    print(f"\n✅ نتیجه:")
    print(f"   • اجرا شده: {result['ran']}")
    print(f"   • skip شده: {result['skipped']}")
    print(f"   • ناموفق: {result['failed']}")
    if result['backup']:
        print(f"   • backup: {result['backup']}")
    
    # 2. لیست backup‌ها
    print("\n📦 Backup‌های موجود:")
    backups = list_available_backups()
    for b in backups[:5]:
        print(f"   • {b['name']} ({b['size_mb']:.2f} MB)")
    
    # 3. ساخت backup دستی
    print("\n💾 ساخت backup دستی...")
    backup = create_manual_backup()
    if backup:
        print(f"   ✅ ساخته شد: {backup}")
    
    print("\n" + "=" * 60)
    print("✅ تست کامل شد")
    print("=" * 60)
