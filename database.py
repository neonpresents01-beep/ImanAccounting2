# database.py
# ============================================================
# دیتابیس ImanAccount - نسخه v6.1 (Inventory Fix)
# ============================================================
#
# تغییرات نسبت به v6.0:
# ✅ رفع باگ update_warehouse_stock.subtract
# ✅ حفظ created_at در بروزرسانی‌ها
# ✅ سایر موارد v6.0 حفظ شد
# ============================================================

import sqlite3
import os
import time
import hashlib
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, List, Tuple


# ============================================================
# ========== بررسی نسخه SQLite ==========
# ============================================================

MIN_SQLITE_VERSION = (3, 24, 0)


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
    """
    دریافت مسیر امن دیتابیس

    ترتیب اولویت:
    1. متغیر محیطی IMANACCOUNT_DB_PATH
    2. APPDATA/ImanAccount/accounting.db (ویندوز)
    3. ~/.config/imanaccount/accounting.db (لینوکس)
    4. ~/Documents/ImanAccount/accounting.db (fallback)
    """
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
# ========== تبدیل تاریخ ==========
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
# ========== اتصال به دیتابیس ==========
# ============================================================

@contextmanager
def get_db(timeout: float = 30.0):
    """
    Context Manager برای اتصال به دیتابیس

    Usage:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(...)
    """
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
# ========== مدیر دیتابیس ==========
# ============================================================

