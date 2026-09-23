# fix_utils_imports.py
# حذف تمام ارجاعات به utils از پروژه

import os
import re
from pathlib import Path


def main():
    root = Path(__file__).parent.resolve()
    
    print("=" * 70)
    print("🔧 حذف ارجاعات utils")
    print("=" * 70)
    
    # ماژول‌های منتقل شده
    MODULES = [
        'error_handler', 'shamsi_date', 'screen_utils', 'path_utils',
        'date_utils', 'dialog_utils', 'file_utils', 'global_date',
    ]
    
    # پوشه‌های نادیده
    SKIP_DIRS = {
        '__pycache__', '.git', 'venv', '.venv', 'build', 'dist',
        'node_modules', '.idea', '.vscode', 'backups', 'temp', 'logs',
        'utils'  # اگه هست، نادیده بگیر
    }
    
    changed_files = []
    
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            
            filepath = Path(dirpath) / filename
            
            # از فایل‌های pycache صرف‌نظر
            if '__pycache__' in str(filepath):
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original = content
                
                # ===== اصلاح importها =====
                for mod in MODULES:
                    # from utils.xxx import YYY → from xxx import YYY
                    content = re.sub(
                        rf'from\s+utils\.{mod}\s+import',
                        f'from {mod} import',
                        content
                    )
                    
                    # from utils.xxx import (multi-line)
                    content = re.sub(
                        rf'from\s+utils\.{mod}\s+import\s+\(',
                        f'from {mod} import (',
                        content
                    )
                    
                    # import utils.xxx as YYY → import xxx as YYY
                    content = re.sub(
                        rf'import\s+utils\.{mod}\s+as',
                        f'import {mod} as',
                        content
                    )
                    
                    # import utils.xxx → import xxx
                    content = re.sub(
                        rf'^import\s+utils\.{mod}\b',
                        f'import {mod}',
                        content,
                        flags=re.MULTILINE
                    )
                    
                    # from utils import xxx → from xxx import *
                    content = re.sub(
                        rf'from\s+utils\s+import\s+{mod}\b',
                        f'from {mod} import *',
                        content
                    )
                
                # ===== حذف کامل from utils import * =====
                content = re.sub(
                    r'^from\s+utils\s+import\s+\*\s*$',
                    '# from utils import *  # حذف شد',
                    content,
                    flags=re.MULTILINE
                )
                
                # ===== حذف import utils =====
                content = re.sub(
                    r'^import\s+utils\s*$',
                    '# import utils  # حذف شد',
                    content,
                    flags=re.MULTILINE
                )
                
                if content != original:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    rel = filepath.relative_to(root)
                    changed_files.append(rel)
                    print(f"   ✅ {rel}")
            
            except Exception as e:
                print(f"   ❌ {filepath}: {e}")
    
    print(f"\n📊 {len(changed_files)} فایل اصلاح شد")
    
    # ============================================================
    # چک نهایی
    # ============================================================
    print("\n🔍 چک نهایی برای باقی‌مانده utils:")
    
    remaining = []
    
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            
            filepath = Path(dirpath) / filename
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # فقط importهای فعال رو چک کن
                if re.search(r'^\s*from\s+utils[\.\s]', content, re.MULTILINE):
                    rel = filepath.relative_to(root)
                    remaining.append(rel)
            except Exception:
                pass
    
    if remaining:
        print(f"\n⚠️ {len(remaining)} فایل هنوز utils دارن:")
        for f in remaining:
            print(f"   ⚠️ {f}")
    else:
        print("   ✅ همه چیز تمیزه!")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
