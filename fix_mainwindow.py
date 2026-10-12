# merge_utils.py
# انتقال فایل‌های utils به ریشه و حذف پوشه utils
# ============================================================

import os
import re
import shutil
from pathlib import Path


def main():
    root = Path(__file__).parent.resolve()
    utils_dir = root / "utils"
    
    print("=" * 70)
    print("🔧 ادغام utils در ریشه پروژه")
    print("=" * 70)
    
    # ============================================================
    # ۱. چک کردن
    # ============================================================
    if not utils_dir.exists():
        print("⚠️ پوشه utils وجود نداره!")
        return
    
    print(f"\n📂 پوشه utils: {utils_dir}")
    
    # ============================================================
    # ۲. انتقال فایل‌ها
    # ============================================================
    print("\n📦 انتقال فایل‌ها به ریشه:")
    
    py_files = list(utils_dir.glob("*.py"))
    py_files = [f for f in py_files if f.name != "__init__.py"]
    
    moved = []
    
    for src in py_files:
        dst = root / src.name
        
        if dst.exists():
            print(f"   ⚠️ {src.name} از قبل توی ریشه هست — بازنویسی می‌شه")
            try:
                backup = root / f"{src.name}.old"
                if backup.exists():
                    backup.unlink()
                dst.rename(backup)
            except Exception:
                pass
        
        try:
            shutil.move(str(src), str(dst))
            print(f"   ✅ {src.name}")
            moved.append(src.name)
        except Exception as e:
            print(f"   ❌ {src.name}: {e}")
    
    print(f"\n📊 {len(moved)} فایل منتقل شد")
    
    # ============================================================
    # ۳. حذف پوشه utils
    # ============================================================
    print("\n🗑️ حذف پوشه utils:")
    
    try:
        # حذف __pycache__
        cache_dir = utils_dir / "__pycache__"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        
        # حذف __init__.py
        init_file = utils_dir / "__init__.py"
        if init_file.exists():
            init_file.unlink()
        
        # حذف پوشه (اگه خالیه)
        utils_dir.rmdir()
        print(f"   ✅ پوشه utils حذف شد")
    except Exception as e:
        print(f"   ⚠️ نمی‌تونم پوشه utils رو حذف کنم: {e}")
        print(f"   ℹ️ به صورت دستی حذفش کن")
    
    # ============================================================
    # ۴. اصلاح importها در کل پروژه
    # ============================================================
    print("\n🔄 اصلاح importها:")
    
    # ماژول‌های منتقل شده
    modules = [f.replace('.py', '') for f in moved]
    
    if not modules:
        print("   ⚠️ ماژول برای اصلاح نیست")
        return
    
    print(f"   ماژول‌ها: {', '.join(modules)}")
    
    # پوشه‌های نادیده
    SKIP_DIRS = {
        '__pycache__', '.git', 'venv', '.venv', 'build', 'dist',
        'node_modules', '.idea', '.vscode', 'utils', 'backups',
        'temp', 'logs'
    }
    
    changed_files = []
    
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            
            filepath = Path(dirpath) / filename
            
            # از فایل‌های utils صرف‌نظر
            try:
                filepath.relative_to(utils_dir)
                continue
            except ValueError:
                pass
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original = content
                
                # ===== اصلاح importها =====
                for mod in modules:
                    # from utils.xxx import YYY → from xxx import YYY
                    content = re.sub(
                        rf'from\s+utils\.{mod}\s+import',
                        f'from {mod} import',
                        content
                    )
                    
                    # from utils import xxx → from xxx import *
                    content = re.sub(
                        rf'from\s+utils\s+import\s+{mod}\b',
                        f'from {mod} import *',
                        content
                    )
                
                # ===== حذف from utils import * =====
                content = re.sub(
                    r'^from\s+utils\s+import\s+\*\s*$',
                    '# from utils import *  # حذف شد — utils دیگه نیست',
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
    # ۵. خلاصه
    # ============================================================
    print("\n" + "=" * 70)
    print("✅ تمام!")
    print("=" * 70)
    
    print(f"\n📂 فایل‌های منتقل شده به ریشه:")
    for m in moved:
        exists = (root / m).exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {m}")
    
    print(f"\n📝 فایل‌های اصلاح شده:")
    for f in changed_files[:20]:
        print(f"   ✅ {f}")
    if len(changed_files) > 20:
        print(f"   ... و {len(changed_files) - 20} فایل دیگه")
    
    print(f"\n🚀 حالا تست کن:")
    print(f"   python main2.py")


if __name__ == '__main__':
    main()
