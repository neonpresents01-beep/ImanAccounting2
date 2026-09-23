# ui/login_dialog.py
# ============================================================
# دیالوگ‌های ورود، قفل و تغییر رمز — نسخه 2.0 (bcrypt)
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui.base_widgets import BaseDialog
from database import get_db
from security import PasswordHasher  # ✅ جدید
import logging

logger = logging.getLogger(__name__)


# ============================================================
# UserManager — نسخه امن
# ============================================================

# ui/login_dialog.py - بخش UserManager

class UserManager:
    """مدیریت کاربران با bcrypt"""
    
    LEVEL_ADMIN = 'admin'
    LEVEL_ACCOUNTANT = 'accountant'
    LEVEL_INVENTORY = 'inventory'
    LEVEL_VIEWER = 'viewer'
    LEVEL_PAYROLL = 'payroll'
    
    LEVEL_NAMES = {
        'admin': 'مدیر سیستم',
        'accountant': 'حسابدار',
        'inventory': 'انباردار',
        'viewer': 'کاربر عادی',
        'payroll': 'کارشناس حقوق'
    }
    
    LEVEL_PERMISSIONS = {
        'admin': ['all'],
        'accountant': ['accounting', 'reports', 'parties', 'documents'],
        'inventory': ['inventory', 'documents'],
        'viewer': ['dashboard', 'reports_view'],
        'payroll': ['payroll', 'employees']
    }
    
    @staticmethod
    def init_default_users():
        """ایجاد کاربران پیش‌فرض"""
        try:
            from security import PasswordHasher
            
            with get_db() as conn:
                c = conn.cursor()
                
                # بررسی جدول
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if not c.fetchone():
                    c.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            full_name TEXT,
                            level TEXT DEFAULT 'viewer',
                            is_active BOOLEAN DEFAULT 1,
                            must_change_password INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_login TIMESTAMP
                        )
                    ''')
                
                # بررسی ستون‌ها
                c.execute("PRAGMA table_info(users)")
                columns = [col[1] for col in c.fetchall()]
                if 'must_change_password' not in columns:
                    c.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
                    logger.info("✅ ستون must_change_password اضافه شد")
                
                # ✅ کاربران پیش‌فرض
                default_users = [
                    ('admin', 'admin123', 'مدیر سیستم', 'admin'),
                    ('accountant', 'acc123', 'حسابدار', 'accountant'),
                    ('inventory', 'inv123', 'انباردار', 'inventory'),
                    ('viewer', 'view123', 'کاربر عادی', 'viewer'),
                    ('payroll', 'pay123', 'کارشناس حقوق', 'payroll'),
                ]
                
                created = 0
                for username, password, full_name, level in default_users:
                    # بررسی وجود
                    c.execute("SELECT id, password_hash FROM users WHERE username = ?", [username])
                    existing = c.fetchone()
                    
                    if existing:
                        # اگه hash قدیمیه → بازسازی
                        old_hash = existing['password_hash']
                        if not old_hash.startswith("$2"):
                            # بازسازی با bcrypt
                            new_hash = PasswordHasher.hash(password)
                            c.execute(
                                "UPDATE users SET password_hash = ? WHERE id = ?",
                                [new_hash, existing['id']]
                            )
                            logger.info(f"🔄 رمز {username} به bcrypt بازسازی شد")
                        continue
                    
                    # ✅ Hash با bcrypt
                    password_hash = PasswordHasher.hash(password)
                    
                    c.execute('''
                        INSERT INTO users (username, password_hash, full_name, level)
                        VALUES (?, ?, ?, ?)
                    ''', (username, password_hash, full_name, level))
                    created += 1
                
                conn.commit()
                logger.info(f"✅ {created} کاربر پیش‌فرض ایجاد شد")
                
                print(f"✅ کاربران پیش‌فرض (bcrypt):")
                print("   admin/admin123")
                print("   accountant/acc123")
                print("   inventory/inv123")
                print("   viewer/view123")
                print("   payroll/pay123")
        
        except Exception as e:
            logger.error(f"❌ خطا در ایجاد کاربران: {e}", exc_info=True)
    
    @staticmethod
    def get_user(username, password):
        """دریافت کاربر با bcrypt"""
        if not username or not password:
            return None
        
        try:
            from security import PasswordHasher
            
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute('''
                    SELECT id, username, password_hash, full_name, level,
                           is_active, must_change_password
                    FROM users
                    WHERE username = ? AND is_active = 1
                ''', (username,))
                
                user = c.fetchone()
                if not user:
                    return None
                
                stored_hash = user['password_hash']
                
                # ✅ Verify
                is_valid, needs_rehash = PasswordHasher.verify(password, stored_hash)
                
                if not is_valid:
                    return None
                
                # ✅ Rehash خودکار
                if needs_rehash:
                    try:
                        new_hash = PasswordHasher.hash(password)
                        c.execute(
                            "UPDATE users SET password_hash = ? WHERE id = ?",
                            [new_hash, user['id']]
                        )
                        conn.commit()
                        logger.info(f"✅ رمز {username} به bcrypt مهاجرت کرد")
                    except Exception as e:
                        logger.warning(f"⚠️ خطا در rehash: {e}")
                
                # ✅ بررسی اجبار تغییر رمز
                must_change = bool(user['must_change_password'])
                if stored_hash.startswith("SHA256_MIGRATED:"):
                    must_change = True
                
                # ✅ بروزرسانی last_login
                c.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    [user['id']]
                )
                conn.commit()
                
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'level': user['level'],
                    'is_active': True,
                    'must_change_password': must_change,
                }
        
        except Exception as e:
            logger.error(f"❌ خطا در get_user: {e}")
            return None
    
    @staticmethod
    def get_all_users():
        """دریافت همه کاربران"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT id, username, full_name, level, is_active,
                           must_change_password, last_login
                    FROM users
                    ORDER BY id
                ''')
                return c.fetchall()
        except Exception as e:
            logger.error(f"❌ خطا: {e}")
            return []
    
    @staticmethod
    def add_user(username, password, full_name, level):
        """افزودن کاربر جدید"""
        try:
            from security import PasswordHasher
            
            is_valid, msg = PasswordHasher.validate_password_strength(password)
            if not is_valid:
                logger.warning(f"⚠️ رمز ضعیف: {msg}")
                return False
            
            password_hash = PasswordHasher.hash(password)
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO users (username, password_hash, full_name, level)
                    VALUES (?, ?, ?, ?)
                ''', (username, password_hash, full_name, level))
                conn.commit()
                
                logger.info(f"✅ کاربر {username} اضافه شد")
                return True
        
        except Exception as e:
            logger.error(f"❌ خطا در add_user: {e}")
            return False
    
    @staticmethod
    def delete_user(user_id):
        """حذف کاربر"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('DELETE FROM users WHERE id = ?', [user_id])
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ خطا: {e}")
            return False
    
    @staticmethod
    def change_password(user_id, new_password, old_password=None, is_admin=False):
        """تغییر رمز عبور"""
        try:
            from security import PasswordHasher
            
            is_valid, msg = PasswordHasher.validate_password_strength(new_password)
            if not is_valid:
                return False, msg
            
            with get_db() as conn:
                c = conn.cursor()
                
                if not is_admin and old_password is not None:
                    c.execute("SELECT password_hash FROM users WHERE id = ?", [user_id])
                    row = c.fetchone()
                    if not row:
                        return False, "کاربر یافت نشد"
                    
                    is_valid, _ = PasswordHasher.verify(old_password, row['password_hash'])
                    if not is_valid:
                        return False, "رمز فعلی اشتباه است"
                
                new_hash = PasswordHasher.hash(new_password)
                
                c.execute('''
                    UPDATE users
                    SET password_hash = ?, must_change_password = 0
                    WHERE id = ?
                ''', (new_hash, user_id))
                conn.commit()
                
                logger.info(f"✅ رمز کاربر #{user_id} تغییر کرد")
                return True, "رمز عبور با موفقیت تغییر کرد"
        
        except Exception as e:
            logger.error(f"❌ خطا: {e}")
            return False, str(e)
    
    @staticmethod
    def has_permission(user_level, module):
        """بررسی دسترسی"""
        if user_level == 'admin':
            return True
        permissions = UserManager.LEVEL_PERMISSIONS.get(user_level, [])
        return module in permissions or 'all' in permissions

# ============================================================
# بقیه کلاس‌ها (بدون تغییر زیاد)
# ============================================================

class UserManagementDialog(BaseDialog):
    """دیالوگ مدیریت کاربران"""
    
    def __init__(self, parent=None):
        super().__init__(parent, base_width=650, base_height=500)
        self.setWindowTitle("👥 مدیریت کاربران")
        self.setModal(True)
        self.setup_ui()
        self.load_users()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(self.margin(15), self.margin(15),
                                  self.margin(15), self.margin(15))
        
        title = QLabel("👥 مدیریت کاربران و سطوح دسترسی")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # نوار ابزار
        toolbar = QHBoxLayout()
        
        add_btn = self.create_button("➕ کاربر جدید", "successBtn")
        add_btn.clicked.connect(self.add_user)
        toolbar.addWidget(add_btn)
        
        edit_btn = self.create_button("✏️ ویرایش", "warningBtn")
        edit_btn.clicked.connect(self.edit_user)
        toolbar.addWidget(edit_btn)
        
        delete_btn = self.create_button("🗑️ حذف", "dangerBtn")
        delete_btn.clicked.connect(self.delete_user)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # جدول
        self.table = self.create_table(
            ["شناسه", "نام کاربری", "نام کامل", "سطح دسترسی", "وضعیت", "آخرین ورود"],
            stretch_last=True
        )
        layout.addWidget(self.table)
        
        # دکمه بستن
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = self.create_button("❌ بستن", "dangerBtn")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def load_users(self):
        users = UserManager.get_all_users()
        self.table.setRowCount(len(users))
        
        level_names = {
            'admin': '🔴 مدیر سیستم',
            'accountant': '🟢 حسابدار',
            'inventory': '🟡 انباردار',
            'viewer': '⚪ کاربر عادی',
            'payroll': '🟣 کارشناس حقوق'
        }
        
        for i, user in enumerate(users):
            self.table.setItem(i, 0, QTableWidgetItem(str(user['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(user['username']))
            self.table.setItem(i, 2, QTableWidgetItem(user['full_name'] or '-'))
            self.table.setItem(i, 3, QTableWidgetItem(
                level_names.get(user['level'], user['level'])
            ))
            
            # ✅ نمایش must_change_password
            if user['must_change_password']:
                status_text = "⚠️ نیاز به تغییر رمز"
                status_color = '#f39c12'
            elif user['is_active']:
                status_text = "✅ فعال"
                status_color = '#4CAF50'
            else:
                status_text = "❌ غیرفعال"
                status_color = '#e74c3c'
            
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            self.table.setItem(i, 4, status_item)
            
            last_login = user['last_login'][:16] if user['last_login'] else 'هرگز'
            self.table.setItem(i, 5, QTableWidgetItem(last_login))
    
    def add_user(self):
        dialog = UserDialog(user_id=None, parent=self)
        if dialog.exec_():
            self.load_users()
            QMessageBox.information(self, "موفق", "✅ کاربر جدید اضافه شد!")
    
    def edit_user(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک کاربر را انتخاب کنید!")
            return
        
        user_id = int(self.table.item(row, 0).text())
        dialog = UserDialog(user_id=user_id, parent=self)
        if dialog.exec_():
            self.load_users()
            QMessageBox.information(self, "موفق", "✅ کاربر ویرایش شد!")
    
    def delete_user(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک کاربر را انتخاب کنید!")
            return
        
        user_id = int(self.table.item(row, 0).text())
        username = self.table.item(row, 1).text()
        
        # جلوگیری از حذف خود
        try:
            parent = self.parent()
            if parent and hasattr(parent, 'current_user') and parent.current_user:
                if username == parent.current_user.get('username'):
                    QMessageBox.warning(self, "خطا", "❌ نمی‌توانید کاربر فعلی را حذف کنید!")
                    return
        except Exception:
            pass
        
        reply = QMessageBox.question(self, "تأیید حذف",
            f"آیا از حذف کاربر '{username}' اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            UserManager.delete_user(user_id)
            self.load_users()
            QMessageBox.information(self, "موفق", "✅ کاربر حذف شد!")


class UserDialog(BaseDialog):
    """دیالوگ افزودن/ویرایش کاربر"""
    
    def __init__(self, user_id=None, parent=None):
        if isinstance(user_id, QWidget):
            parent = user_id
            user_id = None
        
        if user_id is not None:
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                user_id = None
        
        super().__init__(parent, base_width=500, base_height=480)
        self.user_id = user_id
        self.setWindowTitle("✏️ ویرایش کاربر" if user_id else "➕ کاربر جدید")
        self.setModal(True)
        self.setup_ui()
        
        if self.user_id is not None:
            self.load_user_data()
        
        self.apply_theme()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setLabelAlignment(Qt.AlignRight)
        
        # نام کاربری
        self.username_edit = self.create_input("نام کاربری")
        self.username_edit.setPlaceholderText("حداقل ۳ کاراکتر")
        if self.user_id:
            self.username_edit.setReadOnly(True)
        layout.addRow("👤 نام کاربری *:", self.username_edit)
        
        # رمز عبور
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("حداقل ۶ کاراکتر")
        if self.user_id:
            self.password_edit.setPlaceholderText("برای تغییر رمز، مقدار جدید وارد کنید")
        self.password_edit.textChanged.connect(self._update_strength)
        layout.addRow("🔑 رمز عبور:", self.password_edit)
        
        # ✅ نمایش قدرت رمز
        self.strength_label = QLabel("")
        self.strength_label.setStyleSheet("font-size: 9pt; color: #888;")
        layout.addRow("", self.strength_label)
        
        # تکرار رمز
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        self.confirm_edit.setPlaceholderText("تکرار رمز")
        layout.addRow("✅ تکرار رمز:", self.confirm_edit)
        
        # نام کامل
        self.full_name_edit = self.create_input("نام کامل")
        layout.addRow("👤 نام کامل:", self.full_name_edit)
        
        # سطح دسترسی
        self.level_combo = QComboBox()
        self.level_combo.addItems([
            "🔴 مدیر سیستم (admin)",
            "🟢 حسابدار (accountant)",
            "🟡 انباردار (inventory)",
            "🟣 کارشناس حقوق (payroll)",
            "⚪ کاربر عادی (viewer)",
        ])
        layout.addRow("🎯 سطح دسترسی:", self.level_combo)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = self.create_button("💾 ذخیره", "successBtn")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = self.create_button("❌ انصراف", "dangerBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
    
    def _update_strength(self):
        """نمایش قدرت رمز"""
        password = self.password_edit.text()
        
        if not password:
            self.strength_label.setText("")
            return
        
        score = PasswordHasher.get_password_strength_score(password)
        
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
        
        self.strength_label.setText(f"قدرت رمز: {text} ({score}%)")
        self.strength_label.setStyleSheet(f"font-size: 9pt; color: {color}; font-weight: bold;")
    
    def load_user_data(self):
        if self.user_id is None:
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    'SELECT username, full_name, level FROM users WHERE id = ?',
                    [self.user_id]
                )
                user = c.fetchone()
                
                if user:
                    self.username_edit.setText(user['username'])
                    self.full_name_edit.setText(user['full_name'] or '')
                    
                    level_map = {
                        'admin': "🔴 مدیر سیستم (admin)",
                        'accountant': "🟢 حسابدار (accountant)",
                        'inventory': "🟡 انباردار (inventory)",
                        'payroll': "🟣 کارشناس حقوق (payroll)",
                        'viewer': "⚪ کاربر عادی (viewer)",
                    }
                    index = self.level_combo.findText(
                        level_map.get(user['level'], user['level'])
                    )
                    if index >= 0:
                        self.level_combo.setCurrentIndex(index)
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری: {e}")
    
    def get_level_value(self):
        text = self.level_combo.currentText()
        for level in ['admin', 'accountant', 'inventory', 'payroll', 'viewer']:
            if level in text:
                return level
        return 'viewer'
    
    def accept(self):
        username = self.username_edit.text().strip()
        
        if not username or len(username) < 3:
            QMessageBox.warning(self, "خطا", "نام کاربری باید حداقل ۳ کاراکتر باشد!")
            return
        
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()
        
        # برای کاربر جدید، رمز الزامی
        if not self.user_id and not password:
            QMessageBox.warning(self, "خطا", "رمز عبور الزامی است!")
            return
        
        # اگه رمز وارد شده، تطابق رو چک کن
        if password and password != confirm:
            QMessageBox.warning(self, "خطا", "رمز عبور با تکرار آن مطابقت ندارد!")
            return
        
        # ✅ اعتبارسنجی قدرت رمز
        if password:
            is_valid, msg = PasswordHasher.validate_password_strength(password)
            if not is_valid:
                QMessageBox.warning(self, "خطا", msg)
                return
        
        if self.user_id:
            # ویرایش
            if password:
                success, msg = UserManager.change_password(
                    self.user_id, password, is_admin=True
                )
                if not success:
                    QMessageBox.warning(self, "خطا", msg)
                    return
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    UPDATE users 
                    SET full_name = ?, level = ?
                    WHERE id = ?
                ''', (self.full_name_edit.text().strip(),
                      self.get_level_value(),
                      self.user_id))
                conn.commit()
        else:
            # افزودن
            success = UserManager.add_user(
                username, password,
                self.full_name_edit.text().strip(),
                self.get_level_value()
            )
            if not success:
                QMessageBox.warning(self, "خطا", "این نام کاربری قبلاً ثبت شده است!")
                return
        
        super().accept()


