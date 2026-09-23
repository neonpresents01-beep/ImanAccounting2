# ui/hwid_dialog.py
# ============================================================
# دیالوگ نمایش HWID — نسخه 2.0 (خوانا برای تلفن)
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from ui.base_widgets import BaseDialog


class HWIDDialog(BaseDialog):
    """دیالوگ نمایش HWID با فرمت‌های مختلف"""
    
    def __init__(self, parent=None):
        super().__init__(parent, base_width=600, base_height=560)
        
        self.setWindowTitle("🖥️ شناسه سیستم (HWID)")
        self.setModal(True)
        
        try:
            from registry_guard import get_machine_id_manager
            self.manager = get_machine_id_manager()
            self.full_hwid = self.manager.get_or_create_machine_id()
            self.short_hwid = self.manager.get_short_machine_id()
            self.formatted_hwid = self.manager.get_full_machine_id()
        except Exception as e:
            self.full_hwid = "ERROR"
            self.short_hwid = "ERROR"
            self.formatted_hwid = "ERROR"
        
        self.setup_ui()
        self._apply_widget_theme()
    
    # ============================================================
    # UI
    # ============================================================
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(15))
        layout.setContentsMargins(self.margin(25), self.margin(25),
                                  self.margin(25), self.margin(25))
        
        # ===== هدر =====
        header = QHBoxLayout()
        
        icon = QLabel("🖥️")
        icon.setStyleSheet("font-size: 32pt; background: transparent;")
        header.addWidget(icon)
        
        title_layout = QVBoxLayout()
        title = QLabel("شناسه سیستم (HWID)")
        title.setObjectName("titleLabel")
        title_layout.addWidget(title)
        
        subtitle = QLabel("این کد را برای دریافت لایسنس به فروشنده ارسال کنید")
        subtitle.setObjectName("subtitleLabel")
        title_layout.addWidget(subtitle)
        
        header.addLayout(title_layout)
        header.addStretch()
        
        layout.addLayout(header)
        
        # ===== توضیحات =====
        info = QLabel(
            "🔑 هر سیستم دارای یک شناسه منحصربه‌فرد است.\n"
            "برای دریافت لایسنس، این کد را کپی کرده و برای پشتیبانی ارسال کنید."
        )
        info.setWordWrap(True)
        info.setObjectName("infoText")
        layout.addWidget(info)
        
        # ===== HWID کوتاه (برای تلفن) =====
        layout.addWidget(self._create_section_title(
            "📞 کد کوتاه (برای تماس تلفنی)"
        ))
        
        short_layout = QHBoxLayout()
        
        self.short_display = QLineEdit(self.short_hwid)
        self.short_display.setAlignment(Qt.AlignCenter)
        self.short_display.setReadOnly(True)
        self.short_display.setObjectName("shortHwidInput")
        short_layout.addWidget(self.short_display, 1)
        
        copy_short_btn = QPushButton("📋 کپی")
        copy_short_btn.setObjectName("infoBtn")
        copy_short_btn.setFixedWidth(90)
        copy_short_btn.clicked.connect(
            lambda: self._copy_to_clipboard(self.short_hwid, copy_short_btn)
        )
        short_layout.addWidget(copy_short_btn)
        
        layout.addLayout(short_layout)
        
        # ===== HWID کامل (برای ایمیل) =====
        layout.addWidget(self._create_section_title(
            "📧 کد کامل (برای ایمیل/پشتیبانی آنلاین)"
        ))
        
        full_layout = QHBoxLayout()
        
        self.full_display = QLineEdit(self.formatted_hwid)
        self.full_display.setAlignment(Qt.AlignCenter)
        self.full_display.setReadOnly(True)
        self.full_display.setObjectName("fullHwidInput")
        full_layout.addWidget(self.full_display, 1)
        
        copy_full_btn = QPushButton("📋 کپی")
        copy_full_btn.setObjectName("infoBtn")
        copy_full_btn.setFixedWidth(90)
        copy_full_btn.clicked.connect(
            lambda: self._copy_to_clipboard(self.full_hwid, copy_full_btn)
        )
        full_layout.addWidget(copy_full_btn)
        
        layout.addLayout(full_layout)
        
        layout.addSpacing(10)
        
        # ===== راهنما =====
        help_text = QLabel(
            "💡 <b>راهنما:</b>\n"
            "• برای تماس تلفنی: فقط <b>کد کوتاه</b> کافی است\n"
            "• برای ایمیل: <b>کد کامل</b> را ارسال کنید\n"
            "• پس از دریافت لایسنس، آن را در پنجره فعال‌سازی وارد کنید"
        )
        help_text.setWordWrap(True)
        help_text.setObjectName("helpText")
        layout.addWidget(help_text)
        
        layout.addStretch()
        
        # ===== دکمه بستن =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("❌ بستن")
        close_btn.setObjectName("dangerBtn")
        close_btn.setMinimumWidth(120)
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _create_section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label
    
    # ============================================================
    # Copy
    # ============================================================
    
    def _copy_to_clipboard(self, text: str, button: QPushButton):
        try:
            QApplication.clipboard().setText(text)
            
            original = button.text()
            button.setText("✅ کپی شد")
            
            QTimer.singleShot(1500, lambda: button.setText(original))
        except Exception:
            pass
    
    # ============================================================
    # Theme
    # ============================================================
    
    def _apply_widget_theme(self):
        try:
            c = self.get_theme_colors()
            
            # خود دیالوگ
            self.setStyleSheet(f"""
                QDialog {{
                    background: {c['bg']};
                }}
            """)
            
            # titleLabel
            for lbl in self.findChildren(QLabel):
                obj = lbl.objectName()
                
                if obj == 'titleLabel':
                    lbl.setStyleSheet(f"""
                        color: {c['selected']};
                        font-size: 18pt;
                        font-weight: bold;
                        background: transparent;
                    """)
                elif obj == 'subtitleLabel':
                    lbl.setStyleSheet(f"""
                        color: {c['text_secondary']};
                        font-size: 10pt;
                        background: transparent;
                    """)
                elif obj == 'sectionTitle':
                    lbl.setStyleSheet(f"""
                        color: {c['text']};
                        font-size: 11pt;
                        font-weight: bold;
                        padding: 5px 0;
                        background: transparent;
                    """)
                elif obj == 'infoText':
                    lbl.setStyleSheet(f"""
                        color: {c['text']};
                        font-size: 10pt;
                        padding: 10px;
                        background: {c['card']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                    """)
                elif obj == 'helpText':
                    lbl.setStyleSheet(f"""
                        color: {c['text_secondary']};
                        font-size: 9pt;
                        padding: 10px;
                        background: {c['bg_alt']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                    """)
            
            # short_hwid_input
            if hasattr(self, 'short_display'):
                self.short_display.setStyleSheet(f"""
                    QLineEdit {{
                        background: {c['bg_alt']};
                        color: {c['success']};
                        border: 2px solid {c['success']};
                        border-radius: 8px;
                        padding: 12px;
                        font-family: 'Courier New', monospace;
                        font-size: 18pt;
                        font-weight: bold;
                        letter-spacing: 3px;
                    }}
                """)
            
            # full_hwid_input
            if hasattr(self, 'full_display'):
                self.full_display.setStyleSheet(f"""
                    QLineEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                        font-family: 'Courier New', monospace;
                        font-size: 11pt;
                    }}
                """)
            
            # دکمه‌ها
            for btn in self.findChildren(QPushButton):
                obj = btn.objectName()
                
                if obj == 'infoBtn':
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {c['info']};
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 8px;
                            font-weight: bold;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                            color: {c['text']};
                        }}
                    """)
                elif obj == 'dangerBtn':
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {c['danger']};
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 10px 20px;
                            font-weight: bold;
                            font-size: 11pt;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                            color: {c['text']};
                        }}
                    """)
        
        except Exception as e:
            print(f"⚠️ خطا در theme: {e}")
