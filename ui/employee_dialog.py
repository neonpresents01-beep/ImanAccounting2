#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Employee Dialog - تعریف و ویرایش پرسنل با تاریخ شمسی
نسخه بازنویسی شده با پشتیبانی از مزایا و کسورات
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui.base_widgets import BaseDialog
from database import get_db
from additional.payroll_components import MoneyLineEdit
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali


class EmployeeDialog(BaseDialog):
    """دیالوگ تعریف و ویرایش پرسنل"""
    
    def __init__(self, employee_id=None, parent=None, customer_name=""):
        super().__init__(parent, base_width=800, base_height=700, scale_factor=1.0, center=True)
        self.employee_id = employee_id
        self.customer_name = customer_name
        
        self.benefit_items = []
        self.deduction_items = []
        self.benefit_widgets = {}
        self.deduction_widgets = {}
        self._load_payroll_items()
        
        self.setWindowTitle("✏️ ویرایش پرسنل" if employee_id else "➕ تعریف پرسنل جدید")
        self.setGeometry(200, 100, 900, 800)
        self.setModal(True)
        
        self.init_ui()
        
        if parent and hasattr(parent, 'payroll_items_widget'):
            parent.payroll_items_widget.items_changed.connect(self.on_items_changed)
        
        if employee_id:
            self.load_employee_data()
    
    def _load_payroll_items(self):
        """بارگذاری اقلام حقوق (مزایا و کسورات)"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute("PRAGMA table_info(payroll_items)")
                columns = [col[1] for col in c.fetchall()]
                has_category = 'category' in columns
                
                # مزایا
                if has_category:
                    c.execute('''
                        SELECT code, name, type, value, unit, category
                        FROM payroll_items
                        WHERE category = 'benefit' OR category IS NULL
                        ORDER BY code
                    ''')
                else:
                    c.execute('SELECT code, name, type, value, unit FROM payroll_items ORDER BY code')
                
                rows = c.fetchall()
                self.benefit_items = []
                for row in rows:
                    item = {
                        'code': row['code'] if row['code'] is not None else '',
                        'name': row['name'] if row['name'] is not None else '',
                        'type': row['type'] if row['type'] is not None else 'fixed',
                        'value': row['value'] if row['value'] is not None else 0,
                        'unit': row['unit'] if row['unit'] is not None else ''
                    }
                    if has_category and len(row) > 5:
                        item['category'] = row['category'] if row['category'] is not None else 'benefit'
                    else:
                        item['category'] = 'benefit'
                    self.benefit_items.append(item)
                
                # کسورات
                if has_category:
                    c.execute('''
                        SELECT code, name, type, value, unit, category
                        FROM payroll_items
                        WHERE category = 'deduction'
                        ORDER BY code
                    ''')
                    rows = c.fetchall()
                    self.deduction_items = []
                    for row in rows:
                        item = {
                            'code': row['code'] if row['code'] is not None else '',
                            'name': row['name'] if row['name'] is not None else '',
                            'type': row['type'] if row['type'] is not None else 'fixed',
                            'value': row['value'] if row['value'] is not None else 0,
                            'unit': row['unit'] if row['unit'] is not None else '',
                            'category': row['category'] if row['category'] is not None else 'deduction'
                        }
                        self.deduction_items.append(item)
                else:
                    deduction_codes = ['INSURANCE', 'TAX', 'LOAN', 'ADVANCE', 'DEDUCTION', 'PENALTY']
                    self.deduction_items = []
                    for item in self.benefit_items[:]:
                        if item['code'] in deduction_codes or 'کسورات' in item['name'] or 'کسر' in item['name']:
                            self.deduction_items.append(item)
                            self.benefit_items.remove(item)
                
                if not self.benefit_items and not self.deduction_items:
                    self._set_default_items()
                
                print(f"✅ {len(self.benefit_items)} قلم مزایا و {len(self.deduction_items)} قلم کسورات بارگذاری شد")
                
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری اقلام: {e}")
            import traceback
            traceback.print_exc()
            self.benefit_items = []
            self.deduction_items = []
            self._set_default_items()
    
    def _set_default_items(self):
        """تنظیم اقلام پیش‌فرض"""
        self.benefit_items = [
            {'code': 'OVERTIME', 'name': 'اضافه کاری', 'type': 'percent', 'value': 1.5, 'unit': 'برابر'},
            {'code': 'NIGHT', 'name': 'شب کاری', 'type': 'percent', 'value': 0.35, 'unit': 'درصد'},
            {'code': 'FRIDAY', 'name': 'جمعه کاری', 'type': 'percent', 'value': 1.5, 'unit': 'برابر'},
            {'code': 'SHIFT', 'name': 'نوبت کاری', 'type': 'percent', 'value': 0.1, 'unit': 'درصد'},
            {'code': 'CHILD', 'name': 'حق اولاد', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'HOUSING', 'name': 'حق مسکن', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'MEAL', 'name': 'بن کارگری', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'SENIORITY', 'name': 'پایه سنوات', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'SPOUSE', 'name': 'حق همسر', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'RESPONSIBILITY', 'name': 'حق مسئولیت', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'BONUS', 'name': 'پاداش', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'MISSION', 'name': 'حق ماموریت', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
        ]
        self.deduction_items = [
            {'code': 'INSURANCE', 'name': 'بیمه سهم کارمند', 'type': 'percent', 'value': 0.07, 'unit': 'درصد'},
            {'code': 'TAX', 'name': 'مالیات بر درآمد', 'type': 'percent', 'value': 0.1, 'unit': 'درصد'},
            {'code': 'LOAN', 'name': 'قسط وام', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'ADVANCE', 'name': 'مساعده', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'DEDUCTION', 'name': 'سایر کسورات', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'PENALTY', 'name': 'جریمه', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
        ]
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        header = QLabel("📋 اطلاعات پرسنل")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #273c75; padding: 10px; background: #ecf0f1; border-radius: 8px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dcdde1;
                border-radius: 8px;
                padding: 10px;
                background: white;
            }
            QTabBar::tab {
                padding: 10px 20px;
                margin: 2px;
                border-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #273c75;
                color: white;
            }
        """)
        content_layout.addWidget(self.tabs)
        
        self.tabs.addTab(self.create_basic_tab(), "📋 اطلاعات پایه")
        self.tabs.addTab(self.create_benefits_tab(), "💰 مزایا")
        self.tabs.addTab(self.create_deductions_tab(), "📉 کسورات")
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px 30px; border: none; border-radius: 8px; font-weight: bold; font-size: 12pt;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 12px 30px; border: none; border-radius: 8px; font-weight: bold; font-size: 12pt;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        warning = QLabel("⚠️ فیلدهای ستاره‌دار (*) الزامی هستند.")
        warning.setStyleSheet("color: #e74c3c; font-size: 10pt; padding: 5px;")
        warning.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning)
    
    # ======================== تب اطلاعات پایه ========================
    
    def create_basic_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.code = QLineEdit()
        self.code.setPlaceholderText("خودکار")
        self.code.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
        layout.addRow("📋 کد پرسنلی:", self.code)
        
        self.name = QLineEdit()
        self.name.setPlaceholderText("نام و نام خانوادگی")
        self.name.setStyleSheet("padding: 8px; border: 2px solid #27ae60; border-radius: 6px;")
        layout.addRow("👤 نام *:", self.name)
        
        self.national_code = QLineEdit()
        self.national_code.setPlaceholderText("کد ملی 10 رقمی")
        self.national_code.setMaxLength(10)
        self.national_code.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
        self.national_code.textChanged.connect(self.validate_national_code)
        layout.addRow("🆔 کد ملی:", self.national_code)
        
        self.insurance_code = QLineEdit()
        self.insurance_code.setPlaceholderText("شماره بیمه")
        self.insurance_code.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
        layout.addRow("📄 شماره بیمه:", self.insurance_code)
        
        self.position = QLineEdit()
        self.position.setPlaceholderText("سمت سازمانی")
        self.position.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
        layout.addRow("💼 سمت:", self.position)
        
        self.department = QLineEdit()
        self.department.setPlaceholderText("بخش / دپارتمان")
        self.department.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
        layout.addRow("🏢 بخش:", self.department)
        
        self.hire_date = ShamsiDateEdit()
        self.hire_date.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
        layout.addRow("📅 تاریخ استخدام:", self.hire_date)
        
        self.is_active = QCheckBox("فعال")
        self.is_active.setChecked(True)
        self.is_active.setStyleSheet("padding: 8px;")
        layout.addRow("✅ وضعیت:", self.is_active)
        
        hint = QLabel("💡 کد ملی باید 10 رقم باشد و با 0 شروع نشود.")
        hint.setStyleSheet("color: #7f8c8d; font-size: 9pt; padding: 5px;")
        layout.addRow("", hint)
        
        return widget
    
    def validate_national_code(self):
        text = self.national_code.text()
        if len(text) == 10:
            if text.isdigit():
                self.national_code.setStyleSheet("padding: 8px; border: 2px solid #27ae60; border-radius: 6px;")
            else:
                self.national_code.setStyleSheet("padding: 8px; border: 2px solid #e74c3c; border-radius: 6px;")
        elif len(text) > 0:
            self.national_code.setStyleSheet("padding: 8px; border: 2px solid #f39c12; border-radius: 6px;")
        else:
            self.national_code.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
    
    # ======================== تب مزایا ========================
    
    def create_benefits_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.base_salary = MoneyLineEdit()
        self.base_salary.setPlaceholderText("حقوق پایه ماهانه")
        self.base_salary.setStyleSheet("padding: 8px; border: 2px solid #27ae60; border-radius: 6px;")
        layout.addRow("💰 حقوق پایه *:", self.base_salary)
        
        self.child_count = QSpinBox()
        self.child_count.setRange(0, 20)
        self.child_count.setValue(0)
        self.child_count.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
        layout.addRow("👶 تعداد فرزندان:", self.child_count)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addRow("", line)
        
        layout.addRow(QLabel("<b>📋 اقلام مزایا (از سیستم):</b>"))
        
        self.benefit_widgets = {}
        for item in self.benefit_items:
            code = item.get('code', '')
            name = item.get('name', code)
            item_type = item.get('type', 'fixed')
            value = item.get('value', 0)
            
            if item_type == 'fixed':
                widget_item = MoneyLineEdit()
                widget_item.setPlaceholderText(f"{name} (ریال)")
                widget_item.setValue(value if value else 0)
                widget_item.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
                self.benefit_widgets[code] = {'widget': widget_item, 'type': 'fixed', 'default': value}
                layout.addRow(f"💰 {name}:", widget_item)
            else:
                widget_item = QDoubleSpinBox()
                widget_item.setRange(0, 100)
                widget_item.setValue(value if value else 0)
                widget_item.setSingleStep(0.1)
                widget_item.setSuffix(" %")
                widget_item.setStyleSheet("padding: 8px; border: 2px solid #dcdde1; border-radius: 6px;")
                self.benefit_widgets[code] = {'widget': widget_item, 'type': 'percent', 'default': value}
                layout.addRow(f"📊 {name}:", widget_item)
        
        hint = QLabel("💡 این اقلام از سیستم 'اقلام حقوق - مزایا' خوانده شده‌اند.")
        hint.setStyleSheet("color: #7f8c8d; font-size: 9pt; padding: 5px;")
        layout.addRow("", hint)
        
        return widget
    
    # ======================== تب کسورات ========================
    
    def create_deductions_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        layout.addRow(QLabel("<b>📋 اقلام کسورات (از سیستم):</b>"))
        
        self.deduction_widgets = {}
        for item in self.deduction_items:
            code = item.get('code', '')
            name = item.get('name', code)
            item_type = item.get('type', 'fixed')
            value = item.get('value', 0)
            
            if item_type == 'fixed':
                widget_item = MoneyLineEdit()
                widget_item.setPlaceholderText(f"{name} (ریال)")
                widget_item.setValue(value if value else 0)
                widget_item.setStyleSheet("padding: 8px; border: 2px solid #e74c3c; border-radius: 6px;")
                self.deduction_widgets[code] = {'widget': widget_item, 'type': 'fixed', 'default': value}
                layout.addRow(f"📉 {name}:", widget_item)
            else:
                widget_item = QDoubleSpinBox()
                widget_item.setRange(0, 100)
                widget_item.setValue(value if value else 0)
                widget_item.setSingleStep(0.1)
                widget_item.setSuffix(" %")
                widget_item.setStyleSheet("padding: 8px; border: 2px solid #e74c3c; border-radius: 6px;")
                self.deduction_widgets[code] = {'widget': widget_item, 'type': 'percent', 'default': value}
                layout.addRow(f"📊 {name}:", widget_item)
        
        hint = QLabel("💡 این اقلام از سیستم 'اقلام حقوق - کسورات' خوانده شده‌اند.")
        hint.setStyleSheet("color: #7f8c8d; font-size: 9pt; padding: 5px;")
        layout.addRow("", hint)
        
        return widget
    
    # ======================== توابع کمکی ========================
    
    def safe_text(self, value):
        return value if value is not None else ""
    
    def safe_int(self, value):
        return value if value is not None else 0
    
    def safe_float(self, value):
        return value if value is not None else 0.0
    
    # ======================== بارگذاری اطلاعات پرسنل ========================
    
    def load_employee_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('SELECT * FROM employees WHERE id = ?', [self.employee_id])
                row = c.fetchone()
                if not row:
                    return
                emp = dict(row)
                
                self.code.setText(self.safe_text(emp.get('code')))
                self.name.setText(self.safe_text(emp.get('name')))
                self.national_code.setText(self.safe_text(emp.get('national_code')))
                self.insurance_code.setText(self.safe_text(emp.get('insurance_code')))
                self.position.setText(self.safe_text(emp.get('position')))
                self.department.setText(self.safe_text(emp.get('department')))
                
                if emp.get('hire_date'):
                    self.hire_date.set_date(safe_display_date(emp['hire_date']))
                self.is_active.setChecked(emp.get('is_active', 0) == 1)
                
                self.base_salary.setValue(self.safe_int(emp.get('base_salary')))
                self.child_count.setValue(self.safe_int(emp.get('child_count')))
                
                for code, item_data in self.benefit_widgets.items():
                    widget = item_data['widget']
                    item_type = item_data['type']
                    if code == 'OVERTIME':
                        val = self.safe_float(emp.get('overtime_rate', 1.5))
                    elif code == 'NIGHT':
                        val = self.safe_float(emp.get('night_work_rate', 0.35))
                    elif code == 'FRIDAY':
                        val = self.safe_float(emp.get('friday_work_rate', 1.5))
                    elif code == 'SHIFT':
                        val = self.safe_float(emp.get('shift_allowance_rate', 0.1))
                    elif code == 'SPOUSE':
                        val = self.safe_int(emp.get('spouse_allowance', 0))
                    elif code == 'MEAL':
                        val = self.safe_int(emp.get('meal_allowance', 0))
                    elif code == 'HOUSING':
                        val = self.safe_int(emp.get('housing_allowance', 0))
                    elif code == 'RESPONSIBILITY':
                        val = self.safe_int(emp.get('responsibility_pay', 0))
                    elif code == 'SENIORITY':
                        val = self.safe_int(emp.get('seniority_pay', 0))
                    elif code == 'BONUS':
                        val = self.safe_int(emp.get('bonus', 0))
                    elif code == 'MISSION':
                        val = self.safe_int(emp.get('mission_allowance', 0))
                    else:
                        val = item_data.get('default', 0)
                    
                    if item_type == 'fixed':
                        widget.setValue(int(val) if val else 0)
                    else:
                        widget.setValue(float(val) if val else 0.0)
                
                for code, item_data in self.deduction_widgets.items():
                    widget = item_data['widget']
                    item_type = item_data['type']
                    if code == 'INSURANCE':
                        val = self.safe_float(emp.get('insurance_premium', 0.07))
                    elif code == 'TAX':
                        val = self.safe_float(emp.get('tax_rate', 0.1))
                    elif code == 'LOAN':
                        val = self.safe_int(emp.get('loan_installment', 0))
                    elif code == 'ADVANCE':
                        val = self.safe_int(emp.get('advance_payment', 0))
                    elif code == 'DEDUCTION':
                        val = self.safe_int(emp.get('deduction', 0))
                    elif code == 'PENALTY':
                        val = self.safe_int(emp.get('penalty', 0))
                    else:
                        val = item_data.get('default', 0)
                    
                    if item_type == 'fixed':
                        widget.setValue(int(val) if val else 0)
                    else:
                        widget.setValue(float(val) if val else 0.0)
                
                print(f"✅ اطلاعات پرسنل {emp.get('name', '')} بارگذاری شد")
                
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در بارگذاری اطلاعات: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # ======================== بروزرسانی با سیگنال ========================
    
    def on_items_changed(self):
        """بروزرسانی اقلام هنگام تغییر"""
        self._load_payroll_items()
        self._rebuild_tabs()
        if self.employee_id:
            self.load_employee_data()
        print("✅ اقلام حقوق در Employee Dialog بروزرسانی شد")
    
    def _rebuild_tabs(self):
        """بازسازی تب‌های مزایا و کسورات"""
        while self.tabs.count() > 1:
            self.tabs.removeTab(1)
        self.tabs.addTab(self.create_benefits_tab(), "💰 مزایا")
        self.tabs.addTab(self.create_deductions_tab(), "📉 کسورات")
    
    # ======================== ذخیره ========================
    
    def get_next_code(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT MAX(CAST(SUBSTR(code, 4) AS INTEGER)) FROM employees WHERE code LIKE 'EMP%'")
                max_num = c.fetchone()[0]
                if not max_num:
                    max_num = 0
                return f"EMP{max_num + 1:04d}"
        except:
            return "EMP0001"
    
    def validate_national_code_format(self, code):
        if not code:
            return True
        if len(code) != 10 or not code.isdigit() or code[0] == '0':
            return False
        return True
    
    def accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "خطا", "❌ نام پرسنل الزامی است!")
            return
        
        if self.base_salary.value() <= 0:
            QMessageBox.warning(self, "خطا", "❌ حقوق پایه باید بیشتر از صفر باشد!")
            return
        
        national_code = self.national_code.text().strip()
        if national_code and not self.validate_national_code_format(national_code):
            QMessageBox.warning(self, "خطا", "❌ کد ملی نامعتبر است!")
            return
        
        code = self.code.text().strip()
        if not code:
            code = self.get_next_code()
        
        name = self.name.text().strip()
        national_code = national_code if national_code else None
        insurance_code = self.insurance_code.text().strip() or None
        position = self.position.text().strip() or None
        department = self.department.text().strip() or None
        hire_date_shamsi = self.hire_date.get_shamsi()
        
        benefit_values = {}
        for code_item, item_data in self.benefit_widgets.items():
            widget = item_data['widget']
            benefit_values[code_item] = widget.value() if hasattr(widget, 'value') else 0
        
        deduction_values = {}
        for code_item, item_data in self.deduction_widgets.items():
            widget = item_data['widget']
            deduction_values[code_item] = widget.value() if hasattr(widget, 'value') else 0
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                if self.employee_id:
                    c.execute('''
                        UPDATE employees SET
                            code = ?,
                            name = ?,
                            national_code = ?,
                            insurance_code = ?,
                            position = ?,
                            department = ?,
                            hire_date = ?,
                            base_salary = ?,
                            child_count = ?,
                            spouse_allowance = ?,
                            meal_allowance = ?,
                            housing_allowance = ?,
                            responsibility_pay = ?,
                            seniority_pay = ?,
                            bonus = ?,
                            mission_allowance = ?,
                            overtime_rate = ?,
                            night_work_rate = ?,
                            friday_work_rate = ?,
                            holiday_work_rate = ?,
                            shift_allowance_rate = ?,
                            insurance_premium = ?,
                            loan_installment = ?,
                            advance_payment = ?,
                            deduction = ?,
                            penalty = ?,
                            tax_rate = ?,
                            is_active = ?
                        WHERE id = ?
                    ''', (
                        code, name, national_code, insurance_code, position, department,
                        hire_date_shamsi, self.base_salary.value(), self.child_count.value(),
                        benefit_values.get('SPOUSE', 0), benefit_values.get('MEAL', 0),
                        benefit_values.get('HOUSING', 0), benefit_values.get('RESPONSIBILITY', 0),
                        benefit_values.get('SENIORITY', 0), benefit_values.get('BONUS', 0),
                        benefit_values.get('MISSION', 0), benefit_values.get('OVERTIME', 1.5),
                        benefit_values.get('NIGHT', 0.35), benefit_values.get('FRIDAY', 1.5),
                        benefit_values.get('FRIDAY', 1.5), benefit_values.get('SHIFT', 0.1),
                        deduction_values.get('INSURANCE', 0.07), deduction_values.get('LOAN', 0),
                        deduction_values.get('ADVANCE', 0), deduction_values.get('DEDUCTION', 0),
                        deduction_values.get('PENALTY', 0), deduction_values.get('TAX', 0.1),
                        1 if self.is_active.isChecked() else 0, self.employee_id
                    ))
                else:
                    c.execute('''
                        INSERT INTO employees (
                            code, name, national_code, insurance_code, position, department,
                            hire_date, base_salary, child_count, spouse_allowance, meal_allowance,
                            housing_allowance, responsibility_pay, seniority_pay, bonus,
                            mission_allowance, overtime_rate, night_work_rate, friday_work_rate,
                            holiday_work_rate, shift_allowance_rate, insurance_premium,
                            loan_installment, advance_payment, deduction, penalty, tax_rate, is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        code, name, national_code, insurance_code, position, department,
                        hire_date_shamsi, self.base_salary.value(), self.child_count.value(),
                        benefit_values.get('SPOUSE', 0), benefit_values.get('MEAL', 0),
                        benefit_values.get('HOUSING', 0), benefit_values.get('RESPONSIBILITY', 0),
                        benefit_values.get('SENIORITY', 0), benefit_values.get('BONUS', 0),
                        benefit_values.get('MISSION', 0), benefit_values.get('OVERTIME', 1.5),
                        benefit_values.get('NIGHT', 0.35), benefit_values.get('FRIDAY', 1.5),
                        benefit_values.get('FRIDAY', 1.5), benefit_values.get('SHIFT', 0.1),
                        deduction_values.get('INSURANCE', 0.07), deduction_values.get('LOAN', 0),
                        deduction_values.get('ADVANCE', 0), deduction_values.get('DEDUCTION', 0),
                        deduction_values.get('PENALTY', 0), deduction_values.get('TAX', 0.1),
                        1 if self.is_active.isChecked() else 0
                    ))
                
                conn.commit()
                action = "ویرایش" if self.employee_id else "ایجاد"
                QMessageBox.information(self, "موفق", f"✅ پرسنل با موفقیت {action} شد!")
                super().accept()
                
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره اطلاعات: {str(e)}")
            import traceback
            traceback.print_exc()
