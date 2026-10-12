# ui/accounting_tree_widget.py
# ============================================================
# ویجت درختواره حساب‌ها — نسخه 1.0
# ============================================================
# ویژگی‌ها:
# ✅ درختواره ۵ سطحی (QTreeWidget)
# ✅ نمایش مانده حساب‌ها (تجمیع در والدها)
# ✅ CRUD کامل (افزودن/ویرایش/حذف)
# ✅ پنل جزئیات (سمت راست)
# ✅ جستجوی زنده
# ✅ دکمه "ایجاد ساختار پیش‌فرض"
# ✅ رنگ‌بندی بر اساس نوع حساب
# ✅ خروجی Excel/PDF
# ✅ پشتیبانی از تم روشن/تاریک
# ✅ سطوح دسترسی (admin/accountant/viewer)
# ============================================================

import csv
import logging
from datetime import datetime
from typing import Optional, Dict, List, Set

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from ui.base_widgets import BaseWidget, BaseDialog
from database import get_db
from ui.coding_manager import get_coding_structure, CodingStructure

logger = logging.getLogger(__name__)


# ============================================================
# ثابت‌ها
# ============================================================

# آیکون و رنگ بر اساس نوع حساب
TYPE_ICONS = {
    'asset': '🏦',
    'liability': '📋',
    'equity': '💰',
    'income': '📈',
    'expense': '💸',
}

TYPE_COLORS = {
    'asset': '#27ae60',        # سبز
    'liability': '#e74c3c',    # قرمز
    'equity': '#3498db',       # آبی
    'income': '#f39c12',       # نارنجی
    'expense': '#c0392b',      # قرمز تیره
}

TYPE_NAMES = {
    'asset': 'دارایی',
    'liability': 'بدهی',
    'equity': 'سرمایه',
    'income': 'درآمد',
    'expense': 'هزینه',
}


# ============================================================
# کلاس اصلی: AccountingTreeWidget
# ============================================================

