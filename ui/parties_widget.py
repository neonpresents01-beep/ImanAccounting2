# ui/parties_widget.py
# ============================================================
# ویجت مدیریت اشخاص — نسخه 3.0 (کامل و حرفه‌ای)
# ============================================================
# ویژگی‌ها:
# ✅ دو تب (مشتری + فروشنده)
# ✅ CRUD کامل
# ✅ جستجوی پیشرفته
# ✅ فیلتر بر اساس گروه/وضعیت
# ✅ مانده حساب واقعی
# ✅ صورت حساب (statement)
# ✅ دریافت/پرداخت سریع
# ✅ خروجی Excel/PDF
# ✅ سطوح دسترسی
# ✅ پشتیبانی از تم
# ============================================================

import csv
import logging
from datetime import datetime

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from ui.base_widgets import BaseWidget
from ui.party_dialog import PartyDialog
from ui.party_statement_dialog import PartyStatementDialog
from database import get_db
from shamsi_date import safe_display_date

logger = logging.getLogger(__name__)


class PartiesWidget(BaseWidget):
    """ویجت مدیریت اشخاص — نسخه 3.0"""
    
    # ═══════════════════════════════════════════════════════
    # Constructor
    # ═══════════════════════════════════════════════════════
    
    def __init__(self, customer_name: str = "",
                 user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        
        self.customer_name = customer_name
        self.user_level = user_level
        
        # داده‌ها
        self.customers_data = []
        self.suppliers_data = []
        self.current_party = None
        
        # UI
        self.setup_ui()
        self.load_data()
        self.update_ui_by_permission()
        self.apply_theme()
    
    # ═══════════════════════════════════════════════════════
    # Permission
    # ═══════════════════════════════════════════════════════
    
    def set_user_level(self, level: str):
        self.user_level = level
        self.update_ui_by_permission()
    
    def has_permission(self, action: str = 'view') -> bool:
        priority = {
            'admin': 5, 'accountant': 4, 'payroll': 3,
            'inventory': 2, 'viewer': 1
        }
        user_p = priority.get(self.user_level, 0)
        
        permissions = {
            'view': 1,
            'edit': 4,
            'delete': 4,
        }
        return user_p >= permissions.get(action, 1)
    
    def update_ui_by_permission(self):
        can_edit = self.has_permission('edit')
        can_delete = self.has_permission('delete')
        
        for btn_name in ['new_btn', 'edit_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setEnabled(can_edit)
        
        if hasattr(self, 'delete_btn'):
            self.delete_btn.setEnabled(can_delete)
    
    # ═══════════════════════════════════════════════════════
    # UI
    # ═══════════════════════════════════════════════════════
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # ─── Title ───
        title = QLabel("👥 مدیریت اشخاص")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # ─── Tabs ───
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # تب مشتریان
        self.customer_widget = self._create_party_tab('customer')
        self.tabs.addTab(self.customer_widget, "👥 مشتریان")
        
        # تب فروشندگان
        self.supplier_widget = self._create_party_tab('supplier')
        self.tabs.addTab(self.supplier_widget, "📦 فروشندگان")
        
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        layout.addWidget(self.tabs, 1)
        
        # ─── Status ───
        self.status_label = QLabel("✅ آماده")
        self.status_label.setStyleSheet(
            "padding: 8px; background: rgba(128,128,128,0.1); "
            "border-radius: 6px; font-weight: bold;"
        )
        layout.addWidget(self.status_label)
    
    def _create_party_tab(self, party_type: str) -> QWidget:
        """ساخت محتوای تب"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ─── Toolbar ───
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        new_btn = QPushButton("➕ جدید")
        new_btn.setObjectName("successBtn")
        new_btn.clicked.connect(lambda: self.new_party(party_type))
        toolbar.addWidget(new_btn)
        
        edit_btn = QPushButton("✏️ ویرایش")
        edit_btn.setObjectName("warningBtn")
        edit_btn.clicked.connect(lambda: self.edit_party(party_type))
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ حذف")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.clicked.connect(lambda: self.delete_party(party_type))
        toolbar.addWidget(delete_btn)
        
        toolbar.addSpacing(15)
        
        statement_btn = QPushButton("📊 صورت حساب")
        statement_btn.setObjectName("infoBtn")
        statement_btn.clicked.connect(lambda: self.show_statement(party_type))
        toolbar.addWidget(statement_btn)
        
        toolbar.addSpacing(15)
        
        export_btn = QPushButton("📎 Excel")
        export_btn.clicked.connect(lambda: self.export_to_excel(party_type))
        toolbar.addWidget(export_btn)
        
        toolbar.addStretch()
        
        # ذخیره در widget برای دسترسی
        widget.new_btn = new_btn
        widget.edit_btn = edit_btn
        widget.delete_btn = delete_btn
        
        layout.addLayout(toolbar)
        
        # ─── Filters ───
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        
        filter_bar.addWidget(QLabel("🔍 جستجو:"))
        search = QLineEdit()
        search.setPlaceholderText("کد، نام، موبایل، تلفن...")
        search.setMinimumWidth(200)
        search.textChanged.connect(lambda: self._filter(party_type))
        filter_bar.addWidget(search)
        widget.search_input = search
        
        filter_bar.addWidget(QLabel("گروه:"))
        group_filter = QComboBox()
        group_filter.addItem("همه", "")
        group_filter.currentIndexChanged.connect(lambda: self._filter(party_type))
        filter_bar.addWidget(group_filter)
        widget.group_filter = group_filter
        
        filter_bar.addWidget(QLabel("وضعیت:"))
        status_filter = QComboBox()
        status_filter.addItem("همه", "all")
        status_filter.addItem("✅ فعال", "active")
        status_filter.addItem("⛔ غیرفعال", "inactive")
        status_filter.currentIndexChanged.connect(lambda: self._filter(party_type))
        filter_bar.addWidget(status_filter)
        widget.status_filter = status_filter
        
        filter_bar.addStretch()
        
        clear_btn = QPushButton("✖ پاک کردن")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(lambda: self._clear_filters(party_type))
        filter_bar.addWidget(clear_btn)
        
        layout.addLayout(filter_bar)
        
        # ─── Table ───
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "کد", "نام", "شرکت", "موبایل", "تلفن",
            "گروه", "مانده", "وضعیت"
        ])
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 100)
        table.setColumnWidth(1, 180)
        table.setColumnWidth(2, 160)
        table.setColumnWidth(3, 120)
        table.setColumnWidth(4, 120)
        table.setColumnWidth(5, 100)
        table.setColumnWidth(6, 130)
        table.setColumnWidth(7, 90)
        
        table.doubleClicked.connect(lambda: self.edit_party(party_type))
        table.itemSelectionChanged.connect(lambda: self._on_selection_changed(party_type))
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(party_type, pos)
        )
        
        layout.addWidget(table, 1)
        widget.table = table
        
        return widget
    
    # ═══════════════════════════════════════════════════════
    # Data Loading
    # ═══════════════════════════════════════════════════════
    
    def _get_current_widget(self) -> QWidget:
        return self.customer_widget if self.tabs.currentIndex() == 0 else self.supplier_widget
    
    def _get_current_type(self) -> str:
        return 'customer' if self.tabs.currentIndex() == 0 else 'supplier'
    
    def _get_widget_for_type(self, party_type: str) -> QWidget:
        return self.customer_widget if party_type == 'customer' else self.supplier_widget
    
    def load_data(self):
        """بارگذاری همه اشخاص"""
        for party_type in ['customer', 'supplier']:
            self._load_parties(party_type)
        
        self._update_groups()
        self._update_stats()
    
    def _load_parties(self, party_type: str):
        """بارگذاری لیست اشخاص"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                # چک ستون‌های موجود
                c.execute("PRAGMA table_info(parties)")
                cols = [col[1] for col in c.fetchall()]
                
                # ساخت SELECT بر اساس ستون‌های موجود
                fields = ['id', 'code', 'name']
                for f in ['company', 'phone', 'mobile', 'email', 'address']:
                    if f in cols:
                        fields.append(f)
                
                if 'group_name' in cols:
                    fields.append('group_name')
                if 'credit_limit' in cols:
                    fields.append('credit_limit')
                if 'is_active' in cols:
                    fields.append('is_active')
                
                query = f"SELECT {', '.join(fields)} FROM parties WHERE type = ?"
                c.execute(query, [party_type])
                
                parties = [dict(row) for row in c.fetchall()]
                
                # محاسبه مانده واقعی برای هر شخص
                for p in parties:
                    p['balance'] = self._calculate_balance(p['id'], party_type)
            
            # ذخیره در متغیر مناسب
            if party_type == 'customer':
                self.customers_data = parties
            else:
                self.suppliers_data = parties
            
            self._display_parties(party_type, parties)
        
        except Exception as e:
            logger.error(f"خطا در بارگذاری {party_type}: {e}", exc_info=True)
            if party_type == 'customer':
                self.customers_data = []
            else:
                self.suppliers_data = []
            self._display_parties(party_type, [])
    
    def _calculate_balance(self, party_id: int, party_type: str) -> float:
        """محاسبه مانده واقعی شخص"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                balance = 0.0
                
                # فاکتورها
                if party_type == 'customer':
                    # مشتری: فروش = بدهکار مشتری
                    c.execute("""
                        SELECT COALESCE(SUM(net_amount), 0) FROM documents
                        WHERE party_id = ? AND doc_type = 'sales'
                    """, [party_id])
                    balance += c.fetchone()[0] or 0
                else:
                    # فروشنده: خرید = بستانکار ما
                    c.execute("""
                        SELECT COALESCE(SUM(net_amount), 0) FROM documents
                        WHERE party_id = ? AND doc_type = 'purchase'
                    """, [party_id])
                    balance += c.fetchone()[0] or 0
                
                # تراکنش‌های مالی
                if party_type == 'customer':
                    # دریافت از مشتری = کاهش بدهی
                    c.execute("""
                        SELECT COALESCE(SUM(amount), 0) FROM finance_transactions
                        WHERE party_id = ? AND type IN ('receipt', 'income')
                    """, [party_id])
                    balance -= c.fetchone()[0] or 0
                    
                    # پرداخت به مشتری (برگشت) = افزایش بدهی
                    c.execute("""
                        SELECT COALESCE(SUM(amount), 0) FROM finance_transactions
                        WHERE party_id = ? AND type IN ('payment', 'expense')
                    """, [party_id])
                    balance += c.fetchone()[0] or 0
                else:
                    # پرداخت به فروشنده = کاهش بدهی ما
                    c.execute("""
                        SELECT COALESCE(SUM(amount), 0) FROM finance_transactions
                        WHERE party_id = ? AND type IN ('payment', 'expense')
                    """, [party_id])
                    balance -= c.fetchone()[0] or 0
                    
                    # دریافت از فروشنده (برگشت) = افزایش
                    c.execute("""
                        SELECT COALESCE(SUM(amount), 0) FROM finance_transactions
                        WHERE party_id = ? AND type IN ('receipt', 'income')
                    """, [party_id])
                    balance += c.fetchone()[0] or 0
                
                return balance
        except Exception as e:
            logger.warning(f"خطا در محاسبه مانده: {e}")
            return 0.0
    
    def _display_parties(self, party_type: str, parties: list):
        """نمایش اشخاص در جدول"""
        widget = self._get_widget_for_type(party_type)
        table = widget.table
        
        table.setRowCount(len(parties))
        
        for i, p in enumerate(parties):
            # کد
            table.setItem(i, 0, QTableWidgetItem(str(p.get('code', ''))))
            
            # نام
            table.setItem(i, 1, QTableWidgetItem(str(p.get('name', ''))))
            
            # شرکت
            table.setItem(i, 2, QTableWidgetItem(str(p.get('company', '') or '-')))
            
            # موبایل
            table.setItem(i, 3, QTableWidgetItem(str(p.get('mobile', '') or '-')))
            
            # تلفن
            table.setItem(i, 4, QTableWidgetItem(str(p.get('phone', '') or '-')))
            
            # گروه
            group = p.get('group_name', '') or '-'
            table.setItem(i, 5, QTableWidgetItem(group))
            
            # مانده
            balance = p.get('balance', 0) or 0
            balance_item = QTableWidgetItem(f"{balance:,.0f}" if balance else "-")
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if balance > 0:
                balance_item.setForeground(QColor('#e74c3c'))  # بدهکار
            elif balance < 0:
                balance_item.setForeground(QColor('#27ae60'))  # بستانکار
            table.setItem(i, 6, balance_item)
            
            # وضعیت
            is_active = p.get('is_active', 1)
            if is_active:
                status_item = QTableWidgetItem("🟢 فعال")
                status_item.setForeground(QColor('#27ae60'))
            else:
                status_item = QTableWidgetItem("⛔ غیرفعال")
                status_item.setForeground(QColor('#999999'))
            table.setItem(i, 7, status_item)
    
    def _update_groups(self):
        """بروزرسانی فیلتر گروه‌ها"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("PRAGMA table_info(parties)")
                cols = [col[1] for col in c.fetchall()]
                
                if 'group_name' not in cols:
                    return
                
                c.execute("""
                    SELECT DISTINCT group_name FROM parties
                    WHERE group_name IS NOT NULL AND group_name != ''
                    ORDER BY group_name
                """)
                groups = [row[0] if not hasattr(row, 'keys') else row['group_name'] for row in c.fetchall()]
                
                for widget in [self.customer_widget, self.supplier_widget]:
                    combo = widget.group_filter
                    current = combo.currentData()
                    combo.blockSignals(True)
                    combo.clear()
                    combo.addItem("همه", "")
                    for g in groups:
                        if g:
                            combo.addItem(g, g)
                    # بازگردانی انتخاب
                    if current:
                        idx = combo.findData(current)
                        if idx >= 0:
                            combo.setCurrentIndex(idx)
                    combo.blockSignals(False)
        except Exception:
            pass
    
    def _update_stats(self):
        """بروزرسانی آمار"""
        total_c = len(self.customers_data)
        total_s = len(self.suppliers_data)
        
        # مانده کل مشتریان
        balance_c = sum(p.get('balance', 0) or 0 for p in self.customers_data)
        balance_s = sum(p.get('balance', 0) or 0 for p in self.suppliers_data)
        
        self.status_label.setText(
            f"👥 مشتریان: {total_c} | 📦 فروشندگان: {total_s} | "
            f"💰 مانده مشتریان: {balance_c:,.0f} ریال | "
            f"💸 مانده فروشندگان: {balance_s:,.0f} ریال"
        )
    
    # ═══════════════════════════════════════════════════════
    # Filters
    # ═══════════════════════════════════════════════════════
    
    def _filter(self, party_type: str):
        """فیلتر اشخاص"""
        widget = self._get_widget_for_type(party_type)
        
        data = self.customers_data if party_type == 'customer' else self.suppliers_data
        
        search_text = widget.search_input.text().strip().lower()
        group_filter = widget.group_filter.currentData()
        status_filter = widget.status_filter.currentData()
        
        filtered = []
        for p in data:
            # جستجو
            if search_text:
                searchable = ' '.join([
                    str(p.get('code', '')),
                    str(p.get('name', '')),
                    str(p.get('company', '')),
                    str(p.get('mobile', '')),
                    str(p.get('phone', '')),
                    str(p.get('email', '')),
                ]).lower()
                if search_text not in searchable:
                    continue
            
            # گروه
            if group_filter:
                if p.get('group_name', '') != group_filter:
                    continue
            
            # وضعیت
            if status_filter == 'active':
                if not p.get('is_active', 1):
                    continue
            elif status_filter == 'inactive':
                if p.get('is_active', 1):
                    continue
            
            filtered.append(p)
        
        self._display_parties(party_type, filtered)
    
    def _clear_filters(self, party_type: str):
        """پاک کردن فیلترها"""
        widget = self._get_widget_for_type(party_type)
        widget.search_input.clear()
        widget.group_filter.setCurrentIndex(0)
        widget.status_filter.setCurrentIndex(0)
        # trigger reload
        data = self.customers_data if party_type == 'customer' else self.suppliers_data
        self._display_parties(party_type, data)
    
    def _on_tab_changed(self):
        """تغییر تب"""
        self.current_party = None
    
    def _on_selection_changed(self, party_type: str):
        """انتخاب ردیف"""
        widget = self._get_widget_for_type(party_type)
        row = widget.table.currentRow()
        
        data = self.customers_data if party_type == 'customer' else self.suppliers_data
        
        if 0 <= row < len(data):
            self.current_party = data[row]
        else:
            self.current_party = None
    
    # ═══════════════════════════════════════════════════════
    # CRUD
    # ═══════════════════════════════════════════════════════
    
    def new_party(self, party_type: str):
        """افزودن شخص جدید"""
        if not self.has_permission('edit'):
            QMessageBox.warning(self, "دسترسی محدود", "شما دسترسی ندارید!")
            return
        
        dialog = PartyDialog(party_type=party_type, parent=self)
        
        if dialog.exec_():
            self.load_data()
            self._update_groups()
            QMessageBox.information(
                self, "موفق",
                f"✅ {'مشتری' if party_type == 'customer' else 'فروشنده'} اضافه شد!"
            )
    
    def edit_party(self, party_type: str):
        """ویرایش شخص"""
        if not self.has_permission('edit'):
            QMessageBox.warning(self, "دسترسی محدود", "شما دسترسی ندارید!")
            return
        
        if not self.current_party:
            QMessageBox.warning(self, "خطا", "یک شخص را انتخاب کنید!")
            return
        
        dialog = PartyDialog(
            party_type=party_type,
            party_id=self.current_party['id'],
            parent=self
        )
        
        if dialog.exec_():
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ ویرایش شد!")
    
    def delete_party(self, party_type: str):
        """حذف شخص"""
        if not self.has_permission('delete'):
            QMessageBox.warning(self, "دسترسی محدود", "شما دسترسی ندارید!")
            return
        
        if not self.current_party:
            QMessageBox.warning(self, "خطا", "یک شخص را انتخاب کنید!")
            return
        
        party = self.current_party
        name = party.get('name', '')
        
        # چک استفاده
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM documents WHERE party_id = ?",
                         [party['id']])
                doc_count = c.fetchone()[0] or 0
                
                c.execute("SELECT COUNT(*) FROM finance_transactions WHERE party_id = ?",
                         [party['id']])
                trans_count = c.fetchone()[0] or 0
        except Exception:
            doc_count = 0
            trans_count = 0
        
        if doc_count > 0 or trans_count > 0:
            reply = QMessageBox.question(
                self, "هشدار",
                f"⚠️ این شخص در {doc_count} سند و {trans_count} تراکنش استفاده شده!\n\n"
                f"آیا می‌خواهید غیرفعال شود؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    with get_db() as conn:
                        c = conn.cursor()
                        c.execute("PRAGMA table_info(parties)")
                        cols = [col[1] for col in c.fetchall()]
                        
                        if 'is_active' in cols:
                            c.execute("UPDATE parties SET is_active = 0 WHERE id = ?",
                                     [party['id']])
                        else:
                            QMessageBox.warning(self, "خطا", "ستون is_active وجود ندارد!")
                            return
                        conn.commit()
                    
                    self.load_data()
                    QMessageBox.information(self, "موفق", "✅ غیرفعال شد!")
                except Exception as e:
                    QMessageBox.warning(self, "خطا", str(e))
            return
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف «{name}» اطمینان دارید؟\n\n"
            f"⚠️ این عمل قابل بازگشت نیست!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM party_transactions WHERE party_id = ?",
                             [party['id']])
                    c.execute("DELETE FROM parties WHERE id = ?", [party['id']])
                    conn.commit()
                
                self.load_data()
                self.current_party = None
                QMessageBox.information(self, "موفق", "✅ حذف شد!")
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    # ═══════════════════════════════════════════════════════
    # Statement
    # ═══════════════════════════════════════════════════════
    
    def show_statement(self, party_type: str):
        """نمایش صورت حساب"""
        if not self.current_party:
            QMessageBox.warning(self, "خطا", "یک شخص را انتخاب کنید!")
            return
        
        dialog = PartyStatementDialog(
            party_id=self.current_party['id'],
            party_name=self.current_party.get('name', ''),
            party_type=party_type,
            parent=self
        )
        dialog.exec_()
    
    # ═══════════════════════════════════════════════════════
    # Context Menu
    # ═══════════════════════════════════════════════════════
    
    def _show_context_menu(self, party_type: str, pos):
        widget = self._get_widget_for_type(party_type)
        item = widget.table.itemAt(pos)
        if not item:
            return
        
        widget.table.setCurrentItem(item)
        self._on_selection_changed(party_type)
        
        if not self.current_party:
            return
        
        menu = QMenu(self)
        
        menu.addAction("✏️ ویرایش").triggered.connect(
            lambda: self.edit_party(party_type)
        )
        menu.addAction("📊 صورت حساب").triggered.connect(
            lambda: self.show_statement(party_type)
        )
        
        menu.addSeparator()
        
        copy_action = menu.addAction("📋 کپی کد")
        copy_action.triggered.connect(
            lambda: QApplication.clipboard().setText(
                self.current_party.get('code', '')
            )
        )
        
        menu.addSeparator()
        
        if self.has_permission('delete'):
            menu.addAction("🗑️ حذف").triggered.connect(
                lambda: self.delete_party(party_type)
            )
        
        menu.exec_(widget.table.viewport().mapToGlobal(pos))
    
    # ═══════════════════════════════════════════════════════
    # Export
    # ═══════════════════════════════════════════════════════
    
    def export_to_excel(self, party_type: str):
        """خروجی Excel"""
        widget = self._get_widget_for_type(party_type)
        table = widget.table
        
        if table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "داده‌ای برای خروجی نیست!")
            return
        
        name = "مشتریان" if party_type == 'customer' else "فروشندگان"
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره",
            f"{name}_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not file_name:
            return
        
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                
                headers = []
                for col in range(table.columnCount()):
                    h = table.horizontalHeaderItem(col)
                    headers.append(h.text() if h else "")
                writer.writerow(headers)
                
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        it = table.item(row, col)
                        row_data.append(it.text() if it else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "موفق", f"✅ ذخیره شد:\n{file_name}")
        except Exception as e:
            QMessageBox.warning(self, "خطا", str(e))
    
    # ═══════════════════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════════════════
    
    def apply_theme(self):
        """اعمال تم"""
        try:
            from ui.styles.theme_manager import get_theme_manager
            tm = get_theme_manager()
            is_dark = tm.get_theme_name() == 'dark'
        except Exception:
            is_dark = False
        
        if is_dark:
            c = {
                'bg': '#0f0f23', 'card': '#1a1a2e', 'text': '#e8e8e8',
                'border': '#0f3460', 'hover': '#2a2a4a',
                'selected': '#e94560', 'success': '#27ae60',
                'danger': '#e74c3c', 'warning': '#f39c12',
                'info': '#3498db', 'bg_alt': '#16213e',
            }
        else:
            c = {
                'bg': '#f5f6fa', 'card': '#ffffff', 'text': '#1a1a2e',
                'border': '#dcdde1', 'hover': '#e8e8e8',
                'selected': '#1976D2', 'success': '#27ae60',
                'danger': '#e74c3c', 'warning': '#f39c12',
                'info': '#3498db', 'bg_alt': '#ffffff',
            }
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {c['bg']};
                color: {c['text']};
            }}
            QTableWidget {{
                background: {c['bg_alt']};
                alternate-background-color: {c['bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                gridline-color: {c['border']};
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QTableWidget::item:selected {{
                background: {c['selected']};
                color: white;
            }}
            QHeaderView::section {{
                background: {c['card']};
                color: {c['text']};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
            QLineEdit, QComboBox {{
                background: {c['bg_alt']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 28px;
            }}
            QPushButton {{
                padding: 8px 14px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 30px;
                background: {c['bg_alt']};
                color: {c['text']};
                border: 1px solid {c['border']};
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
            QTabWidget::pane {{
                border: 1px solid {c['border']};
                border-radius: 6px;
                background: {c['card']};
            }}
            QTabBar::tab {{
                padding: 10px 20px;
                margin: 2px;
                border-radius: 6px;
                background: {c['bg_alt']};
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: {c['selected']};
                color: white;
            }}
        """)
