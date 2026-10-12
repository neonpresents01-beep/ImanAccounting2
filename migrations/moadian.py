# migrations/moadian.py
# ============================================================
# Migration های مودیان
# ============================================================
# شامل:
# - moadian_settings
# - moadian_invoices
# - moadian_logs
# - moadian_serial
# - moadian_products
# ============================================================

import logging
from migration_registry import get_migration_registry

logger = logging.getLogger(__name__)


def _migration_moadian_tables(conn):
    """ساخت جداول مودیان"""
    c = conn.cursor()
    
    # ─── moadian_settings ───
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
    
    # ─── moadian_invoices ───
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
    
    # ─── moadian_logs ───
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
    
    # ─── moadian_serial ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS moadian_serial (
            customer_id TEXT PRIMARY KEY,
            last_serial INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ─── moadian_products ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS moadian_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER UNIQUE NOT NULL,
            sstid TEXT,
            sstt TEXT,
            unit_moadian TEXT DEFAULT '1627',
            vat_rate INTEGER DEFAULT 9,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    # ─── ایندکس‌ها ───
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_moadian_inv_customer ON moadian_invoices(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_moadian_inv_status ON moadian_invoices(status)",
        "CREATE INDEX IF NOT EXISTS idx_moadian_inv_taxid ON moadian_invoices(taxid)",
        "CREATE INDEX IF NOT EXISTS idx_moadian_inv_sent_at ON moadian_invoices(sent_at)",
        "CREATE INDEX IF NOT EXISTS idx_moadian_logs_customer ON moadian_logs(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_moadian_logs_created ON moadian_logs(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_moadian_products_pid ON moadian_products(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_moadian_products_sstid ON moadian_products(sstid)",
    ]:
        c.execute(idx)


def register_migrations():
    registry = get_migration_registry()
    
    registry.register(
        name='moadian_tables',
        func=_migration_moadian_tables,
        order=600,
        description='جداول مودیان (settings, invoices, logs, serial, products)',
        dependencies=['inventory_warehouse_tables'],
    )


register_migrations()
