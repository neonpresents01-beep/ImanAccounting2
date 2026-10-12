# ui/finance_widget.py
# ============================================================
# ویجت امور مالی اتوماتیک — نسخه کامل نهایی v3
# با گزارشات کامل، AI و رفع کامل باگ چک‌های معوق
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime, timedelta
import csv
import os

from ui.base_widgets import BaseWidget, BaseDialog
from database import get_db, ModuleLimitHelper, FinanceHelper, DateConverter
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali
from screen_utils import ScreenManager


# ============================================================
# کلاس اصلی
# ============================================================

class FinanceWidget(BaseWidget):
    """ویجت امور مالی - مشابه هلو ولی هوشمندتر"""
    
    # ✅ وضعیت‌های "باز" چک (هنوز تسویه نشده)
    OPEN_CHECK_STATUSES = ('pending', 'postponed')
    
    # ✅ وضعیت‌های "بسته" چک
    CLOSED_CHECK_STATUSES = ('collected', 'bounced', 'cancelled')
    
    def __init__(self, customer_name: str = "", user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        
        self.customer_name = customer_name
        self.user_level = user_level
        self.current_operation = 'receipt'
        self.bank_accounts = []
        self.cash_boxes = []
        self.parties = []
        
        self.sm = ScreenManager()
        
        self.setup_ui()
        self.load_data()
        self.update_ui_by_permission()
        self.apply_theme()
    
    # ============================================================
    # مدیریت دسترسی
    # ============================================================
    
    def set_user_level(self, level: str):
        self.user_level = level
        self.update_ui_by_permission()
    
    def update_ui_by_permission(self):
        can_edit = self.user_level in ['admin', 'accountant']
        
        for btn_name in ['save_btn', 'clear_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setVisible(can_edit)
    
    # ============================================================
    # رابط کاربری اصلی
    # ============================================================
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.sm.get_spacing(10))
        layout.setContentsMargins(
            self.sm.get_margin(15), self.sm.get_margin(15),
            self.sm.get_margin(15), self.sm.get_margin(15)
        )
        
        # ─── عنوان ───
        title_layout = QHBoxLayout()
        
        title = QLabel("💰 امور مالی")
        title.setObjectName("titleLabel")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        refresh_btn = self.create_button("🔄 بروزرسانی", "infoBtn")
        refresh_btn.clicked.connect(self.load_data)
        title_layout.addWidget(refresh_btn)
        
        layout.addLayout(title_layout)
        
        # ─── کارت‌های خلاصه ───
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(self.sm.get_spacing(10))
        
        self.card_banks = self._create_summary_card("🏦 بانک‌ها", "۰", "#2980b9")
        self.card_cash = self._create_summary_card("💵 صندوق", "۰", "#27ae60")
        self.card_checks = self._create_summary_card("📄 چک‌ها", "۰", "#f39c12")
        self.card_total = self._create_summary_card("💰 مجموع", "۰", "#e94560")
        
        summary_layout.addWidget(self.card_banks)
        summary_layout.addWidget(self.card_cash)
        summary_layout.addWidget(self.card_checks)
        summary_layout.addWidget(self.card_total)
        
        layout.addLayout(summary_layout)
        
        # ─── تب‌ها ───
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        self.tabs.addTab(self._create_transaction_tab(), "💳 تراکنش جدید")
        self.tabs.addTab(self._create_banks_tab(), "🏦 بانک‌ها")
        self.tabs.addTab(self._create_cash_tab(), "💵 صندوق‌ها")
        self.tabs.addTab(self._create_checks_tab(), "📄 چک‌ها")
        self.tabs.addTab(self._create_history_tab(), "📊 تاریخچه")
        self.tabs.addTab(self._create_reports_tab(), "📈 گزارشات")
        self.tabs.addTab(self._create_ai_tab(), "🤖 دستیار AI")
        
        layout.addWidget(self.tabs)
        
        QTimer.singleShot(300, lambda: self._on_operation_selected('receipt'))
    
    # ============================================================
    # کارت خلاصه
    # ============================================================
    
    def _create_summary_card(self, title: str, value: str, color: str) -> QFrame:
        """کارت خلاصه با رنگ ثابت"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {color};
                border-radius: 10px;
                padding: 12px;
                color: white;
                min-height: {self.sm.get_scaled(75)}px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(self.sm.get_spacing(5))
        
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: {self.sm.get_font_size(10)}pt; "
            f"font-weight: bold; color: white; background: transparent;"
        )
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(
            f"font-size: {self.sm.get_font_size(13)}pt; "
            f"font-weight: bold; color: white; background: transparent;"
        )
        value_label.setWordWrap(True)
        layout.addWidget(value_label)
        
        card.value_label = value_label
        return card
    
    # ============================================================
    # تب ۱: تراکنش جدید
    # ============================================================
    
    def _create_transaction_tab(self):
        """تب تراکنش جدید"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setSpacing(self.sm.get_spacing(10))
        main_layout.setContentsMargins(
            self.sm.get_margin(10), self.sm.get_margin(10),
            self.sm.get_margin(10), self.sm.get_margin(10)
        )
        
        # ─── نوع عملیات ───
        type_group = QGroupBox("🎯 نوع عملیات")
        type_group.setMaximumHeight(self.sm.get_scaled(140))
        type_layout = QGridLayout(type_group)
        type_layout.setSpacing(self.sm.get_spacing(8))
        
        self.operation_buttons = {}
        
        operations = [
            ("📥 دریافت", "receipt", "#27ae60"),
            ("📤 پرداخت", "payment", "#e74c3c"),
            ("🔄 انتقال", "transfer", "#3498db"),
            ("📈 سود بانکی", "bank_profit", "#f39c12"),
            ("💰 درآمد", "income", "#16a085"),
            ("💸 هزینه", "expense", "#c0392b"),
            ("🏦 سرمایه", "capital", "#9b59b6"),
            ("💳 کارت به کارت", "card_to_card", "#34495e"),
        ]
        
        for i, (label, key, color) in enumerate(operations):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(self.sm.get_scaled(40))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: {self.sm.get_font_size(10)}pt;
                    font-weight: bold;
                    padding: 6px;
                }}
                QPushButton:hover {{
                    background: {color}CC;
                }}
                QPushButton:checked {{
                    border: 3px solid #fff;
                }}
            """)
            btn.clicked.connect(
                lambda checked, k=key: self._on_operation_selected(k)
            )
            type_layout.addWidget(btn, i // 4, i % 4)
            self.operation_buttons[key] = btn
        
        main_layout.addWidget(type_group)
        
        # ─── ScrollArea ───
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(self.sm.get_spacing(12))
        scroll_layout.setContentsMargins(
            self.sm.get_margin(5), self.sm.get_margin(5),
            self.sm.get_margin(5), self.sm.get_margin(5)
        )
        
        # ─── فرم ───
        form_group = QGroupBox("📝 اطلاعات تراکنش")
        self.form_layout = QFormLayout(form_group)
        self.form_layout.setSpacing(self.sm.get_spacing(10))
        self.form_layout.setLabelAlignment(Qt.AlignRight)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        self.date_input = ShamsiDateEdit()
        self.date_input.set_date(get_today_jalali())
        self.date_input.dateChanged.connect(self._update_voucher_preview)
        self.form_layout.addRow("📅 تاریخ:", self.date_input)
        
        self.from_account_label = QLabel("از حساب:")
        self.from_account_combo = QComboBox()
        self.from_account_combo.setMinimumHeight(self.sm.get_scaled(32))
        self.from_account_combo.currentIndexChanged.connect(self._update_voucher_preview)
        self.form_layout.addRow(self.from_account_label, self.from_account_combo)
        
        self.to_account_label = QLabel("به حساب:")
        self.to_account_combo = QComboBox()
        self.to_account_combo.setMinimumHeight(self.sm.get_scaled(32))
        self.to_account_combo.currentIndexChanged.connect(self._update_voucher_preview)
        self.form_layout.addRow(self.to_account_label, self.to_account_combo)
        
        self.party_label = QLabel("طرف حساب:")
        self.party_combo = QComboBox()
        self.party_combo.setMinimumHeight(self.sm.get_scaled(32))
        self.party_combo.addItem("-- بدون طرف حساب --", None)
        self.form_layout.addRow(self.party_label, self.party_combo)
        
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("مبلغ به ریال")
        self.amount_input.setAlignment(Qt.AlignRight)
        self.amount_input.setMinimumHeight(self.sm.get_scaled(32))
        self.amount_input.textChanged.connect(self._update_voucher_preview)
        self.form_layout.addRow("💰 مبلغ *:", self.amount_input)
        
        self.fee_input = QLineEdit()
        self.fee_input.setPlaceholderText("۰")
        self.fee_input.setAlignment(Qt.AlignRight)
        self.fee_input.setMinimumHeight(self.sm.get_scaled(32))
        self.fee_input.textChanged.connect(self._update_voucher_preview)
        self.form_layout.addRow("💳 کارمزد:", self.fee_input)
        
        self.discount_input = QLineEdit()
        self.discount_input.setPlaceholderText("۰")
        self.discount_input.setAlignment(Qt.AlignRight)
        self.discount_input.setMinimumHeight(self.sm.get_scaled(32))
        self.discount_input.textChanged.connect(self._update_voucher_preview)
        self.form_layout.addRow("🏷️ تخفیف:", self.discount_input)
        
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("اختیاری")
        self.ref_input.setMinimumHeight(self.sm.get_scaled(32))
        self.form_layout.addRow("🔢 شماره پیگیری:", self.ref_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(self.sm.get_scaled(70))
        self.description_input.setPlaceholderText("توضیحات...")
        self.form_layout.addRow("📝 توضیحات:", self.description_input)
        
        scroll_layout.addWidget(form_group)
        
        # ─── پیش‌نمایش ───
        voucher_group = QGroupBox("📋 پیش‌نمایش سند خودکار")
        voucher_layout = QVBoxLayout(voucher_group)
        
        info_label = QLabel("💡 سند حسابداری به‌صورت خودکار ساخته می‌شود.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            f"color: {self.get_theme_colors().get('text_secondary', '#666')}; "
            f"font-size: {self.sm.get_font_size(9)}pt; "
            f"padding: 5px; background: #fff3cd; border-radius: 5px;"
        )
        voucher_layout.addWidget(info_label)
        
        self.voucher_preview = QTextEdit()
        self.voucher_preview.setReadOnly(True)
        self.voucher_preview.setMinimumHeight(self.sm.get_scaled(150))
        self.voucher_preview.setStyleSheet(f"""
            QTextEdit {{
                background: #f8f9fa;
                font-family: Tahoma;
                font-size: {self.sm.get_font_size(9)}pt;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 6px;
                color: #2c3e50;
            }}
        """)
        voucher_layout.addWidget(self.voucher_preview)
        
        scroll_layout.addWidget(voucher_group)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)
        
        # ─── دکمه‌ها ───
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.clear_btn = self.create_button("🗑️ پاک کردن", "warningBtn")
        self.clear_btn.setMinimumHeight(self.sm.get_scaled(42))
        self.clear_btn.setMinimumWidth(self.sm.get_scaled(130))
        self.clear_btn.clicked.connect(self._clear_form)
        btn_layout.addWidget(self.clear_btn)
        
        self.save_btn = self.create_button("💾 ذخیره", "successBtn")
        self.save_btn.setMinimumHeight(self.sm.get_scaled(42))
        self.save_btn.setMinimumWidth(self.sm.get_scaled(150))
        self.save_btn.clicked.connect(self._save_transaction)
        btn_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(btn_layout)
        
        return widget
    
    def _on_operation_selected(self, op_type: str):
        """وقتی نوع عملیات انتخاب شد"""
        self.current_operation = op_type
        
        for key, btn in self.operation_buttons.items():
            btn.setChecked(key == op_type)
        
        config = {
            'receipt':      {'from': False, 'to': True,  'party': True},
            'payment':      {'from': True,  'to': False, 'party': True},
            'transfer':     {'from': True,  'to': True,  'party': False},
            'bank_profit':  {'from': False, 'to': True,  'party': False},
            'income':       {'from': False, 'to': True,  'party': False},
            'expense':      {'from': True,  'to': False, 'party': False},
            'capital':      {'from': False, 'to': True,  'party': True},
            'card_to_card': {'from': True,  'to': True,  'party': False},
        }
        
        cfg = config.get(op_type, {})
        
        self.from_account_label.setVisible(cfg.get('from', False))
        self.from_account_combo.setVisible(cfg.get('from', False))
        self.to_account_label.setVisible(cfg.get('to', False))
        self.to_account_combo.setVisible(cfg.get('to', False))
        self.party_label.setVisible(cfg.get('party', False))
        self.party_combo.setVisible(cfg.get('party', False))
        
        self._update_voucher_preview()
    
    def _update_voucher_preview(self):
        """آپدیت پیش‌نمایش سند خودکار"""
        try:
            amount = self._parse_int(self.amount_input.text())
            if amount <= 0:
                self.voucher_preview.setHtml(
                    "<div style='text-align:center;color:#999;padding:20px;'>"
                    "مبلغ را وارد کنید تا سند نمایش داده شود"
                    "</div>"
                )
                return
            
            from ui.finance.auto_voucher import AutoVoucherEngine
            
            data = {
                'type': self.current_operation,
                'date': self.date_input.get_shamsi(),
                'amount': amount,
                'fee': self._parse_int(self.fee_input.text()),
                'discount': self._parse_int(self.discount_input.text()),
                'from_account': self._get_selected_account(self.from_account_combo),
                'to_account': self._get_selected_account(self.to_account_combo),
                'party_id': self.party_combo.currentData(),
                'party_name': self.party_combo.currentText() if self.party_combo.currentIndex() > 0 else '',
                'description': self.description_input.toPlainText()
            }
            
            voucher_data = AutoVoucherEngine.create_from_transaction(data)
            html = self._format_voucher_html(voucher_data)
            self.voucher_preview.setHtml(html)
        
        except Exception:
            self.voucher_preview.setHtml(
                "<div style='color:#999;padding:20px;'>"
                "در انتظار تکمیل اطلاعات..."
                "</div>"
            )
    
    def _format_voucher_html(self, voucher_data: dict) -> str:
        """فرمت HTML سند"""
        font_size = self.sm.get_font_size(10)
        
        html = f"""
        <table style='width:100%; border-collapse:collapse; font-size:{font_size}pt;'>
            <thead>
                <tr style='background:#273c75; color:white;'>
                    <th style='padding:6px; text-align:right;'>کد حساب</th>
                    <th style='padding:6px; text-align:right;'>شرح</th>
                    <th style='padding:6px; text-align:center;'>بدهکار</th>
                    <th style='padding:6px; text-align:center;'>بستانکار</th>
                </tr>
            </thead>
            <tbody>
        """
        
        total_debit = 0
        total_credit = 0
        
        for item in voucher_data['voucher_items']:
            debit = item['debit']
            credit = item['credit']
            total_debit += debit
            total_credit += credit
            
            html += f"""
            <tr style='border-bottom:1px solid #eee;'>
                <td style='padding:6px;'>{item['account_code']}</td>
                <td style='padding:6px;'>{item['description']}</td>
                <td style='padding:6px; text-align:left; color:#27ae60;'>
                    {f"{debit:,.0f}" if debit > 0 else "-"}
                </td>
                <td style='padding:6px; text-align:left; color:#e74c3c;'>
                    {f"{credit:,.0f}" if credit > 0 else "-"}
                </td>
            </tr>
            """
        
        html += f"""
            <tr style='font-weight:bold; background:#f0f0f0;'>
                <td colspan='2' style='padding:6px;'>جمع</td>
                <td style='padding:6px; text-align:left;'>{total_debit:,.0f}</td>
                <td style='padding:6px; text-align:left;'>{total_credit:,.0f}</td>
            </tr>
        </tbody>
        </table>
        """
        
        if abs(total_debit - total_credit) < 1:
            html += """
            <div style='margin-top:10px; padding:8px; background:#d4edda; 
                        color:#155724; border-radius:5px; text-align:center;'>
                ✅ سند موازنه است
            </div>
            """
        
        return html
    
    # ============================================================
    # تب ۲: بانک‌ها
    # ============================================================
    
    def _create_banks_tab(self):
        """تب بانک‌ها"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(self.sm.get_spacing(10))
        layout.setContentsMargins(
            self.sm.get_margin(10), self.sm.get_margin(10),
            self.sm.get_margin(10), self.sm.get_margin(10)
        )
        
        toolbar = QHBoxLayout()
        
        new_bank_btn = self.create_button("➕ بانک جدید", "successBtn")
        new_bank_btn.clicked.connect(self._add_bank)
        toolbar.addWidget(new_bank_btn)
        
        edit_bank_btn = self.create_button("✏️ ویرایش", "warningBtn")
        edit_bank_btn.clicked.connect(self._edit_bank)
        toolbar.addWidget(edit_bank_btn)
        
        delete_bank_btn = self.create_button("🗑️ حذف", "dangerBtn")
        delete_bank_btn.clicked.connect(self._delete_bank)
        toolbar.addWidget(delete_bank_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        self.banks_table = self.create_table(
            ["کد", "نام بانک", "شماره حساب", "شماره کارت", "مانده", "وضعیت"],
            stretch_last=True
        )
        self.banks_table.doubleClicked.connect(self._edit_bank)
        layout.addWidget(self.banks_table)
        
        return widget
    
    # ============================================================
    # تب ۳: صندوق‌ها
    # ============================================================
    
    def _create_cash_tab(self):
        """تب صندوق‌ها"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(self.sm.get_spacing(10))
        layout.setContentsMargins(
            self.sm.get_margin(10), self.sm.get_margin(10),
            self.sm.get_margin(10), self.sm.get_margin(10)
        )
        
        toolbar = QHBoxLayout()
        
        new_cash_btn = self.create_button("➕ صندوق جدید", "successBtn")
        new_cash_btn.clicked.connect(self._add_cash)
        toolbar.addWidget(new_cash_btn)
        
        edit_cash_btn = self.create_button("✏️ ویرایش", "warningBtn")
        edit_cash_btn.clicked.connect(self._edit_cash)
        toolbar.addWidget(edit_cash_btn)
        
        delete_cash_btn = self.create_button("🗑️ حذف", "dangerBtn")
        delete_cash_btn.clicked.connect(self._delete_cash)
        toolbar.addWidget(delete_cash_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        self.cash_table = self.create_table(
            ["کد", "نام صندوق", "محل", "مانده", "وضعیت"],
            stretch_last=True
        )
        self.cash_table.doubleClicked.connect(self._edit_cash)
        layout.addWidget(self.cash_table)
        
        return widget
    
    # ============================================================
    # تب ۴: چک‌ها
    # ============================================================
    
    def _create_checks_tab(self):
        """تب چک‌ها"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(self.sm.get_spacing(10))
        layout.setContentsMargins(
            self.sm.get_margin(10), self.sm.get_margin(10),
            self.sm.get_margin(10), self.sm.get_margin(10)
        )
        
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("🔍 فیلتر:"))
        
        self.check_filter = QComboBox()
        self.check_filter.addItems([
            "همه چک‌ها",
            "📥 چک‌های دریافتی",
            "📤 چک‌های پرداختی",
            "⏳ در جریان",
            "✅ وصول شده",
            "❌ برگشتی",
            "⏸️ به تعویق افتاده",
            "🔴 معوق",
        ])
        self.check_filter.currentIndexChanged.connect(self._load_checks)
        filter_layout.addWidget(self.check_filter)
        
        filter_layout.addStretch()
        
        new_check_btn = self.create_button("➕ چک جدید", "successBtn")
        new_check_btn.clicked.connect(self._add_check)
        filter_layout.addWidget(new_check_btn)
        
        edit_check_btn = self.create_button("✏️ ویرایش", "warningBtn")
        edit_check_btn.clicked.connect(self._edit_check)
        filter_layout.addWidget(edit_check_btn)
        
        layout.addLayout(filter_layout)
        
        self.checks_table = self.create_table(
            ["شماره چک", "بانک", "نوع", "مبلغ", "سرسید", "وضعیت", "طرف حساب"],
            stretch_last=True
        )
        self.checks_table.doubleClicked.connect(self._edit_check)
        layout.addWidget(self.checks_table)
        
        self.check_alert = QLabel("")
        self.check_alert.setWordWrap(True)
        self.check_alert.setStyleSheet(
            "padding: 8px; border-radius: 5px; font-weight: bold;"
        )
        layout.addWidget(self.check_alert)
        
        return widget
    
    # ============================================================
    # تب ۵: تاریخچه
    # ============================================================
    
    def _create_history_tab(self):
        """تب تاریخچه تراکنش‌ها"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(self.sm.get_spacing(10))
        layout.setContentsMargins(
            self.sm.get_margin(10), self.sm.get_margin(10),
            self.sm.get_margin(10), self.sm.get_margin(10)
        )
        
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("از:"))
        self.history_from = ShamsiDateEdit()
        self.history_from.set_date(get_today_jalali())
        filter_layout.addWidget(self.history_from)
        
        filter_layout.addWidget(QLabel("تا:"))
        self.history_to = ShamsiDateEdit()
        self.history_to.set_date(get_today_jalali())
        filter_layout.addWidget(self.history_to)
        
        show_btn = self.create_button("🔍 نمایش", "infoBtn")
        show_btn.clicked.connect(self._load_history)
        filter_layout.addWidget(show_btn)
        
        filter_layout.addStretch()
        
        export_btn = self.create_button("📎 خروجی", "successBtn")
        export_btn.clicked.connect(self._export_history)
        filter_layout.addWidget(export_btn)
        
        layout.addLayout(filter_layout)
        
        self.history_table = self.create_table(
            ["شماره", "تاریخ", "نوع", "از", "به", "طرف حساب", "مبلغ", "شرح"],
            stretch_last=True
        )
        layout.addWidget(self.history_table)
        
        self.history_total = QLabel("جمع: ۰")
        self.history_total.setStyleSheet(
            "padding: 8px; background: #f0f0f0; border-radius: 5px; font-weight: bold;"
        )
        layout.addWidget(self.history_total)
        
        return widget
    
    # ============================================================
    # تب ۶: گزارشات
    # ============================================================
    
    def _create_reports_tab(self):
        """تب گزارشات"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(self.sm.get_spacing(10))
        layout.setContentsMargins(
            self.sm.get_margin(10), self.sm.get_margin(10),
            self.sm.get_margin(10), self.sm.get_margin(10)
        )
        
        reports_layout = QGridLayout()
        reports_layout.setSpacing(self.sm.get_spacing(10))
        
        # ✅ ۸ گزارش (شامل همه چک‌های باز)
        reports = [
            ("📊 تراکنش‌های امروز", self._report_today, "#3498db"),
            ("📅 تراکنش‌های هفته", self._report_week, "#9b59b6"),
            ("💰 جریان نقدی", self._report_cash_flow, "#27ae60"),
            ("📈 نمودار درآمد/هزینه", self._report_chart, "#e74c3c"),
            ("📋 همه چک‌های باز", self._report_open_checks, "#2980b9"),
            ("⏳ چک‌های معوق", self._report_overdue_checks, "#f39c12"),
            ("💼 خلاصه حساب‌ها", self._report_accounts_summary, "#16a085"),
            ("📊 خلاصه وضعیت", self._report_overall_summary, "#8e44ad"),
        ]
        
        for i, (label, callback, color) in enumerate(reports):
            btn = QPushButton(label)
            btn.setMinimumHeight(self.sm.get_scaled(80))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: {self.sm.get_font_size(11)}pt;
                    font-weight: bold;
                    padding: 15px;
                }}
                QPushButton:hover {{
                    background: {color}CC;
                }}
            """)
            btn.clicked.connect(callback)
            reports_layout.addWidget(btn, i // 2, i % 2)
        
        layout.addLayout(reports_layout)
        
        # ─── خروجی کامل ───
        export_group = QGroupBox("📎 خروجی کامل")
        export_layout = QHBoxLayout(export_group)
        
        csv_btn = self.create_button("📄 Excel (CSV)", "successBtn")
        csv_btn.clicked.connect(self._export_full_report_csv)
        export_layout.addWidget(csv_btn)
        
        summary_btn = self.create_button("📊 گزارش خلاصه", "infoBtn")
        summary_btn.clicked.connect(self._report_overall_summary)
        export_layout.addWidget(summary_btn)
        
        export_layout.addStretch()
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        return widget
    
    # ============================================================
    # تب ۷: AI
    # ============================================================
    
    def _create_ai_tab(self):
        """تب AI مالی"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(self.sm.get_spacing(10))
        layout.setContentsMargins(
            self.sm.get_margin(10), self.sm.get_margin(10),
            self.sm.get_margin(10), self.sm.get_margin(10)
        )
        
        info = QLabel(
            "🤖 دستیار هوشمند امور مالی\n"
            "تحلیل، پیش‌بینی و پیشنهاد خودکار"
        )
        info.setStyleSheet(f"""
            font-size: {self.sm.get_font_size(13)}pt;
            font-weight: bold;
            color: #e94560;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        """)
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        ai_layout = QGridLayout()
        ai_layout.setSpacing(self.sm.get_spacing(10))
        
        ai_features = [
            ("📊 تحلیل جریان نقدی", self._ai_cash_flow, "#3498db"),
            ("🔮 پیش‌بینی بحران", self._ai_predict_crisis, "#e74c3c"),
            ("🔍 تشخیص تراکنش مشکوک", self._ai_detect_fraud, "#f39c12"),
            ("💡 پیشنهاد اولویت پرداخت", self._ai_suggest_priority, "#27ae60"),
            ("📈 روند درآمد/هزینه", self._ai_trend_analysis, "#9b59b6"),
            ("🎤 دستور صوتی", self._ai_voice_command, "#16a085"),
        ]
        
        for i, (label, callback, color) in enumerate(ai_features):
            btn = QPushButton(label)
            btn.setMinimumHeight(self.sm.get_scaled(70))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: {self.sm.get_font_size(11)}pt;
                    font-weight: bold;
                    padding: 15px;
                }}
                QPushButton:hover {{
                    background: {color}CC;
                }}
            """)
            btn.clicked.connect(callback)
            ai_layout.addWidget(btn, i // 2, i % 2)
        
        layout.addLayout(ai_layout)
        
        self.ai_result = QTextEdit()
        self.ai_result.setReadOnly(True)
        self.ai_result.setMinimumHeight(self.sm.get_scaled(200))
        self.ai_result.setStyleSheet(f"""
            QTextEdit {{
                background: #f8f9fa;
                font-family: Tahoma;
                font-size: {self.sm.get_font_size(10)}pt;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 8px;
                color: #2c3e50;
            }}
        """)
        layout.addWidget(self.ai_result)
        
        return widget
    
    # ============================================================
    # توابع کمکی
    # ============================================================
    
    def _parse_int(self, text: str) -> int:
        """تبدیل متن به عدد"""
        try:
            clean = text.replace(',', '').replace(' ', '').strip()
            return int(clean) if clean else 0
        except Exception:
            return 0
    
    def _get_selected_account(self, combo: QComboBox) -> dict:
        """دریافت حساب انتخاب‌شده"""
        if combo.currentIndex() < 0:
            return {}
        
        data = combo.currentData()
        if not data:
            return {}
        
        return data
    
    def _calculate_days_diff(self, due_date: str) -> int:
        """محاسبه اختلاف روز با تاریخ امروز
        
        Returns:
            مثبت: تعداد روزهای تأخیر
            صفر: امروز
            منفی: تعداد روزهای باقی‌مانده
        """
        try:
            from persiantools.jdatetime import JalaliDate
            today = JalaliDate.today()
            parts = due_date.split('/')
            due = JalaliDate(int(parts[0]), int(parts[1]), int(parts[2]))
            return (today.to_gregorian() - due.to_gregorian()).days
        except Exception:
            return 0
    
    def _clear_form(self):
        """پاک کردن فرم"""
        self.amount_input.clear()
        self.fee_input.clear()
        self.discount_input.clear()
        self.ref_input.clear()
        self.description_input.clear()
        self.voucher_preview.clear()
        
        self._on_operation_selected('receipt')
    
    # ============================================================
    # ذخیره تراکنش
    # ============================================================
    
    def _save_transaction(self):
        """ذخیره تراکنش"""
        amount = self._parse_int(self.amount_input.text())
        
        if amount <= 0:
            QMessageBox.warning(self, "خطا", "لطفاً مبلغ را وارد کنید!")
            return
        
        needs_from = self.current_operation in ['payment', 'expense', 'transfer', 'card_to_card']
        needs_to = self.current_operation in ['receipt', 'income', 'capital', 'bank_profit', 'transfer', 'card_to_card']
        
        if needs_from and self.from_account_combo.currentIndex() < 0:
            QMessageBox.warning(self, "خطا", "لطفاً حساب مبدأ را انتخاب کنید!")
            return
        
        if needs_to and self.to_account_combo.currentIndex() < 0:
            QMessageBox.warning(self, "خطا", "لطفاً حساب مقصد را انتخاب کنید!")
            return
        
        data = {
            'type': self.current_operation,
            'date': self.date_input.get_shamsi(),
            'amount': amount,
            'fee': self._parse_int(self.fee_input.text()),
            'discount': self._parse_int(self.discount_input.text()),
            'from_account': self._get_selected_account(self.from_account_combo),
            'to_account': self._get_selected_account(self.to_account_combo),
            'party_id': self.party_combo.currentData(),
            'party_name': self.party_combo.currentText() if self.party_combo.currentIndex() > 0 else '',
            'description': self.description_input.toPlainText(),
            'reference_no': self.ref_input.text()
        }
        
        try:
            from ui.finance.auto_voucher import AutoVoucherEngine
            
            voucher_data = AutoVoucherEngine.create_from_transaction(data)
            voucher_id = AutoVoucherEngine.save_voucher(voucher_data, data['date'])
            
            self._save_transaction_record(data, voucher_id)
            self._update_balances(data)
            
            QMessageBox.information(
                self, "موفق",
                f"✅ تراکنش با موفقیت ثبت شد!\n\n"
                f"📋 شماره سند: {voucher_id}"
            )
            
            self._clear_form()
            self.load_data()
        
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def _save_transaction_record(self, data: dict, voucher_id: int):
        """ذخیره تراکنش در جدول finance_transactions"""
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute("SELECT MAX(id) FROM finance_transactions")
            max_id = c.fetchone()[0] or 0
            transaction_no = f"TRX{max_id + 1:06d}"
            
            gregorian_date = DateConverter.for_db(data['date'])
            
            c.execute('''
                INSERT INTO finance_transactions 
                (transaction_no, date, type,
                 from_account_type, from_account_id,
                 to_account_type, to_account_id,
                 party_id, amount, fee, discount,
                 description, reference_no, voucher_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                transaction_no,
                gregorian_date,
                data['type'],
                data['from_account'].get('type') if data['from_account'] else None,
                data['from_account'].get('id') if data['from_account'] else None,
                data['to_account'].get('type') if data['to_account'] else None,
                data['to_account'].get('id') if data['to_account'] else None,
                data.get('party_id'),
                data['amount'],
                data.get('fee', 0),
                data.get('discount', 0),
                data.get('description', ''),
                data.get('reference_no', ''),
                voucher_id
            ])
            
            conn.commit()
    
    def _update_balances(self, data: dict):
        """آپدیت مانده حساب‌ها"""
        amount = data['amount']
        fee = data.get('fee', 0)
        
        if data.get('from_account'):
            acc = data['from_account']
            FinanceHelper.update_balance(acc['type'], acc['id'], -(amount + fee))
        
        if data.get('to_account'):
            acc = data['to_account']
            FinanceHelper.update_balance(acc['type'], acc['id'], amount)
    
    # ============================================================
    # بارگذاری داده‌ها
    # ============================================================
    
    def load_data(self):
        """بارگذاری همه داده‌ها"""
        try:
            self._load_banks()
            self._load_cash_boxes()
            self._load_parties()
            self._load_checks()
            self._load_history()
            self._update_summary()
            self._populate_account_combos()
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری امور مالی: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_banks(self):
        """بارگذاری بانک‌ها"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, code, name, account_number, card_number, 
                       balance, is_active
                FROM banks
                ORDER BY name
            ''')
            self.bank_accounts = [dict(row) for row in c.fetchall()]
        
        self.banks_table.setRowCount(len(self.bank_accounts))
        
        for i, bank in enumerate(self.bank_accounts):
            self.banks_table.setItem(i, 0, QTableWidgetItem(bank['code']))
            self.banks_table.setItem(i, 1, QTableWidgetItem(bank['name']))
            self.banks_table.setItem(i, 2, QTableWidgetItem(bank.get('account_number') or '-'))
            self.banks_table.setItem(i, 3, QTableWidgetItem(bank.get('card_number') or '-'))
            
            balance_item = QTableWidgetItem(f"{bank['balance']:,.0f}")
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if bank['balance'] > 0:
                balance_item.setForeground(QColor('#27ae60'))
            elif bank['balance'] < 0:
                balance_item.setForeground(QColor('#e74c3c'))
            self.banks_table.setItem(i, 4, balance_item)
            
            status = "🟢 فعال" if bank['is_active'] else "🔴 غیرفعال"
            self.banks_table.setItem(i, 5, QTableWidgetItem(status))
    
    def _load_cash_boxes(self):
        """بارگذاری صندوق‌ها"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, code, name, location, balance, is_active
                FROM cash_boxes
                ORDER BY name
            ''')
            self.cash_boxes = [dict(row) for row in c.fetchall()]
        
        self.cash_table.setRowCount(len(self.cash_boxes))
        
        for i, cash in enumerate(self.cash_boxes):
            self.cash_table.setItem(i, 0, QTableWidgetItem(cash['code']))
            self.cash_table.setItem(i, 1, QTableWidgetItem(cash['name']))
            self.cash_table.setItem(i, 2, QTableWidgetItem(cash.get('location') or '-'))
            
            balance_item = QTableWidgetItem(f"{cash['balance']:,.0f}")
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if cash['balance'] > 0:
                balance_item.setForeground(QColor('#27ae60'))
            elif cash['balance'] < 0:
                balance_item.setForeground(QColor('#e74c3c'))
            self.cash_table.setItem(i, 3, balance_item)
            
            status = "🟢 فعال" if cash['is_active'] else "🔴 غیرفعال"
            self.cash_table.setItem(i, 4, QTableWidgetItem(status))
    
    def _load_parties(self):
        """بارگذاری طرف‌های حساب"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, code, name, type
                FROM parties
                ORDER BY name
            ''')
            self.parties = [dict(row) for row in c.fetchall()]
        
        current = self.party_combo.currentData()
        self.party_combo.clear()
        self.party_combo.addItem("-- بدون طرف حساب --", None)
        
        for party in self.parties:
            type_icon = "👤" if party['type'] == 'customer' else "🏢"
            self.party_combo.addItem(
                f"{type_icon} {party['name']}",
                party['id']
            )
        
        if current:
            idx = self.party_combo.findData(current)
            if idx >= 0:
                self.party_combo.setCurrentIndex(idx)
    
    def _populate_account_combos(self):
        """پر کردن combo حساب‌ها"""
        self.from_account_combo.clear()
        for bank in self.bank_accounts:
            if bank['is_active']:
                self.from_account_combo.addItem(
                    f"🏦 {bank['name']} ({bank['balance']:,.0f})",
                    {'type': 'bank', 'id': bank['id'], 'code': '1102', 'name': bank['name']}
                )
        for cash in self.cash_boxes:
            if cash['is_active']:
                self.from_account_combo.addItem(
                    f"💵 {cash['name']} ({cash['balance']:,.0f})",
                    {'type': 'cash', 'id': cash['id'], 'code': '1101', 'name': cash['name']}
                )
        
        self.to_account_combo.clear()
        for bank in self.bank_accounts:
            if bank['is_active']:
                self.to_account_combo.addItem(
                    f"🏦 {bank['name']} ({bank['balance']:,.0f})",
                    {'type': 'bank', 'id': bank['id'], 'code': '1102', 'name': bank['name']}
                )
        for cash in self.cash_boxes:
            if cash['is_active']:
                self.to_account_combo.addItem(
                    f"💵 {cash['name']} ({cash['balance']:,.0f})",
                    {'type': 'cash', 'id': cash['id'], 'code': '1101', 'name': cash['name']}
                )
    
    def _load_checks(self):
        """بارگذاری چک‌ها"""
        filter_idx = self.check_filter.currentIndex() if hasattr(self, 'check_filter') else 0
        
        query = '''
            SELECT 
                c.id, 
                c.check_number, 
                c.bank_name, 
                c.type, 
                c.amount,
                c.due_date, 
                c.status, 
                p.name as party_name
            FROM checks c
            LEFT JOIN parties p ON c.party_id = p.id
        '''
        
        today = get_today_jalali()
        today_g = DateConverter.for_db(today)
        
        if filter_idx == 1:
            query += " WHERE c.type = 'received'"
        elif filter_idx == 2:
            query += " WHERE c.type = 'paid'"
        elif filter_idx == 3:
            query += " WHERE c.status = 'pending'"
        elif filter_idx == 4:
            query += " WHERE c.status = 'collected'"
        elif filter_idx == 5:
            query += " WHERE c.status = 'bounced'"
        elif filter_idx == 6:
            query += " WHERE c.status = 'postponed'"
        elif filter_idx == 7:
            # ✅ معوق: سرسید امروز یا گذشته
            query += f" WHERE c.status IN ('pending', 'postponed') AND c.due_date <= '{today_g}'"
        
        query += " ORDER BY c.due_date ASC"
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute(query)
            checks = [dict(row) for row in c.fetchall()]
        
        self.checks_table.setRowCount(len(checks))
        
        type_map = {'received': '📥 دریافتی', 'paid': '📤 پرداختی'}
        status_map = {
            'pending': ('⏳ در جریان', '#f39c12'),
            'collected': ('✅ وصول شده', '#27ae60'),
            'bounced': ('❌ برگشتی', '#e74c3c'),
            'cancelled': ('🚫 ابطالی', '#95a5a6'),
            'postponed': ('⏸️ به تعویق', '#3498db'),
        }
        
        for i, check in enumerate(checks):
            self.checks_table.setItem(i, 0, QTableWidgetItem(check['check_number']))
            self.checks_table.setItem(i, 1, QTableWidgetItem(check.get('bank_name') or '-'))
            self.checks_table.setItem(i, 2, QTableWidgetItem(
                type_map.get(check['type'], check['type'])
            ))
            
            amount_item = QTableWidgetItem(f"{check['amount']:,.0f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.checks_table.setItem(i, 3, amount_item)
            
            # ✅ نمایش سرسید با رنگ
            due_date_str = safe_display_date(check['due_date']) if check['due_date'] else '-'
            due_item = QTableWidgetItem(due_date_str)
            
            if check['status'] in self.OPEN_CHECK_STATUSES and check['due_date']:
                days_diff = self._calculate_days_diff(check['due_date'])
                if days_diff >= 0:
                    due_item.setForeground(QColor('#e74c3c'))  # معوق یا امروز
                elif days_diff > -7:
                    due_item.setForeground(QColor('#f39c12'))  # نزدیک
            
            self.checks_table.setItem(i, 4, due_item)
            
            status_text, status_color = status_map.get(
                check['status'], 
                (check['status'], '#666')
            )
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            self.checks_table.setItem(i, 5, status_item)
            
            self.checks_table.setItem(i, 6, QTableWidgetItem(check.get('party_name') or '-'))
        
        self._check_due_dates_alert()
    
    def _check_due_dates_alert(self):
        """هشدار چک‌های نزدیک سرسید و معوق"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                from persiantools.jdatetime import JalaliDate
                today = JalaliDate.today()
                future = today + timedelta(days=7)
                
                today_str = today.strftime("%Y/%m/%d")
                future_str = future.strftime("%Y/%m/%d")
                
                # ✅ چک‌های نزدیک سرسید
                c.execute('''
                    SELECT COUNT(*) 
                    FROM checks 
                    WHERE status IN ('pending', 'postponed')
                    AND due_date > ?
                    AND due_date <= ?
                ''', [today_str, future_str])
                near_count = c.fetchone()[0] or 0
                
                # ✅ چک‌های معوق (سرسید امروز یا گذشته)
                c.execute('''
                    SELECT COUNT(*) 
                    FROM checks 
                    WHERE status IN ('pending', 'postponed')
                    AND due_date <= ?
                ''', [today_str])
                overdue_count = c.fetchone()[0] or 0
            
            messages = []
            if overdue_count > 0:
                messages.append(f"🔴 {overdue_count} چک معوق دارید!")
            if near_count > 0:
                messages.append(f"⚠️ {near_count} چک در ۷ روز آینده سرسید دارد!")
            
            if messages:
                self.check_alert.setText(" | ".join(messages))
                self.check_alert.setStyleSheet(
                    "padding: 8px; border-radius: 5px; "
                    "background: #fff3cd; color: #856404; "
                    "font-weight: bold; border: 1px solid #f39c12;"
                )
            else:
                self.check_alert.setText("✅ چک معوقی وجود ندارد")
                self.check_alert.setStyleSheet(
                    "padding: 8px; border-radius: 5px; "
                    "background: #e8f5e9; color: #2e7d32; "
                    "font-weight: bold;"
                )
        except Exception as e:
            print(f"⚠️ خطا در هشدار چک: {e}")
            self.check_alert.setText("")
    
    def _load_history(self):
        """بارگذاری تاریخچه"""
        try:
            from_date = self.history_from.get_shamsi()
            to_date = self.history_to.get_shamsi()
            
            from_g = DateConverter.for_db(from_date)
            to_g = DateConverter.for_db(to_date)
            
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute('''
                    SELECT 
                        t.id, 
                        t.transaction_no, 
                        t.date, 
                        t.type,
                        t.amount, 
                        t.fee, 
                        t.discount, 
                        t.description,
                        p.name as party_name,
                        COALESCE(
                            (SELECT name FROM banks 
                             WHERE id = t.from_account_id 
                             AND t.from_account_type = 'bank'),
                            (SELECT name FROM cash_boxes 
                             WHERE id = t.from_account_id 
                             AND t.from_account_type = 'cash'),
                            '-'
                        ) as from_name,
                        COALESCE(
                            (SELECT name FROM banks 
                             WHERE id = t.to_account_id 
                             AND t.to_account_type = 'bank'),
                            (SELECT name FROM cash_boxes 
                             WHERE id = t.to_account_id 
                             AND t.to_account_type = 'cash'),
                            '-'
                        ) as to_name
                    FROM finance_transactions t
                    LEFT JOIN parties p ON t.party_id = p.id
                    WHERE t.date >= ? AND t.date <= ?
                    ORDER BY t.id DESC
                ''', [from_g, to_g])
                
                transactions = [dict(row) for row in c.fetchall()]
            
            type_map = {
                'receipt': '📥 دریافت',
                'payment': '📤 پرداخت',
                'transfer': '🔄 انتقال',
                'income': '💰 درآمد',
                'expense': '💸 هزینه',
                'capital': '🏦 سرمایه',
                'bank_profit': '📈 سود بانکی',
                'bank_charge': '💳 کارمزد',
                'card_to_card': '💳 کارت به کارت',
            }
            
            self.history_table.setRowCount(len(transactions))
            total = 0
            
            for i, t in enumerate(transactions):
                self.history_table.setItem(i, 0, QTableWidgetItem(t['transaction_no']))
                self.history_table.setItem(i, 1, QTableWidgetItem(
                    safe_display_date(t['date']) if t['date'] else '-'
                ))
                self.history_table.setItem(i, 2, QTableWidgetItem(
                    type_map.get(t['type'], t['type'])
                ))
                self.history_table.setItem(i, 3, QTableWidgetItem(t.get('from_name') or '-'))
                self.history_table.setItem(i, 4, QTableWidgetItem(t.get('to_name') or '-'))
                self.history_table.setItem(i, 5, QTableWidgetItem(t.get('party_name') or '-'))
                
                amount_item = QTableWidgetItem(f"{t['amount']:,.0f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.history_table.setItem(i, 6, amount_item)
                
                self.history_table.setItem(i, 7, QTableWidgetItem(t.get('description') or ''))
                
                total += t['amount'] or 0
            
            self.history_total.setText(
                f"📊 {len(transactions)} تراکنش | مجموع: {total:,.0f} ریال"
            )
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری تاریخچه: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_summary(self):
        """آپدیت کارت‌های خلاصه"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute(
                    "SELECT COUNT(*), COALESCE(SUM(balance), 0) "
                    "FROM banks WHERE is_active = 1"
                )
                bank_row = c.fetchone()
                bank_count = bank_row[0]
                bank_total = bank_row[1]
                
                c.execute(
                    "SELECT COALESCE(SUM(balance), 0) "
                    "FROM cash_boxes WHERE is_active = 1"
                )
                cash_total = c.fetchone()[0]
                
                # ✅ چک‌های باز (pending + postponed)
                c.execute('''
                    SELECT COUNT(*) FROM checks 
                    WHERE status IN ('pending', 'postponed')
                ''')
                check_count = c.fetchone()[0] or 0
            
            self.card_banks.value_label.setText(
                f"{bank_count} حساب\n{bank_total:,.0f} ریال"
            )
            self.card_cash.value_label.setText(f"{cash_total:,.0f} ریال")
            self.card_checks.value_label.setText(f"{check_count} چک باز")
            self.card_total.value_label.setText(
                f"{bank_total + cash_total:,.0f} ریال"
            )
        except Exception as e:
            print(f"⚠️ خطا در آپدیت خلاصه: {e}")
    
    # ============================================================
    # عملیات بانک
    # ============================================================
    
    def _add_bank(self):
        dialog = BankDialog(parent=self)
        if dialog.exec_():
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ بانک اضافه شد!")
    
    def _edit_bank(self):
        row = self.banks_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک بانک انتخاب کنید!")
            return
        
        bank = self.bank_accounts[row]
        dialog = BankDialog(bank_id=bank['id'], parent=self)
        if dialog.exec_():
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ بانک ویرایش شد!")
    
    def _delete_bank(self):
        row = self.banks_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک بانک انتخاب کنید!")
            return
        
        bank = self.bank_accounts[row]
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف بانک '{bank['name']}' اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE banks SET is_active = 0 WHERE id = ?",
                    [bank['id']]
                )
                conn.commit()
            
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ بانک غیرفعال شد!")
    
    # ============================================================
    # عملیات صندوق
    # ============================================================
    
    def _add_cash(self):
        dialog = CashDialog(parent=self)
        if dialog.exec_():
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ صندوق اضافه شد!")
    
    def _edit_cash(self):
        row = self.cash_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک صندوق انتخاب کنید!")
            return
        
        cash = self.cash_boxes[row]
        dialog = CashDialog(cash_id=cash['id'], parent=self)
        if dialog.exec_():
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ صندوق ویرایش شد!")
    
    def _delete_cash(self):
        row = self.cash_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک صندوق انتخاب کنید!")
            return
        
        cash = self.cash_boxes[row]
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف صندوق '{cash['name']}' اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE cash_boxes SET is_active = 0 WHERE id = ?",
                    [cash['id']]
                )
                conn.commit()
            
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ صندوق غیرفعال شد!")
    
    # ============================================================
    # عملیات چک
    # ============================================================
    
    def _add_check(self):
        """افزودن چک جدید"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("➕ چک جدید")
        msg_box.setText("چه نوع چکی؟")
        msg_box.setIcon(QMessageBox.Question)
        
        btn_received = msg_box.addButton("📥 دریافتی", QMessageBox.AcceptRole)
        btn_paid = msg_box.addButton("📤 پرداختی", QMessageBox.AcceptRole)
        btn_cancel = msg_box.addButton("❌ انصراف", QMessageBox.RejectRole)
        
        msg_box.exec_()
        
        clicked = msg_box.clickedButton()
        
        if clicked == btn_cancel:
            return
        
        check_type = 'received' if clicked == btn_received else 'paid'
        
        try:
            from ui.finance.check_dialog import CheckDialog
            dialog = CheckDialog(check_type=check_type, parent=self)
            
            if dialog.exec_():
                self.load_data()
                QMessageBox.information(self, "موفق", "✅ چک ثبت شد!")
        except ImportError:
            QMessageBox.warning(self, "خطا", "دیالوگ چک پیدا نشد!")
    
    def _edit_check(self):
        """ویرایش چک"""
        row = self.checks_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک چک انتخاب کنید!")
            return
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, type FROM checks 
                WHERE check_number = ?
                ORDER BY id DESC LIMIT 1
            ''', [self.checks_table.item(row, 0).text()])
            
            check = c.fetchone()
        
        if not check:
            QMessageBox.warning(self, "خطا", "چک پیدا نشد!")
            return
        
        try:
            from ui.finance.check_dialog import CheckDialog
            dialog = CheckDialog(
                check_id=check['id'],
                check_type=check['type'],
                parent=self
            )
            
            if dialog.exec_():
                self.load_data()
                QMessageBox.information(self, "موفق", "✅ چک ویرایش شد!")
        except ImportError:
            QMessageBox.warning(self, "خطا", "دیالوگ چک پیدا نشد!")
    
    # ============================================================
    # گزارشات
    # ============================================================
    
    def _report_today(self):
        """گزارش تراکنش‌های امروز"""
        try:
            today = get_today_jalali()
            today_g = DateConverter.for_db(today)
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT 
                        t.transaction_no, 
                        t.type, 
                        t.amount, 
                        t.description
                    FROM finance_transactions t
                    WHERE t.date = ?
                    ORDER BY t.id DESC
                ''', [today_g])
                
                transactions = [dict(row) for row in c.fetchall()]
            
            if not transactions:
                QMessageBox.information(self, "گزارش امروز", "امروز تراکنشی ثبت نشده")
                return
            
            self._show_transactions_dialog(
                f"📊 تراکنش‌های امروز ({today})",
                transactions,
                ["شماره", "نوع", "مبلغ", "شرح"],
                f"transactions_today_{today.replace('/', '_')}"
            )
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _report_week(self):
        """گزارش تراکنش‌های هفته"""
        try:
            from persiantools.jdatetime import JalaliDate
            today = JalaliDate.today()
            week_ago = today - timedelta(days=7)
            
            from_date = week_ago.strftime("%Y/%m/%d")
            to_date = today.strftime("%Y/%m/%d")
            
            from_g = DateConverter.for_db(from_date)
            to_g = DateConverter.for_db(to_date)
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT 
                        t.transaction_no, 
                        t.date, 
                        t.type, 
                        t.amount, 
                        t.description
                    FROM finance_transactions t
                    WHERE t.date >= ? AND t.date <= ?
                    ORDER BY t.id DESC
                ''', [from_g, to_g])
                
                transactions = [dict(row) for row in c.fetchall()]
            
            if not transactions:
                QMessageBox.information(self, "گزارش هفته", "این هفته تراکنشی ثبت نشده")
                return
            
            self._show_transactions_dialog(
                f"📅 تراکنش‌های هفته ({from_date} تا {to_date})",
                transactions,
                ["شماره", "تاریخ", "نوع", "مبلغ", "شرح"],
                f"transactions_week_{from_date.replace('/', '_')}",
                include_date=True
            )
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _show_transactions_dialog(self, title, transactions, headers, filename, include_date=False):
        """نمایش دیالوگ تراکنش‌ها"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(self.sm.get_scaled(850), self.sm.get_scaled(550))
        
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setRowCount(len(transactions))
        table.setAlternatingRowColors(True)
        
        type_map = {
            'receipt': '📥 دریافت',
            'payment': '📤 پرداخت',
            'transfer': '🔄 انتقال',
            'income': '💰 درآمد',
            'expense': '💸 هزینه',
            'capital': '🏦 سرمایه',
            'bank_profit': '📈 سود بانکی',
            'bank_charge': '💳 کارمزد',
            'card_to_card': '💳 کارت به کارت',
        }
        
        total = 0
        
        for i, t in enumerate(transactions):
            col = 0
            
            table.setItem(i, col, QTableWidgetItem(t['transaction_no']))
            col += 1
            
            if include_date:
                table.setItem(i, col, QTableWidgetItem(
                    safe_display_date(t['date']) if t['date'] else '-'
                ))
                col += 1
            
            table.setItem(i, col, QTableWidgetItem(
                type_map.get(t['type'], t['type'])
            ))
            col += 1
            
            amount_item = QTableWidgetItem(f"{t['amount']:,.0f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(i, col, amount_item)
            total += t['amount'] or 0
            col += 1
            
            table.setItem(i, col, QTableWidgetItem(t.get('description') or ''))
        
        layout.addWidget(table)
        
        total_label = QLabel(
            f"📊 {len(transactions)} تراکنش | مجموع: {total:,.0f} ریال"
        )
        total_label.setStyleSheet(
            "padding: 12px; background: #e8f5e9; "
            "border-radius: 6px; font-weight: bold; "
            "font-size: 11pt; color: #2e7d32;"
        )
        total_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(total_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        export_btn = QPushButton("📎 خروجی Excel")
        export_btn.setStyleSheet(
            "background: #4CAF50; color: white; "
            "padding: 10px 20px; border-radius: 6px; font-weight: bold;"
        )
        export_btn.clicked.connect(
            lambda: self._export_table_csv(table, filename)
        )
        btn_layout.addWidget(export_btn)
        
        close_btn = QPushButton("❌ بستن")
        close_btn.setMinimumWidth(self.sm.get_scaled(100))
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.exec_()
    
    def _report_cash_flow(self):
        """گزارش جریان نقدی"""
        try:
            from persiantools.jdatetime import JalaliDate
            today = JalaliDate.today()
            start = today - timedelta(days=30)
            
            from_date = start.strftime("%Y/%m/%d")
            to_date = today.strftime("%Y/%m/%d")
            
            from_g = DateConverter.for_db(from_date)
            to_g = DateConverter.for_db(to_date)
            
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute('''
                    SELECT COALESCE(SUM(t.amount), 0)
                    FROM finance_transactions t
                    WHERE t.type IN ('receipt', 'income', 'capital', 'bank_profit')
                    AND t.date >= ? AND t.date <= ?
                ''', [from_g, to_g])
                total_in = c.fetchone()[0] or 0
                
                c.execute('''
                    SELECT COALESCE(SUM(t.amount), 0)
                    FROM finance_transactions t
                    WHERE t.type IN ('payment', 'expense', 'bank_charge')
                    AND t.date >= ? AND t.date <= ?
                ''', [from_g, to_g])
                total_out = c.fetchone()[0] or 0
                
                c.execute('''
                    SELECT t.type, COUNT(*) as cnt, COALESCE(SUM(t.amount), 0) as total
                    FROM finance_transactions t
                    WHERE t.date >= ? AND t.date <= ?
                    GROUP BY t.type
                ''', [from_g, to_g])
                breakdown = c.fetchall()
            
            net = total_in - total_out
            
            html = f"""
            <div style='font-family: Tahoma; direction: rtl; padding: 20px;'>
                <h2 style='color:#273c75; text-align:center;'>
                    💰 جریان نقدی
                </h2>
                <p style='text-align:center; color:#666;'>
                    {from_date} تا {to_date}
                </p>
                
                <table style='width:100%; margin-top:20px; border-collapse:collapse;'>
                    <tr style='background:#e8f5e9;'>
                        <td style='padding:15px; font-weight:bold; border:1px solid #ccc;'>📥 ورودی‌ها:</td>
                        <td style='padding:15px; text-align:left; color:#27ae60; 
                            font-size:16pt; border:1px solid #ccc;'>
                            {total_in:,.0f} ریال
                        </td>
                    </tr>
                    <tr style='background:#ffebee;'>
                        <td style='padding:15px; font-weight:bold; border:1px solid #ccc;'>📤 خروجی‌ها:</td>
                        <td style='padding:15px; text-align:left; color:#e74c3c; 
                            font-size:16pt; border:1px solid #ccc;'>
                            {total_out:,.0f} ریال
                        </td>
                    </tr>
                    <tr style='background:{"#e8f5e9" if net >= 0 else "#ffebee"};'>
                        <td style='padding:15px; font-weight:bold; font-size:14pt; border:1px solid #ccc;'>
                            {"✅ سود نقدی:" if net >= 0 else "❌ کسری نقدی:"}
                        </td>
                        <td style='padding:15px; text-align:left; 
                            color:{"#27ae60" if net >= 0 else "#e74c3c"}; 
                            font-size:18pt; font-weight:bold; border:1px solid #ccc;'>
                            {abs(net):,.0f} ریال
                        </td>
                    </tr>
                </table>
                
                <h3 style='margin-top:30px; color:#273c75;'>📊 تفکیک بر اساس نوع:</h3>
                <table style='width:100%; border-collapse:collapse;'>
                    <tr style='background:#273c75; color:white;'>
                        <th style='padding:10px; border:1px solid #ccc;'>نوع</th>
                        <th style='padding:10px; border:1px solid #ccc;'>تعداد</th>
                        <th style='padding:10px; border:1px solid #ccc;'>مبلغ</th>
                    </tr>
            """
            
            type_names = {
                'receipt': '📥 دریافت',
                'payment': '📤 پرداخت',
                'transfer': '🔄 انتقال',
                'income': '💰 درآمد',
                'expense': '💸 هزینه',
                'capital': '🏦 سرمایه',
                'bank_profit': '📈 سود بانکی',
                'bank_charge': '💳 کارمزد بانکی',
                'card_to_card': '💳 کارت به کارت',
            }
            
            for row in breakdown:
                type_name = type_names.get(row['type'], row['type'])
                html += f"""
                    <tr style='border-bottom:1px solid #eee;'>
                        <td style='padding:10px; border:1px solid #eee;'>{type_name}</td>
                        <td style='padding:10px; text-align:center; border:1px solid #eee;'>{row['cnt']}</td>
                        <td style='padding:10px; text-align:left; border:1px solid #eee;'>
                            {row['total']:,.0f} ریال
                        </td>
                    </tr>
                """
            
            html += "</table></div>"
            
            msg = QMessageBox(self)
            msg.setWindowTitle("💰 جریان نقدی")
            msg.setTextFormat(Qt.RichText)
            msg.setText(html)
            msg.exec_()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def _report_chart(self):
        """نمودار درآمد/هزینه ۶ ماه"""
        try:
            from persiantools.jdatetime import JalaliDate
            today = JalaliDate.today()
            
            months_data = []
            month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
            
            for i in range(5, -1, -1):
                month = today.month - i
                year = today.year
                if month <= 0:
                    month += 12
                    year -= 1
                
                month_start = f"{year:04d}/{month:02d}/01"
                if month == 12:
                    month_end = f"{year:04d}/12/29"
                else:
                    month_end = f"{year:04d}/{month+1:02d}/01"
                
                start_g = DateConverter.for_db(month_start)
                end_g = DateConverter.for_db(month_end)
                
                with get_db() as conn:
                    c = conn.cursor()
                    
                    c.execute('''
                        SELECT COALESCE(SUM(t.amount), 0)
                        FROM finance_transactions t
                        WHERE t.type IN ('income', 'bank_profit', 'receipt')
                        AND t.date >= ? AND t.date < ?
                    ''', [start_g, end_g])
                    income = c.fetchone()[0] or 0
                    
                    c.execute('''
                        SELECT COALESCE(SUM(t.amount), 0)
                        FROM finance_transactions t
                        WHERE t.type IN ('expense', 'payment', 'bank_charge')
                        AND t.date >= ? AND t.date < ?
                    ''', [start_g, end_g])
                    expense = c.fetchone()[0] or 0
                
                months_data.append({
                    'name': month_names[month - 1],
                    'income': income,
                    'expense': expense
                })
            
            html = """
            <div style='font-family: Tahoma; direction: rtl; padding: 20px;'>
                <h2 style='color:#273c75; text-align:center;'>
                    📈 نمودار درآمد/هزینه (۶ ماه اخیر)
                </h2>
                <table style='width:100%; border-collapse:collapse; margin-top:20px;'>
                    <tr style='background:#273c75; color:white;'>
                        <th style='padding:10px; border:1px solid #ccc;'>ماه</th>
                        <th style='padding:10px; border:1px solid #ccc;'>درآمد</th>
                        <th style='padding:10px; border:1px solid #ccc;'>هزینه</th>
                        <th style='padding:10px; border:1px solid #ccc;'>مانده</th>
                    </tr>
            """
            
            for m in months_data:
                net = m['income'] - m['expense']
                net_color = '#27ae60' if net >= 0 else '#e74c3c'
                
                html += f"""
                    <tr style='border-bottom:1px solid #eee;'>
                        <td style='padding:10px; font-weight:bold; border:1px solid #eee;'>{m['name']}</td>
                        <td style='padding:10px; text-align:left; color:#27ae60; border:1px solid #eee;'>
                            {m['income']:,.0f}
                        </td>
                        <td style='padding:10px; text-align:left; color:#e74c3c; border:1px solid #eee;'>
                            {m['expense']:,.0f}
                        </td>
                        <td style='padding:10px; text-align:left; color:{net_color}; 
                            font-weight:bold; border:1px solid #eee;'>
                            {net:,.0f}
                        </td>
                    </tr>
                """
            
            html += "</table></div>"
            
            msg = QMessageBox(self)
            msg.setWindowTitle("📈 نمودار درآمد/هزینه")
            msg.setTextFormat(Qt.RichText)
            msg.setText(html)
            msg.exec_()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def _report_open_checks(self):
        """گزارش همه چک‌های باز (pending + postponed) — حتی سرسید آینده"""
        try:
            today = get_today_jalali()
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT 
                        c.check_number, 
                        c.bank_name, 
                        c.type, 
                        c.amount, 
                        c.due_date, 
                        c.status, 
                        c.description,
                        p.name as party_name
                    FROM checks c
                    LEFT JOIN parties p ON c.party_id = p.id
                    WHERE c.status IN ('pending', 'postponed')
                    ORDER BY c.due_date ASC
                ''')
                
                checks = [dict(row) for row in c.fetchall()]
            
            if not checks:
                QMessageBox.information(
                    self, 
                    "چک‌های باز", 
                    "✅ هیچ چک بازی وجود ندارد!"
                )
                return
            
            # شمارش معوق و آینده
            overdue_count = 0
            upcoming_count = 0
            today_count = 0
            
            for chk in checks:
                days = self._calculate_days_diff(chk['due_date'])
                if days > 0:
                    overdue_count += 1
                elif days == 0:
                    today_count += 1
                else:
                    upcoming_count += 1
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"📋 همه چک‌های باز ({len(checks)} مورد)")
            dialog.resize(self.sm.get_scaled(950), self.sm.get_scaled(650))
            
            layout = QVBoxLayout(dialog)
            
            # هشدار
            warning_text = f"📋 {len(checks)} چک باز دارید\n"
            warning_text += f"🔴 {overdue_count} چک معوق"
            if today_count > 0:
                warning_text += f" | 🔥 {today_count} چک امروز"
            warning_text += f" | 🟢 {upcoming_count} چک در آینده"
            
            warning = QLabel(warning_text)
            warning.setStyleSheet(
                "padding: 12px; background: #e3f2fd; color: #1565c0; "
                "border-radius: 6px; font-weight: bold; font-size: 11pt; line-height: 1.8;"
            )
            warning.setAlignment(Qt.AlignCenter)
            layout.addWidget(warning)
            
            # جدول
            table = QTableWidget()
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels([
                "شماره چک", "بانک", "نوع", "مبلغ", "سرسید", "وضعیت زمانی", "طرف حساب"
            ])
            table.horizontalHeader().setStretchLastSection(True)
            table.setRowCount(len(checks))
            table.setAlternatingRowColors(True)
            
            type_map = {
                'received': '📥 دریافتی', 
                'paid': '📤 پرداختی'
            }
            
            total_received = 0
            total_paid = 0
            
            for i, check in enumerate(checks):
                table.setItem(i, 0, QTableWidgetItem(check['check_number']))
                table.setItem(i, 1, QTableWidgetItem(check.get('bank_name') or '-'))
                
                type_text = type_map.get(check['type'], check['type'])
                type_item = QTableWidgetItem(type_text)
                if check['type'] == 'received':
                    type_item.setForeground(QColor('#27ae60'))
                    total_received += check['amount']
                else:
                    type_item.setForeground(QColor('#e74c3c'))
                    total_paid += check['amount']
                table.setItem(i, 2, type_item)
                
                amount_item = QTableWidgetItem(f"{check['amount']:,.0f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(i, 3, amount_item)
                
                due_item = QTableWidgetItem(safe_display_date(check['due_date']))
                table.setItem(i, 4, due_item)
                
                # وضعیت زمانی
                days_late = self._calculate_days_diff(check['due_date'])
                if days_late > 0:
                    status_text = f"🔴 {days_late} روز تأخیر"
                    status_color = '#e74c3c'
                elif days_late == 0:
                    status_text = "🔥 امروز سرسید"
                    status_color = '#e74c3c'
                else:
                    status_text = f"⏰ {-days_late} روز مانده"
                    status_color = '#27ae60'
                
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QColor(status_color))
                status_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, 5, status_item)
                
                table.setItem(i, 6, QTableWidgetItem(check.get('party_name') or '-'))
            
            layout.addWidget(table)
            
            # خلاصه
            summary = QLabel(
                f"📥 چک‌های دریافتی باز: {total_received:,.0f} ریال\n"
                f"📤 چک‌های پرداختی باز: {total_paid:,.0f} ریال\n"
                f"📊 مجموع: {total_received + total_paid:,.0f} ریال"
            )
            summary.setStyleSheet(
                "padding: 12px; background: #e3f2fd; color: #1565c0; "
                "border-radius: 6px; font-weight: bold; "
                "border: 1px solid #2196f3; line-height: 1.8;"
            )
            summary.setAlignment(Qt.AlignCenter)
            layout.addWidget(summary)
            
            # دکمه‌ها
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            export_btn = QPushButton("📎 خروجی Excel")
            export_btn.setStyleSheet(
                "background: #4CAF50; color: white; "
                "padding: 10px 20px; border-radius: 6px; font-weight: bold;"
            )
            export_btn.clicked.connect(lambda: self._export_table_csv(
                table, f"open_checks_{today.replace('/', '_')}"
            ))
            btn_layout.addWidget(export_btn)
            
            close_btn = QPushButton("❌ بستن")
            close_btn.setMinimumWidth(self.sm.get_scaled(100))
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _report_overdue_checks(self):
        """گزارش چک‌های معوق (سرسید امروز یا گذشته)"""
        try:
            today = get_today_jalali()
            today_g = DateConverter.for_db(today)
            
            with get_db() as conn:
                c = conn.cursor()
                # ✅ شامل pending و postponed + سرسید امروز یا گذشته
                c.execute('''
                    SELECT 
                        c.check_number, 
                        c.bank_name, 
                        c.type, 
                        c.amount, 
                        c.due_date, 
                        c.status, 
                        c.description,
                        p.name as party_name
                    FROM checks c
                    LEFT JOIN parties p ON c.party_id = p.id
                    WHERE c.status IN ('pending', 'postponed')
                    AND c.due_date <= ?
                    ORDER BY c.due_date ASC
                ''', [today_g])
                
                checks = [dict(row) for row in c.fetchall()]
            
            if not checks:
                QMessageBox.information(
                    self, 
                    "چک‌های معوق", 
                    "✅ چک معوقی وجود ندارد!\n\n"
                    "📋 فقط چک‌های با وضعیت:\n"
                    "• ⏳ در جریان\n"
                    "• ⏸️ به تعویق افتاده\n\n"
                    "...و سرسید امروز یا گذشته، معوق حساب می‌شوند."
                )
                return
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"⏳ چک‌های معوق ({len(checks)} مورد)")
            dialog.resize(self.sm.get_scaled(900), self.sm.get_scaled(600))
            
            layout = QVBoxLayout(dialog)
            
            # هشدار
            warning = QLabel(
                f"⚠️ {len(checks)} چک با سرسید امروز یا گذشته دارید!"
            )
            warning.setStyleSheet(
                "padding: 12px; background: #ffebee; color: #c62828; "
                "border-radius: 6px; font-weight: bold; font-size: 12pt;"
            )
            warning.setAlignment(Qt.AlignCenter)
            layout.addWidget(warning)
            
            # جدول
            table = QTableWidget()
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels([
                "شماره چک", "بانک", "نوع", "مبلغ", "سرسید", "روز تأخیر", "طرف حساب"
            ])
            table.horizontalHeader().setStretchLastSection(True)
            table.setRowCount(len(checks))
            table.setAlternatingRowColors(True)
            
            type_map = {
                'received': '📥 دریافتی', 
                'paid': '📤 پرداختی'
            }
            
            total_received = 0
            total_paid = 0
            
            for i, check in enumerate(checks):
                table.setItem(i, 0, QTableWidgetItem(check['check_number']))
                table.setItem(i, 1, QTableWidgetItem(check.get('bank_name') or '-'))
                
                type_text = type_map.get(check['type'], check['type'])
                type_item = QTableWidgetItem(type_text)
                if check['type'] == 'received':
                    type_item.setForeground(QColor('#27ae60'))
                    total_received += check['amount']
                else:
                    type_item.setForeground(QColor('#e74c3c'))
                    total_paid += check['amount']
                table.setItem(i, 2, type_item)
                
                amount_item = QTableWidgetItem(f"{check['amount']:,.0f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                amount_item.setForeground(QColor('#e74c3c'))
                table.setItem(i, 3, amount_item)
                
                due_item = QTableWidgetItem(safe_display_date(check['due_date']))
                due_item.setForeground(QColor('#e74c3c'))
                table.setItem(i, 4, due_item)
                
                # روز تأخیر
                days_late = self._calculate_days_diff(check['due_date'])
                if days_late > 0:
                    delay_text = f"🔴 {days_late} روز"
                    delay_color = '#e74c3c'
                else:
                    delay_text = "🔥 امروز"
                    delay_color = '#e74c3c'
                
                delay_item = QTableWidgetItem(delay_text)
                delay_item.setForeground(QColor(delay_color))
                delay_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, 5, delay_item)
                
                table.setItem(i, 6, QTableWidgetItem(check.get('party_name') or '-'))
            
            layout.addWidget(table)
            
            # خلاصه
            summary = QLabel(
                f"📥 چک‌های دریافتی معوق: {total_received:,.0f} ریال\n"
                f"📤 چک‌های پرداختی معوق: {total_paid:,.0f} ریال\n"
                f"📊 مجموع: {total_received + total_paid:,.0f} ریال"
            )
            summary.setStyleSheet(
                "padding: 12px; background: #fff3cd; color: #856404; "
                "border-radius: 6px; font-weight: bold; "
                "border: 1px solid #f39c12; line-height: 1.8;"
            )
            summary.setAlignment(Qt.AlignCenter)
            layout.addWidget(summary)
            
            # دکمه‌ها
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            export_btn = QPushButton("📎 خروجی Excel")
            export_btn.setStyleSheet(
                "background: #4CAF50; color: white; "
                "padding: 10px 20px; border-radius: 6px; font-weight: bold;"
            )
            export_btn.clicked.connect(lambda: self._export_table_csv(
                table, f"overdue_checks_{today.replace('/', '_')}"
            ))
            btn_layout.addWidget(export_btn)
            
            close_btn = QPushButton("❌ بستن")
            close_btn.setMinimumWidth(self.sm.get_scaled(100))
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _report_accounts_summary(self):
        """خلاصه حساب‌ها"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute('''
                    SELECT b.code, b.name, b.balance, b.is_active
                    FROM banks b
                    ORDER BY b.balance DESC
                ''')
                banks = [dict(row) for row in c.fetchall()]
                
                c.execute('''
                    SELECT cb.code, cb.name, cb.balance, cb.is_active
                    FROM cash_boxes cb
                    ORDER BY cb.balance DESC
                ''')
                cash_boxes = [dict(row) for row in c.fetchall()]
            
            total_banks = sum(b['balance'] for b in banks)
            total_cash = sum(cb['balance'] for cb in cash_boxes)
            
            dialog = QDialog(self)
            dialog.setWindowTitle("💼 خلاصه حساب‌ها")
            dialog.resize(self.sm.get_scaled(700), self.sm.get_scaled(650))
            
            layout = QVBoxLayout(dialog)
            
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            
            content = QWidget()
            content_layout = QVBoxLayout(content)
            
            # بانک‌ها
            bank_group = QGroupBox(f"🏦 بانک‌ها ({len(banks)} حساب)")
            bank_layout = QVBoxLayout(bank_group)
            
            bank_table = QTableWidget()
            bank_table.setColumnCount(3)
            bank_table.setHorizontalHeaderLabels(["کد", "نام", "مانده"])
            bank_table.horizontalHeader().setStretchLastSection(True)
            bank_table.setRowCount(len(banks))
            
            for i, b in enumerate(banks):
                bank_table.setItem(i, 0, QTableWidgetItem(b['code']))
                bank_table.setItem(i, 1, QTableWidgetItem(b['name']))
                
                amount_item = QTableWidgetItem(f"{b['balance']:,.0f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if b['balance'] >= 0:
                    amount_item.setForeground(QColor('#27ae60'))
                else:
                    amount_item.setForeground(QColor('#e74c3c'))
                bank_table.setItem(i, 2, amount_item)
            
            bank_layout.addWidget(bank_table)
            
            bank_total = QLabel(f"📊 مجموع بانک‌ها: {total_banks:,.0f} ریال")
            bank_total.setStyleSheet("font-weight: bold; padding: 8px;")
            bank_layout.addWidget(bank_total)
            
            content_layout.addWidget(bank_group)
            
            # صندوق‌ها
            cash_group = QGroupBox(f"💵 صندوق‌ها ({len(cash_boxes)} صندوق)")
            cash_layout = QVBoxLayout(cash_group)
            
            cash_table = QTableWidget()
            cash_table.setColumnCount(3)
            cash_table.setHorizontalHeaderLabels(["کد", "نام", "مانده"])
            cash_table.horizontalHeader().setStretchLastSection(True)
            cash_table.setRowCount(len(cash_boxes))
            
            for i, cb in enumerate(cash_boxes):
                cash_table.setItem(i, 0, QTableWidgetItem(cb['code']))
                cash_table.setItem(i, 1, QTableWidgetItem(cb['name']))
                
                amount_item = QTableWidgetItem(f"{cb['balance']:,.0f}")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if cb['balance'] >= 0:
                    amount_item.setForeground(QColor('#27ae60'))
                else:
                    amount_item.setForeground(QColor('#e74c3c'))
                cash_table.setItem(i, 2, amount_item)
            
            cash_layout.addWidget(cash_table)
            
            cash_total = QLabel(f"📊 مجموع صندوق‌ها: {total_cash:,.0f} ریال")
            cash_total.setStyleSheet("font-weight: bold; padding: 8px;")
            cash_layout.addWidget(cash_total)
            
            content_layout.addWidget(cash_group)
            
            # مجموع کل
            grand_total = QLabel(f"💰 مجموع کل: {total_banks + total_cash:,.0f} ریال")
            grand_total.setStyleSheet(
                "font-weight: bold; padding: 15px; "
                "background: #273c75; color: white; "
                "border-radius: 8px; font-size: 14pt;"
            )
            grand_total.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(grand_total)
            
            content_layout.addStretch()
            
            scroll.setWidget(content)
            layout.addWidget(scroll)
            
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            close_btn = QPushButton("❌ بستن")
            close_btn.setMinimumWidth(self.sm.get_scaled(120))
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def _report_overall_summary(self):
        """خلاصه وضعیت کلی مالی"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                # بانک‌ها
                c.execute("SELECT COUNT(*), COALESCE(SUM(balance), 0) FROM banks WHERE is_active = 1")
                row = c.fetchone()
                bank_count, bank_total = row[0], row[1]
                
                # صندوق‌ها
                c.execute("SELECT COUNT(*), COALESCE(SUM(balance), 0) FROM cash_boxes WHERE is_active = 1")
                row = c.fetchone()
                cash_count, cash_total = row[0], row[1]
                
                # چک‌های باز
                today = get_today_jalali()
                today_g = DateConverter.for_db(today)
                
                c.execute('''
                    SELECT COUNT(*), COALESCE(SUM(amount), 0)
                    FROM checks 
                    WHERE status IN ('pending', 'postponed')
                    AND due_date <= ?
                ''', [today_g])
                overdue_row = c.fetchone()
                overdue_count, overdue_total = overdue_row[0], overdue_row[1]
                
                c.execute('''
                    SELECT COUNT(*), COALESCE(SUM(amount), 0)
                    FROM checks 
                    WHERE status IN ('pending', 'postponed')
                ''')
                open_row = c.fetchone()
                open_count, open_total = open_row[0], open_row[1]
                
                # تراکنش‌های امروز
                c.execute('''
                    SELECT COUNT(*), COALESCE(SUM(amount), 0)
                    FROM finance_transactions
                    WHERE date = ?
                ''', [today_g])
                today_row = c.fetchone()
                today_tx_count, today_tx_total = today_row[0], today_row[1]
            
            html = f"""
            <div style='font-family: Tahoma; direction: rtl; padding: 20px;'>
                <h2 style='color:#8e44ad; text-align:center;'>
                    📊 خلاصه وضعیت مالی
                </h2>
                <p style='text-align:center; color:#666;'>{today}</p>
                
                <h3 style='color:#2980b9; margin-top:20px;'>💼 حساب‌ها:</h3>
                <table style='width:100%; border-collapse:collapse;'>
                    <tr style='background:#e3f2fd;'>
                        <td style='padding:12px; border:1px solid #ddd;'>
                            🏦 بانک‌ها ({bank_count} حساب)
                        </td>
                        <td style='padding:12px; text-align:left; 
                            border:1px solid #ddd; color:#2980b9; 
                            font-weight:bold; font-size:13pt;'>
                            {bank_total:,.0f} ریال
                        </td>
                    </tr>
                    <tr style='background:#e8f5e9;'>
                        <td style='padding:12px; border:1px solid #ddd;'>
                            💵 صندوق‌ها ({cash_count} صندوق)
                        </td>
                        <td style='padding:12px; text-align:left; 
                            border:1px solid #ddd; color:#27ae60; 
                            font-weight:bold; font-size:13pt;'>
                            {cash_total:,.0f} ریال
                        </td>
                    </tr>
                    <tr style='background:#fff3cd;'>
                        <td style='padding:12px; border:1px solid #ddd; 
                            font-weight:bold;'>
                            💰 مجموع نقدینگی
                        </td>
                        <td style='padding:12px; text-align:left; 
                            border:1px solid #ddd; color:#e94560; 
                            font-weight:bold; font-size:14pt;'>
                            {bank_total + cash_total:,.0f} ریال
                        </td>
                    </tr>
                </table>
                
                <h3 style='color:#f39c12; margin-top:25px;'>📄 چک‌ها:</h3>
                <table style='width:100%; border-collapse:collapse;'>
                    <tr style='background:#f0f0f0;'>
                        <td style='padding:12px; border:1px solid #ddd;'>
                            📋 چک‌های باز
                        </td>
                        <td style='padding:12px; text-align:left; 
                            border:1px solid #ddd;'>
                            <b>{open_count} چک</b> — {open_total:,.0f} ریال
                        </td>
                    </tr>
                    <tr style='background:#ffebee;'>
                        <td style='padding:12px; border:1px solid #ddd; 
                            color:#e74c3c; font-weight:bold;'>
                            ⏳ چک‌های معوق
                        </td>
                        <td style='padding:12px; text-align:left; 
                            border:1px solid #ddd; color:#e74c3c; 
                            font-weight:bold;'>
                            <b>{overdue_count} چک</b> — {overdue_total:,.0f} ریال
                        </td>
                    </tr>
                </table>
                
                <h3 style='color:#16a085; margin-top:25px;'>📊 فعالیت امروز:</h3>
                <table style='width:100%; border-collapse:collapse;'>
                    <tr style='background:#e8f5e9;'>
                        <td style='padding:12px; border:1px solid #ddd;'>
                            💳 تراکنش‌های امروز
                        </td>
                        <td style='padding:12px; text-align:left; 
                            border:1px solid #ddd;'>
                            <b>{today_tx_count} تراکنش</b> — {today_tx_total:,.0f} ریال
                        </td>
                    </tr>
                </table>
            </div>
            """
            
            msg = QMessageBox(self)
            msg.setWindowTitle("📊 خلاصه وضعیت مالی")
            msg.setTextFormat(Qt.RichText)
            msg.setText(html)
            msg.exec_()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _export_table_csv(self, table: QTableWidget, filename: str):
        """خروجی CSV از جدول"""
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "ذخیره خروجی",
                f"{filename}.csv",
                "CSV Files (*.csv)"
            )
            
            if not file_name:
                return
            
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                
                headers = []
                for col in range(table.columnCount()):
                    header = table.horizontalHeaderItem(col)
                    headers.append(header.text() if header else "")
                writer.writerow(headers)
                
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "موفق", f"✅ ذخیره شد:\n{file_name}")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def _export_full_report_csv(self):
        """خروجی کامل همه تراکنش‌ها"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT 
                        t.transaction_no, 
                        t.date, 
                        t.type, 
                        t.amount,
                        t.fee, 
                        t.discount, 
                        t.description,
                        p.name as party_name
                    FROM finance_transactions t
                    LEFT JOIN parties p ON t.party_id = p.id
                    ORDER BY t.id DESC
                ''')
                transactions = [dict(row) for row in c.fetchall()]
            
            if not transactions:
                QMessageBox.information(self, "خروجی", "هیچ تراکنشی وجود ندارد")
                return
            
            file_name, _ = QFileDialog.getSaveFileName(
                self, "ذخیره گزارش کامل",
                f"finance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)"
            )
            
            if not file_name:
                return
            
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "شماره تراکنش", "تاریخ", "نوع", "مبلغ", 
                    "کارمزد", "تخفیف", "شرح", "طرف حساب"
                ])
                
                type_map = {
                    'receipt': 'دریافت',
                    'payment': 'پرداخت',
                    'transfer': 'انتقال',
                    'income': 'درآمد',
                    'expense': 'هزینه',
                    'capital': 'سرمایه',
                    'bank_profit': 'سود بانکی',
                    'bank_charge': 'کارمزد بانکی',
                    'card_to_card': 'کارت به کارت',
                }
                
                for t in transactions:
                    writer.writerow([
                        t['transaction_no'],
                        safe_display_date(t['date']) if t['date'] else '-',
                        type_map.get(t['type'], t['type']),
                        t['amount'],
                        t.get('fee', 0),
                        t.get('discount', 0),
                        t.get('description', ''),
                        t.get('party_name') or '-'
                    ])
            
            QMessageBox.information(
                self, "موفق",
                f"✅ گزارش کامل ذخیره شد:\n{file_name}\n\n"
                f"📊 {len(transactions)} تراکنش"
            )
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def _export_history(self):
        """خروجی تاریخچه"""
        try:
            if not hasattr(self, 'history_table'):
                return
            
            today = get_today_jalali().replace('/', '_')
            self._export_table_csv(self.history_table, f"history_{today}")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    # ============================================================
    # AI
    # ============================================================
    
    def _ai_cash_flow(self):
        """تحلیل جریان نقدی با AI"""
        try:
            from persiantools.jdatetime import JalaliDate
            today = JalaliDate.today()
            month_start = today.replace(day=1)
            
            month_start_str = month_start.strftime("%Y/%m/%d")
            today_str = today.strftime("%Y/%m/%d")
            
            start_g = DateConverter.for_db(month_start_str)
            end_g = DateConverter.for_db(today_str)
            
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute('''
                    SELECT 
                        COALESCE(SUM(CASE WHEN t.type IN ('receipt', 'income', 'capital', 'bank_profit') 
                                     THEN t.amount ELSE 0 END), 0) as total_in,
                        COALESCE(SUM(CASE WHEN t.type IN ('payment', 'expense', 'bank_charge') 
                                     THEN t.amount ELSE 0 END), 0) as total_out,
                        COUNT(*) as cnt
                    FROM finance_transactions t
                    WHERE t.date >= ? AND t.date <= ?
                ''', [start_g, end_g])
                
                row = c.fetchone()
                total_in = row['total_in']
                total_out = row['total_out']
                count = row['cnt']
            
            net = total_in - total_out
            
            self.ai_result.setHtml(f"""
            <div style='font-family: Tahoma; direction: rtl;'>
                <h3 style='color:#3498db;'>📊 تحلیل جریان نقدی (این ماه)</h3>
                
                <table style='width:100%; border-collapse:collapse; margin:15px 0;'>
                    <tr style='background:#e8f5e9;'>
                        <td style='padding:12px; font-weight:bold; border:1px solid #ccc;'>📥 ورودی‌ها:</td>
                        <td style='padding:12px; text-align:left; color:#27ae60; 
                            font-size:14pt; border:1px solid #ccc;'>
                            {total_in:,.0f} ریال
                        </td>
                    </tr>
                    <tr style='background:#ffebee;'>
                        <td style='padding:12px; font-weight:bold; border:1px solid #ccc;'>📤 خروجی‌ها:</td>
                        <td style='padding:12px; text-align:left; color:#e74c3c; 
                            font-size:14pt; border:1px solid #ccc;'>
                            {total_out:,.0f} ریال
                        </td>
                    </tr>
                    <tr style='background:{"#e8f5e9" if net >= 0 else "#ffebee"};'>
                        <td style='padding:12px; font-weight:bold; border:1px solid #ccc;'>
                            {"✅ سود نقدی:" if net >= 0 else "❌ کسری نقدی:"}
                        </td>
                        <td style='padding:12px; text-align:left; 
                            color:{"#27ae60" if net >= 0 else "#e74c3c"}; 
                            font-size:16pt; font-weight:bold; border:1px solid #ccc;'>
                            {abs(net):,.0f} ریال
                        </td>
                    </tr>
                </table>
                
                <div style='background:#f8f9fa; padding:15px; border-radius:8px; margin-top:20px;'>
                    <h4>💡 تحلیل:</h4>
                    <p>📊 تعداد تراکنش‌ها: {count}</p>
                    <p>📈 میانگین ورودی: {total_in / count if count > 0 else 0:,.0f} ریال</p>
                    <p>📉 میانگین خروجی: {total_out / count if count > 0 else 0:,.0f} ریال</p>
                    <p style='color:{"#27ae60" if net >= 0 else "#e74c3c"}; 
                       font-weight:bold; margin-top:10px;'>
                        {self._get_cash_flow_message(net, total_in, total_out)}
                    </p>
                </div>
                
                <p style='color:#888; font-size:9pt; margin-top:15px; text-align:center;'>
                    🤖 تحلیل ساده — اتصال به ImanAI به زودی
                </p>
            </div>
            """)
        except Exception as e:
            self.ai_result.setHtml(f"<p style='color:#e74c3c;'>❌ خطا: {str(e)}</p>")
    
    def _get_cash_flow_message(self, net, total_in, total_out):
        """پیام تحلیل جریان نقدی"""
        if total_in == 0 and total_out == 0:
            return "هیچ تراکنشی ثبت نشده است."
        
        ratio = net / total_in if total_in > 0 else 0
        
        if ratio > 0.3:
            return "✅ وضعیت نقدینگی عالی! سود خوبی دارید."
        elif ratio > 0:
            return "🟢 وضعیت نقدینگی مثبت. ادامه بدید."
        elif ratio > -0.2:
            return "🟡 کسری نقدی کوچک. دقت کنید."
        else:
            return "🔴 هشدار! کسری نقدی بزرگ."
    
    def _ai_predict_crisis(self):
        """پیش‌بینی بحران نقدینگی"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute("SELECT COALESCE(SUM(balance), 0) FROM banks WHERE is_active = 1")
                bank_total = c.fetchone()[0] or 0
                
                c.execute("SELECT COALESCE(SUM(balance), 0) FROM cash_boxes WHERE is_active = 1")
                cash_total = c.fetchone()[0] or 0
                
                current_balance = bank_total + cash_total
                
                from persiantools.jdatetime import JalaliDate
                today = JalaliDate.today()
                future = today + timedelta(days=30)
                
                today_str = today.strftime("%Y/%m/%d")
                future_str = future.strftime("%Y/%m/%d")
                
                c.execute('''
                    SELECT COALESCE(SUM(amount), 0)
                    FROM checks
                    WHERE type = 'paid' 
                    AND status IN ('pending', 'postponed')
                    AND due_date >= ? AND due_date <= ?
                ''', [today_str, future_str])
                upcoming_checks = c.fetchone()[0] or 0
            
            balance_after = current_balance - upcoming_checks
            
            self.ai_result.setHtml(f"""
            <div style='font-family: Tahoma; direction: rtl;'>
                <h3 style='color:#e74c3c;'>🔮 پیش‌بینی بحران نقدینگی</h3>
                
                <table style='width:100%; border-collapse:collapse; margin:15px 0;'>
                    <tr style='background:#e8f5e9;'>
                        <td style='padding:12px; font-weight:bold; border:1px solid #ccc;'>
                            💰 مانده فعلی:
                        </td>
                        <td style='padding:12px; text-align:left; color:#27ae60; 
                            font-size:14pt; border:1px solid #ccc;'>
                            {current_balance:,.0f} ریال
                        </td>
                    </tr>
                    <tr style='background:#ffebee;'>
                        <td style='padding:12px; font-weight:bold; border:1px solid #ccc;'>
                            📤 چک‌های پرداختی ۳۰ روز آینده:
                        </td>
                        <td style='padding:12px; text-align:left; color:#e74c3c; 
                            font-size:14pt; border:1px solid #ccc;'>
                            {upcoming_checks:,.0f} ریال
                        </td>
                    </tr>
                    <tr style='background:{"#e8f5e9" if balance_after >= 0 else "#ffebee"};'>
                        <td style='padding:12px; font-weight:bold; border:1px solid #ccc;'>
                            {"✅ مانده بعد از پرداخت:" if balance_after >= 0 else "❌ کسری پیش‌بینی شده:"}
                        </td>
                        <td style='padding:12px; text-align:left; 
                            color:{"#27ae60" if balance_after >= 0 else "#e74c3c"}; 
                            font-size:16pt; font-weight:bold; border:1px solid #ccc;'>
                            {abs(balance_after):,.0f} ریال
                        </td>
                    </tr>
                </table>
                
                <div style='background:#f8f9fa; padding:15px; border-radius:8px; margin-top:20px;'>
                    <h4>💡 نتیجه‌گیری:</h4>
                    <p style='color:{"#27ae60" if balance_after >= 0 else "#e74c3c"}; 
                       font-weight:bold; font-size:12pt;'>
                        {self._get_crisis_message(balance_after, upcoming_checks)}
                    </p>
                </div>
                
                <p style='color:#888; font-size:9pt; margin-top:15px; text-align:center;'>
                    🤖 پیش‌بینی ساده — AI واقعی به زودی
                </p>
            </div>
            """)
        except Exception as e:
            self.ai_result.setHtml(f"<p style='color:#e74c3c;'>❌ خطا: {str(e)}</p>")
    
    def _get_crisis_message(self, balance_after, upcoming_checks):
        """پیام پیش‌بینی بحران"""
        if upcoming_checks == 0:
            return "✅ هیچ چک پرداختی در ۳۰ روز آینده ندارید."
        
        if balance_after > 0:
            return "✅ مانده نقدی شما برای پرداخت همه چک‌ها کافی است."
        else:
            return f"🔴 هشدار! برای پرداخت چک‌ها {abs(balance_after):,.0f} ریال کم دارید."
    
    def _ai_detect_fraud(self):
        """تشخیص تراکنش مشکوک"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute('''
                    SELECT AVG(t.amount) FROM finance_transactions t
                    WHERE t.date >= date('now', '-90 days')
                ''')
                avg_amount = c.fetchone()[0] or 0
                
                threshold = avg_amount * 3
                
                c.execute('''
                    SELECT 
                        t.transaction_no, 
                        t.date, 
                        t.type, 
                        t.amount, 
                        t.description
                    FROM finance_transactions t
                    WHERE t.amount > ?
                    AND t.date >= date('now', '-30 days')
                    ORDER BY t.amount DESC
                    LIMIT 20
                ''', [threshold])
                
                suspicious = [dict(row) for row in c.fetchall()]
            
            if not suspicious:
                self.ai_result.setHtml(f"""
                <div style='font-family: Tahoma; direction: rtl;'>
                    <h3 style='color:#f39c12;'>🔍 تشخیص تراکنش مشکوک</h3>
                    <p style='padding:20px; text-align:center; color:#27ae60; font-size:14pt;'>
                        ✅ هیچ تراکنش مشکوکی یافت نشد
                    </p>
                    <p style='color:#888; text-align:center;'>
                        میانگین تراکنش‌ها: {avg_amount:,.0f} ریال
                    </p>
                </div>
                """)
                return
            
            html = f"""
            <div style='font-family: Tahoma; direction: rtl;'>
                <h3 style='color:#f39c12;'>🔍 تراکنش‌های مشکوک</h3>
                <p style='color:#666;'>آستانه: {threshold:,.0f} ریال (۳ برابر میانگین)</p>
                
                <table style='width:100%; border-collapse:collapse; margin-top:15px;'>
                    <tr style='background:#273c75; color:white;'>
                        <th style='padding:8px; border:1px solid #ccc;'>شماره</th>
                        <th style='padding:8px; border:1px solid #ccc;'>تاریخ</th>
                        <th style='padding:8px; border:1px solid #ccc;'>نوع</th>
                        <th style='padding:8px; border:1px solid #ccc;'>مبلغ</th>
                    </tr>
            """
            
            type_map = {
                'receipt': '📥 دریافت',
                'payment': '📤 پرداخت',
                'transfer': '🔄 انتقال',
                'income': '💰 درآمد',
                'expense': '💸 هزینه',
            }
            
            for s in suspicious:
                html += f"""
                    <tr style='border-bottom:1px solid #eee; background:#fff3cd;'>
                        <td style='padding:8px; border:1px solid #eee;'>{s['transaction_no']}</td>
                        <td style='padding:8px; border:1px solid #eee;'>
                            {safe_display_date(s['date'])}
                        </td>
                        <td style='padding:8px; border:1px solid #eee;'>
                            {type_map.get(s['type'], s['type'])}
                        </td>
                        <td style='padding:8px; text-align:left; color:#e74c3c; 
                            font-weight:bold; border:1px solid #eee;'>
                            {s['amount']:,.0f}
                        </td>
                    </tr>
                """
            
            html += """
                </table>
                <p style='color:#888; margin-top:15px; text-align:center;'>
                    🤖 تشخیص ساده بر اساس مبلغ — AI واقعی به زودی
                </p>
            </div>
            """
            
            self.ai_result.setHtml(html)
        except Exception as e:
            self.ai_result.setHtml(f"<p style='color:#e74c3c;'>❌ خطا: {str(e)}</p>")
    
    def _ai_suggest_priority(self):
        """پیشنهاد اولویت پرداخت"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute('''
                    SELECT 
                        c.check_number, 
                        c.bank_name, 
                        c.amount, 
                        c.due_date,
                        p.name as party_name
                    FROM checks c
                    LEFT JOIN parties p ON c.party_id = p.id
                    WHERE c.type = 'paid' 
                    AND c.status IN ('pending', 'postponed')
                    ORDER BY c.due_date ASC
                    LIMIT 10
                ''')
                
                checks = [dict(row) for row in c.fetchall()]
            
            if not checks:
                self.ai_result.setHtml("""
                <div style='font-family: Tahoma; direction: rtl;'>
                    <h3 style='color:#27ae60;'>💡 پیشنهاد اولویت پرداخت</h3>
                    <p style='padding:20px; text-align:center; color:#27ae60; font-size:14pt;'>
                        ✅ هیچ چک پرداختی ندارید
                    </p>
                </div>
                """)
                return
            
            html = """
            <div style='font-family: Tahoma; direction: rtl;'>
                <h3 style='color:#27ae60;'>💡 اولویت پرداخت چک‌ها</h3>
                <p style='color:#666;'>بر اساس نزدیک‌ترین سرسید</p>
                
                <table style='width:100%; border-collapse:collapse; margin-top:15px;'>
                    <tr style='background:#273c75; color:white;'>
                        <th style='padding:8px; border:1px solid #ccc;'>اولویت</th>
                        <th style='padding:8px; border:1px solid #ccc;'>شماره چک</th>
                        <th style='padding:8px; border:1px solid #ccc;'>طرف حساب</th>
                        <th style='padding:8px; border:1px solid #ccc;'>سرسید</th>
                        <th style='padding:8px; border:1px solid #ccc;'>مبلغ</th>
                    </tr>
            """
            
            for i, check in enumerate(checks, 1):
                priority_icon = "🔴" if i <= 3 else "🟡" if i <= 6 else "🟢"
                
                days_diff = self._calculate_days_diff(check['due_date'])
                if days_diff > 0:
                    status = f"⚠️ {days_diff} روز تأخیر"
                    status_color = '#e74c3c'
                elif days_diff == 0:
                    status = "🔥 امروز"
                    status_color = '#e74c3c'
                else:
                    status = f"⏰ {-days_diff} روز مانده"
                    status_color = '#f39c12'
                
                html += f"""
                    <tr style='border-bottom:1px solid #eee;'>
                        <td style='padding:8px; text-align:center; 
                            font-weight:bold; border:1px solid #eee;'>
                            {priority_icon} {i}
                        </td>
                        <td style='padding:8px; border:1px solid #eee;'>
                            {check['check_number']}
                        </td>
                        <td style='padding:8px; border:1px solid #eee;'>
                            {check.get('party_name') or '-'}
                        </td>
                        <td style='padding:8px; color:{status_color}; border:1px solid #eee;'>
                            {safe_display_date(check['due_date'])}
                            <br><small>{status}</small>
                        </td>
                        <td style='padding:8px; text-align:left; border:1px solid #eee;'>
                            {check['amount']:,.0f}
                        </td>
                    </tr>
                """
            
            html += """
                </table>
                <p style='color:#888; margin-top:15px; text-align:center;'>
                    🤖 پیشنهاد بر اساس سرسید — AI واقعی به زودی
                </p>
            </div>
            """
            
            self.ai_result.setHtml(html)
        except Exception as e:
            self.ai_result.setHtml(f"<p style='color:#e74c3c;'>❌ خطا: {str(e)}</p>")
    
    def _ai_trend_analysis(self):
        """تحلیل روند"""
        self._report_chart()
    
    def _ai_voice_command(self):
        self.ai_result.setHtml("""
        <h3 style='color:#16a085;'>🎤 دستور صوتی</h3>
        <p>مثال: "از صندوق ۵۰۰ هزار تومان برداشت کن"</p>
        <p style='color:#888;'>به زودی با اتصال به ImanAI</p>
        """)


# ============================================================
# دیالوگ بانک
# ============================================================

class BankDialog(BaseDialog):
    """دیالوگ افزودن/ویرایش بانک"""
    
    def __init__(self, bank_id=None, parent=None):
        super().__init__(parent, base_width=500, base_height=550)
        self.bank_id = bank_id
        self.parent_widget = parent
        self.sm = ScreenManager()
        
        self.setWindowTitle(
            "✏️ ویرایش بانک" if bank_id else "➕ بانک جدید"
        )
        self.setModal(True)
        self.setup_ui()
        
        if bank_id:
            self.load_data()
        
        self.apply_theme()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(self.sm.get_spacing(12))
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("خودکار")
        self.code_input.setMinimumHeight(self.sm.get_scaled(32))
        layout.addRow("📋 کد بانک:", self.code_input)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("مثال: بانک ملی")
        self.name_input.setMinimumHeight(self.sm.get_scaled(32))
        self.name_input.setStyleSheet("border: 2px solid #27ae60;")
        layout.addRow("🏦 نام بانک *:", self.name_input)
        
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("مثال: 1234567890")
        self.account_input.setMinimumHeight(self.sm.get_scaled(32))
        layout.addRow("🔢 شماره حساب:", self.account_input)
        
        self.card_input = QLineEdit()
        self.card_input.setPlaceholderText("مثال: 6037-XXXX-XXXX-XXXX")
        self.card_input.setMinimumHeight(self.sm.get_scaled(32))
        layout.addRow("💳 شماره کارت:", self.card_input)
        
        self.iban_input = QLineEdit()
        self.iban_input.setPlaceholderText("IR...")
        self.iban_input.setMinimumHeight(self.sm.get_scaled(32))
        layout.addRow("🏦 شبا:", self.iban_input)
        
        self.branch_input = QLineEdit()
        self.branch_input.setPlaceholderText("نام شعبه")
        self.branch_input.setMinimumHeight(self.sm.get_scaled(32))
        layout.addRow("🏛️ شعبه:", self.branch_input)
        
        self.balance_input = QLineEdit()
        self.balance_input.setPlaceholderText("۰")
        self.balance_input.setAlignment(Qt.AlignRight)
        self.balance_input.setMinimumHeight(self.sm.get_scaled(32))
        layout.addRow("💰 مانده اولیه:", self.balance_input)
        
        self.is_active = QCheckBox("فعال")
        self.is_active.setChecked(True)
        layout.addRow("", self.is_active)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = self.create_button("💾 ذخیره", "successBtn")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = self.create_button("❌ انصراف", "dangerBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
    
    def load_data(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM banks WHERE id = ?", [self.bank_id])
            bank = c.fetchone()
            
            if bank:
                bank = dict(bank)
                self.code_input.setText(bank.get('code') or '')
                self.name_input.setText(bank.get('name') or '')
                self.account_input.setText(bank.get('account_number') or '')
                self.card_input.setText(bank.get('card_number') or '')
                self.iban_input.setText(bank.get('iban') or '')
                self.branch_input.setText(bank.get('branch') or '')
                self.balance_input.setText(f"{bank.get('balance', 0):,}")
                self.is_active.setChecked(bank.get('is_active', 1) == 1)
    
    def get_next_code(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code FROM banks ORDER BY code DESC LIMIT 1")
            last = c.fetchone()
            if last and last['code']:
                try:
                    num = int(last['code'].replace('BNK', '')) + 1
                    return f"BNK{num:03d}"
                except Exception:
                    pass
            return "BNK001"
    
    def accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "خطا", "نام بانک را وارد کنید!")
            return
        
        code = self.code_input.text().strip() or self.get_next_code()
        
        try:
            balance = int(self.balance_input.text().replace(',', '') or 0)
        except ValueError:
            QMessageBox.warning(self, "خطا", "مانده نامعتبر!")
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                if self.bank_id:
                    c.execute('''
                        UPDATE banks SET
                            code = ?, name = ?, account_number = ?,
                            card_number = ?, iban = ?, branch = ?,
                            balance = ?, is_active = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', [
                        code, self.name_input.text().strip(),
                        self.account_input.text().strip() or None,
                        self.card_input.text().strip() or None,
                        self.iban_input.text().strip() or None,
                        self.branch_input.text().strip() or None,
                        balance,
                        1 if self.is_active.isChecked() else 0,
                        self.bank_id
                    ])
                else:
                    c.execute('''
                        INSERT INTO banks 
                        (code, name, account_number, card_number, 
                         iban, branch, balance, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [
                        code, self.name_input.text().strip(),
                        self.account_input.text().strip() or None,
                        self.card_input.text().strip() or None,
                        self.iban_input.text().strip() or None,
                        self.branch_input.text().strip() or None,
                        balance,
                        1 if self.is_active.isChecked() else 0
                    ])
                
                conn.commit()
            
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا: {str(e)}")


# ============================================================
# دیالوگ صندوق
# ============================================================

class CashDialog(BaseDialog):
    """دیالوگ افزودن/ویرایش صندوق"""
    
    def __init__(self, cash_id=None, parent=None):
        super().__init__(parent, base_width=500, base_height=450)
        self.cash_id = cash_id
        self.parent_widget = parent
        self.sm = ScreenManager()
        
        self.setWindowTitle(
            "✏️ ویرایش صندوق" if cash_id else "➕ صندوق جدید"
        )
        self.setModal(True)
        self.setup_ui()
        
        if cash_id:
            self.load_data()
        
        self.apply_theme()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(self.sm.get_spacing(12))
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("خودکار")
        self.code_input.setMinimumHeight(self.sm.get_scaled(32))
        layout.addRow("📋 کد صندوق:", self.code_input)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("مثال: صندوق اصلی")
        self.name_input.setMinimumHeight(self.sm.get_scaled(32))
        self.name_input.setStyleSheet("border: 2px solid #27ae60;")
        layout.addRow("💵 نام صندوق *:", self.name_input)
        
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("مثال: شعبه مرکزی")
        self.location_input.setMinimumHeight(self.sm.get_scaled(32))
        layout.addRow("📍 محل:", self.location_input)
        
        self.balance_input = QLineEdit()
        self.balance_input.setPlaceholderText("۰")
        self.balance_input.setAlignment(Qt.AlignRight)
        self.balance_input.setMinimumHeight(self.sm.get_scaled(32))
        layout.addRow("💰 مانده:", self.balance_input)
        
        self.is_active = QCheckBox("فعال")
        self.is_active.setChecked(True)
        layout.addRow("", self.is_active)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = self.create_button("💾 ذخیره", "successBtn")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = self.create_button("❌ انصراف", "dangerBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
    
    def load_data(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM cash_boxes WHERE id = ?", [self.cash_id])
            cash = c.fetchone()
            
            if cash:
                cash = dict(cash)
                self.code_input.setText(cash.get('code') or '')
                self.name_input.setText(cash.get('name') or '')
                self.location_input.setText(cash.get('location') or '')
                self.balance_input.setText(f"{cash.get('balance', 0):,}")
                self.is_active.setChecked(cash.get('is_active', 1) == 1)
    
    def get_next_code(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code FROM cash_boxes ORDER BY code DESC LIMIT 1")
            last = c.fetchone()
            if last and last['code']:
                try:
                    num = int(last['code'].replace('CSH', '')) + 1
                    return f"CSH{num:03d}"
                except Exception:
                    pass
            return "CSH001"
    
    def accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "خطا", "نام صندوق را وارد کنید!")
            return
        
        code = self.code_input.text().strip() or self.get_next_code()
        
        try:
            balance = int(self.balance_input.text().replace(',', '') or 0)
        except ValueError:
            QMessageBox.warning(self, "خطا", "مانده نامعتبر!")
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                if self.cash_id:
                    c.execute('''
                        UPDATE cash_boxes SET
                            code = ?, name = ?, location = ?,
                            balance = ?, is_active = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', [
                        code,
                        self.name_input.text().strip(),
                        self.location_input.text().strip() or None,
                        balance,
                        1 if self.is_active.isChecked() else 0,
                        self.cash_id
                    ])
                else:
                    c.execute('''
                        INSERT INTO cash_boxes 
                        (code, name, location, balance, is_active)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [
                        code,
                        self.name_input.text().strip(),
                        self.location_input.text().strip() or None,
                        balance,
                        1 if self.is_active.isChecked() else 0
                    ])
                
                conn.commit()
            
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا: {str(e)}")
