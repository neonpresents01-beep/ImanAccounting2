# ui/party_dialog.py
# ============================================================
# دیالوگ افزودن/ویرایش شخص
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from ui.base_widgets import BaseDialog
from database import get_db


class PartyDialog(BaseDialog):
    """دیالوگ افزودن/ویرایش شخص"""
    
    def __init__(self, party_type: str = 'customer', party_id: int = None,
                 parent=None):
        super().__init__(parent, base_width=750, base_height=650)
        
        self.party_type = party_type
        self.party_id = party_id
        self.is_edit = party_id is not None
        
        type_name = "مشتری" if party_type == 'customer' else "فروشنده"
        action = "ویرایش" if self.is_edit else "جدید"
        self.setWindowTitle(f"✏️ {action} {type_name}")
        self.setModal(True)
        
        self.setup_ui()
        
        if self.is_edit:
            self.load_party_data()
        else:
            self.generate_next_code()
        
        self.apply_theme()
    
    # ═══════════════════════════════════════════════════════
    # UI
    # ═══════════════════════════════════════════════════════
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        self.tabs.addTab(self._create_main_tab(), "📋 اصلی")
        self.tabs.addTab(self._create_contact_tab(), "📞 تماس")
        self.tabs.addTab(self._create_bank_tab(), "🏦 بانکی")
        self.tabs.addTab(self._create_credit_tab(), "💰 اعتبار")
        
        layout.addWidget(self.tabs, 1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setObjectName("successBtn")
        save_btn.setMinimumWidth(130)
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.setMinimumWidth(110)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_main_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        form.setContentsMargins(20, 20, 20, 20)
        
        # کد
        code_layout = QHBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("خودکار")
        self.code_input.setMaximumWidth(200)
        code_layout.addWidget(self.code_input)
        
        auto_code_btn = QPushButton("🔢 خودکار")
        auto_code_btn.setMaximumWidth(100)
        auto_code_btn.clicked.connect(self.generate_next_code)
        code_layout.addWidget(auto_code_btn)
        code_layout.addStretch()
        
        form.addRow("📋 کد *:", code_layout)
        
        # نام
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("نام و نام خانوادگی *")
        form.addRow("👤 نام *:", self.name_input)
        
        # شرکت
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("نام شرکت / کسب‌وکار")
        form.addRow("🏢 شرکت:", self.company_input)
        
        # گروه
        self.group_combo = QComboBox()
        self.group_combo.setEditable(True)
        self.group_combo.addItem("--- بدون گروه ---", "")
        self.load_groups()
        form.addRow("🏷️ گروه:", self.group_combo)
        
        # نوع
        type_label = QLabel(
            "👤 مشتری" if self.party_type == 'customer' else "🏢 تأمین‌کننده"
        )
        type_label.setStyleSheet("""
            background: #e3f2fd; color: #1976D2; padding: 8px;
            border-radius: 6px; font-weight: bold;
        """)
        form.addRow("نوع:", type_label)
        
        # کد ملی
        self.national_id = QLineEdit()
        self.national_id.setPlaceholderText("10 رقم")
        self.national_id.setMaxLength(10)
        form.addRow("🆔 کد ملی:", self.national_id)
        
        # کد اقتصادی
        self.economic_code = QLineEdit()
        self.economic_code.setPlaceholderText("کد اقتصادی")
        form.addRow("💳 کد اقتصادی:", self.economic_code)
        
        # وضعیت
        self.is_active_check = QCheckBox("✅ فعال")
        self.is_active_check.setChecked(True)
        form.addRow("وضعیت:", self.is_active_check)
        
        return widget
    
    def _create_contact_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        form.setContentsMargins(20, 20, 20, 20)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("021-12345678")
        form.addRow("📞 تلفن ثابت:", self.phone_input)
        
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("0912-1234567")
        form.addRow("📱 موبایل:", self.mobile_input)
        
        self.fax_input = QLineEdit()
        self.fax_input.setPlaceholderText("021-12345678")
        form.addRow("📠 فکس:", self.fax_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@domain.com")
        form.addRow("📧 ایمیل:", self.email_input)
        
        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText("آدرس کامل")
        self.address_input.setMaximumHeight(100)
        form.addRow("📍 آدرس:", self.address_input)
        
        return widget
    
    def _create_bank_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        form.setContentsMargins(20, 20, 20, 20)
        
        info = QLabel("💡 اطلاعات بانکی برای فاکتور رسمی")
        info.setStyleSheet("""
            background: #fff3cd; color: #856404; padding: 10px;
            border-radius: 6px;
        """)
        info.setWordWrap(True)
        form.addRow(info)
        
        self.shaba_input = QLineEdit()
        self.shaba_input.setPlaceholderText("IR... (24 رقم)")
        form.addRow("🏦 شبا:", self.shaba_input)
        
        self.card_input = QLineEdit()
        self.card_input.setPlaceholderText("6037-XXXX-XXXX-XXXX")
        form.addRow("💳 کارت:", self.card_input)
        
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("شماره حساب")
        form.addRow("🔢 حساب:", self.account_input)
        
        self.bank_name = QLineEdit()
        self.bank_name.setPlaceholderText("نام بانک")
        form.addRow("🏛️ بانک:", self.bank_name)
        
        return widget
    
    def _create_credit_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        form.setContentsMargins(20, 20, 20, 20)
        
        self.credit_limit = QLineEdit()
        self.credit_limit.setPlaceholderText("0")
        self.credit_limit.setAlignment(Qt.AlignRight)
        self.credit_limit.setText("0")
        form.addRow("💰 سقف اعتبار (ریال):", self.credit_limit)
        
        self.payment_terms = QComboBox()
        self.payment_terms.addItems([
            "نقدی", "30 روزه", "60 روزه", "90 روزه", "سفارشی"
        ])
        form.addRow("⏰ شرایط پرداخت:", self.payment_terms)
        
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("یادداشت...")
        self.notes_input.setMaximumHeight(100)
        form.addRow("📝 یادداشت:", self.notes_input)
        
        return widget
    
    # ═══════════════════════════════════════════════════════
    # Load
    # ═══════════════════════════════════════════════════════
    
    def load_groups(self):
        """بارگذاری گروه‌های موجود"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT DISTINCT group_name FROM parties 
                    WHERE group_name IS NOT NULL AND group_name != ''
                    ORDER BY group_name
                """)
                for row in c.fetchall():
                    group_name = row[0] if not hasattr(row, 'keys') else row['group_name']
                    if group_name:
                        self.group_combo.addItem(group_name, group_name)
        except Exception:
            pass
    
    def generate_next_code(self):
        """تولید کد خودکار"""
        prefix = "CUST" if self.party_type == 'customer' else "SUPP"
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(f"""
                    SELECT code FROM parties 
                    WHERE code LIKE '{prefix}%' 
                    ORDER BY code DESC LIMIT 1
                """)
                last = c.fetchone()
                
                if last:
                    code = last['code'] if hasattr(last, 'keys') else last[0]
                    try:
                        num = int(code.replace(prefix, '')) + 1
                    except:
                        num = 1
                else:
                    num = 1
                
                self.code_input.setText(f"{prefix}{num:05d}")
        except Exception:
            self.code_input.setText(f"{prefix}00001")
    
    def load_party_data(self):
        """بارگذاری اطلاعات شخص"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                # چک ستون‌ها
                c.execute("PRAGMA table_info(parties)")
                columns = [col[1] for col in c.fetchall()]
                
                c.execute("SELECT * FROM parties WHERE id = ?", [self.party_id])
                row = c.fetchone()
                
                if not row:
                    return
                
                p = dict(row)
                
                self.code_input.setText(str(p.get('code', '')))
                self.name_input.setText(str(p.get('name', '')))
                self.company_input.setText(str(p.get('company', '') or ''))
                self.national_id.setText(str(p.get('national_id', '') or ''))
                self.economic_code.setText(str(p.get('economic_code', '') or ''))
                
                # گروه
                group = p.get('group_name', '') or ''
                if group:
                    idx = self.group_combo.findData(group)
                    if idx >= 0:
                        self.group_combo.setCurrentIndex(idx)
                    else:
                        self.group_combo.setEditText(group)
                
                if 'is_active' in columns:
                    self.is_active_check.setChecked(p.get('is_active', 1) == 1)
                
                self.phone_input.setText(str(p.get('phone', '') or ''))
                self.mobile_input.setText(str(p.get('mobile', '') or ''))
                self.email_input.setText(str(p.get('email', '') or ''))
                self.address_input.setPlainText(str(p.get('address', '') or ''))
                
                if 'fax' in columns:
                    self.fax_input.setText(str(p.get('fax', '') or ''))
                
                if 'shaba' in columns:
                    self.shaba_input.setText(str(p.get('shaba', '') or ''))
                if 'card_number' in columns:
                    self.card_input.setText(str(p.get('card_number', '') or ''))
                if 'account_number' in columns:
                    self.account_input.setText(str(p.get('account_number', '') or ''))
                if 'bank_name' in columns:
                    self.bank_name.setText(str(p.get('bank_name', '') or ''))
                
                if 'credit_limit' in columns:
                    cl = p.get('credit_limit', 0) or 0
                    self.credit_limit.setText(f"{cl:,}" if cl else "0")
                
                if 'payment_terms' in columns:
                    pt = p.get('payment_terms', 'نقدی') or 'نقدی'
                    idx = self.payment_terms.findText(pt)
                    if idx >= 0:
                        self.payment_terms.setCurrentIndex(idx)
                
                if 'notes' in columns:
                    self.notes_input.setPlainText(str(p.get('notes', '') or ''))
        
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در بارگذاری:\n{str(e)}")
    
    # ═══════════════════════════════════════════════════════
    # Save
    # ═══════════════════════════════════════════════════════
    
    def accept(self):
        """ذخیره"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "خطا", "نام الزامی است!")
            self.tabs.setCurrentIndex(0)
            return
        
        code = self.code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "خطا", "کد الزامی است!")
            return
        
        # چک تکراری
        try:
            with get_db() as conn:
                c = conn.cursor()
                if self.is_edit:
                    c.execute(
                        "SELECT id FROM parties WHERE code = ? AND id != ?",
                        [code, self.party_id]
                    )
                else:
                    c.execute("SELECT id FROM parties WHERE code = ?", [code])
                
                if c.fetchone():
                    QMessageBox.warning(self, "خطا", f"کد '{code}' قبلاً استفاده شده!")
                    return
        except Exception:
            pass
        
        try:
            credit_limit = int(self.credit_limit.text().replace(',', '').strip() or 0)
        except:
            credit_limit = 0
        
        data = {
            'code': code,
            'name': name,
            'company': self.company_input.text().strip() or None,
            'type': self.party_type,
            'phone': self.phone_input.text().strip() or None,
            'mobile': self.mobile_input.text().strip() or None,
            'fax': self.fax_input.text().strip() or None,
            'email': self.email_input.text().strip() or None,
            'address': self.address_input.toPlainText().strip() or None,
            'national_id': self.national_id.text().strip() or None,
            'economic_code': self.economic_code.text().strip() or None,
            'shaba': self.shaba_input.text().strip() or None,
            'card_number': self.card_input.text().strip() or None,
            'account_number': self.account_input.text().strip() or None,
            'bank_name': self.bank_name.text().strip() or None,
            'group_name': (
                self.group_combo.currentData() 
                if self.group_combo.currentData() 
                else self.group_combo.currentText().strip() or None
            ),
            'credit_limit': credit_limit,
            'payment_terms': self.payment_terms.currentText(),
            'notes': self.notes_input.toPlainText().strip() or None,
            'is_active': 1 if self.is_active_check.isChecked() else 0,
        }
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute("PRAGMA table_info(parties)")
                cols = [col[1] for col in c.fetchall()]
                
                if self.is_edit:
                    set_parts = []
                    values = []
                    for key, value in data.items():
                        if key in cols:
                            set_parts.append(f"{key} = ?")
                            values.append(value)
                    
                    if 'updated_at' in cols:
                        set_parts.append("updated_at = CURRENT_TIMESTAMP")
                    
                    values.append(self.party_id)
                    sql = f"UPDATE parties SET {', '.join(set_parts)} WHERE id = ?"
                    c.execute(sql, values)
                else:
                    insert_cols = []
                    insert_vals = []
                    for key, value in data.items():
                        if key in cols:
                            insert_cols.append(key)
                            insert_vals.append(value)
                    
                    if 'balance' in cols:
                        insert_cols.append('balance')
                        insert_vals.append(0)
                    
                    placeholders = ', '.join(['?'] * len(insert_cols))
                    sql = f"INSERT INTO parties ({', '.join(insert_cols)}) VALUES ({placeholders})"
                    c.execute(sql, insert_vals)
                
                conn.commit()
            
            QMessageBox.information(
                self, "موفق",
                f"✅ {'ویرایش شد' if self.is_edit else 'ذخیره شد'}!"
            )
            super().accept()
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره:\n{str(e)}")
    
    def apply_theme(self):
        """اعمال تم"""
        self.setStyleSheet("""
            QDialog { background: #f5f6fa; }
            QLineEdit, QComboBox, QTextEdit {
                background: white; color: #1a1a2e;
                border: 1px solid #dcdde1; border-radius: 6px;
                padding: 8px 10px; min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 2px solid #1976D2;
            }
            QPushButton {
                padding: 8px 16px; border-radius: 6px;
                font-weight: bold; min-height: 32px;
            }
            QPushButton#successBtn {
                background: #27ae60; color: white; border: none;
            }
            QPushButton#successBtn:hover { background: #1e8449; }
            QPushButton#dangerBtn {
                background: #e74c3c; color: white; border: none;
            }
            QPushButton#dangerBtn:hover { background: #c0392b; }
            QTabWidget::pane {
                border: 1px solid #dcdde1; border-radius: 6px;
                background: white; padding: 5px;
            }
            QTabBar::tab {
                padding: 10px 20px; margin: 2px;
                border-radius: 6px; background: #e8e8e8;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #1976D2; color: white;
            }
        """)
