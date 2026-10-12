# ui/account_manager_widget.py
# ============================================================
# ویجت مدیریت حساب‌ها — نسخه 5.0
# با Tree View، سیستم کدینگ، حساب‌های پیش‌فرض و جستجو
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui.base_widgets import BaseWidget, BaseDialog
from ui.coding_manager import CodingStructure, CodingStructureDialog
from database import get_db
import json
import os
import sqlite3


# ═══════════════════════════════════════════════════════════
# تابع ایجاد حساب‌های پیش‌فرض
# ═══════════════════════════════════════════════════════════

def create_default_accounts(coding_structure=None):
    """
    ایجاد ساختار پیش‌فرض حساب‌های حسابداری
    
    Args:
        coding_structure: ساختار کدینگ (اختیاری)
    
    Returns:
        tuple: (created_count, updated_count)
    """
    if coding_structure is None:
        coding_structure = CodingStructure()
        if not coding_structure.levels:
            coding_structure.get_default_structure()
    
    if len(coding_structure.levels) < 2:
        print("⚠️ ساختار کدینگ باید حداقل ۲ سطح داشته باشه!")
        return (0, 0)
    
    def make_code(parts):
        """ساخت کد از لیست بخش‌ها"""
        return coding_structure.format_code(parts)
    
    # ═══════════════════════════════════════════════════════
    # تعریف ساختار استاندارد
    # ═══════════════════════════════════════════════════════
    
    default_accounts = []
    
    # ═══════ 1 - دارایی‌ها ═══════
    acc_1 = make_code(['1'])
    default_accounts.append((acc_1, 'دارایی‌ها', 'asset', None))
    
    # 11 - دارایی جاری
    acc_11 = make_code(['1', '11'])
    default_accounts.append((acc_11, 'دارایی جاری', 'asset', acc_1))
    
    for code, name in [
        ('1101', 'صندوق'),
        ('1102', 'بانک'),
        ('1103', 'تنخواه‌گردان'),
        ('1104', 'حساب‌های دریافتنی'),
        ('1105', 'اسناد دریافتنی'),
        ('1106', 'موجودی کالا'),
        ('1107', 'پیش‌پرداخت‌ها'),
        ('1108', 'سفارشات و اعتبارات'),
        ('1109', 'موجودی مواد و کالای در جریان ساخت'),
    ]:
        default_accounts.append(
            (make_code(['1', code]), name, 'asset', acc_11)
        )
    
    # 12 - دارایی غیر جاری
    acc_12 = make_code(['1', '12'])
    default_accounts.append((acc_12, 'دارایی غیر جاری', 'asset', acc_1))
    
    for code, name in [
        ('1201', 'دارایی ثابت'),
        ('1202', 'استهلاک انباشته'),
        ('1203', 'دارایی نامشهود'),
        ('1204', 'سرمایه‌گذاری بلندمدت'),
        ('1205', 'اموال، ماشین‌آلات و تجهیزات'),
        ('1206', 'زمین'),
        ('1207', 'ساختمان'),
    ]:
        default_accounts.append(
            (make_code(['1', code]), name, 'asset', acc_12)
        )
    
    # 13 - سایر دارایی‌ها
    acc_13 = make_code(['1', '13'])
    default_accounts.append((acc_13, 'سایر دارایی‌ها', 'asset', acc_1))
    
    for code, name in [
        ('1301', 'سود و زیان انباشته'),
        ('1302', 'هزینه‌های تأسیس'),
        ('1303', 'دارایی‌های سرقفلی'),
    ]:
        default_accounts.append(
            (make_code(['1', code]), name, 'asset', acc_13)
        )
    
    # ═══════ 2 - بدهی‌ها ═══════
    acc_2 = make_code(['2'])
    default_accounts.append((acc_2, 'بدهی‌ها', 'liability', None))
    
    # 21 - بدهی جاری
    acc_21 = make_code(['2', '21'])
    default_accounts.append((acc_21, 'بدهی جاری', 'liability', acc_2))
    
    for code, name in [
        ('2101', 'حساب‌های پرداختنی'),
        ('2102', 'اسناد پرداختنی'),
        ('2103', 'حقوق و دستمزد پرداختنی'),
        ('2104', 'مالیات پرداختنی'),
        ('2105', 'بیمه پرداختنی'),
        ('2106', 'پیش‌دریافت‌ها'),
        ('2107', 'سود سهام پرداختنی'),
        ('2108', 'هزینه‌های پرداختنی'),
        ('2109', 'ذخیره مالیات'),
    ]:
        default_accounts.append(
            (make_code(['2', code]), name, 'liability', acc_21)
        )
    
    # 22 - بدهی غیر جاری
    acc_22 = make_code(['2', '22'])
    default_accounts.append((acc_22, 'بدهی غیر جاری', 'liability', acc_2))
    
    for code, name in [
        ('2201', 'تسهیلات مالی بلندمدت'),
        ('2202', 'ذخیره مزایای پایان خدمت'),
        ('2203', 'اوراق قرضه پرداختنی'),
    ]:
        default_accounts.append(
            (make_code(['2', code]), name, 'liability', acc_22)
        )
    
    # ═══════ 3 - سرمایه ═══════
    acc_3 = make_code(['3'])
    default_accounts.append((acc_3, 'سرمایه', 'equity', None))
    
    # 31 - سرمایه اولیه
    acc_31 = make_code(['3', '31'])
    default_accounts.append((acc_31, 'سرمایه اولیه', 'equity', acc_3))
    
    for code, name in [
        ('3101', 'سرمایه'),
        ('3102', 'آورده نقدی شرکا'),
        ('3103', 'آورده غیرنقدی شرکا'),
    ]:
        default_accounts.append(
            (make_code(['3', code]), name, 'equity', acc_31)
        )
    
    # 32 - برداشت‌ها
    acc_32 = make_code(['3', '32'])
    default_accounts.append((acc_32, 'برداشت‌ها', 'equity', acc_3))
    
    for code, name in [
        ('3201', 'برداشت شخصی'),
        ('3202', 'برداشت شرکا'),
    ]:
        default_accounts.append(
            (make_code(['3', code]), name, 'equity', acc_32)
        )
    
    # 33 - سود و زیان
    acc_33 = make_code(['3', '33'])
    default_accounts.append((acc_33, 'سود و زیان', 'equity', acc_3))
    
    for code, name in [
        ('3301', 'سود و زیان انباشته'),
        ('3302', 'سود و زیان دوره جاری'),
    ]:
        default_accounts.append(
            (make_code(['3', code]), name, 'equity', acc_33)
        )
    
    # ═══════ 4 - درآمدها ═══════
    acc_4 = make_code(['4'])
    default_accounts.append((acc_4, 'درآمدها', 'income', None))
    
    # 41 - درآمد فروش
    acc_41 = make_code(['4', '41'])
    default_accounts.append((acc_41, 'درآمد فروش', 'income', acc_4))
    
    for code, name in [
        ('4101', 'فروش کالا'),
        ('4102', 'فروش خدمات'),
        ('4103', 'برگشت از فروش'),
        ('4104', 'تخفیفات نقدی فروش'),
        ('4105', 'فروش صادراتی'),
    ]:
        default_accounts.append(
            (make_code(['4', code]), name, 'income', acc_41)
        )
    
    # 42 - درآمد سایر
    acc_42 = make_code(['4', '42'])
    default_accounts.append((acc_42, 'درآمد سایر', 'income', acc_4))
    
    for code, name in [
        ('4201', 'درآمد اجاره'),
        ('4202', 'سود بانکی'),
        ('4203', 'سود سرمایه‌گذاری'),
        ('4204', 'درآمد متفرقه'),
    ]:
        default_accounts.append(
            (make_code(['4', code]), name, 'income', acc_42)
        )
    
    # ═══════ 5 - هزینه‌ها ═══════
    acc_5 = make_code(['5'])
    default_accounts.append((acc_5, 'هزینه‌ها', 'expense', None))
    
    # 51 - بهای تمام شده
    acc_51 = make_code(['5', '51'])
    default_accounts.append((acc_51, 'بهای تمام شده', 'expense', acc_5))
    
    for code, name in [
        ('5101', 'خرید کالا'),
        ('5102', 'حمل و نقل خرید'),
        ('5103', 'حقوق مستقیم تولید'),
    ]:
        default_accounts.append(
            (make_code(['5', code]), name, 'expense', acc_51)
        )
    
    # 52 - هزینه‌های عملیاتی
    acc_52 = make_code(['5', '52'])
    default_accounts.append((acc_52, 'هزینه‌های عملیاتی', 'expense', acc_5))
    
    for code, name in [
        ('5201', 'حقوق و دستمزد'),
        ('5202', 'اجاره'),
        ('5203', 'آب و برق و گاز'),
        ('5204', 'تلفن و اینترنت'),
        ('5205', 'لوازم مصرفی'),
        ('5206', 'استهلاک'),
        ('5207', 'تبلیغات و بازاریابی'),
        ('5208', 'حمل و نقل'),
        ('5209', 'بیمه'),
        ('5210', 'مالیات و عوارض'),
        ('5211', 'هزینه‌های اداری'),
        ('5212', 'هزینه‌های بانکی'),
    ]:
        default_accounts.append(
            (make_code(['5', code]), name, 'expense', acc_52)
        )
    
    # 53 - هزینه‌های غیرعملیاتی
    acc_53 = make_code(['5', '53'])
    default_accounts.append((acc_53, 'هزینه‌های غیرعملیاتی', 'expense', acc_5))
    
    for code, name in [
        ('5301', 'هزینه‌های مالی'),
        ('5302', 'جریمه‌ها'),
        ('5303', 'خسارات'),
        ('5304', 'هزینه‌های متفرقه'),
    ]:
        default_accounts.append(
            (make_code(['5', code]), name, 'expense', acc_53)
        )
    
    # ═══════════════════════════════════════════════════════
    # ذخیره در دیتابیس
    # ═══════════════════════════════════════════════════════
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            created = 0
            updated = 0
            
            for code, name, type_, parent in default_accounts:
                c.execute("SELECT code FROM accounts WHERE code = ?", [code])
                existing = c.fetchone()
                
                if existing:
                    c.execute('''
                        UPDATE accounts
                        SET name = ?, type = ?, parent_code = ?
                        WHERE code = ?
                    ''', (name, type_, parent, code))
                    updated += 1
                else:
                    parts = coding_structure.parse_code(code)
                    level = len(parts)
                    
                    c.execute('''
                        INSERT INTO accounts 
                        (code, name, type, parent_code, level, is_active)
                        VALUES (?, ?, ?, ?, ?, 1)
                    ''', (code, name, type_, parent, level))
                    created += 1
            
            conn.commit()
            print(f"✅ {created} حساب ایجاد، {updated} حساب بروزرسانی")
            return (created, updated)
    
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return (0, 0)


