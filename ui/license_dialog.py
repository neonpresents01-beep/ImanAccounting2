# ui/license_dialog.py
# ============================================================
# دیالوگ انتخاب لایسنس - با ScreenManager و BaseDialog
# ============================================================

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QFrame, QMessageBox, QApplication, QPushButton
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from ui.base_widgets import BaseDialog
from screen_utils import ScreenManager


class LicenseDialog(BaseDialog):
    """دیالوگ انتخاب لایسنس با پشتیبانی از تم و اسکرین"""
    
    def __init__(self, parent=None, trial_available=True):
        super().__init__(
            parent=parent,
            base_width=580,
            base_height=520,
            scale_factor=1.0,
            center=True,
            max_size=(700, 650)
        )
        
        self.trial_available = trial_available
        self.selected_option = None
        self.license_key = None
        
        # ScreenManager برای اسکیل‌دهی
        self.screen_manager = ScreenManager()
        
        self.setWindowTitle("🔐 فعال‌سازی لایسنس ImanAccount")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        # ========== راه‌اندازی UI ==========
        self.setup_ui()
        
        # اعمال تم و مرکز کردن
        self.apply_theme()
        self.center()
    
    def setup_ui(self):
        """راه‌اندازی رابط کاربری با اسکیل‌دهی"""
        # ایجاد Layout اصلی
        layout = QVBoxLayout(self)
        layout.setSpacing(self.screen_manager.get_spacing(20))
        layout.setContentsMargins(
            self.screen_manager.get_margin(40),
            self.screen_manager.get_margin(40),
            self.screen_manager.get_margin(40),
            self.screen_manager.get_margin(40)
        )
        
        # ========== هدر ==========
        header_layout = QHBoxLayout()
        
        icon_label = QLabel("🔐")
        icon_label.setStyleSheet(f"font-size: {self.screen_manager.get_font_size(28)}px; background: transparent;")
        header_layout.addWidget(icon_label)
        
        title = QLabel("فعال‌سازی ImanAccount")
        title.setObjectName("titleLabel")
        title.setStyleSheet(f"""
            font-size: {self.screen_manager.get_font_size(20)}pt;
            font-weight: bold;
            color: #e94560;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # ========== توضیحات ==========
        desc = QLabel(
            "برای استفاده از نرم‌افزار، یکی از گزینه‌های زیر را انتخاب کنید:"
        )
        desc.setStyleSheet(f"color: #aaa; font-size: {self.screen_manager.get_font_size(11)}pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # ========== گزینه ۱: لایسنس رسمی ==========
        official_frame = self._create_card_frame()
        official_layout = QVBoxLayout(official_frame)
        official_layout.setSpacing(self.screen_manager.get_spacing(12))
        
        official_title = QLabel("📋 لایسنس رسمی")
        official_title.setStyleSheet(f"font-size: {self.screen_manager.get_font_size(14)}pt; font-weight: bold; color: #4CAF50;")
        official_layout.addWidget(official_title)
        
        official_desc = QLabel(
            "اگر لایسنس رسمی دریافت کرده‌اید، کد آن را وارد کنید."
        )
        official_desc.setStyleSheet(f"color: #aaa; font-size: {self.screen_manager.get_font_size(10)}pt;")
        official_layout.addWidget(official_desc)
        
        # فیلد وارد کردن لایسنس
        key_layout = QHBoxLayout()
        key_layout.setSpacing(self.screen_manager.get_spacing(10))
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("کد لایسنس را وارد کنید...")
        self.license_input.setMinimumHeight(self.screen_manager.get_scaled(45))
        self.license_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #16213e;
                color: #eee;
                border: 2px solid #0f3460;
                border-radius: {self.screen_manager.get_scaled(8)}px;
                padding: {self.screen_manager.get_scaled(10)}px {self.screen_manager.get_scaled(15)}px;
                font-size: {self.screen_manager.get_font_size(11)}pt;
                font-family: monospace;
            }}
            QLineEdit:focus {{
                border-color: #e94560;
            }}
        """)
        self.license_input.returnPressed.connect(self.verify_official_license)
        key_layout.addWidget(self.license_input, 2)
        
        verify_btn = QPushButton("✅ تأیید")
        verify_btn.setObjectName("successBtn")
        verify_btn.setFixedHeight(self.screen_manager.get_scaled(45))
        verify_btn.setFixedWidth(self.screen_manager.get_scaled(90))
        verify_btn.clicked.connect(self.verify_official_license)
        key_layout.addWidget(verify_btn)
        
        official_layout.addLayout(key_layout)
        
        self.official_status = QLabel("")
        self.official_status.setStyleSheet(f"color: #FF9800; font-size: {self.screen_manager.get_font_size(9)}pt; padding: {self.screen_manager.get_scaled(5)}px;")
        self.official_status.setAlignment(Qt.AlignCenter)
        official_layout.addWidget(self.official_status)
        
        layout.addWidget(official_frame)
        
        # ========== جداکننده ==========
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #2c3e50; max-height: 2px; margin: 5px 0;")
        layout.addWidget(separator)
        
        # ========== گزینه ۲: نسخه آزمایشی ==========
        trial_frame = self._create_card_frame()
        trial_layout = QVBoxLayout(trial_frame)
        trial_layout.setSpacing(self.screen_manager.get_spacing(12))
        
        trial_title = QLabel("🧪 نسخه آزمایشی ۳۰ روزه")
        trial_title.setStyleSheet(f"font-size: {self.screen_manager.get_font_size(14)}pt; font-weight: bold; color: #FF9800;")
        trial_layout.addWidget(trial_title)
        
        trial_desc = QLabel(
            "می‌توانید به مدت ۳۰ روز از نرم‌افزار استفاده کنید.\n"
            "⚠️ این گزینه فقط یک بار قابل استفاده است!"
        )
        trial_desc.setStyleSheet(f"color: #aaa; font-size: {self.screen_manager.get_font_size(10)}pt;")
        trial_layout.addWidget(trial_desc)
        
        trial_btn = QPushButton("🚀 شروع نسخه آزمایشی")
        trial_btn.setObjectName("trialBtn")
        trial_btn.setMinimumHeight(self.screen_manager.get_scaled(48))
        trial_btn.setEnabled(self.trial_available)
        trial_btn.setStyleSheet(f"""
            QPushButton#trialBtn {{
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: {self.screen_manager.get_scaled(8)}px;
                font-weight: bold;
                font-size: {self.screen_manager.get_font_size(12)}pt;
            }}
            QPushButton#trialBtn:hover {{
                background-color: #E68900;
            }}
            QPushButton#trialBtn:disabled {{
                background-color: #555;
                color: #888;
            }}
        """)
        trial_btn.clicked.connect(self.start_trial)
        trial_layout.addWidget(trial_btn)
        
        if not self.trial_available:
            trial_status = QLabel("❌ نسخه آزمایشی قبلاً استفاده شده است!")
            trial_status.setStyleSheet(f"color: #e74c3c; font-size: {self.screen_manager.get_font_size(10)}pt; font-weight: bold;")
            trial_status.setAlignment(Qt.AlignCenter)
            trial_layout.addWidget(trial_status)
        
        layout.addWidget(trial_frame)
        
        # ========== دکمه خروج ==========
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("❌ خروج")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.setFixedWidth(self.screen_manager.get_scaled(120))
        cancel_btn.setMinimumHeight(self.screen_manager.get_scaled(42))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # ========== فوتر ==========
        footer = QLabel("نسخه ۱.۰.۰ | ImanAccount")
        footer.setStyleSheet(f"color: #666; font-size: {self.screen_manager.get_font_size(9)}pt; text-align: center;")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)
    
    def _create_card_frame(self):
        """ایجاد یک کارت با استایل یکنواخت"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a2e;
                border: 1px solid #0f3460;
                border-radius: {self.screen_manager.get_scaled(12)}px;
                padding: {self.screen_manager.get_scaled(15)}px;
            }}
        """)
        return frame
    
    # ============================================================
    # توابع اصلی
    # ============================================================
    
    def verify_official_license(self):
        """بررسی لایسنس رسمی وارد شده"""
        key = self.license_input.text().strip()
        if not key:
            self.official_status.setText("❌ لطفاً کد لایسنس را وارد کنید!")
            self.official_status.setStyleSheet(f"color: #e74c3c; font-size: {self.screen_manager.get_font_size(9)}pt; padding: {self.screen_manager.get_scaled(5)}px;")
            return
        
        from license_core import get_license_core
        license_core = get_license_core()
        result = license_core.verify_license(key)
        
        if result.get('valid'):
            self.official_status.setText("✅ لایسنس معتبر است!")
            self.official_status.setStyleSheet(f"color: #4CAF50; font-size: {self.screen_manager.get_font_size(9)}pt; padding: {self.screen_manager.get_scaled(5)}px;")
            
            with open("license.key", 'w', encoding='utf-8') as f:
                f.write(key)
            
            self.license_key = key
            self.selected_option = 'official'
            
            QTimer.singleShot(500, self.accept)
        else:
            error_msg = result.get('message', 'لایسنس نامعتبر است!')
            self.official_status.setText(f"❌ {error_msg}")
            self.official_status.setStyleSheet(f"color: #e74c3c; font-size: {self.screen_manager.get_font_size(9)}pt; padding: {self.screen_manager.get_scaled(5)}px;")
            
            # اگر خطای تطابق شناسه بود
            if result.get('error') == 'machine_mismatch':
                reply = QMessageBox.question(self, "عدم تطابق سیستم",
                    f"{error_msg}\n\n"
                    "آیا می‌خواهید شناسه سیستم خود را ببینید؟",
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self._show_machine_id_dialog()
    
    def start_trial(self):
        """شروع نسخه آزمایشی"""
        from license_core import get_license_core
        license_core = get_license_core()
        
        result = license_core.create_trial_license()
        
        if result.get('valid'):
            self.selected_option = 'trial'
            self.license_key = None
            QMessageBox.information(self, "موفق", 
                "✅ نسخه آزمایشی ۳۰ روزه با موفقیت فعال شد!\n\n"
                f"تاریخ انقضا: {result.get('data', {}).get('expire_date', 'نامحدود')[:10]}\n"
                "از نرم‌افزار لذت ببرید! 🚀")
            self.accept()
        else:
            QMessageBox.warning(self, "خطا", 
                result.get('message', 'خطا در فعال‌سازی آزمایشی!'))
    
    def _show_machine_id_dialog(self):
        """نمایش شناسه سیستم"""
        from license_core import get_system_hwid
        machine_id = get_system_hwid()
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🖥️ شناسه سیستم")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(
            f"شناسه سیستم خود را برای دریافت لایسنس ارسال کنید:\n\n"
            f"<b style='font-family: monospace; font-size: 12pt;'>{machine_id}</b>\n\n"
            "👆 این کد را کپی کرده و برای پشتیبانی ارسال کنید."
        )
        copy_btn = msg_box.addButton("📋 کپی", QMessageBox.ActionRole)
        cancel_btn = msg_box.addButton("❌ بستن", QMessageBox.RejectRole)
        msg_box.setDefaultButton(cancel_btn)
        
        if msg_box.exec_() == copy_btn:
            clipboard = QApplication.clipboard()
            clipboard.setText(machine_id)
            QMessageBox.information(self, "کپی شد", "✅ شناسه سیستم در کلیپ‌بورد کپی شد!")
