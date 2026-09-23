# ui/parties_widget.py
# ============================================================
# ویجت مدیریت اشخاص با پشتیبانی از تم
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui.base_widgets import BaseWidget, BaseDialog
from database import get_db, ModuleLimitHelper
import sqlite3


# ui/parties_widget.py - بخش سازنده
# ============================================================

class PartiesWidget(BaseWidget):
    """ویجت مدیریت مشتریان و فروشندگان با پشتیبانی از تم و سطح دسترسی"""
    
    def __init__(self, customer_name: str = "", user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        self.customer_name = customer_name
        self.user_level = user_level
        self.current_tab_index = 0
        
        self.setup_ui()
        self.load_data()
        self.update_ui_by_permission()
        self.update_limit_display()
        self.check_and_disable_buttons()
        self.apply_theme()
    
    def set_user_level(self, level: str):
        """تنظیم سطح دسترسی"""
        self.user_level = level
        self.update_ui_by_permission()
    
    def update_ui_by_permission(self):
        """بروزرسانی UI بر اساس سطح دسترسی"""
        can_edit = self.user_level in ['admin', 'accountant', 'inventory']
        
        # بروزرسانی دکمه‌های هر دو تب
        for tab in [self.customer_tab, self.supplier_tab]:
            if hasattr(tab, 'new_btn'):
                tab.new_btn.setVisible(can_edit)
            if hasattr(tab, 'edit_btn'):
                tab.edit_btn.setVisible(can_edit)
            if hasattr(tab, 'delete_btn'):
                tab.delete_btn.setVisible(can_edit)
    
    # ... بقیه کدها ...
        self.setup_ui()
        self.load_data()
        self.update_limit_display()
        self.check_and_disable_buttons()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(self.margin(10), self.margin(10),
                                  self.margin(10), self.margin(10))
        
        title = QLabel("👥 مدیریت اشخاص (مشتریان و فروشندگان)")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        self.customer_tab = self._create_party_tab("customer")
        self.supplier_tab = self._create_party_tab("supplier")
        
        self.tab_widget.addTab(self.customer_tab, "👥 مشتریان")
        self.tab_widget.addTab(self.supplier_tab, "📦 فروشندگان")
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tab_widget)
        
        self.apply_theme()
    
    def _create_party_tab(self, party_type):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(self.spacing(10))
        
        # پنل راست
        right_panel = QWidget()
        right_panel.setObjectName("cardWidget")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(self.spacing(10))
        
        # نوار ابزار
        toolbar = QHBoxLayout()
        toolbar.setSpacing(self.spacing(8))
        
        new_btn = self.create_button("➕ جدید", "successBtn")
        new_btn.clicked.connect(lambda: self.new_party(party_type))
        toolbar.addWidget(new_btn)
        
        edit_btn = self.create_button("✏️ ویرایش", "warningBtn")
        edit_btn.clicked.connect(lambda: self.edit_party(party_type))
        toolbar.addWidget(edit_btn)
        
        delete_btn = self.create_button("🗑️ حذف", "dangerBtn")
        delete_btn.clicked.connect(lambda: self.delete_party(party_type))
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        # لیبل محدودیت
        limit_label = QLabel("")
        toolbar.addWidget(limit_label)
        
        # جستجو
        search_label = QLabel("🔍 جستجو:")
        toolbar.addWidget(search_label)
        
        search_input = self.create_input("نام، کد یا تلفن...")
        search_input.setMaximumWidth(self.scaled(200))
        search_input.textChanged.connect(lambda text: self.filter_parties(party_type, text))
        toolbar.addWidget(search_input)
        
        right_layout.addLayout(toolbar)
        
        # جدول
        table = self.create_table(
            ["کد", "نام", "شرکت", "تلفن", "موبایل", "ایمیل", "مانده حساب"],
            stretch_last=True
        )
        table.cellClicked.connect(self.on_party_selected)
        right_layout.addWidget(table)
        
        # پنل چپ
        left_panel = QWidget()
        left_panel.setObjectName("cardWidget")
        left_panel.setMaximumWidth(self.scaled(450))
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(self.spacing(10))
        
        # اطلاعات
        info_group = QGroupBox("📋 اطلاعات")
        info_layout = QFormLayout(info_group)
        info_layout.setLabelAlignment(Qt.AlignRight)
        
        code_edit = QLineEdit()
        code_edit.setReadOnly(True)
        info_layout.addRow("کد:", code_edit)
        
        name_edit = QLineEdit()
        name_edit.setReadOnly(True)
        info_layout.addRow("نام:", name_edit)
        
        company_edit = QLineEdit()
        company_edit.setReadOnly(True)
        info_layout.addRow("شرکت:", company_edit)
        
        phone_edit = QLineEdit()
        phone_edit.setReadOnly(True)
        info_layout.addRow("تلفن:", phone_edit)
        
        mobile_edit = QLineEdit()
        mobile_edit.setReadOnly(True)
        info_layout.addRow("موبایل:", mobile_edit)
        
        email_edit = QLineEdit()
        email_edit.setReadOnly(True)
        info_layout.addRow("ایمیل:", email_edit)
        
        address_edit = QTextEdit()
        address_edit.setReadOnly(True)
        address_edit.setMaximumHeight(self.scaled(80))
        info_layout.addRow("آدرس:", address_edit)
        
        info_group.setLayout(info_layout)
        left_layout.addWidget(info_group)
        
        # تراکنش‌ها
        trans_group = QGroupBox("🔄 آخرین تراکنش‌ها")
        trans_layout = QVBoxLayout(trans_group)
        
        trans_table = self.create_table(
            ["تاریخ", "نوع", "مبلغ", "شرح"],
            stretch_last=True
        )
        trans_layout.addWidget(trans_table)
        
        trans_group.setLayout(trans_layout)
        left_layout.addWidget(trans_group)
        
        layout.addWidget(right_panel, 2)
        layout.addWidget(left_panel, 1)
        
        # ذخیره ارجاعات
        widget.table = table
        widget.search_input = search_input
        widget.code_edit = code_edit
        widget.name_edit = name_edit
        widget.company_edit = company_edit
        widget.phone_edit = phone_edit
        widget.mobile_edit = mobile_edit
        widget.email_edit = email_edit
        widget.address_edit = address_edit
        widget.trans_table = trans_table
        widget.parties_data = []
        widget.party_type = party_type
        widget.new_btn = new_btn
        widget.limit_label = limit_label
        
        return widget
    
    # ========== توابع اصلی ==========
    
    def get_current_widget(self):
        if self.tab_widget.currentIndex() == 0:
            return self.customer_tab
        return self.supplier_tab
    
    def get_current_type(self):
        return "customer" if self.tab_widget.currentIndex() == 0 else "supplier"
    
    def on_tab_changed(self):
        self.load_data()
        self.update_limit_display()
        self.check_and_disable_buttons()
    
    def load_data(self):
        party_type = self.get_current_type()
        widget = self.get_current_widget()
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, code, name, company, phone, mobile, email, COALESCE(balance, 0) as balance
                FROM parties
                WHERE type = ?
                ORDER BY code
            ''', [party_type])
            parties = c.fetchall()
        
        widget.parties_data = parties
        widget.table.setRowCount(len(parties))
        widget.table.clearSelection()
        
        for i, p in enumerate(parties):
            widget.table.setItem(i, 0, QTableWidgetItem(str(p['code']) if p['code'] else "-"))
            widget.table.setItem(i, 1, QTableWidgetItem(str(p['name']) if p['name'] else "-"))
            widget.table.setItem(i, 2, QTableWidgetItem(str(p['company']) if p['company'] else "-"))
            widget.table.setItem(i, 3, QTableWidgetItem(str(p['phone']) if p['phone'] else "-"))
            widget.table.setItem(i, 4, QTableWidgetItem(str(p['mobile']) if p['mobile'] else "-"))
            widget.table.setItem(i, 5, QTableWidgetItem(str(p['email']) if p['email'] else "-"))
            
            balance_item = QTableWidgetItem(f"{p['balance']:,.0f}")
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if p['balance'] > 0:
                balance_item.setForeground(QColor('#27ae60'))
            elif p['balance'] < 0:
                balance_item.setForeground(QColor('#e84118'))
            widget.table.setItem(i, 6, balance_item)
        
        # پاک کردن اطلاعات
        for edit in [widget.code_edit, widget.name_edit, widget.company_edit,
                    widget.phone_edit, widget.mobile_edit, widget.email_edit]:
            edit.clear()
        widget.address_edit.clear()
        widget.trans_table.setRowCount(0)
        
        self.update_limit_display()
        self.check_and_disable_buttons()
    
    def filter_parties(self, party_type, text):
        widget = self.get_current_widget()
        if not hasattr(widget, 'parties_data'):
            return
        
        if not text:
            parties = widget.parties_data
        else:
            parties = []
            for p in widget.parties_data:
                name = str(p['name']) if p['name'] else ""
                code = str(p['code']) if p['code'] else ""
                phone = str(p['phone']) if p['phone'] else ""
                mobile = str(p['mobile']) if p['mobile'] else ""
                if (text.lower() in name.lower() or text.lower() in code.lower() or
                    text.lower() in phone.lower() or text.lower() in mobile.lower()):
                    parties.append(p)
        
        widget.table.setRowCount(len(parties))
        widget.table.clearSelection()
        
        for i, p in enumerate(parties):
            widget.table.setItem(i, 0, QTableWidgetItem(str(p['code']) if p['code'] else "-"))
            widget.table.setItem(i, 1, QTableWidgetItem(str(p['name']) if p['name'] else "-"))
            widget.table.setItem(i, 2, QTableWidgetItem(str(p['company']) if p['company'] else "-"))
            widget.table.setItem(i, 3, QTableWidgetItem(str(p['phone']) if p['phone'] else "-"))
            widget.table.setItem(i, 4, QTableWidgetItem(str(p['mobile']) if p['mobile'] else "-"))
            widget.table.setItem(i, 5, QTableWidgetItem(str(p['email']) if p['email'] else "-"))
            
            balance_item = QTableWidgetItem(f"{p['balance']:,.0f}")
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if p['balance'] > 0:
                balance_item.setForeground(QColor('#27ae60'))
            elif p['balance'] < 0:
                balance_item.setForeground(QColor('#e84118'))
            widget.table.setItem(i, 6, balance_item)
    
    def on_party_selected(self, row, col=None):
        widget = self.get_current_widget()
        if row < 0 or not hasattr(widget, 'parties_data') or row >= len(widget.parties_data):
            return
        
        party = widget.parties_data[row]
        
        widget.code_edit.setText(str(party['code']) if party['code'] else "-")
        widget.name_edit.setText(str(party['name']) if party['name'] else "-")
        widget.company_edit.setText(str(party['company']) if party['company'] else "-")
        widget.phone_edit.setText(str(party['phone']) if party['phone'] else "-")
        widget.mobile_edit.setText(str(party['mobile']) if party['mobile'] else "-")
        widget.email_edit.setText(str(party['email']) if party['email'] else "-")
        widget.address_edit.setText(str(party['address']) if party['address'] else "")
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT date, type, amount, description
                    FROM party_transactions
                    WHERE party_id = ?
                    ORDER BY date DESC, id DESC
                    LIMIT 20
                ''', [party['id']])
                transactions = c.fetchall()
            
            widget.trans_table.setRowCount(len(transactions))
            for i, t in enumerate(transactions):
                widget.trans_table.setItem(i, 0, QTableWidgetItem(str(t['date']) if t['date'] else "-"))
                
                type_text = "📥 بدهکار" if t['type'] == 'debit' else "📤 بستانکار"
                type_item = QTableWidgetItem(type_text)
                if t['type'] == 'debit':
                    type_item.setForeground(QColor('#e84118'))
                else:
                    type_item.setForeground(QColor('#27ae60'))
                widget.trans_table.setItem(i, 1, type_item)
                
                amount_item = QTableWidgetItem(f"{t['amount']:,.0f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                widget.trans_table.setItem(i, 2, amount_item)
                widget.trans_table.setItem(i, 3, QTableWidgetItem(str(t['description']) if t['description'] else "-"))
        except Exception as e:
            print(f"خطا: {e}")
    
    # ========== محدودیت‌ها ==========
    
    def update_limit_display(self):
        widget = self.get_current_widget()
        if self.customer_name:
            allowed, current, limit, msg = ModuleLimitHelper.check_module_limit(self.customer_name, 'parties')
            if limit > 0:
                remaining = limit - current
                if remaining <= 3:
                    widget.limit_label.setText(f"⚠️ {remaining} شخص باقی مانده")
                elif remaining <= 10:
                    widget.limit_label.setText(f"👥 {remaining} شخص تا سقف مجاز")
                else:
                    widget.limit_label.setText(f"👥 {current} از {limit} شخص")
            else:
                widget.limit_label.setText("👥 نامحدود")
    
    def check_and_disable_buttons(self):
        widget = self.get_current_widget()
        if self.customer_name:
            allowed, current, limit, msg = ModuleLimitHelper.check_module_limit(self.customer_name, 'parties')
            widget.new_btn.setEnabled(allowed)
    
    def check_party_limit(self):
        if self.customer_name:
            allowed, current, limit, msg = ModuleLimitHelper.check_module_limit(self.customer_name, 'parties')
            if not allowed:
                QMessageBox.warning(self, "خطا", f"❌ به سقف مجاز {limit} شخص رسیده‌اید!")
                return False
        return True
    
    def new_party(self, party_type):
        if not self.check_party_limit():
            return
        dialog = PartyDialog(party_type)
        if dialog.exec_():
            self.load_data()
            self.update_limit_display()
            self.check_and_disable_buttons()
            QMessageBox.information(self, "موفق", "✅ شخص جدید اضافه شد!")
    
    def edit_party(self, party_type):
        widget = self.get_current_widget()
        row = widget.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک شخص را انتخاب کنید!")
            return
        if not hasattr(widget, 'parties_data') or row >= len(widget.parties_data):
            return
        party = widget.parties_data[row]
        dialog = PartyDialog(party_type, party['id'])
        if dialog.exec_():
            self.load_data()
            self.update_limit_display()
            QMessageBox.information(self, "موفق", "✅ شخص ویرایش شد!")
    
    def delete_party(self, party_type):
        widget = self.get_current_widget()
        row = widget.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک شخص را انتخاب کنید!")
            return
        if not hasattr(widget, 'parties_data') or row >= len(widget.parties_data):
            return
        party = widget.parties_data[row]
        
        reply = QMessageBox.question(self, "تأیید حذف", f"آیا از حذف '{party['name']}' اطمینان دارید؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('DELETE FROM party_transactions WHERE party_id = ?', [party['id']])
                c.execute('DELETE FROM parties WHERE id = ?', [party['id']])
            self.load_data()
            self.update_limit_display()
            self.check_and_disable_buttons()
            for edit in [widget.code_edit, widget.name_edit, widget.company_edit,
                        widget.phone_edit, widget.mobile_edit, widget.email_edit]:
                edit.clear()
            widget.address_edit.clear()
            widget.trans_table.setRowCount(0)
            QMessageBox.information(self, "موفق", "✅ شخص حذف شد!")


class PartyDialog(BaseDialog):
    """دیالوگ ایجاد/ویرایش شخص"""
    
    def __init__(self, party_type, party_id=None):
        super().__init__(base_width=500, base_height=600)
        self.party_type = party_type
        self.party_id = party_id
        self.screen_manager = self.screen_manager
        
        type_name = "مشتری" if party_type == 'customer' else "فروشنده"
        self.setWindowTitle(f"✏️ ویرایش {type_name}" if party_id else f"➕ افزودن {type_name} جدید")
        self.setModal(True)
        self.setup_ui()
        if party_id:
            self.load_data()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(self.spacing(15))
        layout.setLabelAlignment(Qt.AlignRight)
        
        type_label = QLabel(f"<b>نوع شخص:</b> {'👥 مشتری' if self.party_type == 'customer' else '📦 فروشنده'}")
        type_label.setStyleSheet("padding: 8px; border-radius: 8px;")
        layout.addRow(type_label)
        
        self.code = self.create_input("کد (خودکار)")
        layout.addRow("📋 کد:", self.code)
        
        self.name = self.create_input("نام *")
        self.name.setStyleSheet("border: 2px solid #27ae60;")
        layout.addRow("👤 نام *:", self.name)
        
        self.company = self.create_input("نام شرکت")
        layout.addRow("🏢 شرکت:", self.company)
        
        self.phone = self.create_input("تلفن")
        layout.addRow("📞 تلفن:", self.phone)
        
        self.mobile = self.create_input("موبایل")
        layout.addRow("📱 موبایل:", self.mobile)
        
        self.email = self.create_input("ایمیل")
        layout.addRow("📧 ایمیل:", self.email)
        
        self.address = QTextEdit()
        self.address.setPlaceholderText("آدرس کامل")
        self.address.setMaximumHeight(self.scaled(80))
        layout.addRow("📍 آدرس:", self.address)
        
        self.economic_code = self.create_input("کد اقتصادی")
        layout.addRow("💳 کد اقتصادی:", self.economic_code)
        
        self.national_id = self.create_input("شناسه ملی")
        layout.addRow("🆔 شناسه ملی:", self.national_id)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = self.create_button("💾 ذخیره", "successBtn")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = self.create_button("❌ انصراف", "dangerBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
    
    def create_input(self, placeholder):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setMinimumHeight(self.scaled(32))
        return inp
    
    def load_data(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM parties WHERE id = ?', [self.party_id])
            party = c.fetchone()
            if party:
                self.code.setText(str(party['code']) if party['code'] else "")
                self.name.setText(str(party['name']) if party['name'] else "")
                self.company.setText(str(party['company']) if party['company'] else "")
                self.phone.setText(str(party['phone']) if party['phone'] else "")
                self.mobile.setText(str(party['mobile']) if party['mobile'] else "")
                self.email.setText(str(party['email']) if party['email'] else "")
                self.address.setText(str(party['address']) if party['address'] else "")
                self.economic_code.setText(str(party['economic_code']) if party['economic_code'] else "")
                self.national_id.setText(str(party['national_id']) if party['national_id'] else "")
    
    def get_next_code(self):
        with get_db() as conn:
            c = conn.cursor()
            prefix = "CUST" if self.party_type == 'customer' else "SUPP"
            c.execute(f"SELECT code FROM parties WHERE code LIKE '{prefix}%' ORDER BY code DESC LIMIT 1")
            last_code = c.fetchone()
            if last_code and last_code['code']:
                try:
                    last_num = int(last_code['code'][len(prefix):])
                except:
                    last_num = 0
            else:
                last_num = 0
            return f"{prefix}{last_num + 1:05d}"
    
    def accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "خطا", "نام را وارد کنید!")
            return
        
        code = self.code.text().strip()
        if not code:
            code = self.get_next_code()
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                if self.party_id:
                    c.execute('''
                        UPDATE parties SET code=?, name=?, company=?, phone=?, mobile=?,
                            email=?, address=?, economic_code=?, national_id=?, type=?
                        WHERE id=?
                    ''', (code, self.name.text().strip(), self.company.text().strip() or None,
                          self.phone.text().strip() or None, self.mobile.text().strip() or None,
                          self.email.text().strip() or None, self.address.toPlainText().strip() or None,
                          self.economic_code.text().strip() or None, self.national_id.text().strip() or None,
                          self.party_type, self.party_id))
                else:
                    c.execute("SELECT code FROM parties WHERE code = ?", (code,))
                    if c.fetchone():
                        QMessageBox.warning(self, "خطا", f"کد '{code}' قبلاً ثبت شده است!")
                        return
                    c.execute('''
                        INSERT INTO parties (code, name, company, phone, mobile, email,
                            address, economic_code, national_id, type, balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ''', (code, self.name.text().strip(), self.company.text().strip() or None,
                          self.phone.text().strip() or None, self.mobile.text().strip() or None,
                          self.email.text().strip() or None, self.address.toPlainText().strip() or None,
                          self.economic_code.text().strip() or None, self.national_id.text().strip() or None,
                          self.party_type))
                conn.commit()
            super().accept()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "خطا", f"کد '{code}' قبلاً ثبت شده است!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا: {str(e)}")
