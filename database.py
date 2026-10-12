# database.py
# ============================================================
# دیتابیس ImanAccount - نسخه v10.0 (Migration-Based)
# ============================================================
# تغییرات نسبت به v9.0:
# ✅ جداول ماژولار به پوشه migrations/ منتقل شد
# ✅ فقط جداول هسته در اینجا ساخته می‌شوند
# ✅ استفاده از MigrationRegistry برای بقیه جداول
# ✅ کد بسیار تمیزتر و قابل نگهداری
# ============================================================

import os
import re
import time
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager, nullcontext
from typing import Optional, Dict, List, Tuple, Any

logger = logging.getLogger(__name__)


# ============================================================
# ========== ثابت‌های نسخه ==========
# ============================================================

SCHEMA_VERSION = 10
MIN_SQLITE_VERSION = (3, 24, 0)


# ============================================================
# ========== بررسی نسخه SQLite ==========
# ============================================================

def check_sqlite_version() -> None:
    """بررسی حداقل نسخه SQLite موردنیاز"""
    current = tuple(map(int, sqlite3.sqlite_version.split('.')))
    if current < MIN_SQLITE_VERSION:
        raise RuntimeError(
            f"SQLite نسخه {sqlite3.sqlite_version} نصب است. "
            f"حداقل نسخه موردنیاز "
            f"{'.'.join(map(str, MIN_SQLITE_VERSION))} است."
        )


# ============================================================
# ========== مسیر امن دیتابیس ==========
# ============================================================

