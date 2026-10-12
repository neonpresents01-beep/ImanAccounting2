# ui/finance/auto_voucher.py
# ============================================================
# موتور ساخت خودکار سند حسابداری
# قلب امور مالی اتوماتیک — مشابه هلو، ولی هوشمندتر
# ============================================================
# 
# فلسفه:
#   کاربر فقط نوع عملیات + مبلغ را وارد می‌کند
#   موتور خودش سند حسابداری (بدهکار/بستانکار) می‌سازد
#   نیازی به دانش تخصصی حسابداری نیست
# 
# ============================================================

from database import get_db, DateConverter
from datetime import datetime
from typing import Dict, List, Optional


# ============================================================
# کدهای حساب پیش‌فرض
# ============================================================

class AccountCodes:
    """کدهای حساب استاندارد"""
    
    # دارایی‌ها (1xxx)
    CASH = '1101'                 # صندوق
    BANK = '1102'                 # بانک
    RECEIVABLE = '1103'           # حساب‌های دریافتنی
    INVENTORY = '1104'            # موجودی کالا
    PREPAID = '1105'              # پیش‌پرداخت‌ها
    
    # بدهی‌ها (2xxx)
    PAYABLE = '2101'              # حساب‌های پرداختنی
    LOANS = '2102'                # وام‌ها
    TAX_PAYABLE = '2103'          # مالیات پرداختنی
    INSURANCE_PAYABLE = '2104'    # بیمه پرداختنی
    
    # سرمایه (3xxx)
    CAPITAL = '3101'              # سرمایه
    DRAWINGS = '3102'             # برداشت‌ها
    RETAINED_EARNINGS = '3103'    # سود انباشته
    
    # درآمدها (4xxx)
    SALES = '4101'                # فروش کالا
    BANK_PROFIT = '4102'          # سود بانکی
    DISCOUNT_RECEIVED = '4103'    # تخفیف دریافتی
    OTHER_INCOME = '4104'         # درآمدهای متفرقه
    
    # هزینه‌ها (5xxx)
    COGS = '5101'                 # بهای تمام شده
    SALARY = '5102'               # حقوق و دستمزد
    BANK_FEE = '5103'             # کارمزد بانکی
    RENT = '5104'                 # اجاره
    UTILITIES = '5105'            # آب، برق، گاز
    DISCOUNT_GIVEN = '5106'       # تخفیف داده شده
    OTHER_EXPENSE = '5109'        # سایر هزینه‌ها


# ============================================================
# موتور اصلی
# ============================================================

