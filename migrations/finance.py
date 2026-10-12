# migrations/finance.py
# ============================================================
# Migration های امور مالی
# ============================================================
# شامل:
# - banks (بانک‌ها)
# - cash_boxes (صندوق‌ها)
# - finance_transactions (تراکنش‌های مالی)
# - checks (چک‌ها)
# ============================================================

import logging
from migration_registry import get_migration_registry

logger = logging.getLogger(__name__)


def _migration_finance_tables(conn):
    """ساخت جداول امور مالی"""
    c = conn.cursor()
    
    # ─── banks ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            account_number TEXT,
            card_number TEXT,
            iban TEXT,
            branch TEXT,
            account_code TEXT DEFAULT '1102',
            balance INTEGER DEFAULT 0,
            company_id INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ─── cash_boxes ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS cash_boxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            location TEXT,
            account_code TEXT DEFAULT '1101',
            balance INTEGER DEFAULT 0,
            company_id INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ─── finance_transactions ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS finance_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_no TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            from_account_type TEXT,
            from_account_id INTEGER,
            to_account_type TEXT,
            to_account_id INTEGER,
            party_id INTEGER,
            amount INTEGER NOT NULL,
            fee INTEGER DEFAULT 0,
            discount INTEGER DEFAULT 0,
            description TEXT,
            reference_no TEXT,
            voucher_id INTEGER,
            company_id INTEGER DEFAULT 1,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(voucher_id) REFERENCES vouchers(id),
            FOREIGN KEY(party_id) REFERENCES parties(id)
        )
    ''')
    
    # ─── checks ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_number TEXT UNIQUE NOT NULL,
            bank_name TEXT,
            branch TEXT,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            issue_date TEXT,
            due_date TEXT NOT NULL,
            party_id INTEGER,
            account_id INTEGER,
            status TEXT DEFAULT 'pending',
            description TEXT,
            notes TEXT,
            reminder_sent BOOLEAN DEFAULT 0,
            transaction_id INTEGER,
            voucher_id INTEGER,
            company_id INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(party_id) REFERENCES parties(id),
            FOREIGN KEY(account_id) REFERENCES banks(id),
            FOREIGN KEY(transaction_id) REFERENCES finance_transactions(id)
        )
    ''')
    
    # ─── ایندکس‌ها ───
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_banks_code ON banks(code)",
        "CREATE INDEX IF NOT EXISTS idx_banks_active ON banks(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_cash_code ON cash_boxes(code)",
        "CREATE INDEX IF NOT EXISTS idx_cash_active ON cash_boxes(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_fin_date ON finance_transactions(date)",
        "CREATE INDEX IF NOT EXISTS idx_fin_type ON finance_transactions(type)",
        "CREATE INDEX IF NOT EXISTS idx_fin_party ON finance_transactions(party_id)",
        "CREATE INDEX IF NOT EXISTS idx_fin_voucher ON finance_transactions(voucher_id)",
        "CREATE INDEX IF NOT EXISTS idx_fin_txn_no ON finance_transactions(transaction_no)",
        "CREATE INDEX IF NOT EXISTS idx_checks_due ON checks(due_date)",
        "CREATE INDEX IF NOT EXISTS idx_checks_status ON checks(status)",
        "CREATE INDEX IF NOT EXISTS idx_checks_type ON checks(type)",
        "CREATE INDEX IF NOT EXISTS idx_checks_party ON checks(party_id)",
    ]:
        c.execute(idx)


def _migration_finance_defaults(conn):
    """درج داده‌های پیش‌فرض امور مالی"""
    c = conn.cursor()
    
    c.execute('''
        INSERT OR IGNORE INTO banks (code, name, balance, is_active)
        VALUES ('BNK001', 'بانک اصلی', 0, 1)
    ''')
    
    c.execute('''
        INSERT OR IGNORE INTO cash_boxes (code, name, balance, is_active)
        VALUES ('CSH001', 'صندوق اصلی', 0, 1)
    ''')


def register_migrations():
    registry = get_migration_registry()
    
    registry.register(
        name='finance_tables',
        func=_migration_finance_tables,
        order=400,
        description='جداول امور مالی (banks, cash_boxes, finance_transactions, checks)',
        dependencies=['parties_tables'],
    )
    
    registry.register(
        name='finance_defaults',
        func=_migration_finance_defaults,
        order=410,
        description='داده‌های پیش‌فرض امور مالی',
        dependencies=['finance_tables'],
    )


register_migrations()
