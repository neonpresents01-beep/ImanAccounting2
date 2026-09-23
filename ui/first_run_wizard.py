# ui/first_run_wizard.py
# ============================================================
# First-Run Wizard — راه‌اندازی اولیه ImanAccount
# نسخه 1.0 (Production-Ready)
# ============================================================
# ۴ مرحله:
#   1. خوش‌آمد + اطلاعات شرکت
#   2. ساخت کاربر مدیر (نام کاربری + رمز قوی)
#   3. تنظیمات منطقه‌ای (واحد پول، تاریخ)
#   4. پایان
# ============================================================

import logging
from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QPushButton, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon

from database import get_db
from security import PasswordHasher

logger = logging.getLogger(__name__)


# ============================================================
# ========== استایل‌ها ==========
# ============================================================

WIZARD_STYLE = """
QWizard {
    background: #f5f6fa;
}
QWizardPage {
    background: transparent;
}
QLabel {
    color: #1a1a2e;
    font-size: 11pt;
}
QLabel#title {
    color: #e94560;
    font-size: 20pt;
    font-weight: bold;
    padding: 10px 0;
}
QLabel#subtitle {
    color: #666;
    font-size: 11pt;
    padding-bottom: 15px;
}
QLabel#hint {
    color: #888;
    font-size: 9pt;
    padding: 5px;
}
QLineEdit, QTextEdit, QComboBox {
    background: white;
    color: #1a1a2e;
    border: 2px solid #dcdde1;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 11pt;
    min-height: 32px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border-color: #e94560;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QCheckBox {
    color: #1a1a2e;
    font-size: 11pt;
    padding: 5px;
    spacing: 8px;
}
QPushButton {
    background: #1976D2;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 11pt;
    min-height: 36px;
    min-width: 100px;
}
QPushButton:hover {
    background: #1565C0;
}
QPushButton:disabled {
    background: #ccc;
    color: #888;
}
QProgressBar {
    border: 2px solid #dcdde1;
    border-radius: 6px;
    background: white;
    height: 20px;
    text-align: center;
    color: #1a1a2e;
}
QProgressBar::chunk {
    background: #27ae60;
    border-radius: 3px;
}
"""


# ============================================================
# ========== صفحه ۱: خوش‌آمد + اطلاعات شرکت ==========
# ============================================================

