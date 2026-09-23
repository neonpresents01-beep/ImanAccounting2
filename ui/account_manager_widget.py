# ui/account_manager_widget.py
# ============================================================
# ویجت مدیریت حساب‌ها با پشتیبانی از تم
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from ui.base_widgets import BaseWidget, BaseDialog
from database import get_db
import json
import os
import sqlite3


class AccountManagerWidget(BaseWidget):
    """ویجت مدیریت حساب‌های حسابداری با پشتیبانی از تم"""
    
    def __init__(self):
        super().__init__()
        self.accounts_data = []
        self.setup_ui()
        self.load_accounts()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(self.margin(15), self.margin(15), 
                                  self.margin(15), self.margin(15))
        
        title = QLabel("📊 مدیریت حساب‌ها")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # نوار ابزار
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
        
        toolbar.addStretch()
        
        search_label = QLabel("🔍 جستجو:")
        toolbar.addWidget(search_label)
        
        self.search_input = self.create_input("کد یا نام حساب...")
        self.search_input.setMaximumWidth(self.scaled(200))
        self.search_input.textChanged.connect(self.filter_accounts)
        toolbar.addWidget(self.search_input)
        
        layout.addLayout(toolbar)
        
        # جدول
        self.table = self.create_table(
            ["کد حساب", "نام حساب", "نوع", "حساب والد", "وضعیت"],
            stretch_last=True
        )
        layout.addWidget(self.table)
    
    def load_accounts(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('SELECT code, name, type, parent_code, is_active FROM accounts ORDER BY code')
                self.accounts_data = c.fetchall()
                self.display_accounts(self.accounts_data)
        except Exception as e:
            print(f"❌ خطا در بارگذاری حساب‌ها: {e}")
            self.accounts_data = []
            self.display_accounts([])
    
    def display_accounts(self, accounts):
        self.table.setRowCount(len(accounts))
        type_names = {'asset': 'دارایی', 'liability': 'بدهی', 'equity': 'سرمایه', 
                      'income': 'درآمد', 'expense': 'هزینه'}
        
        for i, acc in enumerate(accounts):
            self.table.setItem(i, 0, QTableWidgetItem(acc['code']))
            self.table.setItem(i, 1, QTableWidgetItem(acc['name']))
            self.table.setItem(i, 2, QTableWidgetItem(type_names.get(acc['type'], acc['type'])))
            self.table.setItem(i, 3, QTableWidgetItem(acc['parent_code'] or "-"))
            
            status_item = QTableWidgetItem("فعال" if acc['is_active'] else "غیرفعال")
            status_item.setForeground(QColor('#4CAF50') if acc['is_active'] else QColor('#f44336'))
            self.table.setItem(i, 4, status_item)
    
    def filter_accounts(self):
        text = self.search_input.text().lower()
        if not text:
            self.display_accounts(self.accounts_data)
            return
        filtered = [acc for acc in self.accounts_data 
                   if text in acc['code'].lower() or text in acc['name'].lower()]
        self.display_accounts(filtered)
    
    def new_account(self):
        dialog = AccountDialog(parent=self)
        if dialog.exec_():
            self.load_accounts()
            QMessageBox.information(self, "موفق", "✅ حساب جدید ایجاد شد!")
    
    def edit_account(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک حساب را انتخاب کنید!")
            return
        code = self.table.item(row, 0).text()
        dialog = AccountDialog(code, parent=self)
        if dialog.exec_():
            self.load_accounts()
            QMessageBox.information(self, "موفق", "✅ حساب ویرایش شد!")
    
    def delete_account(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک حساب را انتخاب کنید!")
            return
        
        code = self.table.item(row, 0).text()
        name = self.table.item(row, 1).text()
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM accounts WHERE parent_code = ?", [code])
            child_count = c.fetchone()[0]
            if child_count > 0:
                QMessageBox.warning(self, "خطا", f"این حساب دارای {child_count} زیرمجموعه است!")
                return
        
        reply = QMessageBox.question(self, "تأیید حذف", f"آیا از حذف '{code} - {name}' اطمینان دارید؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM accounts WHERE code = ?", [code])
            self.load_accounts()
            QMessageBox.information(self, "موفق", "✅ حساب حذف شد!")


class AccountDialog(BaseDialog):
    """دیالوگ ایجاد/ویرایش حساب با پشتیبانی از تم"""
    
    def __init__(self, code=None, parent=None):
        super().__init__(base_width=550, base_height=600)
        self.account_code = code
        self.parent_widget = parent
        self.setWindowTitle("✏️ ویرایش حساب" if code else "➕ حساب جدید")
        self.setModal(True)
        self.setup_ui()
        if code:
            self.load_account_data()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(self.spacing(15))
        
        # نام حساب
        self.name_edit = self.parent_widget.create_input("نام حساب")
        self.name_edit.setPlaceholderText("مثال: صندوق، بانک ملی")
        layout.addRow("📛 نام حساب *:", self.name_edit)
        
        # نوع حساب
        self.type_combo = QComboBox()
        self.type_combo.addItems(["🏦 دارایی (asset)", "📋 بدهی (liability)", 
                                  "💰 سرمایه (equity)", "📈 درآمد (income)", "💸 هزینه (expense)"])
        layout.addRow("🏷️ نوع حساب:", self.type_combo)
        
        # کد حساب
        self.code_edit = self.parent_widget.create_input("کد حساب")
        if self.account_code:
            self.code_edit.setText(self.account_code)
            self.code_edit.setReadOnly(True)
        layout.addRow("🔢 کد حساب:", self.code_edit)
        
        # حساب والد
        self.parent_code = self.parent_widget.create_input("کد حساب والد")
        self.parent_code.setPlaceholderText("اختیاری")
        layout.addRow("👪 حساب والد:", self.parent_code)
        
        # فعال
        self.is_active = QCheckBox("فعال")
        self.is_active.setChecked(True)
        layout.addRow("✅ وضعیت:", self.is_active)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = self.parent_widget.create_button("💾 ذخیره", "successBtn")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = self.parent_widget.create_button("❌ انصراف", "dangerBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
    
    def load_account_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM accounts WHERE code = ?", [self.account_code])
                acc = c.fetchone()
                if acc:
                    self.name_edit.setText(acc['name'])
                    type_map = {'asset': '🏦 دارایی (asset)', 'liability': '📋 بدهی (liability)',
                               'equity': '💰 سرمایه (equity)', 'income': '📈 درآمد (income)',
                               'expense': '💸 هزینه (expense)'}
                    self.type_combo.setCurrentText(type_map.get(acc['type'], acc['type']))
                    self.parent_code.setText(acc['parent_code'] or "")
                    self.is_active.setChecked(acc['is_active'] == 1)
        except Exception as e:
            print(f"❌ خطا در بارگذاری حساب: {e}")
    
    def get_type_value(self):
        text = self.type_combo.currentText()
        if 'asset' in text:
            return 'asset'
        elif 'liability' in text:
            return 'liability'
        elif 'equity' in text:
            return 'equity'
        elif 'income' in text:
            return 'income'
        elif 'expense' in text:
            return 'expense'
        return text
    
    def check_code_exists(self, code):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code FROM accounts WHERE code = ?", [code])
            return c.fetchone() is not None
    
    def accept(self):
        code = self.code_edit.text().strip()
        if not code:
            QMessageBox.warning(self, "خطا", "کد حساب را وارد کنید!")
            return
        
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "خطا", "نام حساب را وارد کنید!")
            return
        
        if not self.account_code and self.check_code_exists(code):
            QMessageBox.warning(self, "خطا", f"کد '{code}' قبلاً ثبت شده است!")
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                if self.account_code:
                    c.execute('''
                        UPDATE accounts 
                        SET name=?, type=?, parent_code=?, is_active=?
                        WHERE code=?
                    ''', (self.name_edit.text().strip(), self.get_type_value(),
                          self.parent_code.text().strip() or None,
                          1 if self.is_active.isChecked() else 0, self.account_code))
                else:
                    c.execute('''
                        INSERT INTO accounts (code, name, type, parent_code, is_active)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (code, self.name_edit.text().strip(), self.get_type_value(),
                          self.parent_code.text().strip() or None,
                          1 if self.is_active.isChecked() else 0))
                
                conn.commit()
                super().accept()
                
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "خطا", f"کد '{code}' قبلاً ثبت شده است!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا در ذخیره: {str(e)}")
