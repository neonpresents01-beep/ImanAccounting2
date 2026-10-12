# migrations/payroll.py
# ============================================================
# Migration های حقوق و دستمزد
# ============================================================
# شامل:
# - employees
# - payrolls
# - payroll_settings
# - payroll_items
# ============================================================

import logging
from migration_registry import get_migration_registry

logger = logging.getLogger(__name__)


def _migration_payroll_tables(conn):
    """ساخت جداول حقوق"""
    c = conn.cursor()
    
    # ─── employees ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            national_code TEXT,
            insurance_code TEXT,
            position TEXT,
            department TEXT,
            hire_date TEXT,
            base_salary INTEGER DEFAULT 0,
            child_count INTEGER DEFAULT 0,
            spouse_allowance INTEGER DEFAULT 0,
            meal_allowance INTEGER DEFAULT 0,
            housing_allowance INTEGER DEFAULT 0,
            responsibility_pay INTEGER DEFAULT 0,
            overtime_rate REAL DEFAULT 1.5,
            night_work_rate REAL DEFAULT 0.35,
            friday_work_rate REAL DEFAULT 1.5,
            shift_allowance_rate REAL DEFAULT 0.1,
            hardship_rate REAL DEFAULT 0,
            insurance_premium REAL DEFAULT 0.07,
            loan_installment INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            company_id INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            head_of_household_allowance INTEGER DEFAULT 0,
            supplemental_insurance INTEGER DEFAULT 0,
            holiday_work_rate REAL DEFAULT 1.5,
            bonus INTEGER DEFAULT 0,
            mission_allowance INTEGER DEFAULT 0,
            advance_payment INTEGER DEFAULT 0,
            deduction INTEGER DEFAULT 0,
            penalty INTEGER DEFAULT 0,
            tax_rate REAL DEFAULT 0.1,
            seniority_pay INTEGER DEFAULT 0
        )
    ''')
    
    # ─── payrolls ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS payrolls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            work_days INTEGER DEFAULT 0,
            overtime_hours REAL DEFAULT 0,
            night_work_hours REAL DEFAULT 0,
            friday_work_hours REAL DEFAULT 0,
            shift_days INTEGER DEFAULT 0,
            base_salary INTEGER DEFAULT 0,
            child_allowance INTEGER DEFAULT 0,
            spouse_allowance INTEGER DEFAULT 0,
            housing_allowance INTEGER DEFAULT 0,
            meal_allowance INTEGER DEFAULT 0,
            seniority_pay INTEGER DEFAULT 0,
            overtime_pay INTEGER DEFAULT 0,
            night_work_pay INTEGER DEFAULT 0,
            friday_work_pay INTEGER DEFAULT 0,
            shift_allowance INTEGER DEFAULT 0,
            responsibility_pay INTEGER DEFAULT 0,
            bonus INTEGER DEFAULT 0,
            performance_bonus INTEGER DEFAULT 0,
            mission_allowance INTEGER DEFAULT 0,
            loan_installment INTEGER DEFAULT 0,
            advance_payment INTEGER DEFAULT 0,
            deduction INTEGER DEFAULT 0,
            penalty INTEGER DEFAULT 0,
            gross_salary INTEGER DEFAULT 0,
            insurance_employee INTEGER DEFAULT 0,
            insurance_employer INTEGER DEFAULT 0,
            legal_deductions INTEGER DEFAULT 0,
            tax INTEGER DEFAULT 0,
            net_salary INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'pending',
            payment_date TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            UNIQUE(employee_id, year, month)
        )
    ''')
    
    # ─── payroll_settings ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS payroll_settings (
            year INTEGER PRIMARY KEY,
            daily_minimum_wage INTEGER DEFAULT 2650000,
            base_seniority_pay INTEGER DEFAULT 2100000,
            child_allowance_per_child INTEGER DEFAULT 15000000,
            housing_allowance INTEGER DEFAULT 15000000,
            meal_allowance INTEGER DEFAULT 14000000,
            tax_rate REAL DEFAULT 0.10,
            insurance_employee_rate REAL DEFAULT 0.07,
            insurance_employer_rate REAL DEFAULT 0.23,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ─── payroll_items ───
    c.execute('''
        CREATE TABLE IF NOT EXISTS payroll_items (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            value REAL DEFAULT 0,
            unit TEXT,
            category TEXT DEFAULT 'benefit'
        )
    ''')
    
    # ─── ایندکس‌ها ───
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_payrolls_employee ON payrolls(employee_id)",
        "CREATE INDEX IF NOT EXISTS idx_payrolls_year_month ON payrolls(year, month)",
        "CREATE INDEX IF NOT EXISTS idx_payrolls_status ON payrolls(payment_status)",
        "CREATE INDEX IF NOT EXISTS idx_employees_code ON employees(code)",
        "CREATE INDEX IF NOT EXISTS idx_employees_active ON employees(is_active)",
    ]:
        c.execute(idx)


