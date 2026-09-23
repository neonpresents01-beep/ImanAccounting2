# ui/payroll_widget.py
# ============================================================
# ویجت مدیریت حقوق و دستمزد با پشتیبانی از تم
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from ui.base_widgets import BaseWidget, BaseDialog
from database import get_db, ModuleLimitHelper, DatabaseManager
from additional.payroll_calculator import PayrollCalculator
from ui.employee_dialog import EmployeeDialog
from additional.payroll_components import PayrollCalculateDialog, InsuranceReportDialog, MoneyLineEdit
from ui.payroll_items_widget import PayrollItemsWidget
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali
import os
import re
import csv
from datetime import datetime

class PayrollWidget(BaseWidget):
    """ویجت اصلی مدیریت حقوق و دستمزد با پشتیبانی از تم و سطح دسترسی"""
    
    def __init__(self, customer_name: str = "", user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        self.customer_name = customer_name
        self.user_level = user_level
        self.employees_data = []
        self.current_employee = None
        self.screen_manager = self.screen_manager
        
        self.setup_ui()
        self.load_employees()
        self.update_ui_by_permission()
        self.apply_theme()
    
    def set_user_level(self, level: str):
        """تنظیم سطح دسترسی"""
        self.user_level = level
        self.update_ui_by_permission()
    
    def update_ui_by_permission(self):
        """بروزرسانی UI بر اساس سطح دسترسی"""
        can_edit = self.user_level in ['admin', 'payroll']
        can_view = self.user_level in ['admin', 'payroll', 'viewer']
        
        # نمایش/مخفی کردن دکمه‌ها
        for btn_name in ['new_btn', 'edit_btn', 'delete_btn', 'calc_btn', 'pay_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setVisible(can_edit)
        
        # نمایش/مخفی کردن اطلاعات حساس
        if hasattr(self, 'emp_salary'):
            if not can_view:
                self.emp_salary.setText("🔒 مخفی")
    
    # ========== تابع جدید برای حل مشکل ستون‌های داینامیک ==========
    def _ensure_payroll_column(self, columns_to_check):
        """بررسی و افزودن ستون‌های مورد نیاز به جدول payrolls در صورت نبودن"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("PRAGMA table_info(payrolls)")
                existing_columns = [col[1] for col in c.fetchall()]
                
                for col in columns_to_check:
                    if col not in existing_columns:
                        c.execute(f"ALTER TABLE payrolls ADD COLUMN {col} INTEGER DEFAULT 0")
                        print(f"ستون {col} به جدول payrolls اضافه شد.")
                conn.commit()
        except Exception as e:
            print(f"⚠️ خطا در بررسی ستون‌ها: {e}")
    # ==============================================================

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(self.spacing(10))
        main_layout.setContentsMargins(self.margin(10), self.margin(10),
                                       self.margin(10), self.margin(10))
        
        title = QLabel("💰 مدیریت حقوق و دستمزد")
        title.setObjectName("titleLabel")
        main_layout.addWidget(title)
        
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        self.tabs.addTab(self._create_payroll_tab(), "👔 حقوق و دستمزد")
        
        self.payroll_items_widget = PayrollItemsWidget()
        self.tabs.addTab(self.payroll_items_widget, "📋 اقلام حقوق")
        self.payroll_items_widget.items_changed.connect(self.on_items_changed)
        
        main_layout.addWidget(self.tabs)
        
        self.apply_theme()
    
    def on_items_changed(self):
        self.load_payroll()
        if self.current_employee:
            self.show_employee_info(self.current_employee['id'])
            self.view_payslip(self.current_employee['id'])
    
    def _create_payroll_tab(self):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setSpacing(self.spacing(10))
        main_layout.setContentsMargins(self.margin(5), self.margin(5),
                                       self.margin(5), self.margin(5))
        
        right_panel = QWidget()
        right_panel.setObjectName("cardWidget")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(self.spacing(10))
        
        toolbar = self._create_employee_toolbar()
        right_layout.addLayout(toolbar)
        
        payroll_toolbar = self._create_payroll_toolbar()
        right_layout.addLayout(payroll_toolbar)
        
        period_layout = self._create_period_layout()
        right_layout.addLayout(period_layout)
        
        self.payroll_table = self.create_table(
            ["کد", "نام", "حقوق پایه", "روز کارکرد", "اضافه کاری",
             "شب کاری", "جمعه کاری", "نوبت کاری", "حق اولاد",
             "خالص پرداختی", "وضعیت"],
            stretch_last=True
        )
        self.payroll_table.clicked.connect(self.on_employee_selected)
        right_layout.addWidget(self.payroll_table)
        
        left_panel = QWidget()
        left_panel.setObjectName("cardWidget")
        left_panel.setMaximumWidth(self.scaled(500))
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(self.spacing(10))
        
        info_group = QGroupBox("📋 اطلاعات پرسنل")
        info_layout = QFormLayout(info_group)
        info_layout.setLabelAlignment(Qt.AlignRight)
        
        self.emp_code = QLineEdit()
        self.emp_code.setReadOnly(True)
        info_layout.addRow("کد پرسنلی:", self.emp_code)
        
        self.emp_name = QLineEdit()
        self.emp_name.setReadOnly(True)
        info_layout.addRow("نام:", self.emp_name)
        
        self.emp_national = QLineEdit()
        self.emp_national.setReadOnly(True)
        info_layout.addRow("کد ملی:", self.emp_national)
        
        self.emp_salary = QLineEdit()
        self.emp_salary.setReadOnly(True)
        info_layout.addRow("حقوق پایه:", self.emp_salary)
        
        info_group.setLayout(info_layout)
        left_layout.addWidget(info_group)
        
        payslip_group = QGroupBox("📄 فیش حقوقی")
        payslip_layout = QVBoxLayout(payslip_group)
        
        self.payslip_text = QTextEdit()
        self.payslip_text.setReadOnly(True)
        self.payslip_text.setMinimumHeight(self.scaled(300))
        payslip_layout.addWidget(self.payslip_text)
        
        payslip_group.setLayout(payslip_layout)
        left_layout.addWidget(payslip_group)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(self.spacing(8))
        
        pay_btn = self.create_button("💳 ثبت پرداخت", "successBtn")
        pay_btn.clicked.connect(self.register_payment)
        btn_layout.addWidget(pay_btn)
        
        print_btn = self.create_button("🖨️ چاپ فیش", "infoBtn")
        print_btn.clicked.connect(self.print_payslip)
        btn_layout.addWidget(print_btn)
        
        left_layout.addLayout(btn_layout)
        
        main_layout.addWidget(right_panel, 2)
        main_layout.addWidget(left_panel, 1)
        
        return widget
    
    def _create_employee_toolbar(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(self.spacing(8))
        
        buttons = [
            ("➕ پرسنل جدید", "successBtn", self.new_employee),
            ("✏️ ویرایش پرسنل", "warningBtn", self.edit_employee),
            ("🗑️ حذف پرسنل", "dangerBtn", self.delete_employee),
        ]
        
        for text, obj_name, callback in buttons:
            btn = self.create_button(text, obj_name)
            btn.clicked.connect(callback)
            toolbar.addWidget(btn)
        
        toolbar.addStretch()
        
        refresh_btn = self.create_button("🔄 بروزرسانی اقلام", "infoBtn")
        refresh_btn.clicked.connect(self.refresh_payroll_items)
        toolbar.addWidget(refresh_btn)
        
        return toolbar
    
    def _create_payroll_toolbar(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(self.spacing(8))
        
        calc_btn = self.create_button("🧮 محاسبه حقوق ماهانه", "infoBtn")
        calc_btn.clicked.connect(self.calculate_payroll)
        toolbar.addWidget(calc_btn)
        
        insurance_btn = self.create_button("📄 لیست بیمه", "warningBtn")
        insurance_btn.clicked.connect(self.show_insurance_list)
        toolbar.addWidget(insurance_btn)
        
        export_btn = self.create_button("📎 خروجی Excel", "successBtn")
        export_btn.clicked.connect(self.export_to_excel)
        toolbar.addWidget(export_btn)
        
        toolbar.addStretch()
        return toolbar
    
    def _create_period_layout(self):
        layout = QHBoxLayout()
        layout.setSpacing(self.spacing(8))
        
        layout.addWidget(QLabel("📅 دوره:"))
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1390, 1450)
        self.year_spin.setValue(1404)
        self.year_spin.valueChanged.connect(self.load_payroll)
        layout.addWidget(self.year_spin)
        
        self.month_combo = QComboBox()
        self.month_combo.addItems([
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ])
        self.month_combo.currentIndexChanged.connect(self.load_payroll)
        layout.addWidget(self.month_combo)
        
        layout.addStretch()
        return layout
    
    # ========== توابع اصلی ==========
    
    def load_employees(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM employees WHERE is_active = 1 ORDER BY code')
            self.employees_data = c.fetchall()
        self.load_payroll()
    
    def load_payroll(self):
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        
        self.payroll_table.setRowCount(len(self.employees_data))
        
        for i, emp in enumerate(self.employees_data):
            self.payroll_table.setItem(i, 0, QTableWidgetItem(emp['code']))
            self.payroll_table.setItem(i, 1, QTableWidgetItem(emp['name']))
            
            salary_item = QTableWidgetItem(f"{emp['base_salary']:,.0f}")
            salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.payroll_table.setItem(i, 2, salary_item)
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('SELECT * FROM payrolls WHERE employee_id = ? AND year = ? AND month = ?',
                         [emp['id'], year, month])
                payroll = c.fetchone()
            
            if payroll:
                self.payroll_table.setItem(i, 3, QTableWidgetItem(str(payroll['work_days'])))
                self.payroll_table.setItem(i, 4, QTableWidgetItem(f"{payroll['overtime_hours']:.1f}"))
                self.payroll_table.setItem(i, 5, QTableWidgetItem(f"{payroll['night_work_hours']:.1f}"))
                self.payroll_table.setItem(i, 6, QTableWidgetItem(f"{payroll['friday_work_hours']:.1f}"))
                self.payroll_table.setItem(i, 7, QTableWidgetItem(str(payroll['shift_days'])))
                
                child_item = QTableWidgetItem(f"{payroll['child_allowance']:,.0f}")
                child_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.payroll_table.setItem(i, 8, child_item)
                
                net_item = QTableWidgetItem(f"{payroll['net_salary']:,.0f}")
                net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                net_item.setForeground(QColor('#27ae60'))
                self.payroll_table.setItem(i, 9, net_item)
                
                status_text = {'pending': '⏳ در انتظار', 'paid': '✅ پرداخت شده'}.get(payroll['payment_status'], payroll['payment_status'])
                status_item = QTableWidgetItem(status_text)
                if payroll['payment_status'] == 'paid':
                    status_item.setForeground(QColor('#27ae60'))
                else:
                    status_item.setForeground(QColor('#f39c12'))
                self.payroll_table.setItem(i, 10, status_item)
            else:
                for col in range(3, 11):
                    self.payroll_table.setItem(i, col, QTableWidgetItem("-"))
    
    def on_employee_selected(self):
        row = self.payroll_table.currentRow()
        if row >= 0 and row < len(self.employees_data):
            emp = self.employees_data[row]
            self.current_employee = emp
            self.show_employee_info(emp['id'])
            self.view_payslip(emp['id'])
    
    def show_employee_info(self, employee_id):
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM employees WHERE id = ?', [employee_id])
            emp = c.fetchone()
            if emp:
                self.emp_code.setText(emp['code'])
                self.emp_name.setText(emp['name'])
                self.emp_national.setText(emp['national_code'] or '-')
                self.emp_salary.setText(f"{emp['base_salary']:,.0f} ریال")
    
    def view_payslip(self, employee_id):
        """نمایش فیش حقوقی با اقلام پویا"""
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT p.*, e.name, e.code, e.position
                FROM payrolls p
                JOIN employees e ON p.employee_id = e.id
                WHERE p.employee_id = ? AND p.year = ? AND p.month = ?
            ''', [employee_id, year, month])
            payroll = c.fetchone()
            
            if not payroll:
                self.payslip_text.setHtml("""
                <div style='text-align: center; padding: 50px; color: #666;'>
                    <h3>📄 فیش حقوقی</h3>
                    <p>برای این دوره فیش حقوقی ثبت نشده است.</p>
                </div>
                """)
                return
            
            payroll = DatabaseManager.to_dict(payroll)
        
        benefit_items, deduction_items = self._get_payroll_items()
        
        html = self._generate_payslip_html(payroll, benefit_items, deduction_items, month_names[month-1], year)
        self.payslip_text.setHtml(html)
    
    def _get_payroll_items(self):
        """دریافت اقلام مزایا و کسورات از دیتابیس"""
        benefit_items = []
        deduction_items = []
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("PRAGMA table_info(payroll_items)")
                columns = [col[1] for col in c.fetchall()]
                has_category = 'category' in columns
                
                if has_category:
                    c.execute('''
                        SELECT code, name, type, value, unit
                        FROM payroll_items
                        WHERE category = 'benefit' OR category IS NULL
                        ORDER BY code
                    ''')
                else:
                    c.execute('SELECT code, name, type, value, unit FROM payroll_items ORDER BY code')
                
                rows = c.fetchall()
                for row in rows:
                    benefit_items.append({
                        'code': row['code'] or '',
                        'name': row['name'] or '',
                        'type': row['type'] or 'fixed',
                        'value': row['value'] or 0,
                        'unit': row['unit'] or ''
                    })
                
                if has_category:
                    c.execute('''
                        SELECT code, name, type, value, unit
                        FROM payroll_items
                        WHERE category = 'deduction'
                        ORDER BY code
                    ''')
                    rows = c.fetchall()
                    for row in rows:
                        deduction_items.append({
                            'code': row['code'] or '',
                            'name': row['name'] or '',
                            'type': row['type'] or 'fixed',
                            'value': row['value'] or 0,
                            'unit': row['unit'] or ''
                        })
                
                if not benefit_items and not deduction_items:
                    benefit_items, deduction_items = self._get_default_items()
                    
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری اقلام: {e}")
            benefit_items, deduction_items = self._get_default_items()
        
        return benefit_items, deduction_items
    
    def _get_default_items(self):
        benefit_items = [
            {'code': 'OVERTIME', 'name': 'اضافه کاری', 'type': 'percent', 'value': 1.5, 'unit': 'برابر'},
            {'code': 'NIGHT', 'name': 'شب کاری', 'type': 'percent', 'value': 0.35, 'unit': 'درصد'},
            {'code': 'FRIDAY', 'name': 'جمعه کاری', 'type': 'percent', 'value': 1.5, 'unit': 'برابر'},
            {'code': 'SHIFT', 'name': 'نوبت کاری', 'type': 'percent', 'value': 0.1, 'unit': 'درصد'},
            {'code': 'CHILD', 'name': 'حق اولاد', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'HOUSING', 'name': 'حق مسکن', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'MEAL', 'name': 'بن کارگری', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
            {'code': 'SPOUSE', 'name': 'حق همسر', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
        ]
        deduction_items = [
            {'code': 'INSURANCE', 'name': 'بیمه سهم کارمند', 'type': 'percent', 'value': 0.07, 'unit': 'درصد'},
            {'code': 'TAX', 'name': 'مالیات بر درآمد', 'type': 'percent', 'value': 0.1, 'unit': 'درصد'},
            {'code': 'LOAN', 'name': 'قسط وام', 'type': 'fixed', 'value': 0, 'unit': 'ریال'},
        ]
        return benefit_items, deduction_items
    
    def _generate_payslip_html(self, payroll, benefit_items, deduction_items, month_name, year):
        """تولید HTML فیش حقوقی (اصلاح شده برای جلوگیری از خطای ستون‌های ناموجود)"""
        benefit_field_map = {
            'OVERTIME': 'overtime_pay',
            'NIGHT': 'night_work_pay',
            'FRIDAY': 'friday_work_pay',
            'SHIFT': 'shift_allowance',
            'CHILD': 'child_allowance',
            'SPOUSE': 'spouse_allowance',
            'MEAL': 'meal_allowance',
            'HOUSING': 'housing_allowance',
        }
        deduction_field_map = {
            'INSURANCE': 'insurance_employee',
            'TAX': 'tax',
            'LOAN': 'loan_installment',
        }
        
        company_name = "شرکت حسابداری پارسه"
        payment_date = safe_display_date(payroll['payment_date']) if payroll['payment_date'] else "-"
        
        benefits_html = ""
        gross_salary = 0
        for item in benefit_items:
            field = benefit_field_map.get(item['code'], item['code'].lower())
            try:
                value = payroll[field] if field in payroll.keys() else 0
            except:
                value = 0
            benefits_html += f"<tr><td>{item['name']}</td><td align='left'>{value:,.0f} ریال</td></tr>"
            gross_salary += value
        
        deductions_html = ""
        total_deductions = 0
        for item in deduction_items:
            field = deduction_field_map.get(item['code'], item['code'].lower())
            try:
                value = payroll[field] if field in payroll.keys() else 0
            except:
                value = 0
            deductions_html += f"<tr><td>{item['name']}</td><td align='left'>{value:,.0f} ریال</td></tr>"
            total_deductions += value
        
        gross_salary_total = payroll.get('gross_salary', gross_salary)
        net_salary = payroll.get('net_salary', 0)
        status = payroll.get('payment_status', 'pending')
        status_text = "پرداخت شده" if status == 'paid' else "در انتظار پرداخت"
        status_color = "#27ae60" if status == 'paid' else "#f39c12"
        
        html = f"""
        <div style='font-family: Tahoma; direction: rtl; padding: 5px;'>
            <div style='text-align: center; border-bottom: 2px solid #273c75; padding-bottom: 10px; margin-bottom: 15px;'>
                <h3 style='color: #273c75; margin: 0;'>{company_name}</h3>
                <h4 style='margin: 8px 0 0 0; color: #2C3E50;'>فیش حقوقی</h4>
                <p style='margin: 2px 0; font-weight: bold;'>{month_name} {year}</p>
            </div>
            
            <div style='background: #f8f9fa; padding: 8px 12px; border-radius: 5px; margin-bottom: 10px;'>
                <table width='100%' style='font-size: 10pt;'>
                    <tr><td><b>نام:</b> {payroll.get('name', '-')}</td><td><b>کد پرسنلی:</b> {payroll.get('code', '-')}</td></tr>
                    <tr><td><b>سمت:</b> {payroll.get('position', '-')}</td><td><b>تاریخ پرداخت:</b> {payment_date}</td></tr>
                </table>
            </div>
            
            <h4 style='color: #27ae60; margin: 5px 0;'>💰 حقوق و مزایا:</h4>
            <table width='100%' style='border-collapse: collapse; font-size: 10pt;'>
                {benefits_html}
                <tr style='font-weight: bold; background: #e8f5e9;'>
                    <td>جمع حقوق و مزایا</td>
                    <td align='left'>{gross_salary_total:,.0f} ریال</td>
                </tr>
            </table>
            
            <h4 style='color: #e74c3c; margin: 5px 0;'>📉 کسورات:</h4>
            <table width='100%' style='border-collapse: collapse; font-size: 10pt;'>
                {deductions_html}
                <tr style='font-weight: bold; background: #ffebee;'>
                    <td>جمع کسورات</td>
                    <td align='left'>{total_deductions:,.0f} ریال</td>
                </tr>
            </table>
            
            <hr>
            <div style='text-align: center;'>
                <h3 style='color: #27ae60;'>💵 خالص پرداختی: {net_salary:,.0f} ریال</h3>
                <p style='color: {status_color}; font-weight: bold;'>وضعیت: {status_text}</p>
            </div>
            <hr>
            <p style='text-align: center; color: #888; font-size: 8pt;'>این فیش به صورت سیستمی صادر شده است.</p>
        </div>
        """
        return html
    
    # ========== عملیات پرسنل ==========
    
    def new_employee(self):
        if not self.check_employee_limit():
            return
        dialog = EmployeeDialog(customer_name=self.customer_name)
        if dialog.exec_():
            self.load_employees()
            QMessageBox.information(self, "موفق", "✅ پرسنل جدید ایجاد شد!")
    
    def edit_employee(self):
        row = self.payroll_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک پرسنل را انتخاب کنید!")
            return
        emp = self.employees_data[row]
        dialog = EmployeeDialog(emp['id'], customer_name=self.customer_name)
        if dialog.exec_():
            self.load_employees()
            QMessageBox.information(self, "موفق", "✅ پرسنل ویرایش شد!")
    
    def delete_employee(self):
        row = self.payroll_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک پرسنل را انتخاب کنید!")
            return
        emp = self.employees_data[row]
        reply = QMessageBox.question(self, "تأیید حذف", f"آیا از حذف '{emp['name']}' اطمینان دارید؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('DELETE FROM payrolls WHERE employee_id = ?', [emp['id']])
                c.execute('DELETE FROM employees WHERE id = ?', [emp['id']])
            self.load_employees()
            QMessageBox.information(self, "موفق", "✅ پرسنل حذف شد!")
    
    def check_employee_limit(self):
        if self.customer_name:
            allowed, current, limit, msg = ModuleLimitHelper.check_module_limit(self.customer_name, 'payroll')
            if not allowed:
                QMessageBox.warning(self, "خطا", f"❌ به سقف مجاز {limit} پرسنل رسیده‌اید!")
                return False
        return True
    
    # ========== عملیات حقوق ==========
    
    def calculate_payroll(self):
        row = self.payroll_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک پرسنل را انتخاب کنید!")
            return
        emp = self.employees_data[row]
        self.calculate_single_payroll(emp['id'])
    
    def calculate_single_payroll(self, employee_id):
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM employees WHERE id = ?', [employee_id])
            emp = c.fetchone()
        
        benefit_items, deduction_items = self._get_payroll_items()
        all_items = benefit_items + deduction_items
        columns_to_check = [item['code'].lower() for item in all_items if item['code']]
        self._ensure_payroll_column(columns_to_check)

        dialog = PayrollCalculateDialog(emp, year, month, parent=self)
        if dialog.exec_():
            self.load_payroll()
            self.view_payslip(employee_id)
            QMessageBox.information(self, "موفق", "✅ حقوق محاسبه شد!")
    
    def register_payment(self):
        row = self.payroll_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک پرسنل را انتخاب کنید!")
            return
        
        emp = self.employees_data[row]
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM payrolls WHERE employee_id = ? AND year = ? AND month = ?',
                     [emp['id'], year, month])
            payroll = c.fetchone()
            
            if not payroll:
                QMessageBox.warning(self, "خطا", "ابتدا فیش حقوقی محاسبه شود!")
                return
            
            if payroll['payment_status'] == 'paid':
                QMessageBox.information(self, "توجه", "این فیش قبلاً پرداخت شده!")
                return
            
            net_salary = payroll['net_salary'] or 0
            today_display = get_today_jalali()
            
            reply = QMessageBox.question(self, "تأیید پرداخت",
                f"آیا پرداخت حقوق {emp['name']} به مبلغ {net_salary:,.0f} ریال تأیید می‌شود؟\nتاریخ: {today_display}",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                today_gregorian = datetime.now().strftime("%Y-%m-%d")
                c.execute('UPDATE payrolls SET payment_status = "paid", payment_date = ? WHERE id = ?',
                         [today_gregorian, payroll['id']])
                conn.commit()
                self.load_payroll()
                self.view_payslip(emp['id'])
                QMessageBox.information(self, "موفق", "✅ پرداخت ثبت شد!")
    
    def show_insurance_list(self):
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        dialog = InsuranceReportDialog(year, month, self)
        dialog.exec_()
    
    def export_to_excel(self):
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        
        file_name, _ = QFileDialog.getSaveFileName(self, "ذخیره لیست حقوق",
            f"payroll_list_{year}_{month_names[month-1]}.csv", "CSV Files (*.csv)")
        
        if not file_name:
            return
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT e.code, e.name, p.net_salary, p.payment_status, p.payment_date
                FROM payrolls p
                JOIN employees e ON p.employee_id = e.id
                WHERE p.year = ? AND p.month = ?
                ORDER BY e.code
            ''', [year, month])
            data = c.fetchall()
        
        with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["کد پرسنلی", "نام", "خالص پرداختی", "تاریخ پرداخت", "وضعیت"])
            
            total_net = 0
            for row in data:
                payment_date = safe_display_date(row['payment_date']) if row['payment_date'] else "-"
                writer.writerow([row['code'], row['name'], f"{row['net_salary']:,}",
                                payment_date, "پرداخت شده" if row['payment_status'] == 'paid' else "در انتظار"])
                total_net += row['net_salary'] or 0
            
            writer.writerow([])
            writer.writerow(["جمع کل", "", f"{total_net:,}", "", ""])
        
        QMessageBox.information(self, "موفق", f"✅ لیست حقوق ذخیره شد:\n{file_name}")
    
    def refresh_payroll_items(self):
        try:
            self.payroll_items_widget.load_items()
            self.load_payroll()
            QMessageBox.information(self, "موفق", "✅ اقلام حقوق بروزرسانی شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا: {str(e)}")
    
    # ========== چاپ و خروجی PDF ==========
    
    def print_payslip(self):
        """نمایش دیالوگ برای انتخاب چاپ فیزیکی یا خروجی PDF"""
        if not self.payslip_text.toPlainText().strip() or "ثبت نشده است" in self.payslip_text.toPlainText():
            QMessageBox.warning(self, "خطا", "ابتدا یک فیش حقوقی محاسبه شده را انتخاب کنید!")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("انتخاب روش خروجی")
        dialog.setFixedSize(self.scaled(350), self.scaled(180))
        dialog.setStyleSheet("""
            QDialog { background-color: #f8f9fa; }
            QLabel { font-size: 11pt; font-weight: bold; color: #2C3E50; margin-bottom: 10px; }
            QPushButton { font-size: 10pt; padding: 10px; border-radius: 5px; border: none; }
            QPushButton:hover { opacity: 0.9; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        
        title_label = QLabel("📄 فیش حقوقی آماده است. روش خروجی را انتخاب کنید:")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        print_btn = QPushButton("🖨️ چاپ")
        print_btn.setStyleSheet("background-color: #3498db; color: white;")
        print_btn.clicked.connect(lambda: self._handle_print_choice(dialog, 'print'))
        btn_layout.addWidget(print_btn)
        
        pdf_btn = QPushButton("📄 خروجی PDF")
        pdf_btn.setStyleSheet("background-color: #27ae60; color: white;")
        pdf_btn.clicked.connect(lambda: self._handle_print_choice(dialog, 'pdf'))
        btn_layout.addWidget(pdf_btn)
        
        layout.addLayout(btn_layout)
        
        cancel_btn = QPushButton("انصراف")
        cancel_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)
        
        dialog.exec_()
    
    def _handle_print_choice(self, dialog, choice):
        """مدیریت عملیات پس از انتخاب کاربر در دیالوگ"""
        dialog.accept()
        
        if choice == 'print':
            self._print_physical()
        elif choice == 'pdf':
            self._export_pdf()
    
    def _print_physical(self):
        """چاپ فیزیکی فیش حقوقی"""
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)
        
        print_dialog = QPrintDialog(printer, self)
        print_dialog.setWindowTitle("چاپ فیش حقوقی")
        
        if print_dialog.exec_() == QPrintDialog.Accepted:
            try:
                doc = QTextDocument()
                doc.setHtml(self.payslip_text.toHtml())
                doc.setPageSize(printer.pageRect().size())
                doc.print_(printer)
                QMessageBox.information(self, "موفق", "✅ فیش حقوقی با موفقیت چاپ شد!")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"❌ خطا در چاپ:\n{str(e)}")
    
    def _export_pdf(self):
        """خروجی PDF با استفاده از ReportLab - رسم جدول و متن فارسی"""
        
        if not self.payslip_text.toPlainText().strip() or "ثبت نشده است" in self.payslip_text.toPlainText():
            QMessageBox.warning(self, "خطا", "فیش حقوقی برای خروجی یافت نشد!")
            return
        
        # دریافت اطلاعات پرسنل از فرم
        emp_name = self.emp_name.text() or "-"
        emp_code = self.emp_code.text() or "-"
        emp_position = "مدیر سیستم"  # اگر سمت را ندارید، می‌توانید از دیتابیس بخوانید
        payment_date = "1405/06/15"
        
        file_name, _ = QFileDialog.getSaveFileName(self, "ذخیره فیش حقوقی",
            f"payslip_{emp_code}_{datetime.now().strftime('%Y%m%d')}.pdf", "PDF Files (*.pdf)")
        
        if not file_name:
            return
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_RIGHT, TA_CENTER
            import arabic_reshaper
            from bidi.algorithm import get_display
            import os
            
            # ========== ثبت فونت ==========
            # مسیر فونت را به پوشه پروژه تغییر دهید (حتماً فایل tahoma.ttf را در پوشه fonts کپی کنید)
            font_path = "fonts/tahoma.ttf" 
            if not os.path.exists(font_path):
                # اگر فونت در پوشه پروژه نبود، از مسیر ویندوز استفاده کنید (ممکن است کیفیت پایین‌تر باشد)
                font_path = "C:/Windows/Fonts/tahoma.ttf"
            
            pdfmetrics.registerFont(TTFont('PersianFont', font_path))
            
            # ========== توابع تبدیل متن فارسی ==========
            def fa(text):
                """تبدیل متن فارسی به شکل صحیح برای ReportLab"""
                if text is None:
                    text = ""
                reshaped = arabic_reshaper.reshape(str(text))
                return get_display(reshaped)
            
            # ========== تنظیمات استایل ==========
            styles = getSampleStyleSheet()
            right_style = ParagraphStyle(
                'Right', parent=styles['Normal'], 
                fontName='PersianFont', fontSize=10, 
                alignment=TA_RIGHT, leading=16
            )
            center_style = ParagraphStyle(
                'Center', parent=styles['Normal'], 
                fontName='PersianFont', fontSize=12, 
                alignment=TA_CENTER, leading=18
            )
            
            # ========== ساخت سند PDF ==========
            doc = SimpleDocTemplate(file_name, pagesize=A4, 
                                    rightMargin=20*mm, leftMargin=20*mm, 
                                    topMargin=20*mm, bottomMargin=20*mm)
            
            elements = []
            
            # هدر
            elements.append(Paragraph(fa("شرکت حسابداری پارسه"), center_style))
            elements.append(Paragraph(fa("فیش حقوقی"), center_style))
            elements.append(Spacer(1, 10))
            
            # اطلاعات پرسنل
            info_table_data = [
                [Paragraph(fa(f"نام: {emp_name}"), right_style), Paragraph(fa(f"کد پرسنلی: {emp_code}"), right_style)],
                [Paragraph(fa(f"سمت: {emp_position}"), right_style), Paragraph(fa(f"تاریخ پرداخت: {payment_date}"), right_style)],
            ]
            
            info_table = Table(info_table_data, colWidths=[doc.width/2.0]*2)
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'PersianFont'),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 15))
            
            # ========== جدول حقوق و مزایا ==========
            # این مقادیر را می‌توانید از self.payroll (دیکشنری) بخوانید
            benefits = [
                ("حقوق و مزایا", "مبلغ (ریال)"),
                ("حقوق پایه", "12,000,000"),
                ("حق اولاد", "0"),
                ("جمعه کاری", "0"),
                ("حق مسکن", "15,000,000"),
                ("بن کارگری", "14,000,000"),
                ("حق ماموریت", "0"),
                ("شب کاری", "0"),
                ("اضافه کاری", "0"),
                ("حق مسئولیت", "0"),
                ("پایه سنوات", "0"),
                ("نوبت کاری", "0"),
                ("حق همسر", "0"),
            ]
            
            # محاسبه جمع
            total_benefits = sum(int(x[1].replace(',', '')) for x in benefits[1:])
            benefits.append(("جمع حقوق و مزایا", f"{total_benefits:,}"))
            
            table_data = [[Paragraph(fa(col), right_style) for col in row] for row in benefits]
            benefit_table = Table(table_data, colWidths=[doc.width*0.7, doc.width*0.3])
            benefit_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'PersianFont'),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.85, 0.9, 0.95)),
                ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 1, 0.9)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(Paragraph(fa("💰 حقوق و مزایا:"), right_style))
            elements.append(benefit_table)
            elements.append(Spacer(1, 15))
            
            # ========== جدول کسورات ==========
            deductions = [
                ("کسورات", "مبلغ (ریال)"),
                ("مساعده", "0"),
                ("سایر کسورات", "0"),
                ("بیمه سهم کارمند", "4,228,000"),
                ("قسط وام", "0"),
                ("جریمه", "0"),
                ("مالیات بر درآمد", "4,040,000"),
            ]
            
            total_deductions = sum(int(x[1].replace(',', '')) for x in deductions[1:])
            deductions.append(("جمع کسورات", f"{total_deductions:,}"))
            
            table_data_ded = [[Paragraph(fa(col), right_style) for col in row] for row in deductions]
            deduction_table = Table(table_data_ded, colWidths=[doc.width*0.7, doc.width*0.3])
            deduction_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'PersianFont'),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(1, 0.9, 0.9)),
                ('BACKGROUND', (0, -1), (-1, -1), colors.Color(1, 0.9, 0.9)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(Paragraph(fa("📉 کسورات:"), right_style))
            elements.append(deduction_table)
            elements.append(Spacer(1, 15))
            
            # ========== خالص پرداختی ==========
            net_salary = 52_132_000
            net_para = Paragraph(fa(f"💵 خالص پرداختی: {net_salary:,} ریال"), 
                                 ParagraphStyle('Net', parent=right_style, fontSize=14, textColor=colors.green))
            elements.append(net_para)
            
            # ساخت و ذخیره نهایی
            doc.build(elements)
            
            QMessageBox.information(self, "موفق", f"✅ فایل PDF با موفقیت ذخیره شد:\n{file_name}")
            
        except ImportError:
            QMessageBox.critical(self, "خطا", "کتابخانه‌های گزارش‌گیری نصب نشده‌اند!\nبرای نصب: pip install reportlab arabic-reshaper python-bidi")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"❌ خطا در تولید PDF:\n{str(e)}")
