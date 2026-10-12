# ui/finance/check_dialog.py
# ============================================================
# دیالوگ مدیریت چک — دریافتی و پرداختی
# با اتصال به سند خودکار و آپدیت مانده
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime, timedelta

from ui.base_widgets import BaseDialog
from database import get_db, DateConverter, FinanceHelper
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali
from screen_utils import ScreenManager


class CheckDialog(BaseDialog):
    """دیالوگ افزودن/ویرایش چک"""
    
    # ✅ نگاشت وضعیت‌ها به ایندکس ComboBox
    STATUS_MAP = {
        'pending': 0,
        'collected': 1,
        'bounced': 2,
        'cancelled': 3,
        'postponed': 4,
    }
    
    STATUS_REVERSE = {
        0: 'pending',
        1: 'collected',
        2: 'bounced',
        3: 'cancelled',
        4: 'postponed',
    }
    
    def __init__(self, check_id=None, check_type='received', parent=None):
        super().__init__(parent, base_width=650, base_height=780)
        
        self.check_id = check_id
        self.check_type = check_type
        self.sm = ScreenManager()
        
        # اطلاعات چک قبلی (برای ویرایش)
        self._original_check = None
        
        title = "✏️ ویرایش چک" if check_id else "➕ چک جدید"
        type_text = "دریافتی" if check_type == 'received' else "پرداختی"
        self.setWindowTitle(f"{title} - {type_text}")
        
        self.setModal(True)
        self.setup_ui()
        
        if check_id:
            self.load_data()
        
        self.apply_theme()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(self.sm.get_spacing(10))
        main_layout.setContentsMargins(
            self.sm.get_margin(15), self.sm.get_margin(15),
            self.sm.get_margin(15), self.sm.get_margin(15)
        )
        
        # ─── ScrollArea ───
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(self.sm.get_spacing(15))
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # ═══════════════════════════════════════════
        # 🎯 نوع چک
        # ═══════════════════════════════════════════
        type_group = QGroupBox("🎯 نوع چک")
        type_layout = QHBoxLayout(type_group)
        type_layout.setSpacing(self.sm.get_spacing(10))
        
        self.type_received = QRadioButton("📥 چک دریافتی")
        self.type_received.setMinimumHeight(self.sm.get_scaled(35))
        self.type_received.setStyleSheet(f"""
            QRadioButton {{
                font-size: {self.sm.get_font_size(11)}pt;
                font-weight: bold;
                padding: 8px 15px;
                color: #27ae60;
            }}
        """)
        
        self.type_paid = QRadioButton("📤 چک پرداختی")
        self.type_paid.setMinimumHeight(self.sm.get_scaled(35))
        self.type_paid.setStyleSheet(f"""
            QRadioButton {{
                font-size: {self.sm.get_font_size(11)}pt;
                font-weight: bold;
                padding: 8px 15px;
                color: #e74c3c;
            }}
        """)
        
        if self.check_type == 'received':
            self.type_received.setChecked(True)
        else:
            self.type_paid.setChecked(True)
        
        # ✅ اتصال: تغییر نوع → reload طرف حساب
        self.type_received.toggled.connect(self._on_type_changed)
        self.type_paid.toggled.connect(self._on_type_changed)
        
        type_layout.addWidget(self.type_received)
        type_layout.addWidget(self.type_paid)
        type_layout.addStretch()
        
        content_layout.addWidget(type_group)
        
        # ═══════════════════════════════════════════
        # 📄 اطلاعات چک
        # ═══════════════════════════════════════════
        info_group = QGroupBox("📄 اطلاعات چک")
        form_layout = QFormLayout(info_group)
        form_layout.setSpacing(self.sm.get_spacing(10))
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        self.check_number = QLineEdit()
        self.check_number.setPlaceholderText("مثال: ۱۲۳۴۵۶")
        self.check_number.setMinimumHeight(self.sm.get_scaled(32))
        self.check_number.textChanged.connect(self._update_preview)
        form_layout.addRow("🔢 شماره چک *:", self.check_number)
        
        self.bank_name = QLineEdit()
        self.bank_name.setPlaceholderText("مثال: بانک ملی")
        self.bank_name.setMinimumHeight(self.sm.get_scaled(32))
        self.bank_name.textChanged.connect(self._update_preview)
        form_layout.addRow("🏦 نام بانک:", self.bank_name)
        
        self.branch = QLineEdit()
        self.branch.setPlaceholderText("نام شعبه")
        self.branch.setMinimumHeight(self.sm.get_scaled(32))
        form_layout.addRow("🏛️ شعبه:", self.branch)
        
        self.amount = QLineEdit()
        self.amount.setPlaceholderText("مبلغ به ریال")
        self.amount.setAlignment(Qt.AlignRight)
        self.amount.setMinimumHeight(self.sm.get_scaled(32))
        self.amount.textChanged.connect(self._update_preview)
        form_layout.addRow("💰 مبلغ *:", self.amount)
        
        content_layout.addWidget(info_group)
        
        # ═══════════════════════════════════════════
        # 📅 تاریخ‌ها
        # ═══════════════════════════════════════════
        dates_group = QGroupBox("📅 تاریخ‌ها")
        dates_layout = QFormLayout(dates_group)
        dates_layout.setSpacing(self.sm.get_spacing(10))
        dates_layout.setLabelAlignment(Qt.AlignRight)
        
        self.issue_date = ShamsiDateEdit()
        self.issue_date.set_date(get_today_jalali())
        dates_layout.addRow("📅 تاریخ صدور:", self.issue_date)
        
        self.due_date = ShamsiDateEdit()
        
        try:
            from persiantools.jdatetime import JalaliDate
            today = JalaliDate.today()
            future = today + timedelta(days=30)
            self.due_date.set_date(future.strftime("%Y/%m/%d"))
        except Exception:
            self.due_date.set_date(get_today_jalali())
        
        self.due_date.dateChanged.connect(self._update_preview)
        dates_layout.addRow("⏰ تاریخ سرسید *:", self.due_date)
        
        content_layout.addWidget(dates_group)
        
        # ═══════════════════════════════════════════
        # 👤 طرف حساب
        # ═══════════════════════════════════════════
        party_group = QGroupBox("👤 طرف حساب")
        party_layout = QFormLayout(party_group)
        party_layout.setSpacing(self.sm.get_spacing(10))
        party_layout.setLabelAlignment(Qt.AlignRight)
        
        self.party_combo = QComboBox()
        self.party_combo.setMinimumHeight(self.sm.get_scaled(32))
        self.party_combo.addItem("-- انتخاب کنید --", None)
        self._load_parties()
        party_layout.addRow("👤 طرف حساب:", self.party_combo)
        
        content_layout.addWidget(party_group)
        
        # ═══════════════════════════════════════════
        # 📋 وضعیت
        # ═══════════════════════════════════════════
        status_group = QGroupBox("📋 وضعیت")
        status_layout = QFormLayout(status_group)
        status_layout.setSpacing(self.sm.get_spacing(10))
        status_layout.setLabelAlignment(Qt.AlignRight)
        
        self.status_combo = QComboBox()
        self.status_combo.setMinimumHeight(self.sm.get_scaled(32))
        self.status_combo.addItems([
            "⏳ در جریان",
            "✅ وصول شده",
            "❌ برگشتی",
            "🚫 ابطالی",
            "⏸️ به تعویق افتاده",
        ])
        status_layout.addRow("📋 وضعیت:", self.status_combo)
        
        self.description = QTextEdit()
        self.description.setMaximumHeight(self.sm.get_scaled(80))
        self.description.setPlaceholderText("توضیحات...")
        status_layout.addRow("📝 توضیحات:", self.description)
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(self.sm.get_scaled(60))
        self.notes.setPlaceholderText("یادداشت داخلی...")
        status_layout.addRow("📌 یادداشت:", self.notes)
        
        content_layout.addWidget(status_group)
        
        # ═══════════════════════════════════════════
        # 📊 پیش‌نمایش
        # ═══════════════════════════════════════════
        self.preview_group = QGroupBox("📊 خلاصه")
        preview_layout = QVBoxLayout(self.preview_group)
        
        self.preview_label = QLabel("اطلاعات را وارد کنید...")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(f"""
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            color: #2c3e50;
            font-size: {self.sm.get_font_size(10)}pt;
            line-height: 1.8;
        """)
        preview_layout.addWidget(self.preview_label)
        
        content_layout.addWidget(self.preview_group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)
        
        # ═══════════════════════════════════════════
        # دکمه‌های عملیات (فقط برای ویرایش)
        # ═══════════════════════════════════════════
        if self.check_id:
            action_layout = QHBoxLayout()
            action_layout.setSpacing(self.sm.get_spacing(8))
            
            action_label = QLabel("⚡ عملیات سریع:")
            action_layout.addWidget(action_label)
            
            collect_btn = self.create_button("✅ وصول شد", "successBtn")
            collect_btn.setToolTip("وضعیت را وصول شده قرار می‌دهد و ذخیره می‌کند")
            collect_btn.clicked.connect(lambda: self._quick_action('collected'))
            action_layout.addWidget(collect_btn)
            
            bounce_btn = self.create_button("❌ برگشتی", "dangerBtn")
            bounce_btn.setToolTip("وضعیت را برگشتی قرار می‌دهد")
            bounce_btn.clicked.connect(lambda: self._quick_action('bounced'))
            action_layout.addWidget(bounce_btn)
            
            postpone_btn = self.create_button("⏸️ به تعویق", "warningBtn")
            postpone_btn.setToolTip("وضعیت را به تعویق افتاده قرار می‌دهد")
            postpone_btn.clicked.connect(lambda: self._quick_action('postponed'))
            action_layout.addWidget(postpone_btn)
            
            action_layout.addStretch()
            main_layout.addLayout(action_layout)
        
        # ═══════════════════════════════════════════
        # دکمه‌های اصلی (پایین)
        # ═══════════════════════════════════════════
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = self.create_button("💾 ذخیره", "successBtn")
        save_btn.setMinimumWidth(self.sm.get_scaled(130))
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = self.create_button("❌ انصراف", "dangerBtn")
        cancel_btn.setMinimumWidth(self.sm.get_scaled(100))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(btn_layout)
    
    # ============================================================
    # توابع کمکی
    # ============================================================
    
    def _on_type_changed(self):
        """وقتی نوع چک تغییر کرد → reload طرف‌های حساب"""
        new_type = 'received' if self.type_received.isChecked() else 'paid'
        
        if new_type != self.check_type:
            self.check_type = new_type
            
            # ذخیره انتخاب فعلی
            current_party = self.party_combo.currentData()
            
            # Reload
            self.party_combo.clear()
            self.party_combo.addItem("-- انتخاب کنید --", None)
            self._load_parties()
            
            # تلاش برای انتخاب قبلی
            if current_party:
                idx = self.party_combo.findData(current_party)
                if idx >= 0:
                    self.party_combo.setCurrentIndex(idx)
            
            # آپدیت پیش‌نمایش
            self._update_preview()
    
    def _load_parties(self):
        """بارگذاری طرف‌های حساب بر اساس نوع چک"""
        with get_db() as conn:
            c = conn.cursor()
            
            if self.check_type == 'received':
                # چک دریافتی → از مشتری
                c.execute("""
                    SELECT id, name, code FROM parties 
                    WHERE type = 'customer' 
                    ORDER BY name
                """)
            else:
                # چک پرداختی → به تأمین‌کننده
                c.execute("""
                    SELECT id, name, code FROM parties 
                    WHERE type = 'supplier' 
                    ORDER BY name
                """)
            
            for row in c.fetchall():
                self.party_combo.addItem(f"{row['name']}", row['id'])
    
    def _parse_int(self, text: str) -> int:
        """تبدیل متن به عدد"""
        try:
            clean = text.replace(',', '').replace(' ', '').strip()
            return int(clean) if clean else 0
        except Exception:
            return 0
    
    def _format_amount_input(self):
        """فرمت‌دهی فیلد مبلغ"""
        text = self.amount.text().replace(',', '').strip()
        if text.isdigit():
            value = int(text)
            self.amount.blockSignals(True)
            self.amount.setText(f"{value:,}")
            self.amount.blockSignals(False)
    
    def _update_preview(self):
        """آپدیت پیش‌نمایش"""
        check_number = self.check_number.text().strip() or "---"
        bank = self.bank_name.text().strip() or "---"
        amount = self._parse_int(self.amount.text())
        due_date = self.due_date.get_shamsi()
        
        # محاسبه روزهای باقیمانده
        days_text = ""
        try:
            from persiantools.jdatetime import JalaliDate
            today = JalaliDate.today()
            parts = due_date.split('/')
            if len(parts) == 3:
                due = JalaliDate(int(parts[0]), int(parts[1]), int(parts[2]))
                days = (due.to_gregorian() - today.to_gregorian()).days
                
                if days < 0:
                    days_text = f"<span style='color:#e74c3c; font-weight:bold;'>🔴 {abs(days)} روز تأخیر</span>"
                elif days == 0:
                    days_text = "<span style='color:#e74c3c; font-weight:bold;'>🔥 امروز سرسید!</span>"
                elif days <= 7:
                    days_text = f"<span style='color:#f39c12; font-weight:bold;'>⏰ {days} روز باقی‌مانده</span>"
                else:
                    days_text = f"<span style='color:#27ae60;'>✅ {days} روز باقی‌مانده</span>"
        except Exception:
            pass
        
        type_icon = "📥" if self.type_received.isChecked() else "📤"
        type_text = "دریافتی" if self.type_received.isChecked() else "پرداختی"
        type_color = "#27ae60" if self.type_received.isChecked() else "#e74c3c"
        
        html = f"""
        <div style='text-align:right;'>
            <div style='font-size:14pt; font-weight:bold; color:{type_color}; 
                margin-bottom:15px; padding:10px; background:#f0f0f0; 
                border-radius:6px; text-align:center;'>
                {type_icon} چک {type_text}
            </div>
            <table style='width:100%; border-collapse:collapse;'>
                <tr>
                    <td style='padding:8px; width:40%; background:#f8f9fa; 
                        border:1px solid #ddd;'><b>شماره چک:</b></td>
                    <td style='padding:8px; border:1px solid #ddd;'>{check_number}</td>
                </tr>
                <tr>
                    <td style='padding:8px; background:#f8f9fa; 
                        border:1px solid #ddd;'><b>بانک:</b></td>
                    <td style='padding:8px; border:1px solid #ddd;'>{bank}</td>
                </tr>
                <tr>
                    <td style='padding:8px; background:#f8f9fa; 
                        border:1px solid #ddd;'><b>مبلغ:</b></td>
                    <td style='padding:8px; border:1px solid #ddd; 
                        color:#27ae60; font-size:13pt; font-weight:bold;'>
                        {amount:,.0f} ریال
                    </td>
                </tr>
                <tr>
                    <td style='padding:8px; background:#f8f9fa; 
                        border:1px solid #ddd;'><b>سرسید:</b></td>
                    <td style='padding:8px; border:1px solid #ddd;'>{due_date}</td>
                </tr>
                <tr>
                    <td style='padding:8px; background:#f8f9fa; 
                        border:1px solid #ddd;'><b>وضعیت زمانی:</b></td>
                    <td style='padding:8px; border:1px solid #ddd;'>{days_text}</td>
                </tr>
            </table>
        </div>
        """
        
        self.preview_label.setText(html)
    
    def load_data(self):
        """بارگذاری داده‌های چک"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM checks WHERE id = ?", [self.check_id])
            check = c.fetchone()
            
            if not check:
                return
            
            check = dict(check)
            self._original_check = check.copy()
            
            # نوع
            self.check_type = check.get('type', 'received')
            if self.check_type == 'received':
                self.type_received.setChecked(True)
            else:
                self.type_paid.setChecked(True)
            
            # اطلاعات
            self.check_number.setText(check.get('check_number') or '')
            self.bank_name.setText(check.get('bank_name') or '')
            self.branch.setText(check.get('branch') or '')
            
            amount = check.get('amount', 0)
            if amount:
                self.amount.setText(f"{amount:,}")
            
            # تاریخ‌ها
            if check.get('issue_date'):
                self.issue_date.set_date(safe_display_date(check['issue_date']))
            if check.get('due_date'):
                self.due_date.set_date(safe_display_date(check['due_date']))
            
            # طرف حساب
            if check.get('party_id'):
                idx = self.party_combo.findData(check['party_id'])
                if idx >= 0:
                    self.party_combo.setCurrentIndex(idx)
            
            # وضعیت
            status_idx = self.STATUS_MAP.get(check.get('status', 'pending'), 0)
            self.status_combo.setCurrentIndex(status_idx)
            
            # توضیحات
            self.description.setPlainText(check.get('description') or '')
            self.notes.setPlainText(check.get('notes') or '')
            
            self._update_preview()
    
    def _quick_action(self, new_status: str):
        """عملیات سریع (وصول، برگشتی، تعویق)"""
        status_text_map = {
            'collected': 'وصول شده',
            'bounced': 'برگشتی',
            'postponed': 'به تعویق افتاده',
        }
        
        status_text = status_text_map.get(new_status, new_status)
        
        reply = QMessageBox.question(
            self, "تأیید",
            f"آیا چک به وضعیت «{status_text}» تغییر کند؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # ست کردن وضعیت
            status_idx = self.STATUS_MAP.get(new_status, 0)
            self.status_combo.setCurrentIndex(status_idx)
            
            # ذخیره
            self.accept()
    
    def _validate_dates(self) -> tuple:
        """اعتبارسنجی تاریخ‌ها
        
        Returns:
            (is_valid, error_message)
        """
        try:
            from persiantools.jdatetime import JalaliDate
            
            issue_str = self.issue_date.get_shamsi()
            due_str = self.due_date.get_shamsi()
            
            issue_parts = issue_str.split('/')
            due_parts = due_str.split('/')
            
            if len(issue_parts) != 3 or len(due_parts) != 3:
                return False, "فرمت تاریخ نامعتبر"
            
            issue = JalaliDate(
                int(issue_parts[0]), 
                int(issue_parts[1]), 
                int(issue_parts[2])
            )
            due = JalaliDate(
                int(due_parts[0]), 
                int(due_parts[1]), 
                int(due_parts[2])
            )
            
            if due.to_gregorian() < issue.to_gregorian():
                return False, "تاریخ سرسید باید بعد از تاریخ صدور باشد!"
            
            return True, ""
        except Exception as e:
            return False, f"خطا در اعتبارسنجی تاریخ: {str(e)}"
    
    def _create_check_voucher(self, check_data: dict, action: str = 'create') -> int:
        """ساخت سند خودکار برای چک
        
        Args:
            check_data: اطلاعات چک
            action: 'create' | 'collected' | 'bounced'
        
        Returns:
            voucher_id
        """
        try:
            from ui.finance.auto_voucher import AutoVoucherEngine
            
            check_type = check_data.get('type', 'received')
            amount = check_data.get('amount', 0)
            party_name = check_data.get('party_name', 'طرف حساب')
            date = check_data.get('date', get_today_jalali())
            
            items = []
            
            if check_type == 'received':
                # چک دریافتی
                if action == 'create' or action == 'collected':
                    # بدهکار: حساب دریافتنی (چک‌های دریافتنی)
                    items.append({
                        'account_code': '1103',  # حساب‌های دریافتنی
                        'description': f"چک دریافتی از {party_name}",
                        'debit': amount,
                        'credit': 0
                    })
                    # بستانکار: حساب‌های دریافتنی (تسویه)
                    items.append({
                        'account_code': '1103',
                        'description': f"چک دریافتی از {party_name}",
                        'debit': 0,
                        'credit': amount
                    })
            else:
                # چک پرداختی
                if action == 'create' or action == 'collected':
                    # بدهکار: حساب‌های پرداختنی
                    items.append({
                        'account_code': '2101',
                        'description': f"چک پرداختی به {party_name}",
                        'debit': amount,
                        'credit': 0
                    })
                    # بستانکار: حساب‌های پرداختنی
                    items.append({
                        'account_code': '2101',
                        'description': f"چک پرداختی به {party_name}",
                        'debit': 0,
                        'credit': amount
                    })
            
            voucher_data = {
                'voucher_items': items,
                'description': f"چک {('دریافتی' if check_type == 'received' else 'پرداختی')} - {party_name}"
            }
            
            voucher_id = AutoVoucherEngine.save_voucher(voucher_data, date)
            return voucher_id
        
        except Exception as e:
            print(f"⚠️ خطا در ساخت سند چک: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def accept(self):
        """ذخیره چک"""
        # ─── اعتبارسنجی ───
        if not self.check_number.text().strip():
            QMessageBox.warning(self, "خطا", "شماره چک را وارد کنید!")
            self.check_number.setFocus()
            return
        
        amount = self._parse_int(self.amount.text())
        if amount <= 0:
            QMessageBox.warning(self, "خطا", "مبلغ را وارد کنید!")
            self.amount.setFocus()
            return
        
        # اعتبارسنجی تاریخ
        valid, error = self._validate_dates()
        if not valid:
            QMessageBox.warning(self, "خطا", error)
            return
        
        # اطلاعات
        check_type = 'received' if self.type_received.isChecked() else 'paid'
        status = self.STATUS_REVERSE.get(self.status_combo.currentIndex(), 'pending')
        party_id = self.party_combo.currentData()
        party_name = self.party_combo.currentText() if party_id else ''
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                if self.check_id:
                    # ─── ویرایش ───
                    c.execute('''
                        UPDATE checks SET
                            check_number = ?,
                            bank_name = ?,
                            branch = ?,
                            type = ?,
                            amount = ?,
                            issue_date = ?,
                            due_date = ?,
                            party_id = ?,
                            status = ?,
                            description = ?,
                            notes = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', [
                        self.check_number.text().strip(),
                        self.bank_name.text().strip() or None,
                        self.branch.text().strip() or None,
                        check_type,
                        amount,
                        DateConverter.for_db(self.issue_date.get_shamsi()),
                        DateConverter.for_db(self.due_date.get_shamsi()),
                        party_id,
                        status,
                        self.description.toPlainText(),
                        self.notes.toPlainText(),
                        self.check_id
                    ])
                    check_id = self.check_id
                    
                    # ✅ اگه وضعیت به "وصول شده" تغییر کرد → آپدیت مانده
                    original_status = self._original_check.get('status') if self._original_check else None
                    if status == 'collected' and original_status != 'collected':
                        self._update_balance_on_collect(
                            check_type, amount, party_name
                        )
                    
                else:
                    # ─── ثبت جدید ───
                    c.execute('''
                        INSERT INTO checks
                        (check_number, bank_name, branch, type, amount,
                         issue_date, due_date, party_id, status,
                         description, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [
                        self.check_number.text().strip(),
                        self.bank_name.text().strip() or None,
                        self.branch.text().strip() or None,
                        check_type,
                        amount,
                        DateConverter.for_db(self.issue_date.get_shamsi()),
                        DateConverter.for_db(self.due_date.get_shamsi()),
                        party_id,
                        status,
                        self.description.toPlainText(),
                        self.notes.toPlainText()
                    ])
                    check_id = c.lastrowid
                    
                    # ✅ اگه از ابتدا "وصول شده" ثبت شد → آپدیت مانده
                    if status == 'collected':
                        self._update_balance_on_collect(
                            check_type, amount, party_name
                        )
                
                conn.commit()
            
            # ─── اطلاع موفقیت ───
            if self.check_id:
                QMessageBox.information(self, "موفق", "✅ چک با موفقیت ویرایش شد!")
            else:
                QMessageBox.information(
                    self, "موفق", 
                    f"✅ چک با موفقیت ثبت شد!\n\n"
                    f"📋 شماره چک: {self.check_number.text()}"
                )
            
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def _update_balance_on_collect(self, check_type: str, amount: int, party_name: str):
        """آپدیت مانده بانک/صندوق وقتی چک وصول شد
        
        چک دریافتی: پول وارد صندوق/بانک می‌شه
        چک پرداختی: پول از صندوق/بانک خارج می‌شه
        """
        try:
            # فعلاً صندوق اصلی رو انتخاب می‌کنیم
            # TODO: کاربر بتونه انتخاب کنه که پول کجا واریز/برداشت بشه
            with get_db() as conn:
                c = conn.cursor()
                
                if check_type == 'received':
                    # چک دریافتی → پول وارد صندوق اصلی
                    c.execute("SELECT id FROM cash_boxes WHERE is_active = 1 LIMIT 1")
                    row = c.fetchone()
                    if row:
                        cash_id = row['id']
                        FinanceHelper.update_balance('cash', cash_id, amount)
                        print(f"✅ {amount:,} ریال به صندوق اضافه شد (چک دریافتی)")
                
                else:
                    # چک پرداختی → پول از صندوق اصلی خارج شد
                    c.execute("SELECT id FROM cash_boxes WHERE is_active = 1 LIMIT 1")
                    row = c.fetchone()
                    if row:
                        cash_id = row['id']
                        FinanceHelper.update_balance('cash', cash_id, -amount)
                        print(f"✅ {amount:,} ریال از صندوق کم شد (چک پرداختی)")
        
        except Exception as e:
            print(f"⚠️ خطا در آپدیت مانده: {e}")