def _get_db_path() -> str:
    """دریافت مسیر امن دیتابیس"""
    env_path = os.environ.get('IMANACCOUNT_DB_PATH')
    if env_path:
        path = Path(env_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    if os.name == 'nt':
        appdata = os.environ.get('APPDATA')
        if appdata and os.path.isdir(appdata):
            base = Path(appdata) / "ImanAccount"
            base.mkdir(parents=True, exist_ok=True)
            return str(base / "accounting.db")

    if os.name != 'nt':
        xdg = os.environ.get('XDG_CONFIG_HOME')
        if xdg and os.path.isdir(xdg):
            base = Path(xdg) / "imanaccount"
            base.mkdir(parents=True, exist_ok=True)
            return str(base / "accounting.db")
        home = Path.home()
        base = home / ".config" / "imanaccount"
        base.mkdir(parents=True, exist_ok=True)
        return str(base / "accounting.db")

    home = Path.home()
    docs = home / "Documents" / "ImanAccount"
    docs.mkdir(parents=True, exist_ok=True)
    return str(docs / "accounting.db")


DB_NAME = _get_db_path()


# ============================================================
# ========== Context Manager ==========
# ============================================================

@contextmanager
def get_db(timeout: float = 30.0):
    """Context Manager برای اتصال به دیتابیس"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, timeout=timeout)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            try:
                conn.execute("PRAGMA optimize")
            except Exception:
                pass
            conn.close()


# ============================================================
# ========== DateConverter ==========
# ============================================================

class DateConverter:
    """کلاس تبدیل تاریخ - پشتیبانی شمسی↔میلادی"""

    _date_system = None
    _date_system_loaded = False

    @classmethod
    def get_date_system(cls) -> str:
        if not cls._date_system_loaded:
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("SELECT value FROM settings WHERE key = 'date_system'")
                    row = c.fetchone()
                    cls._date_system = row[0] if row else "شمسی"
            except Exception:
                cls._date_system = "شمسی"
            cls._date_system_loaded = True
        return cls._date_system or "شمسی"

    @classmethod
    def set_date_system(cls, system: str):
        if system in ['شمسی', 'میلادی']:
            cls._date_system = system
            cls._date_system_loaded = True
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute(
                        "INSERT OR REPLACE INTO settings (key, value) VALUES ('date_system', ?)",
                        (system,)
                    )
            except Exception:
                pass

    @classmethod
    def refresh(cls):
        cls._date_system = None
        cls._date_system_loaded = False

    @staticmethod
    def _is_jalali(date_str: str) -> bool:
        try:
            date_str = str(date_str).replace('-', '/')
            if '/' in date_str:
                year = int(date_str.split('/')[0])
                return 1300 <= year <= 1500
        except Exception:
            pass
        return False

    @staticmethod
    def _is_gregorian(date_str: str) -> bool:
        try:
            date_str = str(date_str).replace('-', '/')
            if '/' in date_str:
                year = int(date_str.split('/')[0])
                return 1900 <= year <= 2100
        except Exception:
            pass
        return False

    @staticmethod
    def _to_jalali(gregorian_str: str) -> str:
        try:
            from persiantools.jdatetime import JalaliDate
            gregorian_str = str(gregorian_str).replace('-', '/')
            parts = gregorian_str.split('/')
            if len(parts) == 3:
                j = JalaliDate.to_jalali(int(parts[0]), int(parts[1]), int(parts[2]))
                return f"{j.year:04d}/{j.month:02d}/{j.day:02d}"
        except Exception:
            pass
        return str(gregorian_str)

    @staticmethod
    def _to_gregorian(jalali_str: str) -> str:
        try:
            from persiantools.jdatetime import JalaliDate
            jalali_str = str(jalali_str).replace('-', '/')
            parts = jalali_str.split('/')
            if len(parts) == 3:
                g = JalaliDate(int(parts[0]), int(parts[1]), int(parts[2])).to_gregorian()
                return g.strftime("%Y-%m-%d")
        except Exception:
            pass
        return str(jalali_str)

    @classmethod
    def for_display(cls, date_value) -> str:
        if not date_value:
            return ""
        date_str = str(date_value).strip()
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        if ' ' in date_str:
            date_str = date_str.split(' ')[0]
        date_str = date_str.replace('-', '/')
        system = cls.get_date_system()

        if cls._is_gregorian(date_str) and system == "شمسی":
            return cls._to_jalali(date_str)
        if cls._is_jalali(date_str) and system == "میلادی":
            return cls._to_gregorian(date_str)
        return date_str

    @classmethod
    def for_db(cls, date_value) -> str:
        if not date_value:
            return cls.today_jalali()
        date_str = str(date_value).strip()
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        if ' ' in date_str:
            date_str = date_str.split(' ')[0]
        date_str = date_str.replace('-', '/')

        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                try:
                    year = int(parts[0])
                    if 1900 <= year <= 2100:
                        return cls._to_jalali(date_str)
                except Exception:
                    pass
        return date_str

    @staticmethod
    def today_gregorian() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def today_jalali() -> str:
        try:
            from persiantools.jdatetime import JalaliDate
            return JalaliDate.today().strftime("%Y/%m/%d")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")


# ============================================================
# ========== Migration Engine (Legacy) ==========
# ============================================================
# این Engine فقط برای Migration از دیتابیس‌های بسیار قدیمی است.
# برای Migration های جدید، از MigrationRegistry استفاده می‌کنیم.
# ============================================================

class MigrationEngine:
    """موتور Migration قدیمی - فقط برای سازگاری با دیتابیس‌های v0-v9"""
    
    @classmethod
    def get_current_version(cls, conn) -> int:
        try:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS db_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
            c.execute("SELECT MAX(version) FROM db_version")
            row = c.fetchone()
            return row[0] if row and row[0] else 0
        except Exception:
            return 0
    
    @classmethod
    def migrate(cls, conn) -> bool:
        """اجرای Migration های قدیمی"""
        current = cls.get_current_version(conn)
        target = SCHEMA_VERSION
        
        if current >= target:
            return True
        
        logger.info(f"🔄 Migration Engine: از v{current} به v{target}")
        
        for version in range(current + 1, target + 1):
            migration_func = getattr(cls, f'_migrate_to_v{version}', None)
            if migration_func:
                try:
                    logger.info(f"   → v{version}: {migration_func.__doc__ or ''}")
                    migration_func(conn)
                    cls._record_version(conn, version)
                except Exception as e:
                    logger.error(f"❌ خطا در Migration v{version}: {e}")
                    return False
        
        return True
    
    @classmethod
    def _record_version(cls, conn, version: int):
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO db_version (version, description) VALUES (?, ?)",
            [version, f"Migration to v{version}"]
        )
    
    # Migration های قدیمی (فقط برای سازگاری)
    @staticmethod
    def _migrate_to_v10(conn):
        """این نسخه توسط MigrationRegistry مدیریت می‌شود"""
        pass


# ============================================================
# ========== DatabaseManager ==========
# ============================================================

class DatabaseManager:
    """
    مدیریت دیتابیس - فقط جداول هسته.
    
    جداول ماژولار در پوشه migrations/ ساخته می‌شوند و
    از طریق MigrationRegistry اجرا می‌شوند.
    """

    @staticmethod
    def to_dict(row) -> Optional[Dict]:
        if row is None:
            return None
        return dict(row)

    @staticmethod
    def init_db():
        """
        راه‌اندازی دیتابیس.
        
        مراحل:
        1. ساخت جداول هسته (companies, settings, users, accounts, vouchers)
        2. Migration Engine (برای سازگاری با دیتابیس‌های قدیمی)
        3. ثبت Migration های ماژولار
        4. اجرای Migration های ماژولار
        5. داده‌های پیش‌فرض
        """
        check_sqlite_version()
        
        with get_db() as conn:
            # ─── ۱. جداول هسته ───
            DatabaseManager._create_core_tables(conn)
            conn.commit()
            
            # ─── ۲. Migration Engine (Legacy) ───
            MigrationEngine.migrate(conn)
            conn.commit()
            
            # ─── ۳. ثبت Migration های ماژولار ───
            try:
                from migrations import register_all_migrations
                loaded, failed = register_all_migrations()
                logger.info(f"📋 {len(loaded)} ماژول Migration بارگذاری شد")
                if failed:
                    for module_name, error in failed:
                        logger.warning(f"   ⚠️ {module_name}: {error}")
            except Exception as e:
                logger.error(f"❌ خطا در ثبت Migration ها: {e}", exc_info=True)
            
            # ─── ۴. اجرای Migration های ماژولار ───
            try:
                from migration_registry import get_migration_registry
                registry = get_migration_registry()
                result = registry.run_all(conn)
                conn.commit()
                
                if result['failed']:
                    logger.error(f"❌ {len(result['failed'])} Migration با خطا مواجه شد")
                    for name, error in result['failed']:
                        logger.error(f"   • {name}: {error}")
            except Exception as e:
                logger.error(f"❌ خطا در اجرای Migration ها: {e}", exc_info=True)
            
            # ─── ۵. نسخه نهایی ───
            version = MigrationEngine.get_current_version(conn)
            
            print(f"✅ دیتابیس v{version} آماده است - مسیر: {DB_NAME}")
            print(f"📅 سیستم تاریخ: {DateConverter.get_date_system()}")

    # ═══════════════════════════════════════════════════════
    # جداول هسته — فقط جداول پایه بدون وابستگی
    # ═══════════════════════════════════════════════════════
    
    @staticmethod
    def _create_core_tables(conn):
        """
        ساخت جداول هسته.
        
        این جداول توسط MigrationRegistry هم قابل ساخت هستند،
        اما برای اطمینان و سازگاری، اینجا هم ساخته می‌شوند.
        """
        c = conn.cursor()
        
        # ─── companies ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                legal_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ─── settings ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # ─── users ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                level TEXT DEFAULT 'viewer',
                is_active BOOLEAN DEFAULT 1,
                must_change_password INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # ─── accounts ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parent_code TEXT,
                level INTEGER DEFAULT 1,
                color TEXT,
                balance REAL DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                company_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ─── vouchers ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_no INTEGER UNIQUE,
                date TEXT NOT NULL,
                description TEXT,
                type TEXT DEFAULT 'عادی',
                status TEXT DEFAULT 'draft',
                created_by TEXT,
                approved_by TEXT,
                company_id INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ─── voucher_items ───
        c.execute('''
            CREATE TABLE IF NOT EXISTS voucher_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_id INTEGER,
                account_code TEXT,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                description TEXT,
                cost_center TEXT,
                project_code TEXT,
                FOREIGN KEY(voucher_id) REFERENCES vouchers(id) ON DELETE CASCADE,
                FOREIGN KEY(account_code) REFERENCES accounts(code)
            )
        ''')
        
        # ─── ایندکس‌های هسته ───
        for idx in [
            "CREATE INDEX IF NOT EXISTS idx_vouchers_date ON vouchers(date)",
            "CREATE INDEX IF NOT EXISTS idx_vouchers_type ON vouchers(type)",
            "CREATE INDEX IF NOT EXISTS idx_vouchers_status ON vouchers(status)",
            "CREATE INDEX IF NOT EXISTS idx_voucher_items_voucher ON voucher_items(voucher_id)",
            "CREATE INDEX IF NOT EXISTS idx_voucher_items_account ON voucher_items(account_code)",
            "CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(type)",
            "CREATE INDEX IF NOT EXISTS idx_accounts_parent ON accounts(parent_code)",
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
        ]:
            c.execute(idx)


# ============================================================
# ========== AccountingHelper ==========
# ============================================================

class AccountingHelper:
    """کلاس کمکی برای عملیات حسابداری"""

    @staticmethod
    def get_account_balance(account_code: str, from_date: str = None, to_date: str = None) -> float:
        with get_db() as conn:
            c = conn.cursor()
            query = '''
                SELECT COALESCE(SUM(vi.debit), 0) - COALESCE(SUM(vi.credit), 0)
                FROM voucher_items vi
                JOIN vouchers v ON vi.voucher_id = v.id
                WHERE vi.account_code = ?
            '''
            params = [account_code]
            if from_date:
                query += " AND v.date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND v.date <= ?"
                params.append(to_date)
            c.execute(query, params)
            return c.fetchone()[0] or 0

    @staticmethod
    def get_accounts_balances(account_codes: List[str], from_date: str = None, to_date: str = None) -> Dict[str, float]:
        if not account_codes:
            return {}
        with get_db() as conn:
            c = conn.cursor()
            placeholders = ','.join('?' * len(account_codes))
            query = f'''
                SELECT vi.account_code,
                       COALESCE(SUM(vi.debit), 0) - COALESCE(SUM(vi.credit), 0) as balance
                FROM voucher_items vi
                JOIN vouchers v ON vi.voucher_id = v.id
                WHERE vi.account_code IN ({placeholders})
            '''
            params = list(account_codes)
            if from_date:
                query += " AND v.date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND v.date <= ?"
                params.append(to_date)
            query += " GROUP BY vi.account_code"
            c.execute(query, params)
            return {row['account_code']: row['balance'] for row in c.fetchall()}

    @staticmethod
    def get_account_balance_by_type(account_type: str, from_date: str = None, to_date: str = None) -> float:
        with get_db() as conn:
            c = conn.cursor()
            if account_type in ['asset', 'expense']:
                balance_sql = "COALESCE(SUM(vi.debit), 0) - COALESCE(SUM(vi.credit), 0)"
            else:
                balance_sql = "COALESCE(SUM(vi.credit), 0) - COALESCE(SUM(vi.debit), 0)"
            query = f'''
                SELECT {balance_sql}
                FROM voucher_items vi
                JOIN accounts a ON vi.account_code = a.code
                JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = ?
            '''
            params = [account_type]
            if from_date:
                query += " AND v.date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND v.date <= ?"
                params.append(to_date)
            c.execute(query, params)
            return c.fetchone()[0] or 0


# ============================================================
# ========== InventoryHelper ==========
# ============================================================

class InventoryHelper:
    """
    کلاس کمکی برای عملیات انبار.
    
    تابع مرکزی adjust_stock همه تغییرات موجودی را مدیریت می‌کند.
    """
    
    @staticmethod
    def adjust_stock(product_id: int, quantity: float, transaction_type: str,
                     warehouse_id: int = None, conn=None) -> bool:
        """
        تنظیم موجودی کالا در هر دو جدول products و warehouse_stock.
        
        Args:
            product_id: شناسه کالا
            quantity: مقدار (همیشه مثبت)
            transaction_type: 'in' (ورود) | 'out' (خروج)
            warehouse_id: شناسه انبار (اگر None باشد، انبار پیش‌فرض)
            conn: اتصال موجود (اختیاری)
        
        Returns:
            bool: موفقیت
        """
        if quantity <= 0:
            logger.warning(f"⚠️ quantity باید مثبت باشد: {quantity}")
            return False
        
        if transaction_type not in ('in', 'out'):
            logger.error(f"❌ transaction_type نامعتبر: {transaction_type}")
            return False
        
        if conn is None:
            ctx = get_db(timeout=10.0)
            should_close = True
        else:
            ctx = nullcontext(conn)
            should_close = False
        
        try:
            with ctx as c:
                # ─── ۱. تعیین انبار ───
                if warehouse_id is None:
                    warehouse_id = InventoryHelper._get_default_warehouse_id(c)
                
                if warehouse_id is None:
                    logger.warning("⚠️ هیچ انبار فعالی وجود ندارد")
                    return False
                
                # ─── ۲. محاسبه delta ───
                delta = quantity if transaction_type == 'in' else -quantity
                
                # ─── ۳. اطمینان از وجود رکورد در warehouse_stock ───
                c.execute("""
                    INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, updated_at)
                    VALUES (?, ?, 0, CURRENT_TIMESTAMP)
                    ON CONFLICT(product_id, warehouse_id) DO NOTHING
                """, [product_id, warehouse_id])
                
                # ─── ۴. به‌روزرسانی warehouse_stock ───
                c.execute("""
                    UPDATE warehouse_stock 
                    SET quantity = MAX(0, quantity + ?), 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ? AND warehouse_id = ?
                """, [delta, product_id, warehouse_id])
                
                # ─── ۵. به‌روزرسانی products.stock ───
                c.execute("""
                    UPDATE products 
                    SET stock = (
                        SELECT COALESCE(SUM(quantity), 0) 
                        FROM warehouse_stock 
                        WHERE product_id = ?
                    ),
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, [product_id, product_id])
                
                return True
        
        except Exception as e:
            logger.error(f"❌ خطا در adjust_stock: {e}", exc_info=True)
            return False
    
    @staticmethod
    def _get_default_warehouse_id(conn) -> Optional[int]:
        """دریافت شناسه انبار پیش‌فرض"""
        c = conn.cursor()
        
        c.execute("""
            SELECT id FROM warehouses 
            WHERE is_default = 1 AND is_active = 1 
            LIMIT 1
        """)
        row = c.fetchone()
        if row:
            return row['id'] if hasattr(row, 'keys') else row[0]
        
        c.execute("""
            SELECT id FROM warehouses 
            WHERE is_active = 1 
            ORDER BY id LIMIT 1
        """)
        row = c.fetchone()
        if row:
            return row['id'] if hasattr(row, 'keys') else row[0]
        
        return None
    
    @staticmethod
    def get_stock(product_id: int, warehouse_id: int = None) -> float:
        """خواندن موجودی کالا"""
        with get_db() as conn:
            c = conn.cursor()
            
            if warehouse_id is None:
                c.execute("""
                    SELECT COALESCE(SUM(quantity), 0) 
                    FROM warehouse_stock 
                    WHERE product_id = ?
                """, [product_id])
            else:
                c.execute("""
                    SELECT COALESCE(quantity, 0) 
                    FROM warehouse_stock 
                    WHERE product_id = ? AND warehouse_id = ?
                """, [product_id, warehouse_id])
            
            row = c.fetchone()
            return float(row[0]) if row and row[0] else 0.0
    
    @staticmethod
    def get_product_stock(product_id: int) -> float:
        """خواندن موجودی کل کالا از جدول products"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT stock FROM products WHERE id = ?", [product_id])
            row = c.fetchone()
            return float(row[0]) if row and row[0] else 0.0
    
    @staticmethod
    def get_warehouse_stock(product_id: int, warehouse_id: int = None) -> float:
        """خواندن موجودی از warehouse_stock"""
        return InventoryHelper.get_stock(product_id, warehouse_id)
    
    @staticmethod
    def get_low_stock_products() -> List:
        """دریافت کالاهای زیر حداقل موجودی"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM products
                WHERE stock <= min_stock AND min_stock > 0 AND is_active = 1
                ORDER BY stock ASC
            ''')
            return c.fetchall()
    
    @staticmethod
    def sync_product_stock(product_id: int, conn=None) -> bool:
        """همگام‌سازی products.stock با مجموع warehouse_stock"""
        if conn is None:
            ctx = get_db(timeout=10.0)
        else:
            ctx = nullcontext(conn)
        
        try:
            with ctx as c:
                c.execute("""
                    UPDATE products 
                    SET stock = (
                        SELECT COALESCE(SUM(quantity), 0) 
                        FROM warehouse_stock 
                        WHERE product_id = ?
                    ),
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, [product_id, product_id])
                return True
        except Exception as e:
            logger.error(f"❌ خطا در sync_product_stock: {e}")
            return False
    
    @staticmethod
    def sync_all_products(conn=None) -> int:
        """همگام‌سازی همه کالاها"""
        if conn is None:
            ctx = get_db(timeout=30.0)
        else:
            ctx = nullcontext(conn)
        
        try:
            with ctx as c:
                c.execute("SELECT id FROM products")
                product_ids = [row[0] if not hasattr(row, 'keys') else row['id'] 
                              for row in c.fetchall()]
                
                count = 0
                for pid in product_ids:
                    c.execute("""
                        UPDATE products 
                        SET stock = (
                            SELECT COALESCE(SUM(quantity), 0) 
                            FROM warehouse_stock 
                            WHERE product_id = ?
                        ),
                        updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, [pid, pid])
                    count += 1
                
                logger.info(f"✅ {count} کالا همگام‌سازی شد")
                return count
        except Exception as e:
            logger.error(f"❌ خطا در sync_all_products: {e}")
            return 0
    
    @staticmethod
    def update_stock(product_id: int, quantity: float, transaction_type: str):
        """سازگاری با کد قدیم"""
        return InventoryHelper.adjust_stock(product_id, quantity, transaction_type)


# ============================================================
# ========== FinanceHelper ==========
# ============================================================

class FinanceHelper:
    """کلاس کمکی برای عملیات امور مالی"""

    @staticmethod
    def get_total_balance() -> Dict[str, int]:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COALESCE(SUM(balance), 0) FROM banks WHERE is_active = 1")
            bank_total = c.fetchone()[0] or 0
            c.execute("SELECT COALESCE(SUM(balance), 0) FROM cash_boxes WHERE is_active = 1")
            cash_total = c.fetchone()[0] or 0
            return {
                'banks': bank_total,
                'cash': cash_total,
                'total': bank_total + cash_total
            }

    @staticmethod
    def update_balance(account_type: str, account_id: int, amount: int) -> bool:
        try:
            with get_db() as conn:
                c = conn.cursor()
                if account_type == 'bank':
                    c.execute(
                        "UPDATE banks SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        [amount, account_id]
                    )
                elif account_type == 'cash':
                    c.execute(
                        "UPDATE cash_boxes SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        [amount, account_id]
                    )
                return True
        except Exception as e:
            logger.error(f"خطا در بروزرسانی مانده: {e}")
            return False

    @staticmethod
    def generate_transaction_no() -> str:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT MAX(id) FROM finance_transactions")
            max_id = c.fetchone()[0] or 0
            return f"TRX{max_id + 1:06d}"


# ============================================================
# ========== PartyHelper ==========
# ============================================================

class PartyHelper:
    """کلاس کمکی برای اشخاص"""

    @staticmethod
    def get_party_balance(party_id: int) -> int:
        """محاسبه مانده واقعی شخص"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                balance = 0
                
                c.execute("SELECT type FROM parties WHERE id = ?", [party_id])
                row = c.fetchone()
                if not row:
                    return 0
                
                party_type = row['type'] if hasattr(row, 'keys') else row[0]
                
                # فاکتورها
                if party_type == 'customer':
                    c.execute("""
                        SELECT COALESCE(SUM(net_amount), 0) FROM documents
                        WHERE party_id = ? AND doc_type = 'sales'
                    """, [party_id])
                    balance += c.fetchone()[0] or 0
                    
                    c.execute("""
                        SELECT COALESCE(SUM(net_amount), 0) FROM documents
                        WHERE party_id = ? AND doc_type = 'sales_return'
                    """, [party_id])
                    balance -= c.fetchone()[0] or 0
                else:
                    c.execute("""
                        SELECT COALESCE(SUM(net_amount), 0) FROM documents
                        WHERE party_id = ? AND doc_type = 'purchase'
                    """, [party_id])
                    balance += c.fetchone()[0] or 0
                    
                    c.execute("""
                        SELECT COALESCE(SUM(net_amount), 0) FROM documents
                        WHERE party_id = ? AND doc_type = 'purchase_return'
                    """, [party_id])
                    balance -= c.fetchone()[0] or 0
                
                # تراکنش‌های مالی
                if party_type == 'customer':
                    c.execute("""
                        SELECT COALESCE(SUM(amount), 0) FROM finance_transactions
                        WHERE party_id = ? AND type IN ('receipt', 'income')
                    """, [party_id])
                    balance -= c.fetchone()[0] or 0
                else:
                    c.execute("""
                        SELECT COALESCE(SUM(amount), 0) FROM finance_transactions
                        WHERE party_id = ? AND type IN ('payment', 'expense')
                    """, [party_id])
                    balance -= c.fetchone()[0] or 0
                
                # چک‌ها
                if party_type == 'customer':
                    c.execute("""
                        SELECT COALESCE(SUM(amount), 0) FROM checks
                        WHERE party_id = ? AND type = 'received' AND status = 'collected'
                    """, [party_id])
                    balance -= c.fetchone()[0] or 0
                else:
                    c.execute("""
                        SELECT COALESCE(SUM(amount), 0) FROM checks
                        WHERE party_id = ? AND type = 'paid' AND status = 'collected'
                    """, [party_id])
                    balance -= c.fetchone()[0] or 0
                
                return int(balance)
        except Exception as e:
            logger.error(f"خطا در محاسبه مانده: {e}")
            return 0

    @staticmethod
    def get_party_transactions(party_id: int, 
                                from_date: str = None, 
                                to_date: str = None,
                                limit: int = 500) -> List[Dict]:
        """دریافت تراکنش‌های شخص"""
        try:
            transactions = []
            
            with get_db() as conn:
                c = conn.cursor()
                
                # فاکتورها
                query = """
                    SELECT d.date, d.doc_type as type, d.doc_no as ref,
                           d.net_amount as amount, d.description
                    FROM documents d
                    WHERE d.party_id = ?
                """
                params = [party_id]
                if from_date:
                    query += " AND d.date >= ?"
                    params.append(from_date)
                if to_date:
                    query += " AND d.date <= ?"
                    params.append(to_date)
                query += " ORDER BY d.date DESC LIMIT ?"
                params.append(limit)
                
                c.execute(query, params)
                type_map = {
                    'sales': 'فروش', 'purchase': 'خرید',
                    'sales_return': 'برگشت فروش', 'purchase_return': 'برگشت خرید',
                }
                for row in c.fetchall():
                    r = dict(row)
                    transactions.append({
                        'date': r['date'],
                        'type': type_map.get(r['type'], r['type']),
                        'ref': r['ref'],
                        'amount': r['amount'],
                        'description': r['description'] or '',
                        'kind': 'document',
                    })
                
                # تراکنش‌های مالی
                query = """
                    SELECT t.date, t.type, t.transaction_no as ref,
                           t.amount, t.description
                    FROM finance_transactions t
                    WHERE t.party_id = ?
                """
                params = [party_id]
                if from_date:
                    query += " AND t.date >= ?"
                    params.append(from_date)
                if to_date:
                    query += " AND t.date <= ?"
                    params.append(to_date)
                query += " ORDER BY t.date DESC LIMIT ?"
                params.append(limit)
                
                c.execute(query, params)
                fin_type_map = {
                    'receipt': 'دریافت', 'payment': 'پرداخت',
                    'transfer': 'انتقال', 'income': 'درآمد',
                    'expense': 'هزینه', 'capital': 'سرمایه',
                }
                for row in c.fetchall():
                    r = dict(row)
                    transactions.append({
                        'date': r['date'],
                        'type': fin_type_map.get(r['type'], r['type']),
                        'ref': r['ref'],
                        'amount': r['amount'],
                        'description': r['description'] or '',
                        'kind': 'transaction',
                    })
                
                # چک‌ها
                query = """
                    SELECT ch.issue_date as date, ch.check_number as ref,
                           ch.amount, ch.type, ch.status, ch.bank_name
                    FROM checks ch
                    WHERE ch.party_id = ?
                """
                params = [party_id]
                if from_date:
                    query += " AND ch.issue_date >= ?"
                    params.append(from_date)
                if to_date:
                    query += " AND ch.issue_date <= ?"
                    params.append(to_date)
                query += " ORDER BY ch.issue_date DESC LIMIT ?"
                params.append(limit)
                
                c.execute(query, params)
                for row in c.fetchall():
                    r = dict(row)
                    transactions.append({
                        'date': r['date'],
                        'type': 'چک دریافتی' if r['type'] == 'received' else 'چک پرداختی',
                        'ref': r['ref'],
                        'amount': r['amount'],
                        'description': f"{r['bank_name'] or ''} - {r['status']}",
                        'kind': 'check',
                    })
            
            transactions.sort(key=lambda x: x.get('date', ''), reverse=True)
            return transactions[:limit]
        
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌ها: {e}")
            return []

    @staticmethod
    def generate_next_code(party_type: str = 'customer') -> str:
        """تولید کد بعدی"""
        prefix = "CUST" if party_type == 'customer' else "SUPP"
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(f"""
                    SELECT code FROM parties 
                    WHERE code LIKE '{prefix}%' 
                    ORDER BY code DESC LIMIT 1
                """)
                last = c.fetchone()
                
                if last:
                    code = last['code'] if hasattr(last, 'keys') else last[0]
                    try:
                        num = int(code.replace(prefix, '')) + 1
                    except:
                        num = 1
                else:
                    num = 1
                
                return f"{prefix}{num:05d}"
        except Exception:
            return f"{prefix}00001"

    @staticmethod
    def get_groups(party_type: str = None) -> List[Dict]:
        """دریافت گروه‌های اشخاص"""
        with get_db() as conn:
            c = conn.cursor()
            if party_type:
                c.execute("""
                    SELECT * FROM party_groups
                    WHERE (party_type = ? OR party_type = 'both') AND is_active = 1
                    ORDER BY name
                """, [party_type])
            else:
                c.execute("SELECT * FROM party_groups WHERE is_active = 1 ORDER BY name")
            return [dict(row) for row in c.fetchall()]

    @staticmethod
    def add_note(party_id: int, note_text: str, note_type: str = 'general', created_by: str = None):
        """افزودن یادداشت"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO party_notes (party_id, note_text, note_type, created_by)
                VALUES (?, ?, ?, ?)
            """, [party_id, note_text, note_type, created_by])

    @staticmethod
    def get_notes(party_id: int) -> List[Dict]:
        """دریافت یادداشت‌ها"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM party_notes WHERE party_id = ?
                ORDER BY created_at DESC
            """, [party_id])
            return [dict(row) for row in c.fetchall()]

    @staticmethod
    def add_contact(party_id: int, name: str, position: str = None,
                    phone: str = None, mobile: str = None, email: str = None):
        """افزودن مخاطب"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO party_contacts 
                (party_id, name, position, phone, mobile, email)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [party_id, name, position, phone, mobile, email])

    @staticmethod
    def get_contacts(party_id: int) -> List[Dict]:
        """دریافت مخاطبین"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM party_contacts WHERE party_id = ?
                ORDER BY is_primary DESC, name
            """, [party_id])
            return [dict(row) for row in c.fetchall()]

    @staticmethod
    def update_balance_cache(party_id: int):
        """بروزرسانی مانده کش شده"""
        try:
            balance = PartyHelper.get_party_balance(party_id)
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE parties SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [balance, party_id]
                )
        except Exception as e:
            logger.error(f"خطا در بروزرسانی کش: {e}")


# ============================================================
# ========== ModuleLimitHelper ==========
# ============================================================

class ModuleLimitHelper:
    """مدیریت محدودیت ماژول‌ها"""

    _limits_cache = None
    _cache_loaded = False

    @classmethod
    def _load_limits_from_license(cls) -> Dict:
        if cls._cache_loaded:
            return cls._limits_cache or {}
        try:
            from license_core import get_license_core
            core = get_license_core()
            license_key = core.load_license()
            if not license_key:
                cls._limits_cache = {}
                cls._cache_loaded = True
                return {}
            result = core.verify_license(license_key)
            if not result.get('valid'):
                cls._limits_cache = {}
                cls._cache_loaded = True
                return {}
            data = result.get('data', {})
            cls._limits_cache = data.get('limits', {})
            cls._cache_loaded = True
            return cls._limits_cache
        except Exception as e:
            logger.warning(f"خطا در خواندن محدودیت‌ها: {e}")
            cls._limits_cache = {}
            cls._cache_loaded = True
            return {}

    @classmethod
    def refresh_cache(cls):
        cls._limits_cache = None
        cls._cache_loaded = False

    @classmethod
    def get_module_limit(cls, customer_name: str, module_name: str) -> int:
        limits = cls._load_limits_from_license()
        return limits.get(module_name, 0)

    @classmethod
    def get_current_count(cls, module_name: str) -> int:
        with get_db() as conn:
            c = conn.cursor()
            table_map = {
                'accounting': 'vouchers',
                'inventory': 'products',
                'payroll': 'employees',
                'parties': 'parties',
                'finance': 'finance_transactions',
            }
            if module_name in table_map:
                c.execute(f"SELECT COUNT(*) FROM {table_map[module_name]}")
            elif module_name == 'invoice':
                c.execute("SELECT COUNT(*) FROM documents WHERE doc_type = 'sales'")
            elif module_name == 'purchase':
                c.execute("SELECT COUNT(*) FROM documents WHERE doc_type = 'purchase'")
            else:
                return 0
            return c.fetchone()[0] or 0

    @classmethod
    def check_module_limit(cls, customer_name: str, module_name: str) -> Tuple[bool, int, int, str]:
        limit = cls.get_module_limit(customer_name, module_name)
        current = cls.get_current_count(module_name)
        if limit == 0:
            return True, current, limit, "نامحدود"
        remaining = limit - current
        if current >= limit:
            return False, current, limit, f"به سقف مجاز {limit} رسیده‌اید!"
        elif remaining <= 5:
            return True, current, limit, f"⚠️ فقط {remaining} مورد دیگر تا سقف مجاز"
        else:
            return True, current, limit, f"{current} از {limit}"


# ============================================================
# ========== PayrollHelper ==========
# ============================================================

class PayrollHelper:
    """کلاس کمکی برای محاسبات حقوق"""

    @staticmethod
    def get_payroll_settings(year: int):
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM payroll_settings WHERE year = ?', [year])
            settings = c.fetchone()
            if not settings:
                c.execute('SELECT * FROM payroll_settings ORDER BY year DESC LIMIT 1')
                settings = c.fetchone()
            return settings

    @staticmethod
    def calculate_child_allowance(child_count: int, settings) -> int:
        if not settings:
            return 0
        eligible_children = min(child_count if child_count else 0, 2)
        try:
            per_child = settings['child_allowance_per_child'] if 'child_allowance_per_child' in settings.keys() else 15000000
        except Exception:
            per_child = 15000000
        return eligible_children * per_child

    @staticmethod
    def calculate_seniority_pay(hire_date, base_salary: int, settings) -> int:
        if not hire_date or not base_salary:
            return 0
        try:
            if isinstance(hire_date, str):
                hire_year = int(hire_date[:4])
            else:
                hire_year = hire_date.year
            current_year = datetime.now().year
            years = max(0, current_year - hire_year)
            eligible_years = min(years, 10)
            if settings and 'base_seniority_pay' in settings.keys():
                base_seniority = settings['base_seniority_pay']
            else:
                base_seniority = 2100000
            return base_seniority * eligible_years
        except Exception:
            return 0

    @staticmethod
    def calculate_overtime_pay(base_salary: int, hours: float, rate: float) -> int:
        if base_salary <= 0 or hours <= 0:
            return 0
        hourly_rate = (base_salary / 30) / 8
        return int(hourly_rate * hours * rate)

    @staticmethod
    def calculate_insurance(gross_salary: int, employee_rate: float, employer_rate: float) -> Tuple[int, int]:
        insurance_cap = 100_000_000
        insurance_base = min(gross_salary, insurance_cap)
        employee_share = int(insurance_base * employee_rate)
        employer_share = int(insurance_base * employer_rate)
        return employee_share, employer_share

    @staticmethod
    def calculate_tax(gross_salary: int, tax_rate: float) -> int:
        exemption = 20_000_000
        taxable = max(0, gross_salary - exemption)
        return int(taxable * tax_rate)


# ============================================================
# ========== DocumentHelper ==========
# ============================================================

class DocumentHelper:
    """کلاس کمکی برای اسناد"""

    @staticmethod
    def get_next_doc_no(doc_type: str) -> str:
        with get_db() as conn:
            c = conn.cursor()
            
            prefix_map = {
                'sales': 'SAL',
                'purchase': 'PUR',
                'sales_return': 'RSL',
                'purchase_return': 'RPR',
            }
            prefix = prefix_map.get(doc_type, 'DOC')
            
            c.execute(f"""
                SELECT MAX(CAST(SUBSTR(doc_no, 4) AS INTEGER)) 
                FROM documents WHERE doc_no LIKE '{prefix}%'
            """)
            max_no = c.fetchone()[0]
            return f"{prefix}{(max_no or 0) + 1:06d}"


# ============================================================
# ========== توابع کمکی عمومی ==========
# ============================================================

def execute_with_retry(func, *args, max_retries: int = 3, delay: float = 0.5, **kwargs):
    """اجرای تابع با تلاش مجدد"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            raise e


def safe_display_date(date_value) -> str:
    return DateConverter.for_display(date_value)


def get_today_jalali() -> str:
    return DateConverter.today_jalali()


def get_date_system() -> str:
    return DateConverter.get_date_system()


def set_date_system(system: str):
    return DateConverter.set_date_system(system)


def refresh_date_cache():
    DateConverter.refresh()


# ============================================================
# ========== اجرای مستقیم ==========
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print(f"📦 نسخه SQLite: {sqlite3.sqlite_version}")
    DatabaseManager.init_db()
    
    print("\n" + "=" * 60)
    print(f"✅ دیتابیس ImanAccount v{SCHEMA_VERSION} ساخته شد!")
    print("=" * 60)
    print(f"📁 مسیر: {DB_NAME}")
    print(f"📅 سیستم تاریخ: {DateConverter.get_date_system()}")
    print("\n✅ معماری جدید:")
    print("   • database.py فقط جداول هسته را می‌سازد")
    print("   • جداول ماژولار در migrations/ تعریف شده‌اند")
    print("   • MigrationRegistry همه را به ترتیب اجرا می‌کند")
    print("=" * 60)
