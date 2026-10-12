# migrations/parties.py
# ============================================================
# Migration های اشخاص
# ============================================================
# شامل:
# - parties (اشخاص)
# - party_groups (گروه‌ها)
# - party_contacts (مخاطبین)
# - party_notes (یادداشت‌ها)
# - party_attachments (پیوست‌ها)
# - party_transactions (تراکنش‌ها)
# ============================================================

import logging
from migration_registry import get_migration_registry

logger = logging.getLogger(__name__)


def _migration_parties_tables(conn):
    """ساخت جداول اشخاص"""
    c = conn.cursor()
    
    # ─── parties ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            
            -- اطلاعات پایه
            company TEXT,
            national_id TEXT,
            economic_code TEXT,
            reg_number TEXT,
            
            -- تماس
            phone TEXT,
            mobile TEXT,
            fax TEXT,
            email TEXT,
            website TEXT,
            address TEXT,
            postal_code TEXT,
            
            -- بانکی
            shaba TEXT,
            card_number TEXT,
            account_number TEXT,
            bank_name TEXT,
            branch TEXT,
            
            -- گروه‌بندی
            group_name TEXT,
            category TEXT,
            tags TEXT,
            
            -- اعتبار و پرداخت
            credit_limit INTEGER DEFAULT 0,
            payment_terms TEXT DEFAULT 'نقدی',
            default_discount REAL DEFAULT 0,
            
            -- مالی
            balance INTEGER DEFAULT 0,
            opening_balance INTEGER DEFAULT 0,
            
            -- یادداشت
            notes TEXT,
            
            -- تاریخ‌ها
            birth_date TEXT,
            last_transaction_date TEXT,
            
            -- متادیتا
            is_active INTEGER DEFAULT 1,
            company_id INTEGER DEFAULT 1,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ─── party_groups ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS party_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            party_type TEXT,
            color TEXT DEFAULT '#3498db',
            icon TEXT DEFAULT '📁',
            default_discount REAL DEFAULT 0,
            default_credit_limit INTEGER DEFAULT 0,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ─── party_contacts ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS party_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position TEXT,
            phone TEXT,
            mobile TEXT,
            email TEXT,
            is_primary INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(party_id) REFERENCES parties(id) ON DELETE CASCADE
        )
    ''')
    
    # ─── party_notes ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS party_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER NOT NULL,
            note_text TEXT NOT NULL,
            note_type TEXT DEFAULT 'general',
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(party_id) REFERENCES parties(id) ON DELETE CASCADE
        )
    ''')
    
    # ─── party_attachments ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS party_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER DEFAULT 0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(party_id) REFERENCES parties(id) ON DELETE CASCADE
        )
    ''')
    
    # ─── party_transactions ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS party_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT,
            amount INTEGER NOT NULL,
            description TEXT,
            voucher_id INTEGER,
            FOREIGN KEY(party_id) REFERENCES parties(id) ON DELETE CASCADE
        )
    ''')
    
    # ─── ایندکس‌ها ───
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_parties_type ON parties(type)",
        "CREATE INDEX IF NOT EXISTS idx_parties_code ON parties(code)",
        "CREATE INDEX IF NOT EXISTS idx_parties_name ON parties(name)",
        "CREATE INDEX IF NOT EXISTS idx_parties_group ON parties(group_name)",
        "CREATE INDEX IF NOT EXISTS idx_parties_active ON parties(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_parties_mobile ON parties(mobile)",
        "CREATE INDEX IF NOT EXISTS idx_party_groups_type ON party_groups(party_type)",
        "CREATE INDEX IF NOT EXISTS idx_party_contacts_party ON party_contacts(party_id)",
        "CREATE INDEX IF NOT EXISTS idx_party_notes_party ON party_notes(party_id)",
        "CREATE INDEX IF NOT EXISTS idx_party_attach_party ON party_attachments(party_id)",
        "CREATE INDEX IF NOT EXISTS idx_party_trans_party ON party_transactions(party_id)",
        "CREATE INDEX IF NOT EXISTS idx_party_trans_date ON party_transactions(date)",
    ]:
        c.execute(idx)


def _migration_parties_defaults(conn):
    """درج گروه‌های پیش‌فرض اشخاص"""
    c = conn.cursor()
    
    default_groups = [
        ('عادی', 'both', '#3498db', '👤', 0, 0),
        ('VIP', 'customer', '#e74c3c', '⭐', 5, 100000000),
        ('عمده', 'customer', '#27ae60', '🏢', 10, 500000000),
        ('خرده', 'customer', '#f39c12', '🛒', 0, 10000000),
        ('دولتی', 'customer', '#9b59b6', '🏛️', 0, 0),
        ('تولیدی', 'supplier', '#16a085', '🏭', 0, 0),
        ('بازرگانی', 'supplier', '#3498db', '📦', 0, 0),
    ]
    for group in default_groups:
        c.execute('''
            INSERT OR IGNORE INTO party_groups 
            (name, party_type, color, icon, default_discount, default_credit_limit)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', group)
    
    # ─── اشخاص نمونه ───
    sample_parties = [
        ('CUST00001', 'مشتری نمونه', 'customer', 'عادی'),
        ('SUPP00001', 'تأمین‌کننده نمونه', 'supplier', 'بازرگانی'),
    ]
    for code, name, ptype, group in sample_parties:
        c.execute('''
            INSERT OR IGNORE INTO parties 
            (code, name, type, group_name, balance, is_active)
            VALUES (?, ?, ?, ?, 0, 1)
        ''', (code, name, ptype, group))


# ═══════════════════════════════════════════════════════════
# ثبت Migration ها
# ═══════════════════════════════════════════════════════════

def register_migrations():
    registry = get_migration_registry()
    
    registry.register(
        name='parties_tables',
        func=_migration_parties_tables,
        order=100,
        description='جداول اشخاص (parties, party_groups, ...)',
        dependencies=['core_tables'],
    )
    
    registry.register(
        name='parties_defaults',
        func=_migration_parties_defaults,
        order=110,
        description='داده‌های پیش‌فرض اشخاص',
        dependencies=['parties_tables'],
    )


register_migrations()
