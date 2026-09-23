# ui/ai_assistant_widget.py
# -*- coding: utf-8 -*-
# ============================================================
# دستیار هوشمند ImanAI - نسخه 10.0 (Core-Based)
# متصل به AppCore — Thread-Safe، Simple، Clean
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from ui.base_widgets import BaseWidget
from screen_utils import ScreenManager

# ✅ اتصال به هسته مرکزی
from core import get_app_core, EventType

import os
import sys
import json
import re
import traceback
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

# مسیر پروژه
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


# ============================================================
# Config
# ============================================================

API_CONFIG = {
    "base_url": "https://api.gapgpt.app/v1",
    "api_key": "sk-h2vbT01AL5eXurJrgx3iIoUq2xUwIM1Ngj9SVKGhYtksbsoE",
    "model": "gpt-4o-mini",
    "max_tokens": 500,
    "temperature": 0.7,
    "timeout": 8,
    "use_api": True
}


# ============================================================
# توابع کمکی
# ============================================================

def convert_markdown_to_html(text: str) -> str:
    """تبدیل Markdown به HTML"""
    if not text:
        return ""
    try:
        text = re.sub(r'^### (.*)$', r'<h3 style="color:#e94560;">\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*)$', r'<h3 style="color:#e94560;">\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.*)$', r'<h2 style="color:#e94560;">\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.*?)\*\*', r'<b style="color:#4CAF50;">\1</b>', text)
        text = re.sub(r'^[•\-\*] (.*)$', r'<li style="margin-bottom:5px;">\1</li>', text, flags=re.MULTILINE)
        text = text.replace('\n', '<br>')
        return text
    except Exception:
        return text


# ============================================================
# Workers
# ============================================================

class APIConnectionWorker(QObject):
    """تست اتصال API"""
    finished = pyqtSignal(bool)
    
    def __init__(self, api_manager):
        super().__init__()
        self.api_manager = api_manager
    
    @pyqtSlot()
    def run(self):
        try:
            result = self.api_manager.test_connection()
            self.finished.emit(result)
        except Exception as e:
            logger.warning(f"خطا در تست اتصال: {e}")
            self.finished.emit(False)


class AIQueryWorker(QObject):
    """پردازش سوال با استفاده از AIService مرکزی"""
    
    finished = pyqtSignal(str, str)   # (query, response)
    error = pyqtSignal(str, str)      # (query, error)
    
    def __init__(self, query: str, ai_service):
        super().__init__()
        self.query = query
        self.ai_service = ai_service
        self._is_running = True
    
    def stop(self):
        self._is_running = False
    
    @pyqtSlot()
    def run(self):
        try:
            if not self._is_running:
                return
            
            # ✅ استفاده از سرویس مرکزی
            response = self.ai_service.ask(self.query)
            
            if not self._is_running:
                return
            
            if response:
                self.finished.emit(self.query, response)
            else:
                self.error.emit(self.query, "پاسخی دریافت نشد")
        
        except Exception as e:
            logger.error(f"خطا در AIQueryWorker: {e}", exc_info=True)
            self.error.emit(self.query, str(e)[:200])


# ============================================================
# ویجت اصلی
# ============================================================