class WelcomePage(QWizardPage):
    """صفحه خوش‌آمد و اطلاعات شرکت"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("👋 خوش آمدید به ImanAccount")
        self.setSubTitle("بیایید در چند مرحله ساده، برنامه را تنظیم کنیم")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # خوش‌آمد
        welcome = QLabel(
            "🎉 به ImanAccount خوش آمدید!\n\n"
            "این نرم‌افزار به شما کمک می‌کند:\n"
            "  ✅ فاکتور فروش و خرید بزنید\n"
            "  ✅ موجودی انبار را مدیریت کنید\n"
            "  ✅ حقوق پرسنل را محاسبه کنید\n"
            "  ✅ گزارشات مالی دقیق بگیرید\n\n"
            "بیایید در ۴ مرحله ساده، برنامه را راه‌اندازی کنیم."
        )
        welcome.setWordWrap(True)
        welcome.setStyleSheet("""
            font-size: 11pt;
            color: #2c3e50;
            background: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            line-height: 1.6;
        """)
        layout.addWidget(welcome)
        
        layout.addSpacing(10)
        
        # عنوان بخش
        section = QLabel("📋 اطلاعات کسب‌وکار")
        section.setStyleSheet("font-size: 13pt; font-weight: bold; color: #e94560;")
        layout.addWidget(section)
        
        # فرم
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        
        # نام شرکت
        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("مثال: فروشگاه رضایی")
        form.addRow("نام کسب‌وکار *:", self.company_name)
        
        # نام حقوقی
        self.company_legal = QLineEdit()
        self.company_legal.setPlaceholderText("اختیاری")
        form.addRow("نام حقوقی:", self.company_legal)
        
        # تلفن
        self.company_phone = QLineEdit()
        self.company_phone.setPlaceholderText("مثال: 021-12345678")
        form.addRow("تلفن:", self.company_phone)
        
        # کد اقتصادی
        self.company_economic = QLineEdit()
        self.company_economic.setPlaceholderText("اختیاری")
        form.addRow("کد اقتصادی:", self.company_economic)
        
        # آدرس
        self.company_address = QTextEdit()
        self.company_address.setPlaceholderText("آدرس کامل")
        self.company_address.setMaximumHeight(80)
        form.addRow("آدرس:", self.company_address)
        
        layout.addLayout(form)
        
        # راهنما
        hint = QLabel("💡 این اطلاعات در فاکتورها و گزارشات نمایش داده می‌شود")
        hint.setObjectName("hint")
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # ✅ اتصال سیگنال‌ها
        self.company_name.textChanged.connect(self.completeChanged)
    
    def isComplete(self):
        """آیا صفحه کامل است؟"""
        return bool(self.company_name.text().strip())
    
    def validatePage(self):
        """اعتبارسنجی قبل از رفتن به مرحله بعد"""
        if not self.company_name.text().strip():
            QMessageBox.warning(
                self, "خطا",
                "لطفاً نام کسب‌وکار را وارد کنید."
            )
            return False
        return True
    
    def get_data(self):
        """دریافت داده‌های صفحه"""
        return {
            'company_name': self.company_name.text().strip(),
            'company_legal_name': self.company_legal.text().strip(),
            'company_phone': self.company_phone.text().strip(),
            'company_economic': self.company_economic.text().strip(),
            'company_address': self.company_address.toPlainText().strip(),
        }


# ============================================================
# ========== صفحه ۲: ساخت کاربر مدیر ==========
# ============================================================

class AdminUserPage(QWizardPage):
    """صفحه ساخت کاربر مدیر"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("👤 ساخت حساب مدیر")
        self.setSubTitle("یک حساب مدیر برای خودتان بسازید")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # توضیح
        info = QLabel(
            "🔐 این حساب، دسترسی کامل به تمام بخش‌های برنامه دارد.\n"
            "لطفاً یک نام کاربری و رمز عبور قوی انتخاب کنید."
        )
        info.setWordWrap(True)
        info.setStyleSheet("""
            font-size: 11pt;
            color: #2c3e50;
            background: #fff3cd;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #f39c12;
        """)
        layout.addWidget(info)
        
        layout.addSpacing(10)
        
        # فرم
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        
        # نام کامل
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("نام و نام خانوادگی")
        form.addRow("نام کامل *:", self.full_name)
        
        # نام کاربری
        self.username = QLineEdit()
        self.username.setPlaceholderText("مثال: admin یا manager")
        self.username.setText("admin")
        form.addRow("نام کاربری *:", self.username)
        
        # رمز عبور
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("حداقل ۶ کاراکتر")
        self.password.textChanged.connect(self._update_strength)
        form.addRow("رمز عبور *:", self.password)
        
        # نمایش قدرت رمز
        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(True)
        self.strength_bar.setFormat("قدرت رمز: %p%")
        form.addRow("", self.strength_bar)
        
        # تکرار رمز
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.Password)
        self.confirm.setPlaceholderText("تکرار رمز عبور")
        self.confirm.textChanged.connect(self.completeChanged)
        form.addRow("تکرار رمز *:", self.confirm)
        
        layout.addLayout(form)
        
        # چک‌لیست رمز قوی
        checklist = QLabel(
            "🔒 رمز عبور قوی شامل:\n"
            "  • حداقل ۶ کاراکتر\n"
            "  • حروف کوچک و بزرگ (a-z, A-Z)\n"
            "  • اعداد (0-9)\n"
            "  • کاراکترهای خاص (!@#$%...)"
        )
        checklist.setObjectName("hint")
        checklist.setStyleSheet("""
            color: #666;
            font-size: 9pt;
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            line-height: 1.6;
        """)
        layout.addWidget(checklist)
        
        layout.addStretch()
        
        # اتصال
        self.full_name.textChanged.connect(self.completeChanged)
        self.username.textChanged.connect(self.completeChanged)
        self.password.textChanged.connect(self.completeChanged)
    
    def _update_strength(self):
        """بروزرسانی قدرت رمز"""
        password = self.password.text()
        score = PasswordHasher.get_password_strength_score(password)
        
        self.strength_bar.setValue(score)
        
        # رنگ
        if score < 30:
            color = "#e74c3c"
            text = "ضعیف"
        elif score < 60:
            color = "#f39c12"
            text = "متوسط"
        elif score < 85:
            color = "#3498db"
            text = "خوب"
        else:
            color = "#27ae60"
            text = "قوی"
        
        self.strength_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #dcdde1;
                border-radius: 6px;
                background: white;
                height: 20px;
                text-align: center;
                color: #1a1a2e;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 3px;
            }}
        """)
        self.strength_bar.setFormat(f"قدرت رمز: {text} (%p%)")
    
    def isComplete(self):
        """آیا صفحه کامل است؟"""
        full_name = self.full_name.text().strip()
        username = self.username.text().strip()
        password = self.password.text()
        confirm = self.confirm.text()
        
        if not full_name or len(full_name) < 3:
            return False
        if not username or len(username) < 3:
            return False
        if not password or len(password) < 6:
            return False
        if password != confirm:
            return False
        
        return True
    
    def validatePage(self):
        """اعتبارسنجی نهایی"""
        full_name = self.full_name.text().strip()
        username = self.username.text().strip()
        password = self.password.text()
        confirm = self.confirm.text()
        
        # نام کامل
        if not full_name or len(full_name) < 3:
            QMessageBox.warning(
                self, "خطا",
                "نام کامل باید حداقل ۳ کاراکتر باشد."
            )
            return False
        
        # نام کاربری
        if not username or len(username) < 3:
            QMessageBox.warning(
                self, "خطا",
                "نام کاربری باید حداقل ۳ کاراکتر باشد."
            )
            return False
        
        if not username.replace('_', '').replace('.', '').isalnum():
            QMessageBox.warning(
                self, "خطا",
                "نام کاربری فقط می‌تواند شامل حروف، اعداد، _ و . باشد."
            )
            return False
        
        # رمز عبور
        is_valid, msg = PasswordHasher.validate_password_strength(password)
        if not is_valid:
            QMessageBox.warning(self, "خطا", msg)
            return False
        
        # تطابق
        if password != confirm:
            QMessageBox.warning(
                self, "خطا",
                "رمز عبور با تکرار آن مطابقت ندارد."
            )
            return False
        
        return True
    
    def get_data(self):
        """دریافت داده‌ها"""
        return {
            'full_name': self.full_name.text().strip(),
            'username': self.username.text().strip(),
            'password': self.password.text(),
        }


# ============================================================
# ========== صفحه ۳: تنظیمات منطقه‌ای ==========
# ============================================================

class RegionalPage(QWizardPage):
    """صفحه تنظیمات منطقه‌ای"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🌍 تنظیمات منطقه‌ای")
        self.setSubTitle("واحد پول، تاریخ و مالیات را انتخاب کنید")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # توضیح
        info = QLabel(
            "این تنظیمات بعداً از بخش «تنظیمات» قابل تغییر هستند."
        )
        info.setStyleSheet("color: #666; font-size: 10pt; padding: 5px;")
        layout.addWidget(info)
        
        # فرم
        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignRight)
        
        # واحد پول
        self.currency = QComboBox()
        self.currency.addItems(["ریال", "تومان", "دلار", "یورو"])
        self.currency.setCurrentText("تومان")
        form.addRow("💰 واحد پول:", self.currency)
        
        # سیستم تاریخ
        self.date_system = QComboBox()
        self.date_system.addItems(["شمسی", "میلادی"])
        self.date_system.setCurrentText("شمسی")
        form.addRow("📅 سیستم تاریخ:", self.date_system)
        
        # نرخ مالیات
        self.tax_rate = QLineEdit()
        self.tax_rate.setText("10")
        self.tax_rate.setPlaceholderText("مثال: 10")
        form.addRow("📊 نرخ مالیات (%):", self.tax_rate)
        
        # سال مالی
        self.fiscal_year = QLineEdit()
        from shamsi_date import get_today_jalali
        today = get_today_jalali()
        year = today.split('/')[0] if '/' in today else '1404'
        self.fiscal_year.setText(year)
        self.fiscal_year.setPlaceholderText("مثال: 1404")
        form.addRow("📆 سال مالی:", self.fiscal_year)
        
        layout.addLayout(form)
        
        layout.addSpacing(10)
        
        # چک‌باکس: ایجاد داده نمونه
        self.create_sample = QCheckBox(
            "📦 ایجاد داده‌های نمونه (مشتری، کالا، اسناد تست)"
        )
        self.create_sample.setChecked(True)
        layout.addWidget(self.create_sample)
        
        hint = QLabel(
            "💡 اگه تازه‌کار هستید، گزینه «داده نمونه» را فعال کنید\n"
            "تا برنامه را با داده‌های تستی ببینید."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        layout.addStretch()
    
    def get_data(self):
        """دریافت داده‌ها"""
        try:
            tax_rate = float(self.tax_rate.text().strip() or '10')
        except:
            tax_rate = 10.0
        
        try:
            fiscal_year = int(self.fiscal_year.text().strip() or '1404')
        except:
            fiscal_year = 1404
        
        return {
            'currency': self.currency.currentText(),
            'date_system': self.date_system.currentText(),
            'tax_rate': tax_rate,
            'fiscal_year': fiscal_year,
            'create_sample': self.create_sample.isChecked(),
        }


# ============================================================
# ========== صفحه ۴: پایان ==========
# ============================================================

class FinishPage(QWizardPage):
    """صفحه پایان"""
    
    def __init__(self, wizard):
        super().__init__()
        self.wizard_ref = wizard
        
        self.setTitle("✅ آماده شروع!")
        self.setSubTitle("همه چیز آماده است")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # پیام موفقیت
        success = QLabel(
            "🎉 <b>راه‌اندازی با موفقیت انجام شد!</b>\n\n"
            "اطلاعات ورود شما:\n"
            "  👤 نام کاربری: <b>{username}</b>\n"
            "  🔑 رمز عبور: <b>همان که وارد کردید</b>\n\n"
            "⚠️ لطفاً این اطلاعات را در جای امنی نگه دارید."
        )
        success.setWordWrap(True)
        success.setStyleSheet("""
            font-size: 11pt;
            color: #155724;
            background: #d4edda;
            padding: 15px;
            border-radius: 8px;
            line-height: 1.8;
        """)
        layout.addWidget(success)
        
        # اطلاعات پشتیبانی
        support = QLabel(
            "📞 <b>پشتیبانی:</b>\n\n"
            "برای هرگونه سؤال یا مشکل با ما تماس بگیرید:\n"
            "  • تلفن: 021-XXXXXXXX\n"
            "  • ایمیل: support@imanai.ir\n"
            "  • ساعات: شنبه تا چهارشنبه ۹ تا ۱۸"
        )
        support.setWordWrap(True)
        support.setStyleSheet("""
            font-size: 10pt;
            color: #2c3e50;
            background: #e7f3ff;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #1976D2;
            line-height: 1.8;
        """)
        layout.addWidget(support)
        
        layout.addStretch()
        
        # نکته آخر
        tip = QLabel(
            "💡 <b>نکته:</b> پس از ورود، از بخش «تنظیمات» می‌توانید\n"
            "تمام اطلاعات را تغییر دهید یا کاربران جدید بسازید."
        )
        tip.setWordWrap(True)
        tip.setObjectName("hint")
        layout.addWidget(tip)
    
    def initializePage(self):
        """وقتی صفحه باز میشه، اطلاعات کاربر رو نشون بده"""
        if not self.wizard_ref:
            return
        
        username = self.wizard_ref.get_username()
        
        # پیدا کردن label
        for child in self.findChildren(QLabel):
            if "نام کاربری" in child.text():
                child.setText(
                    child.text().replace("{username}", username)
                )
                break


# ============================================================
# ========== کلاس اصلی Wizard ==========
# ============================================================

class FirstRunWizard(QWizard):
    """ویزارد راه‌اندازی اولیه"""
    
    # سیگنال‌ها
    setup_completed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("🚀 راه‌اندازی ImanAccount")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.NoCancelButtonOnLastPage, False)
        self.setOption(QWizard.HaveHelpButton, False)
        self.setOption(QWizard.HaveFinishButtonOnEarlyPages, False)
        
        self.setMinimumSize(700, 550)
        self.setStyleSheet(WIZARD_STYLE)
        
        # ✅ ساخت صفحات
        self.welcome_page = WelcomePage()
        self.admin_page = AdminUserPage()
        self.regional_page = RegionalPage()
        self.finish_page = FinishPage(self)
        
        self.addPage(self.welcome_page)
        self.addPage(self.admin_page)
        self.addPage(self.regional_page)
        self.addPage(self.finish_page)
        
        # دکمه‌ها
        self.setButtonText(QWizard.NextButton, "بعدی ←")
        self.setButtonText(QWizard.BackButton, "→ قبلی")
        self.setButtonText(QWizard.FinishButton, "✅ شروع کار با ImanAccount")
        self.setButtonText(QWizard.CancelButton, "❌ انصراف")
        
        # اتصال
        self.currentIdChanged.connect(self._on_page_changed)
    
    def _on_page_changed(self, page_id):
        """هنگام تغییر صفحه"""
        # وقتی به صفحه آخر رسید، دکمه Finish رو فعال کن
        if page_id == 3:
            self.button(QWizard.FinishButton).setDefault(True)
    
    def get_username(self) -> str:
        """دریافت نام کاربری"""
        return self.admin_page.username.text().strip()
    
    def accept(self):
        """ذخیره همه چیز در دیتابیس"""
        
        try:
            # ===== ۱. جمع‌آوری داده‌ها =====
            company_data = self.welcome_page.get_data()
            admin_data = self.admin_page.get_data()
            regional_data = self.regional_page.get_data()
            
            logger.info("🚀 شروع ذخیره تنظیمات wizard...")
            
            # ===== ۲. ذخیره در دیتابیس =====
            with get_db() as conn:
                c = conn.cursor()
                
                # ✅ اطلاعات شرکت
                settings_company = [
                    ('company_name', company_data['company_name']),
                    ('company_legal_name', company_data['company_legal_name']),
                    ('company_phone', company_data['company_phone']),
                    ('company_economic', company_data['company_economic']),
                    ('company_address', company_data['company_address']),
                ]
                for key, value in settings_company:
                    c.execute(
                        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                        (key, value)
                    )
                
                # ✅ تنظیمات منطقه‌ای
                settings_regional = [
                    ('currency', regional_data['currency']),
                    ('date_system', regional_data['date_system']),
                    ('tax_rate', str(regional_data['tax_rate'])),
                    ('fiscal_year', str(regional_data['fiscal_year'])),
                    ('wizard_completed', 'true'),
                ]
                for key, value in settings_regional:
                    c.execute(
                        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                        (key, value)
                    )
                
                # ✅ ساخت کاربر مدیر
                password_hash = PasswordHasher.hash(admin_data['password'])
                
                # حذف کاربر admin قدیمی اگه هست
                c.execute("DELETE FROM users WHERE username = ?", [admin_data['username']])
                
                # درج کاربر جدید
                c.execute('''
                    INSERT INTO users (username, password_hash, full_name, level, is_active)
                    VALUES (?, ?, ?, 'admin', 1)
                ''', (
                    admin_data['username'],
                    password_hash,
                    admin_data['full_name'],
                ))
                
                conn.commit()
            
            logger.info(f"✅ کاربر مدیر ساخته شد: {admin_data['username']}")
            
            # ===== ۳. داده نمونه (اختیاری) =====
            if regional_data['create_sample']:
                try:
                    self._create_sample_data()
                    logger.info("✅ داده نمونه ساخته شد")
                except Exception as e:
                    logger.warning(f"⚠️ خطا در داده نمونه: {e}")
            
            # ===== ۴. اطلاع‌رسانی =====
            result = {
                'company_name': company_data['company_name'],
                'username': admin_data['username'],
                'currency': regional_data['currency'],
            }
            self.setup_completed.emit(result)
            
            logger.info("✅ First-Run Wizard با موفقیت تموم شد")
            
            # بستن wizard
            super().accept()
        
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره: {e}", exc_info=True)
            QMessageBox.critical(
                self, "خطا",
                f"❌ خطا در ذخیره تنظیمات:\n\n{str(e)}"
            )
    
    def _create_sample_data(self):
        """ساخت داده نمونه"""
        from database import get_db
        from shamsi_date import get_today_jalali
        
        today = get_today_jalali()
        
        with get_db() as conn:
            c = conn.cursor()
            
            # ✅ مشتری نمونه
            c.execute('''
                INSERT OR IGNORE INTO parties (code, name, type, phone, balance)
                VALUES ('CUST00001', 'مشتری نمونه', 'customer', '09121234567', 0)
            ''')
            
            # ✅ تأمین‌کننده نمونه
            c.execute('''
                INSERT OR IGNORE INTO parties (code, name, type, balance)
                VALUES ('SUPP00001', 'تأمین‌کننده نمونه', 'supplier', 0)
            ''')
            
            # ✅ کالای نمونه
            c.execute('''
                INSERT OR IGNORE INTO products 
                (code, name, unit, purchase_price, sale_price, stock)
                VALUES ('KALA001', 'کالای نمونه', 'عدد', 100000, 150000, 50)
            ''')
            
            # ✅ انبار نمونه
            c.execute('''
                INSERT OR IGNORE INTO warehouses (code, name, is_default, is_active)
                VALUES ('WH-001', 'انبار اصلی', 1, 1)
            ''')
            
            conn.commit()


