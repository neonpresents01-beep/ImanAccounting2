# main.py - پنل مدیریت لایسنس ImanAI
# نسخه نهایی با پشتیبانی کامل از محدودیت ماژول‌ها (limits)

import sys
import sqlite3
import os
import shutil
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from license_core import LicenseGenerator

# ============================================================
# استایل برنامه
# ============================================================
STYLE = """
QMainWindow { background-color: #1a1a2e; }
QLabel { color: #eee; font-size: 11pt; }
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f3460, stop:1 #16213e);
    color: white; border: none; padding: 10px 20px; border-radius: 6px;
    font-weight: bold; font-size: 11pt;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e94560, stop:1 #c62a40);
}
QTableWidget {
    background-color: #16213e; color: #eee; gridline-color: #0f3460;
    border: 1px solid #0f3460; border-radius: 8px;
}
QTableWidget::item:selected { background-color: #e94560; }
QHeaderView::section {
    background-color: #0f3460; color: white; padding: 8px;
    border: none; font-weight: bold;
}
QLineEdit, QSpinBox, QComboBox, QDateEdit, QTextEdit {
    background-color: #16213e; color: #eee; border: 2px solid #0f3460;
    padding: 8px; border-radius: 6px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #e94560; }
QTabWidget::pane { border: 1px solid #0f3460; background-color: #1a1a2e; border-radius: 8px; }
QTabBar::tab {
    background-color: #16213e; color: #eee; padding: 10px 25px;
    margin-right: 3px; font-weight: bold;
}
QTabBar::tab:selected { background-color: #e94560; }
QTabBar::tab:hover { background-color: #0f3460; }
QGroupBox {
    color: #e94560; font-weight: bold; border: 2px solid #0f3460;
    border-radius: 8px; margin-top: 12px; padding-top: 10px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 10px; }
QCheckBox { color: #eee; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; }
QCheckBox::indicator:unchecked {
    border: 2px solid #0f3460; border-radius: 4px; background-color: #16213e;
}
QCheckBox::indicator:checked {
    border: 2px solid #e94560; border-radius: 4px; background-color: #e94560;
}
QStatusBar { background-color: #0f3460; color: white; font-weight: bold; }
"""

# لیست ماژول‌ها و نام فارسی آنها
MODULES_LIST = [
    ("accounting", "📊 حسابداری"),
    ("inventory", "📦 انبارداری"),
    ("payroll", "💰 حقوق دستمزد"),
    ("parties", "👥 اشخاص"),
    ("invoice", "🧾 فاکتور فروش"),
    ("purchase", "📥 فاکتور خرید"),
    ("ai", "🤖 هوش مصنوعی"),
    ("reports", "📈 گزارشات"),
    ("plugin", "🧩 سیستم پلاگین"),
]


class AdminPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.license_gen = LicenseGenerator()
        self.db_path = 'licenses.db'
        
        self.customers_data = []
        self.licenses_data = []
        
        self.setWindowTitle("🔐 پنل مدیریت ImanAI + محدودیت ماژول + امضای پلاگین")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(STYLE)
        
        self.init_database()
        self.init_ui()
        self.load_customers()
        self.load_licenses()
        self.update_stats()
    
    def init_database(self):
        self.conn = sqlite3.connect(self.db_path)
        c = self.conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                company TEXT,
                phone TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_id TEXT UNIQUE,
                customer_name TEXT,
                hwid TEXT,
                expire_date TEXT,
                modules TEXT,
                limits TEXT,
                license_key TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS plugin_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT UNIQUE,
                private_key TEXT,
                public_key TEXT,
                assigned_to TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS signed_plugins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id TEXT,
                name TEXT,
                version TEXT,
                customer_name TEXT,
                key_id TEXT,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS module_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                module_name TEXT NOT NULL,
                limit_value INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(customer_name, module_name)
            )
        ''')
        
        c.execute("SELECT COUNT(*) FROM settings")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO settings (key, value) VALUES ('smtp_server', '')")
            c.execute("INSERT INTO settings (key, value) VALUES ('smtp_port', '587')")
            c.execute("INSERT INTO settings (key, value) VALUES ('email_user', '')")
            c.execute("INSERT INTO settings (key, value) VALUES ('email_password', '')")
        
        self.conn.commit()
    
    def get_setting(self, key):
        c = self.conn.cursor()
        c.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = c.fetchone()
        return row[0] if row else ""
    
    def save_setting(self, key, value):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        layout.addWidget(self.create_header())
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_generate_tab(), "🔑 ساخت لایسنس")
        self.tabs.addTab(self.create_customers_tab(), "👥 مشتریان")
        self.tabs.addTab(self.create_licenses_tab(), "📋 لایسنس‌ها")
        self.tabs.addTab(self.create_verify_tab(), "🔍 بررسی")
        self.tabs.addTab(self.create_plugin_keys_tab(), "🔐 کلیدهای امضا")
        self.tabs.addTab(self.create_plugin_signer_tab(), "✍️ امضای پلاگین")
        self.tabs.addTab(self.create_module_limits_tab(), "⚙️ محدودیت ماژول")
        self.tabs.addTab(self.create_settings_tab(), "⚙️ تنظیمات")
        layout.addWidget(self.tabs)
        
        self.statusBar().showMessage("✅ آماده")
    
    def create_header(self):
        w = QWidget()
        w.setMaximumHeight(80)
        h = QHBoxLayout(w)
        
        title = QLabel("🔐 پنل مدیریت ImanAI + محدودیت ماژول + امضای پلاگین")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #e94560;")
        h.addWidget(title)
        h.addStretch()
        
        self.stats_label = QLabel("📊 در حال بارگذاری...")
        self.stats_label.setStyleSheet("background: #16213e; padding: 10px 20px; border-radius: 8px;")
        h.addWidget(self.stats_label)
        
        return w
    
    def create_generate_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        form = QHBoxLayout()
        
        cust = QGroupBox("اطلاعات مشتری")
        cl = QFormLayout()
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setPlaceholderText("نام مشتری...")
        cl.addRow("👤 نام:", self.customer_combo)
        self.company_input = QLineEdit()
        cl.addRow("🏢 شرکت:", self.company_input)
        self.phone_input = QLineEdit()
        cl.addRow("📞 تلفن:", self.phone_input)
        cust.setLayout(cl)
        form.addWidget(cust)
        
        lic = QGroupBox("اطلاعات لایسنس")
        ll = QFormLayout()
        
        hwid_layout = QHBoxLayout()
        self.hwid_input = QLineEdit()
        self.hwid_input.setPlaceholderText("HWID سیستم...")
        hwid_layout.addWidget(self.hwid_input)
        paste_btn = QPushButton("📋")
        paste_btn.setMaximumWidth(40)
        paste_btn.clicked.connect(lambda: self.hwid_input.setText(QApplication.clipboard().text()))
        hwid_layout.addWidget(paste_btn)
        ll.addRow("🖥️ HWID:", hwid_layout)
        
        exp_layout = QHBoxLayout()
        self.expire_spin = QSpinBox()
        self.expire_spin.setRange(1, 3650)
        self.expire_spin.setValue(30)
        exp_layout.addWidget(self.expire_spin)
        exp_layout.addWidget(QLabel("روز"))
        self.expire_date_label = QLabel()
        self.expire_date_label.setStyleSheet("color: #4CAF50;")
        exp_layout.addWidget(self.expire_date_label)
        ll.addRow("📅 اعتبار:", exp_layout)
        self.expire_spin.valueChanged.connect(
            lambda: self.expire_date_label.setText(
                (datetime.now() + timedelta(days=self.expire_spin.value())).strftime("%Y/%m/%d")
            )
        )
        self.expire_spin.valueChanged.emit(30)
        
        lic.setLayout(ll)
        form.addWidget(lic)
        layout.addLayout(form)
        
        mod = QGroupBox("ماژول‌های فعال")
        ml = QGridLayout()
        
        self.mod_accounting = QCheckBox("📊 حسابداری")
        self.mod_accounting.setChecked(True)
        ml.addWidget(self.mod_accounting, 0, 0)
        
        self.mod_inventory = QCheckBox("📦 انبارداری")
        self.mod_inventory.setChecked(True)
        ml.addWidget(self.mod_inventory, 0, 1)
        
        self.mod_payroll = QCheckBox("💰 حقوق دستمزد")
        self.mod_payroll.setChecked(True)
        ml.addWidget(self.mod_payroll, 0, 2)
        
        self.mod_parties = QCheckBox("👥 مدیریت اشخاص")
        self.mod_parties.setChecked(True)
        ml.addWidget(self.mod_parties, 1, 0)
        
        self.mod_invoice = QCheckBox("🧾 فاکتور فروش")
        self.mod_invoice.setChecked(True)
        ml.addWidget(self.mod_invoice, 1, 1)
        
        self.mod_purchase = QCheckBox("📥 فاکتور خرید")
        self.mod_purchase.setChecked(True)
        ml.addWidget(self.mod_purchase, 1, 2)
        
        self.mod_ai = QCheckBox("🤖 هوش مصنوعی ImanAI")
        self.mod_ai.setChecked(True)
        ml.addWidget(self.mod_ai, 2, 0)
        
        self.mod_reports = QCheckBox("📊 گزارشات پیشرفته")
        self.mod_reports.setChecked(True)
        ml.addWidget(self.mod_reports, 2, 1)
        
        self.mod_plugin = QCheckBox("🧩 سیستم پلاگین")
        self.mod_plugin.setChecked(True)
        ml.addWidget(self.mod_plugin, 2, 2)
        
        mod.setLayout(ml)
        layout.addWidget(mod)
        
        limits_group = QGroupBox("⚙️ محدودیت ماژول‌ها (0 = نامحدود)")
        limits_layout = QGridLayout()
        
        self.limit_accounting = QSpinBox()
        self.limit_accounting.setRange(0, 999999)
        self.limit_accounting.setValue(0)
        self.limit_accounting.setSuffix(" سند")
        self.limit_accounting.setSpecialValueText("نامحدود")
        limits_layout.addWidget(QLabel("📊 حسابداری:"), 0, 0)
        limits_layout.addWidget(self.limit_accounting, 0, 1)
        
        self.limit_inventory = QSpinBox()
        self.limit_inventory.setRange(0, 999999)
        self.limit_inventory.setValue(0)
        self.limit_inventory.setSuffix(" کالا")
        self.limit_inventory.setSpecialValueText("نامحدود")
        limits_layout.addWidget(QLabel("📦 انبارداری:"), 1, 0)
        limits_layout.addWidget(self.limit_inventory, 1, 1)
        
        self.limit_payroll = QSpinBox()
        self.limit_payroll.setRange(0, 999999)
        self.limit_payroll.setValue(0)
        self.limit_payroll.setSuffix(" پرسنل")
        self.limit_payroll.setSpecialValueText("نامحدود")
        limits_layout.addWidget(QLabel("💰 حقوق دستمزد:"), 2, 0)
        limits_layout.addWidget(self.limit_payroll, 2, 1)
        
        self.limit_parties = QSpinBox()
        self.limit_parties.setRange(0, 999999)
        self.limit_parties.setValue(0)
        self.limit_parties.setSuffix(" شخص")
        self.limit_parties.setSpecialValueText("نامحدود")
        limits_layout.addWidget(QLabel("👥 اشخاص:"), 3, 0)
        limits_layout.addWidget(self.limit_parties, 3, 1)
        
        self.limit_invoice = QSpinBox()
        self.limit_invoice.setRange(0, 999999)
        self.limit_invoice.setValue(0)
        self.limit_invoice.setSuffix(" فاکتور")
        self.limit_invoice.setSpecialValueText("نامحدود")
        limits_layout.addWidget(QLabel("🧾 فاکتور فروش:"), 0, 2)
        limits_layout.addWidget(self.limit_invoice, 0, 3)
        
        self.limit_purchase = QSpinBox()
        self.limit_purchase.setRange(0, 999999)
        self.limit_purchase.setValue(0)
        self.limit_purchase.setSuffix(" فاکتور")
        self.limit_purchase.setSpecialValueText("نامحدود")
        limits_layout.addWidget(QLabel("📥 فاکتور خرید:"), 1, 2)
        limits_layout.addWidget(self.limit_purchase, 1, 3)
        
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)
        
        gen_btn = QPushButton("🚀 ساخت لایسنس")
        gen_btn.setStyleSheet("background: #4CAF50; font-size: 14pt; padding: 15px;")
        gen_btn.clicked.connect(self.generate_license)
        layout.addWidget(gen_btn)
        
        res = QGroupBox("لایسنس ساخته شده")
        rl = QVBoxLayout()
        self.license_result = QTextEdit()
        self.license_result.setReadOnly(True)
        self.license_result.setMaximumHeight(100)
        self.license_result.setStyleSheet("background: #0a0a1a; color: #4CAF50; font-family: monospace;")
        rl.addWidget(self.license_result)
        
        bl = QHBoxLayout()
        copy_btn = QPushButton("📋 کپی")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.license_result.toPlainText()))
        bl.addWidget(copy_btn)
        save_btn = QPushButton("💾 ذخیره")
        save_btn.clicked.connect(self.save_license_file)
        bl.addWidget(save_btn)
        rl.addLayout(bl)
        
        res.setLayout(rl)
        layout.addWidget(res)
        
        return w
    
    def create_customers_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        toolbar = QHBoxLayout()
        
        new_customer_btn = QPushButton("➕ مشتری جدید")
        new_customer_btn.setStyleSheet("background: #4CAF50;")
        new_customer_btn.clicked.connect(self.add_customer_dialog)
        toolbar.addWidget(new_customer_btn)
        
        toolbar.addStretch()
        
        toolbar.addWidget(QLabel("🔍 جستجو:"))
        self.customer_search = QLineEdit()
        self.customer_search.setPlaceholderText("جستجو در مشتریان...")
        self.customer_search.textChanged.connect(self.filter_customers)
        toolbar.addWidget(self.customer_search)
        
        layout.addLayout(toolbar)
        
        self.customers_table = QTableWidget()
        self.customers_table.setColumnCount(6)
        self.customers_table.setHorizontalHeaderLabels(["شناسه", "نام", "شرکت", "تلفن", "ایمیل", "تاریخ ثبت"])
        self.customers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.customers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.customers_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.customers_table)
        
        bl = QHBoxLayout()
        bl.addStretch()
        delete_btn = QPushButton("🗑️ حذف مشتری")
        delete_btn.setStyleSheet("background: #f44336;")
        delete_btn.clicked.connect(self.delete_customer)
        bl.addWidget(delete_btn)
        layout.addLayout(bl)
        
        return w
    
    def add_customer_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("➕ مشتری جدید")
        dialog.setGeometry(400, 300, 400, 350)
        dialog.setStyleSheet("""
            QDialog { background-color: #1a1a2e; }
            QLabel { color: #eee; }
            QLineEdit, QTextEdit { background-color: #16213e; color: #eee; border: 1px solid #0f3460; padding: 5px; }
            QPushButton { background-color: #0f3460; }
            QPushButton:hover { background-color: #e94560; }
        """)
        
        layout = QFormLayout(dialog)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("نام مشتری")
        layout.addRow("نام *:", name_input)
        
        company_input = QLineEdit()
        company_input.setPlaceholderText("نام شرکت (اختیاری)")
        layout.addRow("شرکت:", company_input)
        
        phone_input = QLineEdit()
        phone_input.setPlaceholderText("تلفن")
        layout.addRow("تلفن:", phone_input)
        
        email_input = QLineEdit()
        email_input.setPlaceholderText("ایمیل")
        layout.addRow("ایمیل:", email_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "خطا", "نام مشتری الزامی است!")
                return
            
            c = self.conn.cursor()
            try:
                c.execute('''
                    INSERT INTO customers (name, company, phone, email)
                    VALUES (?, ?, ?, ?)
                ''', (name, company_input.text().strip(), phone_input.text().strip(), email_input.text().strip()))
                self.conn.commit()
                QMessageBox.information(self, "موفق", f"✅ مشتری {name} با موفقیت اضافه شد!")
                self.load_customers()
                self.load_customers_for_signer()
                self.refresh_keys_table()
                self.load_module_limits()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "خطا", f"مشتری با نام '{name}' قبلاً وجود دارد!")
    
    def create_licenses_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        fl = QHBoxLayout()
        fl.addWidget(QLabel("مشتری:"))
        self.license_filter = QComboBox()
        self.license_filter.addItem("همه")
        self.license_filter.currentIndexChanged.connect(self.filter_licenses)
        fl.addWidget(self.license_filter)
        fl.addStretch()
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.clicked.connect(self.load_licenses)
        fl.addWidget(refresh_btn)
        layout.addLayout(fl)
        
        self.licenses_table = QTableWidget()
        self.licenses_table.setColumnCount(8)
        self.licenses_table.setHorizontalHeaderLabels([
            "کد", "مشتری", "تاریخ ایجاد", "انقضا", "وضعیت", "روز باقی", "ماژول‌ها", "محدودیت‌ها"
        ])
        self.licenses_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.licenses_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.licenses_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.licenses_table)
        
        return w
    
    def create_verify_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        g = QGroupBox("بررسی لایسنس")
        gl = QVBoxLayout()
        
        self.verify_input = QTextEdit()
        self.verify_input.setPlaceholderText("لایسنس را اینجا وارد کنید...")
        self.verify_input.setMaximumHeight(100)
        gl.addWidget(self.verify_input)
        
        bl = QHBoxLayout()
        verify_btn = QPushButton("🔍 بررسی")
        verify_btn.clicked.connect(self.verify_license)
        bl.addWidget(verify_btn)
        paste_btn = QPushButton("📋 پیست")
        paste_btn.clicked.connect(lambda: self.verify_input.setText(QApplication.clipboard().text()))
        bl.addWidget(paste_btn)
        gl.addLayout(bl)
        
        self.verify_result = QTextEdit()
        self.verify_result.setReadOnly(True)
        self.verify_result.setStyleSheet("background: #0a0a1a; font-family: monospace;")
        gl.addWidget(self.verify_result)
        
        g.setLayout(gl)
        layout.addWidget(g)
        
        return w
    
    def create_plugin_keys_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("🔑 مدیریت کلیدهای RSA برای امضای دیجیتال پلاگین‌ها")
        info.setStyleSheet("color: #4CAF50; font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(info)
        
        desc = QLabel("از این کلیدها برای امضای پلاگین‌ها استفاده کنید. هر مشتری می‌تواند کلید مخصوص خود را داشته باشد.")
        desc.setStyleSheet("color: #aaa; padding: 5px 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        btn_layout = QHBoxLayout()
        gen_btn = QPushButton("➕ ساختن کلید جدید RSA (2048 بیت)")
        gen_btn.setStyleSheet("background: #4CAF50; padding: 8px 15px;")
        gen_btn.clicked.connect(self.generate_plugin_keypair)
        btn_layout.addWidget(gen_btn)
        
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.clicked.connect(self.refresh_keys_table)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.keys_table = QTableWidget()
        self.keys_table.setColumnCount(6)
        self.keys_table.setHorizontalHeaderLabels(["شناسه", "تاریخ ساخت", "اختصاص به", "وضعیت", "کلید عمومی", "عملیات"])
        self.keys_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.keys_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.keys_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.keys_table)
        
        del_btn = QPushButton("🗑️ حذف کلید انتخاب شده")
        del_btn.setStyleSheet("background: #f44336;")
        del_btn.clicked.connect(self.delete_selected_key)
        layout.addWidget(del_btn)
        
        self.refresh_keys_table()
        
        return widget
    
    def create_plugin_signer_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("✍️ امضای دیجیتال پلاگین")
        info.setStyleSheet("color: #4CAF50; font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(info)
        
        form_layout = QFormLayout()
        
        self.signer_customer = QComboBox()
        self.signer_customer.currentIndexChanged.connect(self.load_customer_keys)
        form_layout.addRow("👤 مشتری:", self.signer_customer)
        
        self.signer_key = QComboBox()
        form_layout.addRow("🔑 کلید امضا:", self.signer_key)
        
        self.plugin_file_path = QLineEdit()
        self.plugin_file_path.setReadOnly(True)
        file_btn_layout = QHBoxLayout()
        file_btn_layout.addWidget(self.plugin_file_path)
        browse_btn = QPushButton("📂 انتخاب فایل .py")
        browse_btn.clicked.connect(self.select_plugin_file)
        file_btn_layout.addWidget(browse_btn)
        form_layout.addRow("📄 فایل پلاگین:", file_btn_layout)
        
        self.plugin_name = QLineEdit()
        self.plugin_name.setPlaceholderText("نام پلاگین (مثال: گزارش فروش)")
        form_layout.addRow("نام پلاگین:", self.plugin_name)
        
        self.plugin_version = QLineEdit()
        self.plugin_version.setPlaceholderText("نسخه (مثال: 1.0.0)")
        form_layout.addRow("نسخه:", self.plugin_version)
        
        self.plugin_author = QLineEdit()
        self.plugin_author.setPlaceholderText("نویسنده")
        form_layout.addRow("نویسنده:", self.plugin_author)
        
        self.plugin_desc = QTextEdit()
        self.plugin_desc.setPlaceholderText("توضیحات پلاگین")
        self.plugin_desc.setMaximumHeight(80)
        form_layout.addRow("توضیحات:", self.plugin_desc)
        
        layout.addLayout(form_layout)
        
        sign_btn = QPushButton("🔏 امضا و ساخت فایل پلاگین")
        sign_btn.setStyleSheet("background: #4CAF50; font-size: 12pt; padding: 12px;")
        sign_btn.clicked.connect(self.sign_plugin)
        layout.addWidget(sign_btn)
        
        result_group = QGroupBox("نتیجه")
        result_layout = QVBoxLayout()
        self.sign_result = QTextEdit()
        self.sign_result.setReadOnly(True)
        self.sign_result.setStyleSheet("background: #0a0a1a; color: #4CAF50; font-family: monospace;")
        result_layout.addWidget(self.sign_result)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        plugins_group = QGroupBox("📦 پلاگین‌های ساخته شده")
        plugins_layout = QVBoxLayout()
        
        self.plugins_table = QTableWidget()
        self.plugins_table.setColumnCount(6)
        self.plugins_table.setHorizontalHeaderLabels(["نام", "نسخه", "مشتری", "تاریخ", "شناسه کلید", "عملیات"])
        self.plugins_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.plugins_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        plugins_layout.addWidget(self.plugins_table)
        
        plugins_group.setLayout(plugins_layout)
        layout.addWidget(plugins_group)
        
        self.load_customers_for_signer()
        self.refresh_plugins_table()
        
        return widget
    
    # ======================== تب محدودیت ماژول‌ها ========================
    
    def create_module_limits_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("⚙️ تنظیم سقف مجاز برای هر ماژول (بر اساس مشتری)")
        info.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4CAF50; padding: 10px;")
        layout.addWidget(info)
        
        desc = QLabel("برای هر مشتری می‌توانید حداکثر تعداد تراکنش/رکورد مجاز را تعیین کنید. مقدار 0 به معنی نامحدود است.")
        desc.setStyleSheet("color: #aaa; padding: 5px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("👤 مشتری:"))
        self.limit_customer_combo = QComboBox()
        self.limit_customer_combo.currentIndexChanged.connect(self.load_module_limits)
        select_layout.addWidget(self.limit_customer_combo)
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        self.limits_table = QTableWidget()
        self.limits_table.setColumnCount(4)
        self.limits_table.setHorizontalHeaderLabels(["ماژول", "عنوان ماژول", "محدودیت فعلی", "محدودیت جدید"])
        self.limits_table.horizontalHeader().setStretchLastSection(True)
        self.limits_table.setAlternatingRowColors(True)
        layout.addWidget(self.limits_table)
        
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 ذخیره محدودیت‌ها")
        save_btn.setStyleSheet("background-color: #4CAF50; padding: 10px;")
        save_btn.clicked.connect(self.save_module_limits)
        btn_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("🔄 بازنشانی به حالت پیش‌فرض (نامحدود)")
        reset_btn.clicked.connect(self.reset_module_limits)
        btn_layout.addWidget(reset_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.load_customers_for_limits()
        
        return widget
    
    def load_customers_for_limits(self):
        self.limit_customer_combo.clear()
        for cust in self.customers_data:
            self.limit_customer_combo.addItem(cust[1])
    
    def load_module_limits(self):
        customer = self.limit_customer_combo.currentText()
        if not customer:
            return
        
        c = self.conn.cursor()
        c.execute("SELECT module_name, limit_value FROM module_limits WHERE customer_name = ?", (customer,))
        existing_limits = {row[0]: row[1] for row in c.fetchall()}
        
        self.limits_table.setRowCount(len(MODULES_LIST))
        
        for i, (module_code, module_title) in enumerate(MODULES_LIST):
            self.limits_table.setItem(i, 0, QTableWidgetItem(module_code))
            self.limits_table.setItem(i, 1, QTableWidgetItem(module_title))
            
            current_limit = existing_limits.get(module_code, 0)
            current_text = "نامحدود" if current_limit == 0 else f"{current_limit:,}"
            self.limits_table.setItem(i, 2, QTableWidgetItem(current_text))
            
            spinbox = QSpinBox()
            spinbox.setRange(0, 999999)
            spinbox.setValue(current_limit)
            spinbox.setSuffix(" عدد")
            spinbox.setSpecialValueText("نامحدود")
            self.limits_table.setCellWidget(i, 3, spinbox)
    
    def save_module_limits(self):
        customer = self.limit_customer_combo.currentText()
        if not customer:
            QMessageBox.warning(self, "خطا", "لطفاً یک مشتری انتخاب کنید!")
            return
        
        c = self.conn.cursor()
        
        for i in range(self.limits_table.rowCount()):
            module_code = self.limits_table.item(i, 0).text()
            spinbox = self.limits_table.cellWidget(i, 3)
            limit_value = spinbox.value()
            
            c.execute("DELETE FROM module_limits WHERE customer_name = ? AND module_name = ?", (customer, module_code))
            if limit_value > 0:
                c.execute("INSERT INTO module_limits (customer_name, module_name, limit_value) VALUES (?, ?, ?)",
                         (customer, module_code, limit_value))
        
        self.conn.commit()
        self.load_module_limits()
        QMessageBox.information(self, "موفق", "✅ محدودیت‌های ماژول ذخیره شد!")
    
    def reset_module_limits(self):
        customer = self.limit_customer_combo.currentText()
        if not customer:
            QMessageBox.warning(self, "خطا", "لطفاً یک مشتری انتخاب کنید!")
            return
        
        reply = QMessageBox.question(self, "تأیید بازنشانی", 
            f"آیا از بازنشانی محدودیت‌های مشتری '{customer}' به حالت نامحدود اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            c = self.conn.cursor()
            c.execute("DELETE FROM module_limits WHERE customer_name = ?", (customer,))
            self.conn.commit()
            self.load_module_limits()
            QMessageBox.information(self, "موفق", "✅ محدودیت‌ها به حالت نامحدود بازنشانی شد!")
    
    def create_settings_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        g = QGroupBox("تنظیمات")
        fl = QFormLayout()
        
        self.smtp_server = QLineEdit()
        self.smtp_server.setText(self.get_setting('smtp_server'))
        fl.addRow("SMTP Server:", self.smtp_server)
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(int(self.get_setting('smtp_port') or 587))
        fl.addRow("SMTP Port:", self.smtp_port)
        
        self.email_user = QLineEdit()
        self.email_user.setText(self.get_setting('email_user'))
        fl.addRow("ایمیل:", self.email_user)
        
        self.email_pass = QLineEdit()
        self.email_pass.setEchoMode(QLineEdit.Password)
        self.email_pass.setText(self.get_setting('email_password'))
        fl.addRow("رمز:", self.email_pass)
        
        g.setLayout(fl)
        layout.addWidget(g)
        
        save_btn = QPushButton("💾 ذخیره تنظیمات")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        g2 = QGroupBox("پشتیبان‌گیری")
        gl2 = QHBoxLayout()
        backup_btn = QPushButton("💾 پشتیبان‌گیری")
        backup_btn.clicked.connect(self.backup_database)
        gl2.addWidget(backup_btn)
        restore_btn = QPushButton("📂 بازیابی")
        restore_btn.clicked.connect(self.restore_database)
        gl2.addWidget(restore_btn)
        g2.setLayout(gl2)
        layout.addWidget(g2)
        
        layout.addStretch()
        return w
    
    # ======================== توابع کمکی ========================
    
    def update_stats(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM customers")
        cust_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM licenses WHERE date(expire_date) >= date('now') AND is_active=1")
        active = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM licenses")
        total = c.fetchone()[0]
        self.stats_label.setText(f"👥 {cust_count} | ✅ {active} | 📋 {total}")
    
    def load_customers(self):
        c = self.conn.cursor()
        c.execute("SELECT id, name, company, phone, email, created_at FROM customers ORDER BY created_at DESC")
        self.customers_data = c.fetchall()
        self.display_customers(self.customers_data)
        
        self.customer_combo.clear()
        self.license_filter.clear()
        self.license_filter.addItem("همه")
        for cust in self.customers_data:
            self.customer_combo.addItem(cust[1])
            self.license_filter.addItem(cust[1])
        
        self.load_customers_for_limits()
        self.load_customers_for_signer()
    
    def display_customers(self, data):
        self.customers_table.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, val in enumerate(row):
                self.customers_table.setItem(i, j, QTableWidgetItem(str(val if val else "-")))
    
    def filter_customers(self):
        search = self.customer_search.text().lower()
        if not search:
            self.display_customers(self.customers_data)
            return
        filtered = [c for c in self.customers_data if search in c[1].lower() or (c[2] and search in c[2].lower())]
        self.display_customers(filtered)
    
    def delete_customer(self):
        row = self.customers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک مشتری انتخاب کنید!")
            return
        cust_id = self.customers_table.item(row, 0).text()
        cust_name = self.customers_table.item(row, 1).text()
        
        reply = QMessageBox.question(self, "تأیید", f"حذف مشتری '{cust_name}'؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            c = self.conn.cursor()
            c.execute("DELETE FROM licenses WHERE customer_name=?", (cust_name,))
            c.execute("DELETE FROM module_limits WHERE customer_name=?", (cust_name,))
            c.execute("DELETE FROM customers WHERE id=?", (cust_id,))
            self.conn.commit()
            self.load_customers()
            self.load_licenses()
            self.update_stats()
    
    def load_licenses(self):
        c = self.conn.cursor()
        c.execute('''
            SELECT license_id, customer_name, created_at, expire_date,
                   CASE WHEN date(expire_date) >= date('now') AND is_active=1 THEN 'فعال' ELSE 'منقضی' END,
                   modules, limits
            FROM licenses ORDER BY created_at DESC
        ''')
        self.licenses_data = c.fetchall()
        self.display_licenses(self.licenses_data)
    
    def display_licenses(self, data):
        self.licenses_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.licenses_table.setItem(i, 0, QTableWidgetItem(row[0] if row[0] else "-"))
            self.licenses_table.setItem(i, 1, QTableWidgetItem(row[1] if row[1] else "-"))
            self.licenses_table.setItem(i, 2, QTableWidgetItem(row[2][:10] if row[2] else "-"))
            self.licenses_table.setItem(i, 3, QTableWidgetItem(row[3] if row[3] else "-"))
            
            status = QTableWidgetItem(row[4] if row[4] else "-")
            status.setForeground(QColor('#4CAF50' if row[4]=='فعال' else '#f44336'))
            self.licenses_table.setItem(i, 4, status)
            
            try:
                exp = datetime.strptime(row[3], "%Y-%m-%d")
                days = (exp - datetime.now()).days
                self.licenses_table.setItem(i, 5, QTableWidgetItem(str(days) if days>0 else "0"))
            except:
                self.licenses_table.setItem(i, 5, QTableWidgetItem("-"))
            
            self.licenses_table.setItem(i, 6, QTableWidgetItem(row[5] if row[5] else "-"))
            
            limits_display = ""
            if row[6]:
                try:
                    limits = json.loads(row[6])
                    limits_display = ", ".join([f"{k}:{v}" for k, v in limits.items() if v > 0])
                except:
                    limits_display = row[6]
            self.licenses_table.setItem(i, 7, QTableWidgetItem(limits_display[:30] if limits_display else "-"))
    
    def filter_licenses(self):
        cust = self.license_filter.currentText()
        if cust == "همه":
            self.display_licenses(self.licenses_data)
        else:
            filtered = [l for l in self.licenses_data if l[1] == cust]
            self.display_licenses(filtered)
    
    def generate_license(self):
        cust_name = self.customer_combo.currentText().strip()
        hwid = self.hwid_input.text().strip()
        
        if not cust_name or not hwid:
            QMessageBox.warning(self, "خطا", "نام مشتری و HWID الزامی است!")
            return
        
        modules = []
        if self.mod_accounting.isChecked(): modules.append("accounting")
        if self.mod_inventory.isChecked(): modules.append("inventory")
        if self.mod_payroll.isChecked(): modules.append("payroll")
        if self.mod_parties.isChecked(): modules.append("parties")
        if self.mod_invoice.isChecked(): modules.append("invoice")
        if self.mod_purchase.isChecked(): modules.append("purchase")
        if self.mod_ai.isChecked(): modules.append("ai")
        if self.mod_reports.isChecked(): modules.append("reports")
        if self.mod_plugin.isChecked(): modules.append("plugin")
        
        if not modules:
            QMessageBox.warning(self, "خطا", "حداقل یک ماژول انتخاب کنید!")
            return
        
        limits = {
            "accounting": self.limit_accounting.value(),
            "inventory": self.limit_inventory.value(),
            "payroll": self.limit_payroll.value(),
            "parties": self.limit_parties.value(),
            "invoice": self.limit_invoice.value(),
            "purchase": self.limit_purchase.value()
        }
        
        public_key = None
        if self.mod_plugin.isChecked():
            current_row = self.keys_table.currentRow()
            if current_row >= 0:
                key_id = self.keys_table.item(current_row, 0).text()
                c = self.conn.cursor()
                c.execute('SELECT public_key FROM plugin_keys WHERE key_id = ?', (key_id,))
                row_data = c.fetchone()
                if row_data and row_data[0]:
                    public_key = row_data[0]
        
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO customers (name, company, phone, email) VALUES (?,?,?,?)",
                  (cust_name, self.company_input.text(), self.phone_input.text(), ""))
        
        lic = self.license_gen.generate_license(
            cust_name, hwid, self.expire_spin.value(), 
            modules=modules, 
            limits=limits,
            public_key=public_key
        )
        
        limits_json = json.dumps(limits, ensure_ascii=False)
        
        c.execute('''
            INSERT INTO licenses (license_id, customer_name, hwid, expire_date, modules, limits, license_key)
            VALUES (?,?,?,?,?,?,?)
        ''', (lic['data']['license_id'], cust_name, hwid, lic['data']['expire'], 
              ",".join(modules), limits_json, lic['raw']))
        self.conn.commit()
        
        self.license_result.setText(lic['formatted'])
        self.load_customers()
        self.load_licenses()
        self.update_stats()
        
        modules_text = "، ".join(modules)
        limits_text = "\n".join([f"   {k}: {v}" for k, v in limits.items() if v > 0])
        QMessageBox.information(self, "موفق", 
            f"✅ لایسنس ساخته شد!\n📅 انقضا: {lic['data']['expire']}\n"
            f"📦 ماژول‌ها: {modules_text}\n"
            f"⚙️ محدودیت‌ها:\n{limits_text if limits_text else '   همه نامحدود'}")
    
    def save_license_file(self):
        if not self.license_result.toPlainText():
            QMessageBox.warning(self, "خطا", "ابتدا لایسنس بسازید!")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "ذخیره", "license.key", "*.key")
        if fname:
            with open(fname, 'w') as f:
                f.write(self.license_result.toPlainText())
            QMessageBox.information(self, "موفق", "ذخیره شد!")
    
    def verify_license(self):
        lic = self.verify_input.toPlainText().strip()
        if not lic:
            QMessageBox.warning(self, "خطا", "لایسنس را وارد کنید!")
            return
        result = self.license_gen.decode_license(lic)
        if "error" in result:
            self.verify_result.setText(f"❌ {result['error']}")
        else:
            modules = ', '.join(result.get('modules', []))
            limits = result.get('limits', {})
            limits_text = "\n".join([f"   - {k}: {v}" for k, v in limits.items() if v > 0])
            self.verify_result.setText(f"""
✅ لایسنس معتبر
🆔 {result.get('license_id')}
👤 {result.get('customer')}
📅 {result.get('expire')}
📦 ماژول‌ها: {modules}
⚙️ محدودیت‌ها:
{limits_text if limits_text else '   همه نامحدود'}
            """)
    
    def save_settings(self):
        self.save_setting('smtp_server', self.smtp_server.text())
        self.save_setting('smtp_port', str(self.smtp_port.value()))
        self.save_setting('email_user', self.email_user.text())
        self.save_setting('email_password', self.email_pass.text())
        QMessageBox.information(self, "موفق", "تنظیمات ذخیره شد!")
    
    def backup_database(self):
        fname, _ = QFileDialog.getSaveFileName(self, "پشتیبان‌گیری", 
                                                f"backup_{datetime.now().strftime('%Y%m%d')}.db", "*.db")
        if fname:
            shutil.copy2(self.db_path, fname)
            QMessageBox.information(self, "موفق", "پشتیبان‌گیری انجام شد!")
    
    def restore_database(self):
        fname, _ = QFileDialog.getOpenFileName(self, "بازیابی", "", "*.db")
        if fname:
            reply = QMessageBox.question(self, "تأیید", "جایگزینی دیتابیس فعلی؟", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.conn.close()
                shutil.copy2(fname, self.db_path)
                self.conn = sqlite3.connect(self.db_path)
                self.load_customers()
                self.load_licenses()
                self.update_stats()
                QMessageBox.information(self, "موفق", "بازیابی انجام شد!")
    
    # ======================== توابع مدیریت کلیدها ========================
    
    def generate_plugin_keypair(self):
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            import uuid
            
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public_key = private_key.public_key()
            key_id = str(uuid.uuid4())[:8]
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            
            c = self.conn.cursor()
            c.execute('INSERT INTO plugin_keys (key_id, private_key, public_key, assigned_to) VALUES (?, ?, ?, ?)',
                     (key_id, private_pem, public_pem, ""))
            self.conn.commit()
            
            QMessageBox.information(self, "موفق", f"✅ کلید جدید با شناسه {key_id} ساخته شد!")
            self.refresh_keys_table()
            self.load_customers_for_signer()
            
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا در ساخت کلید: {str(e)}")
    
    def refresh_keys_table(self):
        c = self.conn.cursor()
        c.execute('SELECT key_id, created_at, assigned_to, is_active, public_key FROM plugin_keys ORDER BY created_at DESC')
        keys = c.fetchall()
        
        self.keys_table.setRowCount(len(keys))
        for i, key in enumerate(keys):
            self.keys_table.setItem(i, 0, QTableWidgetItem(key[0]))
            self.keys_table.setItem(i, 1, QTableWidgetItem(key[1][:19] if key[1] else "-"))
            self.keys_table.setItem(i, 2, QTableWidgetItem(key[2] if key[2] else "-"))
            self.keys_table.setItem(i, 3, QTableWidgetItem("✅ فعال" if key[3] else "❌ غیرفعال"))
            
            pub_short = key[4][:50] + "..." if key[4] and len(key[4]) > 50 else key[4]
            self.keys_table.setItem(i, 4, QTableWidgetItem(pub_short if pub_short else "-"))
            
            assign_btn = QPushButton("👤 اختصاص")
            assign_btn.clicked.connect(lambda checked, kid=key[0]: self.assign_key_to_customer(kid))
            self.keys_table.setCellWidget(i, 5, assign_btn)
    
    def assign_key_to_customer(self, key_id):
        dialog = QDialog(self)
        dialog.setWindowTitle("اختصاص کلید به مشتری")
        dialog.setGeometry(400, 300, 300, 150)
        dialog.setStyleSheet("""
            QDialog { background-color: #1a1a2e; }
            QLabel { color: #eee; }
            QComboBox { background-color: #16213e; color: #eee; }
            QPushButton { background-color: #0f3460; }
            QPushButton:hover { background-color: #e94560; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("انتخاب مشتری:"))
        combo = QComboBox()
        for cust in self.customers_data:
            combo.addItem(cust[1])
        layout.addWidget(combo)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("ذخیره")
        cancel_btn = QPushButton("انصراف")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        def save_assign():
            customer = combo.currentText()
            c = self.conn.cursor()
            c.execute("UPDATE plugin_keys SET assigned_to = ? WHERE key_id = ?", (customer, key_id))
            self.conn.commit()
            self.refresh_keys_table()
            self.load_customers_for_signer()
            dialog.accept()
            QMessageBox.information(self, "موفق", f"کلید به {customer} اختصاص یافت!")
        
        save_btn.clicked.connect(save_assign)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec_()
    
    def delete_selected_key(self):
        row = self.keys_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک کلید انتخاب کنید!")
            return
        
        key_id = self.keys_table.item(row, 0).text()
        reply = QMessageBox.question(self, "تأیید حذف", f"آیا از حذف کلید {key_id} اطمینان دارید؟", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            c = self.conn.cursor()
            c.execute("DELETE FROM plugin_keys WHERE key_id = ?", (key_id,))
            self.conn.commit()
            self.refresh_keys_table()
            self.load_customers_for_signer()
            QMessageBox.information(self, "موفق", "کلید حذف شد!")
    
    # ======================== توابع امضای پلاگین ========================
    
    def load_customers_for_signer(self):
        self.signer_customer.clear()
        for cust in self.customers_data:
            self.signer_customer.addItem(cust[1])
        self.load_customer_keys()
    
    def load_customer_keys(self):
        customer = self.signer_customer.currentText()
        self.signer_key.clear()
        
        c = self.conn.cursor()
        c.execute('SELECT key_id, public_key FROM plugin_keys WHERE assigned_to = ? OR assigned_to = ""', (customer,))
        keys = c.fetchall()
        
        for key in keys:
            self.signer_key.addItem(f"{key[0]} - {key[1][:30]}...", key[0])
    
    def select_plugin_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل پلاگین", "", "Python Files (*.py)")
        if fname:
            self.plugin_file_path.setText(fname)
    
    def sign_plugin(self):
        if not self.plugin_file_path.text():
            QMessageBox.warning(self, "خطا", "لطفاً فایل پلاگین را انتخاب کنید!")
            return
        
        if not self.plugin_name.text():
            QMessageBox.warning(self, "خطا", "نام پلاگین را وارد کنید!")
            return
        
        if self.signer_key.currentIndex() < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک کلید امضا انتخاب کنید!")
            return
        
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            
            with open(self.plugin_file_path.text(), 'r', encoding='utf-8') as f:
                code = f.read().encode('utf-8')
            
            plugin_id = self.plugin_name.text().replace(" ", "_").lower()
            manifest = {
                "id": plugin_id,
                "name": self.plugin_name.text(),
                "version": self.plugin_version.text() or "1.0.0",
                "description": self.plugin_desc.toPlainText(),
                "author": self.plugin_author.text() or "ImanAI",
                "min_app_version": "1.0.0",
                "permissions": ["read", "write"]
            }
            
            manifest_json = json.dumps(manifest, ensure_ascii=False).encode('utf-8')
            data_to_sign = manifest_json + code
            
            key_id = self.signer_key.currentData()
            c = self.conn.cursor()
            c.execute('SELECT private_key FROM plugin_keys WHERE key_id = ?', (key_id,))
            row = c.fetchone()
            
            if not row:
                QMessageBox.warning(self, "خطا", "کلید یافت نشد!")
                return
            
            private_key = serialization.load_pem_private_key(row[0].encode(), password=None)
            
            signature = private_key.sign(
                data_to_sign,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            
            result = (len(manifest_json).to_bytes(4, 'big') + manifest_json + 
                      len(signature).to_bytes(4, 'big') + signature + code)
            
            output_path = f"{plugin_id}.plugin"
            with open(output_path, 'wb') as f:
                f.write(result)
            
            c.execute('''
                INSERT INTO signed_plugins (plugin_id, name, version, customer_name, key_id, file_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (plugin_id, self.plugin_name.text(), self.plugin_version.text() or "1.0.0",
                  self.signer_customer.currentText(), key_id, output_path))
            self.conn.commit()
            
            self.sign_result.setText(f"""
✅ پلاگین با موفقیت امضا شد!

📁 فایل خروجی: {output_path}
🆔 شناسه: {plugin_id}
📦 نام: {self.plugin_name.text()}
🔑 کلید: {key_id}
👤 مشتری: {self.signer_customer.currentText()}
            """)
            
            self.refresh_plugins_table()
            QMessageBox.information(self, "موفق", f"پلاگین در {output_path} ذخیره شد!")
            
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا در امضای پلاگین: {str(e)}")
            self.sign_result.setText(f"❌ خطا: {str(e)}")
    
    def refresh_plugins_table(self):
        c = self.conn.cursor()
        c.execute('SELECT name, version, customer_name, created_at, key_id, file_path FROM signed_plugins ORDER BY created_at DESC')
        plugins = c.fetchall()
        
        self.plugins_table.setRowCount(len(plugins))
        for i, p in enumerate(plugins):
            self.plugins_table.setItem(i, 0, QTableWidgetItem(p[0]))
            self.plugins_table.setItem(i, 1, QTableWidgetItem(p[1]))
            self.plugins_table.setItem(i, 2, QTableWidgetItem(p[2] if p[2] else "-"))
            self.plugins_table.setItem(i, 3, QTableWidgetItem(p[3][:19] if p[3] else "-"))
            self.plugins_table.setItem(i, 4, QTableWidgetItem(p[4] if p[4] else "-"))
            
            download_btn = QPushButton("📥 دانلود")
            download_btn.clicked.connect(lambda checked, path=p[5]: self.download_plugin(path))
            self.plugins_table.setCellWidget(i, 5, download_btn)
    
    def download_plugin(self, file_path):
        if os.path.exists(file_path):
            save_path, _ = QFileDialog.getSaveFileName(self, "ذخیره پلاگین", file_path, "Plugin Files (*.plugin)")
            if save_path:
                shutil.copy2(file_path, save_path)
                QMessageBox.information(self, "موفق", f"پلاگین در {save_path} ذخیره شد!")
        else:
            QMessageBox.warning(self, "خطا", "فایل پلاگین یافت نشد!")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Tahoma", 9))
    window = AdminPanel()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()