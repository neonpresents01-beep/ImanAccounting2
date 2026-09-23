# payroll_components.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# ============================================================
# کلاس فیلد ورودی مبالغ ریالی
# ============================================================
class MoneyLineEdit(QLineEdit):
    """فیلد ورودی مخصوص مبالغ ریالی با فرمت خودکار جداکننده هزارگان"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignRight)
        self.setPlaceholderText("مبلغ به ریال")
        self.textChanged.connect(self._format_text)
        self._current_value = 0
        
    def _format_text(self):
        text = self.text().strip()
        if not text:
            self._current_value = 0
            return
            
        digits = ''.join(filter(str.isdigit, text))
        if not digits:
            self._current_value = 0
            self.blockSignals(True)
            self.setText("")
            self.blockSignals(False)
            return
            
        self._current_value = int(digits)
        formatted = f"{self._current_value:,}"
        
        self.blockSignals(True)
        self.setText(formatted)
        self.blockSignals(False)
        
    def value(self) -> int:
        return self._current_value
        
    def setValue(self, value: int):
        self._current_value = value if value else 0
        self.blockSignals(True)
        self.setText(f"{self._current_value:,}" if self._current_value > 0 else "")
        self.blockSignals(False)


# ============================================================
# کلاس دیالوگ محاسبه حقوق
# ============================================================
class PayrollCalculateDialog(QDialog):
    """دیالوگ محاسبه حقوق ماهانه با تمام اقلام"""
    
    def __init__(self, employee, year, month, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.year = year
        self.month = month
        self.setWindowTitle(f"🧮 محاسبه حقوق {employee['name']}")
        self.setGeometry(350, 200, 600, 700)
        self.init_ui()
        self.load_existing_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # عنوان
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        title = QLabel(f"<h3>{self.employee['name']} - {month_names[self.month-1]} {self.year}</h3>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # فرم ورودی
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        
        # اطلاعات پایه
        self.work_days = QSpinBox()
        self.work_days.setRange(0, 31)
        self.work_days.setValue(30)
        self.work_days.setSuffix(" روز")
        form_layout.addRow("روز کارکرد:", self.work_days)
        
        self.overtime_hours = QDoubleSpinBox()
        self.overtime_hours.setRange(0, 300)
        self.overtime_hours.setSingleStep(1)
        self.overtime_hours.setDecimals(1)
        self.overtime_hours.setSuffix(" ساعت")
        form_layout.addRow("اضافه کاری:", self.overtime_hours)
        
        self.night_hours = QDoubleSpinBox()
        self.night_hours.setRange(0, 300)
        self.night_hours.setSingleStep(1)
        self.night_hours.setDecimals(1)
        self.night_hours.setSuffix(" ساعت")
        form_layout.addRow("شب کاری:", self.night_hours)
        
        self.friday_hours = QDoubleSpinBox()
        self.friday_hours.setRange(0, 100)
        self.friday_hours.setSingleStep(1)
        self.friday_hours.setDecimals(1)
        self.friday_hours.setSuffix(" ساعت")
        form_layout.addRow("جمعه کاری:", self.friday_hours)
        
        self.shift_days = QSpinBox()
        self.shift_days.setRange(0, 31)
        self.shift_days.setSuffix(" روز")
        form_layout.addRow("نوبت کاری:", self.shift_days)
        
        # خط جداکننده
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        form_layout.addRow(line)
        
        # پاداش‌ها
        self.bonus = MoneyLineEdit()
        form_layout.addRow("پاداش:", self.bonus)
        
        self.performance_bonus = MoneyLineEdit()
        form_layout.addRow("پاداش عملکرد:", self.performance_bonus)
        
        self.mission_allowance = MoneyLineEdit()
        form_layout.addRow("حق ماموریت:", self.mission_allowance)
        
        # خط جداکننده
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        form_layout.addRow(line2)
        
        # کسورات
        self.advance_payment = MoneyLineEdit()
        form_layout.addRow("مساعده:", self.advance_payment)
        
        self.deduction = MoneyLineEdit()
        form_layout.addRow("سایر کسورات:", self.deduction)
        
        layout.addWidget(form_widget)
        
        # پیش‌نمایش
        preview_group = QGroupBox("📊 پیش‌نمایش محاسبه")
        preview_layout = QVBoxLayout()
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(250)
        self.preview_text.setStyleSheet("font-family: monospace; font-size: 10pt;")
        preview_layout.addWidget(self.preview_text)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        calc_btn = QPushButton("🧮 محاسبه")
        calc_btn.clicked.connect(self.calculate)
        btn_layout.addWidget(calc_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("background-color: #4CAF50;")
        save_btn.clicked.connect(self.save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # اتصال رویدادها
        self.work_days.valueChanged.connect(self.calculate)
        self.overtime_hours.valueChanged.connect(self.calculate)
        self.night_hours.valueChanged.connect(self.calculate)
        self.friday_hours.valueChanged.connect(self.calculate)
        self.shift_days.valueChanged.connect(self.calculate)
        self.bonus.textChanged.connect(self.calculate)
        self.performance_bonus.textChanged.connect(self.calculate)
        self.mission_allowance.textChanged.connect(self.calculate)
        self.advance_payment.textChanged.connect(self.calculate)
        self.deduction.textChanged.connect(self.calculate)
    
    def load_existing_data(self):
        """بارگذاری داده‌های موجود (برای ویرایش)"""
        from database import get_db
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM payrolls 
                WHERE employee_id = ? AND year = ? AND month = ?
            ''', [self.employee['id'], self.year, self.month])
            payroll = c.fetchone()
            
            if payroll:
                self.work_days.setValue(payroll['work_days'] or 30)
                self.overtime_hours.setValue(payroll['overtime_hours'] or 0)
                self.night_hours.setValue(payroll['night_work_hours'] or 0)
                self.friday_hours.setValue(payroll['friday_work_hours'] or 0)
                self.shift_days.setValue(payroll['shift_days'] or 0)
                self.bonus.setValue(payroll['bonus'] or 0)
                self.performance_bonus.setValue(0)
                self.mission_allowance.setValue(payroll['mission_allowance'] or 0)
                self.advance_payment.setValue(payroll['advance_payment'] or 0)
                self.deduction.setValue(payroll['deduction'] or 0)
        
        self.calculate()
    
    def calculate(self):
        """محاسبه و نمایش پیش‌نمایش"""
        from additional.payroll_calculator import PayrollCalculator
        
        calculator = PayrollCalculator(self.employee['id'], self.year, self.month)
        
        result = calculator.calculate(
            work_days=self.work_days.value(),
            overtime_hours=self.overtime_hours.value(),
            night_hours=self.night_hours.value(),
            friday_hours=self.friday_hours.value(),
            shift_days=self.shift_days.value(),
            bonus=self.bonus.value(),
            performance_bonus=self.performance_bonus.value(),
            mission_allowance=self.mission_allowance.value(),
            advance_payment=self.advance_payment.value(),
            deduction=self.deduction.value()
        )
        
        if result:
            self.current_result = result
            
            preview = f"""
            ═══════════════════════════════════════════════════════
            📊 جزئیات محاسبه حقوق {self.employee['name']}
            ═══════════════════════════════════════════════════════
            
            🟢 حقوق و مزایا:
            ───────────────────────────────────────────────────────
            • حقوق پایه کارکرد ({self.work_days.value()} روز):     {result['base_salary']:>15,} ریال
            • اضافه کاری ({self.overtime_hours.value()} ساعت):     {result['overtime_pay']:>15,} ریال
            • شب کاری ({self.night_hours.value()} ساعت):           {result['night_work_pay']:>15,} ریال
            • جمعه کاری ({self.friday_hours.value()} ساعت):        {result['friday_work_pay']:>15,} ریال
            • نوبت کاری ({self.shift_days.value()} روز):           {result['shift_allowance']:>15,} ریال
            • حق اولاد ({self.employee['child_count']} فرزند):     {result['child_allowance']:>15,} ریال
            • حق همسر:                                             {result['spouse_allowance']:>15,} ریال
            • بن خواربار:                                          {result['meal_allowance']:>15,} ریال
            • کمک هزینه مسکن:                                      {result['housing_allowance']:>15,} ریال
            • پایه سنوات:                                          {result['seniority_pay']:>15,} ریال
            • حق مسئولیت:                                          {result['responsibility_pay']:>15,} ریال
            • پاداش:                                               {result['bonus']:>15,} ریال
            • حق ماموریت:                                          {result['mission_allowance']:>15,} ریال
            ───────────────────────────────────────────────────────
            جمع حقوق و مزایا:                                      {result['gross_salary']:>15,} ریال
            
            🔴 کسورات:
            ───────────────────────────────────────────────────────
            • بیمه (سهم کارمند):                                   {result['insurance_employee']:>15,} ریال
            • مالیات:                                              {result['tax']:>15,} ریال
            • قسط وام:                                             {result['loan_installment']:>15,} ریال
            • مساعده:                                              {result['advance_payment']:>15,} ریال
            • سایر کسورات:                                         {result['deduction']:>15,} ریال
            ───────────────────────────────────────────────────────
            جمع کسورات:                                            {result['gross_salary'] - result['net_salary']:>15,} ریال
            
            ═══════════════════════════════════════════════════════
            💵 خالص پرداختی:                                       {result['net_salary']:>15,} ریال
            ═══════════════════════════════════════════════════════
            """
            
            self.preview_text.setText(preview)
    
    def save(self):
        """ذخیره فیش حقوقی"""
        if not hasattr(self, 'current_result'):
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا محاسبه را انجام دهید!")
            return
        
        from database import get_db
        from additional.payroll_calculator import PayrollCalculator
        
        calculator = PayrollCalculator(self.employee['id'], self.year, self.month)
        calculator.save(self.current_result)
        
        QMessageBox.information(self, "موفق", "✅ فیش حقوقی با موفقیت ذخیره شد!")
        self.accept()


# ============================================================
# کلاس دیالوگ لیست بیمه تأمین اجتماعی
# ============================================================
class InsuranceReportDialog(QDialog):
    """دیالوگ نمایش و خروجی لیست بیمه"""
    
    def __init__(self, year, month, parent=None):
        super().__init__(parent)
        self.year = year
        self.month = month
        self.setWindowTitle(f"📄 لیست بیمه تأمین اجتماعی - {year}/{month}")
        self.setGeometry(200, 200, 900, 500)
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # عنوان
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        title = QLabel(f"📄 لیست بیمه تأمین اجتماعی - {month_names[self.month-1]} {self.year}")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # جدول
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "کد پرسنلی", "نام", "کد بیمه", "حقوق مشمول", 
            "سهم کارمند (۷%)", "سهم کارفرما (۲۳%)", "بیمه بیکاری", "جمع", "وضعیت"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # جمع
        self.total_label = QLabel()
        self.total_label.setStyleSheet("font-weight: bold; padding: 10px; background: #f0f0f0;")
        layout.addWidget(self.total_label)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        
        export_btn = QPushButton("📎 خروجی Excel")
        export_btn.clicked.connect(self.export_to_excel)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("✖️ بستن")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def load_data(self):
        from database import get_db
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT e.code, e.name, e.insurance_code, p.gross_salary, 
                       p.insurance_employee, p.insurance_employer,
                       p.payment_status
                FROM payrolls p
                JOIN employees e ON p.employee_id = e.id
                WHERE p.year = ? AND p.month = ?
                ORDER BY e.code
            ''', [self.year, self.month])
            
            data = c.fetchall()
        
        self.table.setRowCount(len(data))
        
        total_employee = 0
        total_employer = 0
        
        for i, row in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(row['code'] or "-"))
            self.table.setItem(i, 1, QTableWidgetItem(row['name'] or "-"))
            self.table.setItem(i, 2, QTableWidgetItem(row['insurance_code'] or "-"))
            
            gross_item = QTableWidgetItem(f"{row['gross_salary']:,.0f}")
            gross_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 3, gross_item)
            
            emp_item = QTableWidgetItem(f"{row['insurance_employee']:,.0f}")
            emp_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 4, emp_item)
            
            employer_item = QTableWidgetItem(f"{row['insurance_employer']:,.0f}")
            employer_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 5, employer_item)
            
            unemployment = int(row['insurance_employee'] * 0.03) if row['insurance_employee'] else 0
            unemp_item = QTableWidgetItem(f"{unemployment:,.0f}")
            unemp_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 6, unemp_item)
            
            total = (row['insurance_employee'] or 0) + (row['insurance_employer'] or 0) + unemployment
            total_item = QTableWidgetItem(f"{total:,.0f}")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 7, total_item)
            
            status = "✅ محاسبه شده" if row['payment_status'] == 'paid' else "⏳ در انتظار"
            status_item = QTableWidgetItem(status)
            if row['payment_status'] == 'paid':
                status_item.setForeground(QColor('#4CAF50'))
            else:
                status_item.setForeground(QColor('#FF9800'))
            self.table.setItem(i, 8, status_item)
            
            total_employee += row['insurance_employee'] or 0
            total_employer += row['insurance_employer'] or 0
        
        self.total_label.setText(
            f"📊 جمع سهم بیمه کارمندان: {total_employee:,.0f} ریال | "
            f"جمع سهم بیمه کارفرما: {total_employer:,.0f} ریال | "
            f"جمع کل قابل پرداخت: {total_employee + total_employer:,.0f} ریال"
        )
    
    def export_to_excel(self):
        """خروجی به فرمت CSV"""
        import csv
        from datetime import datetime
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره لیست بیمه", 
            f"insurance_list_{self.year}_{self.month}_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not file_name:
            return
        
        with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            # هدر
            headers = ["کد پرسنلی", "نام", "کد بیمه", "حقوق مشمول", 
                      "سهم کارمند (۷%)", "سهم کارفرما (۲۳%)", "بیمه بیکاری", "جمع"]
            writer.writerow(headers)
            
            # داده‌ها
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(7):  # فقط ستون‌های عددی
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                writer.writerow(row_data)
        
        QMessageBox.information(self, "موفق", f"✅ لیست بیمه در مسیر زیر ذخیره شد:\n{file_name}")
