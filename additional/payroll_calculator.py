# payroll_calculator.py
from datetime import datetime
from database import get_db, PayrollHelper


class PayrollCalculator:
    """کلاس محاسبه کامل حقوق و دستمزد - نسخه نهایی"""
    
    def __init__(self, employee_id, year, month):
        self.employee_id = employee_id
        self.year = year
        self.month = month
        self.employee = None
        self.settings = None
        self._load_data()
    
    def _load_data(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM employees WHERE id = ?', [self.employee_id])
            self.employee = c.fetchone()
            self.settings = PayrollHelper.get_payroll_settings(self.year)
    
    def _get_employee_value(self, key, default=0):
        """دسترسی ایمن به فیلدهای employee (چون sqlite3.Row get نداره)"""
        if self.employee and key in self.employee.keys():
            val = self.employee[key]
            return val if val is not None else default
        return default
    
    def _get_settings_value(self, key, default=0):
        """دسترسی ایمن به فیلدهای settings"""
        if self.settings and key in self.settings.keys():
            val = self.settings[key]
            return val if val is not None else default
        return default
    
    def calculate(self, work_days, overtime_hours=0, night_hours=0, friday_hours=0, 
                  shift_days=0, bonus=0, performance_bonus=0, mission_allowance=0,
                  advance_payment=0, deduction=0, **kwargs):
        """
        محاسبه کامل حقوق با همه اقلام
        """
        if not self.employee or not self.settings:
            return None
        
        base = self._get_employee_value('base_salary', 0)
        
        # ========== حقوق پایه کارکرد ==========
        daily_rate = base / 30 if base > 0 else 0
        base_salary = int(daily_rate * work_days)
        
        # ========== حق اولاد ==========
        child_count = self._get_employee_value('child_count', 0)
        child_allowance = PayrollHelper.calculate_child_allowance(
            child_count, 
            self.settings
        )
        
        # ========== حق همسر ==========
        spouse_allowance = self._get_employee_value('spouse_allowance', 0)
        
        # ========== حق مسکن ==========
        housing_allowance = self._get_settings_value('housing_allowance', 0)
        
        # ========== بن کارگری ==========
        meal_allowance = self._get_settings_value('meal_allowance', 0)
        
        # ========== پایه سنوات ==========
        hire_date = self.employee['hire_date'] if 'hire_date' in self.employee.keys() else None
        seniority_pay = PayrollHelper.calculate_seniority_pay(
            hire_date, 
            base, 
            self.settings
        )
        
        # ========== اضافه کاری ==========
        overtime_rate = self._get_employee_value('overtime_rate', 1.5)
        overtime_pay = PayrollHelper.calculate_overtime_pay(
            base, 
            overtime_hours, 
            overtime_rate
        )
        
        # ========== شب کاری ==========
        night_work_rate = self._get_employee_value('night_work_rate', 0.35)
        night_work_pay = PayrollHelper.calculate_overtime_pay(
            base,
            night_hours,
            night_work_rate
        )
        
        # ========== جمعه کاری ==========
        friday_work_rate = self._get_employee_value('friday_work_rate', 1.5)
        friday_work_pay = PayrollHelper.calculate_overtime_pay(
            base,
            friday_hours,
            friday_work_rate
        )
        
        # ========== نوبت کاری ==========
        shift_allowance_rate = self._get_employee_value('shift_allowance_rate', 0.1)
        shift_allowance = PayrollHelper.calculate_overtime_pay(
            base,
            shift_days * 8,
            shift_allowance_rate
        )
        
        # ========== حق مسئولیت ==========
        responsibility_pay = self._get_employee_value('responsibility_pay', 0)
        
        # ========== قسط وام ==========
        loan_installment = self._get_employee_value('loan_installment', 0)
        
        # ========== جمع مزایا ==========
        gross_salary = (base_salary + child_allowance + spouse_allowance + 
                       housing_allowance + meal_allowance + seniority_pay + 
                       overtime_pay + night_work_pay + friday_work_pay + 
                       shift_allowance + responsibility_pay + bonus + 
                       performance_bonus + mission_allowance)
        
        # ========== بیمه ==========
        insurance_employee_rate = self._get_settings_value('insurance_employee_rate', 0.07)
        insurance_employer_rate = self._get_settings_value('insurance_employer_rate', 0.23)
        
        insurance_employee, insurance_employer = PayrollHelper.calculate_insurance(
            gross_salary, 
            insurance_employee_rate,
            insurance_employer_rate
        )
        
        # ========== مالیات ==========
        tax_rate = self._get_settings_value('tax_rate', 0.10)
        tax = PayrollHelper.calculate_tax(gross_salary, tax_rate)
        
        # ========== کسورات ==========
        legal_deductions = insurance_employee + tax
        total_deductions = legal_deductions + loan_installment + advance_payment + deduction
        
        # ========== خالص حقوق ==========
        net_salary = gross_salary - total_deductions
        
        return {
            'employee_id': self.employee_id,
            'year': self.year,
            'month': self.month,
            'work_days': work_days,
            'overtime_hours': overtime_hours,
            'night_hours': night_hours,
            'friday_hours': friday_hours,
            'shift_days': shift_days,
            'base_salary': base_salary,
            'child_allowance': child_allowance,
            'spouse_allowance': spouse_allowance,
            'housing_allowance': housing_allowance,
            'meal_allowance': meal_allowance,
            'seniority_pay': seniority_pay,
            'overtime_pay': overtime_pay,
            'night_work_pay': night_work_pay,
            'friday_work_pay': friday_work_pay,
            'shift_allowance': shift_allowance,
            'responsibility_pay': responsibility_pay,
            'bonus': bonus,
            'performance_bonus': performance_bonus,
            'mission_allowance': mission_allowance,
            'loan_installment': loan_installment,
            'advance_payment': advance_payment,
            'deduction': deduction,
            'gross_salary': gross_salary,
            'insurance_employee': insurance_employee,
            'insurance_employer': insurance_employer,
            'legal_deductions': legal_deductions,
            'tax': tax,
            'net_salary': net_salary
        }
    
    def save(self, result):
        """ذخیره فیش حقوقی در دیتابیس"""
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('''
                SELECT id FROM payrolls 
                WHERE employee_id = ? AND year = ? AND month = ?
            ''', [result['employee_id'], result['year'], result['month']])
            existing = c.fetchone()
            
            if existing:
                c.execute('''
                    UPDATE payrolls SET
                        work_days=?, overtime_hours=?, night_work_hours=?, friday_work_hours=?,
                        shift_days=?, base_salary=?, child_allowance=?, spouse_allowance=?,
                        housing_allowance=?, meal_allowance=?, seniority_pay=?, overtime_pay=?,
                        night_work_pay=?, friday_work_pay=?, shift_allowance=?, responsibility_pay=?,
                        bonus=?, performance_bonus=?, mission_allowance=?, loan_installment=?,
                        advance_payment=?, deduction=?, gross_salary=?, insurance_employee=?,
                        insurance_employer=?, legal_deductions=?, tax=?, net_salary=?,
                        payment_status='pending'
                    WHERE employee_id=? AND year=? AND month=?
                ''', [
                    result['work_days'], result['overtime_hours'], result['night_hours'], result['friday_hours'],
                    result['shift_days'], result['base_salary'], result['child_allowance'], result['spouse_allowance'],
                    result['housing_allowance'], result['meal_allowance'], result['seniority_pay'], result['overtime_pay'],
                    result['night_work_pay'], result['friday_work_pay'], result['shift_allowance'], result['responsibility_pay'],
                    result['bonus'], result['performance_bonus'], result['mission_allowance'], result['loan_installment'],
                    result['advance_payment'], result['deduction'], result['gross_salary'], result['insurance_employee'],
                    result['insurance_employer'], result['legal_deductions'], result['tax'], result['net_salary'],
                    result['employee_id'], result['year'], result['month']
                ])
            else:
                c.execute('''
                    INSERT INTO payrolls (
                        employee_id, year, month, work_days, overtime_hours, night_work_hours, friday_work_hours,
                        shift_days, base_salary, child_allowance, spouse_allowance, housing_allowance, meal_allowance,
                        seniority_pay, overtime_pay, night_work_pay, friday_work_pay, shift_allowance, responsibility_pay,
                        bonus, performance_bonus, mission_allowance, loan_installment, advance_payment, deduction,
                        gross_salary, insurance_employee, insurance_employer, legal_deductions, tax, net_salary, payment_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                ''', [
                    result['employee_id'], result['year'], result['month'],
                    result['work_days'], result['overtime_hours'], result['night_hours'], result['friday_hours'],
                    result['shift_days'], result['base_salary'], result['child_allowance'], result['spouse_allowance'],
                    result['housing_allowance'], result['meal_allowance'], result['seniority_pay'], result['overtime_pay'],
                    result['night_work_pay'], result['friday_work_pay'], result['shift_allowance'], result['responsibility_pay'],
                    result['bonus'], result['performance_bonus'], result['mission_allowance'], result['loan_installment'],
                    result['advance_payment'], result['deduction'], result['gross_salary'], result['insurance_employee'],
                    result['insurance_employer'], result['legal_deductions'], result['tax'], result['net_salary']
                ])