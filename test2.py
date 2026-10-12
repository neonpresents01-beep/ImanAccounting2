# fix_keys.py
# ============================================================
# ساخت کلیدها به صورت دستی
# ============================================================

import os
import sys
from pathlib import Path

# تنظیم متغیر محیطی قبل از import
os.environ['IMANACCOUNT_KEY_PASSWORD'] = 'MySellerKey@2025#ImanAI'

# Import
sys.path.insert(0, str(Path(__file__).parent))

# ============================================================
# پاک کردن کلیدهای قدیمی
# ============================================================
import shutil

keys_dir = Path(os.environ.get('APPDATA', Path.home())) / "ImanAccount" / ".keys"

if keys_dir.exists():
    print(f"🗑️ حذف کلیدهای قدیمی: {keys_dir}")
    shutil.rmtree(keys_dir)

keys_dir.mkdir(parents=True, exist_ok=True)

# ============================================================
# حالا LicenseCore رو با is_seller=True بساز
# ============================================================
from license_core import LicenseCore

print("\n🔑 تولید کلیدهای فروشنده...")

# ایجاد نمونه به عنوان فروشنده
core = LicenseCore(is_seller=True)

print("\n✅ کلیدها ساخته شدند!")
print(f"   📁 مسیر: {keys_dir}")

# نمایش فایل‌ها
for f in keys_dir.iterdir():
    print(f"   📄 {f.name} ({f.stat().st_size:,} بایت)")

# ============================================================
# تست
# ============================================================
print("\n🧪 تست تولید لایسنس...")

try:
    lic = core.generate_license(
        customer_name="تست توسعه",
        expire_days=30
    )
    print(f"   ✅ لایسنس تولید شد")
    print(f"   🔑 کلید: {lic['formatted'][:50]}...")
    
    # تست بررسی
    result = core.verify_license(lic['license_key'])
    print(f"   ✅ بررسی: {result['message']}")
    print(f"   ⏰ روزهای باقیمانده: {result['days_left']}")
    
    # ذخیره
    core.save_license(lic['license_key'])
    print(f"   💾 لایسنس ذخیره شد")
    
except Exception as e:
    print(f"   ❌ خطا: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ حالا می‌تونی برنامه رو اجرا کنی:")
print("   python main2.py")
print("=" * 60)
