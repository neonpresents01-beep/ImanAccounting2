# -*- coding: utf-8 -*-
"""
کامپوننت‌های حقوق و دستمزد - نسخه نهایی
پشتیبانی کامل از screen_utils، تم پویا و QScrollArea
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from screen_utils import ScreenManager
from shamsi_date import get_today_jalali
from database import get_db
from additional.payroll_calculator import PayrollCalculator

import csv
from datetime import datetime


# ============================================================
# کلاس ۱: MoneyLineEdit (ورودی مبلغ با فرمت هزارگان)
# ============================================================

class MoneyLineEdit(QLineEdit):
    """فیلد ورودی مبالغ ریالی با فرمت خودکار جداکننده هزارگان"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.screen_manager = ScreenManager()
        self._current_value = 0

        self.setAlignment(Qt.AlignRight)
        self.setPlaceholderText("مبلغ به ریال")
        self.textChanged.connect(self._format_text)

        self._apply_style()

    def _apply_style(self):
        fs = self.screen_manager.get_font_size(10)
        padding = self.screen_manager.get_scaled(8)
        min_h = self.screen_manager.get_scaled(32)
        self.setStyleSheet(f"""
            QLineEdit {{
                padding: {padding}px;
                font-size: {fs}pt;
                border: 1px solid #dcdde1;
                border-radius: {self.screen_manager.get_scaled(6)}px;
                background-color: white;
                min-height: {min_h}px;
            }}
            QLineEdit:focus {{
                border-color: #273c75;
            }}
        """)

    def _format_text(self):
        text = self.text().replace(',', '').strip()
        if not text:
            self._current_value = 0
            return

        if text.isdigit():
            self._current_value = int(text)
            formatted = f"{self._current_value:,}"
            if formatted != self.text():
                self.blockSignals(True)
                self.setText(formatted)
                self.blockSignals(False)
        else:
            # حذف کاراکترهای غیرعددی
            digits = ''.join(filter(str.isdigit, text))
            if digits:
                self._current_value = int(digits)
                self.blockSignals(True)
                self.setText(f"{self._current_value:,}")
                self.blockSignals(False)

    def get_value(self) -> int:
        """دریافت مقدار عددی"""
        return self._current_value

    def setValue(self, value: int):
        """تنظیم مقدار عددی"""
        self._current_value = value if value else 0
        self.blockSignals(True)
        self.setText(f"{self._current_value:,}" if self._current_value > 0 else "")
        self.blockSignals(False)

    def clear(self):
        self._current_value = 0
        super().clear()

    def value(self) -> int:
        """Alias برای get_value (سازگاری با کدهای قدیمی)"""
        return self.get_value()
    def set_value(self,value:int):
        """تنظیم مقدار عددی"""
        self._current_value = value if value else 0
        self.blockSignals(True)
        self.setText(f"{self._current_value:,}" if self._current_value > 0 else "")
        self.blockSignals(False)
        
# ============================================================
# کلاس ۲: PayrollCalculateDialog (دیالوگ محاسبه حقوق)
# ============================================================

