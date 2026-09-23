# utils/dialog_utils.py
# -*- coding: utf-8 -*-

"""
توابع کمکی برای دیالوگ‌های پرکاربرد در سراسر برنامه
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from database import get_db
from date_utils import JalaliDateEdit, safe_display_date


# ============================================================
# دیالوگ انتخاب تاریخ (تک تاریخ)
# ============================================================
class DatePickerDialog(QDialog):
    """دیالوگ انتخاب تاریخ با تقویم شمسی"""
    
    def __init__(self, title="انتخاب تاریخ", parent=None, default_date=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setGeometry(400, 300, 350, 200)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"📅 {title}:"))
        
        self.date_edit = JalaliDateEdit()
        if default_date:
            self.date_edit.set_from_gregorian(default_date)
        layout.addWidget(self.date_edit)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("✅ تأیید")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def get_gregorian_date(self):
        return self.date_edit.get_gregorian()
    
    def get_display_date(self):
        return self.date_edit.get_display()


# ============================================================
# دیالوگ انتخاب بازه زمانی
# ============================================================
class DateRangeDialog(QDialog):
    """دیالوگ انتخاب بازه زمانی (از تاریخ - تا تاریخ)"""
    
    def __init__(self, title="انتخاب بازه زمانی", parent=None, 
                 from_date=None, to_date=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setGeometry(400, 300, 400, 250)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"📅 {title}:"))
        
        form_layout = QFormLayout()
        
        self.from_date = JalaliDateEdit()
        if from_date:
            self.from_date.set_from_gregorian(from_date)
        form_layout.addRow("از تاریخ:", self.from_date)
        
        self.to_date = JalaliDateEdit()
        if to_date:
            self.to_date.set_from_gregorian(to_date)
        form_layout.addRow("تا تاریخ:", self.to_date)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("✅ تأیید")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def get_gregorian_from(self):
        return self.from_date.get_gregorian()
    
    def get_gregorian_to(self):
        return self.to_date.get_gregorian()
    
    def get_display_from(self):
        return self.from_date.get_display()
    
    def get_display_to(self):
        return self.to_date.get_display()


# ============================================================
# دیالوگ ساده برای نمایش پیام با تأیید
# ============================================================
def show_info_dialog(parent, title, message, icon_type="info"):
    """نمایش دیالوگ اطلاعات ساده"""
    if icon_type == "info":
        QMessageBox.information(parent, title, message)
    elif icon_type == "warning":
        QMessageBox.warning(parent, title, message)
    elif icon_type == "error":
        QMessageBox.critical(parent, title, message)


def show_confirm_dialog(parent, title, message):
    """نمایش دیالوگ تأیید - بازگشت True/False"""
    reply = QMessageBox.question(parent, title, message,
                                 QMessageBox.Yes | QMessageBox.No,
                                 QMessageBox.No)
    return reply == QMessageBox.Yes


# ============================================================
# دیالوگ ورودی ساده
# ============================================================
class InputDialog(QDialog):
    """دیالوگ ورودی ساده با یک فیلد"""
    
    def __init__(self, title, label, parent=None, default_value=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setGeometry(400, 300, 400, 150)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(label))
        
        self.input_field = QLineEdit()
        self.input_field.setText(default_value)
        layout.addWidget(self.input_field)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("✅ تأیید")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def get_value(self):
        return self.input_field.text().strip()


# ============================================================
# دیالوگ انتخاب از لیست
# ============================================================
class SelectFromListDialog(QDialog):
    """دیالوگ انتخاب یک آیتم از لیست"""
    
    def __init__(self, title, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setGeometry(400, 300, 500, 400)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"📋 {title}:"))
        
        self.list_widget = QListWidget()
        for item in items:
            if isinstance(item, dict):
                display = f"{item.get('code', '')} - {item.get('name', '')}"
                self.list_widget.addItem(display)
                self.list_widget.item(len(self.list_widget)-1).setData(Qt.UserRole, item)
            else:
                self.list_widget.addItem(str(item))
                self.list_widget.item(len(self.list_widget)-1).setData(Qt.UserRole, item)
        
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("✅ انتخاب")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def get_selected(self):
        current = self.list_widget.currentItem()
        if current:
            return current.data(Qt.UserRole)
        return None
    
    def get_selected_index(self):
        return self.list_widget.currentRow()


# ============================================================
# دیالوگ جستجو و انتخاب حساب
# ============================================================
class AccountSearchDialog(QDialog):
    """دیالوگ جستجو و انتخاب حساب از لیست"""
    
    def __init__(self, parent=None, selected_code=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 جستجوی حساب")
        self.setModal(True)
        self.setGeometry(400, 300, 600, 500)
        
        self.selected_account = None
        
        layout = QVBoxLayout(self)
        
        # جستجو
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("جستجو:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("کد یا نام حساب...")
        self.search_input.textChanged.connect(self.filter_accounts)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # جدول
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["کد", "نام", "نوع"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.select_and_close)
        layout.addWidget(self.table)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        select_btn = QPushButton("✅ انتخاب")
        select_btn.clicked.connect(self.select_and_close)
        btn_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.load_accounts()
    
    def load_accounts(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code, name, type FROM accounts WHERE is_active = 1 ORDER BY code")
            self.accounts = c.fetchall()
            self.display_accounts(self.accounts)
    
    def display_accounts(self, accounts):
        self.table.setRowCount(len(accounts))
        
        type_names = {'asset': 'دارایی', 'liability': 'بدهی', 'equity': 'سرمایه', 
                      'income': 'درآمد', 'expense': 'هزینه'}
        
        for i, acc in enumerate(accounts):
            self.table.setItem(i, 0, QTableWidgetItem(acc['code']))
            self.table.setItem(i, 1, QTableWidgetItem(acc['name']))
            self.table.setItem(i, 2, QTableWidgetItem(type_names.get(acc['type'], acc['type'])))
    
    def filter_accounts(self):
        text = self.search_input.text().lower()
        if not text:
            self.display_accounts(self.accounts)
            return
        
        filtered = []
        for acc in self.accounts:
            if text in acc['code'].lower() or text in acc['name'].lower():
                filtered.append(acc)
        self.display_accounts(filtered)
    
    def select_and_close(self):
        row = self.table.currentRow()
        if row >= 0:
            self.selected_account = self.accounts[row] if hasattr(self, 'accounts') else None
            self.accept()
        else:
            QMessageBox.warning(self, "خطا", "لطفاً یک حساب را انتخاب کنید!")
    
    def get_selected_account(self):
        return self.selected_account


# ============================================================
# دیالوگ جستجو و انتخاب کالا
# ============================================================
class ProductSearchDialog(QDialog):
    """دیالوگ جستجو و انتخاب کالا از لیست"""
    
    def __init__(self, parent=None, selected_id=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 جستجوی کالا")
        self.setModal(True)
        self.setGeometry(400, 300, 600, 500)
        
        self.selected_product = None
        
        layout = QVBoxLayout(self)
        
        # جستجو
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("جستجو:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("کد یا نام کالا...")
        self.search_input.textChanged.connect(self.filter_products)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # جدول
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["کد", "نام", "واحد", "موجودی", "قیمت فروش"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.select_and_close)
        layout.addWidget(self.table)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        select_btn = QPushButton("✅ انتخاب")
        select_btn.clicked.connect(self.select_and_close)
        btn_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.load_products()
    
    def load_products(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, code, name, unit, stock, sale_price FROM products ORDER BY code")
            self.products = c.fetchall()
            self.display_products(self.products)
    
    def display_products(self, products):
        self.table.setRowCount(len(products))
        
        for i, p in enumerate(products):
            self.table.setItem(i, 0, QTableWidgetItem(p['code']))
            self.table.setItem(i, 1, QTableWidgetItem(p['name']))
            self.table.setItem(i, 2, QTableWidgetItem(p['unit'] or 'عدد'))
            
            stock_item = QTableWidgetItem(f"{p['stock']:,.2f}")
            stock_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 3, stock_item)
            
            price_item = QTableWidgetItem(f"{p['sale_price']:,.0f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 4, price_item)
    
    def filter_products(self):
        text = self.search_input.text().lower()
        if not text:
            self.display_products(self.products)
            return
        
        filtered = []
        for p in self.products:
            if text in p['code'].lower() or text in p['name'].lower():
                filtered.append(p)
        self.display_products(filtered)
    
    def select_and_close(self):
        row = self.table.currentRow()
        if row >= 0:
            self.selected_product = self.products[row] if hasattr(self, 'products') else None
            self.accept()
        else:
            QMessageBox.warning(self, "خطا", "لطفاً یک کالا را انتخاب کنید!")
    
    def get_selected_product(self):
        return self.selected_product


# ============================================================
# دیالوگ جستجو و انتخاب شخص (مشتری/فروشنده)
# ============================================================
class PartySearchDialog(QDialog):
    """دیالوگ جستجو و انتخاب شخص (مشتری یا فروشنده)"""
    
    def __init__(self, party_type="customer", parent=None, selected_id=None):
        super().__init__(parent)
        self.party_type = party_type
        self.setWindowTitle(f"🔍 جستجوی {'مشتری' if party_type == 'customer' else 'تأمین‌کننده'}")
        self.setModal(True)
        self.setGeometry(400, 300, 600, 500)
        
        self.selected_party = None
        
        layout = QVBoxLayout(self)
        
        # جستجو
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("جستجو:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("کد، نام یا تلفن...")
        self.search_input.textChanged.connect(self.filter_parties)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # جدول
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["کد", "نام", "شرکت", "تلفن", "موبایل"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.select_and_close)
        layout.addWidget(self.table)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        select_btn = QPushButton("✅ انتخاب")
        select_btn.clicked.connect(self.select_and_close)
        btn_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.load_parties()
    
    def load_parties(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, code, name, company, phone, mobile
                FROM parties 
                WHERE type = ?
                ORDER BY code
            ''', [self.party_type])
            self.parties = c.fetchall()
            self.display_parties(self.parties)
    
    def display_parties(self, parties):
        self.table.setRowCount(len(parties))
        
        for i, p in enumerate(parties):
            self.table.setItem(i, 0, QTableWidgetItem(p['code'] or '-'))
            self.table.setItem(i, 1, QTableWidgetItem(p['name'] or '-'))
            self.table.setItem(i, 2, QTableWidgetItem(p['company'] or '-'))
            self.table.setItem(i, 3, QTableWidgetItem(p['phone'] or '-'))
            self.table.setItem(i, 4, QTableWidgetItem(p['mobile'] or '-'))
    
    def filter_parties(self):
        text = self.search_input.text().lower()
        if not text:
            self.display_parties(self.parties)
            return
        
        filtered = []
        for p in self.parties:
            if (text in (p['code'] or '').lower() or 
                text in (p['name'] or '').lower() or
                text in (p['phone'] or '').lower() or
                text in (p['mobile'] or '').lower()):
                filtered.append(p)
        self.display_parties(filtered)
    
    def select_and_close(self):
        row = self.table.currentRow()
        if row >= 0:
            self.selected_party = self.parties[row] if hasattr(self, 'parties') else None
            self.accept()
        else:
            QMessageBox.warning(self, "خطا", "لطفاً یک شخص را انتخاب کنید!")
    
    def get_selected_party(self):
        return self.selected_party


# ============================================================
# دیالوگ نمایش پیشرفت
# ============================================================
class ProgressDialog(QDialog):
    """دیالوگ نمایش پیشرفت عملیات طولانی"""
    
    def __init__(self, title="در حال اجرا...", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setGeometry(400, 300, 450, 120)
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel("لطفاً صبر کنید...")
        layout.addWidget(self.label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.cancel_btn = QPushButton("❌ لغو")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)
    
    def set_text(self, text):
        self.label.setText(text)
    
    def set_progress(self, value):
        self.progress_bar.setValue(value)
    
    def set_range(self, minimum, maximum):
        self.progress_bar.setRange(minimum, maximum)


# ============================================================
# دیالوگ ورودی مبلغ
# ============================================================
class MoneyInputDialog(QDialog):
    """دیالوگ ورودی مبلغ ریالی با فرمت خودکار"""
    
    def __init__(self, title, label, parent=None, default_value=0):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setGeometry(400, 300, 400, 150)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(label))
        
        from ui.inventory_widget import MoneyLineEdit
        self.money_input = MoneyLineEdit()
        self.money_input.setValue(default_value)
        layout.addWidget(self.money_input)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        ok_btn = QPushButton("✅ تأیید")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def get_value(self):
        return self.money_input.value()