# ============================================================
# LoginDialog (بدون تغییر زیاد)
# ============================================================

class LoginDialog(BaseDialog):
    """دیالوگ ورود با bcrypt"""
    
    def __init__(self, parent=None):
        super().__init__(parent, base_width=450, base_height=520)
        self.setWindowTitle("ورود به ImanAccount")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.current_user = None
        self.setup_ui()
        self.load_settings()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # عنوان
        title = QLabel("🤖 ImanAccount")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26pt; font-weight: bold; color: #e94560;")
        layout.addWidget(title)
        
        subtitle = QLabel("حسابداری هوشمند با هوش مصنوعی")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 11pt; color: #888; margin-bottom: 15px;")
        layout.addWidget(subtitle)
        
        # فیلدها
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("نام کاربری")
        self.username_input.setMinimumHeight(45)
        layout.addWidget(self.username_input)
        
        layout.addSpacing(15)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("رمز عبور")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(45)
        self.password_input.returnPressed.connect(self.check_login)
        layout.addWidget(self.password_input)
        
        layout.addSpacing(10)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.addStretch()
        
        login_btn = QPushButton("✅ ورود")
        login_btn.setMinimumHeight(48)
        login_btn.setMinimumWidth(120)
        login_btn.clicked.connect(self.check_login)
        btn_layout.addWidget(login_btn)
        
        cancel_btn = QPushButton("❌ خروج")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.setMinimumHeight(48)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addSpacing(15)
        
        # خطا
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #e74c3c; font-size: 11pt; min-height: 35px;")
        layout.addWidget(self.error_label)
        
        layout.addStretch()
    
    def load_settings(self):
        UserManager.init_default_users()
    
    def check_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.error_label.setText("❌ نام کاربری و رمز عبور را وارد کنید!")
            return
        
        user = UserManager.get_user(username, password)
        
        if user:
            self.current_user = user
            self.error_label.setText("")
            
            # ✅ بررسی اجبار تغییر رمز
            if user.get('must_change_password'):
                QMessageBox.warning(
                    self, "تغییر رمز الزامی",
                    "🔐 به دلایل امنیتی، لطفاً رمز عبور خود را تغییر دهید."
                )
                
                # باز کردن دیالوگ تغییر رمز
                dialog = ChangePasswordDialog(
                    username=user['username'],
                    user_id=user['id'],
                    force_change=True,
                    parent=self
                )
                if not dialog.exec_():
                    self.error_label.setText("❌ برای ادامه باید رمز را تغییر دهید!")
                    return
            
            level_names = {
                'admin': 'مدیر سیستم',
                'accountant': 'حسابدار',
                'inventory': 'انباردار',
                'viewer': 'کاربر عادی',
                'payroll': 'کارشناس حقوق'
            }
            level_name = level_names.get(user['level'], user['level'])
            
            QMessageBox.information(self, "خوش آمدید",
                f"👋 خوش آمدید {user['full_name'] or user['username']}!\n"
                f"🎯 سطح دسترسی: {level_name}")
            
            self.accept()
        else:
            self.error_label.setText("❌ نام کاربری یا رمز عبور اشتباه است!")
            self.password_input.clear()
            self.password_input.setFocus()
    
    def get_current_user(self):
        return self.current_user