class DatabaseManager:
    """مدیریت دیتابیس - ایجاد جداول و داده‌های اولیه"""

    @staticmethod
    def to_dict(row) -> Optional[Dict]:
        if row is None:
            return None
        return dict(row)

    @staticmethod
    def init_db():
        """راه‌اندازی دیتابیس با تمام جداول، ایندکس‌ها و داده‌های اولیه"""
        check_sqlite_version()

        with get_db() as conn:
            c = conn.cursor()

            # ============================================================
            # ========== جداول اصلی ==========
            # ============================================================

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

            # ============================================================
            # ========== جداول انبار ==========
            # ============================================================

            c.execute('''
                CREATE TABLE IF NOT EXISTS warehouses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    address TEXT,
                    manager TEXT,
                    phone TEXT,
                    is_default BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    unit TEXT DEFAULT 'عدد',
                    stock REAL DEFAULT 0,
                    purchase_price REAL DEFAULT 0,
                    sale_price REAL DEFAULT 0,
                    min_stock REAL DEFAULT 0,
                    max_stock REAL DEFAULT 0,
                    barcode TEXT,
                    category TEXT,
                    brand TEXT,
                    model TEXT,
                    color TEXT,
                    size TEXT,
                    weight REAL DEFAULT 0,
                    has_serial BOOLEAN DEFAULT 0,
                    expiry_date TEXT,
                    location TEXT,
                    warehouse_id INTEGER,
                    company_id INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS warehouse_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    warehouse_id INTEGER NOT NULL,
                    quantity REAL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
                    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE,
                    UNIQUE(product_id, warehouse_id)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS product_serials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    serial_number TEXT NOT NULL,
                    warehouse_id INTEGER,
                    status TEXT DEFAULT 'in_stock',
                    purchase_date TEXT,
                    purchase_price REAL DEFAULT 0,
                    sell_date TEXT,
                    sell_price REAL DEFAULT 0,
                    customer_name TEXT,
                    notes TEXT,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
                    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
                    UNIQUE(product_id, serial_number)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS stock_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    product_id INTEGER NOT NULL,
                    warehouse_id INTEGER,
                    from_warehouse_id INTEGER,
                    to_warehouse_id INTEGER,
                    type TEXT NOT NULL CHECK(type IN ('in', 'out', 'transfer')),
                    quantity REAL NOT NULL,
                    unit_price REAL DEFAULT 0,
                    total_price REAL DEFAULT 0,
                    ref_no TEXT,
                    description TEXT,
                    serial_numbers TEXT,
                    expiry_date TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
                    FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
                    FOREIGN KEY(from_warehouse_id) REFERENCES warehouses(id),
                    FOREIGN KEY(to_warehouse_id) REFERENCES warehouses(id)
                )
            ''')

            # ============================================================
            # ========== جداول حقوق ==========
            # ============================================================

            c.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    national_code TEXT,
                    insurance_code TEXT,
                    position TEXT,
                    department TEXT,
                    hire_date TEXT,
                    base_salary INTEGER DEFAULT 0,
                    child_count INTEGER DEFAULT 0,
                    spouse_allowance INTEGER DEFAULT 0,
                    meal_allowance INTEGER DEFAULT 0,
                    housing_allowance INTEGER DEFAULT 0,
                    responsibility_pay INTEGER DEFAULT 0,
                    overtime_rate REAL DEFAULT 1.5,
                    night_work_rate REAL DEFAULT 0.35,
                    friday_work_rate REAL DEFAULT 1.5,
                    shift_allowance_rate REAL DEFAULT 0.1,
                    hardship_rate REAL DEFAULT 0,
                    insurance_premium REAL DEFAULT 0.07,
                    loan_installment INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    company_id INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    head_of_household_allowance INTEGER DEFAULT 0,
                    supplemental_insurance INTEGER DEFAULT 0,
                    holiday_work_rate REAL DEFAULT 1.5,
                    bonus INTEGER DEFAULT 0,
                    mission_allowance INTEGER DEFAULT 0,
                    advance_payment INTEGER DEFAULT 0,
                    deduction INTEGER DEFAULT 0,
                    penalty INTEGER DEFAULT 0,
                    tax_rate REAL DEFAULT 0.1,
                    seniority_pay INTEGER DEFAULT 0
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS payrolls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    work_days INTEGER DEFAULT 0,
                    overtime_hours REAL DEFAULT 0,
                    night_work_hours REAL DEFAULT 0,
                    friday_work_hours REAL DEFAULT 0,
                    shift_days INTEGER DEFAULT 0,
                    base_salary INTEGER DEFAULT 0,
                    child_allowance INTEGER DEFAULT 0,
                    spouse_allowance INTEGER DEFAULT 0,
                    housing_allowance INTEGER DEFAULT 0,
                    meal_allowance INTEGER DEFAULT 0,
                    seniority_pay INTEGER DEFAULT 0,
                    overtime_pay INTEGER DEFAULT 0,
                    night_work_pay INTEGER DEFAULT 0,
                    friday_work_pay INTEGER DEFAULT 0,
                    shift_allowance INTEGER DEFAULT 0,
                    responsibility_pay INTEGER DEFAULT 0,
                    bonus INTEGER DEFAULT 0,
                    performance_bonus INTEGER DEFAULT 0,
                    mission_allowance INTEGER DEFAULT 0,
                    loan_installment INTEGER DEFAULT 0,
                    advance_payment INTEGER DEFAULT 0,
                    deduction INTEGER DEFAULT 0,
                    penalty INTEGER DEFAULT 0,
                    gross_salary INTEGER DEFAULT 0,
                    insurance_employee INTEGER DEFAULT 0,
                    insurance_employer INTEGER DEFAULT 0,
                    legal_deductions INTEGER DEFAULT 0,
                    tax INTEGER DEFAULT 0,
                    net_salary INTEGER DEFAULT 0,
                    payment_status TEXT DEFAULT 'pending',
                    payment_date TEXT,
                    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                    UNIQUE(employee_id, year, month)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS payroll_settings (
                    year INTEGER PRIMARY KEY,
                    daily_minimum_wage INTEGER DEFAULT 2650000,
                    base_seniority_pay INTEGER DEFAULT 2100000,
                    child_allowance_per_child INTEGER DEFAULT 15000000,
                    housing_allowance INTEGER DEFAULT 15000000,
                    meal_allowance INTEGER DEFAULT 14000000,
                    tax_rate REAL DEFAULT 0.10,
                    insurance_employee_rate REAL DEFAULT 0.07,
                    insurance_employer_rate REAL DEFAULT 0.23,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS payroll_items (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT CHECK(type IN ('fixed', 'percent')),
                    value REAL DEFAULT 0,
                    unit TEXT,
                    category TEXT DEFAULT 'benefit'
                )
            ''')

            # ============================================================
            # ========== جداول اشخاص و اسناد ==========
            # ============================================================

            c.execute('''
                CREATE TABLE IF NOT EXISTS parties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    name TEXT NOT NULL,
                    company TEXT,
                    phone TEXT,
                    mobile TEXT,
                    email TEXT,
                    address TEXT,
                    economic_code TEXT,
                    national_id TEXT,
                    type TEXT CHECK(type IN ('customer', 'supplier')),
                    balance INTEGER DEFAULT 0,
                    company_id INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS party_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    party_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    type TEXT CHECK(type IN ('debit', 'credit')),
                    amount INTEGER NOT NULL,
                    description TEXT,
                    voucher_id INTEGER,
                    FOREIGN KEY(party_id) REFERENCES parties(id) ON DELETE CASCADE
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_no TEXT UNIQUE NOT NULL,
                    doc_type TEXT CHECK(doc_type IN ('sales', 'purchase')),
                    date TEXT NOT NULL,
                    party_id INTEGER NOT NULL,
                    total_amount INTEGER DEFAULT 0,
                    discount INTEGER DEFAULT 0,
                    tax INTEGER DEFAULT 0,
                    net_amount INTEGER DEFAULT 0,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    company_id INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(party_id) REFERENCES parties(id)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS document_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price INTEGER NOT NULL,
                    total_price INTEGER NOT NULL,
                    description TEXT,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    FOREIGN KEY(product_id) REFERENCES products(id)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_no TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    party_id INTEGER NOT NULL,
                    total_amount INTEGER DEFAULT 0,
                    discount INTEGER DEFAULT 0,
                    tax INTEGER DEFAULT 0,
                    net_amount INTEGER DEFAULT 0,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    company_id INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(party_id) REFERENCES parties(id)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price INTEGER NOT NULL,
                    total_price INTEGER NOT NULL,
                    description TEXT,
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                    FOREIGN KEY(product_id) REFERENCES products(id)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_no TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    party_id INTEGER NOT NULL,
                    total_amount INTEGER DEFAULT 0,
                    discount INTEGER DEFAULT 0,
                    tax INTEGER DEFAULT 0,
                    net_amount INTEGER DEFAULT 0,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    company_id INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(party_id) REFERENCES parties(id)
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS purchase_order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price INTEGER NOT NULL,
                    total_price INTEGER NOT NULL,
                    description TEXT,
                    FOREIGN KEY(order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                    FOREIGN KEY(product_id) REFERENCES products(id)
                )
            ''')

            # ============================================================
            # ========== جداول تنظیمات و کاربران ==========
            # ============================================================

            c.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    level TEXT DEFAULT 'viewer',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')

            # ============================================================
            # ✅ جداول پلاگین مودیان
            # ============================================================

            c.execute('''
                CREATE TABLE IF NOT EXISTS moadian_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT UNIQUE NOT NULL,
                    fiscal_id TEXT,
                    economic_code TEXT,
                    private_key_path TEXT,
                    certificate_path TEXT,
                    is_sandbox BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS moadian_invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    taxid TEXT UNIQUE NOT NULL,
                    reference_number TEXT,
                    uid TEXT,
                    invoice_type TEXT DEFAULT 'normal',
                    invoice_data TEXT,
                    status TEXT DEFAULT 'pending',
                    response_data TEXT,
                    retry_count INTEGER DEFAULT 0,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS moadian_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT,
                    endpoint TEXT,
                    request_data TEXT,
                    response_data TEXT,
                    status_code INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            c.execute('''
                CREATE TABLE IF NOT EXISTS moadian_serial (
                    customer_id TEXT PRIMARY KEY,
                    last_serial INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # ============================================================
            # ✅ ایندکس‌های کارایی
            # ============================================================

            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_vouchers_date ON vouchers(date)",
                "CREATE INDEX IF NOT EXISTS idx_vouchers_type ON vouchers(type)",
                "CREATE INDEX IF NOT EXISTS idx_vouchers_status ON vouchers(status)",
                "CREATE INDEX IF NOT EXISTS idx_voucher_items_voucher ON voucher_items(voucher_id)",
                "CREATE INDEX IF NOT EXISTS idx_voucher_items_account ON voucher_items(account_code)",
                "CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(type)",
                "CREATE INDEX IF NOT EXISTS idx_accounts_parent ON accounts(parent_code)",
                "CREATE INDEX IF NOT EXISTS idx_products_code ON products(code)",
                "CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)",
                "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)",
                "CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode)",
                "CREATE INDEX IF NOT EXISTS idx_products_warehouse ON products(warehouse_id)",
                "CREATE INDEX IF NOT EXISTS idx_warehouse_stock_product ON warehouse_stock(product_id)",
                "CREATE INDEX IF NOT EXISTS idx_warehouse_stock_warehouse ON warehouse_stock(warehouse_id)",
                "CREATE INDEX IF NOT EXISTS idx_stock_trans_date ON stock_transactions(date)",
                "CREATE INDEX IF NOT EXISTS idx_stock_trans_product ON stock_transactions(product_id)",
                "CREATE INDEX IF NOT EXISTS idx_stock_trans_type ON stock_transactions(type)",
                "CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(date)",
                "CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type)",
                "CREATE INDEX IF NOT EXISTS idx_documents_party ON documents(party_id)",
                "CREATE INDEX IF NOT EXISTS idx_document_items_doc ON document_items(document_id)",
                "CREATE INDEX IF NOT EXISTS idx_document_items_product ON document_items(product_id)",
                "CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(date)",
                "CREATE INDEX IF NOT EXISTS idx_invoices_party ON invoices(party_id)",
                "CREATE INDEX IF NOT EXISTS idx_purchase_orders_date ON purchase_orders(date)",
                "CREATE INDEX IF NOT EXISTS idx_purchase_orders_party ON purchase_orders(party_id)",
                "CREATE INDEX IF NOT EXISTS idx_payrolls_employee ON payrolls(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_payrolls_year_month ON payrolls(year, month)",
                "CREATE INDEX IF NOT EXISTS idx_payrolls_status ON payrolls(payment_status)",
                "CREATE INDEX IF NOT EXISTS idx_employees_code ON employees(code)",
                "CREATE INDEX IF NOT EXISTS idx_employees_active ON employees(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_parties_type ON parties(type)",
                "CREATE INDEX IF NOT EXISTS idx_parties_code ON parties(code)",
                "CREATE INDEX IF NOT EXISTS idx_parties_name ON parties(name)",
                "CREATE INDEX IF NOT EXISTS idx_party_trans_party ON party_transactions(party_id)",
                "CREATE INDEX IF NOT EXISTS idx_party_trans_date ON party_transactions(date)",
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                "CREATE INDEX IF NOT EXISTS idx_moadian_inv_customer ON moadian_invoices(customer_id)",
                "CREATE INDEX IF NOT EXISTS idx_moadian_inv_status ON moadian_invoices(status)",
                "CREATE INDEX IF NOT EXISTS idx_moadian_inv_taxid ON moadian_invoices(taxid)",
                "CREATE INDEX IF NOT EXISTS idx_moadian_inv_sent_at ON moadian_invoices(sent_at)",
                "CREATE INDEX IF NOT EXISTS idx_moadian_logs_customer ON moadian_logs(customer_id)",
                "CREATE INDEX IF NOT EXISTS idx_moadian_logs_created ON moadian_logs(created_at)",
            ]

            for idx_sql in indexes:
                c.execute(idx_sql)

            # ============================================================
            # ========== درج داده‌های پیش‌فرض ==========
            # ============================================================

            c.execute('INSERT OR IGNORE INTO companies (code, name) VALUES ("001", "شرکت اصلی")')

            default_accounts = [
                ('1101', 'صندوق', 'asset', None, 1),
                ('1102', 'بانک', 'asset', None, 1),
                ('1103', 'حساب‌های دریافتنی', 'asset', None, 1),
                ('1104', 'موجودی کالا', 'asset', None, 1),
                ('2101', 'حساب‌های پرداختنی', 'liability', None, 1),
                ('3101', 'سرمایه', 'equity', None, 1),
                ('4101', 'فروش کالا', 'income', None, 1),
                ('5101', 'خرید کالا', 'expense', None, 1),
                ('5102', 'هزینه حقوق', 'expense', None, 1),
            ]
            for acc in default_accounts:
                c.execute(
                    'INSERT OR IGNORE INTO accounts (code, name, type, parent_code, is_active) VALUES (?, ?, ?, ?, ?)',
                    acc
                )

            default_settings = [
                ('company_name', 'شرکت حسابداری پارسه'),
                ('currency', 'ریال'),
                ('tax_rate', '10'),
                ('date_system', 'شمسی'),
                ('valuation_method', 'simple'),
            ]
            for key, value in default_settings:
                c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))

            c.execute('''
                INSERT OR IGNORE INTO payroll_settings
                (year, daily_minimum_wage, base_seniority_pay, child_allowance_per_child,
                 housing_allowance, meal_allowance)
                VALUES (1404, 2650000, 2100000, 15000000, 15000000, 14000000)
            ''')

            default_payroll_items = [
                ('OVERTIME', 'اضافه کاری', 'percent', 1.5, 'برابر', 'benefit'),
                ('NIGHT', 'شب کاری', 'percent', 0.35, 'درصد', 'benefit'),
                ('FRIDAY', 'جمعه کاری', 'percent', 1.5, 'برابر', 'benefit'),
                ('SHIFT', 'نوبت کاری', 'percent', 0.1, 'درصد', 'benefit'),
                ('CHILD', 'حق اولاد', 'fixed', 0, 'ریال', 'benefit'),
                ('HOUSING', 'حق مسکن', 'fixed', 0, 'ریال', 'benefit'),
                ('MEAL', 'بن کارگری', 'fixed', 0, 'ریال', 'benefit'),
                ('SENIORITY', 'پایه سنوات', 'fixed', 0, 'ریال', 'benefit'),
                ('SPOUSE', 'حق همسر', 'fixed', 0, 'ریال', 'benefit'),
                ('RESPONSIBILITY', 'حق مسئولیت', 'fixed', 0, 'ریال', 'benefit'),
                ('BONUS', 'پاداش', 'fixed', 0, 'ریال', 'benefit'),
                ('MISSION', 'حق ماموریت', 'fixed', 0, 'ریال', 'benefit'),
                ('INSURANCE', 'بیمه سهم کارمند', 'percent', 0.07, 'درصد', 'deduction'),
                ('TAX', 'مالیات بر درآمد', 'percent', 0.1, 'درصد', 'deduction'),
                ('LOAN', 'قسط وام', 'fixed', 0, 'ریال', 'deduction'),
                ('ADVANCE', 'مساعده', 'fixed', 0, 'ریال', 'deduction'),
                ('DEDUCTION', 'سایر کسورات', 'fixed', 0, 'ریال', 'deduction'),
                ('PENALTY', 'جریمه', 'fixed', 0, 'ریال', 'deduction'),
            ]
            for item in default_payroll_items:
                c.execute('''
                    INSERT OR IGNORE INTO payroll_items (code, name, type, value, unit, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', item)

            default_parties = [
                ('CUST00001', 'مشتری نقدی', None, None, None, None, None, None, None, 'customer'),
                ('SUPP00001', 'تأمین‌کننده نمونه', None, None, None, None, None, None, None, 'supplier'),
            ]
            for party in default_parties:
                c.execute('''
                    INSERT OR IGNORE INTO parties
                    (code, name, company, phone, mobile, email, address, economic_code, national_id, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', party)

            c.execute('''
                INSERT OR IGNORE INTO products (code, name, unit, purchase_price, sale_price)
                VALUES ("KALA001", "کالای نمونه", "عدد", 0, 0)
            ''')

            c.execute('''
                INSERT OR IGNORE INTO warehouses (code, name, is_default, is_active)
                VALUES ('WH-001', 'انبار اصلی', 1, 1)
            ''')

            conn.commit()

            print(f"✅ دیتابیس v6.1 آماده است - مسیر: {DB_NAME}")
            print(f"📅 سیستم تاریخ: {DateConverter.get_date_system()}")
            print(f"✅ {len(indexes)} ایندکس ایجاد/بررسی شد")


# ============================================================
# ========== کلاس‌های کمکی ==========
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


class InventoryHelper:
    """کلاس کمکی برای عملیات انبار"""

    @staticmethod
    def update_stock(product_id: int, quantity: float, transaction_type: str):
        with get_db(timeout=10.0) as conn:
            c = conn.cursor()
            if transaction_type == 'in':
                c.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (quantity, product_id))
            else:
                c.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (quantity, product_id))

    @staticmethod
    def get_low_stock_products() -> List:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM products
                WHERE stock <= min_stock AND min_stock > 0
                ORDER BY stock ASC
            ''')
            return c.fetchall()

    @staticmethod
    def get_warehouse_stock(product_id: int, warehouse_id: int = None) -> float:
        with get_db() as conn:
            c = conn.cursor()
            if warehouse_id:
                c.execute(
                    "SELECT quantity FROM warehouse_stock WHERE product_id = ? AND warehouse_id = ?",
                    [product_id, warehouse_id]
                )
            else:
                c.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM warehouse_stock WHERE product_id = ?",
                    [product_id]
                )
            row = c.fetchone()
            return row[0] if row else 0

    @staticmethod
    def update_warehouse_stock(product_id: int, warehouse_id: int, quantity: float, operation: str = 'add'):
        """
        بروزرسانی موجودی انبار

        Args:
            product_id: شناسه محصول
            warehouse_id: شناسه انبار
            quantity: مقدار (همیشه مثبت)
            operation: 'set' | 'add' | 'subtract'
        """
        with get_db() as conn:
            c = conn.cursor()
            if operation == 'set':
                c.execute('''
                    INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(product_id, warehouse_id) DO UPDATE SET
                        quantity = ?,
                        updated_at = CURRENT_TIMESTAMP
                ''', [product_id, warehouse_id, quantity, quantity])
            elif operation == 'add':
                c.execute('''
                    INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(product_id, warehouse_id) DO UPDATE SET
                        quantity = quantity + ?,
                        updated_at = CURRENT_TIMESTAMP
                ''', [product_id, warehouse_id, quantity, quantity])
            elif operation == 'subtract':
                # ✅ رفع باگ: quantity مثبت، ولی تو VALUES مقدار اولیه 0 و بعد subtract
                c.execute('''
                    INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, updated_at)
                    VALUES (?, ?, 0, CURRENT_TIMESTAMP)
                    ON CONFLICT(product_id, warehouse_id) DO UPDATE SET
                        quantity = MAX(0, quantity - ?),
                        updated_at = CURRENT_TIMESTAMP
                ''', [product_id, warehouse_id, quantity])

    @staticmethod
    def get_total_stock(product_id: int) -> float:
        """مجموع موجودی محصول در همه انبارها"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM warehouse_stock WHERE product_id = ?",
                [product_id]
            )
            row = c.fetchone()
            return float(row[0]) if row and row[0] else 0


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
            print(f"⚠️ خطا در خواندن محدودیت‌ها: {e}")
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

    @classmethod
    def get_remaining(cls, customer_name: str, module_name: str) -> int:
        limit = cls.get_module_limit(customer_name, module_name)
        if limit == 0:
            return -1
        current = cls.get_current_count(module_name)
        return max(0, limit - current)


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


class PartyHelper:
    """کلاس کمکی برای اشخاص"""

    @staticmethod
    def get_party_balance(party_id: int) -> int:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT
                    COALESCE(SUM(CASE WHEN type='debit' THEN amount ELSE 0 END), 0) as total_debit,
                    COALESCE(SUM(CASE WHEN type='credit' THEN amount ELSE 0 END), 0) as total_credit
                FROM party_transactions
                WHERE party_id = ?
            ''', [party_id])
            row = c.fetchone()
            return (row['total_debit'] or 0) - (row['total_credit'] or 0)


class DocumentHelper:
    """کلاس کمکی برای اسناد"""

    @staticmethod
    def get_next_doc_no(doc_type: str) -> str:
        with get_db() as conn:
            c = conn.cursor()
            prefix = "SAL" if doc_type == 'sales' else "PUR"
            c.execute(
                f"SELECT MAX(CAST(SUBSTR(doc_no, 4) AS INTEGER)) FROM documents WHERE doc_no LIKE '{prefix}%'"
            )
            max_no = c.fetchone()[0]
            return f"{prefix}{(max_no or 0) + 1:06d}"

    @staticmethod
    def _save_document(doc_type: str, party_id: int, date: str, items: List[Dict],
                       discount: int, tax_rate: float, description: str = "") -> str:
        """ذخیره سند با استفاده از RETURNING (سازگار با SQLite 3.35+)"""
        with get_db(timeout=30.0) as conn:
            c = conn.cursor()

            doc_no = DocumentHelper.get_next_doc_no(doc_type)
            total_amount = sum(item['total_price'] for item in items)
            tax = int(total_amount * tax_rate / 100)
            net_amount = total_amount - discount + tax
            db_date = DateConverter.for_db(date)

            c.execute('''
                INSERT INTO documents
                (doc_no, doc_type, date, party_id, total_amount, discount, tax, net_amount, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            ''', (doc_no, doc_type, db_date, party_id, total_amount, discount, tax, net_amount, description))

            row = c.fetchone()
            doc_id = row['id'] if row else None

            if not doc_id:
                raise RuntimeError("خطا در دریافت شناسه سند")

            for item in items:
                c.execute('''
                    INSERT INTO document_items
                    (document_id, product_id, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (doc_id, item['product_id'], item['quantity'], item['unit_price'], item['total_price']))

                if doc_type == 'sales':
                    c.execute(
                        'UPDATE products SET stock = stock - ? WHERE id = ?',
                        (item['quantity'], item['product_id'])
                    )
                else:
                    c.execute(
                        'UPDATE products SET stock = stock + ? WHERE id = ?',
                        (item['quantity'], item['product_id'])
                    )

            print(f"✅ سند {doc_no} ثبت شد")
            return doc_no

    @staticmethod
    def create_document(doc_type: str, party_id: int, date: str, items: List[Dict],
                        discount: int, tax_rate: float, description: str = "") -> str:
        return execute_with_retry(
            DocumentHelper._save_document,
            doc_type, party_id, date, items, discount, tax_rate, description,
            max_retries=5,
            delay=0.5
        )


# ============================================================
# ========== توابع کمکی ==========
# ============================================================

def execute_with_retry(func, *args, max_retries: int = 3, delay: float = 0.5, **kwargs):
    """اجرای تابع با تلاش مجدد در صورت قفل دیتابیس"""
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
    print(f"📦 نسخه SQLite: {sqlite3.sqlite_version}")
    DatabaseManager.init_db()
    print("\n" + "=" * 60)
    print("✅ دیتابیس ImanAccount v6.1 ساخته شد!")
    print("=" * 60)
    print(f"📁 مسیر: {DB_NAME}")
    print(f"📅 سیستم تاریخ: {DateConverter.get_date_system()}")
    print("=" * 60)
