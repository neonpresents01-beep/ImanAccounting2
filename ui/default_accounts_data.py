# ui/default_accounts_data.py
# ============================================================
# ساختار پیش‌فرض حساب‌های حسابداری ایرانی
# ============================================================
# این فایل، لیست حساب‌های استاندارد رو به‌صورت ساختاریافته نگه می‌داره
# و در accounting_tree_widget.py برای ساخت خودکار استفاده می‌شه
# ============================================================
#
# فرمت هر حساب:
# {
#     'code': '1',                    # کد کامل (با جداکننده)
#     'name': 'دارایی‌ها',             # نام
#     'type': 'asset',                # نوع (asset/liability/equity/income/expense)
#     'parent': None,                 # کد والد (None = سطح 1)
#     'description': '...',           # توضیحات (اختیاری)
# }
#
# ============================================================

# انواع حساب‌ها (استاندارد)
TYPE_ASSET = 'asset'           # دارایی
TYPE_LIABILITY = 'liability'   # بدهی
TYPE_EQUITY = 'equity'         # سرمایه
TYPE_INCOME = 'income'         # درآمد
TYPE_EXPENSE = 'expense'       # هزینه

# نام فارسی انواع
TYPE_NAMES = {
    'asset': 'دارایی',
    'liability': 'بدهی',
    'equity': 'سرمایه',
    'income': 'درآمد',
    'expense': 'هزینه',
}


