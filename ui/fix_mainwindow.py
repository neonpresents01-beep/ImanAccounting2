# fix_main_window.py
# جایگزین سریع خط 15-25 در main_window.py

import re
from pathlib import Path

# مسیر فایل
file_path = Path(__file__).parent / "ui" / "main_window.py"

print(f"📂 فایل: {file_path}")

if not file_path.exists():
    print("❌ فایل پیدا نشد!")
    exit(1)

# خوندن
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# چک کردن
if 'from error_handler import' not in content:
    print("✅ فایل قبلاً اصلاح شده!")
    exit(0)

print("🔧 در حال اصلاح...")

# ✅ پیدا کردن بلوک import قدیمی و جایگزینی
old_pattern = r"from utils\.error_handler import \(\s*[^)]+\)"

new_import = """# مدیریت خطا — با اصلاح sys.path
import sys
from pathlib import Path

# اطمینان از مسیر پروژه
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from error_handler import (
    get_logger,
    get_error_handler,
    safe_execute,
    row_to_dict,
    ValidationError,
    PermissionError,
)"""

# جایگزینی
new_content = re.sub(old_pattern, new_import, content, count=1)

if new_content == content:
    print("⚠️ الگو پیدا نشد — شاید ساختار متفاوته")
    exit(1)

# ذخیره
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ فایل اصلاح شد!")
print("🚀 حالا تست کن: python main2.py")
