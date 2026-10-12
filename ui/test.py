# test_sidebar.py
import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# ✅ لاگ فعال
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

app = QApplication(sys.argv)

print("=" * 70)
print("🧪 تست SidebarWidget")
print("=" * 70)

# 1. ثبت منوی پیش‌فرض اول
from menu_registry import get_menu_registry, register_default_menu
register_default_menu()

r = get_menu_registry()
stats = r.get_stats()
print(f"\n✅ MenuRegistry: groups={stats['groups']}, items={stats['items']}")

# 2. ساخت Sidebar
print("\n🔨 ساخت SidebarWidget...")
try:
    from ui.main_window import SidebarWidget
    
    license_info = {
        'customer': 'test',
        'modules': ['accounting', 'inventory', 'payroll', 'parties', 'invoice', 'purchase', 'reports', 'ai'],
        'days_left': 30,
    }
    
    sidebar = SidebarWidget(
        license_info=license_info,
        user_level='admin',
    )
    
    print(f"\n📊 نتیجه:")
    print(f"   buttons: {len(sidebar.buttons)}")
    print(f"   group_buttons: {len(sidebar.group_buttons)}")
    print(f"   group_containers: {len(sidebar.group_containers)}")
    print(f"   group_keys: {len(sidebar.group_keys)}")
    
    print(f"\n📋 دکمه‌ها:")
    for key in sidebar.buttons.keys():
        print(f"   • {key}")
    
    print(f"\n📁 گروه‌ها:")
    for key in sidebar.group_buttons.keys():
        print(f"   • {key}")
    
    # 3. نمایش در پنجره
    window = QMainWindow()
    window.setCentralWidget(sidebar)
    window.resize(400, 800)
    window.show()
    
    print("\n✅ پنجره باز شد — 5 ثانیه صبر کن...")
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(5000, app.quit)
    
    sys.exit(app.exec_())

except Exception as e:
    import traceback
    print(f"\n❌ خطا: {e}")
    traceback.print_exc()