def get_default_accounts(separator='.'):
    """
    دریافت لیست حساب‌های پیش‌فرض
    
    Args:
        separator: جداکننده سطوح (پیش‌فرض '.')
    
    Returns:
        list[dict]: لیست حساب‌ها
    """
    
    def C(*parts):
        """ساخت کد از بخش‌ها"""
        return separator.join(str(p) for p in parts)
    
    accounts = []
    
    # ═══════════════════════════════════════════════════════
    # گروه ۱: دارایی‌ها
    # ═══════════════════════════════════════════════════════
    
    accounts.append({
        'code': C('1'), 'name': 'دارایی‌ها', 'type': TYPE_ASSET,
        'parent': None, 'description': 'کل دارایی‌های شرکت',
    })
    
    # ─── 1.11 دارایی‌های جاری ───
    accounts.append({
        'code': C('1', '11'), 'name': 'دارایی‌های جاری', 'type': TYPE_ASSET,
        'parent': C('1'),
        'description': 'دارایی‌هایی که در کمتر از یک سال به نقد تبدیل می‌شوند',
    })
    
    # 1.11.01 موجودی نقد
    accounts.append({
        'code': C('1', '11', '01'), 'name': 'موجودی نقد', 'type': TYPE_ASSET,
        'parent': C('1', '11'),
    })
    for code_part, name in [
        ('001', 'صندوق'),
        ('002', 'تنخواه گردان'),
        ('003', 'بانک ملت'),
        ('004', 'بانک ملی'),
        ('005', 'بانک صادرات'),
        ('006', 'بانک تجارت'),
        ('007', 'بانک پارسیان'),
        ('008', 'بانک پاسارگاد'),
    ]:
        accounts.append({
            'code': C('1', '11', '01', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '11', '01'),
        })
    
    # 1.11.02 سرمایه‌گذاری کوتاه مدت
    accounts.append({
        'code': C('1', '11', '02'), 'name': 'سرمایه‌گذاری کوتاه مدت',
        'type': TYPE_ASSET, 'parent': C('1', '11'),
    })
    for code_part, name in [
        ('001', 'سپرده کوتاه مدت'),
        ('002', 'سهام بورس'),
        ('003', 'واحدهای صندوق سرمایه‌گذاری'),
    ]:
        accounts.append({
            'code': C('1', '11', '02', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '11', '02'),
        })
    
    # 1.11.03 حساب‌ها و اسناد دریافتنی
    accounts.append({
        'code': C('1', '11', '03'), 'name': 'حساب‌ها و اسناد دریافتنی',
        'type': TYPE_ASSET, 'parent': C('1', '11'),
    })
    for code_part, name in [
        ('001', 'حساب‌های دریافتنی تجاری'),
        ('002', 'اسناد دریافتنی'),
        ('003', 'چک‌های دریافتنی'),
        ('004', 'حساب‌های دریافتنی غیرتجاری'),
        ('005', 'ذخیره مطالبات مشکوک الوصول'),
    ]:
        accounts.append({
            'code': C('1', '11', '03', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '11', '03'),
        })
    
    # 1.11.04 موجودی کالا
    accounts.append({
        'code': C('1', '11', '04'), 'name': 'موجودی کالا',
        'type': TYPE_ASSET, 'parent': C('1', '11'),
    })
    for code_part, name in [
        ('001', 'مواد اولیه'),
        ('002', 'کالای در جریان ساخت'),
        ('003', 'کالای ساخته شده'),
        ('004', 'موجودی کالای بازرگانی'),
        ('005', 'کالای امانی'),
    ]:
        accounts.append({
            'code': C('1', '11', '04', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '11', '04'),
        })
    
    # 1.11.05 پیش‌پرداخت‌ها و سفارشات
    accounts.append({
        'code': C('1', '11', '05'), 'name': 'پیش‌پرداخت‌ها و سفارشات',
        'type': TYPE_ASSET, 'parent': C('1', '11'),
    })
    for code_part, name in [
        ('001', 'پیش‌پرداخت خرید'),
        ('002', 'سفارشات و اعتبارات'),
        ('003', 'پیش‌پرداخت اجاره'),
    ]:
        accounts.append({
            'code': C('1', '11', '05', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '11', '05'),
        })
    
    # 1.11.06 علی‌الحساب‌ها و بیش‌پرداخت‌ها
    accounts.append({
        'code': C('1', '11', '06'), 'name': 'علی‌الحساب‌ها و بیش‌پرداخت‌ها',
        'type': TYPE_ASSET, 'parent': C('1', '11'),
    })
    for code_part, name in [
        ('001', 'علی‌الحساب کارکنان'),
        ('002', 'بیش‌پرداخت به تأمین‌کننده'),
        ('003', 'علی‌الحساب فروشندگان'),
    ]:
        accounts.append({
            'code': C('1', '11', '06', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '11', '06'),
        })
    
    # 1.11.07 مالیات بر ارزش افزوده
    accounts.append({
        'code': C('1', '11', '07'), 'name': 'مالیات بر ارزش افزوده (اعتبار)',
        'type': TYPE_ASSET, 'parent': C('1', '11'),
    })
    accounts.append({
        'code': C('1', '11', '07', '001'),
        'name': 'اعتبار مالیات بر ارزش افزوده',
        'type': TYPE_ASSET, 'parent': C('1', '11', '07'),
    })
    
    # ─── 1.12 دارایی‌های غیرجاری ───
    accounts.append({
        'code': C('1', '12'), 'name': 'دارایی‌های غیرجاری', 'type': TYPE_ASSET,
        'parent': C('1'),
        'description': 'دارایی‌هایی که بیش از یک سال نگهداری می‌شوند',
    })
    
    # 1.12.01 دارایی‌های ثابت مشهود
    accounts.append({
        'code': C('1', '12', '01'), 'name': 'دارایی‌های ثابت مشهود',
        'type': TYPE_ASSET, 'parent': C('1', '12'),
    })
    for code_part, name in [
        ('001', 'زمین'),
        ('002', 'ساختمان'),
        ('003', 'تأسیسات و تجهیزات'),
        ('004', 'ماشین‌آلات'),
        ('005', 'وسایل نقلیه'),
        ('006', 'اثاثیه و منصوبات'),
        ('007', 'ابزار و لوازم کار'),
        ('008', 'تجهیزات اداری'),
    ]:
        accounts.append({
            'code': C('1', '12', '01', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '12', '01'),
        })
    
    # 1.12.02 دارایی‌های نامشهود
    accounts.append({
        'code': C('1', '12', '02'), 'name': 'دارایی‌های نامشهود',
        'type': TYPE_ASSET, 'parent': C('1', '12'),
    })
    for code_part, name in [
        ('001', 'نرم‌افزار و سیستم'),
        ('002', 'سرقفلی و حق‌الامتیاز'),
        ('003', 'علائم تجاری'),
        ('004', 'حق ثبت اختراع'),
    ]:
        accounts.append({
            'code': C('1', '12', '02', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '12', '02'),
        })
    
    # 1.12.03 سایر دارایی‌ها
    accounts.append({
        'code': C('1', '12', '03'), 'name': 'سایر دارایی‌ها',
        'type': TYPE_ASSET, 'parent': C('1', '12'),
    })
    for code_part, name in [
        ('001', 'دارایی‌های راکد'),
        ('002', 'ضمانت‌نامه‌ها'),
    ]:
        accounts.append({
            'code': C('1', '12', '03', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '12', '03'),
        })
    
    # 1.12.04 استهلاک انباشته
    accounts.append({
        'code': C('1', '12', '04'), 'name': 'استهلاک انباشته دارایی‌ها',
        'type': TYPE_ASSET, 'parent': C('1', '12'),
        'description': 'حساب کاهنده دارایی‌ها',
    })
    for code_part, name in [
        ('001', 'استهلاک انباشته ساختمان'),
        ('002', 'استهلاک انباشته ماشین‌آلات'),
        ('003', 'استهلاک انباشته وسایل نقلیه'),
        ('004', 'استهلاک انباشته اثاثیه'),
    ]:
        accounts.append({
            'code': C('1', '12', '04', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '12', '04'),
        })
    
    # ─── 1.13 دارایی‌های بلندمدت ───
    accounts.append({
        'code': C('1', '13'), 'name': 'دارایی‌های بلندمدت', 'type': TYPE_ASSET,
        'parent': C('1'),
    })
    
    accounts.append({
        'code': C('1', '13', '01'), 'name': 'سرمایه‌گذاری بلندمدت',
        'type': TYPE_ASSET, 'parent': C('1', '13'),
    })
    for code_part, name in [
        ('001', 'سهام شرکت‌های فرعی'),
        ('002', 'سپرده بلندمدت'),
    ]:
        accounts.append({
            'code': C('1', '13', '01', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '13', '01'),
        })
    
    accounts.append({
        'code': C('1', '13', '02'), 'name': 'مطالبات بلندمدت',
        'type': TYPE_ASSET, 'parent': C('1', '13'),
    })
    for code_part, name in [
        ('001', 'وام کارکنان'),
        ('002', 'مطالبات مشکوک الوصول بلندمدت'),
    ]:
        accounts.append({
            'code': C('1', '13', '02', code_part), 'name': name,
            'type': TYPE_ASSET, 'parent': C('1', '13', '02'),
        })
    
    # ═══════════════════════════════════════════════════════
    # گروه ۲: بدهی‌ها
    # ═══════════════════════════════════════════════════════
    
    accounts.append({
        'code': C('2'), 'name': 'بدهی‌ها', 'type': TYPE_LIABILITY,
        'parent': None, 'description': 'کل بدهی‌های شرکت',
    })
    
    # ─── 2.21 بدهی‌های جاری ───
    accounts.append({
        'code': C('2', '21'), 'name': 'بدهی‌های جاری', 'type': TYPE_LIABILITY,
        'parent': C('2'),
    })
    
    # 2.21.01 حساب‌ها و اسناد پرداختنی
    accounts.append({
        'code': C('2', '21', '01'), 'name': 'حساب‌ها و اسناد پرداختنی',
        'type': TYPE_LIABILITY, 'parent': C('2', '21'),
    })
    for code_part, name in [
        ('001', 'حساب‌های پرداختنی تجاری'),
        ('002', 'اسناد پرداختنی'),
        ('003', 'چک‌های پرداختنی'),
        ('004', 'حساب‌های پرداختنی غیرتجاری'),
    ]:
        accounts.append({
            'code': C('2', '21', '01', code_part), 'name': name,
            'type': TYPE_LIABILITY, 'parent': C('2', '21', '01'),
        })
    
    # 2.21.02 حقوق و دستمزد پرداختنی
    accounts.append({
        'code': C('2', '21', '02'), 'name': 'حقوق و دستمزد پرداختنی',
        'type': TYPE_LIABILITY, 'parent': C('2', '21'),
    })
    for code_part, name in [
        ('001', 'حقوق پرداختنی'),
        ('002', 'پاداش و اضافه‌کاری'),
        ('003', 'مزایای پایان خدمت'),
    ]:
        accounts.append({
            'code': C('2', '21', '02', code_part), 'name': name,
            'type': TYPE_LIABILITY, 'parent': C('2', '21', '02'),
        })
    
    # 2.21.03 مالیات پرداختنی
    accounts.append({
        'code': C('2', '21', '03'), 'name': 'مالیات پرداختنی',
        'type': TYPE_LIABILITY, 'parent': C('2', '21'),
    })
    for code_part, name in [
        ('001', 'مالیات بر درآمد'),
        ('002', 'مالیات بر ارزش افزوده'),
        ('003', 'عوارض و جریمه‌ها'),
    ]:
        accounts.append({
            'code': C('2', '21', '03', code_part), 'name': name,
            'type': TYPE_LIABILITY, 'parent': C('2', '21', '03'),
        })
    
    # 2.21.04 بیمه پرداختنی
    accounts.append({
        'code': C('2', '21', '04'), 'name': 'بیمه پرداختنی',
        'type': TYPE_LIABILITY, 'parent': C('2', '21'),
    })
    for code_part, name in [
        ('001', 'بیمه تأمین اجتماعی'),
        ('002', 'بیمه تکمیلی'),
    ]:
        accounts.append({
            'code': C('2', '21', '04', code_part), 'name': name,
            'type': TYPE_LIABILITY, 'parent': C('2', '21', '04'),
        })
    
    # 2.21.05 پیش‌دریافت‌ها
    accounts.append({
        'code': C('2', '21', '05'), 'name': 'پیش‌دریافت‌ها',
        'type': TYPE_LIABILITY, 'parent': C('2', '21'),
    })
    for code_part, name in [
        ('001', 'پیش‌دریافت فروش'),
        ('002', 'پیش‌دریافت سفارشات'),
    ]:
        accounts.append({
            'code': C('2', '21', '05', code_part), 'name': name,
            'type': TYPE_LIABILITY, 'parent': C('2', '21', '05'),
        })
    
    # 2.21.06 ذخایر جاری
    accounts.append({
        'code': C('2', '21', '06'), 'name': 'ذخایر جاری',
        'type': TYPE_LIABILITY, 'parent': C('2', '21'),
    })
    for code_part, name in [
        ('001', 'ذخیره مالیات'),
        ('002', 'ذخیره مطالبات مشکوک'),
    ]:
        accounts.append({
            'code': C('2', '21', '06', code_part), 'name': name,
            'type': TYPE_LIABILITY, 'parent': C('2', '21', '06'),
        })
    
    # 2.21.07 بدهی‌های متفرقه
    accounts.append({
        'code': C('2', '21', '07'), 'name': 'بدهی‌های متفرقه و هزینه‌های معوق',
        'type': TYPE_LIABILITY, 'parent': C('2', '21'),
    })
    for code_part, name in [
        ('001', 'هزینه‌های معوق'),
        ('002', 'بدهی‌های متفرقه'),
    ]:
        accounts.append({
            'code': C('2', '21', '07', code_part), 'name': name,
            'type': TYPE_LIABILITY, 'parent': C('2', '21', '07'),
        })
    
    # ─── 2.22 بدهی‌های غیرجاری ───
    accounts.append({
        'code': C('2', '22'), 'name': 'بدهی‌های غیرجاری',
        'type': TYPE_LIABILITY, 'parent': C('2'),
    })
    
    accounts.append({
        'code': C('2', '22', '01'), 'name': 'تسهیلات مالی بلندمدت',
        'type': TYPE_LIABILITY, 'parent': C('2', '22'),
    })
    for code_part, name in [
        ('001', 'وام بلندمدت بانکی'),
        ('002', 'تسهیلات لیزینگ'),
    ]:
        accounts.append({
            'code': C('2', '22', '01', code_part), 'name': name,
            'type': TYPE_LIABILITY, 'parent': C('2', '22', '01'),
        })
    
    accounts.append({
        'code': C('2', '22', '02'), 'name': 'ذخیره مزایای پایان خدمت',
        'type': TYPE_LIABILITY, 'parent': C('2', '22'),
    })
    accounts.append({
        'code': C('2', '22', '02', '001'), 'name': 'ذخیره بازخرید خدمت',
        'type': TYPE_LIABILITY, 'parent': C('2', '22', '02'),
    })
    
    accounts.append({
        'code': C('2', '22', '03'), 'name': 'اوراق قرضه پرداختنی',
        'type': TYPE_LIABILITY, 'parent': C('2', '22'),
    })
    accounts.append({
        'code': C('2', '22', '03', '001'), 'name': 'اوراق قرضه',
        'type': TYPE_LIABILITY, 'parent': C('2', '22', '03'),
    })
    
    # ═══════════════════════════════════════════════════════
    # گروه ۳: سرمایه
    # ═══════════════════════════════════════════════════════
    
    accounts.append({
        'code': C('3'), 'name': 'سرمایه و حقوق صاحبان سهام',
        'type': TYPE_EQUITY, 'parent': None,
    })
    
    # ─── 3.31 سرمایه اولیه ───
    accounts.append({
        'code': C('3', '31'), 'name': 'سرمایه اولیه', 'type': TYPE_EQUITY,
        'parent': C('3'),
    })
    
    accounts.append({
        'code': C('3', '31', '01'), 'name': 'سرمایه', 'type': TYPE_EQUITY,
        'parent': C('3', '31'),
    })
    accounts.append({
        'code': C('3', '31', '01', '001'), 'name': 'سرمایه ثبت شده',
        'type': TYPE_EQUITY, 'parent': C('3', '31', '01'),
    })
    
    accounts.append({
        'code': C('3', '31', '02'), 'name': 'آورده شرکا',
        'type': TYPE_EQUITY, 'parent': C('3', '31'),
    })
    for code_part, name in [
        ('001', 'آورده نقدی'),
        ('002', 'آورده غیرنقدی'),
    ]:
        accounts.append({
            'code': C('3', '31', '02', code_part), 'name': name,
            'type': TYPE_EQUITY, 'parent': C('3', '31', '02'),
        })
    
    # ─── 3.32 برداشت‌ها ───
    accounts.append({
        'code': C('3', '32'), 'name': 'برداشت‌ها', 'type': TYPE_EQUITY,
        'parent': C('3'),
    })
    
    accounts.append({
        'code': C('3', '32', '01'), 'name': 'برداشت شخصی',
        'type': TYPE_EQUITY, 'parent': C('3', '32'),
    })
    accounts.append({
        'code': C('3', '32', '01', '001'), 'name': 'برداشت مالک',
        'type': TYPE_EQUITY, 'parent': C('3', '32', '01'),
    })
    
    accounts.append({
        'code': C('3', '32', '02'), 'name': 'برداشت شرکا',
        'type': TYPE_EQUITY, 'parent': C('3', '32'),
    })
    accounts.append({
        'code': C('3', '32', '02', '001'), 'name': 'سود سهام پرداختی',
        'type': TYPE_EQUITY, 'parent': C('3', '32', '02'),
    })
    
    # ─── 3.33 سود و زیان ───
    accounts.append({
        'code': C('3', '33'), 'name': 'سود و زیان انباشته',
        'type': TYPE_EQUITY, 'parent': C('3'),
    })
    
    accounts.append({
        'code': C('3', '33', '01'), 'name': 'سود و زیان دوره جاری',
        'type': TYPE_EQUITY, 'parent': C('3', '33'),
    })
    accounts.append({
        'code': C('3', '33', '01', '001'), 'name': 'سود (زیان) سال جاری',
        'type': TYPE_EQUITY, 'parent': C('3', '33', '01'),
    })
    
    accounts.append({
        'code': C('3', '33', '02'), 'name': 'سود و زیان انباشته',
        'type': TYPE_EQUITY, 'parent': C('3', '33'),
    })
    for code_part, name in [
        ('001', 'سود انباشته'),
        ('002', 'زیان انباشته'),
    ]:
        accounts.append({
            'code': C('3', '33', '02', code_part), 'name': name,
            'type': TYPE_EQUITY, 'parent': C('3', '33', '02'),
        })
    
    # ─── 3.34 اندوخته‌ها ───
    accounts.append({
        'code': C('3', '34'), 'name': 'اندوخته‌ها', 'type': TYPE_EQUITY,
        'parent': C('3'),
    })
    
    accounts.append({
        'code': C('3', '34', '01'), 'name': 'اندوخته قانونی',
        'type': TYPE_EQUITY, 'parent': C('3', '34'),
    })
    accounts.append({
        'code': C('3', '34', '01', '001'), 'name': 'اندوخته قانونی',
        'type': TYPE_EQUITY, 'parent': C('3', '34', '01'),
    })
    
    accounts.append({
        'code': C('3', '34', '02'), 'name': 'اندوخته احتیاطی',
        'type': TYPE_EQUITY, 'parent': C('3', '34'),
    })
    accounts.append({
        'code': C('3', '34', '02', '001'), 'name': 'اندوخته احتیاطی',
        'type': TYPE_EQUITY, 'parent': C('3', '34', '02'),
    })
    
    # ═══════════════════════════════════════════════════════
    # گروه ۴: درآمدها
    # ═══════════════════════════════════════════════════════
    
    accounts.append({
        'code': C('4'), 'name': 'درآمدها', 'type': TYPE_INCOME,
        'parent': None,
    })
    
    # ─── 4.41 درآمدهای عملیاتی ───
    accounts.append({
        'code': C('4', '41'), 'name': 'درآمدهای عملیاتی',
        'type': TYPE_INCOME, 'parent': C('4'),
    })
    
    accounts.append({
        'code': C('4', '41', '01'), 'name': 'فروش کالا',
        'type': TYPE_INCOME, 'parent': C('4', '41'),
    })
    for code_part, name in [
        ('001', 'فروش کالای داخلی'),
        ('002', 'فروش کالای صادراتی'),
    ]:
        accounts.append({
            'code': C('4', '41', '01', code_part), 'name': name,
            'type': TYPE_INCOME, 'parent': C('4', '41', '01'),
        })
    
    accounts.append({
        'code': C('4', '41', '02'), 'name': 'فروش خدمات',
        'type': TYPE_INCOME, 'parent': C('4', '41'),
    })
    for code_part, name in [
        ('001', 'خدمات فنی'),
        ('002', 'خدمات مشاوره'),
        ('003', 'خدمات آموزشی'),
    ]:
        accounts.append({
            'code': C('4', '41', '02', code_part), 'name': name,
            'type': TYPE_INCOME, 'parent': C('4', '41', '02'),
        })
    
    accounts.append({
        'code': C('4', '41', '03'), 'name': 'برگشت از فروش',
        'type': TYPE_INCOME, 'parent': C('4', '41'),
        'description': 'حساب کاهنده درآمد',
    })
    accounts.append({
        'code': C('4', '41', '03', '001'), 'name': 'برگشت از فروش',
        'type': TYPE_INCOME, 'parent': C('4', '41', '03'),
    })
    
    accounts.append({
        'code': C('4', '41', '04'), 'name': 'تخفیفات نقدی فروش',
        'type': TYPE_INCOME, 'parent': C('4', '41'),
    })
    accounts.append({
        'code': C('4', '41', '04', '001'), 'name': 'تخفیف نقدی',
        'type': TYPE_INCOME, 'parent': C('4', '41', '04'),
    })
    
    # ─── 4.42 درآمدهای غیرعملیاتی ───
    accounts.append({
        'code': C('4', '42'), 'name': 'درآمدهای غیرعملیاتی',
        'type': TYPE_INCOME, 'parent': C('4'),
    })
    
    accounts.append({
        'code': C('4', '42', '01'), 'name': 'درآمدهای مالی',
        'type': TYPE_INCOME, 'parent': C('4', '42'),
    })
    for code_part, name in [
        ('001', 'سود بانکی'),
        ('002', 'سود سپرده'),
    ]:
        accounts.append({
            'code': C('4', '42', '01', code_part), 'name': name,
            'type': TYPE_INCOME, 'parent': C('4', '42', '01'),
        })
    
    accounts.append({
        'code': C('4', '42', '02'), 'name': 'درآمدهای سرمایه‌گذاری',
        'type': TYPE_INCOME, 'parent': C('4', '42'),
    })
    for code_part, name in [
        ('001', 'سود سهام'),
        ('002', 'سود فروش سرمایه‌گذاری'),
    ]:
        accounts.append({
            'code': C('4', '42', '02', code_part), 'name': name,
            'type': TYPE_INCOME, 'parent': C('4', '42', '02'),
        })
    
    accounts.append({
        'code': C('4', '42', '03'), 'name': 'درآمدهای متفرقه',
        'type': TYPE_INCOME, 'parent': C('4', '42'),
    })
    for code_part, name in [
        ('001', 'درآمد اجاره'),
        ('002', 'فروش ضایعات'),
        ('003', 'تخفیف دریافتی'),
        ('004', 'سایر درآمدها'),
    ]:
        accounts.append({
            'code': C('4', '42', '03', code_part), 'name': name,
            'type': TYPE_INCOME, 'parent': C('4', '42', '03'),
        })
    
    # ─── 4.43 درآمدهای انتقالی ───
    accounts.append({
        'code': C('4', '43'), 'name': 'درآمدهای انتقالی و غیره',
        'type': TYPE_INCOME, 'parent': C('4'),
    })
    accounts.append({
        'code': C('4', '43', '01'), 'name': 'درآمدهای انتقالی',
        'type': TYPE_INCOME, 'parent': C('4', '43'),
    })
    for code_part, name in [
        ('001', 'کمک‌های بلاعوض'),
        ('002', 'هدایا'),
    ]:
        accounts.append({
            'code': C('4', '43', '01', code_part), 'name': name,
            'type': TYPE_INCOME, 'parent': C('4', '43', '01'),
        })
    
    # ═══════════════════════════════════════════════════════
    # گروه ۵: هزینه‌ها
    # ═══════════════════════════════════════════════════════
    
    accounts.append({
        'code': C('5'), 'name': 'هزینه‌ها', 'type': TYPE_EXPENSE,
        'parent': None,
    })
    
    # ─── 5.51 بهای تمام شده ───
    accounts.append({
        'code': C('5', '51'), 'name': 'بهای تمام شده',
        'type': TYPE_EXPENSE, 'parent': C('5'),
    })
    
    accounts.append({
        'code': C('5', '51', '01'), 'name': 'بهای تمام شده کالای فروش رفته',
        'type': TYPE_EXPENSE, 'parent': C('5', '51'),
    })
    accounts.append({
        'code': C('5', '51', '01', '001'),
        'name': 'بهای تمام شده کالای فروش رفته',
        'type': TYPE_EXPENSE, 'parent': C('5', '51', '01'),
    })
    
    accounts.append({
        'code': C('5', '51', '02'), 'name': 'خرید کالا',
        'type': TYPE_EXPENSE, 'parent': C('5', '51'),
    })
    accounts.append({
        'code': C('5', '51', '02', '001'), 'name': 'خرید کالا',
        'type': TYPE_EXPENSE, 'parent': C('5', '51', '02'),
    })
    
    accounts.append({
        'code': C('5', '51', '03'), 'name': 'برگشت از خرید',
        'type': TYPE_EXPENSE, 'parent': C('5', '51'),
        'description': 'حساب کاهنده هزینه',
    })
    accounts.append({
        'code': C('5', '51', '03', '001'), 'name': 'برگشت از خرید',
        'type': TYPE_EXPENSE, 'parent': C('5', '51', '03'),
    })
    
    # ─── 5.52 هزینه‌های عملیاتی ───
    accounts.append({
        'code': C('5', '52'), 'name': 'هزینه‌های عملیاتی',
        'type': TYPE_EXPENSE, 'parent': C('5'),
    })
    
    # 5.52.01 هزینه‌های پرسنلی
    accounts.append({
        'code': C('5', '52', '01'), 'name': 'هزینه‌های پرسنلی',
        'type': TYPE_EXPENSE, 'parent': C('5', '52'),
    })
    for code_part, name in [
        ('001', 'حقوق و دستمزد'),
        ('002', 'مزایای پرسنلی'),
        ('003', 'بیمه سهم کارفرما'),
        ('004', 'هزینه ایاب و ذهاب'),
        ('005', 'آموزش پرسنل'),
        ('006', 'پاداش و اضافه‌کاری'),
    ]:
        accounts.append({
            'code': C('5', '52', '01', code_part), 'name': name,
            'type': TYPE_EXPENSE, 'parent': C('5', '52', '01'),
        })
    
    # 5.52.02 هزینه‌های عمومی و اداری
    accounts.append({
        'code': C('5', '52', '02'), 'name': 'هزینه‌های عمومی و اداری',
        'type': TYPE_EXPENSE, 'parent': C('5', '52'),
    })
    for code_part, name in [
        ('001', 'اجاره'),
        ('002', 'آب و برق و گاز'),
        ('003', 'تلفن و اینترنت'),
        ('004', 'ملزومات مصرفی'),
        ('005', 'پذیرایی'),
        ('006', 'هزینه‌های اداری متفرقه'),
        ('007', 'هزینه‌های پستی'),
        ('008', 'هزینه‌های چاپ و تکثیر'),
    ]:
        accounts.append({
            'code': C('5', '52', '02', code_part), 'name': name,
            'type': TYPE_EXPENSE, 'parent': C('5', '52', '02'),
        })
    
    # 5.52.03 هزینه‌های فروش و بازاریابی
    accounts.append({
        'code': C('5', '52', '03'), 'name': 'هزینه‌های فروش و بازاریابی',
        'type': TYPE_EXPENSE, 'parent': C('5', '52'),
    })
    for code_part, name in [
        ('001', 'تبلیغات'),
        ('002', 'هزینه‌های بازاریابی'),
        ('003', 'کمیسیون فروش'),
        ('004', 'حمل و نقل فروش'),
    ]:
        accounts.append({
            'code': C('5', '52', '03', code_part), 'name': name,
            'type': TYPE_EXPENSE, 'parent': C('5', '52', '03'),
        })
    
    # 5.52.04 هزینه‌های استهلاک
    accounts.append({
        'code': C('5', '52', '04'), 'name': 'هزینه‌های استهلاک',
        'type': TYPE_EXPENSE, 'parent': C('5', '52'),
    })
    for code_part, name in [
        ('001', 'استهلاک ساختمان'),
        ('002', 'استهلاک ماشین‌آلات'),
        ('003', 'استهلاک وسایل نقلیه'),
        ('004', 'استهلاک نرم‌افزار'),
    ]:
        accounts.append({
            'code': C('5', '52', '04', code_part), 'name': name,
            'type': TYPE_EXPENSE, 'parent': C('5', '52', '04'),
        })
    
    # 5.52.05 هزینه‌های مالی و بانکی
    accounts.append({
        'code': C('5', '52', '05'), 'name': 'هزینه‌های مالی و بانکی',
        'type': TYPE_EXPENSE, 'parent': C('5', '52'),
    })
    for code_part, name in [
        ('001', 'کارمزد بانکی'),
        ('002', 'سود تسهیلات'),
    ]:
        accounts.append({
            'code': C('5', '52', '05', code_part), 'name': name,
            'type': TYPE_EXPENSE, 'parent': C('5', '52', '05'),
        })
    
    # 5.52.06 مالیات و عوارض
    accounts.append({
        'code': C('5', '52', '06'), 'name': 'مالیات و عوارض',
        'type': TYPE_EXPENSE, 'parent': C('5', '52'),
    })
    accounts.append({
        'code': C('5', '52', '06', '001'), 'name': 'مالیات و عوارض',
        'type': TYPE_EXPENSE, 'parent': C('5', '52', '06'),
    })
    
    # ─── 5.53 هزینه‌های غیرعملیاتی ───
    accounts.append({
        'code': C('5', '53'), 'name': 'هزینه‌های غیرعملیاتی',
        'type': TYPE_EXPENSE, 'parent': C('5'),
    })
    
    accounts.append({
        'code': C('5', '53', '01'), 'name': 'هزینه‌های مالی',
        'type': TYPE_EXPENSE, 'parent': C('5', '53'),
    })
    accounts.append({
        'code': C('5', '53', '01', '001'), 'name': 'سود و کارمزد وام',
        'type': TYPE_EXPENSE, 'parent': C('5', '53', '01'),
    })
    
    accounts.append({
        'code': C('5', '53', '02'), 'name': 'جریمه‌ها و خسارات',
        'type': TYPE_EXPENSE, 'parent': C('5', '53'),
    })
    for code_part, name in [
        ('001', 'جریمه‌های مالیاتی'),
        ('002', 'خسارات'),
    ]:
        accounts.append({
            'code': C('5', '53', '02', code_part), 'name': name,
            'type': TYPE_EXPENSE, 'parent': C('5', '53', '02'),
        })
    
    accounts.append({
        'code': C('5', '53', '03'), 'name': 'هزینه‌های متفرقه',
        'type': TYPE_EXPENSE, 'parent': C('5', '53'),
    })
    accounts.append({
        'code': C('5', '53', '03', '001'), 'name': 'هزینه‌های پیش‌بینی نشده',
        'type': TYPE_EXPENSE, 'parent': C('5', '53', '03'),
    })
    
    return accounts


# تعداد کل حساب‌ها
TOTAL_DEFAULT_ACCOUNTS = len(get_default_accounts())