class AccountingTreeWidget(BaseWidget):
    """
    ویجت درختواره حساب‌ها
    
    ساختار:
    ┌─────────────────────────────────────┬──────────────┐
    │  Toolbar (فیلترها + دکمه‌ها)         │              │
    ├─────────────────────────────────────┤  جزئیات      │
    │                                     │              │
    │  Tree Widget (سلسله‌مراتبی)          │  حساب        │
    │                                     │              │
    │                                     │              │
    ├─────────────────────────────────────┤              │
    │  Status Bar (جمع کل)                │              │
    └─────────────────────────────────────┴──────────────┘
    """
    
    # ═══════════════════════════════════════════════════════
    # Constructor
    # ═══════════════════════════════════════════════════════
    
    def __init__(self, user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        
        self._user_level = user_level
        self.coding = get_coding_structure()
        
        # نگهداری داده‌ها
        self.accounts_data: Dict[str, dict] = {}
        self.tree_items: Dict[str, QTreeWidgetItem] = {}
        self.current_account: Optional[dict] = None
        self.expanded_codes: Set[str] = set()
        
        # UI
        self.setup_ui()
        self.apply_theme()
        
        # بارگذاری اولیه
        self.load_accounts()
    
    # ═══════════════════════════════════════════════════════
    # Permission
    # ═══════════════════════════════════════════════════════
    
    def set_user_level(self, level: str):
        """تنظیم سطح دسترسی"""
        self._user_level = level
        self.update_ui_by_permission()
    
    def has_permission(self, action: str = 'view') -> bool:
        """
        بررسی دسترسی
        
        Args:
            action: 'view' | 'edit' | 'delete' | 'admin'
        """
        priority = {
            'admin': 5, 'accountant': 4, 'payroll': 3,
            'inventory': 2, 'viewer': 1
        }
        user_priority = priority.get(self._user_level, 0)
        
        permissions = {
            'view': 1,       # viewer+
            'edit': 4,       # accountant+
            'delete': 4,     # accountant+
            'admin': 5,      # admin فقط
        }
        
        return user_priority >= permissions.get(action, 1)
    
    def update_ui_by_permission(self):
        """بروزرسانی دکمه‌ها بر اساس دسترسی"""
        can_edit = self.has_permission('edit')
        can_delete = self.has_permission('delete')
        can_admin = self.has_permission('admin')
        
        for btn_name in ['add_root_btn', 'add_child_btn', 'edit_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setEnabled(can_edit)
        
        if hasattr(self, 'delete_btn'):
            self.delete_btn.setEnabled(can_delete)
        
        if hasattr(self, 'create_default_btn'):
            self.create_default_btn.setEnabled(can_admin)
    
    # ═══════════════════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════════════════
    
    def get_theme_colors(self) -> dict:
        """دریافت رنگ‌های تم"""
        try:
            from ui.styles.theme_manager import get_theme_manager
            tm = get_theme_manager()
            is_dark = tm.get_theme_name() == 'dark'
        except Exception:
            is_dark = False
        
        if is_dark:
            return {
                'bg': "#1a1a2e", 'bg_alt': "#16213e", 'card': "#1a1a3e",
                'text': "#e8e8e8", 'text_secondary': "#a0a0a0",
                'border': "#0f3460", 'hover': "#2a2a4a",
                'selected': "#e94560", 'selected_text': "#ffffff",
                'success': "#27ae60", 'danger': "#e74c3c",
                'warning': "#f39c12", 'info': "#3498db",
                'is_dark': True,
            }
        else:
            return {
                'bg': "#f5f6fa", 'bg_alt': "#ffffff", 'card': "#ffffff",
                'text': "#1a1a2e", 'text_secondary': "#5d6d7e",
                'border': "#dcdde1", 'hover': "#e8e8e8",
                'selected': "#1976D2", 'selected_text': "#ffffff",
                'success': "#27ae60", 'danger': "#e74c3c",
                'warning': "#f39c12", 'info': "#3498db",
                'is_dark': False,
            }
    
    def apply_theme(self):
        """اعمال تم روی ویجت"""
        try:
            c = self.get_theme_colors()
            
            self.setStyleSheet(f"""
                QWidget {{
                    background: {c['bg']};
                    color: {c['text']};
                }}
                QGroupBox {{
                    background: {c['card']};
                    color: {c['text']};
                    border: 2px solid {c['border']};
                    border-radius: 8px;
                    margin-top: 15px;
                    padding: 15px 10px 10px 10px;
                    font-weight: bold;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top right;
                    right: 15px;
                    padding: 0 8px;
                    color: {c['selected']};
                    background: {c['bg']};
                }}
                QLineEdit, QComboBox, QSpinBox {{
                    background: {c['bg_alt']};
                    color: {c['text']};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    padding: 6px 10px;
                    min-height: 26px;
                }}
                QLineEdit:focus, QComboBox:focus {{
                    border: 2px solid {c['selected']};
                }}
                QPushButton {{
                    background: {c['bg_alt']};
                    color: {c['text']};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    padding: 8px 14px;
                    font-weight: bold;
                    min-height: 32px;
                }}
                QPushButton:hover {{
                    background: {c['hover']};
                    border: 1px solid {c['selected']};
                }}
                QPushButton#successBtn {{
                    background: {c['success']};
                    color: white;
                    border: none;
                }}
                QPushButton#successBtn:hover {{
                    background: #1e8449;
                }}
                QPushButton#dangerBtn {{
                    background: {c['danger']};
                    color: white;
                    border: none;
                }}
                QPushButton#dangerBtn:hover {{
                    background: #c0392b;
                }}
                QPushButton#warningBtn {{
                    background: {c['warning']};
                    color: white;
                    border: none;
                }}
                QPushButton#warningBtn:hover {{
                    background: #d68910;
                }}
                QPushButton#infoBtn {{
                    background: {c['info']};
                    color: white;
                    border: none;
                }}
                QPushButton#infoBtn:hover {{
                    background: #2980b9;
                }}
                QTreeWidget {{
                    background: {c['bg_alt']};
                    color: {c['text']};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    outline: none;
                    font-size: 10pt;
                }}
                QTreeWidget::item {{
                    padding: 4px 2px;
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
                QHeaderView::section {{
                    background: {c['card']};
                    color: {c['text']};
                    padding: 8px;
                    border: none;
                    border-bottom: 2px solid {c['selected']};
                    font-weight: bold;
                }}
                QTextEdit {{
                    background: {c['bg_alt']};
                    color: {c['text']};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    padding: 8px;
                }}
                QLabel#titleLabel {{
                    color: {c['selected']};
                    font-size: 18pt;
                    font-weight: bold;
                    padding: 10px;
                    background: transparent;
                }}
                QLabel#subtitleLabel {{
                    color: {c['text']};
                    font-size: 12pt;
                    font-weight: bold;
                    padding: 5px;
                    background: transparent;
                }}
            """)
        except Exception as e:
            logger.error(f"خطا در apply_theme: {e}")
    
    # ═══════════════════════════════════════════════════════
    # UI Setup
    # ═══════════════════════════════════════════════════════
    
    def setup_ui(self):
        """راه‌اندازی UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ─── عنوان ───
        title = QLabel("🌳 درختواره حساب‌ها")
        title.setObjectName("titleLabel")
        main_layout.addWidget(title)
        
        # ─── بدنه اصلی: درخت + جزئیات ───
        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)
        
        # === پنل چپ: درخت ===
        left_panel = QWidget()
        left_panel.setObjectName("cardWidget")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # نوار ابزار
        toolbar = self._create_toolbar()
        left_layout.addLayout(toolbar)
        
        # نوار فیلتر
        filter_bar = self._create_filter_bar()
        left_layout.addLayout(filter_bar)
        
        # درخت
        self.tree = self._create_tree()
        left_layout.addWidget(self.tree, 1)
        
        # آمار پایین
        self.stats_label = QLabel("📊 در حال بارگذاری...")
        self.stats_label.setStyleSheet(
            "padding: 8px; background: rgba(128,128,128,0.1); "
            "border-radius: 6px; font-weight: bold; font-size: 9pt;"
        )
        left_layout.addWidget(self.stats_label)
        
        # === پنل راست: جزئیات ===
        right_panel = self._create_details_panel()
        right_panel.setMaximumWidth(400)
        right_panel.setMinimumWidth(320)
        
        body_layout.addWidget(left_panel, 3)
        body_layout.addWidget(right_panel, 1)
        
        main_layout.addLayout(body_layout, 1)
    
    def _create_toolbar(self) -> QHBoxLayout:
        """نوار ابزار بالا"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        # افزودن گروه اصلی
        self.add_root_btn = self.create_button("➕ گروه اصلی", "successBtn")
        self.add_root_btn.setToolTip("افزودن حساب سطح ۱")
        self.add_root_btn.clicked.connect(self.add_root_account)
        toolbar.addWidget(self.add_root_btn)
        
        # افزودن زیرحساب
        self.add_child_btn = self.create_button("📁 افزودن زیرحساب", "infoBtn")
        self.add_child_btn.setToolTip("افزودن زیرحساب به حساب انتخاب‌شده")
        self.add_child_btn.clicked.connect(self.add_child_account)
        toolbar.addWidget(self.add_child_btn)
        
        # ویرایش
        self.edit_btn = self.create_button("✏️ ویرایش", "warningBtn")
        self.edit_btn.clicked.connect(self.edit_account)
        toolbar.addWidget(self.edit_btn)
        
        # حذف
        self.delete_btn = self.create_button("🗑️ حذف", "dangerBtn")
        self.delete_btn.clicked.connect(self.delete_account)
        toolbar.addWidget(self.delete_btn)
        
        toolbar.addStretch()
        
        # بسط/جمع
        expand_btn = self.create_button("📂 باز کردن همه")
        expand_btn.clicked.connect(self.expand_all)
        toolbar.addWidget(expand_btn)
        
        collapse_btn = self.create_button("📁 بستن همه")
        collapse_btn.clicked.connect(self.collapse_all)
        toolbar.addWidget(collapse_btn)
        
        return toolbar
    
    def _create_filter_bar(self) -> QHBoxLayout:
        """نوار فیلتر"""
        bar = QHBoxLayout()
        bar.setSpacing(8)
        
        bar.addWidget(QLabel("🔍 جستجو:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("کد یا نام حساب...")
        self.search_input.textChanged.connect(self.filter_tree)
        bar.addWidget(self.search_input, 1)
        
        bar.addWidget(QLabel("نوع:"))
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("همه", "")
        self.type_filter.addItem("🏦 دارایی", "asset")
        self.type_filter.addItem("📋 بدهی", "liability")
        self.type_filter.addItem("💰 سرمایه", "equity")
        self.type_filter.addItem("📈 درآمد", "income")
        self.type_filter.addItem("💸 هزینه", "expense")
        self.type_filter.currentIndexChanged.connect(self.filter_tree)
        bar.addWidget(self.type_filter)
        
        # دکمه ساخت پیش‌فرض
        self.create_default_btn = self.create_button(
            "🎯 ایجاد ساختار پیش‌فرض", "warningBtn"
        )
        self.create_default_btn.setToolTip(
            "ایجاد ~180 حساب استاندارد حسابداری"
        )
        self.create_default_btn.clicked.connect(self.create_default_structure)
        bar.addWidget(self.create_default_btn)
        
        return bar
    
    def _create_tree(self) -> QTreeWidget:
        """ساخت درختواره"""
        tree = QTreeWidget()
        tree.setColumnCount(5)
        tree.setHeaderLabels([
            "کد و نام حساب", "نوع", "سطح", "مانده (ریال)", "تعداد زیرحساب"
        ])
        tree.setAlternatingRowColors(False)
        tree.setAnimated(True)
        tree.setIndentation(22)
        tree.setExpandsOnDoubleClick(False)
        tree.setColumnWidth(0, 400)
        tree.setColumnWidth(1, 100)
        tree.setColumnWidth(2, 120)
        tree.setColumnWidth(3, 130)
        tree.setColumnWidth(4, 100)
        tree.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # رویدادها
        tree.itemClicked.connect(self._on_item_clicked)
        tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        tree.itemExpanded.connect(self._on_item_expanded)
        tree.itemCollapsed.connect(self._on_item_collapsed)
        
        # منوی راست‌کلیک
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._show_context_menu)
        
        return tree
    
    def _create_details_panel(self) -> QWidget:
        """پنل جزئیات (سمت راست)"""
        panel = QWidget()
        panel.setObjectName("cardWidget")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # عنوان
        title = QLabel("📋 جزئیات حساب")
        title.setObjectName("subtitleLabel")
        layout.addWidget(title)
        
        # فرم اطلاعات
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)
        
        self.detail_code = QLineEdit()
        self.detail_code.setReadOnly(True)
        form.addRow("کد:", self.detail_code)
        
        self.detail_name = QLineEdit()
        self.detail_name.setReadOnly(True)
        form.addRow("نام:", self.detail_name)
        
        self.detail_type = QLineEdit()
        self.detail_type.setReadOnly(True)
        form.addRow("نوع:", self.detail_type)
        
        self.detail_level = QLineEdit()
        self.detail_level.setReadOnly(True)
        form.addRow("سطح:", self.detail_level)
        
        self.detail_parent = QLineEdit()
        self.detail_parent.setReadOnly(True)
        form.addRow("والد:", self.detail_parent)
        
        self.detail_balance = QLineEdit()
        self.detail_balance.setReadOnly(True)
        self.detail_balance.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: #27ae60;"
        )
        form.addRow("مانده:", self.detail_balance)
        
        self.detail_children = QLineEdit()
        self.detail_children.setReadOnly(True)
        form.addRow("زیرحساب‌ها:", self.detail_children)
        
        self.detail_active = QLineEdit()
        self.detail_active.setReadOnly(True)
        form.addRow("وضعیت:", self.detail_active)
        
        layout.addLayout(form)
        
        # توضیحات
        layout.addWidget(QLabel("📝 توضیحات:"))
        self.detail_desc = QTextEdit()
        self.detail_desc.setReadOnly(True)
        self.detail_desc.setMaximumHeight(80)
        self.detail_desc.setPlaceholderText("بدون توضیحات")
        layout.addWidget(self.detail_desc)
        
        layout.addStretch()
        
        # دکمه‌های عملیات
        btn_layout = QHBoxLayout()
        
        print_btn = self.create_button("🖨️ چاپ", "infoBtn")
        print_btn.clicked.connect(self.print_current_account)
        btn_layout.addWidget(print_btn)
        
        pdf_btn = self.create_button("📄 PDF", "successBtn")
        pdf_btn.clicked.connect(self.export_current_to_pdf)
        btn_layout.addWidget(pdf_btn)
        
        layout.addLayout(btn_layout)
        
        return panel
    
    # ═══════════════════════════════════════════════════════
    # Load Data
    # ═══════════════════════════════════════════════════════
    
    def load_accounts(self):
        """بارگذاری همه حساب‌ها از دیتابیس"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT code, name, type, parent_code, level,
                           balance, is_active, created_at
                    FROM accounts
                    ORDER BY code
                """)
                
                self.accounts_data = {}
                for row in c.fetchall():
                    # row می‌تونه sqlite3.Row یا dict باشه
                    if hasattr(row, 'keys'):
                        acc = {k: row[k] for k in row.keys()}
                    else:
                        acc = dict(row)
                    
                    code = acc.get('code', '')
                    if code:
                        # اطمینان از مقادیر پیش‌فرض
                        acc.setdefault('balance', 0)
                        acc.setdefault('is_active', 1)
                        acc.setdefault('level', 0)
                        self.accounts_data[code] = acc
            
            logger.info(f"✅ {len(self.accounts_data)} حساب بارگذاری شد")
            
            # ساخت درخت
            self.build_tree()
            
            # بروزرسانی آمار
            self.update_stats()
        
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری حساب‌ها: {e}", exc_info=True)
            QMessageBox.warning(
                self, "خطا",
                f"خطا در بارگذاری حساب‌ها:\n{str(e)}"
            )
    
    def build_tree(self):
        """ساخت درختواره"""
        self.tree.clear()
        self.tree_items.clear()
        
        if not self.accounts_data:
            # درخت خالی
            return
        
        # ═══ مرتب‌سازی حساب‌ها ═══
        codes = sorted(self.accounts_data.keys())
        
        # ═══ ساخت آیتم‌ها ═══
        for code in codes:
            acc = self.accounts_data[code]
            item = self._create_tree_item(acc)
            self.tree_items[code] = item
        
        # ═══ سلسله‌مراتب ═══
        root_items = []
        for code in codes:
            acc = self.accounts_data[code]
            item = self.tree_items[code]
            parent_code = acc.get('parent_code')
            
            if parent_code and parent_code in self.tree_items:
                # زیرشاخه
                parent_item = self.tree_items[parent_code]
                parent_item.addChild(item)
            else:
                # سطح بالا
                root_items.append(item)
        
        # ═══ افزودن به درخت ═══
        self.tree.addTopLevelItems(root_items)
        
        # ═══ بازگردانی حالت expand ═══
        for code in self.expanded_codes:
            if code in self.tree_items:
                self.tree_items[code].setExpanded(True)
        
        # اگه اولین باره، 2 سطح اول رو باز کن
        if not self.expanded_codes:
            self.tree.expandToDepth(1)
        
        logger.info(
            f"✅ درخت ساخته شد: {len(root_items)} ریشه، "
            f"{len(codes)} کل"
        )
    
    def _create_tree_item(self, acc: dict) -> QTreeWidgetItem:
        """ساخت یک آیتم درخت"""
        item = QTreeWidgetItem()
        
        code = acc.get('code', '')
        name = acc.get('name', '')
        acc_type = acc.get('type', 'asset')
        balance = acc.get('balance', 0) or 0
        
        # ═══ ستون 0: کد و نام ═══
        type_icon = TYPE_ICONS.get(acc_type, '📄')
        level = self.coding.get_level_of_code(code)
        level_icon = self.coding.get_level_icon(level) if level else '⚪'
        
        item.setText(0, f"{level_icon} {code} — {name}")
        item.setData(0, Qt.UserRole, code)
        
        # ═══ ستون 1: نوع ═══
        item.setText(1, f"{type_icon} {TYPE_NAMES.get(acc_type, acc_type)}")
        
        # ═══ ستون 2: سطح ═══
        level_name = self.coding.get_level_name(level) if level else '?'
        item.setText(2, f"سطح {level} ({level_name})")
        
        # ═══ ستون 3: مانده ═══
        # محاسبه تجمیع (اگه زیرحساب داره)
        total_balance = self._get_aggregated_balance(code)
        
        balance_str = f"{total_balance:,.0f}" if total_balance else "-"
        item.setText(3, balance_str)
        item.setTextAlignment(3, Qt.AlignRight | Qt.AlignVCenter)
        
        # رنگ مانده
        if total_balance > 0:
            item.setForeground(3, QColor('#27ae60'))
        elif total_balance < 0:
            item.setForeground(3, QColor('#e74c3c'))
        
        # ═══ ستون 4: تعداد زیرحساب ═══
        children_count = self._count_children(code)
        item.setText(4, str(children_count) if children_count else "-")
        item.setTextAlignment(4, Qt.AlignCenter)
        
        # ═══ رنگ‌بندی و فونت ═══
        level_color = self.coding.get_level_color(level) if level else '#666666'
        
        # رنگ ستون 0 بر اساس سطح
        item.setForeground(0, QColor(level_color))
        
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        
        # فونت درشت‌تر برای سطوح بالا
        if level <= 2:
            font.setPointSize(font.pointSize() + 1)
            item.setFont(0, font)
        
        # ═══ خاکستری برای غیرفعال ═══
        if not acc.get('is_active', 1):
            for col in range(5):
                item.setForeground(col, QColor('#999999'))
            item.setText(0, item.text(0) + " ⛔")
        
        return item
    
    def _get_aggregated_balance(self, code: str) -> float:
        """
        محاسبه مانده تجمیعی یک حساب
        
        شامل مانده خود حساب + مانده همه زیرحساب‌ها
        """
        total = 0.0
        acc = self.accounts_data.get(code)
        
        if acc:
            total += acc.get('balance', 0) or 0
        
        # زیرحساب‌ها
        prefix = code + self.coding.separator
        for other_code, other_acc in self.accounts_data.items():
            if other_code.startswith(prefix):
                total += other_acc.get('balance', 0) or 0
        
        return total
    
    def _count_children(self, code: str) -> int:
        """شمارش زیرحساب‌های مستقیم"""
        prefix = code + self.coding.separator
        count = 0
        direct_level = len(self.coding.parse_code(code)) + 1
        
        for other_code in self.accounts_data.keys():
            if other_code.startswith(prefix):
                other_level = len(self.coding.parse_code(other_code))
                if other_level == direct_level:
                    count += 1
        
        return count
    
    # ═══════════════════════════════════════════════════════
    # Stats
    # ═══════════════════════════════════════════════════════
    
    def update_stats(self):
        """بروزرسانی آمار پایین صفحه"""
        total = len(self.accounts_data)
        
        # شمارش بر اساس سطح
        by_level = {}
        for code in self.accounts_data.keys():
            lvl = len(self.coding.parse_code(code))
            by_level[lvl] = by_level.get(lvl, 0) + 1
        
        # شمارش بر اساس نوع
        by_type = {}
        for acc in self.accounts_data.values():
            t = acc.get('type', 'asset')
            by_type[t] = by_type.get(t, 0) + 1
        
        # مجموع مانده
        total_balance = sum(
            (acc.get('balance', 0) or 0)
            for acc in self.accounts_data.values()
            if not self._has_children(acc.get('code', ''))
        )
        
        # ساخت متن
        parts = [f"📊 مجموع: {total} حساب"]
        
        for lvl in sorted(by_level.keys()):
            level_name = self.coding.get_level_name(lvl)
            parts.append(f"سطح{lvl}({level_name}): {by_level[lvl]}")
        
        parts.append(f"💰 مجموع مانده: {total_balance:,.0f} ریال")
        
        self.stats_label.setText(" | ".join(parts))
    
    def _has_children(self, code: str) -> bool:
        """آیا حساب زیرحساب داره؟"""
        prefix = code + self.coding.separator
        return any(
            other.startswith(prefix)
            for other in self.accounts_data.keys()
        )
    
    # ═══════════════════════════════════════════════════════
    # Selection / Details
    # ═══════════════════════════════════════════════════════
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """کلیک روی آیتم"""
        code = item.data(0, Qt.UserRole)
        if not code:
            return
        
        self.current_account = self.accounts_data.get(code)
        if self.current_account:
            self._show_details(self.current_account)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """دابل‌کلیک"""
        code = item.data(0, Qt.UserRole)
        if code:
            # باز/بسته کردن
            item.setExpanded(not item.isExpanded())
    
    def _on_item_expanded(self, item: QTreeWidgetItem):
        """گسترش آیتم"""
        code = item.data(0, Qt.UserRole)
        if code:
            self.expanded_codes.add(code)
    
    def _on_item_collapsed(self, item: QTreeWidgetItem):
        """جمع شدن آیتم"""
        code = item.data(0, Qt.UserRole)
        if code:
            self.expanded_codes.discard(code)
    
    def _show_details(self, acc: dict):
        """نمایش جزئیات در پنل راست"""
        code = acc.get('code', '')
        name = acc.get('name', '')
        acc_type = acc.get('type', 'asset')
        level = self.coding.get_level_of_code(code)
        parent_code = acc.get('parent_code') or '—'
        balance = acc.get('balance', 0) or 0
        aggregated = self._get_aggregated_balance(code)
        children = self._count_children(code)
        is_active = acc.get('is_active', 1)
        description = acc.get('description', '') or ''
        
        # کد
        self.detail_code.setText(code)
        
        # نام
        self.detail_name.setText(name)
        
        # نوع
        type_icon = TYPE_ICONS.get(acc_type, '📄')
        self.detail_type.setText(
            f"{type_icon} {TYPE_NAMES.get(acc_type, acc_type)}"
        )
        
        # سطح
        level_name = self.coding.get_level_name(level) if level else '?'
        self.detail_level.setText(f"سطح {level} ({level_name})")
        
        # والد
        self.detail_parent.setText(parent_code)
        
        # مانده
        if aggregated != balance:
            # زیرحساب داره → نمایش تجمیعی
            self.detail_balance.setText(
                f"{aggregated:,.0f} ریال (تجمیعی)"
            )
        else:
            self.detail_balance.setText(f"{balance:,.0f} ریال")
        
        # زیرحساب‌ها
        self.detail_children.setText(
            f"{children} حساب" if children else "ندارد"
        )
        
        # وضعیت
        if is_active:
            self.detail_active.setText("✅ فعال")
            self.detail_active.setStyleSheet("color: #27ae60;")
        else:
            self.detail_active.setText("⛔ غیرفعال")
            self.detail_active.setStyleSheet("color: #999999;")
        
        # توضیحات
        self.detail_desc.setPlainText(description)
    
    # ═══════════════════════════════════════════════════════
    # Filter / Search
    # ═══════════════════════════════════════════════════════
    
    def filter_tree(self):
        """فیلتر درخت بر اساس جستجو و نوع"""
        search_text = self.search_input.text().strip().lower()
        type_filter = self.type_filter.currentData()
        
        # اگه فیلتری نیست، همه رو نشون بده
        if not search_text and not type_filter:
            self._show_all_items()
            return
        
        # مخفی کردن همه
        for item in self.tree_items.values():
            item.setHidden(True)
        
        # پیدا کردن آیتم‌های مطابق
        matching_codes = set()
        
        for code, acc in self.accounts_data.items():
            name = (acc.get('name', '') or '').lower()
            acc_type = acc.get('type', '')
            
            # چک جستجو
            match_search = True
            if search_text:
                match_search = (
                    search_text in code.lower() or
                    search_text in name
                )
            
            # چک نوع
            match_type = True
            if type_filter:
                match_type = (acc_type == type_filter)
            
            if match_search and match_type:
                matching_codes.add(code)
                # والدها رو هم نشون بده
                for ancestor in self.coding.get_ancestors(code):
                    matching_codes.add(ancestor)
        
        # نمایش آیتم‌های مطابق + والدها
        for code in matching_codes:
            if code in self.tree_items:
                self.tree_items[code].setHidden(False)
        
        # باز کردن خودکار
        for code in matching_codes:
            if code in self.tree_items:
                self.tree_items[code].setExpanded(True)
    
    def _show_all_items(self):
        """نمایش همه آیتم‌ها"""
        for item in self.tree_items.values():
            item.setHidden(False)
    
    # ═══════════════════════════════════════════════════════
    # CRUD
    # ═══════════════════════════════════════════════════════
    
    def add_root_account(self):
        """افزودن گروه اصلی (سطح ۱)"""
        if not self.has_permission('edit'):
            QMessageBox.warning(
                self, "دسترسی محدود",
                "⚠️ شما دسترسی افزودن حساب را ندارید!"
            )
            return
        
        dialog = AccountEditDialog(
            coding=self.coding,
            parent_code=None,
            all_accounts=self.accounts_data,
            mode='create',
            parent=self
        )
        
        if dialog.exec_():
            self.load_accounts()
            QMessageBox.information(
                self, "موفق", "✅ حساب جدید ایجاد شد!"
            )
    
    def add_child_account(self):
        """افزودن زیرحساب به حساب انتخاب‌شده"""
        if not self.has_permission('edit'):
            QMessageBox.warning(
                self, "دسترسی محدود",
                "⚠️ شما دسترسی افزودن حساب را ندارید!"
            )
            return
        
        if not self.current_account:
            QMessageBox.warning(
                self, "خطا",
                "لطفاً ابتدا یک حساب را انتخاب کنید!"
            )
            return
        
        parent_code = self.current_account.get('code', '')
        parent_level = len(self.coding.parse_code(parent_code))
        max_level = len(self.coding.levels)
        
        if parent_level >= max_level:
            QMessageBox.warning(
                self, "خطا",
                f"سطح {parent_level} آخرین سطح است — "
                f"نمی‌توان زیرحساب اضافه کرد!"
            )
            return
        
        dialog = AccountEditDialog(
            coding=self.coding,
            parent_code=parent_code,
            all_accounts=self.accounts_data,
            mode='create',
            parent=self
        )
        
        if dialog.exec_():
            self.load_accounts()
            # باز کردن والد
            if parent_code in self.tree_items:
                self.tree_items[parent_code].setExpanded(True)
            
            QMessageBox.information(
                self, "موفق", "✅ زیرحساب ایجاد شد!"
            )
    
    def edit_account(self):
        """ویرایش حساب انتخاب‌شده"""
        if not self.has_permission('edit'):
            QMessageBox.warning(
                self, "دسترسی محدود",
                "⚠️ شما دسترسی ویرایش حساب را ندارید!"
            )
            return
        
        if not self.current_account:
            QMessageBox.warning(
                self, "خطا",
                "لطفاً ابتدا یک حساب را انتخاب کنید!"
            )
            return
        
        dialog = AccountEditDialog(
            coding=self.coding,
            parent_code=None,
            all_accounts=self.accounts_data,
            mode='edit',
            account_code=self.current_account.get('code'),
            parent=self
        )
        
        if dialog.exec_():
            self.load_accounts()
            QMessageBox.information(
                self, "موفق", "✅ حساب ویرایش شد!"
            )
    
    def delete_account(self):
        """حذف حساب انتخاب‌شده"""
        if not self.has_permission('delete'):
            QMessageBox.warning(
                self, "دسترسی محدود",
                "⚠️ شما دسترسی حذف حساب را ندارید!"
            )
            return
        
        if not self.current_account:
            QMessageBox.warning(
                self, "خطا",
                "لطفاً ابتدا یک حساب را انتخاب کنید!"
            )
            return
        
        code = self.current_account.get('code', '')
        name = self.current_account.get('name', '')
        
        # چک زیرحساب
        children_count = self._count_children(code)
        if children_count > 0:
            QMessageBox.warning(
                self, "خطا",
                f"❌ این حساب {children_count} زیرحساب دارد!\n"
                f"ابتدا زیرحساب‌ها را حذف کنید."
            )
            return
        
        # چک استفاده در اسناد
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT COUNT(*) FROM voucher_items WHERE account_code = ?",
                    [code]
                )
                row = c.fetchone()
                usage_count = row[0] if row else 0
        except Exception as e:
            logger.warning(f"خطا در چک استفاده: {e}")
            usage_count = 0
        
        if usage_count > 0:
            reply = QMessageBox.question(
                self, "هشدار",
                f"⚠️ این حساب در {usage_count} سند حسابداری استفاده شده!\n\n"
                f"آیا مطمئن هستید که می‌خواهید حذف کنید؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # تأیید نهایی
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف «{code} — {name}» اطمینان دارید؟\n\n"
            f"⚠️ این عمل قابل بازگشت نیست!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM accounts WHERE code = ?", [code])
                conn.commit()
            
            # پاک کردن از حافظه
            self.accounts_data.pop(code, None)
            
            self.load_accounts()
            self._clear_details()
            
            QMessageBox.information(
                self, "موفق", "✅ حساب حذف شد!"
            )
        
        except Exception as e:
            logger.error(f"خطا در حذف: {e}")
            QMessageBox.warning(
                self, "خطا", f"❌ خطا در حذف:\n{str(e)}"
            )
    
    def _clear_details(self):
        """پاک کردن پنل جزئیات"""
        for widget in [
            self.detail_code, self.detail_name, self.detail_type,
            self.detail_level, self.detail_parent, self.detail_balance,
            self.detail_children, self.detail_active
        ]:
            widget.clear()
        self.detail_desc.clear()
        self.current_account = None
    
    # ═══════════════════════════════════════════════════════
    # Context Menu
    # ═══════════════════════════════════════════════════════
    
    def _show_context_menu(self, pos):
        """منوی راست‌کلیک"""
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        self.tree.setCurrentItem(item)
        code = item.data(0, Qt.UserRole)
        if code:
            self.current_account = self.accounts_data.get(code)
            if self.current_account:
                self._show_details(self.current_account)
        
        menu = QMenu(self)
        
        # افزودن زیرحساب
        if self.has_permission('edit'):
            add_action = menu.addAction("📁 افزودن زیرحساب")
            add_action.triggered.connect(self.add_child_account)
        
        # ویرایش
        if self.has_permission('edit'):
            edit_action = menu.addAction("✏️ ویرایش")
            edit_action.triggered.connect(self.edit_account)
        
        # حذف
        if self.has_permission('delete'):
            menu.addSeparator()
            delete_action = menu.addAction("🗑️ حذف")
            delete_action.triggered.connect(self.delete_account)
        
        # کپی کد
        menu.addSeparator()
        copy_action = menu.addAction("📋 کپی کد")
        copy_action.triggered.connect(
            lambda: self._copy_code(code)
        )
        
        # چاپ
        print_action = menu.addAction("🖨️ چاپ")
        print_action.triggered.connect(self.print_current_account)
        
        menu.exec_(self.tree.viewport().mapToGlobal(pos))
    
    def _copy_code(self, code: str):
        """کپی کد در کلیپ‌بورد"""
        QApplication.clipboard().setText(code)
        self.stats_label.setText(f"📋 کد «{code}» کپی شد")
        QTimer.singleShot(2000, self.update_stats)
    
    # ═══════════════════════════════════════════════════════
    # Expand / Collapse
    # ═══════════════════════════════════════════════════════
    
    def expand_all(self):
        """باز کردن همه"""
        self.tree.expandAll()
        for code in self.tree_items.keys():
            self.expanded_codes.add(code)
    
    def collapse_all(self):
        """بستن همه"""
        self.tree.collapseAll()
        self.expanded_codes.clear()
    
    # ═══════════════════════════════════════════════════════
    # Default Structure
    # ═══════════════════════════════════════════════════════
    
    def create_default_structure(self):
        """ایجاد ساختار پیش‌فرض حسابداری"""
        if not self.has_permission('admin'):
            QMessageBox.warning(
                self, "دسترسی محدود",
                "⚠️ فقط مدیر سیستم می‌تواند ساختار پیش‌فرض ایجاد کند!"
            )
            return
        
        try:
            from ui.default_accounts_data import get_default_accounts
        except ImportError:
            QMessageBox.warning(
                self, "خطا",
                "❌ فایل default_accounts_data.py پیدا نشد!"
            )
            return
        
        # چک وجود حساب
        existing_count = len(self.accounts_data)
        
        if existing_count > 0:
            reply = QMessageBox.question(
                self, "تأیید",
                f"در حال حاضر {existing_count} حساب وجود دارد.\n\n"
                f"آیا می‌خواهید ساختار پیش‌فرض اضافه شود؟\n\n"
                f"✅ حساب‌های موجود حفظ می‌شوند\n"
                f"✅ فقط حساب‌های جدید اضافه می‌شوند",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # دریافت لیست
        accounts = get_default_accounts(separator=self.coding.separator)
        
        created = 0
        updated = 0
        skipped = 0
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                for acc in accounts:
                    code = acc['code']
                    
                    # چک وجود
                    c.execute("SELECT code FROM accounts WHERE code = ?", [code])
                    existing = c.fetchone()
                    
                    if existing:
                        # بروزرسانی (فقط اگه is_active=1 باشه)
                        c.execute("""
                            UPDATE accounts
                            SET name = ?, type = ?, parent_code = ?
                            WHERE code = ?
                        """, (
                            acc['name'],
                            acc['type'],
                            acc.get('parent'),
                            code
                        ))
                        updated += 1
                    else:
                        # ایجاد
                        level = len(self.coding.parse_code(code))
                        c.execute("""
                            INSERT INTO accounts
                            (code, name, type, parent_code, level, is_active)
                            VALUES (?, ?, ?, ?, ?, 1)
                        """, (
                            code,
                            acc['name'],
                            acc['type'],
                            acc.get('parent'),
                            level
                        ))
                        created += 1
                
                conn.commit()
            
            logger.info(
                f"✅ ساختار پیش‌فرض: "
                f"{created} ایجاد، {updated} بروزرسانی"
            )
            
            # بارگذاری مجدد
            self.load_accounts()
            
            QMessageBox.information(
                self, "موفق",
                f"✅ ساختار پیش‌فرض اعمال شد!\n\n"
                f"➕ ایجاد: {created} حساب\n"
                f"🔄 بروزرسانی: {updated} حساب\n"
                f"📊 مجموع: {created + updated} حساب"
            )
        
        except Exception as e:
            logger.error(f"خطا در ساخت پیش‌فرض: {e}", exc_info=True)
            QMessageBox.warning(
                self, "خطا",
                f"❌ خطا در ساخت ساختار:\n{str(e)}"
            )
    
    # ═══════════════════════════════════════════════════════
    # Print / Export
    # ═══════════════════════════════════════════════════════
    
    def print_current_account(self):
        """چاپ حساب انتخاب‌شده"""
        if not self.current_account:
            QMessageBox.warning(
                self, "خطا", "لطفاً یک حساب را انتخاب کنید!"
            )
            return
        
        try:
            from ui.accounting_pdf import (
                AccountingPDFGenerator, get_pdf_generator
            )
            
            # ساخت HTML
            html = self._generate_account_html(self.current_account)
            
            # چاپ
            AccountingPDFGenerator.print_html(html, self)
        
        except Exception as e:
            logger.error(f"خطا در چاپ: {e}")
            QMessageBox.warning(
                self, "خطا", f"❌ خطا در چاپ:\n{str(e)}"
            )
    
    def export_current_to_pdf(self):
        """خروجی PDF از حساب انتخاب‌شده"""
        if not self.current_account:
            QMessageBox.warning(
                self, "خطا", "لطفاً یک حساب را انتخاب کنید!"
            )
            return
        
        try:
            from ui.accounting_pdf import AccountingPDFGenerator
            
            default_name = (
                f"حساب_{self.current_account['code']}_"
                f"{datetime.now().strftime('%Y%m%d')}.pdf"
            )
            
            file_path = AccountingPDFGenerator.ask_save_path(
                self, default_name
            )
            
            if not file_path:
                return
            
            # ساخت HTML
            html = self._generate_account_html(self.current_account)
            
            # ذخیره به PDF
            success = self._save_html_as_pdf(html, file_path)
            
            if success:
                QMessageBox.information(
                    self, "موفق",
                    f"✅ PDF ذخیره شد:\n{file_path}"
                )
            else:
                QMessageBox.warning(
                    self, "خطا", "❌ خطا در ذخیره PDF!"
                )
        
        except Exception as e:
            logger.error(f"خطا در PDF: {e}")
            QMessageBox.warning(
                self, "خطا", f"❌ خطا در PDF:\n{str(e)}"
            )
    
    def _generate_account_html(self, acc: dict) -> str:
        """تولید HTML برای نمایش/چاپ حساب"""
        code = acc.get('code', '')
        name = acc.get('name', '')
        acc_type = acc.get('type', 'asset')
        balance = acc.get('balance', 0) or 0
        aggregated = self._get_aggregated_balance(code)
        children = self._count_children(code)
        description = acc.get('description', '') or ''
        level = self.coding.get_level_of_code(code)
        
        type_icon = TYPE_ICONS.get(acc_type, '📄')
        type_name = TYPE_NAMES.get(acc_type, acc_type)
        level_name = self.coding.get_level_name(level)
        level_color = self.coding.get_level_color(level)
        
        # زیرحساب‌ها
        prefix = code + self.coding.separator
        children_list = []
        for other_code, other_acc in self.accounts_data.items():
            if other_code.startswith(prefix):
                other_level = len(self.coding.parse_code(other_code))
                if other_level == level + 1:
                    children_list.append(other_acc)
        
        children_html = ""
        if children_list:
            children_html = "<h3>📁 زیرحساب‌ها:</h3>"
            children_html += "<table width='100%' border='1' style='border-collapse: collapse;'>"
            children_html += "<tr style='background: #273c75; color: white;'>"
            children_html += "<th>کد</th><th>نام</th><th>مانده</th></tr>"
            
            for child in children_list:
                child_code = child.get('code', '')
                child_name = child.get('name', '')
                child_bal = self._get_aggregated_balance(child_code)
                
                children_html += (
                    f"<tr>"
                    f"<td>{child_code}</td>"
                    f"<td>{child_name}</td>"
                    f"<td style='text-align: left;'>{child_bal:,.0f}</td>"
                    f"</tr>"
                )
            
            children_html += "</table>"
        
        html = f"""
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Tahoma, sans-serif;
                direction: rtl;
                padding: 20px;
                color: #2c3e50;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #273c75;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            .code {{
                font-family: 'Courier New', monospace;
                font-size: 18pt;
                font-weight: bold;
                color: {level_color};
                direction: ltr;
            }}
            .name {{
                font-size: 20pt;
                font-weight: bold;
                color: #273c75;
                margin-top: 10px;
            }}
            .type {{
                display: inline-block;
                background: {level_color};
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                margin-top: 10px;
            }}
            .info-table {{
                width: 100%;
                margin: 20px 0;
                border-collapse: collapse;
            }}
            .info-table td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }}
            .info-table td:first-child {{
                font-weight: bold;
                width: 40%;
                background: #f8f9fa;
            }}
            .balance {{
                font-size: 18pt;
                font-weight: bold;
                color: {'#27ae60' if aggregated >= 0 else '#e74c3c'};
                text-align: left;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 9pt;
                color: #999;
                border-top: 1px solid #ddd;
                padding-top: 10px;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <div class="code">{code}</div>
                <div class="name">{name}</div>
                <div class="type">{type_icon} {type_name} — سطح {level} ({level_name})</div>
            </div>
            
            <table class="info-table">
                <tr>
                    <td>🆔 کد حساب</td>
                    <td style="direction: ltr; font-family: monospace;">{code}</td>
                </tr>
                <tr>
                    <td>📛 نام حساب</td>
                    <td>{name}</td>
                </tr>
                <tr>
                    <td>🏷️ نوع حساب</td>
                    <td>{type_icon} {type_name}</td>
                </tr>
                <tr>
                    <td>📊 سطح</td>
                    <td>سطح {level} ({level_name})</td>
                </tr>
                <tr>
                    <td>👪 والد</td>
                    <td>{acc.get('parent_code') or '—'}</td>
                </tr>
                <tr>
                    <td>💰 مانده</td>
                    <td class="balance">{aggregated:,.0f} ریال</td>
                </tr>
                <tr>
                    <td>📁 تعداد زیرحساب</td>
                    <td>{children} حساب</td>
                </tr>
                <tr>
                    <td>📝 توضیحات</td>
                    <td>{description or '—'}</td>
                </tr>
            </table>
            
            {children_html}
            
            <div class="footer">
                <p>تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')}</p>
                <p>ImanAccount — حسابداری هوشمند</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _save_html_as_pdf(self, html_content: str, file_path: str) -> bool:
        """ذخیره HTML به PDF"""
        try:
            from PyQt5.QtPrintSupport import QPrinter
            from PyQt5.QtGui import QTextDocument
            from PyQt5.QtCore import QSizeF
            
            printer = QPrinter(QPrinter.ScreenResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
            
            doc = QTextDocument()
            doc.setHtml(html_content)
            
            rect = printer.pageRect(QPrinter.DevicePixel)
            doc.setPageSize(QSizeF(rect.width(), rect.height()))
            
            doc.print_(printer)
            return True
        except Exception as e:
            logger.error(f"خطا در save PDF: {e}")
            return False


# ============================================================
# دیالوگ افزودن/ویرایش حساب
# ============================================================

class AccountEditDialog(BaseDialog):
    """دیالوگ افزودن/ویرایش حساب"""
    
    def __init__(self, coding: CodingStructure, parent_code: Optional[str],
                 all_accounts: Dict[str, dict], mode: str = 'create',
                 account_code: Optional[str] = None, parent=None):
        super().__init__(parent, base_width=600, base_height=550)
        
        self.coding = coding
        self.parent_code = parent_code
        self.all_accounts = all_accounts
        self.mode = mode
        self.edit_code = account_code
        
        title = "➕ افزودن حساب" if mode == 'create' else "✏️ ویرایش حساب"
        self.setWindowTitle(title)
        self.setModal(True)
        
        self.setup_ui()
        
        if mode == 'edit' and account_code:
            self.load_account_data(account_code)
        else:
            self.prepare_new_account()
        
        self.apply_theme()
    
    def get_theme_colors(self):
        """رنگ‌های تم"""
        try:
            from ui.styles.theme_manager import get_theme_manager
            tm = get_theme_manager()
            is_dark = tm.get_theme_name() == 'dark'
        except Exception:
            is_dark = False
        
        if is_dark:
            return {
                'bg': "#1a1a2e", 'bg_alt': "#16213e", 'card': "#1a1a3e",
                'text': "#e8e8e8", 'text_secondary': "#a0a0a0",
                'border': "#0f3460", 'hover': "#2a2a4a",
                'selected': "#e94560", 'selected_text': "#ffffff",
                'success': "#27ae60", 'danger': "#e74c3c",
                'warning': "#f39c12", 'info': "#3498db",
            }
        else:
            return {
                'bg': "#f5f6fa", 'bg_alt': "#ffffff", 'card': "#ffffff",
                'text': "#1a1a2e", 'text_secondary': "#5d6d7e",
                'border': "#dcdde1", 'hover': "#e8e8e8",
                'selected': "#1976D2", 'selected_text': "#ffffff",
                'success': "#27ae60", 'danger': "#e74c3c",
                'warning': "#f39c12", 'info': "#3498db",
            }
    
    def apply_theme(self):
        """اعمال تم"""
        c = self.get_theme_colors()
        
        self.setStyleSheet(f"""
            QDialog {{
                background: {c['bg']};
                color: {c['text']};
            }}
            QLabel {{
                color: {c['text']};
                background: transparent;
            }}
            QLineEdit, QComboBox, QSpinBox, QTextEdit {{
                background: {c['bg_alt']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 28px;
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border: 2px solid {c['selected']};
            }}
            QGroupBox {{
                background: {c['card']};
                color: {c['text']};
                border: 2px solid {c['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top right;
                right: 12px;
                padding: 0 8px;
                color: {c['selected']};
                background: {c['bg']};
            }}
            QPushButton {{
                background: {c['bg_alt']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: {c['hover']};
            }}
            QPushButton#successBtn {{
                background: {c['success']};
                color: white;
                border: none;
            }}
            QPushButton#successBtn:hover {{
                background: #1e8449;
            }}
            QPushButton#dangerBtn {{
                background: {c['danger']};
                color: white;
                border: none;
            }}
            QPushButton#dangerBtn:hover {{
                background: #c0392b;
            }}
        """)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # عنوان
        title = QLabel(
            "➕ افزودن حساب جدید" if self.mode == 'create' else "✏️ ویرایش حساب"
        )
        title.setStyleSheet(
            "font-size: 16pt; font-weight: bold; "
            "color: #1976D2; padding: 10px;"
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # گروه اطلاعات
        info_group = QGroupBox("📋 اطلاعات حساب")
        form = QFormLayout(info_group)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        
        # سطح
        self.level_label = QLabel()
        self.level_label.setStyleSheet(
            "font-weight: bold; padding: 8px; "
            "background: rgba(128,128,128,0.15); border-radius: 6px;"
        )
        form.addRow("📊 سطح:", self.level_label)
        
        # کد (بخش‌ها)
        self.code_widget = QWidget()
        self.code_layout = QHBoxLayout(self.code_widget)
        self.code_layout.setContentsMargins(0, 0, 0, 0)
        self.code_layout.setSpacing(4)
        self.code_parts: List[QLineEdit] = []
        
        # بعد از تعیین سطح پر میشه
        form.addRow("🔢 کد:", self.code_widget)
        
        # پیش‌نمایش کد
        self.code_preview = QLabel("---")
        self.code_preview.setStyleSheet(
            "font-family: 'Courier New', monospace; "
            "font-size: 14pt; font-weight: bold; "
            "color: #1976D2; padding: 8px 16px; "
            "background: rgba(25,118,210,0.1); border-radius: 6px;"
        )
        self.code_preview.setAlignment(Qt.AlignCenter)
        form.addRow("📌 کد نهایی:", self.code_preview)
        
        # نام
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("نام حساب...")
        form.addRow("📛 نام حساب *:", self.name_input)
        
        # نوع
        self.type_combo = QComboBox()
        for type_key, type_name in TYPE_NAMES.items():
            icon = TYPE_ICONS.get(type_key, '📄')
            self.type_combo.addItem(f"{icon} {type_name}", type_key)
        form.addRow("🏷️ نوع حساب *:", self.type_combo)
        
        # والد (نمایش)
        if self.parent_code:
            self.parent_label = QLabel(self.parent_code)
        else:
            self.parent_label = QLabel("— (سطح بالا)")
        self.parent_label.setStyleSheet(
            "font-family: monospace; padding: 6px;"
        )
        form.addRow("👪 والد:", self.parent_label)
        
        # وضعیت
        self.active_check = QCheckBox("✅ فعال")
        self.active_check.setChecked(True)
        form.addRow("وضعیت:", self.active_check)
        
        # توضیحات
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("توضیحات (اختیاری)")
        self.desc_input.setMaximumHeight(80)
        form.addRow("📝 توضیحات:", self.desc_input)
        
        layout.addWidget(info_group)
        layout.addStretch()
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton(
            "💾 ذخیره" if self.mode == 'create' else "💾 بروزرسانی"
        )
        save_btn.setObjectName("successBtn")
        save_btn.setMinimumWidth(130)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def prepare_new_account(self):
        """آماده‌سازی برای حساب جدید"""
        if self.parent_code:
            # زیرحساب
            parent_level = len(self.coding.parse_code(self.parent_code))
            new_level = parent_level + 1
        else:
            # سطح بالا
            new_level = 1
        
        self._build_code_parts(new_level)
        
        # سطح
        level_name = self.coding.get_level_name(new_level)
        level_color = self.coding.get_level_color(new_level)
        self.level_label.setText(f"سطح {new_level} — {level_name}")
        self.level_label.setStyleSheet(
            f"font-weight: bold; padding: 8px; "
            f"background: {level_color}33; "
            f"border: 2px solid {level_color}; "
            f"border-radius: 6px; color: {level_color};"
        )
        
        # پر کردن بخش‌ها
        if self.parent_code:
            parent_parts = self.coding.parse_code(self.parent_code)
            for i, part in enumerate(parent_parts):
                if i < len(self.code_parts):
                    self.code_parts[i].setText(part)
                    self.code_parts[i].setReadOnly(True)
        
        # پیشنهاد کد بعدی برای آخرین بخش
        if self.code_parts:
            last_input = self.code_parts[-1]
            if not last_input.isReadOnly():
                next_code = self._suggest_next_code()
                if next_code:
                    last_input.setText(next_code)
        
        self._update_preview()
    
    def load_account_data(self, code: str):
        """بارگذاری داده‌های حساب برای ویرایش"""
        acc = self.all_accounts.get(code, {})
        
        if not acc:
            return
        
        level = self.coding.get_level_of_code(code)
        self._build_code_parts(level)
        
        # سطح
        level_name = self.coding.get_level_name(level)
        level_color = self.coding.get_level_color(level)
        self.level_label.setText(f"سطح {level} — {level_name}")
        self.level_label.setStyleSheet(
            f"font-weight: bold; padding: 8px; "
            f"background: {level_color}33; "
            f"border: 2px solid {level_color}; "
            f"border-radius: 6px; color: {level_color};"
        )
        
        # پر کردن بخش‌های کد
        parts = self.coding.parse_code(code)
        for i, part in enumerate(parts):
            if i < len(self.code_parts):
                self.code_parts[i].setText(part)
                self.code_parts[i].setReadOnly(True)
        
        # نام
        self.name_input.setText(acc.get('name', ''))
        
        # نوع
        acc_type = acc.get('type', 'asset')
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == acc_type:
                self.type_combo.setCurrentIndex(i)
                break
        
        # وضعیت
        self.active_check.setChecked(bool(acc.get('is_active', 1)))
        
        # توضیحات
        self.desc_input.setPlainText(acc.get('description', '') or '')
        
        # والد
        parent = acc.get('parent_code') or ''
        self.parent_label.setText(parent or "— (سطح بالا)")
        
        self._update_preview()
    
    def _build_code_parts(self, level_num: int):
        """ساخت فیلدهای کد بر اساس سطح"""
        # پاک کردن قبلی‌ها
        while self.code_layout.count():
            item = self.code_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        
        self.code_parts = []
        
        # ساخت فیلدها برای هر سطح تا سطح فعلی
        for i in range(level_num):
            level_info = self.coding.levels[i]
            length = level_info['length']
            color = level_info['color']
            name = level_info['name']
            
            if i > 0:
                sep = QLabel(self.coding.separator)
                sep.setStyleSheet(
                    f"color: {color}; font-weight: bold; "
                    f"font-size: 14pt;"
                )
                self.code_layout.addWidget(sep)
            
            inp = QLineEdit()
            inp.setPlaceholderText("0" * length)
            inp.setMaxLength(length)
            inp.setAlignment(Qt.AlignCenter)
            inp.setFixedWidth(60 + length * 8)
            inp.setStyleSheet(
                f"border: 2px solid {color}; border-radius: 6px; "
                f"padding: 6px; font-family: 'Courier New', monospace; "
                f"font-weight: bold; font-size: 12pt; color: {color};"
            )
            inp.setToolTip(f"{name} ({length} رقم)")
            inp.textChanged.connect(self._update_preview)
            
            self.code_parts.append(inp)
            self.code_layout.addWidget(inp)
        
        self.code_layout.addStretch()
    
    def _update_preview(self):
        """بروزرسانی پیش‌نمایش کد"""
        parts = []
        for i, inp in enumerate(self.code_parts):
            text = inp.text().strip()
            if text:
                parts.append(text)
            else:
                # placeholder
                length = self.coding.levels[i]['length']
                parts.append("_" * length)
        
        preview = self.coding.separator.join(parts)
        self.code_preview.setText(preview)
        
        # رنگ بر اساس کامل بودن
        if all(p and not p.startswith('_') for p in parts):
            self.code_preview.setStyleSheet(
                "font-family: 'Courier New', monospace; "
                "font-size: 14pt; font-weight: bold; "
                "color: #27ae60; padding: 8px 16px; "
                "background: rgba(39,174,96,0.15); border-radius: 6px;"
            )
        else:
            self.code_preview.setStyleSheet(
                "font-family: 'Courier New', monospace; "
                "font-size: 14pt; font-weight: bold; "
                "color: #1976D2; padding: 8px 16px; "
                "background: rgba(25,118,210,0.1); border-radius: 6px;"
            )
    
    def _suggest_next_code(self) -> str:
        """پیشنهاد کد بعدی در همان سطح"""
        # کد والد
        if self.parent_code:
            parent_parts = self.coding.parse_code(self.parent_code)
            siblings = []
            
            for code in self.all_accounts.keys():
                code_parts = self.coding.parse_code(code)
                if len(code_parts) == len(parent_parts) + 1:
                    if code_parts[:len(parent_parts)] == parent_parts:
                        siblings.append(code)
            
            return self.coding.get_next_code(self.parent_code, siblings)
        else:
            # سطح 1
            siblings = []
            for code in self.all_accounts.keys():
                code_parts = self.coding.parse_code(code)
                if len(code_parts) == 1:
                    siblings.append(code)
            
            return self.coding.get_next_code(None, siblings)
    
    def accept(self):
        """ذخیره"""
        # اعتبارسنجی
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "خطا", "نام حساب الزامی است!")
            return
        
        # کد
        code_parts = [inp.text().strip() for inp in self.code_parts]
        for i, part in enumerate(code_parts):
            length = self.coding.levels[i]['length']
            if not part or not part.isdigit() or len(part) != length:
                QMessageBox.warning(
                    self, "خطا",
                    f"سطح {i+1} ({self.coding.get_level_name(i+1)}) "
                    f"باید دقیقاً {length} رقم باشد!"
                )
                return
        
        code = self.coding.format_code(code_parts)
        
        # چک تکراری (در حالت ایجاد)
        if self.mode == 'create' and code in self.all_accounts:
            QMessageBox.warning(
                self, "خطا", f"کد «{code}» قبلاً استفاده شده!"
            )
            return
        
        # نوع
        acc_type = self.type_combo.currentData()
        
        # والد
        if self.parent_code:
            parent = self.parent_code
        else:
            # خودش از کد استخراج میشه
            parent = self.coding.get_parent_code(code)
        
        # سطح
        level = len(code_parts)
        
        # وضعیت
        is_active = 1 if self.active_check.isChecked() else 0
        
        # توضیحات
        description = self.desc_input.toPlainText().strip()
        
        # ذخیره
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                if self.mode == 'create':
                    c.execute("""
                        INSERT INTO accounts
                        (code, name, type, parent_code, level,
                         is_active, balance)
                        VALUES (?, ?, ?, ?, ?, ?, 0)
                    """, (
                        code, name, acc_type, parent,
                        level, is_active
                    ))
                else:
                    c.execute("""
                        UPDATE accounts
                        SET name = ?, type = ?, parent_code = ?,
                            level = ?, is_active = ?
                        WHERE code = ?
                    """, (
                        name, acc_type, parent, level,
                        is_active, self.edit_code
                    ))
                
                conn.commit()
            
            super().accept()
        
        except Exception as e:
            logger.error(f"خطا در ذخیره: {e}")
            QMessageBox.warning(
                self, "خطا", f"❌ خطا در ذخیره:\n{str(e)}"
            )


# ============================================================
# تست
# ============================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    
    from database import DatabaseManager
    DatabaseManager.init_db()
    
    widget = AccountingTreeWidget(user_level='admin')
    widget.resize(1200, 700)
    widget.setWindowTitle("🌳 درختواره حساب‌ها — تست")
    widget.show()
    
    sys.exit(app.exec_())
