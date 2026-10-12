# migrations/inventory.py
# ============================================================
# Migration های ماژول انبار
# ============================================================
# شامل:
# - warehouses (انبارها)
# - products (کالاها)
# - warehouse_stock (موجودی هر انبار)
# - product_serials (سریال‌نمبر)
# - stock_transactions (تراکنش‌های انبار)
# - inventory_counts (انبارگردانی)
# - inventory_count_items (اقلام انبارگردانی)
# ============================================================

import logging
from migration_registry import get_migration_registry

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Migration 1: جداول پایه انبار
# ═══════════════════════════════════════════════════════════

def _migration_warehouse_tables(conn):
    """ساخت جداول پایه انبار"""
    c = conn.cursor()
    
    # ─── warehouses ───
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
    
    # ─── products ───
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
    
    # ─── warehouse_stock ───
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
    
    # ─── product_serials ───
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
    
    # ─── stock_transactions ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS stock_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            warehouse_id INTEGER,
            from_warehouse_id INTEGER,
            to_warehouse_id INTEGER,
            type TEXT NOT NULL,
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
    
    # ─── ایندکس‌ها ───
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_products_code ON products(code)",
        "CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)",
        "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)",
        "CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode)",
        "CREATE INDEX IF NOT EXISTS idx_warehouse_stock_product ON warehouse_stock(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_warehouse_stock_warehouse ON warehouse_stock(warehouse_id)",
        "CREATE INDEX IF NOT EXISTS idx_stock_trans_date ON stock_transactions(date)",
        "CREATE INDEX IF NOT EXISTS idx_stock_trans_product ON stock_transactions(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_stock_trans_type ON stock_transactions(type)",
    ]:
        c.execute(idx)


# ═══════════════════════════════════════════════════════════
# Migration 2: جداول انبارگردانی (جدید)
# ═══════════════════════════════════════════════════════════

def _migration_inventory_count_tables(conn):
    """
    ساخت جداول انبارگردانی.
    
    inventory_counts: سند انبارگردانی (سرآیند)
    inventory_count_items: اقلام شمارش‌شده
    """
    c = conn.cursor()
    
    # ─── inventory_counts (سند انبارگردانی) ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            count_no TEXT UNIQUE NOT NULL,
            warehouse_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            description TEXT,
            total_items INTEGER DEFAULT 0,
            counted_items INTEGER DEFAULT 0,
            variance_items INTEGER DEFAULT 0,
            total_variance_value INTEGER DEFAULT 0,
            created_by TEXT,
            approved_by TEXT,
            approved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
        )
    ''')
    
    # ─── inventory_count_items (اقلام) ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_count_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            count_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            system_qty REAL DEFAULT 0,
            actual_qty REAL DEFAULT 0,
            variance REAL DEFAULT 0,
            unit_price REAL DEFAULT 0,
            variance_value REAL DEFAULT 0,
            notes TEXT,
            counted INTEGER DEFAULT 0,
            FOREIGN KEY(count_id) REFERENCES inventory_counts(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    
    # ─── ایندکس‌ها ───
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_inv_counts_warehouse ON inventory_counts(warehouse_id)",
        "CREATE INDEX IF NOT EXISTS idx_inv_counts_date ON inventory_counts(date)",
        "CREATE INDEX IF NOT EXISTS idx_inv_counts_status ON inventory_counts(status)",
        "CREATE INDEX IF NOT EXISTS idx_inv_counts_no ON inventory_counts(count_no)",
        "CREATE INDEX IF NOT EXISTS idx_inv_count_items_count ON inventory_count_items(count_id)",
        "CREATE INDEX IF NOT EXISTS idx_inv_count_items_product ON inventory_count_items(product_id)",
    ]:
        c.execute(idx)
    
    logger.info("   ✅ جداول انبارگردانی ساخته شد")


# ═══════════════════════════════════════════════════════════
# Migration 3: همگام‌سازی کالاهای قدیمی
# ═══════════════════════════════════════════════════════════

def _migration_sync_products_stock(conn):
    """
    همگام‌سازی products.stock با warehouse_stock.
    
    برای کالاهای قدیمی که فقط در products.stock موجودی داشتند
    و رکوردی در warehouse_stock نداشتند.
    """
    c = conn.cursor()
    
    # پیدا کردن انبار پیش‌فرض
    c.execute("SELECT id FROM warehouses WHERE is_default = 1 AND is_active = 1 LIMIT 1")
    row = c.fetchone()
    default_wh_id = row[0] if row else None
    
    if default_wh_id is None:
        c.execute("SELECT id FROM warehouses WHERE is_active = 1 ORDER BY id LIMIT 1")
        row = c.fetchone()
        default_wh_id = row[0] if row else None
    
    if default_wh_id is None:
        logger.warning("   ⚠️ هیچ انبار فعالی نیست — Migration رد شد")
        return
    
    # کالاهای بدون رکورد در warehouse_stock
    c.execute("""
        SELECT p.id, p.stock FROM products p
        LEFT JOIN warehouse_stock ws ON p.id = ws.product_id
        WHERE ws.id IS NULL
    """)
    
    count = 0
    for product in c.fetchall():
        c.execute("""
            INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, [product[0], default_wh_id, product[1] or 0])
        count += 1
    
    if count > 0:
        logger.info(f"   → {count} کالا به warehouse_stock منتقل شد")
    
    # همگام‌سازی نهایی
    c.execute("""
        UPDATE products 
        SET stock = (
            SELECT COALESCE(SUM(quantity), 0) 
            FROM warehouse_stock 
            WHERE product_id = products.id
        )
    """)


# ═══════════════════════════════════════════════════════════
# Migration 4: داده‌های پیش‌فرض انبار
# ═══════════════════════════════════════════════════════════

def _migration_inventory_defaults(conn):
    """درج داده‌های پیش‌فرض انبار"""
    c = conn.cursor()
    
    # ─── انبار پیش‌فرض ───
    c.execute('''
        INSERT OR IGNORE INTO warehouses (code, name, is_default, is_active)
        VALUES ('WH-001', 'انبار اصلی', 1, 1)
    ''')
    
    # ─── کالای نمونه ───
    c.execute('''
        INSERT OR IGNORE INTO products (code, name, unit, purchase_price, sale_price)
        VALUES ("KALA001", "کالای نمونه", "عدد", 0, 0)
    ''')


# ═══════════════════════════════════════════════════════════
# ثبت Migration ها
# ═══════════════════════════════════════════════════════════

def register_migrations():
    """ثبت Migration های ماژول انبار"""
    registry = get_migration_registry()
    
    registry.register(
        name='inventory_warehouse_tables',
        func=_migration_warehouse_tables,
        order=200,
        description='جداول پایه انبار (warehouses, products, warehouse_stock, ...)',
        dependencies=['core_tables'],
    )
    
    registry.register(
        name='inventory_count_tables',
        func=_migration_inventory_count_tables,
        order=210,
        description='جداول انبارگردانی (inventory_counts, inventory_count_items)',
        dependencies=['inventory_warehouse_tables'],
    )
    
    registry.register(
        name='inventory_sync_products_stock',
        func=_migration_sync_products_stock,
        order=220,
        description='همگام‌سازی products.stock با warehouse_stock',
        dependencies=['inventory_warehouse_tables'],
    )
    
    registry.register(
        name='inventory_defaults',
        func=_migration_inventory_defaults,
        order=230,
        description='داده‌های پیش‌فرض انبار',
        dependencies=['inventory_warehouse_tables'],
    )


register_migrations()
