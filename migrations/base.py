# migrations/base.py
# ============================================================
# Migration های پایه — جداول هسته
# ============================================================
# شامل:
# - companies
# - settings
# - users
# - accounts
# - vouchers / voucher_items
# ============================================================

import logging
from migration_registry import get_migration_registry

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Migration 1: جداول هسته
# ═══════════════════════════════════════════════════════════

def _migration_core_tables(conn):
    """ساخت جداول هسته (بدون وابستگی به ماژول‌های دیگر)"""
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
    
    # ─── ایندکس‌ها ───
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


# ═══════════════════════════════════════════════════════════
# Migration 2: داده‌های پیش‌فرض هسته
# ═══════════════════════════════════════════════════════════

def _migration_core_defaults(conn):
    """درج داده‌های پیش‌فرض هسته"""
    c = conn.cursor()
    
    # ─── شرکت ───
    c.execute('INSERT OR IGNORE INTO companies (code, name) VALUES ("001", "شرکت اصلی")')
    
    # ─── حساب‌های پیش‌فرض ───
    default_accounts = [
        ('1101', 'صندوق', 'asset', None, 1),
        ('1102', 'بانک', 'asset', None, 1),
        ('1103', 'حساب‌های دریافتنی', 'asset', None, 1),
        ('1104', 'موجودی کالا', 'asset', None, 1),
        ('1105', 'پیش‌پرداخت‌ها', 'asset', None, 1),
        ('2101', 'حساب‌های پرداختنی', 'liability', None, 1),
        ('2102', 'وام‌ها', 'liability', None, 1),
        ('3101', 'سرمایه', 'equity', None, 1),
        ('3102', 'برداشت‌ها', 'equity', None, 1),
        ('4101', 'فروش کالا', 'income', None, 1),
        ('4102', 'سود بانکی', 'income', None, 1),
        ('4103', 'تخفیف دریافتی', 'income', None, 1),
        ('4104', 'درآمدهای متفرقه', 'income', None, 1),
        ('5101', 'خرید کالا', 'expense', None, 1),
        ('5102', 'حقوق و دستمزد', 'expense', None, 1),
        ('5103', 'کارمزد بانکی', 'expense', None, 1),
        ('5104', 'اجاره', 'expense', None, 1),
        ('5105', 'آب، برق، گاز', 'expense', None, 1),
        ('5106', 'تخفیف داده شده', 'expense', None, 1),
        ('5109', 'سایر هزینه‌ها', 'expense', None, 1),
    ]
    for acc in default_accounts:
        c.execute(
            'INSERT OR IGNORE INTO accounts (code, name, type, parent_code, is_active) '
            'VALUES (?, ?, ?, ?, ?)',
            acc
        )
    
    # ─── تنظیمات پیش‌فرض ───
    default_settings = [
        ('company_name', 'شرکت حسابداری پارسه'),
        ('currency', 'ریال'),
        ('tax_rate', '10'),
        ('date_system', 'شمسی'),
        ('valuation_method', 'simple'),
    ]
    for key, value in default_settings:
        c.execute(
            'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
            (key, value)
        )


# ═══════════════════════════════════════════════════════════
# ثبت Migration ها
# ═══════════════════════════════════════════════════════════

def register_migrations():
    """ثبت Migration های پایه"""
    registry = get_migration_registry()
    
    registry.register(
        name='core_tables',
        func=_migration_core_tables,
        order=10,
        description='جداول هسته (companies, settings, users, accounts, vouchers)',
    )
    
    registry.register(
        name='core_defaults',
        func=_migration_core_defaults,
        order=20,
        description='داده‌های پیش‌فرض هسته',
        dependencies=['core_tables'],
    )


# اجرای ثبت در زمان import
register_migrations()