def _migration_payroll_defaults(conn):
    """درج داده‌های پیش‌فرض حقوق"""
    c = conn.cursor()
    
    # ─── تنظیمات حقوق ۱۴۰۴ ───
    c.execute('''
        INSERT OR IGNORE INTO payroll_settings
        (year, daily_minimum_wage, base_seniority_pay, child_allowance_per_child,
         housing_allowance, meal_allowance)
        VALUES (1404, 2650000, 2100000, 15000000, 15000000, 14000000)
    ''')
    
    # ─── اقلام حقوق ───
    default_items = [
        ('OVERTIME', 'اضافه کاری', 'percent', 1.5, 'برابر', 'benefit'),
        ('NIGHT', 'شب کاری', 'percent', 0.35, 'درصد', 'benefit'),
        ('FRIDAY', 'جمعه کاری', 'percent', 1.5, 'برابر', 'benefit'),
        ('SHIFT', 'نوبت کاری', 'percent', 0.1, 'درصد', 'benefit'),
        ('CHILD', 'حق اولاد', 'fixed', 0, 'ریال', 'benefit'),
        ('HOUSING', 'حق مسکن', 'fixed', 0, 'ریال', 'benefit'),
        ('MEAL', 'بن کارگری', 'fixed', 0, 'ریال', 'benefit'),
        ('SENIORITY', 'پایه سنوات', 'fixed', 0, 'ریال', 'benefit'),
        ('SPOUSE', 'حق همسر', 'fixed', 0, 'ریال', 'benefit'),
        ('RESPONSIBILITY', 'حق مسئولیت', 'fixed', 0, 'ریال', 'benefit'),
        ('BONUS', 'پاداش', 'fixed', 0, 'ریال', 'benefit'),
        ('MISSION', 'حق ماموریت', 'fixed', 0, 'ریال', 'benefit'),
        ('INSURANCE', 'بیمه سهم کارمند', 'percent', 0.07, 'درصد', 'deduction'),
        ('TAX', 'مالیات بر درآمد', 'percent', 0.1, 'درصد', 'deduction'),
        ('LOAN', 'قسط وام', 'fixed', 0, 'ریال', 'deduction'),
        ('ADVANCE', 'مساعده', 'fixed', 0, 'ریال', 'deduction'),
        ('DEDUCTION', 'سایر کسورات', 'fixed', 0, 'ریال', 'deduction'),
        ('PENALTY', 'جریمه', 'fixed', 0, 'ریال', 'deduction'),
    ]
    for item in default_items:
        c.execute('''
            INSERT OR IGNORE INTO payroll_items (code, name, type, value, unit, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', item)


def register_migrations():
    registry = get_migration_registry()
    
    registry.register(
        name='payroll_tables',
        func=_migration_payroll_tables,
        order=500,
        description='جداول حقوق (employees, payrolls, payroll_settings, payroll_items)',
        dependencies=['core_tables'],
    )
    
    registry.register(
        name='payroll_defaults',
        func=_migration_payroll_defaults,
        order=510,
        description='داده‌های پیش‌فرض حقوق',
        dependencies=['payroll_tables'],
    )


register_migrations()