# ============================================================
# ChangePasswordDialog (بهبود یافته)
# ============================================================

class ChangePasswordDialog(BaseDialog):
    """دیالوگ تغییر رمز با bcrypt"""
    
    def __init__(self, username="", user_id=None, force_change=False, parent=None):
        super().__init__(parent, base_width=480, base_height=520)
        self.username = username
        self.user_id = user_id
        self.force_change = force_change
        
        if force_change:
            self.setWindowTitle("🔐 تغییر رمز الزامی")
        else:
            self.setWindowTitle("🔑 تغییر رمز عبور")
        
        self.setModal(True)
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(35, 35, 35, 35)
        
        title = QLabel("🔑 تغییر رمز عبور")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22pt; font-weight: bold; color: #e94560;")
        layout.addWidget(title)
        
        if self.force_change:
            warning = QLabel(
                "⚠️ به دلایل امنیتی (مهاجرت به bcrypt)،\n"
                "لطفاً رمز عبور جدیدی تعیین کنید."
            )
            warning.setAlignment(Qt.AlignCenter)
            warning.setStyleSheet("""
                color: #f39c12; font-size: 10pt;
                background: #fff3cd; padding: 10px;
                border-radius: 6px; border: 1px solid #f39c12;
            """)
            warning.setWordWrap(True)
            layout.addWidget(warning)
        
        user_label = QLabel(f"👤 {self.username or 'کاربر'}")
        user_label.setAlignment(Qt.AlignCenter)
        user_label.setStyleSheet("font-size: 12pt; color: #888;")
        layout.addWidget(user_label)
        
        # رمز فعلی
        old_label = QLabel("🔒 رمز فعلی")
        old_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(old_label)
        
        self.old_password = QLineEdit()
        self.old_password.setEchoMode(QLineEdit.Password)
        self.old_password.setPlaceholderText("رمز عبور فعلی")
        self.old_password.setMinimumHeight(45)
        layout.addWidget(self.old_password)
        
        layout.addSpacing(10)
        
        # رمز جدید
        new_label = QLabel("🔑 رمز جدید")
        new_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(new_label)
        
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setPlaceholderText("حداقل ۶ کاراکتر")
        self.new_password.setMinimumHeight(45)
        self.new_password.textChanged.connect(self._update_strength)
        layout.addWidget(self.new_password)
        
        # ✅ نمایش قدرت
        self.strength_label = QLabel("")
        self.strength_label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self.strength_label)
        
        layout.addSpacing(5)
        
        # تکرار
        confirm_label = QLabel("✅ تکرار رمز جدید")
        confirm_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(confirm_label)
        
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.confirm_password.setPlaceholderText("تکرار رمز جدید")
        self.confirm_password.setMinimumHeight(45)
        layout.addWidget(self.confirm_password)
        
        layout.addSpacing(15)
        
        # خطا
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #e74c3c; font-size: 10pt; min-height: 30px;")
        layout.addWidget(self.error_label)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setObjectName("successBtn")
        save_btn.setMinimumHeight(45)
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self.save_password)
        btn_layout.addWidget(save_btn)
        
        if not self.force_change:
            cancel_btn = QPushButton("❌ انصراف")
            cancel_btn.setObjectName("dangerBtn")
            cancel_btn.setMinimumHeight(45)
            cancel_btn.setMinimumWidth(120)
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # ✅ در حالت force، بدون گزینه انصراف
        if self.force_change:
            self.setWindowFlags(
                Qt.Dialog | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint
            )
    
    def _update_strength(self):
        password = self.new_password.text()
        
        if not password:
            self.strength_label.setText("")
            return
        
        score = PasswordHasher.get_password_strength_score(password)
        
        if score < 30:
            color, text = "#e74c3c", "ضعیف"
        elif score < 60:
            color, text = "#f39c12", "متوسط"
        elif score < 85:
            color, text = "#3498db", "خوب"
        else:
            color, text = "#27ae60", "قوی"
        
        self.strength_label.setText(f"قدرت رمز: {text} ({score}%)")
        self.strength_label.setStyleSheet(
            f"font-size: 9pt; color: {color}; font-weight: bold;"
        )
    
    def save_password(self):
        old_pass = self.old_password.text().strip()
        new_pass = self.new_password.text().strip()
        confirm_pass = self.confirm_password.text().strip()
        
        if not old_pass:
            self.error_label.setText("❌ رمز فعلی را وارد کنید!")
            return
        
        if not new_pass:
            self.error_label.setText("❌ رمز جدید را وارد کنید!")
            return
        
        if new_pass != confirm_pass:
            self.error_label.setText("❌ رمز جدید با تکرار آن مطابقت ندارد!")
            return
        
        # ✅ اعتبارسنجی قدرت
        is_valid, msg = PasswordHasher.validate_password_strength(new_pass)
        if not is_valid:
            self.error_label.setText(f"❌ {msg}")
            return
        
        # ✅ بررسی رمز فعلی
        if self.user_id:
            # اگه user_id داریم، ازش استفاده کن
            success, msg = UserManager.change_password(
                self.user_id, new_pass,
                old_password=old_pass,
                is_admin=False
            )
            
            if not success:
                self.error_label.setText(f"❌ {msg}")
                return
        else:
            # از username استفاده کن
            user = UserManager.get_user(self.username, old_pass)
            if not user:
                self.error_label.setText("❌ رمز فعلی اشتباه است!")
                return
            
            success, msg = UserManager.change_password(
                user['id'], new_pass, is_admin=True
            )
            
            if not success:
                self.error_label.setText(f"❌ {msg}")
                return
        
        QMessageBox.information(self, "موفق", "✅ رمز عبور با موفقیت تغییر کرد!")
        self.accept()


