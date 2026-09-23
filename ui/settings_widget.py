# ui/settings_widget.py
# ============================================================
# ویجت تنظیمات پیشرفته — نسخه 4.0 (Theme-Integrated)
# ============================================================

import os
import shutil
import platform
import logging
from datetime import datetime

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from database import get_db
from shamsi_date import ShamsiDateEdit, get_today_jalali
from persiantools.jdatetime import JalaliDate
from ui.base_widgets import BaseWidget

logger = logging.getLogger(__name__)


class SettingsWidget(BaseWidget):
    """ویجت تنظیمات پیشرفته سیستم — با تم یکپارچه"""
    
    # ========== سیگنال‌ها ==========
    date_system_changed = pyqtSignal(str)
    valuation_method_changed = pyqtSignal(str)
    company_info_changed = pyqtSignal(dict)
    template_changed = pyqtSignal(dict)
    fiscal_year_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None, user_level: str = 'viewer'):
        super().__init__(parent)
        self._user_level = user_level
        self._backup_timer = None
        self._is_loading = False
        self._current_date_system = "شمسی"
        
        self.init_ui()
        self.load_settings()
        self.setup_signals()
        self._setup_auto_backup()
        self.update_ui_by_permission()
        self._apply_widget_theme()
    
    # ============================================================
    # Theme — کامل و یکپارچه
    # ============================================================
    
    def _apply_widget_theme(self):
        """اعمال تم روی کل ویجت و همه فرزندان"""
        try:
            c = self.get_theme_colors()
            
            # 1. خود ویجت
            self.setStyleSheet(f"""
                QWidget {{
                    background: {c['bg']};
                    color: {c['text']};
                }}
            """)
            
            # 2. TabWidget
            if hasattr(self, 'tabs'):
                self.tabs.setStyleSheet(f"""
                    QTabWidget::pane {{
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                        background: {c['bg']};
                    }}
                    QTabBar::tab {{
                        padding: 10px 18px;
                        margin: 2px;
                        border-radius: 6px;
                        background: {c['bg_alt']};
                        color: {c['text']};
                        font-weight: bold;
                    }}
                    QTabBar::tab:selected {{
                        background: {c['selected']};
                        color: {c['selected_text']};
                    }}
                    QTabBar::tab:hover {{
                        background: {c['hover']};
                    }}
                """)
            
            # 3. همه QGroupBoxها
            for gb in self.findChildren(QGroupBox):
                gb.setStyleSheet(f"""
                    QGroupBox {{
                        background: {c['card']};
                        color: {c['text']};
                        border: 2px solid {c['border']};
                        border-radius: 8px;
                        margin-top: 15px;
                        padding: 15px 10px 10px 10px;
                        font-weight: bold;
                        font-size: 11pt;
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        subcontrol-position: top right;
                        right: 15px;
                        padding: 0 8px;
                        color: {c['selected']};
                        background: {c['bg']};
                    }}
                """)
            
            # 4. ScrollArea
            for sa in self.findChildren(QScrollArea):
                sa.setStyleSheet(f"""
                    QScrollArea {{
                        border: none;
                        background: transparent;
                    }}
                    QScrollBar:vertical {{
                        background: {c['bg_alt']};
                        width: 10px;
                        border-radius: 5px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: {c['border']};
                        border-radius: 5px;
                        min-height: 20px;
                    }}
                    QScrollBar::handle:vertical:hover {{
                        background: {c['selected']};
                    }}
                """)
            
            # 5. QTextEditها
            for te in self.findChildren(QTextEdit):
                te.setStyleSheet(f"""
                    QTextEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                    }}
                """)
            
            # 6. QLineEditها
            for le in self.findChildren(QLineEdit):
                le.setStyleSheet(f"""
                    QLineEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 6px 10px;
                        min-height: 26px;
                    }}
                    QLineEdit:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
            # 7. QComboBoxها
            for cb in self.findChildren(QComboBox):
                cb.setStyleSheet(f"""
                    QComboBox {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 6px 10px;
                        min-height: 26px;
                    }}
                    QComboBox:focus {{
                        border: 2px solid {c['selected']};
                    }}
                    QComboBox::drop-down {{
                        border: none;
                        width: 24px;
                    }}
                    QComboBox QAbstractItemView {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        selection-background-color: {c['selected']};
                        selection-color: {c['selected_text']};
                        border: 1px solid {c['border']};
                    }}
                """)
            
            # 8. QSpinBox و QDoubleSpinBox
            for sb in self.findChildren((QSpinBox, QDoubleSpinBox)):
                sb.setStyleSheet(f"""
                    QSpinBox, QDoubleSpinBox {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 6px;
                        min-height: 26px;
                    }}
                    QSpinBox:focus, QDoubleSpinBox:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
            # 9. QTimeEdit
            for t in self.findChildren(QTimeEdit):
                t.setStyleSheet(f"""
                    QTimeEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 6px;
                        min-height: 26px;
                    }}
                """)
            
            # 10. QLabelهای عمومی (بیرون گروه‌باکس)
            for lbl in self.findChildren(QLabel):
                if not lbl.styleSheet() or 'background' not in lbl.styleSheet():
                    text = lbl.text() or ""
                    # فقط لیبل‌های معمولی
                    if not any(text.startswith(p) for p in [
                        '🏢', '🖼️', '🌍', '📋', '📊', '💰', '🤖',
                        '💾', '🔧', '📅', '⚙️', '📝', '💡'
                    ]):
                        lbl.setStyleSheet(
                            f"color: {c['text']}; background: transparent; padding: 3px;"
                        )
            
            # 11. status_label (مخصوص)
            if hasattr(self, 'status_label'):
                self.status_label.setStyleSheet(
                    f"color: {c['success']}; padding: 5px; font-size: 9pt;"
                )
            
            # 12. fiscal_status_label
            if hasattr(self, 'fiscal_status_label'):
                self.fiscal_status_label.setStyleSheet(
                    f"color: {c['text_secondary']}; font-size: 9pt; padding: 5px;"
                )
            
            # 13. template_opacity_label
            if hasattr(self, 'template_opacity_label'):
                self.template_opacity_label.setStyleSheet(
                    f"font-weight: bold; color: {c['warning']};"
                )
            
            # 14. last_backup_label
            if hasattr(self, 'last_backup_label'):
                self.last_backup_label.setStyleSheet(
                    f"color: {c['text_secondary']}; font-size: 9pt;"
                )
            
            # 15. template_preview
            if hasattr(self, 'template_preview'):
                try:
                    pm = self.template_preview.pixmap()
                    if not pm or pm.isNull():
                        self.template_preview.setStyleSheet(f"""
                            border: 2px dashed {c['border']};
                            background: {c['bg_alt']};
                            border-radius: 8px;
                            color: {c['text_secondary']};
                        """)
                    else:
                        self.template_preview.setStyleSheet(f"""
                            border: 2px solid {c['success']};
                            background: {c['bg_alt']};
                            border-radius: 8px;
                        """)
                except Exception:
                    pass
            
            # 16. preview_text (خاص)
            if hasattr(self, 'preview_text'):
                self.preview_text.setStyleSheet(f"""
                    QTextEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        font-size: 10pt;
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                        font-family: Tahoma;
                    }}
                """)
            
            # 17. fiscal_info_text
            if hasattr(self, 'fiscal_info_text'):
                self.fiscal_info_text.setStyleSheet(f"""
                    QTextEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                        font-family: Tahoma;
                    }}
                """)
            
            # 18. system_info
            if hasattr(self, 'system_info'):
                self.system_info.setStyleSheet(f"""
                    QTextEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                        font-family: 'Courier New', monospace;
                    }}
                """)
            
            # 19. Slider
            for slider in self.findChildren(QSlider):
                slider.setStyleSheet(f"""
                    QSlider::groove:horizontal {{
                        height: 6px;
                        background: {c['border']};
                        border-radius: 3px;
                    }}
                    QSlider::handle:horizontal {{
                        width: 18px;
                        margin: -6px 0;
                        background: {c['selected']};
                        border-radius: 9px;
                    }}
                    QSlider::sub-page:horizontal {{
                        background: {c['selected']};
                        border-radius: 3px;
                    }}
                """)
            
            # 20. QCheckBox
            for chk in self.findChildren(QCheckBox):
                chk.setStyleSheet(f"""
                    QCheckBox {{
                        color: {c['text']};
                        background: transparent;
                        spacing: 8px;
                        padding: 4px;
                    }}
                    QCheckBox::indicator {{
                        width: 18px;
                        height: 18px;
                        border-radius: 4px;
                        border: 2px solid {c['border']};
                        background: {c['bg_alt']};
                    }}
                    QCheckBox::indicator:checked {{
                        background: {c['selected']};
                        border-color: {c['selected']};
                    }}
                """)
        
        except Exception as e:
            print(f"⚠️ خطا در _apply_widget_theme: {e}")
    
    # ============================================================
    # Permission
    # ============================================================
    
    def set_user_level(self, level: str):
        self._user_level = level
        self.update_ui_by_permission()
    
    def get_user_level(self) -> str:
        return self._user_level
    
    def has_permission(self, required_level: str) -> bool:
        priority = {
            'admin': 5, 'accountant': 4, 'payroll': 3,
            'inventory': 2, 'viewer': 1
        }
        return priority.get(self._user_level, 0) >= priority.get(required_level, 0)
    
    def update_ui_by_permission(self):
        is_admin = self._user_level == 'admin'
        is_accountant = self._user_level in ['admin', 'accountant']
        is_payroll = self._user_level in ['admin', 'payroll']
        is_inventory = self._user_level in ['admin', 'inventory']
        
        # Company — admin
        for attr in ['company_name', 'company_legal_name', 'company_registration',
                     'company_economic', 'company_national', 'company_phone',
                     'company_address']:
            if hasattr(self, attr):
                getattr(self, attr).setEnabled(is_admin)
        
        # Template — admin + accountant
        for attr in ['template_path', 'template_position', 'template_opacity']:
            if hasattr(self, attr):
                getattr(self, attr).setEnabled(is_admin or is_accountant)
        
        # Region — admin
        for attr in ['currency', 'date_system', 'language']:
            if hasattr(self, attr):
                getattr(self, attr).setEnabled(is_admin)
        
        # Accounting — admin + accountant
        for attr in ['fiscal_year_start', 'fiscal_year_end', 'tax_rate']:
            if hasattr(self, attr):
                getattr(self, attr).setEnabled(is_admin or is_accountant)
        
        # Inventory — admin + inventory
        for attr in ['valuation_method', 'low_stock_warning', 'low_stock_percent']:
            if hasattr(self, attr):
                getattr(self, attr).setEnabled(is_admin or is_inventory)
        
        # Payroll — admin + payroll
        for attr in ['insurance_employee', 'insurance_employer', 'overtime_rate',
                     'night_rate', 'friday_rate', 'child_allowance',
                     'housing_allowance', 'meal_allowance']:
            if hasattr(self, attr):
                getattr(self, attr).setEnabled(is_admin or is_payroll)
        
        # AI — admin
        for attr in ['ai_enabled', 'ai_confidence', 'ai_classification',
                     'ai_auto_predict']:
            if hasattr(self, attr):
                getattr(self, attr).setEnabled(is_admin)
        
        # Backup — admin
        for attr in ['auto_backup', 'backup_time', 'backup_keep', 'backup_path']:
            if hasattr(self, attr):
                getattr(self, attr).setEnabled(is_admin)
        
        if not is_admin and hasattr(self, 'status_label'):
            c = self.get_theme_colors()
            self.status_label.setText("🔒 برخی تنظیمات فقط برای مدیر سیستم قابل تغییر است")
            self.status_label.setStyleSheet(
                f"color: {c['warning']}; padding: 5px; font-size: 9pt;"
            )
    
    # ============================================================
    # Signals
    # ============================================================
    
    def setup_signals(self):
        self.company_info_changed.connect(self.on_company_info_changed)
        self.date_system_changed.connect(self.on_date_system_changed)
        self.valuation_method_changed.connect(self.on_valuation_method_changed)
        self.template_changed.connect(self.on_template_changed)
        self.fiscal_year_changed.connect(self.on_fiscal_year_changed)
    
    def on_company_info_changed(self, info):
        try:
            main_window = self.window()
            if main_window and hasattr(main_window, 'setWindowTitle'):
                customer = info.get('company_name', 'ImanAccount')
                main_window.setWindowTitle(f"🤖 ImanAccount | {customer}")
            
            if self.core:
                self.notify(f"اطلاعات شرکت ذخیره شد: {customer}", "success")
        except Exception as e:
            logger.warning(f"خطا: {e}")
    
    def on_date_system_changed(self, new_system):
        try:
            self._current_date_system = new_system
            self._update_date_widgets()
            
            if self.core:
                self.core.event_bus.publish("date_system.changed", {
                    'system': new_system
                })
        except Exception as e:
            logger.warning(f"خطا: {e}")
    
    def on_fiscal_year_changed(self, data):
        try:
            logger.info(f"📅 سال مالی: {data}")
            if self.core:
                self.core.event_bus.publish("fiscal_year.changed", data)
        except Exception as e:
            logger.warning(f"خطا: {e}")
    
    def _update_date_widgets(self):
        for attr in ['fiscal_year_start', 'fiscal_year_end']:
            if hasattr(self, attr):
                try:
                    getattr(self, attr).set_date_system(self._current_date_system)
                except Exception:
                    pass
    
    def on_valuation_method_changed(self, new_method):
        try:
            if self.core:
                self.core.event_bus.publish("valuation_method.changed", {
                    'method': new_method
                })
        except Exception as e:
            logger.warning(f"خطا: {e}")
    
    def on_template_changed(self, info):
        try:
            if self.core:
                self.core.event_bus.publish("template.changed", info)
        except Exception as e:
            logger.warning(f"خطا: {e}")
    
    # ============================================================
    # Backup Timer
    # ============================================================
    
    def _setup_auto_backup(self):
        if hasattr(self, 'auto_backup'):
            if self.auto_backup.isChecked():
                self._start_backup_timer()
            else:
                self._stop_backup_timer()
            
            try:
                self.auto_backup.toggled.disconnect()
            except Exception:
                pass
            self.auto_backup.toggled.connect(self._on_auto_backup_toggled)
    
    def _on_auto_backup_toggled(self, checked):
        if checked:
            self._start_backup_timer()
        else:
            self._stop_backup_timer()
    
    def _start_backup_timer(self):
        if self._backup_timer is None and hasattr(self, 'backup_time'):
            self._backup_timer = QTimer()
            self._backup_timer.timeout.connect(self._auto_backup_now)
            
            current_time = QTime.currentTime()
            backup_time = self.backup_time.time()
            
            if current_time < backup_time:
                msecs = current_time.msecsTo(backup_time)
            else:
                msecs = (current_time.msecsTo(QTime(23, 59, 59)) +
                         backup_time.msecsTo(QTime(0, 0, 0)))
            
            self._backup_timer.start(msecs + 1000)
    
    def _stop_backup_timer(self):
        if self._backup_timer:
            self._backup_timer.stop()
            self._backup_timer = None
    
    def _auto_backup_now(self):
        try:
            db_path = os.path.join(
                os.environ.get('APPDATA', ''), 'ImanAccount', 'accounting.db'
            )
            if os.path.exists(db_path):
                backup_dir = self.backup_path.text()
                os.makedirs(backup_dir, exist_ok=True)
                backup_file = os.path.join(
                    backup_dir,
                    f"auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                )
                shutil.copy2(db_path, backup_file)
                self._cleanup_old_backups(backup_dir)
                
                self.last_backup_label.setText(
                    f"📅 آخرین پشتیبان: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
                )
                
                if self.core:
                    self.notify("پشتیبان خودکار ساخته شد", "success")
                
                self._backup_timer.start(24 * 60 * 60 * 1000)
        except Exception as e:
            logger.error(f"❌ خطا: {e}")
    
    def _cleanup_old_backups(self, backup_dir):
        try:
            keep = self.backup_keep.value()
            files = sorted(
                [f for f in os.listdir(backup_dir)
                 if f.startswith('auto_backup_') and f.endswith('.db')],
                key=lambda f: os.path.getmtime(os.path.join(backup_dir, f))
            )
            while len(files) > keep:
                old = os.path.join(backup_dir, files.pop(0))
                os.remove(old)
        except Exception:
            pass
    
    # ============================================================
    # UI Setup
    # ============================================================
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        title = QLabel("⚙️ تنظیمات پیشرفته سیستم")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.tabs.addTab(self.create_general_tab(), "🏢 عمومی")
        self.tabs.addTab(self.create_accounting_tab(), "📊 حسابداری")
        self.tabs.addTab(self.create_inventory_tab(), "📦 انبار")
        self.tabs.addTab(self.create_payroll_tab(), "💰 حقوق")
        self.tabs.addTab(self.create_ai_tab(), "🤖 هوش مصنوعی")
        self.tabs.addTab(self.create_backup_tab(), "💾 پشتیبان")
        self.tabs.addTab(self.create_advanced_tab(), "🔧 پیشرفته")
        
        self.status_label = QLabel("✅ تنظیمات بارگذاری شد")
        layout.addWidget(self.status_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره تنظیمات")
        save_btn.setObjectName("successBtn")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.save_settings)
        save_btn.setEnabled(self._user_level == 'admin')
        btn_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("↩️ بازنشانی به پیش‌فرض")
        reset_btn.setObjectName("warningBtn")
        reset_btn.setMinimumHeight(40)
        reset_btn.clicked.connect(self.reset_settings)
        reset_btn.setEnabled(self._user_level == 'admin')
        btn_layout.addWidget(reset_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.load_settings)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def mark_changed(self):
        if hasattr(self, 'status_label'):
            c = self.get_theme_colors()
            self.status_label.setText("⚠️ تنظیمات تغییر کرده است. ذخیره کنید.")
            self.status_label.setStyleSheet(
                f"color: {c['warning']}; padding: 5px; font-size: 9pt;"
            )
    
    # ============================================================
    # تب عمومی — بدون hard-coded style
    # ============================================================
    
    def create_general_tab(self):
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ===== اطلاعات شرکت =====
        company_group = QGroupBox("🏢 اطلاعات شرکت")
        company_layout = QFormLayout(company_group)
        company_layout.setSpacing(10)
        company_layout.setLabelAlignment(Qt.AlignRight)
        
        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("نام شرکت")
        self.company_name.textChanged.connect(self.mark_changed)
        company_layout.addRow("نام شرکت *:", self.company_name)
        
        self.company_legal_name = QLineEdit()
        self.company_legal_name.setPlaceholderText("نام حقوقی شرکت")
        self.company_legal_name.textChanged.connect(self.mark_changed)
        company_layout.addRow("نام حقوقی:", self.company_legal_name)
        
        self.company_registration = QLineEdit()
        self.company_registration.setPlaceholderText("شماره ثبت")
        company_layout.addRow("شماره ثبت:", self.company_registration)
        
        self.company_economic = QLineEdit()
        self.company_economic.setPlaceholderText("کد اقتصادی")
        company_layout.addRow("کد اقتصادی:", self.company_economic)
        
        self.company_national = QLineEdit()
        self.company_national.setPlaceholderText("شناسه ملی")
        company_layout.addRow("شناسه ملی:", self.company_national)
        
        self.company_phone = QLineEdit()
        self.company_phone.setPlaceholderText("تلفن")
        company_layout.addRow("تلفن:", self.company_phone)
        
        self.company_address = QTextEdit()
        self.company_address.setMaximumHeight(60)
        self.company_address.setPlaceholderText("آدرس کامل")
        company_layout.addRow("آدرس:", self.company_address)
        
        layout.addWidget(company_group)
        
        # ===== قالب فاکتور =====
        template_group = QGroupBox("🖼️ قالب فاکتور")
        template_layout = QVBoxLayout(template_group)
        template_layout.setSpacing(10)
        
        file_layout = QHBoxLayout()
        self.template_path = QLineEdit()
        self.template_path.setPlaceholderText("مسیر فایل قالب (PNG, JPG, JPEG)")
        self.template_path.textChanged.connect(self.mark_changed)
        self.template_path.textChanged.connect(self.load_template_preview)
        file_layout.addWidget(self.template_path, 3)
        
        browse_btn = QPushButton("📁 انتخاب")
        browse_btn.setObjectName("infoBtn")
        browse_btn.clicked.connect(self.select_template_image)
        file_layout.addWidget(browse_btn)
        
        clear_btn = QPushButton("🗑️ حذف")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(self.clear_template)
        file_layout.addWidget(clear_btn)
        
        template_layout.addLayout(file_layout)
        
        settings_layout = QGridLayout()
        settings_layout.setSpacing(15)
        
        settings_layout.addWidget(QLabel("موقعیت:"), 0, 0)
        self.template_position = QComboBox()
        self.template_position.addItems([
            "پس‌زمینه کامل", "هدر (بالا)", "فوتر (پایین)",
            "کنار (چپ)", "کنار (راست)"
        ])
        self.template_position.currentIndexChanged.connect(self.mark_changed)
        settings_layout.addWidget(self.template_position, 0, 1)
        
        settings_layout.addWidget(QLabel("شفافیت:"), 1, 0)
        opacity_layout = QHBoxLayout()
        self.template_opacity = QSlider(Qt.Horizontal)
        self.template_opacity.setRange(5, 100)
        self.template_opacity.setValue(30)
        self.template_opacity.valueChanged.connect(self.mark_changed)
        self.template_opacity.valueChanged.connect(
            lambda v: self.template_opacity_label.setText(f"{v}%")
        )
        opacity_layout.addWidget(self.template_opacity)
        
        self.template_opacity_label = QLabel("30%")
        self.template_opacity_label.setMinimumWidth(40)
        opacity_layout.addWidget(self.template_opacity_label)
        settings_layout.addLayout(opacity_layout, 1, 1)
        
        template_layout.addLayout(settings_layout)
        
        preview_label = QLabel("پیش‌نمایش قالب:")
        template_layout.addWidget(preview_label)
        
        preview_container = QHBoxLayout()
        self.template_preview = QLabel()
        self.template_preview.setFixedSize(180, 240)
        self.template_preview.setAlignment(Qt.AlignCenter)
        self.template_preview.setText("📄\nپیش‌نمایش\nقالب")
        preview_container.addWidget(self.template_preview)
        preview_container.addStretch()
        template_layout.addLayout(preview_container)
        
        desc = QLabel("💡 نکته: از تصاویر با پس‌زمینه شفاف (PNG) استفاده کنید.")
        desc.setStyleSheet("color: #888; font-size: 9pt; font-style: italic; padding: 5px;")
        template_layout.addWidget(desc)
        
        layout.addWidget(template_group)
        
        # ===== تنظیمات منطقه‌ای =====
        region_group = QGroupBox("🌍 تنظیمات منطقه‌ای")
        region_layout = QFormLayout(region_group)
        region_layout.setSpacing(10)
        region_layout.setLabelAlignment(Qt.AlignRight)
        
        self.currency = QComboBox()
        self.currency.addItems(["ریال", "تومان", "دلار", "یورو"])
        self.currency.currentIndexChanged.connect(self.mark_changed)
        region_layout.addRow("واحد پول:", self.currency)
        
        self.date_system = QComboBox()
        self.date_system.addItems(["شمسی", "میلادی"])
        self.date_system.currentTextChanged.connect(self.on_date_system_changed)
        region_layout.addRow("سیستم تاریخ:", self.date_system)
        
        self.language = QComboBox()
        self.language.addItems(["فارسی", "English"])
        region_layout.addRow("زبان:", self.language)
        
        layout.addWidget(region_group)
        
        # ===== پیش‌نمایش =====
        preview_group = QGroupBox("📋 پیش‌نمایش اطلاعات شرکت")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(80)
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        layout.addStretch()
        
        # Connect preview
        self.company_name.textChanged.connect(self.update_preview)
        self.company_legal_name.textChanged.connect(self.update_preview)
        self.company_phone.textChanged.connect(self.update_preview)
        self.company_address.textChanged.connect(self.update_preview)
        
        scroll.setWidget(container)
        
        main = QVBoxLayout(widget)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)
        return widget
    
    def update_preview(self):
        preview = f"""
🏢 {self.company_name.text() or 'نام شرکت'}
📋 {self.company_legal_name.text() or 'نام حقوقی'}
📞 {self.company_phone.text() or 'تلفن'}
📍 {self.company_address.toPlainText() or 'آدرس'}
        """
        self.preview_text.setText(preview)
    
    def select_template_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب تصویر قالب", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.template_path.setText(path)
            self.load_template_preview()
            self.mark_changed()
    
    def clear_template(self):
        if QMessageBox.question(
            self, "تأیید", "قالب فاکتور حذف بشه؟",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.template_path.clear()
            self.load_template_preview()
            self.mark_changed()
    
    def load_template_preview(self):
        path = self.template_path.text()
        c = self.get_theme_colors()
        
        if path and os.path.exists(path):
            try:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        180, 240,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.template_preview.setPixmap(scaled)
                    self.template_preview.setText("")
                    self.template_preview.setStyleSheet(f"""
                        border: 2px solid {c['success']};
                        background: {c['bg_alt']};
                        border-radius: 8px;
                    """)
                    return
            except Exception:
                pass
        
        self.template_preview.clear()
        self.template_preview.setStyleSheet(f"""
            border: 2px dashed {c['border']};
            background: {c['bg_alt']};
            border-radius: 8px;
            color: {c['text_secondary']};
        """)
        self.template_preview.setText("📄\nپیش‌نمایش\nقالب")
    
    # ============================================================
    # تب حسابداری
    # ============================================================
    
    def create_accounting_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        fiscal_label = QLabel("📅 سال مالی")
        fiscal_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addRow(fiscal_label)
        
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("شروع:"))
        self.fiscal_year_start = ShamsiDateEdit()
        self.fiscal_year_start.dateChanged.connect(self._on_fiscal_date_changed)
        start_layout.addWidget(self.fiscal_year_start)
        
        start_today = QPushButton("📅 امروز")
        start_today.setMaximumWidth(80)
        start_today.clicked.connect(
            lambda: self.fiscal_year_start.set_date(get_today_jalali())
        )
        start_layout.addWidget(start_today)
        
        start_year = QPushButton("📆 اول سال")
        start_year.setMaximumWidth(80)
        start_year.clicked.connect(self._set_fiscal_year_start)
        start_layout.addWidget(start_year)
        
        layout.addRow(start_layout)
        
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("پایان:"))
        self.fiscal_year_end = ShamsiDateEdit()
        self.fiscal_year_end.dateChanged.connect(self._on_fiscal_date_changed)
        end_layout.addWidget(self.fiscal_year_end)
        
        end_today = QPushButton("📅 امروز")
        end_today.setMaximumWidth(80)
        end_today.clicked.connect(
            lambda: self.fiscal_year_end.set_date(get_today_jalali())
        )
        end_layout.addWidget(end_today)
        
        end_year = QPushButton("📆 آخر سال")
        end_year.setMaximumWidth(80)
        end_year.clicked.connect(self._set_fiscal_year_end)
        end_layout.addWidget(end_year)
        
        layout.addRow(end_layout)
        
        self.fiscal_status_label = QLabel("")
        layout.addRow(self.fiscal_status_label)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addRow(sep)
        
        tax_label = QLabel("💰 تنظیمات مالیاتی")
        tax_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addRow(tax_label)
        
        self.tax_rate = QDoubleSpinBox()
        self.tax_rate.setRange(0, 100)
        self.tax_rate.setValue(10)
        self.tax_rate.setSuffix(" %")
        self.tax_rate.valueChanged.connect(self.mark_changed)
        layout.addRow("نرخ مالیات:", self.tax_rate)
        
        display_label = QLabel("📊 تنظیمات نمایش")
        display_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addRow(display_label)
        
        self.decimal_places = QSpinBox()
        self.decimal_places.setRange(0, 4)
        self.decimal_places.setValue(0)
        self.decimal_places.valueChanged.connect(self.mark_changed)
        layout.addRow("تعداد اعشار:", self.decimal_places)
        
        self.thousand_separator = QComboBox()
        self.thousand_separator.addItems([",", ".", " ", "بدون جداکننده"])
        self.thousand_separator.currentIndexChanged.connect(self.mark_changed)
        layout.addRow("جداکننده هزارگان:", self.thousand_separator)
        
        info_group = QGroupBox("📋 اطلاعات سال مالی")
        info_layout = QVBoxLayout(info_group)
        
        self.fiscal_info_text = QTextEdit()
        self.fiscal_info_text.setReadOnly(True)
        self.fiscal_info_text.setMaximumHeight(80)
        info_layout.addWidget(self.fiscal_info_text)
        
        layout.addRow(info_group)
        
        return widget
    
    def _on_fiscal_date_changed(self, date_str):
        self.mark_changed()
        self._update_fiscal_info()
    
    def _set_fiscal_year_start(self):
        try:
            today = JalaliDate.today()
            self.fiscal_year_start.set_date(f"{today.year:04d}/01/01")
            self.mark_changed()
        except Exception as e:
            logger.warning(f"خطا: {e}")
    
    def _set_fiscal_year_end(self):
        try:
            today = JalaliDate.today()
            end_day = 30 if JalaliDate.is_leap(today.year) else 29
            self.fiscal_year_end.set_date(f"{today.year:04d}/12/{end_day}")
            self.mark_changed()
        except Exception as e:
            logger.warning(f"خطا: {e}")
    
    def _update_fiscal_info(self):
        start = self.fiscal_year_start.get_shamsi()
        end = self.fiscal_year_end.get_shamsi()
        
        if not start or not end:
            return
        
        try:
            sp = start.split('/')
            ep = end.split('/')
            
            if len(sp) == 3 and len(ep) == 3:
                sj = JalaliDate(int(sp[0]), int(sp[1]), int(sp[2]))
                ej = JalaliDate(int(ep[0]), int(ep[1]), int(ep[2]))
                
                days = (ej.to_gregorian() - sj.to_gregorian()).days
                months = (ej.year - sj.year) * 12 + (ej.month - sj.month)
                
                info = f"""
📅 سال مالی: {start} تا {end}
⏱️ مدت: {months} ماه ({days} روز)
📊 وضعیت: {'✅ معتبر' if days >= 0 else '❌ نامعتبر'}
                """
                self.fiscal_info_text.setText(info)
                
                c = self.get_theme_colors()
                if days < 0:
                    self.fiscal_status_label.setText("⚠️ پایان باید بعد از شروع باشه!")
                    self.fiscal_status_label.setStyleSheet(
                        f"color: {c['danger']}; font-size: 9pt; padding: 5px;"
                    )
                else:
                    self.fiscal_status_label.setText(f"✅ سال مالی {start[:4]} معتبر است")
                    self.fiscal_status_label.setStyleSheet(
                        f"color: {c['success']}; font-size: 9pt; padding: 5px;"
                    )
        except Exception as e:
            self.fiscal_info_text.setText(f"⚠️ خطا: {e}")
    
    # ============================================================
    # تب انبار
    # ============================================================
    
    def create_inventory_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.valuation_method = QComboBox()
        self.valuation_method.addItems([
            "ساده (قیمت خرید)",
            "FIFO (اولین ورودی - اولین خروجی)",
            "LIFO (آخرین ورودی - اولین خروجی)",
            "میانگین موزون"
        ])
        self.valuation_method.currentTextChanged.connect(
            self.on_valuation_method_changed
        )
        layout.addRow("روش ارزشیابی:", self.valuation_method)
        
        self.low_stock_warning = QCheckBox("فعالسازی هشدار موجودی کم")
        self.low_stock_warning.setChecked(True)
        self.low_stock_warning.toggled.connect(self.mark_changed)
        layout.addRow("", self.low_stock_warning)
        
        self.low_stock_percent = QSpinBox()
        self.low_stock_percent.setRange(0, 100)
        self.low_stock_percent.setValue(20)
        self.low_stock_percent.setSuffix(" %")
        layout.addRow("درصد هشدار:", self.low_stock_percent)
        
        desc = QLabel("""
• ساده: موجودی × قیمت خرید
• FIFO: اولین ورودی، اولین خروجی
• LIFO: آخرین ورودی، اولین خروجی
• میانگین موزون: میانگین قیمت خرید
        """)
        desc.setStyleSheet("color: #888; font-size: 9pt;")
        layout.addRow(desc)
        
        return widget
    
    # ============================================================
    # تب حقوق
    # ============================================================
    
    def create_payroll_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.insurance_employee = QDoubleSpinBox()
        self.insurance_employee.setRange(0, 100)
        self.insurance_employee.setValue(7)
        self.insurance_employee.setSuffix(" %")
        layout.addRow("بیمه سهم کارمند:", self.insurance_employee)
        
        self.insurance_employer = QDoubleSpinBox()
        self.insurance_employer.setRange(0, 100)
        self.insurance_employer.setValue(23)
        self.insurance_employer.setSuffix(" %")
        layout.addRow("بیمه سهم کارفرما:", self.insurance_employer)
        
        self.overtime_rate = QDoubleSpinBox()
        self.overtime_rate.setRange(1, 3)
        self.overtime_rate.setValue(1.5)
        self.overtime_rate.setSingleStep(0.1)
        self.overtime_rate.setSuffix(" برابر")
        layout.addRow("نرخ اضافه کاری:", self.overtime_rate)
        
        self.night_rate = QDoubleSpinBox()
        self.night_rate.setRange(0, 1)
        self.night_rate.setValue(0.35)
        self.night_rate.setSingleStep(0.05)
        self.night_rate.setSuffix(" (۳۵٪)")
        layout.addRow("نرخ شب کاری:", self.night_rate)
        
        self.friday_rate = QDoubleSpinBox()
        self.friday_rate.setRange(1, 2)
        self.friday_rate.setValue(1.5)
        self.friday_rate.setSingleStep(0.1)
        self.friday_rate.setSuffix(" برابر")
        layout.addRow("نرخ جمعه کاری:", self.friday_rate)
        
        self.child_allowance = QSpinBox()
        self.child_allowance.setRange(0, 50000000)
        self.child_allowance.setValue(15000000)
        self.child_allowance.setSingleStep(1000000)
        layout.addRow("حق اولاد:", self.child_allowance)
        
        self.housing_allowance = QSpinBox()
        self.housing_allowance.setRange(0, 50000000)
        self.housing_allowance.setValue(15000000)
        self.housing_allowance.setSingleStep(1000000)
        layout.addRow("حق مسکن:", self.housing_allowance)
        
        self.meal_allowance = QSpinBox()
        self.meal_allowance.setRange(0, 50000000)
        self.meal_allowance.setValue(14000000)
        self.meal_allowance.setSingleStep(1000000)
        layout.addRow("بن کارگری:", self.meal_allowance)
        
        return widget
    
    # ============================================================
    # تب AI
    # ============================================================
    
    def create_ai_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.ai_enabled = QCheckBox("فعالسازی دستیار هوشمند ImanAI")
        self.ai_enabled.setChecked(True)
        self.ai_enabled.toggled.connect(self.mark_changed)
        layout.addRow("", self.ai_enabled)
        
        self.ai_confidence = QSlider(Qt.Horizontal)
        self.ai_confidence.setRange(0, 100)
        self.ai_confidence.setValue(70)
        self.ai_confidence.valueChanged.connect(self.mark_changed)
        layout.addRow("حداقل اطمینان:", self.ai_confidence)
        
        self.ai_confidence_label = QLabel("70%")
        layout.addRow("", self.ai_confidence_label)
        self.ai_confidence.valueChanged.connect(
            lambda v: self.ai_confidence_label.setText(f"{v}%")
        )
        
        self.ai_classification = QComboBox()
        self.ai_classification.addItems([
            "سریع (کلمات کلیدی)", "متوسط", "دقیق (شبکه عصبی)"
        ])
        self.ai_classification.currentIndexChanged.connect(self.mark_changed)
        layout.addRow("دقت دسته‌بندی:", self.ai_classification)
        
        self.ai_auto_predict = QCheckBox("پیش‌بینی خودکار جریان نقدی")
        self.ai_auto_predict.setChecked(False)
        self.ai_auto_predict.toggled.connect(self.mark_changed)
        layout.addRow("", self.ai_auto_predict)
        
        return widget
    
    # ============================================================
    # تب پشتیبان
    # ============================================================
    
    def create_backup_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.auto_backup = QCheckBox("فعالسازی پشتیبان خودکار")
        self.auto_backup.setChecked(True)
        self.auto_backup.toggled.connect(self.mark_changed)
        layout.addRow("", self.auto_backup)
        
        self.backup_time = QTimeEdit()
        self.backup_time.setTime(QTime(12, 0))
        self.backup_time.timeChanged.connect(self.mark_changed)
        layout.addRow("زمان پشتیبان‌گیری:", self.backup_time)
        
        self.backup_keep = QSpinBox()
        self.backup_keep.setRange(1, 30)
        self.backup_keep.setValue(7)
        layout.addRow("تعداد نگهداری:", self.backup_keep)
        
        path_layout = QHBoxLayout()
        self.backup_path = QLineEdit()
        self.backup_path.setPlaceholderText("مسیر پشتیبان")
        self.backup_path.setText(
            os.path.join(os.environ.get('USERPROFILE', ''),
                         "Documents", "ImanAccountBackup")
        )
        self.backup_path.textChanged.connect(self.mark_changed)
        path_layout.addWidget(self.backup_path)
        
        browse_btn = QPushButton("📁")
        browse_btn.clicked.connect(self.select_backup_path)
        path_layout.addWidget(browse_btn)
        
        layout.addRow("مسیر:", path_layout)
        
        backup_btn = QPushButton("💾 پشتیبان‌گیری فوری")
        backup_btn.setObjectName("successBtn")
        backup_btn.clicked.connect(self.backup_now)
        layout.addRow(backup_btn)
        
        self.last_backup_label = QLabel("📅 آخرین پشتیبان: هیچ")
        layout.addRow(self.last_backup_label)
        
        return widget
    
    def select_backup_path(self):
        path = QFileDialog.getExistingDirectory(self, "انتخاب مسیر پشتیبان")
        if path:
            self.backup_path.setText(path)
    
    def backup_now(self):
        db_path = os.path.join(
            os.environ.get('APPDATA', ''), 'ImanAccount', 'accounting.db'
        )
        if os.path.exists(db_path):
            backup_dir = self.backup_path.text()
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(
                backup_dir,
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            try:
                shutil.copy2(db_path, backup_file)
                self.last_backup_label.setText(
                    f"📅 آخرین پشتیبان: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
                )
                
                if self.core:
                    self.notify("پشتیبان ساخته شد", "success")
                
                QMessageBox.information(self, "موفق", f"✅ پشتیبان ذخیره شد:\n{backup_file}")
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    # ============================================================
    # تب پیشرفته
    # ============================================================
    
    def create_advanced_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.system_info = QTextEdit()
        self.system_info.setReadOnly(True)
        self.system_info.setMaximumHeight(120)
        self._update_system_info()
        layout.addRow("🖥️ اطلاعات سیستم:", self.system_info)
        
        clear_cache_btn = QPushButton("🗑️ پاک کردن کش")
        clear_cache_btn.setObjectName("warningBtn")
        clear_cache_btn.clicked.connect(self.clear_cache)
        layout.addRow(clear_cache_btn)
        
        optimize_btn = QPushButton("🔧 بهینه‌سازی دیتابیس")
        optimize_btn.setObjectName("infoBtn")
        optimize_btn.clicked.connect(self.optimize_database)
        layout.addRow(optimize_btn)
        
        return widget
    
    def clear_cache(self):
        if QMessageBox.question(
            self, "تأیید", "کش پاک بشه؟",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            try:
                memory_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "conversation_memory.pkl"
                )
                if os.path.exists(memory_path):
                    os.remove(memory_path)
                    QMessageBox.information(self, "موفق", "✅ کش پاک شد!")
                else:
                    QMessageBox.information(self, "توجه", "کشی وجود ندارد.")
            except Exception as e:
                QMessageBox.warning(self, "خطا", str(e))
    
    def optimize_database(self):
        try:
            with get_db() as conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
            
            if self.core:
                self.notify("دیتابیس بهینه شد", "success")
            
            QMessageBox.information(self, "موفق", "✅ بهینه‌سازی انجام شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", str(e))
    
    def _update_system_info(self):
        try:
            db_path = os.path.join(
                os.environ.get('APPDATA', ''), 'ImanAccount', 'accounting.db'
            )
            db_size = os.path.getsize(db_path) / (1024 * 1024) if os.path.exists(db_path) else 0
            
            info = f"""
• سیستم: {platform.system()} {platform.release()}
• پردازنده: {platform.processor() or 'نامشخص'}
• پایتون: {platform.python_version()}
• دیتابیس: {db_size:.2f} MB
• تاریخ: {get_today_jalali()}
            """
            self.system_info.setText(info)
        except Exception as e:
            self.system_info.setText(f"⚠️ خطا: {e}")
    
    # ============================================================
    # Static Methods
    # ============================================================
    
    @staticmethod
    def get_date_system():
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'date_system'")
                row = c.fetchone()
                return row[0] if row else "شمسی"
        except Exception:
            return "شمسی"
    
    @staticmethod
    def get_valuation_method():
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'valuation_method'")
                row = c.fetchone()
                return row[0] if row else "simple"
        except Exception:
            return "simple"
    
    @staticmethod
    def get_template_info():
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT key, value FROM settings 
                    WHERE key IN ('template_path', 'template_position', 'template_opacity')
                """)
                rows = c.fetchall()
                return {row['key']: row['value'] for row in rows}
        except Exception:
            return {}
    
    # ============================================================
    # Load / Save
    # ============================================================
    
    def load_settings(self):
        self._is_loading = True
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT key, value FROM settings")
                settings = dict(c.fetchall())
            
            # Company
            self.company_name.setText(settings.get('company_name', ''))
            self.company_legal_name.setText(settings.get('company_legal_name', ''))
            self.company_registration.setText(settings.get('company_registration', ''))
            self.company_economic.setText(settings.get('company_economic', ''))
            self.company_national.setText(settings.get('company_national', ''))
            self.company_phone.setText(settings.get('company_phone', ''))
            self.company_address.setText(settings.get('company_address', ''))
            
            # Template
            self.template_path.setText(settings.get('template_path', ''))
            pos = settings.get('template_position', 'پس‌زمینه کامل')
            idx = self.template_position.findText(pos)
            if idx >= 0:
                self.template_position.setCurrentIndex(idx)
            try:
                self.template_opacity.setValue(int(settings.get('template_opacity', '30')))
            except Exception:
                pass
            self.load_template_preview()
            
            # Region
            idx = self.currency.findText(settings.get('currency', 'ریال'))
            if idx >= 0:
                self.currency.setCurrentIndex(idx)
            
            ds = settings.get('date_system', 'شمسی')
            idx = self.date_system.findText(ds)
            if idx >= 0:
                self.date_system.setCurrentIndex(idx)
                self._current_date_system = ds
            
            # Fiscal
            fs = settings.get('fiscal_year_start', '')
            fe = settings.get('fiscal_year_end', '')
            
            if fs:
                try:
                    self.fiscal_year_start.set_date(fs)
                except Exception:
                    pass
            else:
                self._set_fiscal_year_start()
            
            if fe:
                try:
                    self.fiscal_year_end.set_date(fe)
                except Exception:
                    pass
            else:
                self._set_fiscal_year_end()
            
            self._update_fiscal_info()
            
            # Valuation
            val = settings.get('valuation_method', 'simple')
            val_map = {
                'simple': "ساده (قیمت خرید)",
                'fifo': "FIFO (اولین ورودی - اولین خروجی)",
                'lifo': "LIFO (آخرین ورودی - اولین خروجی)",
                'weighted_average': "میانگین موزون"
            }
            self.valuation_method.setCurrentText(val_map.get(val, "ساده (قیمت خرید)"))
            
            # Accounting
            try:
                self.tax_rate.setValue(float(settings.get('tax_rate', '10')))
            except Exception:
                pass
            
            # Payroll
            try:
                self.insurance_employee.setValue(float(settings.get('insurance_employee_rate', '7')))
                self.insurance_employer.setValue(float(settings.get('insurance_employer_rate', '23')))
                self.child_allowance.setValue(int(settings.get('child_allowance', '15000000')))
                self.housing_allowance.setValue(int(settings.get('housing_allowance', '15000000')))
                self.meal_allowance.setValue(int(settings.get('meal_allowance', '14000000')))
            except Exception:
                pass
            
            # AI
            self.ai_enabled.setChecked(settings.get('ai_enabled', 'true').lower() == 'true')
            try:
                self.ai_confidence.setValue(int(settings.get('ai_confidence', '70')))
            except Exception:
                pass
            
            # Backup
            self.auto_backup.setChecked(settings.get('auto_backup', 'true').lower() == 'true')
            try:
                self.backup_time.setTime(QTime.fromString(settings.get('backup_time', '12:00')))
            except Exception:
                pass
            try:
                self.backup_keep.setValue(int(settings.get('backup_keep', '7')))
            except Exception:
                pass
            
            backup_path = settings.get(
                'backup_path',
                os.path.join(os.environ.get('USERPROFILE', ''),
                             "Documents", "ImanAccountBackup")
            )
            self.backup_path.setText(backup_path)
            
            self.update_preview()
            self._update_system_info()
            self._setup_auto_backup()
            
            c = self.get_theme_colors()
            self.status_label.setText("✅ تنظیمات بارگذاری شد")
            self.status_label.setStyleSheet(
                f"color: {c['success']}; padding: 5px; font-size: 9pt;"
            )
        except Exception as e:
            logger.error(f"خطا در بارگذاری: {e}")
            c = self.get_theme_colors()
            self.status_label.setText("⚠️ خطا در بارگذاری تنظیمات")
            self.status_label.setStyleSheet(
                f"color: {c['danger']}; padding: 5px; font-size: 9pt;"
            )
        finally:
            self._is_loading = False
        
        self.update_ui_by_permission()
        self._apply_widget_theme()
    
    def save_settings(self):
        if not self.has_permission('admin'):
            QMessageBox.warning(
                self, "دسترسی محدود",
                "تنها مدیر سیستم می‌تواند تنظیمات را ذخیره کند!"
            )
            return
        
        old_val = self.get_valuation_method()
        new_val_text = self.valuation_method.currentText()
        val_map = {
            "ساده (قیمت خرید)": "simple",
            "FIFO (اولین ورودی - اولین خروجی)": "fifo",
            "LIFO (آخرین ورودی - اولین خروجی)": "lifo",
            "میانگین موزون": "weighted_average"
        }
        new_val = val_map.get(new_val_text, "simple")
        
        company_info = {
            'company_name': self.company_name.text().strip(),
            'company_legal_name': self.company_legal_name.text().strip(),
            'company_registration': self.company_registration.text().strip(),
            'company_economic': self.company_economic.text().strip(),
            'company_national': self.company_national.text().strip(),
            'company_phone': self.company_phone.text().strip(),
            'company_address': self.company_address.toPlainText().strip(),
        }
        
        template_info = {
            'template_path': self.template_path.text().strip(),
            'template_position': self.template_position.currentText(),
            'template_opacity': str(self.template_opacity.value())
        }
        
        fiscal_data = {
            'start': self.fiscal_year_start.get_shamsi(),
            'end': self.fiscal_year_end.get_shamsi()
        }
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                settings = [
                    ('company_name', company_info['company_name']),
                    ('company_legal_name', company_info['company_legal_name']),
                    ('company_registration', company_info['company_registration']),
                    ('company_economic', company_info['company_economic']),
                    ('company_national', company_info['company_national']),
                    ('company_phone', company_info['company_phone']),
                    ('company_address', company_info['company_address']),
                    ('currency', self.currency.currentText()),
                    ('date_system', self.date_system.currentText()),
                    ('fiscal_year_start', fiscal_data['start']),
                    ('fiscal_year_end', fiscal_data['end']),
                    ('tax_rate', str(self.tax_rate.value())),
                    ('valuation_method', new_val),
                    ('insurance_employee_rate', str(self.insurance_employee.value())),
                    ('insurance_employer_rate', str(self.insurance_employer.value())),
                    ('overtime_rate', str(self.overtime_rate.value())),
                    ('night_work_rate', str(self.night_rate.value())),
                    ('friday_work_rate', str(self.friday_rate.value())),
                    ('child_allowance', str(self.child_allowance.value())),
                    ('housing_allowance', str(self.housing_allowance.value())),
                    ('meal_allowance', str(self.meal_allowance.value())),
                    ('ai_enabled', str(self.ai_enabled.isChecked())),
                    ('ai_confidence', str(self.ai_confidence.value())),
                    ('ai_classification', self.ai_classification.currentText()),
                    ('ai_auto_predict', str(self.ai_auto_predict.isChecked())),
                    ('auto_backup', str(self.auto_backup.isChecked())),
                    ('backup_time', self.backup_time.time().toString()),
                    ('backup_keep', str(self.backup_keep.value())),
                    ('backup_path', self.backup_path.text()),
                    ('template_path', template_info['template_path']),
                    ('template_position', template_info['template_position']),
                    ('template_opacity', template_info['template_opacity']),
                ]
                
                for key, value in settings:
                    c.execute(
                        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                        (key, value)
                    )
                
                conn.commit()
            
            # Emit signals
            self.company_info_changed.emit(company_info)
            self.template_changed.emit(template_info)
            self.fiscal_year_changed.emit(fiscal_data)
            
            if old_val != new_val:
                self.valuation_method_changed.emit(new_val)
            
            self.date_system_changed.emit(self.date_system.currentText())
            
            self._setup_auto_backup()
            
            c = self.get_theme_colors()
            self.status_label.setText("✅ تنظیمات با موفقیت ذخیره شد!")
            self.status_label.setStyleSheet(
                f"color: {c['success']}; padding: 5px; font-size: 9pt;"
            )
            
            if self.core:
                self.notify(
                    f"تنظیمات ذخیره شد: {company_info['company_name']}",
                    "success"
                )
                self.core.data.notify_change("settings", "update", {
                    'company_name': company_info['company_name'],
                })
            
            QMessageBox.information(
                self, "موفق",
                "✅ تنظیمات با موفقیت ذخیره شد!\n\n"
                f"🏢 نام شرکت: {company_info['company_name'] or 'تعیین نشده'}\n"
                f"📅 سال مالی: {fiscal_data['start']} تا {fiscal_data['end']}\n"
                f"📦 روش ارزشیابی: {new_val_text}\n"
                f"📅 سیستم تاریخ: {self.date_system.currentText()}"
            )
        except Exception as e:
            c = self.get_theme_colors()
            self.status_label.setText("❌ خطا در ذخیره تنظیمات")
            self.status_label.setStyleSheet(
                f"color: {c['danger']}; padding: 5px; font-size: 9pt;"
            )
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")
    
    def reset_settings(self):
        if not self.has_permission('admin'):
            QMessageBox.warning(self, "دسترسی محدود", "تنها مدیر!")
            return
        
        if QMessageBox.question(
            self, "تأیید بازنشانی",
            "همه تنظیمات به حالت پیش‌فرض برگرده؟\n"
            "تمام تغییرات از دست خواهد رفت!",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM settings")
                    conn.commit()
                
                self.load_settings()
                
                if self.core:
                    self.notify("تنظیمات بازنشانی شد", "success")
                
                QMessageBox.information(self, "موفق", "✅ تنظیمات بازنشانی شد!")
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