# ============================================================
# ========== توابع کمکی ==========
# ============================================================

def is_first_run() -> bool:
    """
    بررسی آیا این اولین اجرای برنامه است
    
    Returns:
        bool: True اگه wizard باید اجرا بشه
    """
    try:
        from database import get_db
        
        with get_db() as conn:
            c = conn.cursor()
            
            # بررسی وجود کاربران
            c.execute("SELECT COUNT(*) FROM users")
            user_count = c.fetchone()[0]
            
            if user_count == 0:
                logger.info("🔍 اولین اجرا: هیچ کاربری وجود ندارد")
                return True
            
            # بررسی wizard_completed
            c.execute(
                "SELECT value FROM settings WHERE key = 'wizard_completed'"
            )
            row = c.fetchone()
            
            if not row or row[0] != 'true':
                logger.info("🔍 اولین اجرا: wizard_completed نیست")
                return True
            
            return False
    
    except Exception as e:
        logger.error(f"❌ خطا در تشخیص first_run: {e}")
        return False


def run_first_run_wizard(parent=None) -> bool:
    """
    اجرای First-Run Wizard
    
    Returns:
        bool: True اگه کاربر wizard رو تکمیل کرد
    """
    try:
        wizard = FirstRunWizard(parent)
        
        result = wizard.exec_()
        
        if result == QWizard.Accepted:
            logger.info("✅ Wizard با موفقیت تکمیل شد")
            return True
        else:
            logger.info("⚠️ کاربر wizard رو لغو کرد")
            return False
    
    except Exception as e:
        logger.error(f"❌ خطا در wizard: {e}", exc_info=True)
        return False


# ============================================================
# ========== تست ==========
# ============================================================

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    
    # تست
    wizard = FirstRunWizard()
    if wizard.exec_() == QWizard.Accepted:
        print("✅ Wizard تکمیل شد")
    else:
        print("⚠️ Wizard لغو شد")
