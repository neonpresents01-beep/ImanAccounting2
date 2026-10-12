# test_import.py
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

print(f"PROJECT_ROOT: {_PROJECT_ROOT}")
print(f"sys.path[0]: {sys.path[0]}")

# چک وجود فایل
mr_path = _PROJECT_ROOT / "menu_registry.py"
print(f"\nمنوی رجیستری در: {mr_path}")
print(f"وجود داره؟ {mr_path.exists()}")

# تلاش برای import
try:
    import menu_registry
    print(f"\n✅ menu_registry ایمپورت شد: {menu_registry.__file__}")
except ImportError as e:
    print(f"\n❌ خطا: {e}")

# لیست فایل‌های پوشه
print("\n📁 فایل‌های .py در پوشه پروژه:")
for f in sorted(_PROJECT_ROOT.glob("*.py")):
    print(f"   • {f.name}")