# ============================================================
# LockScreenDialog (بدون تغییر)
# ============================================================

class LockScreenDialog(BaseDialog):
    """صفحه قفل"""
    
    def __init__(self, username="", parent=None):
        super().__init__(parent, base_width=400, base_height=380)
        self.username = username
        self.setWindowTitle("قفل ImanAccount")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(35, 35, 35, 35)
        
        lock_label = QLabel("🔒")
        lock_label.setAlignment(Qt.AlignCenter)
        lock_label.setStyleSheet("font-size: 55pt; margin-bottom: 10px;")
        layout.addWidget(lock_label)
        
        title = QLabel("نرم‌افزار قفل شد")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #e94560;")
        layout.addWidget(title)
        
        user_label = QLabel(f"👤 {self.username or 'کاربر'}")
        user_label.setAlignment(Qt.AlignCenter)
        user_label.setStyleSheet("font-size: 12pt; color: #888;")
        layout.addWidget(user_label)
        
        subtitle = QLabel("لطفاً رمز عبور خود را وارد کنید")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 11pt; color: #888;")
        layout.addWidget(subtitle)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("رمز عبور")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setAlignment(Qt.AlignCenter)
        self.password_input.setMinimumHeight(50)
        self.password_input.returnPressed.connect(self.check_password)
        layout.addWidget(self.password_input)
        
        layout.addSpacing(20)
        
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #e74c3c; font-size: 11pt;")
        layout.addWidget(self.error_label)
        
        layout.addStretch()
    
    def check_password(self):
        password = self.password_input.text().strip()
        if not password:
            self.error_label.setText("❌ رمز عبور را وارد کنید!")
            return
        
        # ✅ استفاده از UserManager.get_user
        if self.username:
            user = UserManager.get_user(self.username, password)
            if user:
                self.accept()
                return
        
        self.error_label.setText("❌ رمز عبور اشتباه است!")
        self.password_input.clear()
        self.password_input.setFocus()