class AIAssistantWidget(BaseWidget):
    """دستیار هوشمند ImanAI - نسخه 10.0 (Core-Based)"""
    
    def __init__(self, parent=None, user_level: str = 'viewer'):
        super().__init__(parent)
        
        # ✅ مرجع هسته مرکزی
        self.core = get_app_core()
        self.ai_service = self.core.ai
        self.event_bus = self.core.event_bus
        
        # سطح دسترسی
        self._user_level = user_level
        
        # وضعیت داخلی
        self._is_processing = False
        self.worker_thread = None
        self.worker = None
        
        # API Manager
        self.api_manager = None
        
        # Speech
        self.speech = None
        
        # UI
        self._init_ui()
        self._add_welcome()
        self._update_permission()
        
        # ✅ اتصال به سیگنال‌های هسته
        self._connect_core_signals()
        
        # شروع اتصال API
        QTimer.singleShot(200, self._init_api_connection)
        
        # بارگذاری Speech
        QTimer.singleShot(800, self._load_speech)
        
        logger.info("✅ AIAssistantWidget v10.0 راه‌اندازی شد")
    
    # ============================================================
    # اتصال به سیگنال‌های هسته
    # ============================================================
    
    def _connect_core_signals(self):
        """اتصال به سیگنال‌های AppCore"""
        try:
            # سیگنال تغییر وضعیت AI
            self.event_bus.ai_status_changed.connect(self._on_ai_status_changed)
            
            # سیگنال تغییر تم
            self.event_bus.theme_changed.connect(self._on_theme_changed)
            
            # سیگنال حافظه
            self.event_bus.ai_memory_updated.connect(self._on_memory_updated)
        except Exception as e:
            logger.warning(f"خطا در اتصال سیگنال‌های هسته: {e}")
    
    def _on_ai_status_changed(self, service: str, is_connected: bool):
        """وقتی وضعیت AI عوض می‌شه"""
        if service == 'api':
            self._update_api_badge(is_connected)
    
    def _on_memory_updated(self, data: dict):
        """وقتی حافظه آپدیت می‌شه"""
        self._update_stats()
    
    def _on_theme_changed(self, theme_name: str):
        """وقتی تم عوض می‌شه"""
        self._apply_widget_theme()
    
    # ============================================================
    # راه‌اندازی API
    # ============================================================
    
    def _init_api_connection(self):
        """اتصال اولیه به API"""
        try:
            self.api_manager = APIManager()
            
            # ✅ اتصال به سرویس مرکزی
            self.ai_service.attach_api_manager(self.api_manager)
            
            # تست اتصال در پس‌زمینه
            self._test_api_connection()
        
        except Exception as e:
            logger.warning(f"خطا در راه‌اندازی API: {e}")
    
    def _test_api_connection(self):
        """تست اتصال API در ترد جداگانه"""
        try:
            self.api_thread = QThread()
            self.api_worker = APIConnectionWorker(self.api_manager)
            self.api_worker.moveToThread(self.api_thread)
            
            self.api_thread.started.connect(self.api_worker.run)
            self.api_worker.finished.connect(self._on_api_result)
            self.api_worker.finished.connect(self.api_thread.quit)
            self.api_thread.finished.connect(self.api_worker.deleteLater)
            
            self.api_thread.start()
        except Exception as e:
            logger.warning(f"خطا در تست API: {e}")
    
    def _on_api_result(self, is_connected: bool):
        """نتیجه تست API"""
        try:
            # ✅ اطلاع‌رسانی به سرویس مرکزی
            self.ai_service.update_connection_status(is_connected)
            self._update_api_badge(is_connected)
            
            if hasattr(self, 'status_label'):
                api_text = "🌐 API متصل" if is_connected else "💻 آفلاین"
                self.status_label.setText(f"✅ آماده | {api_text} | ImanAI v10.0")
        except Exception as e:
            logger.warning(f"خطا در _on_api_result: {e}")
    
    def _update_api_badge(self, is_connected: bool):
        """بروزرسانی نشان API"""
        if not hasattr(self, 'api_status_badge'):
            return
        
        try:
            color = "#4CAF50" if is_connected else "#FF9800"
            text = "🌐 API متصل" if is_connected else "💻 آفلاین"
            self.api_status_badge.setText(text)
            self.api_status_badge.setStyleSheet(
                f"background: {color}; color: white; padding: 4px 12px; "
                f"border-radius: 12px; font-size: 9pt; font-weight: bold;"
            )
        except Exception:
            pass
    
    # ============================================================
    # Speech
    # ============================================================
    
    def _load_speech(self):
        """بارگذاری دستیار صوتی"""
        try:
            from ImanAILite.speech import ImanSpeech
            self.speech = ImanSpeech()
            self.ai_service.attach_speech(self.speech)
            logger.info("✅ دستیار صوتی راه‌اندازی شد")
        except ImportError:
            self.speech = None
        except Exception as e:
            logger.warning(f"خطا در راه‌اندازی صدا: {e}")
            self.speech = None
    
    # ============================================================
    # Theme
    # ============================================================
    
    def _apply_widget_theme(self):
        """اعمال تم روی ویجت‌های خاص"""
        try:
            # چت
            if hasattr(self, 'chat_history') and self.chat_history:
                c = self.get_theme_colors()
                self.chat_history.setStyleSheet(f"""
                    QTextEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 10px;
                        padding: 15px;
                        font-size: 11pt;
                        direction: rtl;
                        text-align: right;
                    }}
                """)
            
            # QTextEditهای دیگه
            for name in ['analysis_text', 'anomaly_text', 'suggestion_result',
                         'voice_result', 'training_result']:
                widget = getattr(self, name, None)
                if widget and isinstance(widget, QTextEdit):
                    widget.setStyleSheet(self.get_textedit_stylesheet())
        except Exception as e:
            logger.warning(f"خطا در _apply_widget_theme: {e}")
    
    # ============================================================
    # Permissions
    # ============================================================
    
    def set_user_level(self, level: str):
        self._user_level = level
        self._update_permission()
    
    def _update_permission(self):
        try:
            is_admin = self._user_level == 'admin'
            is_acc = self._user_level in ['admin', 'accountant']
            can_edit = is_admin or is_acc
            can_view = self._user_level != 'viewer'
            
            if hasattr(self, 'tabs'):
                for i in range(self.tabs.count()):
                    txt = self.tabs.tabText(i)
                    if txt in ["🎓 آموزش", "⚙️ تنظیمات", "🎤 صوتی"]:
                        self.tabs.setTabEnabled(i, can_edit)
                    elif txt == "🧠 پیشنهاد حساب":
                        self.tabs.setTabEnabled(i, can_view)
        except Exception as e:
            logger.warning(f"خطا در permission: {e}")
    
    # ============================================================
    # UI
    # ============================================================
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        header = self._create_header()
        layout.addLayout(header)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { 
                background: transparent; 
                border: none; 
                border-radius: 10px; 
            }
            QTabBar::tab { 
                padding: 8px 16px; 
                margin: 2px; 
                border-radius: 8px; 
            }
            QTabBar::tab:selected { 
                background: #e94560; 
                color: white; 
            }
        """)
        
        self.tabs.addTab(self._tab_chat(), "💬 چت")
        self.tabs.addTab(self._tab_financial(), "💰 مالی")
        self.tabs.addTab(self._tab_analysis(), "📊 تحلیل")
        self.tabs.addTab(self._tab_suggestion(), "🧠 پیشنهاد حساب")
        self.tabs.addTab(self._tab_voice(), "🎤 صوتی")
        self.tabs.addTab(self._tab_training(), "🎓 آموزش")
        self.tabs.addTab(self._tab_settings(), "⚙️ تنظیمات")
        
        layout.addWidget(self.tabs)
        
        self.status_label = QLabel("⏳ در حال بارگذاری...")
        self.status_label.setStyleSheet("color: #888; padding: 5px; font-size: 9pt;")
        layout.addWidget(self.status_label)
    
    def _create_header(self):
        header = QHBoxLayout()
        header.setSpacing(10)
        
        title = QLabel("🤖 ImanAI")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #e94560;")
        header.addWidget(title)
        
        self.api_status_badge = QLabel("🌐 API")
        self.api_status_badge.setStyleSheet(
            "background: #FF9800; color: white; padding: 4px 12px; "
            "border-radius: 12px; font-size: 9pt; font-weight: bold;"
        )
        header.addWidget(self.api_status_badge)
        
        # ✅ از سرویس مرکزی
        status = self.ai_service.get_status()
        
        ai_color = "#4CAF50" if status['available'] else "#FF9800"
        ai_badge = QLabel("🧠 AI")
        ai_badge.setStyleSheet(
            f"background: {ai_color}; color: white; padding: 4px 12px; "
            f"border-radius: 12px; font-size: 9pt; font-weight: bold;"
        )
        header.addWidget(ai_badge)
        
        sp_color = "#4CAF50" if status['speech'] else "#FF9800"
        sp_badge = QLabel("🎤 صوتی")
        sp_badge.setStyleSheet(
            f"background: {sp_color}; color: white; padding: 4px 12px; "
            f"border-radius: 12px; font-size: 9pt; font-weight: bold;"
        )
        header.addWidget(sp_badge)
        
        if status['gpu']:
            gpu = QLabel("🚀 GPU")
            gpu.setStyleSheet(
                "background: #9C27B0; color: white; padding: 4px 12px; "
                "border-radius: 12px; font-size: 9pt; font-weight: bold;"
            )
            header.addWidget(gpu)
        
        header.addStretch()
        return header
    
    # ============================================================
    # تب چت
    # ============================================================
    
    def _tab_chat(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history, 1)
        
        input_layout = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("💬 سوال خود را بپرسید...")
        self.query_input.setMinimumHeight(40)
        self.query_input.returnPressed.connect(self._process_query)
        input_layout.addWidget(self.query_input)
        
        self.send_btn = QPushButton("📤")
        self.send_btn.setFixedSize(45, 45)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #e94560;
                color: white;
                border: none;
                border-radius: 22px;
                font-size: 16pt;
            }
            QPushButton:hover { background: #c62a40; }
            QPushButton:disabled { background: #555; }
        """)
        self.send_btn.clicked.connect(self._process_query)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)
        
        quick = QHBoxLayout()
        quick.setSpacing(5)
        buttons = [
            ("💰 صندوق", "موجودی صندوق"),
            ("🏦 بانک", "موجودی بانک"),
            ("📈 سود", "سود این ماه"),
            ("📊 فروش", "فروش کل"),
            ("❓ راهنما", "راهنما"),
        ]
        for text, query in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0f3460;
                    color: #eee;
                    padding: 5px 10px;
                    border-radius: 15px;
                    font-size: 9pt;
                    border: none;
                }
                QPushButton:hover { background: #1a4a7a; }
            """)
            btn.clicked.connect(lambda checked, q=query: self.query_input.setText(q))
            quick.addWidget(btn)
        quick.addStretch()
        layout.addLayout(quick)
        
        return widget
    
    # ============================================================
    # تب مالی
    # ============================================================
    
    def _tab_financial(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        g1 = QGroupBox("💰 موجودی حساب‌ها")
        gl = QGridLayout()
        gl.setSpacing(10)
        
        refresh = QPushButton("🔄 بروزرسانی")
        refresh.setStyleSheet("background: #4CAF50; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        refresh.clicked.connect(self._show_balances)
        gl.addWidget(refresh, 0, 0, 1, 2)
        
        self.cash_label = QLabel("💰 صندوق: ۰ ریال")
        self.cash_label.setStyleSheet("font-weight: bold; color: #4CAF50; padding: 5px;")
        gl.addWidget(self.cash_label, 1, 0)
        
        self.bank_label = QLabel("🏦 بانک: ۰ ریال")
        self.bank_label.setStyleSheet("font-weight: bold; color: #3498db; padding: 5px;")
        gl.addWidget(self.bank_label, 1, 1)
        
        self.total_label = QLabel("📊 مجموع: ۰ ریال")
        self.total_label.setStyleSheet("font-weight: bold; color: #e94560; font-size: 13pt; padding: 5px;")
        gl.addWidget(self.total_label, 2, 0, 1, 2)
        
        g1.setLayout(gl)
        layout.addWidget(g1)
        
        g2 = QGroupBox("📊 سود و زیان")
        gl2 = QGridLayout()
        gl2.setSpacing(10)
        
        pl_btn = QPushButton("📊 نمایش سود و زیان")
        pl_btn.setStyleSheet("background: #4CAF50; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        pl_btn.clicked.connect(self._show_profit_loss)
        gl2.addWidget(pl_btn, 0, 0, 1, 2)
        
        self.income_label = QLabel("📈 درآمد: ۰ ریال")
        self.income_label.setStyleSheet("color: #4CAF50; padding: 5px;")
        gl2.addWidget(self.income_label, 1, 0)
        
        self.expense_label = QLabel("📉 هزینه: ۰ ریال")
        self.expense_label.setStyleSheet("color: #e74c3c; padding: 5px;")
        gl2.addWidget(self.expense_label, 1, 1)
        
        self.profit_label = QLabel("💰 سود خالص: ۰ ریال")
        self.profit_label.setStyleSheet("font-weight: bold; font-size: 13pt; padding: 5px;")
        gl2.addWidget(self.profit_label, 2, 0, 1, 2)
        
        g2.setLayout(gl2)
        layout.addWidget(g2)
        
        layout.addStretch()
        return widget
    
    # ============================================================
    # تب تحلیل
    # ============================================================
    
    def _tab_analysis(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        g1 = QGroupBox("📊 تحلیل صورت‌های مالی")
        gl1 = QVBoxLayout()
        
        analyze = QPushButton("📈 تحلیل کامل")
        analyze.setStyleSheet("background: #9C27B0; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        analyze.clicked.connect(self._financial_analysis)
        gl1.addWidget(analyze)
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMinimumHeight(120)
        gl1.addWidget(self.analysis_text)
        g1.setLayout(gl1)
        layout.addWidget(g1)
        
        g2 = QGroupBox("⚠️ تشخیص ناهنجاری")
        gl2 = QVBoxLayout()
        
        anomaly = QPushButton("🔍 بررسی فاکتورهای مشکوک")
        anomaly.setStyleSheet("background: #FF9800; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        anomaly.clicked.connect(self._detect_anomalies)
        gl2.addWidget(anomaly)
        
        self.anomaly_text = QTextEdit()
        self.anomaly_text.setReadOnly(True)
        self.anomaly_text.setMinimumHeight(120)
        gl2.addWidget(self.anomaly_text)
        g2.setLayout(gl2)
        layout.addWidget(g2)
        
        layout.addStretch()
        return widget
    
    # ============================================================
    # تب پیشنهاد حساب
    # ============================================================
    
    def _tab_suggestion(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        info = QLabel("🧠 پیشنهاد حساب با هوش مصنوعی")
        info.setStyleSheet("font-size: 14pt; color: #e94560; padding: 10px;")
        layout.addWidget(info)
        
        desc = QLabel(
            "شرح سند را وارد کنید تا هوش مصنوعی حساب‌های مناسب را پیشنهاد دهد.\n"
            "مثال: 'خرید کالا از فروشنده' یا 'دریافت وجه از مشتری'"
        )
        desc.setStyleSheet("color: #888; padding: 5px 10px; font-size: 10pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        input_layout = QHBoxLayout()
        self.suggest_input = QLineEdit()
        self.suggest_input.setPlaceholderText("شرح سند را وارد کنید...")
        self.suggest_input.setMinimumHeight(38)
        self.suggest_input.returnPressed.connect(self._suggest_account)
        input_layout.addWidget(self.suggest_input)
        
        self.suggest_btn = QPushButton("🧠 پیشنهاد")
        self.suggest_btn.setStyleSheet("background: #4CAF50; color: white; padding: 10px 20px; border-radius: 6px; font-weight: bold;")
        self.suggest_btn.clicked.connect(self._suggest_account)
        input_layout.addWidget(self.suggest_btn)
        layout.addLayout(input_layout)
        
        self.suggestion_result = QTextEdit()
        self.suggestion_result.setReadOnly(True)
        self.suggestion_result.setMinimumHeight(200)
        layout.addWidget(self.suggestion_result)
        
        self.use_btn = QPushButton("📝 استفاده در سند جدید")
        self.use_btn.setStyleSheet("background: #3498db; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        self.use_btn.clicked.connect(self._use_suggestion)
        layout.addWidget(self.use_btn)
        
        return widget
    
    # ============================================================
    # تب صوتی
    # ============================================================
    
    def _tab_voice(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        info = QLabel("🎤 دستیار صوتی ImanAI")
        info.setStyleSheet("font-size: 14pt; color: #e94560; padding: 10px;")
        layout.addWidget(info)
        
        status = self.ai_service.get_status()
        if not status['speech']:
            warning = QLabel("⚠️ دستیار صوتی در دسترس نیست!\nبرای نصب: pip install pyaudio pyttsx3")
            warning.setStyleSheet("color: #e74c3c; padding: 20px;")
            warning.setAlignment(Qt.AlignCenter)
            layout.addWidget(warning)
            return widget
        
        btn_layout = QHBoxLayout()
        
        listen = QPushButton("🎤 گوش دادن")
        listen.setStyleSheet("background: #e94560; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        listen.clicked.connect(self._listen_voice)
        btn_layout.addWidget(listen)
        
        test = QPushButton("🔊 تست صدا")
        test.setStyleSheet("background: #4CAF50; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        test.clicked.connect(self._test_voice)
        btn_layout.addWidget(test)
        
        layout.addLayout(btn_layout)
        
        self.voice_result = QTextEdit()
        self.voice_result.setReadOnly(True)
        self.voice_result.setMinimumHeight(150)
        layout.addWidget(self.voice_result)
        
        return widget
    
    # ============================================================
    # تب آموزش
    # ============================================================
    
    def _tab_training(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        info = QLabel("🎓 آموزش مدل با API")
        info.setStyleSheet("font-size: 14pt; color: #e94560; padding: 10px;")
        layout.addWidget(info)
        
        g = QGroupBox("📊 آمار حافظه")
        gl = QGridLayout()
        
        self.total_conv_label = QLabel("💬 گفتگوها: ۰")
        gl.addWidget(self.total_conv_label, 0, 0)
        
        self.helpful_rate_label = QLabel("✅ نرخ مفید بودن: ۰%")
        gl.addWidget(self.helpful_rate_label, 0, 1)
        
        self.vocab_label = QLabel("📚 واژگان: ۰")
        gl.addWidget(self.vocab_label, 1, 0)
        
        g.setLayout(gl)
        layout.addWidget(g)
        
        btn_layout = QHBoxLayout()
        
        train = QPushButton("🧠 آموزش عمیق")
        train.setStyleSheet("background: #4CAF50; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        train.clicked.connect(self._deep_train)
        btn_layout.addWidget(train)
        
        clear = QPushButton("🗑️ پاک کردن حافظه")
        clear.setStyleSheet("background: #e74c3c; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        clear.clicked.connect(self._clear_memory)
        btn_layout.addWidget(clear)
        
        layout.addLayout(btn_layout)
        
        self.training_result = QTextEdit()
        self.training_result.setReadOnly(True)
        self.training_result.setMinimumHeight(180)
        layout.addWidget(self.training_result)
        
        self._update_stats()
        
        return widget
    
    # ============================================================
    # تب تنظیمات
    # ============================================================
    
    def _tab_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        info = QLabel("⚙️ تنظیمات ImanAI")
        info.setStyleSheet("font-size: 14pt; color: #e94560; padding: 10px;")
        layout.addWidget(info)
        
        g = QGroupBox("🌐 تنظیمات API")
        gl = QGridLayout()
        gl.setSpacing(10)
        
        gl.addWidget(QLabel("Base URL:"), 0, 0)
        self.api_url_input = QLineEdit(API_CONFIG["base_url"])
        gl.addWidget(self.api_url_input, 0, 1)
        
        gl.addWidget(QLabel("API Key:"), 1, 0)
        self.api_key_input = QLineEdit(API_CONFIG["api_key"])
        self.api_key_input.setEchoMode(QLineEdit.Password)
        gl.addWidget(self.api_key_input, 1, 1)
        
        gl.addWidget(QLabel("Model:"), 2, 0)
        self.model_input = QLineEdit(API_CONFIG["model"])
        gl.addWidget(self.model_input, 2, 1)
        
        test = QPushButton("🔌 تست اتصال")
        test.setStyleSheet("background: #3498db; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        test.clicked.connect(self._test_api)
        gl.addWidget(test, 3, 0, 1, 2)
        
        g.setLayout(gl)
        layout.addWidget(g)
        
        save = QPushButton("💾 ذخیره تنظیمات")
        save.setStyleSheet("background: #4CAF50; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        save.clicked.connect(self._save_settings)
        layout.addWidget(save)
        
        layout.addStretch()
        return widget
    
    # ============================================================
    # Welcome & Message
    # ============================================================
    
    def _add_welcome(self):
        status = self.ai_service.get_status()
        welcome = f"""
👋 **به ImanAI خوش آمدید!**

🧠 **نسخه:** 10.0 (Core-Based)
🌐 **API:** 🌐 در حال تست
🚀 **GPU:** {'✅ فعال' if status['gpu'] else '❌ غیرفعال'}
🎤 **دستیار صوتی:** {'✅ فعال' if status['speech'] else '❌ غیرفعال'}

✨ **قابلیت‌های من:**

💰 **مالی:** موجودی، سود، فروش
📊 **تحلیل:** صورت‌های مالی، ناهنجاری
🧠 **پیشنهاد حساب**
🎤 **دستیار صوتی**
🎓 **آموزش با API**

💡 **هرچه بیشتر استفاده کنید، باهوش‌تر می‌شوم!**
"""
        self._add_message("assistant", welcome)
    
    def _add_message(self, sender, text):
        try:
            if not hasattr(self, 'chat_history') or self.chat_history is None:
                return
            
            if len(text) > 2000:
                text = text[:2000] + "..."
            
            timestamp = datetime.now().strftime("%H:%M")
            prefix = "👤 شما" if sender == "user" else "🤖 ImanAI"
            
            c = self.get_theme_colors()
            is_dark = c['is_dark']
            
            if sender == "user":
                color = "#4CAF50"
                bg_color = "#1a3a1a" if is_dark else "#e8f5e9"
            else:
                color = "#e94560"
                bg_color = "#3a1a1a" if is_dark else "#ffebee"
            
            text_color = c['text']
            html_text = convert_markdown_to_html(text)
            
            formatted = f"""
            <div style="margin-bottom: 15px; direction: rtl; text-align: right; font-family: 'Tahoma', sans-serif;">
                <span style="color: #888; font-size: 9pt;">[{timestamp}]</span>
                <span style="background: {bg_color}; color: {color}; padding: 2px 8px; border-radius: 12px; font-weight: bold;">{prefix}</span><br>
                <span style="color: {text_color}; font-size: 11pt; margin-left: 60px;">{html_text}</span>
            </div>
            """
            
            current = self.chat_history.toHtml()
            if len(current) > 500000:
                self.chat_history.clear()
                self._add_message("assistant", "🧹 تاریخچه پاک شد")
                return
            
            self.chat_history.setHtml(current + formatted)
            scrollbar = self.chat_history.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            logger.error(f"خطا در _add_message: {e}")
    
    # ============================================================
    # پردازش — با استفاده از سرویس مرکزی
    # ============================================================
    
    def _process_query(self):
        """پردازش سوال کاربر"""
        
        if self._is_processing:
            self._add_message("assistant", "⏳ لطفاً صبر کنید...")
            return
        
        query = self.query_input.text().strip()
        if not query:
            return
        
        # ✅ پاک کردن ایمن worker قبلی — همیشه صدا بزن
        self._cleanup_worker()
        
        self._is_processing = True
        self.query_input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.query_input.setPlaceholderText("⏳ در حال پردازش...")
        
        self._add_message("user", query)
        self.query_input.clear()
        
        # اعلام busy
        self.event_bus.app_busy.emit("در حال پردازش سوال...")
        
        try:
            self.worker_thread = QThread()
            self.worker = AIQueryWorker(
                query=query,
                ai_service=self.ai_service
            )
            self.worker.moveToThread(self.worker_thread)
            
            self.worker_thread.started.connect(
                self.worker.run,
                Qt.QueuedConnection
            )
            self.worker.finished.connect(
                self._on_worker_finished,
                Qt.QueuedConnection
            )
            self.worker.error.connect(
                self._on_worker_error,
                Qt.QueuedConnection
            )
            
            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.error.connect(self.worker_thread.quit)
            
            self.worker_thread.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            
            self.worker_thread.start()
        except Exception as e:
            logger.error(f"خطا در _process_query: {e}", exc_info=True)
            self._reset_ui()
            self._cleanup_worker()
    
    def _on_worker_finished(self, query: str, response: str):
        try:
            self._add_message("assistant", response)
            
            # ✅ ذخیره در حافظه از طریق سرویس
            try:
                self.ai_service.save_conversation(query, response)
            except Exception as e:
                logger.warning(f"خطا در حافظه: {e}")
            
            self._update_stats()
        except Exception as e:
            logger.error(f"خطا در _on_worker_finished: {e}")
        finally:
            self._reset_ui()
    
    def _on_worker_error(self, query: str, error_msg: str):
        self._add_message("assistant", f"❌ {error_msg}")
        self._reset_ui()
    
    def _reset_ui(self):
        try:
            self._is_processing = False
            if hasattr(self, 'query_input') and self.query_input:
                self.query_input.setEnabled(True)
                self.query_input.setPlaceholderText("💬 سوال خود را بپرسید...")
                self.query_input.setFocus()
            if hasattr(self, 'send_btn') and self.send_btn:
                self.send_btn.setEnabled(True)
            
            # اعلام idle
            self.event_bus.app_idle.emit()
        except Exception as e:
            logger.warning(f"خطا در _reset_ui: {e}")
    
    def _cleanup_worker(self):
        """پاک کردن ایمن worker — با محافظت از آبجکت حذف‌شده"""
        try:
            # ✅ چک کن آبجکت هنوز زنده‌ست
            if self.worker is not None:
                try:
                    self.worker.stop()
                except RuntimeError:
                    # آبجکت حذف شده
                    pass
                except Exception:
                    pass
            
            if self.worker_thread is not None:
                try:
                    if self.worker_thread.isRunning():
                        self.worker_thread.quit()
                        if not self.worker_thread.wait(5000):
                            logger.warning("worker thread پاسخ نداد — force terminate")
                            self.worker_thread.terminate()
                            self.worker_thread.wait(1000)
                except RuntimeError:
                    # آبجکت حذف شده — مشکلی نیست
                    pass
            
            # ✅ همیشه None کن
            self.worker_thread = None
            self.worker = None
        except Exception as e:
            logger.warning(f"خطا در _cleanup_worker: {e}")
            self.worker_thread = None
            self.worker = None
    
    # ============================================================
    # مالی
    # ============================================================
    
    def _show_balances(self):
        try:
            from database import AccountingHelper
            cash = AccountingHelper.get_account_balance("1101")
            bank = AccountingHelper.get_account_balance("1102")
            total = cash + bank
            self.cash_label.setText(f"💰 صندوق: {cash:,.0f} ریال")
            self.bank_label.setText(f"🏦 بانک: {bank:,.0f} ریال")
            self.total_label.setText(f"📊 مجموع: {total:,.0f} ریال")
        except Exception as e:
            logger.warning(f"خطا در _show_balances: {e}")
    
    def _show_profit_loss(self):
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT COALESCE(SUM(credit - debit), 0) FROM voucher_items vi JOIN accounts a ON vi.account_code = a.code WHERE a.type = 'income'")
                income = c.fetchone()[0] or 0
                c.execute("SELECT COALESCE(SUM(debit - credit), 0) FROM voucher_items vi JOIN accounts a ON vi.account_code = a.code WHERE a.type = 'expense'")
                expense = c.fetchone()[0] or 0
            profit = income - expense
            self.income_label.setText(f"📈 درآمد: {income:,.0f} ریال")
            self.expense_label.setText(f"📉 هزینه: {expense:,.0f} ریال")
            if profit >= 0:
                self.profit_label.setText(f"💰 سود خالص: {profit:,.0f} ریال")
                self.profit_label.setStyleSheet("font-weight: bold; font-size: 13pt; color: #4CAF50; padding: 5px;")
            else:
                self.profit_label.setText(f"💰 زیان خالص: {abs(profit):,.0f} ریال")
                self.profit_label.setStyleSheet("font-weight: bold; font-size: 13pt; color: #e74c3c; padding: 5px;")
        except Exception as e:
            logger.warning(f"خطا در _show_profit_loss: {e}")
    
    # ============================================================
    # تحلیل
    # ============================================================
    
    def _financial_analysis(self):
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT COALESCE(SUM(vi.debit - vi.credit), 0) FROM voucher_items vi JOIN accounts a ON vi.account_code = a.code WHERE a.type = 'asset'")
                assets = c.fetchone()[0] or 0
                c.execute("SELECT COALESCE(SUM(vi.credit - vi.debit), 0) FROM voucher_items vi JOIN accounts a ON vi.account_code = a.code WHERE a.type = 'liability'")
                liabilities = c.fetchone()[0] or 0
                c.execute("SELECT COALESCE(SUM(vi.credit - vi.debit), 0) FROM voucher_items vi JOIN accounts a ON vi.account_code = a.code WHERE a.type = 'equity'")
                equity = c.fetchone()[0] or 0
                ratio = (liabilities / assets * 100) if assets > 0 else 0
                result = f"""
📊 تحلیل صورت‌های مالی

🏢 دارایی‌ها: {assets:,.0f} ریال
📋 بدهی‌ها: {liabilities:,.0f} ریال
💰 سرمایه: {equity:,.0f} ریال

📊 نسبت بدهی: {ratio:.1f}%

{'✅ وضعیت مناسب' if ratio < 50 else '⚠️ نیاز به بررسی'}
"""
                self.analysis_text.setText(result)
        except Exception as e:
            self.analysis_text.setText(f"⚠️ خطا: {e}")
    
    def _detect_anomalies(self):
        try:
            issues = []
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT AVG(net_amount) FROM documents WHERE doc_type = 'sales'")
                avg = c.fetchone()[0] or 0
                if avg > 0:
                    c.execute("SELECT doc_no, net_amount FROM documents WHERE doc_type = 'sales' AND net_amount > ? ORDER BY net_amount DESC LIMIT 5", [avg * 3])
                    high = c.fetchall()
                    if high:
                        for inv in high:
                            doc_no = inv['doc_no'] if hasattr(inv, 'keys') else inv[0]
                            net = inv['net_amount'] if hasattr(inv, 'keys') else inv[1]
                            issues.append(f"• {doc_no}: {net:,.0f} ریال")
            result = "⚠️ موارد مشکوک:\n\n" + "\n".join(issues) if issues else "✅ موردی یافت نشد."
            self.anomaly_text.setText(result)
        except Exception as e:
            self.anomaly_text.setText(f"⚠️ خطا: {e}")
    
    # ============================================================
    # پیشنهاد
    # ============================================================
    
    def _suggest_account(self):
        description = self.suggest_input.text().strip()
        if not description:
            QMessageBox.warning(self, "خطا", "شرح سند را وارد کنید!")
            return
        
        try:
            response = self.ai_service.ask(
                f"برای شرح سند '{description}' چه حساب‌هایی پیشنهاد می‌شود؟"
            )
            if response:
                self.suggestion_result.setHtml(f"""
<div style="font-family: Tahoma; direction: rtl;">
    <h3 style="color: #4CAF50;">🧠 پیشنهاد</h3>
    <p><b>شرح:</b> {description}</p>
    <hr>
    <p>{convert_markdown_to_html(response)}</p>
</div>
""")
                return
        except Exception as e:
            logger.warning(f"خطا در پیشنهاد: {e}")
        
        keywords = {
            "خرید": "خرید کالا",
            "فروش": "فروش",
            "حقوق": "هزینه حقوق",
            "دریافت": "صندوق",
            "پرداخت": "صندوق",
        }
        found = [f"• {v} (بر اساس '{k}')" for k, v in keywords.items() if k in description]
        
        if found:
            self.suggestion_result.setHtml(f"""
<div style="font-family: Tahoma; direction: rtl;">
    <h3 style="color: #FF9800;">💡 پیشنهاد حساب</h3>
    {''.join(f'<p>{f}</p>' for f in found)}
</div>
""")
        else:
            self.suggestion_result.setHtml("❌ هیچ حسابی پیدا نشد.")
    
    def _use_suggestion(self):
        QMessageBox.information(self, "اطلاع", "به زودی...")
    
    # ============================================================
    # صوتی
    # ============================================================
    
    def _listen_voice(self):
        if not self.speech:
            QMessageBox.warning(self, "خطا", "دستیار صوتی فعال نیست!")
            return
        try:
            self.voice_result.setText("🎤 در حال گوش دادن...")
            QApplication.processEvents()
            result = self.speech.listen_once()
            if result and len(result) >= 2:
                command = result[0]
                confidence = result[1]
                if command:
                    self.voice_result.setText(f"✅ {command} (اطمینان: {confidence:.2f})")
                else:
                    self.voice_result.setText("❌ شناسایی نشد.")
            else:
                self.voice_result.setText("❌ شناسایی نشد.")
        except Exception as e:
            self.voice_result.setText(f"❌ خطا: {e}")
    
    def _test_voice(self):
        if not self.speech:
            return
        try:
            self.speech.speak("سلام! من ImanAI هستم.")
            self.voice_result.setText("🔊 تست انجام شد.")
        except Exception as e:
            self.voice_result.setText(f"❌ خطا: {e}")
    
    # ============================================================
    # آموزش
    # ============================================================
    
    def _update_stats(self):
        try:
            stats = self.ai_service.get_memory_stats()
            if hasattr(self, 'total_conv_label') and self.total_conv_label:
                self.total_conv_label.setText(f"💬 گفتگوها: {stats['total']}")
            if hasattr(self, 'helpful_rate_label') and self.helpful_rate_label:
                self.helpful_rate_label.setText(f"✅ نرخ مفید: {stats['helpful_rate']:.1f}%")
            if hasattr(self, 'vocab_label') and self.vocab_label:
                self.vocab_label.setText(f"📚 واژگان: {stats['vocab_size']}")
        except Exception:
            pass
    
    def _deep_train(self):
        self.training_result.clear()
        self.training_result.append("🧠 شروع آموزش...")
        
        if not self.ai_service.get_status()['connected']:
            self.training_result.append("❌ API در دسترس نیست!")
            return
        
        memory = self.ai_service._memory
        if not memory:
            self.training_result.append("❌ حافظه در دسترس نیست!")
            return
        
        recent = list(memory.conversations)[-50:]
        if len(recent) < 10:
            self.training_result.append("⚠️ حداقل ۱۰ گفتگو نیاز است")
            return
        
        if self.api_manager:
            data = [{
                "query": c['query'],
                "response": c['response'],
                "intent": c['intent'],
                "feedback_score": 3
            } for c in recent]
            
            result = self.api_manager.train_model(data)
            
            if result.get("status") == "success":
                self.training_result.append("✅ آموزش انجام شد!")
                self.training_result.append(result.get('suggestions', ''))
                memory.save()
                self._update_stats()
            else:
                self.training_result.append(f"❌ {result.get('message')}")
    
    def _clear_memory(self):
        reply = QMessageBox.question(self, "تأیید", "حافظه پاک شود؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            memory = self.ai_service._memory
            if memory:
                memory.clear()
                memory.save()
                self._update_stats()
                self.training_result.clear()
                self.training_result.append("🗑️ حافظه پاک شد!")
    
    # ============================================================
    # تنظیمات
    # ============================================================
    
    def _test_api(self):
        try:
            url = self.api_url_input.text().strip()
            key = self.api_key_input.text().strip()
            model = self.model_input.text().strip()
            
            response = requests.post(
                f"{url}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
                timeout=5
            )
            
            if response.status_code == 200:
                QMessageBox.information(self, "موفق", "✅ اتصال برقرار شد!")
                
                if self.api_manager:
                    self.api_manager.is_connected = True
                    self.api_manager.base_url = url
                    self.api_manager.api_key = key
                    self.api_manager.model = model
                
                self.ai_service.update_connection_status(True)
                self._update_api_badge(True)
            else:
                QMessageBox.warning(self, "خطا", f"❌ {response.status_code}")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {e}")
    
    def _save_settings(self):
        if self.api_manager:
            self.api_manager.base_url = self.api_url_input.text().strip()
            self.api_manager.api_key = self.api_key_input.text().strip()
            self.api_manager.model = self.model_input.text().strip()
        QMessageBox.information(self, "موفق", "✅ ذخیره شد!")
    
    # ============================================================
    # Close
    # ============================================================
    
    def closeEvent(self, event):
        """بستن ایمن"""
        try:
            self._cleanup_worker()
            
            # قطع از سیگنال‌های هسته
            try:
                self.event_bus.ai_status_changed.disconnect(self._on_ai_status_changed)
                self.event_bus.theme_changed.disconnect(self._on_theme_changed)
                self.event_bus.ai_memory_updated.disconnect(self._on_memory_updated)
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"خطا در closeEvent: {e}")
        
        try:
            super().closeEvent(event)
        except Exception:
            event.accept()


# ============================================================
# APIManager — کپی شده از فایل اصلی
# ============================================================

class APIManager:
    """مدیریت API GapGPT"""
    
    def __init__(self, config=None):
        cfg = config or API_CONFIG
        self.base_url = cfg["base_url"]
        self.api_key = cfg["api_key"]
        self.model = cfg["model"]
        self.max_tokens = cfg["max_tokens"]
        self.temperature = cfg["temperature"]
        self.timeout = cfg["timeout"]
        self.use_api = cfg["use_api"]
        self.is_connected = False
    
    def test_connection(self) -> bool:
        if not self.use_api:
            return False
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5
                },
                timeout=5
            )
            self.is_connected = (response.status_code == 200)
            return self.is_connected
        except Exception as e:
            logger.warning(f"API در دسترس نیست: {e}")
            self.is_connected = False
            return False
    
    def chat_completion(self, messages, **kwargs):
        if not self.use_api or not self.is_connected:
            return None
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": messages,
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature)
                },
                timeout=kwargs.get("timeout", self.timeout)
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            return None
        except requests.exceptions.Timeout:
            logger.warning("API timeout")
            return None
        except Exception as e:
            logger.warning(f"API خطا: {e}")
            return None
    
    def generate_response(self, query: str):
        messages = [
            {"role": "system", "content": "تو دستیار هوشمند حسابداری ImanAI هستی. پاسخ‌ها رو به فارسی روان بده."},
            {"role": "user", "content": query}
        ]
        return self.chat_completion(messages)
    
    def train_model(self, training_data: list) -> dict:
        if not self.use_api or not self.is_connected:
            return {"status": "error", "message": "API در دسترس نیست"}
        try:
            examples = [
                {
                    "instruction": item.get("query", "")[:200],
                    "output": item.get("response", "")[:200],
                    "intent": item.get("intent", "unknown"),
                    "score": item.get("feedback_score", 3)
                }
                for item in training_data
            ]
            result = self.chat_completion([
                {"role": "system", "content": "تو سیستم آموزش هوش مصنوعی حسابداری هستی."},
                {"role": "user", "content": f"داده‌های آموزشی:\n{json.dumps(examples, ensure_ascii=False, indent=2)}\nالگوهای جدید استخراج کن."}
            ], max_tokens=800)
            if result:
                return {
                    "status": "success",
                    "message": "✅ آموزش انجام شد",
                    "suggestions": result,
                    "samples": len(examples)
                }
            return {"status": "error", "message": "خطا در آموزش"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
