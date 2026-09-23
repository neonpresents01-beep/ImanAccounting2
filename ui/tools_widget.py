# ui/tools_widget.py
# ============================================================
# ویجت ابزارها — نسخه 2.0 (Core-Integrated)
# ============================================================

import os
from datetime import datetime

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from ui.base_widgets import BaseWidget
from shamsi_date import get_today_jalali


class ToolsWidget(BaseWidget):
    """ویجت ابزارهای کمکی"""
    
    def __init__(self, parent=None, user_level: str = 'viewer'):
        super().__init__(parent)
        self.user_level = user_level
        self._reports_loaded = False
        
        self.setup_ui()
        self.update_ui_by_permission()
        
        # ✅ اعمال تم
        self._apply_widget_theme()
    
    def set_user_level(self, level: str):
        self.user_level = level
        self.update_ui_by_permission()
    
    def update_ui_by_permission(self):
        """بروزرسانی UI بر اساس سطح دسترسی"""
        is_admin = self.user_level == 'admin'
        is_accountant = self.user_level in ['admin', 'accountant']
        
        for i in range(self.tabs.count()):
            tab_text = self.tabs.tabText(i)
            if tab_text == "💻 اطلاعات سیستم":
                self.tabs.setTabEnabled(i, is_admin)
            elif tab_text == "📊 گزارشات":
                self.tabs.setTabEnabled(i, is_accountant)
    
    # ============================================================
    # Theme
    # ============================================================
    
    def _apply_widget_theme(self):
        """اعمال تم روی ویجت"""
        try:
            c = self.get_theme_colors()
            
            # جداول
            for table in self.findChildren(QTableWidget):
                table.setStyleSheet(self.get_table_stylesheet())
            
            # QTextEdit
            for te in self.findChildren(QTextEdit):
                te.setStyleSheet(self.get_textedit_stylesheet())
            
            # QGroupBox
            for gb in self.findChildren(QGroupBox):
                gb.setStyleSheet(self.get_group_stylesheet())
            
            # لیبل‌های اطلاعاتی
            if hasattr(self, 'info_label'):
                self.info_label.setStyleSheet(
                    f"color: {c['text_secondary']}; font-size: 9pt; padding: 5px;"
                )
        except Exception as e:
            print(f"⚠️ خطا در _apply_widget_theme: {e}")
    
    # ============================================================
    # UI
    # ============================================================
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(self.margin(10), self.margin(10),
                                  self.margin(10), self.margin(10))
        layout.setSpacing(self.spacing(10))
        
        title = QLabel("🛠️ ابزارها")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        self.tabs.addTab(self._create_reports_tab(), "📊 گزارشات")
        self.tabs.addTab(self._create_calculator_tab(), "🧮 ماشین حساب")
        self.tabs.addTab(self._create_notepad_tab(), "📝 یادداشت")
        self.tabs.addTab(self._create_system_tab(), "💻 اطلاعات سیستم")
        
        layout.addWidget(self.tabs)
    
    # ============================================================
    # تب گزارشات
    # ============================================================
    
    def _create_reports_tab(self):
        """تب گزارشات (Lazy Load)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.reports_placeholder = QLabel(
            "📊 گزارشات جامع حسابداری\n\n"
            "لطفاً صبر کنید...\n"
            "گزارشات در حال بارگذاری هستند"
        )
        self.reports_placeholder.setAlignment(Qt.AlignCenter)
        self.reports_placeholder.setStyleSheet(
            "color: #888; font-size: 14pt; padding: 50px;"
        )
        layout.addWidget(self.reports_placeholder)
        
        return widget
    
    def _on_tab_changed(self, index):
        """Load reports lazily"""
        tab_text = self.tabs.tabText(index)
        
        if tab_text == "📊 گزارشات" and not self._reports_loaded:
            self._reports_loaded = True
            QTimer.singleShot(100, self._load_reports)
    
    def _load_reports(self):
        """بارگذاری ReportsWidget"""
        try:
            from ui.reports_widget import ReportsWidget
            
            # پیدا کردن index
            index = -1
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == "📊 گزارشات":
                    index = i
                    break
            
            if index == -1:
                return
            
            # ساخت ویجت
            reports_widget = ReportsWidget()
            
            # جایگزینی
            old_widget = self.tabs.widget(index)
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, reports_widget, "📊 گزارشات")
            self.tabs.setCurrentIndex(index)
            
            if old_widget:
                old_widget.deleteLater()
            
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری گزارشات: {e}")
            if hasattr(self, 'reports_placeholder'):
                self.reports_placeholder.setText(
                    f"❌ خطا در بارگذاری گزارشات\n\n{str(e)[:200]}"
                )
                self.reports_placeholder.setStyleSheet(
                    "color: #e74c3c; font-size: 12pt; padding: 50px;"
                )
    
    # ============================================================
    # تب ماشین حساب
    # ============================================================
    
    def _create_calculator_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(self.margin(15), self.margin(15),
                                  self.margin(15), self.margin(15))
        layout.setSpacing(self.spacing(10))
        
        self.calc_display = QLineEdit()
        self.calc_display.setReadOnly(True)
        self.calc_display.setAlignment(Qt.AlignRight)
        self.calc_display.setStyleSheet("""
            QLineEdit {
                font-size: 20pt;
                font-weight: bold;
                padding: 15px;
                border: 2px solid #1976D2;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.calc_display)
        
        buttons = [
            ['7', '8', '9', '/'],
            ['4', '5', '6', '*'],
            ['1', '2', '3', '-'],
            ['0', '.', '=', '+'],
            ['C', '⌫', '', '']
        ]
        
        grid = QGridLayout()
        grid.setSpacing(self.spacing(5))
        
        for row_idx, row in enumerate(buttons):
            for col_idx, btn_text in enumerate(row):
                if btn_text:
                    btn = QPushButton(btn_text)
                    btn.setFixedHeight(self.scaled(50))
                    btn.setStyleSheet("""
                        QPushButton {
                            font-size: 14pt;
                            font-weight: bold;
                            border-radius: 6px;
                        }
                    """)
                    if btn_text == '=':
                        btn.setObjectName("successBtn")
                    btn.clicked.connect(
                        lambda checked, t=btn_text: self._calc_button_clicked(t)
                    )
                    grid.addWidget(btn, row_idx, col_idx)
        
        layout.addLayout(grid)
        return widget
    
    def _calc_button_clicked(self, text):
        current = self.calc_display.text()
        if text == 'C':
            self.calc_display.clear()
        elif text == '⌫':
            self.calc_display.setText(current[:-1])
        elif text == '=':
            try:
                result = eval(current)
                self.calc_display.setText(str(result))
            except Exception:
                self.calc_display.setText("خطا")
        else:
            self.calc_display.setText(current + text)
    
    # ============================================================
    # تب یادداشت
    # ============================================================
    
    def _create_notepad_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(self.margin(15), self.margin(15),
                                  self.margin(15), self.margin(15))
        layout.setSpacing(self.spacing(10))
        
        title = QLabel("📝 یادداشت سریع")
        title.setObjectName("subtitleLabel")
        layout.addWidget(title)
        
        self.notepad_text = QTextEdit()
        self.notepad_text.setPlaceholderText("یادداشت خود را بنویسید...")
        layout.addWidget(self.notepad_text)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = self.create_button("💾 ذخیره", "successBtn")
        save_btn.clicked.connect(self._save_notepad)
        btn_layout.addWidget(save_btn)
        
        clear_btn = self.create_button("🗑️ پاک کردن", "dangerBtn")
        clear_btn.clicked.connect(self.notepad_text.clear)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
        
        self._load_notepad()
        return widget
    
    def _save_notepad(self):
        try:
            path = os.path.join(os.path.expanduser("~"), "imanaccount_notepad.txt")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.notepad_text.toPlainText())
            
            # ✅ اطلاع‌رسانی از طریق core
            self.notify("یادداشت ذخیره شد", "success")
            QMessageBox.information(self, "موفق", "✅ یادداشت ذخیره شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def _load_notepad(self):
        try:
            path = os.path.join(os.path.expanduser("~"), "imanaccount_notepad.txt")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.notepad_text.setPlainText(f.read())
        except Exception:
            pass
    
    # ============================================================
    # تب اطلاعات سیستم
    # ============================================================
    
    def _create_system_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(self.margin(15), self.margin(15),
                                  self.margin(15), self.margin(15))
        layout.setSpacing(self.spacing(10))
        
        title = QLabel("💻 اطلاعات سیستم")
        title.setObjectName("subtitleLabel")
        layout.addWidget(title)
        
        self.sys_info_text = QTextEdit()
        self.sys_info_text.setReadOnly(True)
        layout.addWidget(self.sys_info_text)
        
        refresh_btn = self.create_button("🔄 به‌روزرسانی", "infoBtn")
        refresh_btn.clicked.connect(self._refresh_system_info)
        layout.addWidget(refresh_btn)
        
        self.info_label = QLabel(f"📅 تاریخ امروز: {get_today_jalali()}")
        layout.addWidget(self.info_label)
        
        self._refresh_system_info()
        return widget
    
    def _refresh_system_info(self):
        try:
            import platform
            info = f"""
            <h3>💻 اطلاعات سیستم</h3>
            <table width='100%' style='font-size: 10pt;'>
                <tr><td><b>نام سیستم:</b></td><td>{platform.node()}</td></tr>
                <tr><td><b>سیستم عامل:</b></td><td>{platform.system()} {platform.release()}</td></tr>
                <tr><td><b>معماری:</b></td><td>{platform.machine()}</td></tr>
                <tr><td><b>پردازنده:</b></td><td>{platform.processor() or 'نامشخص'}</td></tr>
                <tr><td><b>نسخه پایتون:</b></td><td>{platform.python_version()}</td></tr>
                <tr><td><b>نام کاربر:</b></td><td>{os.environ.get('USERNAME', 'نامشخص')}</td></tr>
                <tr><td><b>تاریخ میلادی:</b></td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                <tr><td><b>تاریخ شمسی:</b></td><td>{get_today_jalali()}</td></tr>
            </table>
            """
            self.sys_info_text.setHtml(info)
        except Exception as e:
            self.sys_info_text.setPlainText(f"خطا: {str(e)}")