class AutoVoucherEngine:
    """
    موتور ساخت خودکار سند حسابداری
    
    هر متد یک dict برمی‌گرداند:
    {
        'voucher_items': [
            {'account_code': '...', 'description': '...', 'debit': N, 'credit': M},
            ...
        ],
        'description': 'شرح سند',
        'type': '...',
        'metadata': {...}  # اطلاعات اضافی
    }
    """
    
    # ═══════════════════════════════════════════════════════════
    # نقطه ورود اصلی
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def create_from_transaction(cls, data: Dict) -> Dict:
        """
        ساخت سند از تراکنش
        
        Args:
            data: dict شامل:
                - type: نوع تراکنش
                - date: تاریخ شمسی
                - amount: مبلغ (الزامی)
                - fee: کارمزد (اختیاری)
                - discount: تخفیف (اختیاری)
                - from_account: {'type', 'id', 'code', 'name'} (اختیاری)
                - to_account: {'type', 'id', 'code', 'name'} (اختیاری)
                - party_id: شناسه طرف حساب (اختیاری)
                - party_name: نام طرف حساب (اختیاری)
                - description: توضیحات (اختیاری)
        
        Returns:
            voucher_data: dict
        """
        
        # اعتبارسنجی
        cls._validate(data)
        
        # انتخاب موتور مناسب
        type_ = data['type']
        
        engines = {
            'receipt':      cls._build_receipt,
            'payment':      cls._build_payment,
            'transfer':     cls._build_transfer,
            'income':       cls._build_income,
            'expense':      cls._build_expense,
            'capital':      cls._build_capital,
            'bank_profit':  cls._build_bank_profit,
            'bank_charge':  cls._build_bank_charge,
            'card_to_card': cls._build_card_to_card,
        }
        
        engine = engines.get(type_)
        if not engine:
            raise ValueError(f"نوع تراکنش نامعتبر: {type_}")
        
        result = engine(data)
        
        # اطلاعات کلی
        result['type'] = type_
        result['date'] = data['date']
        result['amount'] = data['amount']
        
        # اعتبارسنجی موازنه
        cls._validate_balance(result)
        
        return result
    
    # ═══════════════════════════════════════════════════════════
    # اعتبارسنجی
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _validate(cls, data: Dict):
        """اعتبارسنجی داده ورودی"""
        if not data.get('type'):
            raise ValueError("نوع تراکنش الزامی است")
        
        if not data.get('date'):
            raise ValueError("تاریخ الزامی است")
        
        amount = data.get('amount', 0)
        if not amount or amount <= 0:
            raise ValueError("مبلغ باید بیشتر از صفر باشد")
        
        if amount < 1000:
            raise ValueError("حداقل مبلغ ۱۰۰۰ ریال است")
    
    @classmethod
    def _validate_balance(cls, voucher_data: Dict):
        """اعتبارسنجی موازنه سند"""
        total_debit = sum(item['debit'] for item in voucher_data['voucher_items'])
        total_credit = sum(item['credit'] for item in voucher_data['voucher_items'])
        
        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(
                f"سند موازنه نیست!\n"
                f"بدهکار: {total_debit:,.0f}\n"
                f"بستانکار: {total_credit:,.0f}\n"
                f"اختلاف: {abs(total_debit - total_credit):,.0f}"
            )
    
    # ═══════════════════════════════════════════════════════════
    # 📥 دریافت از طرف حساب
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_receipt(cls, data: Dict) -> Dict:
        """
        دریافت پول از مشتری
        
        📌 سند استاندارد:
            🟢 بدهکار: بانک/صندوق         (افزایش دارایی)
            🔴 بستانکار: حساب دریافتنی   (کاهش طلب از مشتری)
            
        📌 حالت با تخفیف:
            🟢 بدهکار: بانک/صندوق         (مبلغ دریافتی)
            🟢 بدهکار: تخفیف داده شده     (تخفیف)
            🔴 بستانکار: حساب دریافتنی    (کل طلب)
        """
        
        items = []
        amount = data['amount']
        discount = data.get('discount', 0)
        party_name = data.get('party_name', 'طرف حساب')
        to_account = data.get('to_account', {})
        
        # 🟢 بدهکار: حساب دریافت
        to_code = to_account.get('code', AccountCodes.CASH)
        items.append({
            'account_code': to_code,
            'description': f"دریافت از {party_name}",
            'debit': amount,
            'credit': 0,
        })
        
        # 🟡 بدهکار: تخفیف داده شده (اگه داشت)
        if discount > 0:
            items.append({
                'account_code': AccountCodes.DISCOUNT_GIVEN,
                'description': f"تخفیف به {party_name}",
                'debit': discount,
                'credit': 0,
            })
        
        # 🔴 بستانکار: حساب دریافتنی
        items.append({
            'account_code': AccountCodes.RECEIVABLE,
            'description': f"تسویه طلب {party_name}",
            'debit': 0,
            'credit': amount + discount,
        })
        
        return {
            'voucher_items': items,
            'description': f"دریافت - {party_name}",
        }
    
    # ═══════════════════════════════════════════════════════════
    # 📤 پرداخت به طرف حساب
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_payment(cls, data: Dict) -> Dict:
        """
        پرداخت به تأمین‌کننده
        
        📌 سند استاندارد:
            🟢 بدهکار: حساب پرداختنی      (کاهش بدهی)
            🔴 بستانکار: بانک/صندوق       (کاهش دارایی)
        """
        
        items = []
        amount = data['amount']
        discount = data.get('discount', 0)
        party_name = data.get('party_name', 'طرف حساب')
        from_account = data.get('from_account', {})
        
        # 🟢 بدهکار: حساب پرداختنی
        items.append({
            'account_code': AccountCodes.PAYABLE,
            'description': f"تسویه بدهی به {party_name}",
            'debit': amount + discount,
            'credit': 0,
        })
        
        # 🔴 بستانکار: حساب پرداخت
        from_code = from_account.get('code', AccountCodes.CASH)
        items.append({
            'account_code': from_code,
            'description': f"پرداخت به {party_name}",
            'debit': 0,
            'credit': amount,
        })
        
        # 🟡 بستانکار: تخفیف دریافتی (اگه داشت)
        if discount > 0:
            items.append({
                'account_code': AccountCodes.DISCOUNT_RECEIVED,
                'description': f"تخفیف از {party_name}",
                'debit': 0,
                'credit': discount,
            })
        
        return {
            'voucher_items': items,
            'description': f"پرداخت - {party_name}",
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🔄 انتقال بین حساب‌ها
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_transfer(cls, data: Dict) -> Dict:
        """
        انتقال وجه بین حساب‌ها
        
        📌 سند:
            🟢 بدهکار: حساب مقصد          (افزایش دارایی)
            🔴 بستانکار: حساب مبدأ        (کاهش دارایی)
            
        📌 با کارمزد:
            🟢 بدهکار: حساب مقصد          (مبلغ انتقال)
            🟢 بدهکار: کارمزد بانکی       (هزینه)
            🔴 بستانکار: حساب مبدأ        (مبلغ + کارمزد)
        """
        
        items = []
        amount = data['amount']
        fee = data.get('fee', 0)
        from_account = data.get('from_account', {})
        to_account = data.get('to_account', {})
        
        from_name = from_account.get('name', 'حساب مبدأ')
        to_name = to_account.get('name', 'حساب مقصد')
        from_code = from_account.get('code', AccountCodes.CASH)
        to_code = to_account.get('code', AccountCodes.CASH)
        
        # 🟢 بدهکار: حساب مقصد
        items.append({
            'account_code': to_code,
            'description': f"انتقال از {from_name}",
            'debit': amount,
            'credit': 0,
        })
        
        # 🔴 بستانکار: حساب مبدأ
        items.append({
            'account_code': from_code,
            'description': f"انتقال به {to_name}",
            'debit': 0,
            'credit': amount + fee,
        })
        
        # 🟡 بدهکار: کارمزد (اگه داشت)
        if fee > 0:
            items.append({
                'account_code': AccountCodes.BANK_FEE,
                'description': f"کارمزد انتقال {from_name} به {to_name}",
                'debit': fee,
                'credit': 0,
            })
        
        return {
            'voucher_items': items,
            'description': f"انتقال وجه: {from_name} → {to_name}",
        }
    
    # ═══════════════════════════════════════════════════════════
    # 💰 درآمد متفرقه
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_income(cls, data: Dict) -> Dict:
        """
        ثبت درآمد متفرقه
        
        📌 سند:
            🟢 بدهکار: بانک/صندوق         (افزایش دارایی)
            🔴 بستانکار: درآمد           (افزایش درآمد)
        """
        
        items = []
        amount = data['amount']
        to_account = data.get('to_account', {})
        description = data.get('description', 'درآمد متفرقه')
        
        # 🟢 بدهکار: حساب دریافت
        to_code = to_account.get('code', AccountCodes.CASH)
        items.append({
            'account_code': to_code,
            'description': description,
            'debit': amount,
            'credit': 0,
        })
        
        # 🔴 بستانکار: درآمد
        items.append({
            'account_code': AccountCodes.OTHER_INCOME,
            'description': description,
            'debit': 0,
            'credit': amount,
        })
        
        return {
            'voucher_items': items,
            'description': description,
        }
    
    # ═══════════════════════════════════════════════════════════
    # 💸 هزینه متفرقه
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_expense(cls, data: Dict) -> Dict:
        """
        ثبت هزینه متفرقه
        
        📌 سند:
            🟢 بدهکار: هزینه             (افزایش هزینه)
            🔴 بستانکار: بانک/صندوق       (کاهش دارایی)
        """
        
        items = []
        amount = data['amount']
        from_account = data.get('from_account', {})
        description = data.get('description', 'هزینه متفرقه')
        
        # 🟢 بدهکار: هزینه
        items.append({
            'account_code': AccountCodes.OTHER_EXPENSE,
            'description': description,
            'debit': amount,
            'credit': 0,
        })
        
        # 🔴 بستانکار: حساب پرداخت
        from_code = from_account.get('code', AccountCodes.CASH)
        items.append({
            'account_code': from_code,
            'description': description,
            'debit': 0,
            'credit': amount,
        })
        
        return {
            'voucher_items': items,
            'description': description,
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🏦 سرمایه‌گذاری
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_capital(cls, data: Dict) -> Dict:
        """
        ثبت سرمایه‌گذاری (افزایش سرمایه)
        
        📌 سند:
            🟢 بدهکار: بانک/صندوق         (افزایش دارایی)
            🔴 بستانکار: سرمایه          (افزایش سرمایه)
        """
        
        items = []
        amount = data['amount']
        to_account = data.get('to_account', {})
        party_name = data.get('party_name', 'سهامدار')
        description = data.get('description', f'سرمایه‌گذاری {party_name}')
        
        # 🟢 بدهکار: حساب دریافت
        to_code = to_account.get('code', AccountCodes.CASH)
        items.append({
            'account_code': to_code,
            'description': description,
            'debit': amount,
            'credit': 0,
        })
        
        # 🔴 بستانکار: سرمایه
        items.append({
            'account_code': AccountCodes.CAPITAL,
            'description': description,
            'debit': 0,
            'credit': amount,
        })
        
        return {
            'voucher_items': items,
            'description': description,
        }
    
    # ═══════════════════════════════════════════════════════════
    # 📈 سود بانکی
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_bank_profit(cls, data: Dict) -> Dict:
        """
        ثبت سود سپرده بانکی
        
        📌 سند:
            🟢 بدهکار: بانک              (افزایش دارایی)
            🔴 بستانکار: سود بانکی       (افزایش درآمد)
        """
        
        items = []
        amount = data['amount']
        to_account = data.get('to_account', {})
        description = data.get('description', 'سود بانکی')
        
        # 🟢 بدهکار: بانک
        to_code = to_account.get('code', AccountCodes.BANK)
        items.append({
            'account_code': to_code,
            'description': description,
            'debit': amount,
            'credit': 0,
        })
        
        # 🔴 بستانکار: درآمد سود بانکی
        items.append({
            'account_code': AccountCodes.BANK_PROFIT,
            'description': description,
            'debit': 0,
            'credit': amount,
        })
        
        return {
            'voucher_items': items,
            'description': description,
        }
    
    # ═══════════════════════════════════════════════════════════
    # 💳 کارمزد بانکی
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_bank_charge(cls, data: Dict) -> Dict:
        """
        ثبت کارمزد بانکی
        
        📌 سند:
            🟢 بدهکار: کارمزد بانکی       (هزینه)
            🔴 بستانکار: بانک              (کاهش دارایی)
        """
        
        items = []
        amount = data['amount']
        from_account = data.get('from_account', {})
        description = data.get('description', 'کارمزد بانکی')
        
        # 🟢 بدهکار: هزینه کارمزد
        items.append({
            'account_code': AccountCodes.BANK_FEE,
            'description': description,
            'debit': amount,
            'credit': 0,
        })
        
        # 🔴 بستانکار: بانک
        from_code = from_account.get('code', AccountCodes.BANK)
        items.append({
            'account_code': from_code,
            'description': description,
            'debit': 0,
            'credit': amount,
        })
        
        return {
            'voucher_items': items,
            'description': description,
        }
    
    # ═══════════════════════════════════════════════════════════
    # 💳 کارت به کارت
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_card_to_card(cls, data: Dict) -> Dict:
        """
        انتقال کارت به کارت
        
        مشابه انتقال بین حساب‌ها، ولی معمولاً با کارمزد
        """
        
        # استفاده از همون منطق transfer
        return cls._build_transfer(data)
    
    # ═══════════════════════════════════════════════════════════
    # ذخیره در دیتابیس
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def save_voucher(cls, voucher_data: Dict, shamsi_date: str) -> int:
        """
        ذخیره سند در دیتابیس
        
        Args:
            voucher_data: نتیجه create_from_transaction
            shamsi_date: تاریخ شمسی (۱۴۰۵/۰۶/۰۱)
        
        Returns:
            voucher_id: شناسه سند ذخیره شده
        """
        
        with get_db() as conn:
            c = conn.cursor()
            
            # ─── شماره سند ───
            c.execute("SELECT MAX(voucher_no) FROM vouchers")
            max_no = c.fetchone()[0] or 0
            voucher_no = max_no + 1
            
            # ─── تبدیل تاریخ ───
            gregorian_date = DateConverter.for_db(shamsi_date)
            
            # ─── ایجاد سند ───
            c.execute('''
                INSERT INTO vouchers 
                (voucher_no, date, description, type, status)
                VALUES (?, ?, ?, ?, 'approved')
            ''', [
                voucher_no,
                gregorian_date,
                voucher_data['description'],
                'امور مالی'
            ])
            
            voucher_id = c.lastrowid
            
            # ─── اقلام سند ───
            for item in voucher_data['voucher_items']:
                c.execute('''
                    INSERT INTO voucher_items
                    (voucher_id, account_code, description, debit, credit)
                    VALUES (?, ?, ?, ?, ?)
                ''', [
                    voucher_id,
                    item['account_code'],
                    item['description'],
                    item['debit'],
                    item['credit']
                ])
            
            conn.commit()
            
            return voucher_id
    
    # ═══════════════════════════════════════════════════════════
    # بازگشت سند (برای حذف/برگشت تراکنش)
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def create_reverse_voucher(cls, voucher_id: int) -> Dict:
        """
        ساخت سند برگشتی (برای ابطال)
        
        تمام بدهکارها به بستانکار و برعکس تبدیل می‌شوند
        """
        
        with get_db() as conn:
            c = conn.cursor()
            
            # خواندن سند اصلی
            c.execute("SELECT * FROM vouchers WHERE id = ?", [voucher_id])
            voucher = c.fetchone()
            
            if not voucher:
                raise ValueError(f"سند {voucher_id} پیدا نشد")
            
            # خواندن اقلام
            c.execute(
                "SELECT * FROM voucher_items WHERE voucher_id = ?",
                [voucher_id]
            )
            items = c.fetchall()
        
        # ساخت سند برگشتی
        reverse_items = []
        for item in items:
            reverse_items.append({
                'account_code': item['account_code'],
                'description': f"برگشت: {item['description']}",
                'debit': item['credit'],      # ← برعکس!
                'credit': item['debit'],      # ← برعکس!
            })
        
        return {
            'voucher_items': reverse_items,
            'description': f"برگشت سند {voucher['voucher_no']}",
            'is_reverse': True,
            'original_voucher_id': voucher_id,
        }
    
    # ═══════════════════════════════════════════════════════════
    # ابزار کمکی: پیش‌نمایش متنی
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def preview_text(cls, voucher_data: Dict) -> str:
        """
        پیش‌نمایش متنی سند (برای CLI یا تست)
        """
        
        lines = []
        lines.append("═" * 60)
        lines.append(f"📋 {voucher_data.get('description', 'سند')}")
        lines.append("═" * 60)
        lines.append(f"{'کد حساب':<10} {'شرح':<30} {'بدهکار':>10} {'بستانکار':>10}")
        lines.append("─" * 60)
        
        total_debit = 0
        total_credit = 0
        
        for item in voucher_data['voucher_items']:
            debit = item['debit']
            credit = item['credit']
            total_debit += debit
            total_credit += credit
            
            desc = item['description'][:28]
            lines.append(
                f"{item['account_code']:<10} {desc:<30} "
                f"{f'{debit:,.0f}' if debit else '-':>10} "
                f"{f'{credit:,.0f}' if credit else '-':>10}"
            )
        
        lines.append("─" * 60)
        lines.append(
            f"{'':<10} {'جمع':<30} "
            f"{total_debit:>10,.0f} {total_credit:>10,.0f}"
        )
        lines.append("═" * 60)
        
        if abs(total_debit - total_credit) < 1:
            lines.append("✅ سند موازنه است")
        else:
            lines.append(
                f"❌ عدم موازنه: {abs(total_debit - total_credit):,.0f} ریال"
            )
        
        return "\n".join(lines)
    
    # ═══════════════════════════════════════════════════════════
    # متد برای گرفتن کدهای حساب پویا از دیتابیس
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def get_account_by_type(cls, account_type: str) -> Optional[str]:
        """
        دریافت کد حساب بر اساس نوع
        (برای وقتی که کاربر کدهای خودش رو داره)
        """
        
        mapping = {
            'cash': cls._find_account(['صندوق', 'نقد']),
            'bank': cls._find_account(['بانک']),
            'receivable': cls._find_account(['دریافتنی', 'طلب']),
            'payable': cls._find_account(['پرداختنی', 'بدهی']),
            'capital': cls._find_account(['سرمایه']),
            'income': cls._find_account(['درآمد']),
            'expense': cls._find_account(['هزینه']),
        }
        
        return mapping.get(account_type)
    
    @classmethod
    def _find_account(cls, keywords: List[str]) -> Optional[str]:
        """پیدا کردن حساب بر اساس کلمات کلیدی"""
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                for keyword in keywords:
                    c.execute('''
                        SELECT code FROM accounts
                        WHERE (name LIKE ? OR name LIKE ?)
                        AND is_active = 1
                        ORDER BY code
                        LIMIT 1
                    ''', [f'%{keyword}%', f'%{keyword}%'])
                    
                    row = c.fetchone()
                    if row:
                        return row['code']
        except Exception:
            pass
        
        return None


# ============================================================
# توابع کمکی مستقل
# ============================================================

def format_voucher_summary(voucher_data: Dict) -> str:
    """خلاصه سند برای نمایش"""
    total = sum(item['debit'] for item in voucher_data['voucher_items'])
    count = len(voucher_data['voucher_items'])
    
    return (
        f"📋 {voucher_data.get('description', 'سند')}\n"
        f"💰 مبلغ: {total:,.0f} ریال\n"
        f"📝 تعداد اقلام: {count}"
    )


def calculate_voucher_totals(voucher_data: Dict) -> Dict:
    """محاسبه مجموع‌های سند"""
    total_debit = sum(item['debit'] for item in voucher_data['voucher_items'])
    total_credit = sum(item['credit'] for item in voucher_data['voucher_items'])
    
    return {
        'total_debit': total_debit,
        'total_credit': total_credit,
        'balance': total_debit - total_credit,
        'is_balanced': abs(total_debit - total_credit) < 0.01,
        'items_count': len(voucher_data['voucher_items']),
    }


# ============================================================
# تست (اگه مستقیم اجرا شد)
# ============================================================

if __name__ == "__main__":
    print("🧪 تست موتور سندساز")
    print("=" * 60)
    
    # تست ۱: دریافت از مشتری
    print("\n📥 تست ۱: دریافت از مشتری (بدون تخفیف)")
    receipt_data = {
        'type': 'receipt',
        'date': '1405/06/01',
        'amount': 10000000,
        'party_name': 'شرکت الف',
        'to_account': {'type': 'bank', 'id': 1, 'code': '1102', 'name': 'بانک ملی'},
    }
    
    voucher = AutoVoucherEngine.create_from_transaction(receipt_data)
    print(AutoVoucherEngine.preview_text(voucher))
    
    # تست ۲: دریافت با تخفیف
    print("\n📥 تست ۲: دریافت با تخفیف")
    receipt_data2 = {
        'type': 'receipt',
        'date': '1405/06/01',
        'amount': 9500000,
        'discount': 500000,
        'party_name': 'شرکت الف',
        'to_account': {'type': 'cash', 'id': 1, 'code': '1101', 'name': 'صندوق'},
    }
    
    voucher2 = AutoVoucherEngine.create_from_transaction(receipt_data2)
    print(AutoVoucherEngine.preview_text(voucher2))
    
    # تست ۳: پرداخت
    print("\n📤 تست ۳: پرداخت به تأمین‌کننده")
    payment_data = {
        'type': 'payment',
        'date': '1405/06/01',
        'amount': 5000000,
        'party_name': 'تأمین‌کننده ب',
        'from_account': {'type': 'bank', 'id': 1, 'code': '1102', 'name': 'بانک ملی'},
    }
    
    voucher3 = AutoVoucherEngine.create_from_transaction(payment_data)
    print(AutoVoucherEngine.preview_text(voucher3))
    
    # تست ۴: انتقال با کارمزد
    print("\n🔄 تست ۴: انتقال با کارمزد")
    transfer_data = {
        'type': 'transfer',
        'date': '1405/06/01',
        'amount': 2000000,
        'fee': 50000,
        'from_account': {'type': 'bank', 'id': 1, 'code': '1102', 'name': 'بانک ملی'},
        'to_account': {'type': 'cash', 'id': 1, 'code': '1101', 'name': 'صندوق'},
    }
    
    voucher4 = AutoVoucherEngine.create_from_transaction(transfer_data)
    print(AutoVoucherEngine.preview_text(voucher4))
    
    # تست ۵: درآمد
    print("\n💰 تست ۵: درآمد متفرقه")
    income_data = {
        'type': 'income',
        'date': '1405/06/01',
        'amount': 3000000,
        'description': 'فروش ضایعات',
        'to_account': {'type': 'cash', 'id': 1, 'code': '1101', 'name': 'صندوق'},
    }
    
    voucher5 = AutoVoucherEngine.create_from_transaction(income_data)
    print(AutoVoucherEngine.preview_text(voucher5))
    
    print("\n" + "=" * 60)
    print("✅ تست کامل شد!")
