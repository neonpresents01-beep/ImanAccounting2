# migration_registry.py
# ============================================================
# رجیستری مرکزی Migration ها — نسخه 1.0
# ============================================================
# این فایل مستقل از database.py و ویجت‌هاست.
# Migration ها از پوشه migrations/ ثبت می‌شوند.
# ============================================================

import logging
from typing import Callable, List, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class MigrationRegistry:
    """
    رجیستری مرکزی Migration ها.
    
    هر Migration یک تابع (conn) است که Schema را تغییر می‌دهد.
    Migration ها به ترتیب order اجرا می‌شوند و در جدول
    migration_history ثبت می‌شوند تا دوباره اجرا نشوند.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if MigrationRegistry._initialized:
            return
        MigrationRegistry._initialized = True
        self._migrations: List[dict] = []
        self._registered_names: set = set()
        logger.info("📋 MigrationRegistry راه‌اندازی شد")
    
    # ═══════════════════════════════════════════════════════
    # Register
    # ═══════════════════════════════════════════════════════
    
    def register(self, name: str, func: Callable,
                 order: int = 100, description: str = "",
                 dependencies: List[str] = None):
        """
        ثبت یک Migration.
        
        Args:
            name: نام یونیک (مثلاً 'inventory_count_tables')
            func: تابع(conn) که Migration را اجرا می‌کند
            order: ترتیب اجرا (کمتر = زودتر)
            description: توضیح کوتاه
            dependencies: لیست نام Migration هایی که باید قبل اجرا شوند
        """
        if name in self._registered_names:
            logger.debug(f"⚠️ Migration '{name}' قبلاً ثبت شده")
            return
        
        self._migrations.append({
            'name': name,
            'func': func,
            'order': order,
            'description': description,
            'dependencies': dependencies or [],
        })
        self._registered_names.add(name)
        logger.debug(f"✅ Migration ثبت: {name} (order={order})")
    
    # ═══════════════════════════════════════════════════════
    # Run
    # ═══════════════════════════════════════════════════════
    
    def run_all(self, conn) -> Dict[str, List]:
        """
        اجرای همه Migration ها با درنظر گرفتن dependencies.
        
        Returns:
            {
                'executed': [...names...],
                'skipped': [...names...],
                'failed': [(name, error), ...],
            }
        """
        self._ensure_history_table(conn)
        
        # مرتب‌سازی بر اساس order
        sorted_migrations = sorted(self._migrations, key=lambda m: m['order'])
        
        executed: List[str] = []
        skipped: List[str] = []
        failed: List[Tuple[str, str]] = []
        
        for migration in sorted_migrations:
            name = migration['name']
            
            # ─── چک dependencies ───
            deps = migration['dependencies']
            missing_deps = []
            
            for dep in deps:
                # dependency باید قبلاً اجرا شده باشد یا در این run اجرا شده باشد
                if dep not in executed and not self._is_executed(conn, dep):
                    missing_deps.append(dep)
            
            if missing_deps:
                logger.warning(
                    f"⚠️ Dependency رد نشد برای '{name}': "
                    f"{', '.join(missing_deps)}"
                )
                failed.append((name, f"dependencies not satisfied: {missing_deps}"))
                continue
            
            # ─── چک اجرای قبلی ───
            if self._is_executed(conn, name):
                skipped.append(name)
                continue
            
            # ─── اجرا ───
            logger.info(f"🔄 اجرای Migration: {name}")
            
            try:
                migration['func'](conn)
                self._mark_executed(conn, name, migration.get('description', ''))
                executed.append(name)
                logger.info(f"   ✅ کامل شد: {name}")
            except Exception as e:
                logger.error(f"   ❌ خطا در {name}: {e}", exc_info=True)
                failed.append((name, str(e)))
                # ادامه می‌دهیم — شاید Migration بعدی مستقل باشد
        
        logger.info(
            f"📊 نتیجه Migration ها: "
            f"{len(executed)} اجرا، "
            f"{len(skipped)} رد شده، "
            f"{len(failed)} خطا"
        )
        
        return {
            'executed': executed,
            'skipped': skipped,
            'failed': failed,
        }
    
    # ═══════════════════════════════════════════════════════
    # History
    # ═══════════════════════════════════════════════════════
    
    def _ensure_history_table(self, conn):
        """ساخت جدول migration_history اگر وجود نداشته باشد"""
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _is_executed(self, conn, name: str) -> bool:
        """بررسی اینکه Migration قبلاً اجرا شده یا نه"""
        c = conn.cursor()
        c.execute("SELECT id FROM migration_history WHERE name = ?", [name])
        return c.fetchone() is not None
    
    def _mark_executed(self, conn, name: str, description: str = ""):
        """ثبت اجرای Migration"""
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO migration_history (name, description)
            VALUES (?, ?)
        """, [name, description])
    
    # ═══════════════════════════════════════════════════════
    # Query / Debug
    # ═══════════════════════════════════════════════════════
    
    def list_all(self) -> List[dict]:
        """لیست همه Migration های ثبت‌شده"""
        return sorted(self._migrations, key=lambda m: m['order'])
    
    def list_executed(self, conn) -> List[dict]:
        """لیست Migration های اجراشده"""
        self._ensure_history_table(conn)
        c = conn.cursor()
        c.execute("""
            SELECT name, description, executed_at 
            FROM migration_history 
            ORDER BY id
        """)
        return [dict(row) for row in c.fetchall()]
    
    def print_structure(self):
        """چاپ ساختار Migration ها (برای دیباگ)"""
        print("\n" + "=" * 70)
        print("📋 Migration Registry Structure")
        print("=" * 70)
        
        for m in self.list_all():
            deps = f" (deps: {', '.join(m['dependencies'])})" if m['dependencies'] else ""
            print(f"   [{m['order']:>4}] {m['name']}{deps}")
            if m['description']:
                print(f"          └─ {m['description']}")
        
        print("=" * 70 + "\n")
    
    # ═══════════════════════════════════════════════════════
    # Reset (فقط برای تست)
    # ═══════════════════════════════════════════════════════
    
    def clear(self):
        """پاک کردن رجیستری (فقط برای تست)"""
        self._migrations.clear()
        self._registered_names.clear()
        logger.warning("🧹 MigrationRegistry پاک شد")