# ═══════════════════════════════════════════════════════════
# ویجت اصلی مدیریت حساب‌ها
# ═══════════════════════════════════════════════════════════

class AccountManagerWidget(BaseWidget):
    """ویجت مدیریت حساب‌ها با Tree View"""
    
    def __init__(self):
        super().__init__()
        self.accounts_data = []
        self.coding = CodingStructure()
        
        if not self.coding.levels:
            self.coding.get_default_structure()
        
        self.current_view = 'tree'
        
        self.setup_ui()
        self.load_accounts()
        self._apply_widget_theme()
    
    # ═══════════════════════════════════════════════════════════
    # UI Setup
    # ═══════════════════════════════════════════════════════════
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(self.margin(15), self.margin(15),
                                  self.margin(15), self.margin(15))
        
        # عنوان
        title_layout = QHBoxLayout()
        title = QLabel("🌳 درخت حساب‌ها")
        title.setObjectName("titleLabel")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        self.structure_label = QLabel(self._get_structure_display())
        self.structure_label.setStyleSheet(
            "color: #666; font-size: 9pt; padding: 5px 10px; "
            "background: rgba(25,118,210,0.1); border-radius: 12px;"
        )
        title_layout.addWidget(self.structure_label)
        
        layout.addLayout(title_layout)
        
        # نوار ابزار اصلی
        toolbar = self._create_main_toolbar()
        layout.addLayout(toolbar)
        
        # نوار فیلتر
        filter_bar = self._create_filter_bar()
        layout.addLayout(filter_bar)
        
        # پشته نمایش
        self.stack = QStackedWidget()
        
        # ۱. Tree View
        self.tree_widget = self._create_tree_view()
        self.stack.addWidget(self.tree_widget)
        
        # ۲. Table View
        self.table_widget = self._create_table_view()
        self.stack.addWidget(self.table_widget)
        
        layout.addWidget(self.stack, 1)
        
        # آمار
        self.stats_label = QLabel("📊 در حال بارگذاری...")
        layout.addWidget(self.stats_label)
    
    def _get_structure_display(self):
        if not self.coding.levels:
            return "📐 بدون ساختار"
        parts = []
        for level in self.coding.levels:
            parts.append("_" * level['length'])
        return f"📐 {self.coding.separator.join(parts)}"
    
    def _create_main_toolbar(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(self.spacing(8))
        
        new_btn = self.create_button("➕ حساب جدید", "successBtn")
        new_btn.clicked.connect(self.new_account)
        toolbar.addWidget(new_btn)
        
        edit_btn = self.create_button("✏️ ویرایش", "warningBtn")
        edit_btn.clicked.connect(self.edit_account)
        toolbar.addWidget(edit_btn)
        
        delete_btn = self.create_button("🗑️ حذف", "dangerBtn")
        delete_btn.clicked.connect(self.delete_account)
        toolbar.addWidget(delete_btn)
        
        toolbar.addSpacing(self.spacing(15))
        
        coding_btn = self.create_button("⚙️ تنظیمات کدینگ", "infoBtn")
        coding_btn.clicked.connect(self.open_coding_settings)
        toolbar.addWidget(coding_btn)
        
        default_btn = self.create_button("🔄 حساب‌های پیش‌فرض", "warningBtn")
        default_btn.clicked.connect(self.create_default)
        toolbar.addWidget(default_btn)
        
        tree_btn = self.create_button("🌳 درخت", "infoBtn")
        tree_btn.clicked.connect(lambda: self.switch_view('tree'))
        toolbar.addWidget(tree_btn)
        
        table_btn = self.create_button("📋 جدول", "infoBtn")
        table_btn.clicked.connect(lambda: self.switch_view('table'))
        toolbar.addWidget(table_btn)
        
        toolbar.addSpacing(self.spacing(10))
        
        expand_btn = self.create_button("📂 باز")
        expand_btn.clicked.connect(self.expand_all)
        toolbar.addWidget(expand_btn)
        
        collapse_btn = self.create_button("📁 بسته")
        collapse_btn.clicked.connect(self.collapse_all)
        toolbar.addWidget(collapse_btn)
        
        toolbar.addStretch()
        
        export_btn = self.create_button("📤 Export", "successBtn")
        export_btn.clicked.connect(self.export_accounts)
        toolbar.addWidget(export_btn)
        
        return toolbar
    
    def _create_filter_bar(self):
        bar = QHBoxLayout()
        bar.setSpacing(self.spacing(8))
        
        bar.addWidget(QLabel("🔍 جستجو:"))
        
        self.search_input = self.create_input("کد یا نام حساب...")
        self.search_input.setMaximumWidth(self.scaled(250))
        self.search_input.textChanged.connect(self.filter_accounts)
        bar.addWidget(self.search_input)
        
        bar.addWidget(QLabel("نوع:"))
        self.type_filter = QComboBox()
        self.type_filter.addItem("همه", "")
        self.type_filter.addItem("🏦 دارایی", "asset")
        self.type_filter.addItem("📋 بدهی", "liability")
        self.type_filter.addItem("💰 سرمایه", "equity")
        self.type_filter.addItem("📈 درآمد", "income")
        self.type_filter.addItem("💸 هزینه", "expense")
        self.type_filter.setMinimumWidth(self.scaled(150))
        self.type_filter.currentIndexChanged.connect(self.filter_accounts)
        bar.addWidget(self.type_filter)
        
        bar.addWidget(QLabel("وضعیت:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("همه", "all")
        self.status_filter.addItem("✅ فعال", "active")
        self.status_filter.addItem("❌ غیرفعال", "inactive")
        self.status_filter.setMinimumWidth(self.scaled(120))
        self.status_filter.currentIndexChanged.connect(self.filter_accounts)
        bar.addWidget(self.status_filter)
        
        bar.addStretch()
        
        clear_btn = self.create_button("✖️ پاک کردن", "dangerBtn")
        clear_btn.clicked.connect(self.clear_filters)
        bar.addWidget(clear_btn)
        
        return bar
    
    def _create_tree_view(self):
        """درخت حساب‌ها"""
        tree = QTreeWidget()
        tree.setColumnCount(5)
        tree.setHeaderLabels([
            "کد و نام حساب", "نوع", "سطح", "مانده", "وضعیت"
        ])
        tree.setAlternatingRowColors(True)
        tree.setAnimated(True)
        tree.setIndentation(self.scaled(22))
        tree.setColumnWidth(0, self.scaled(450))
        tree.setColumnWidth(1, self.scaled(100))
        tree.setColumnWidth(2, self.scaled(150))
        tree.setColumnWidth(3, self.scaled(120))
        tree.setColumnWidth(4, self.scaled(100))
        tree.setExpandsOnDoubleClick(False)
        tree.itemDoubleClicked.connect(self._on_item_double_click)
        tree.itemExpanded.connect(self._on_item_expanded)
        tree.itemCollapsed.connect(self._on_item_collapsed)
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._show_context_menu)
        tree.setSelectionMode(QAbstractItemView.SingleSelection)
        return tree
    
    def _create_table_view(self):
        table = self.create_table(
            ["کد حساب", "نام حساب", "نوع", "سطح", "والد", "مانده", "وضعیت"],
            stretch_last=False
        )
        table.setColumnWidth(0, self.scaled(150))
        table.setColumnWidth(1, self.scaled(250))
        table.setColumnWidth(2, self.scaled(100))
        table.setColumnWidth(3, self.scaled(80))
        table.setColumnWidth(4, self.scaled(120))
        table.setColumnWidth(5, self.scaled(120))
        table.doubleClicked.connect(self.edit_account)
        return table
    
    # ═══════════════════════════════════════════════════════════
    # بارگذاری داده‌ها
    # ═══════════════════════════════════════════════════════════
    
    def load_accounts(self):
        try:
            if not self.coding.levels:
                self.coding.get_default_structure()
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT code, name, type, parent_code, level, 
                           balance, is_active, created_at
                    FROM accounts
                    ORDER BY code
                ''')
                self.accounts_data = [dict(row) for row in c.fetchall()]
            
            self.display_tree()
            self.display_table()
            self.update_stats()
            self.structure_label.setText(self._get_structure_display())
        
        except Exception as e:
            print(f"❌ خطا: {e}")
            import traceback
            traceback.print_exc()
            self.accounts_data = []
    
    def display_tree(self):
        """نمایش درخت با رنگ و آیکون"""
        self.tree_widget.clear()
        
        if not self.accounts_data:
            return
        
        accounts = self._get_filtered_accounts()
        
        # ساخت آیتم‌ها
        items = {}
        for acc in accounts:
            item = self._create_tree_item(acc)
            item.setData(0, Qt.UserRole, acc['code'])
            items[acc['code']] = item
        
        # ساخت سلسله‌مراتب
        root_items = []
        for acc in accounts:
            item = items[acc['code']]
            parent_code = acc.get('parent_code')
            
            if parent_code and parent_code in items:
                items[parent_code].addChild(item)
            else:
                root_items.append(item)
        
        self.tree_widget.addTopLevelItems(root_items)
        self.tree_widget.expandToDepth(2)
    
    def _create_tree_item(self, acc):
        """ساخت یک آیتم درخت با آیکون و رنگ"""
        item = QTreeWidgetItem()
        
        # آیکون بر اساس نوع
        icon_map = {
            'asset': '🏦', 'liability': '📋',
            'equity': '💰', 'income': '📈', 'expense': '💸',
        }
        icon = icon_map.get(acc['type'], '📄')
        
        # سطح رو تعیین کن
        level = acc.get('level', 1) or 1
        
        # آیکون پوشه برای گروه/کل، آیکون فایل برای معین
        if level <= 2:
            folder_icon = '📁'
        else:
            folder_icon = '📄'
        
        # ستون ۰: کد و نام با آیکون
        item.setText(0, f"{icon} {folder_icon} {acc['code']} - {acc['name']}")
        
        # ستون ۱: نوع
        type_names = {
            'asset': 'دارایی', 'liability': 'بدهی',
            'equity': 'سرمایه', 'income': 'درآمد', 'expense': 'هزینه',
        }
        item.setText(1, type_names.get(acc['type'], acc['type']))
        
        # ستون ۲: سطح
        level_name = self._get_level_name(level)
        item.setText(2, f"سطح {level} ({level_name})")
        
        # ستون ۳: مانده
        balance = acc.get('balance', 0) or 0
        item.setText(3, f"{balance:,.0f}")
        item.setTextAlignment(3, Qt.AlignRight | Qt.AlignVCenter)
        
        # ستون ۴: وضعیت
        item.setText(4, "✅ فعال" if acc['is_active'] else "❌ غیرفعال")
        
        # رنگ بر اساس سطح
        if 0 < level <= len(self.coding.levels):
            color = self.coding.levels[level - 1]['color']
            item.setForeground(0, QColor(color))
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            
            if level <= 2:
                # برای گروه و کل، فونت بزرگ‌تر
                font.setPointSize(font.pointSize() + 1)
                item.setFont(0, font)
        
        # رنگ مانده
        if balance > 0:
            item.setForeground(3, QColor('#27ae60'))
        elif balance < 0:
            item.setForeground(3, QColor('#e74c3c'))
        
        # خاکستری برای غیرفعال
        if not acc['is_active']:
            for col in range(5):
                item.setForeground(col, QColor('#999999'))
        
        return item
    
    def _get_level_name(self, level):
        if 0 < level <= len(self.coding.levels):
            return self.coding.levels[level - 1]['name']
        return f"سطح {level}"
    
    def display_table(self):
        """نمایش جدول"""
        accounts = self._get_filtered_accounts()
        self.table_widget.setRowCount(len(accounts))
        c = self.get_theme_colors()
        
        for i, acc in enumerate(accounts):
            self.table_widget.setItem(i, 0, QTableWidgetItem(acc['code']))
            self.table_widget.setItem(i, 1, QTableWidgetItem(acc['name']))
            
            type_names = {
                'asset': '🏦 دارایی', 'liability': '📋 بدهی',
                'equity': '💰 سرمایه', 'income': '📈 درآمد',
                'expense': '💸 هزینه',
            }
            self.table_widget.setItem(
                i, 2,
                QTableWidgetItem(type_names.get(acc['type'], acc['type']))
            )
            
            level = acc.get('level', 1) or 1
            self.table_widget.setItem(i, 3, QTableWidgetItem(f"سطح {level}"))
            self.table_widget.setItem(
                i, 4, QTableWidgetItem(acc.get('parent_code') or "-")
            )
            
            balance = acc.get('balance', 0) or 0
            balance_item = QTableWidgetItem(f"{balance:,.0f}")
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if balance > 0:
                balance_item.setForeground(QColor('#27ae60'))
            elif balance < 0:
                balance_item.setForeground(QColor('#e74c3c'))
            self.table_widget.setItem(i, 5, balance_item)
            
            status_item = QTableWidgetItem(
                "✅ فعال" if acc['is_active'] else "❌ غیرفعال"
            )
            status_item.setForeground(
                QColor('#27ae60') if acc['is_active'] else QColor('#e74c3c')
            )
            self.table_widget.setItem(i, 6, status_item)
    
    def _get_filtered_accounts(self):
        """فیلتر حساب‌ها"""
        accounts = self.accounts_data
        
        text = self.search_input.text().lower().strip()
        if text:
            accounts = [
                a for a in accounts
                if text in str(a['code']).lower()
                or text in str(a['name']).lower()
            ]
        
        type_filter = self.type_filter.currentData()
        if type_filter:
            accounts = [a for a in accounts if a['type'] == type_filter]
        
        status_filter = self.status_filter.currentData()
        if status_filter == 'active':
            accounts = [a for a in accounts if a['is_active']]
        elif status_filter == 'inactive':
            accounts = [a for a in accounts if not a['is_active']]
        
        return accounts
    
    def update_stats(self):
        total = len(self.accounts_data)
        active = sum(1 for a in self.accounts_data if a['is_active'])
        inactive = total - active
        
        type_counts = {}
        for acc in self.accounts_data:
            type_counts[acc['type']] = type_counts.get(acc['type'], 0) + 1
        
        total_balance = sum(a.get('balance', 0) or 0 for a in self.accounts_data)
        
        self.stats_label.setText(
            f"📊 مجموع: {total} | "
            f"✅ فعال: {active} | ❌ غیرفعال: {inactive} | "
            f"🏦 دارایی: {type_counts.get('asset', 0)} | "
            f"📋 بدهی: {type_counts.get('liability', 0)} | "
            f"💰 سرمایه: {type_counts.get('equity', 0)} | "
            f"📈 درآمد: {type_counts.get('income', 0)} | "
            f"💸 هزینه: {type_counts.get('expense', 0)} | "
            f"💰 مانده: {total_balance:,.0f}"
        )
        
        c = self.get_theme_colors()
        self.stats_label.setStyleSheet(f"""
            background: {c['card']};
            color: {c['text']};
            padding: 10px;
            border: 1px solid {c['border']};
            border-radius: 6px;
            font-weight: bold;
        """)
    
    # ═══════════════════════════════════════════════════════════
    # فیلترها
    # ═══════════════════════════════════════════════════════════
    
    def filter_accounts(self):
        self.display_tree()
        self.display_table()
    
    def clear_filters(self):
        self.search_input.clear()
        self.type_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.filter_accounts()
    
    # ═══════════════════════════════════════════════════════════
    # نمایش
    # ═══════════════════════════════════════════════════════════
    
    def switch_view(self, view):
        self.current_view = view
        self.stack.setCurrentIndex(0 if view == 'tree' else 1)
    
    def expand_all(self):
        self.tree_widget.expandAll()
    
    def collapse_all(self):
        self.tree_widget.collapseAll()
    
    def _on_item_expanded(self, item):
        pass
    
    def _on_item_collapsed(self, item):
        pass
    
    def get_selected_code(self):
        if self.current_view == 'tree':
            item = self.tree_widget.currentItem()
            if item:
                return item.data(0, Qt.UserRole)
        else:
            row = self.table_widget.currentRow()
            if row >= 0:
                return self.table_widget.item(row, 0).text()
        return None
    
    def _on_item_double_click(self):
        self.edit_account()
    
    def _show_context_menu(self, pos):
        item = self.tree_widget.itemAt(pos)
        if not item:
            return
        
        self.tree_widget.setCurrentItem(item)
        
        menu = QMenu(self)
        
        new_action = menu.addAction("➕ حساب جدید")
        new_action.triggered.connect(self.new_account)
        
        edit_action = menu.addAction("✏️ ویرایش")
        edit_action.triggered.connect(self.edit_account)
        
        menu.addSeparator()
        
        add_sub_action = menu.addAction("📁 افزودن زیرحساب")
        add_sub_action.triggered.connect(self._add_sub_account)
        
        menu.addSeparator()
        
        delete_action = menu.addAction("🗑️ حذف")
        delete_action.triggered.connect(self.delete_account)
        
        menu.addSeparator()
        
        copy_action = menu.addAction("📋 کپی کد")
        copy_action.triggered.connect(self._copy_code)
        
        menu.exec_(self.tree_widget.mapToGlobal(pos))
    
    def _add_sub_account(self):
        """افزودن زیرحساب به حساب انتخاب شده"""
        code = self.get_selected_code()
        if not code:
            return
        
        dialog = AccountDialog(
            code=None,
            parent=self,
            default_parent=code,
            coding=self.coding
        )
        
        if dialog.exec_():
            self.load_accounts()
            QMessageBox.information(self, "موفق", "✅ زیرحساب ایجاد شد!")
    
    def _copy_code(self):
        code = self.get_selected_code()
        if code:
            QApplication.clipboard().setText(code)
            QMessageBox.information(self, "موفق", f"✅ کد {code} کپی شد!")
    
    # ═══════════════════════════════════════════════════════════
    # CRUD
    # ═══════════════════════════════════════════════════════════
    
    def new_account(self):
        parent_code = self.get_selected_code()
        
        dialog = AccountDialog(
            code=None,
            parent=self,
            default_parent=parent_code,
            coding=self.coding
        )
        
        if dialog.exec_():
            self.load_accounts()
            QMessageBox.information(self, "موفق", "✅ حساب جدید ایجاد شد!")
    
    def edit_account(self):
        code = self.get_selected_code()
        if not code:
            QMessageBox.warning(self, "خطا", "یک حساب انتخاب کنید!")
            return
        
        dialog = AccountDialog(
            code=code,
            parent=self,
            coding=self.coding
        )
        
        if dialog.exec_():
            self.load_accounts()
            QMessageBox.information(self, "موفق", "✅ حساب ویرایش شد!")
    
    def delete_account(self):
        code = self.get_selected_code()
        if not code:
            QMessageBox.warning(self, "خطا", "یک حساب انتخاب کنید!")
            return
        
        account = next(
            (a for a in self.accounts_data if a['code'] == code), None
        )
        if not account:
            return
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM accounts WHERE parent_code = ?",
                [code]
            )
            child_count = c.fetchone()[0]
            
            if child_count > 0:
                QMessageBox.warning(
                    self, "خطا",
                    f"❌ این حساب دارای {child_count} زیرمجموعه است!\n"
                    f"ابتدا زیرمجموعه‌ها را حذف کنید."
                )
                return
            
            c.execute(
                "SELECT COUNT(*) FROM voucher_items WHERE account_code = ?",
                [code]
            )
            usage_count = c.fetchone()[0]
            
            if usage_count > 0:
                reply = QMessageBox.question(
                    self, "هشدار",
                    f"⚠️ این حساب در {usage_count} سند استفاده شده!\n"
                    f"آیا مطمئنید؟",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف '{code} - {account['name']}' اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM accounts WHERE code = ?", [code])
                    conn.commit()
                
                self.load_accounts()
                QMessageBox.information(self, "موفق", "✅ حساب حذف شد!")
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ خطا: {e}")
    
    def open_coding_settings(self):
        dialog = CodingStructureDialog(self.coding, self)
        if dialog.exec_():
            self.coding.load()
            self.structure_label.setText(self._get_structure_display())
            self.load_accounts()
            QMessageBox.information(self, "موفق", "✅ تنظیمات کدینگ ذخیره شد!")
    
    def create_default(self):
        """ایجاد حساب‌های پیش‌فرض"""
        if not self.coding.levels:
            QMessageBox.warning(
                self, "خطا",
                "ابتدا ساختار کدینگ را تنظیم کنید!"
            )
            return
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM accounts")
            count = c.fetchone()[0]
        
        if count > 0:
            reply = QMessageBox.question(
                self, "تأیید",
                f"در حال حاضر {count} حساب وجود دارد.\n\n"
                f"آیا می‌خواهید حساب‌های پیش‌فرض اضافه/بروزرسانی شوند؟\n\n"
                f"✅ حساب‌های موجود حفظ می‌شوند\n"
                f"✅ فقط حساب‌های جدید اضافه می‌شوند\n"
                f"✅ نام و ساختار موجود بروزرسانی می‌شود",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
        
        try:
            created, updated = create_default_accounts(self.coding)
            
            if created > 0 or updated > 0:
                self.load_accounts()
                QMessageBox.information(
                    self, "موفق",
                    f"✅ عملیات انجام شد!\n\n"
                    f"➕ ایجاد: {created} حساب جدید\n"
                    f"🔄 بروزرسانی: {updated} حساب\n\n"
                    f"📊 ساختار:\n"
                    f"├─ ۱: دارایی‌ها\n"
                    f"├─ ۲: بدهی‌ها\n"
                    f"├─ ۳: سرمایه\n"
                    f"├─ ۴: درآمدها\n"
                    f"└─ ۵: هزینه‌ها"
                )
            else:
                QMessageBox.information(
                    self, "توجه",
                    "هیچ حسابی ایجاد نشد."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self, "خطا",
                f"❌ خطا:\n{str(e)}"
            )
    
    # ═══════════════════════════════════════════════════════════
    # Export
    # ═══════════════════════════════════════════════════════════
    
    def export_accounts(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره خروجی",
            f"accounts_{QDate.currentDate().toString('yyyyMMdd')}.csv",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )
        
        if not file_name:
            return
        
        try:
            if file_name.endswith('.json'):
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(self.accounts_data, f, ensure_ascii=False, indent=2)
            else:
                import csv
                with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "کد", "نام", "نوع", "والد", "سطح", "مانده", "وضعیت"
                    ])
                    for acc in self.accounts_data:
                        writer.writerow([
                            acc['code'],
                            acc['name'],
                            acc['type'],
                            acc.get('parent_code', ''),
                            acc.get('level', 1),
                            acc.get('balance', 0),
                            'فعال' if acc['is_active'] else 'غیرفعال',
                        ])
            
            QMessageBox.information(self, "موفق", f"✅ خروجی ذخیره شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا: {e}")
    
    # ═══════════════════════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════════════════════
    
    def _apply_widget_theme(self):
        try:
            c = self.get_theme_colors()
            
            self.tree_widget.setStyleSheet(f"""
                QTreeWidget {{
                    background: {c['bg_alt']};
                    alternate-background-color: {c['bg']};
                    color: {c['text']};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    outline: none;
                    font-size: 10pt;
                }}
                QTreeWidget::item {{
                    padding: 8px 4px;
                    border-bottom: 1px solid {c['border']};
                    min-height: 24px;
                }}
                QTreeWidget::item:selected {{
                    background: {c['selected']};
                    color: {c['selected_text']};
                }}
                QTreeWidget::item:hover {{
                    background: {c['hover']};
                }}
                QTreeWidget::branch {{
                    background: transparent;
                }}
                QHeaderView::section {{
                    background: {c['card']};
                    color: {c['text']};
                    padding: 10px;
                    border: none;
                    border-right: 1px solid {c['border']};
                    border-bottom: 2px solid {c['selected']};
                    font-weight: bold;
                    font-size: 10pt;
                }}
            """)
        except Exception as e:
            print(f"⚠️ خطا theme: {e}")


# ═══════════════════════════════════════════════════════════
# دیالوگ ایجاد/ویرایش حساب
# ═══════════════════════════════════════════════════════════

class AccountDialog(BaseDialog):
    """دیالوگ حساب با سیستم کدینگ"""
    
    def __init__(self, code=None, parent=None, default_parent=None, coding=None):
        super().__init__(base_width=700, base_height=800)
        self.account_code = code
        self.parent_widget = parent
        self.coding = coding or CodingStructure()
        self.default_parent = default_parent
        
        self.code_parts = []
        
        self.setWindowTitle("✏️ ویرایش حساب" if code else "➕ حساب جدید")
        self.setModal(True)
        
        self.setup_ui()
        
        if code:
            self.load_account_data()
        elif default_parent:
            self.parent_code.setText(default_parent)
        
        self.apply_theme()
        self._apply_dialog_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(
            self.margin(15), self.margin(15),
            self.margin(15), self.margin(15)
        )
        
        title = QLabel(
            "✏️ ویرایش حساب" if self.account_code else "➕ حساب جدید"
        )
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # اطلاعات اصلی
        info_group = QGroupBox("📋 اطلاعات اصلی")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(self.spacing(10))
        info_layout.setLabelAlignment(Qt.AlignRight)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("مثال: صندوق، بانک ملی")
        info_layout.addRow("📛 نام حساب *:", self.name_edit)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "🏦 دارایی (asset)",
            "📋 بدهی (liability)",
            "💰 سرمایه (equity)",
            "📈 درآمد (income)",
            "💸 هزینه (expense)",
        ])
        info_layout.addRow("🏷️ نوع حساب:", self.type_combo)
        
        layout.addWidget(info_group)
        
        # کد حساب
        code_group = QGroupBox("🔢 کد حساب (بر اساس ساختار کدینگ)")
        code_layout = QVBoxLayout(code_group)
        
        structure_info = self._get_structure_info()
        self.structure_label = QLabel(structure_info)
        self.structure_label.setStyleSheet(f"""
            color: #666;
            font-size: 9pt;
            padding: 8px;
            background: rgba(25,118,210,0.08);
            border-radius: 6px;
        """)
        self.structure_label.setWordWrap(True)
        code_layout.addWidget(self.structure_label)
        
        code_parts_layout = QHBoxLayout()
        code_parts_layout.setSpacing(self.spacing(4))
        
        for i, level in enumerate(self.coding.levels):
            if i > 0:
                sep_label = QLabel(self.coding.separator)
                sep_label.setStyleSheet(
                    f"color: {level['color']}; "
                    f"font-weight: bold; font-size: 14pt;"
                )
                code_parts_layout.addWidget(sep_label)
            
            part_container = QVBoxLayout()
            part_container.setSpacing(2)
            
            level_label = QLabel(level['name'])
            level_label.setAlignment(Qt.AlignCenter)
            level_label.setStyleSheet(
                f"color: {level['color']}; "
                f"font-size: 8pt; font-weight: bold;"
            )
            part_container.addWidget(level_label)
            
            part_edit = QLineEdit()
            part_edit.setPlaceholderText("0" * level['length'])
            part_edit.setMaxLength(level['length'])
            part_edit.setAlignment(Qt.AlignCenter)
            part_edit.setStyleSheet(f"""
                QLineEdit {{
                    border: 2px solid {level['color']};
                    border-radius: 4px;
                    padding: 6px;
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                    font-size: 12pt;
                    min-width: 50px;
                }}
                QLineEdit:focus {{
                    background: rgba(25,118,210,0.05);
                }}
            """)
            part_edit.textChanged.connect(self._on_code_changed)
            part_container.addWidget(part_edit)
            
            self.code_parts.append(part_edit)
            
            part_widget = QWidget()
            part_widget.setLayout(part_container)
            code_parts_layout.addWidget(part_widget)
        
        code_parts_layout.addStretch()
        code_layout.addLayout(code_parts_layout)
        
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("📌 کد نهایی:"))
        
        self.code_preview = QLabel("---")
        self.code_preview.setStyleSheet("""
            font-family: 'Courier New', monospace;
            font-size: 14pt;
            font-weight: bold;
            color: #273c75;
            padding: 8px 16px;
            background: rgba(39,60,117,0.1);
            border-radius: 6px;
        """)
        preview_layout.addWidget(self.code_preview)
        preview_layout.addStretch()
        
        code_layout.addLayout(preview_layout)
        
        layout.addWidget(code_group)
        
        # حساب والد
        parent_group = QGroupBox("👪 حساب والد")
        parent_layout = QVBoxLayout(parent_group)
        
        self.parent_code = QLineEdit()
        self.parent_code.setPlaceholderText("اختیاری")
        parent_layout.addWidget(self.parent_code)
        
        select_parent_btn = QPushButton("🔍 انتخاب از درخت حساب")
        select_parent_btn.clicked.connect(self._select_parent)
        parent_layout.addWidget(select_parent_btn)
        
        layout.addWidget(parent_group)
        
        # وضعیت
        status_group = QGroupBox("✅ وضعیت")
        status_layout = QHBoxLayout(status_group)
        
        self.is_active = QCheckBox("فعال")
        self.is_active.setChecked(True)
        status_layout.addWidget(self.is_active)
        status_layout.addStretch()
        
        layout.addWidget(status_group)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setObjectName("successBtn")
        save_btn.setMinimumHeight(self.scaled(40))
        save_btn.setMinimumWidth(self.scaled(120))
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.setMinimumHeight(self.scaled(40))
        cancel_btn.setMinimumWidth(self.scaled(120))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _get_structure_info(self):
        parts = []
        for level in self.coding.levels:
            parts.append(f"{level['name']} ({level['length']} رقم)")
        return (
            f"📐 ساختار: {self.coding.separator.join(parts)}\n"
            f"🔢 طول کل کد: {self.coding.get_code_length()} رقم"
        )
    
    def _on_code_changed(self):
        parts = []
        for i, part_edit in enumerate(self.code_parts):
            text = part_edit.text().strip()
            if text:
                parts.append(text)
            else:
                parts.append("_" * self.coding.levels[i]['length'])
        
        code = self.coding.separator.join(parts)
        self.code_preview.setText(code)
    
    def _select_parent(self):
        dialog = ParentAccountSelector(self.coding, self)
        if dialog.exec_():
            parent_code = dialog.get_selected_code()
            if parent_code:
                self.parent_code.setText(parent_code)
    
    def load_account_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM accounts WHERE code = ?", [self.account_code])
                acc = c.fetchone()
                
                if not acc:
                    return
                
                self.name_edit.setText(acc['name'])
                
                type_map = {
                    'asset': '🏦 دارایی (asset)',
                    'liability': '📋 بدهی (liability)',
                    'equity': '💰 سرمایه (equity)',
                    'income': '📈 درآمد (income)',
                    'expense': '💸 هزینه (expense)',
                }
                self.type_combo.setCurrentText(
                    type_map.get(acc['type'], acc['type'])
                )
                
                code = acc['code']
                parts = self.coding.parse_code(code)
                
                for i, part_edit in enumerate(self.code_parts):
                    if i < len(parts):
                        part_edit.setText(parts[i])
                
                self.parent_code.setText(acc['parent_code'] or "")
                self.is_active.setChecked(acc['is_active'] == 1)
        
        except Exception as e:
            print(f"❌ خطا: {e}")
    
    def _get_type_value(self):
        text = self.type_combo.currentText()
        for type_code in ['asset', 'liability', 'equity', 'income', 'expense']:
            if type_code in text:
                return type_code
        return 'asset'
    
    def _check_code_exists(self, code):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code FROM accounts WHERE code = ?", [code])
            return c.fetchone() is not None
    
    def accept(self):
        if not self.coding.levels:
            QMessageBox.warning(self, "خطا", "ساختار کدینگ تنظیم نشده!")
            return
        
        parts = []
        for i, part_edit in enumerate(self.code_parts):
            text = part_edit.text().strip()
            
            if not text:
                QMessageBox.warning(
                    self, "خطا",
                    f"سطح '{self.coding.levels[i]['name']}' را وارد کنید!"
                )
                return
            
            if not text.isdigit():
                QMessageBox.warning(
                    self, "خطا",
                    f"سطح '{self.coding.levels[i]['name']}' فقط عدد!"
                )
                return
            
            if len(text) != self.coding.levels[i]['length']:
                QMessageBox.warning(
                    self, "خطا",
                    f"سطح '{self.coding.levels[i]['name']}' باید "
                    f"{self.coding.levels[i]['length']} رقم باشه!"
                )
                return
            
            parts.append(text)
        
        code = self.coding.format_code(parts)
        
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "خطا", "نام حساب را وارد کنید!")
            return
        
        if not self.account_code and self._check_code_exists(code):
            QMessageBox.warning(self, "خطا", f"کد '{code}' قبلاً ثبت شده!")
            return
        
        level = len(parts)
        parent_code = self.parent_code.text().strip() or None
        type_value = self._get_type_value()
        is_active = 1 if self.is_active.isChecked() else 0
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                if self.account_code:
                    c.execute('''
                        UPDATE accounts 
                        SET code = ?, name = ?, type = ?, 
                            parent_code = ?, level = ?, is_active = ?
                        WHERE code = ?
                    ''', (
                        code, name, type_value, parent_code,
                        level, is_active, self.account_code
                    ))
                else:
                    c.execute('''
                        INSERT INTO accounts 
                        (code, name, type, parent_code, level, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (code, name, type_value, parent_code, level, is_active))
                
                conn.commit()
                super().accept()
        
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "خطا", f"کد '{code}' قبلاً ثبت شده!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا: {e}")
    
    def _apply_dialog_theme(self):
        try:
            c = self.get_theme_colors()
            
            self.setStyleSheet(f"""
                QDialog {{
                    background: {c['bg']};
                    color: {c['text']};
                }}
            """)
            
            for gb in self.findChildren(QGroupBox):
                gb.setStyleSheet(f"""
                    QGroupBox {{
                        background: {c['card']};
                        color: {c['text']};
                        border: 2px solid {c['border']};
                        border-radius: 8px;
                        margin-top: 15px;
                        padding: 15px 10px 10px 10px;
                        font-weight: bold;
                        font-size: 11pt;
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        subcontrol-position: top right;
                        right: 15px;
                        padding: 0 8px;
                        color: {c['selected']};
                        background: {c['bg']};
                    }}
                """)
            
            for le in self.findChildren(QLineEdit):
                if le in self.code_parts:
                    continue
                le.setStyleSheet(f"""
                    QLineEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                        min-height: 28px;
                        font-size: 11pt;
                    }}
                    QLineEdit:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
            for cb in self.findChildren(QComboBox):
                cb.setStyleSheet(f"""
                    QComboBox {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                        min-height: 28px;
                        font-size: 11pt;
                    }}
                    QComboBox:focus {{
                        border: 2px solid {c['selected']};
                    }}
                    QComboBox QAbstractItemView {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        selection-background-color: {c['selected']};
                        selection-color: {c['selected_text']};
                    }}
                """)
            
            for chk in self.findChildren(QCheckBox):
                chk.setStyleSheet(f"""
                    QCheckBox {{
                        color: {c['text']};
                        spacing: 8px;
                        font-size: 11pt;
                    }}
                    QCheckBox::indicator {{
                        width: 20px;
                        height: 20px;
                        border-radius: 4px;
                        border: 2px solid {c['border']};
                        background: {c['bg_alt']};
                    }}
                    QCheckBox::indicator:checked {{
                        background: {c['selected']};
                        border-color: {c['selected']};
                    }}
                """)
            
            for btn in self.findChildren(QPushButton):
                obj = btn.objectName()
                if obj == 'successBtn':
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {c['success']};
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 10px 24px;
                            font-weight: bold;
                            font-size: 11pt;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                        }}
                    """)
                elif obj == 'dangerBtn':
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {c['danger']};
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 10px 24px;
                            font-weight: bold;
                            font-size: 11pt;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                        }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {c['bg_alt']};
                            color: {c['text']};
                            border: 1px solid {c['border']};
                            border-radius: 6px;
                            padding: 8px 16px;
                            font-weight: bold;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                        }}
                    """)
        
        except Exception as e:
            print(f"⚠️ خطا theme: {e}")


# ═══════════════════════════════════════════════════════════
# دیالوگ انتخاب والد
# ═══════════════════════════════════════════════════════════

class ParentAccountSelector(BaseDialog):
    """دیالوگ انتخاب حساب والد از درخت"""
    
    def __init__(self, coding, parent=None):
        super().__init__(base_width=600, base_height=700)
        self.coding = coding
        self.selected_code = None
        
        self.setWindowTitle("👪 انتخاب حساب والد")
        self.setModal(True)
        
        self.setup_ui()
        self.load_tree()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 جستجو:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("کد یا نام...")
        self.search_input.textChanged.connect(self.filter_tree)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["کد", "نام حساب"])
        self.tree.setColumnWidth(0, self.scaled(200))
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.tree)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("✅ انتخاب")
        ok_btn.setObjectName("successBtn")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def load_tree(self):
        self.tree.clear()
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT code, name, parent_code, is_active
                    FROM accounts
                    WHERE is_active = 1
                    ORDER BY code
                ''')
                accounts = [dict(row) for row in c.fetchall()]
            
            items = {}
            for acc in accounts:
                item = QTreeWidgetItem()
                
                icon_map = {
                    'asset': '🏦', 'liability': '📋',
                    'equity': '💰', 'income': '📈', 'expense': '💸',
                }
                icon = icon_map.get(acc.get('type', ''), '📄')
                
                item.setText(0, f"{icon} {acc['code']}")
                item.setText(1, acc['name'])
                item.setData(0, Qt.UserRole, acc['code'])
                
                parts = self.coding.parse_code(acc['code'])
                level = len(parts)
                if 0 < level <= len(self.coding.levels):
                    color = self.coding.levels[level - 1]['color']
                    item.setForeground(0, QColor(color))
                    item.setForeground(1, QColor(color))
                
                items[acc['code']] = item
            
            root_items = []
            for acc in accounts:
                item = items[acc['code']]
                parent_code = acc.get('parent_code')
                
                if parent_code and parent_code in items:
                    items[parent_code].addChild(item)
                else:
                    root_items.append(item)
            
            self.tree.addTopLevelItems(root_items)
            self.tree.expandToDepth(1)
        
        except Exception as e:
            print(f"❌ خطا: {e}")
    
    def filter_tree(self):
        text = self.search_input.text().lower().strip()
        
        for i in range(self.tree.topLevelItemCount()):
            self._filter_item(self.tree.topLevelItem(i), text)
    
    def _filter_item(self, item, text):
        if not text:
            item.setHidden(False)
            for i in range(item.childCount()):
                self._filter_item(item.child(i), text)
            return True
        
        code = item.text(0).lower()
        name = item.text(1).lower()
        match = text in code or text in name
        
        child_match = False
        for i in range(item.childCount()):
            if self._filter_item(item.child(i), text):
                child_match = True
        
        visible = match or child_match
        item.setHidden(not visible)
        
        if child_match:
            item.setExpanded(True)
        
        return visible
    
    def get_selected_code(self):
        item = self.tree.currentItem()
        if item:
            return item.data(0, Qt.UserRole)
        return None
    
    def accept(self):
        self.selected_code = self.get_selected_code()
        if self.selected_code:
            super().accept()
        else:
            QMessageBox.warning(self, "خطا", "یک حساب انتخاب کنید!")
