# migrations/documents.py
# ============================================================
# Migration های اسناد خرید و فروش
# ============================================================
# شامل:
# - documents
# - document_items
# - document_returns
# - invoices (سازگاری)
# - purchase_orders (سازگاری)
# ============================================================

import logging
from migration_registry import get_migration_registry

logger = logging.getLogger(__name__)


def _migration_document_tables(conn):
    """ساخت جداول اسناد"""
    c = conn.cursor()
    
    # ─── documents ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT UNIQUE NOT NULL,
            doc_type TEXT NOT NULL,
            date TEXT NOT NULL,
            party_id INTEGER NOT NULL,
            total_amount INTEGER DEFAULT 0,
            discount INTEGER DEFAULT 0,
            tax INTEGER DEFAULT 0,
            net_amount INTEGER DEFAULT 0,
            description TEXT,
            status TEXT DEFAULT 'pending',
            is_approved INTEGER DEFAULT 0,
            company_id INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(party_id) REFERENCES parties(id)
        )
    ''')
    
    # ─── document_items ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS document_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            unit_price INTEGER NOT NULL,
            total_price INTEGER NOT NULL,
            description TEXT,
            returned_qty REAL DEFAULT 0,
            return_doc_id INTEGER,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    
    # ─── document_returns ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS document_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_doc_id INTEGER NOT NULL,
            return_doc_id INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(original_doc_id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY(return_doc_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    ''')
    
    # ─── invoices (سازگاری) ───
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
    
    # ─── purchase_orders (سازگاری) ───
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
    
    # ─── ایندکس‌ها ───
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(date)",
        "CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type)",
        "CREATE INDEX IF NOT EXISTS idx_documents_party ON documents(party_id)",
        "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)",
        "CREATE INDEX IF NOT EXISTS idx_document_items_doc ON document_items(document_id)",
        "CREATE INDEX IF NOT EXISTS idx_document_items_product ON document_items(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_doc_returns_original ON document_returns(original_doc_id)",
        "CREATE INDEX IF NOT EXISTS idx_doc_returns_return ON document_returns(return_doc_id)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(date)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_party ON invoices(party_id)",
        "CREATE INDEX IF NOT EXISTS idx_purchase_orders_date ON purchase_orders(date)",
        "CREATE INDEX IF NOT EXISTS idx_purchase_orders_party ON purchase_orders(party_id)",
    ]:
        c.execute(idx)


def register_migrations():
    registry = get_migration_registry()
    
    registry.register(
        name='documents_tables',
        func=_migration_document_tables,
        order=300,
        description='جداول اسناد خرید و فروش',
        dependencies=['parties_tables', 'inventory_warehouse_tables'],
    )


register_migrations()