class PayrollCalculateDialog(QDialog):
    """دیالوگ محاسبه حقوق ماهانه با پشتیبانی از اسکرول و تم"""

    def __init__(self, employee, year, month, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.year = year
        self.month = month
        self.screen_manager = ScreenManager()
        self.is_small = self.screen_manager.is_small_screen()
        self._last_result = None

        self.setWindowTitle("🧮 محاسبه حقوق ماهانه")
        self.setModal(True)

        w, h = self.screen_manager.get_scaled_size(750, 650)
        self.setGeometry(200, 200, w, h)

        self.init_ui()
        self.load_existing_data()
        self.apply_styles()

    # ======================== UI ========================

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        spacing = self.screen_manager.get_spacing(10)
        margin = self.screen_manager.get_margin(15)
        main_layout.setSpacing(spacing)
        main_layout.setContentsMargins(margin, margin, margin, margin)

        # ---------- هدر ----------
        header = QLabel(f"🧮 محاسبه حقوق - {self.employee['name']}")
        header.setStyleSheet(f"""
            font-size: {self.screen_manager.get_font_size(14)}pt;
            font-weight: bold;
            color: #273c75;
            padding: {self.screen_manager.get_scaled(10)}px;
            background: #e8f0fe;
            border-radius: {self.screen_manager.get_scaled(8)}px;
        """)
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # ---------- اسکرول ----------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: #f0f0f0;
                width: {self.screen_manager.get_scaled(10)}px;
                border-radius: {self.screen_manager.get_scaled(5)}px;
            }}
            QScrollBar::handle:vertical {{
                background: #273c75;
                border-radius: {self.screen_manager.get_scaled(5)}px;
                min-height: {self.screen_manager.get_scaled(30)}px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        # ---------- محتوای اسکرول ----------
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(self.screen_manager.get_spacing(10))

        # ---- اطلاعات پرسنل ----
        info_group = QGroupBox("📋 اطلاعات پرسنل")
        info_group.setStyleSheet(self._group_style())
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(self.screen_manager.get_spacing(8))
        info_layout.setLabelAlignment(Qt.AlignRight)

        fs = self.screen_manager.get_font_size(10)

        self.lbl_code = QLabel(self.employee['code'])
        self.lbl_code.setStyleSheet(f"font-weight: bold; font-size: {fs}pt;")
        info_layout.addRow("کد پرسنلی:", self.lbl_code)

        self.lbl_name = QLabel(self.employee['name'])
        self.lbl_name.setStyleSheet(f"font-weight: bold; font-size: {fs}pt;")
        info_layout.addRow("نام:", self.lbl_name)

        self.lbl_salary = QLabel(f"{self.employee['base_salary']:,.0f} ریال")
        self.lbl_salary.setStyleSheet(f"font-weight: bold; color: #27ae60; font-size: {fs}pt;")
        info_layout.addRow("حقوق پایه:", self.lbl_salary)

        content_layout.addWidget(info_group)

        # ---- فرم پارامترها ----
        form_group = QGroupBox("📊 پارامترهای محاسبه")
        form_group.setStyleSheet(self._group_style())
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(self.screen_manager.get_spacing(8))
        form_layout.setLabelAlignment(Qt.AlignRight)

        # دو ستون
        if self.is_small:
            cols_layout = QVBoxLayout()
        else:
            cols_layout = QHBoxLayout()

        # ستون چپ
        left = QWidget()
        left_layout = QFormLayout(left)
        left_layout.setSpacing(self.screen_manager.get_spacing(8))
        left_layout.setLabelAlignment(Qt.AlignRight)

        self.work_days = QSpinBox()
        self.work_days.setRange(0, 31)
        self.work_days.setValue(26)
        self.work_days.setMinimumHeight(self.screen_manager.get_scaled(32))
        left_layout.addRow("روز کارکرد:", self.work_days)

        self.overtime = QDoubleSpinBox()
        self.overtime.setRange(0, 100)
        self.overtime.setDecimals(1)
        self.overtime.setValue(0)
        self.overtime.setMinimumHeight(self.screen_manager.get_scaled(32))
        left_layout.addRow("ساعت اضافه کاری:", self.overtime)

        self.night_work = QDoubleSpinBox()
        self.night_work.setRange(0, 100)
        self.night_work.setDecimals(1)
        self.night_work.setValue(0)
        self.night_work.setMinimumHeight(self.screen_manager.get_scaled(32))
        left_layout.addRow("ساعت شب کاری:", self.night_work)

        self.friday_work = QDoubleSpinBox()
        self.friday_work.setRange(0, 100)
        self.friday_work.setDecimals(1)
        self.friday_work.setValue(0)
        self.friday_work.setMinimumHeight(self.screen_manager.get_scaled(32))
        left_layout.addRow("ساعت جمعه کاری:", self.friday_work)

        self.shift_days = QSpinBox()
        self.shift_days.setRange(0, 31)
        self.shift_days.setValue(0)
        self.shift_days.setMinimumHeight(self.screen_manager.get_scaled(32))
        left_layout.addRow("روز نوبت کاری:", self.shift_days)

        # ستون راست
        right = QWidget()
        right_layout = QFormLayout(right)
        right_layout.setSpacing(self.screen_manager.get_spacing(8))
        right_layout.setLabelAlignment(Qt.AlignRight)

        self.child_allowance = MoneyLineEdit()
        self.child_allowance.set_value(0)
        right_layout.addRow("حق اولاد:", self.child_allowance)

        self.spouse_allowance = MoneyLineEdit()
        self.spouse_allowance.set_value(0)
        right_layout.addRow("حق همسر:", self.spouse_allowance)

        self.meal_allowance = MoneyLineEdit()
        self.meal_allowance.set_value(0)
        right_layout.addRow("بن کارگری:", self.meal_allowance)

        self.housing_allowance = MoneyLineEdit()
        self.housing_allowance.set_value(0)
        right_layout.addRow("کمک هزینه مسکن:", self.housing_allowance)

        self.loan_installment = MoneyLineEdit()
        self.loan_installment.set_value(0)
        right_layout.addRow("قسط وام:", self.loan_installment)

        self.advance_payment = MoneyLineEdit()
        self.advance_payment.set_value(0)
        right_layout.addRow("مساعده:", self.advance_payment)

        self.penalty = MoneyLineEdit()
        self.penalty.set_value(0)
        right_layout.addRow("جریمه:", self.penalty)

        cols_layout.addWidget(left)
        cols_layout.addWidget(right)
        form_layout.addRow(cols_layout)

        content_layout.addWidget(form_group)

        # ---- دکمه محاسبه ----
        calc_btn = QPushButton("🧮 محاسبه")
        calc_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: {self.screen_manager.get_scaled(8)}px;
                padding: {self.screen_manager.get_scaled(12)}px;
                font-weight: bold;
                font-size: {self.screen_manager.get_font_size(12)}pt;
                min-height: {self.screen_manager.get_scaled(40)}px;
            }}
            QPushButton:hover {{ background-color: #7B1FA2; }}
        """)
        calc_btn.clicked.connect(self.calculate)
        content_layout.addWidget(calc_btn)

        # ---- نتیجه ----
        result_group = QGroupBox("📊 نتیجه محاسبه")
        result_group.setStyleSheet(self._group_style())
        result_layout = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(self.screen_manager.get_scaled(150))
        self.result_text.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid #ddd;
                border-radius: {self.screen_manager.get_scaled(6)}px;
                padding: {self.screen_manager.get_scaled(10)}px;
                background: #fafafa;
                font-size: {self.screen_manager.get_font_size(10)}pt;
                font-family: Tahoma;
            }}
        """)
        result_layout.addWidget(self.result_text)
        content_layout.addWidget(result_group)

        # ---- قرار دادن محتوا در اسکرول ----
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

        # ---- دکمه‌های پایین (خارج از اسکرول) ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(self.screen_manager.get_spacing(10))
        btn_layout.addStretch()

        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setStyleSheet(self._btn_style("#e74c3c"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.save_btn = QPushButton("✅ ذخیره")
        self.save_btn.setStyleSheet(self._btn_style("#4CAF50"))
        self.save_btn.clicked.connect(self.save)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(btn_layout)

    # ======================== استایل‌ها ========================

    def _group_style(self):
        fs = self.screen_manager.get_font_size(10)
        radius = self.screen_manager.get_scaled(8)
        return f"""
            QGroupBox {{
                font-weight: bold;
                font-size: {fs}pt;
                border: 2px solid #dcdde1;
                border-radius: {radius}px;
                margin-top: {self.screen_manager.get_scaled(10)}px;
                padding-top: {self.screen_manager.get_scaled(10)}px;
                background-color: white;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {self.screen_manager.get_scaled(10)}px;
                padding: 0 {self.screen_manager.get_scaled(10)}px;
                color: #273c75;
            }}
        """

    def _btn_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: {self.screen_manager.get_scaled(6)}px;
                padding: {self.screen_manager.get_scaled(10)}px {self.screen_manager.get_scaled(25)}px;
                font-weight: bold;
                font-size: {self.screen_manager.get_font_size(10)}pt;
                min-height: {self.screen_manager.get_scaled(36)}px;
            }}
            QPushButton:hover {{
                background-color: {color}CC;
            }}
            QPushButton:disabled {{
                background-color: #999;
            }}
        """

    def apply_styles(self):
        fs = self.screen_manager.get_font_size(10)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #f5f6fa;
            }}
            QLabel {{
                font-size: {fs}pt;
                color: #2C3E50;
            }}
            QSpinBox, QDoubleSpinBox, QLineEdit {{
                border: 1px solid #dcdde1;
                border-radius: {self.screen_manager.get_scaled(6)}px;
                padding: {self.screen_manager.get_scaled(5)}px;
                background-color: white;
                font-size: {fs}pt;
                min-height: {self.screen_manager.get_scaled(30)}px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
                border-color: #273c75;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)

    # ======================== منطق ========================

    def load_existing_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT * FROM payrolls
                    WHERE employee_id = ? AND year = ? AND month = ?
                ''', [self.employee['id'], self.year, self.month])
                payroll = c.fetchone()

                if payroll:
                    self.work_days.setValue(payroll['work_days'] or 0)
                    self.overtime.setValue(payroll['overtime_hours'] or 0)
                    self.night_work.setValue(payroll['night_work_hours'] or 0)
                    self.friday_work.setValue(payroll['friday_work_hours'] or 0)
                    self.shift_days.setValue(payroll['shift_days'] or 0)
                    self.child_allowance.set_value(payroll['child_allowance'] or 0)
                    self.spouse_allowance.set_value(payroll['spouse_allowance'] or 0)
                    self.meal_allowance.set_value(payroll['meal_allowance'] or 0)
                    self.housing_allowance.set_value(payroll['housing_allowance'] or 0)
                    self.loan_installment.set_value(payroll['loan_installment'] or 0)
                    self.advance_payment.set_value(payroll['advance_payment'] or 0)
                    self.penalty.set_value(payroll['penalty'] or 0)

                    self.show_result(payroll)
                    self.save_btn.setEnabled(False)
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری داده: {e}")

    def calculate(self):
        try:
            result = PayrollCalculator(
                self.employee['id'],
                self.year,
                self.month
            ).calculate(
                work_days=self.work_days.value(),
                overtime_hours=self.overtime.value(),
                night_hours=self.night_work.value(),
                friday_hours=self.friday_work.value(),
                shift_days=self.shift_days.value(),
                child_allowance=self.child_allowance.get_value(),
                spouse_allowance=self.spouse_allowance.get_value(),
                meal_allowance=self.meal_allowance.get_value(),
                housing_allowance=self.housing_allowance.get_value(),
                loan_installment=self.loan_installment.get_value(),
                advance_payment=self.advance_payment.get_value(),
                penalty=self.penalty.get_value()
            )

            if result:
                self.show_result(result)
                self._last_result = result
                self.save_btn.setEnabled(True)
            else:
                QMessageBox.warning(self, "خطا", "محاسبه با خطا مواجه شد!")

        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در محاسبه: {str(e)}")

    def show_result(self, result):
        """نمایش نتیجه به صورت HTML"""
        if isinstance(result, dict):
            html = f"""
            <div style='font-family: Tahoma; direction: rtl; padding: 5px;'>
                <h4 style='color: #273c75;'>📊 خلاصه محاسبه</h4>
                <table width='100%' style='font-size: 10pt;'>
                    <tr><td>حقوق پایه:</td><td align='left'>{result.get('base_salary', 0):,.0f} ریال</td></tr>
                    <tr><td>اضافه کاری:</td><td align='left'>{result.get('overtime_pay', 0):,.0f} ریال</td></tr>
                    <tr><td>شب کاری:</td><td align='left'>{result.get('night_work_pay', 0):,.0f} ریال</td></tr>
                    <tr><td>جمعه کاری:</td><td align='left'>{result.get('friday_work_pay', 0):,.0f} ریال</td></tr>
                    <tr><td>نوبت کاری:</td><td align='left'>{result.get('shift_allowance', 0):,.0f} ریال</td></tr>
                    <tr><td>حق اولاد:</td><td align='left'>{result.get('child_allowance', 0):,.0f} ریال</td></tr>
                    <tr><td>حق همسر:</td><td align='left'>{result.get('spouse_allowance', 0):,.0f} ریال</td></tr>
                    <tr><td>بن کارگری:</td><td align='left'>{result.get('meal_allowance', 0):,.0f} ریال</td></tr>
                    <tr><td>کمک هزینه مسکن:</td><td align='left'>{result.get('housing_allowance', 0):,.0f} ریال</td></tr>
                    <tr style='font-weight: bold; background: #e8f5e9;'>
                        <td>جمع حقوق و مزایا:</td>
                        <td align='left'>{result.get('gross_salary', 0):,.0f} ریال</td>
                    </tr>
                    <tr style='background: #ffebee;'>
                        <td>بیمه:</td><td align='left'>{result.get('insurance_employee', 0):,.0f} ریال</td></tr>
                    <tr style='background: #ffebee;'>
                        <td>مالیات:</td><td align='left'>{result.get('tax', 0):,.0f} ریال</td></tr>
                    <tr style='background: #ffebee;'>
                        <td>قسط وام:</td><td align='left'>{result.get('loan_installment', 0):,.0f} ریال</td></tr>
                    <tr style='background: #ffebee;'>
                        <td>مساعده:</td><td align='left'>{result.get('advance_payment', 0):,.0f} ریال</td></tr>
                    <tr style='background: #ffebee;'>
                        <td>جریمه:</td><td align='left'>{result.get('penalty', 0):,.0f} ریال</td></tr>
                    <tr style='font-weight: bold; background: #ffebee;'>
                        <td>جمع کسورات:</td>
                        <td align='left'>{result.get('total_deductions', 0):,.0f} ریال</td>
                    </tr>
                    <tr style='font-weight: bold; background: #e8f5e9;'>
                        <td style='font-size: 12pt; color: #27ae60;'>💵 خالص پرداختی:</td>
                        <td align='left' style='font-size: 12pt; color: #27ae60;'>{result.get('net_salary', 0):,.0f} ریال</td>
                    </tr>
                </table>
            </div>
            """
            self.result_text.setHtml(html)

    def save(self):
        if not self._last_result:
            QMessageBox.warning(self, "خطا", "ابتدا محاسبه را انجام دهید!")
            return

        try:
            with get_db() as conn:
                c = conn.cursor()

                # بررسی وجود رکورد
                c.execute('''
                    SELECT id FROM payrolls
                    WHERE employee_id = ? AND year = ? AND month = ?
                ''', [self.employee['id'], self.year, self.month])
                existing = c.fetchone()

                result = self._last_result

                if existing:
                    c.execute('''
                        UPDATE payrolls SET
                            work_days=?, overtime_hours=?, night_work_hours=?,
                            friday_work_hours=?, shift_days=?,
                            child_allowance=?, spouse_allowance=?,
                            meal_allowance=?, housing_allowance=?,
                            overtime_pay=?, night_work_pay=?, friday_work_pay=?,
                            shift_allowance=?, gross_salary=?, 
                            insurance_employee=?, tax=?, loan_installment=?,
                            advance_payment=?, deduction=?, penalty=?,
                            net_salary=?
                        WHERE id=?
                    ''', [
                        result.get('work_days', 0),
                        result.get('overtime_hours', 0),
                        result.get('night_work_hours', 0),
                        result.get('friday_work_hours', 0),
                        result.get('shift_days', 0),
                        result.get('child_allowance', 0),
                        result.get('spouse_allowance', 0),
                        result.get('meal_allowance', 0),
                        result.get('housing_allowance', 0),
                        result.get('overtime_pay', 0),
                        result.get('night_work_pay', 0),
                        result.get('friday_work_pay', 0),
                        result.get('shift_allowance', 0),
                        result.get('gross_salary', 0),
                        result.get('insurance_employee', 0),
                        result.get('tax', 0),
                        result.get('loan_installment', 0),
                        result.get('advance_payment', 0),
                        result.get('deduction', 0),
                        result.get('penalty', 0),
                        result.get('net_salary', 0),
                        existing['id']
                    ])
                else:
                    c.execute('''
                        INSERT INTO payrolls (
                            employee_id, year, month,
                            work_days, overtime_hours, night_work_hours,
                            friday_work_hours, shift_days,
                            child_allowance, spouse_allowance,
                            meal_allowance, housing_allowance,
                            overtime_pay, night_work_pay, friday_work_pay,
                            shift_allowance, gross_salary,
                            insurance_employee, tax, loan_installment,
                            advance_payment, deduction, penalty,
                            net_salary, payment_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                    ''', [
                        self.employee['id'], self.year, self.month,
                        result.get('work_days', 0),
                        result.get('overtime_hours', 0),
                        result.get('night_work_hours', 0),
                        result.get('friday_work_hours', 0),
                        result.get('shift_days', 0),
                        result.get('child_allowance', 0),
                        result.get('spouse_allowance', 0),
                        result.get('meal_allowance', 0),
                        result.get('housing_allowance', 0),
                        result.get('overtime_pay', 0),
                        result.get('night_work_pay', 0),
                        result.get('friday_work_pay', 0),
                        result.get('shift_allowance', 0),
                        result.get('gross_salary', 0),
                        result.get('insurance_employee', 0),
                        result.get('tax', 0),
                        result.get('loan_installment', 0),
                        result.get('advance_payment', 0),
                        result.get('deduction', 0),
                        result.get('penalty', 0),
                        result.get('net_salary', 0)
                    ])

                conn.commit()

            QMessageBox.information(self, "موفق", "✅ حقوق با موفقیت ذخیره شد!")
            self.save_btn.setEnabled(False)
            self.accept()

        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")


# ============================================================
# کلاس ۳: InsuranceReportDialog (گزارش بیمه)
# ============================================================

class InsuranceReportDialog(QDialog):
    """دیالوگ نمایش و خروجی لیست بیمه"""

    def __init__(self, year, month, parent=None):
        super().__init__(parent)
        self.year = year
        self.month = month
        self.screen_manager = ScreenManager()

        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]

        self.setWindowTitle(f"📄 لیست بیمه - {month_names[month-1]} {year}")
        self.setModal(True)

        w, h = self.screen_manager.get_scaled_size(800, 500)
        self.setGeometry(200, 200, w, h)

        self.init_ui()
        self.load_data()
        self.apply_styles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        margin = self.screen_manager.get_margin(15)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(self.screen_manager.get_spacing(10))

        # ---------- هدر ----------
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        header = QLabel(f"📄 لیست بیمه - {month_names[self.month-1]} {self.year}")
        header.setStyleSheet(f"""
            font-size: {self.screen_manager.get_font_size(14)}pt;
            font-weight: bold;
            color: #273c75;
            padding: {self.screen_manager.get_scaled(10)}px;
            background: #e8f0fe;
            border-radius: {self.screen_manager.get_scaled(8)}px;
        """)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # ---------- اسکرول ----------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: #f0f0f0;
                width: {self.screen_manager.get_scaled(10)}px;
                border-radius: {self.screen_manager.get_scaled(5)}px;
            }}
            QScrollBar::handle:vertical {{
                background: #273c75;
                border-radius: {self.screen_manager.get_scaled(5)}px;
                min-height: {self.screen_manager.get_scaled(30)}px;
            }}
        """)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(self.screen_manager.get_spacing(10))

        # ---------- جدول ----------
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["کد پرسنلی", "نام", "حقوق مشمول", "بیمه کارمند", "بیمه کارفرما", "جمع"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        col_widths = [
            self.screen_manager.get_scaled(90),
            self.screen_manager.get_scaled(150),
            self.screen_manager.get_scaled(120),
            self.screen_manager.get_scaled(120),
            self.screen_manager.get_scaled(120),
            self.screen_manager.get_scaled(120),
        ]
        for col, width in enumerate(col_widths):
            self.table.setColumnWidth(col, width)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid #ddd;
                border-radius: {self.screen_manager.get_scaled(6)}px;
                background-color: white;
                font-size: {self.screen_manager.get_font_size(10)}pt;
            }}
            QHeaderView::section {{
                background-color: #273c75;
                color: white;
                padding: {self.screen_manager.get_scaled(8)}px;
                border: none;
                font-weight: bold;
            }}
            QTableWidget::item:selected {{
                background-color: #4a90d9;
                color: white;
            }}
        """)
        content_layout.addWidget(self.table)

        # ---------- جمع ----------
        self.total_label = QLabel("مجموع: ۰ ریال")
        self.total_label.setStyleSheet(f"""
            font-size: {self.screen_manager.get_font_size(12)}pt;
            font-weight: bold;
            color: #273c75;
            padding: {self.screen_manager.get_scaled(10)}px;
            background: #f8f9fa;
            border-radius: {self.screen_manager.get_scaled(6)}px;
        """)
        content_layout.addWidget(self.total_label)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # ---------- دکمه‌ها ----------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        export_btn = QPushButton("📎 خروجی Excel")
        export_btn.setStyleSheet(self._btn_style("#4CAF50"))
        export_btn.clicked.connect(self.export_excel)
        btn_layout.addWidget(export_btn)

        close_btn = QPushButton("❌ بستن")
        close_btn.setStyleSheet(self._btn_style("#e74c3c"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _btn_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: {self.screen_manager.get_scaled(6)}px;
                padding: {self.screen_manager.get_scaled(10)}px {self.screen_manager.get_scaled(25)}px;
                font-weight: bold;
                font-size: {self.screen_manager.get_font_size(10)}pt;
                min-height: {self.screen_manager.get_scaled(36)}px;
            }}
            QPushButton:hover {{
                background-color: {color}CC;
            }}
        """

    def apply_styles(self):
        fs = self.screen_manager.get_font_size(10)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #f5f6fa;
            }}
            QLabel {{
                font-size: {fs}pt;
                color: #2C3E50;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)

    def load_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT
                        e.code, e.name, p.gross_salary,
                        p.insurance_employee,
                        p.insurance_employer,
                        p.insurance_employee + p.insurance_employer as total_insurance
                    FROM payrolls p
                    JOIN employees e ON p.employee_id = e.id
                    WHERE p.year = ? AND p.month = ?
                    ORDER BY e.code
                ''', [self.year, self.month])
                rows = c.fetchall()

                self.table.setRowCount(len(rows))
                total = 0

                for i, row in enumerate(rows):
                    self.table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.table.setItem(i, 1, QTableWidgetItem(row['name']))

                    salary_item = QTableWidgetItem(f"{row['gross_salary']:,.0f}")
                    salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(i, 2, salary_item)

                    emp_item = QTableWidgetItem(f"{row['insurance_employee']:,.0f}")
                    emp_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(i, 3, emp_item)

                    employer_item = QTableWidgetItem(f"{row['insurance_employer']:,.0f}")
                    employer_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(i, 4, employer_item)

                    total_item = QTableWidgetItem(f"{row['total_insurance']:,.0f}")
                    total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    total_item.setForeground(QColor('#27ae60'))
                    self.table.setItem(i, 5, total_item)

                    total += row['total_insurance'] or 0

                self.total_label.setText(f"مجموع کل بیمه: {total:,.0f} ریال")

        except Exception as e:
            print(f"⚠️ خطا در بارگذاری بیمه: {e}")
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")

    def export_excel(self):
        try:
            month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                           "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "ذخیره گزارش بیمه",
                f"insurance_{self.year}_{month_names[self.month-1]}.csv",
                "CSV Files (*.csv)"
            )

            if not filename:
                return

            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["کد پرسنلی", "نام", "حقوق مشمول", "بیمه کارمند", "بیمه کارفرما", "جمع"])

                total = 0
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(6):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)

                    # جمع
                    total_str = row_data[5].replace(',', '')
                    total += int(total_str) if total_str.isdigit() else 0

                writer.writerow([])
                writer.writerow(["", "", "", "", "جمع کل:", f"{total:,}"])

            QMessageBox.information(self, "موفق", f"✅ گزارش ذخیره شد!")

        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