# ============================================================
# Singleton
# ============================================================

_registry_instance: Optional[MigrationRegistry] = None


def get_migration_registry() -> MigrationRegistry:
    """دریافت نمونه Singleton"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = MigrationRegistry()
    return _registry_instance


# ============================================================
# تست
# ============================================================

if __name__ == "__main__":
    import sqlite3
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    
    print("=" * 70)
    print("🧪 تست MigrationRegistry")
    print("=" * 70)
    
    # اتصال به دیتابیس موقت
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    # ثبت چند Migration نمونه
    registry = get_migration_registry()
    
    def mig1(conn):
        conn.cursor().execute("CREATE TABLE users (id INTEGER, name TEXT)")
    
    def mig2(conn):
        conn.cursor().execute("CREATE TABLE posts (id INTEGER, user_id INTEGER)")
    
    def mig3(conn):
        conn.cursor().execute("CREATE TABLE comments (id INTEGER, post_id INTEGER)")
    
    registry.register("create_users", mig1, order=100, description="جدول کاربران")
    registry.register("create_posts", mig2, order=200, description="جدول پست‌ها",
                     dependencies=["create_users"])
    registry.register("create_comments", mig3, order=300, description="جدول کامنت‌ها",
                     dependencies=["create_posts"])
    
    # اجرای اول
    print("\n▶️ اجرای اول:")
    result = registry.run_all(conn)
    print(f"   نتیجه: {result}")
    
    # اجرای دوم (باید همه skip شوند)
    print("\n▶️ اجرای دوم (باید همه skip شوند):")
    result = registry.run_all(conn)
    print(f"   نتیجه: {result}")
    
    # چاپ ساختار
    registry.print_structure()
    
    conn.close()
    print("✅ تست کامل شد")
