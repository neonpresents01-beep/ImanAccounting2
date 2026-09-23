# ui/base_screen_widget.py
# -*- coding: utf-8 -*-

"""
کلاس پایه برای همه ویجت‌ها با پشتیبانی از screen_utils
همه ویجت‌ها باید از این کلاس ارث‌بری کنند
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from screen_utils import ScreenManager


class BaseScreenWidget(QWidget):
    """کلاس پایه برای همه ویجت‌ها با ScreenManager"""

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ========== ScreenManager ==========
        self.screen_manager = ScreenManager()
        self.scale = self.screen_manager.scale
        self.screen_width = self.screen_manager.width
        self.screen_height = self.screen_manager.height
        
        # ========== وضعیت صفحه ==========
        self.is_small = self.screen_manager.is_small_screen()
        self.is_medium = self.screen_manager.is_medium_screen()
        self.is_large = self.screen_manager.is_large_screen()
        
        # ========== اعمال استایل پایه ==========
        self._apply_base_style()
    
    def _apply_base_style(self):
        """اعمال استایل پایه با اندازه‌های داینامیک"""
        fs = self.screen_manager.get_font_size(10)
        self.setStyleSheet(f"""
            QWidget {{
                font-family: "Segoe UI", "Tahoma", sans-serif;
                font-size: {fs}pt;
            }}
        """)
    
    # ========== توابع کمکی ==========
    
    def scaled(self, value: int) -> int:
        """مقیاس‌گذاری مقدار بر اساس صفحه"""
        return self.screen_manager.get_scaled(value)
    
    def font_size(self, size: int) -> int:
        """دریافت اندازه فونت متناسب با صفحه"""
        return self.screen_manager.get_font_size(size)
    
    def spacing(self, value: int = 10) -> int:
        """دریافت فاصله متناسب با صفحه"""
        return self.screen_manager.get_spacing(value)
    
    def margin(self, value: int = 10) -> int:
        """دریافت حاشیه متناسب با صفحه"""
        return self.screen_manager.get_margin(value)
    
    def padding(self, value: int = 10) -> int:
        """دریافت padding متناسب با صفحه"""
        return self.screen_manager.get_padding(value)
    
    # ========== توابع کمکی برای ساخت ویجت‌ها ==========
    
    def create_table(self, columns: list, stretch_last: bool = True) -> QTableWidget:
        """ایجاد جدول با اندازه‌های داینامیک"""
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        
        if stretch_last:
            table.horizontalHeader().setStretchLastSection(True)
        
        row_height = self.scaled(30)
        table.verticalHeader().setDefaultSectionSize(row_height)
        
        fs = self.font_size(10)
        table.setStyleSheet(f"""
            QTableWidget {{
                font-size: {fs}pt;
                gridline-color: #dcdde1;
                border: 1px solid #dcdde1;
                border-radius: {self.scaled(8)}px;
                alternate-background-color: #f9f9f9;
            }}
            QHeaderView::section {{
                padding: {self.scaled(8)}px;
                font-weight: bold;
                font-size: {self.font_size(9)}pt;
            }}
        """)
        
        return table
    
    def create_button(self, text: str, object_name: str = "") -> QPushButton:
        """ایجاد دکمه با اندازه‌های داینامیک"""
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        
        min_height = self.scaled(32)
        fs = self.font_size(10)
        btn.setMinimumHeight(min_height)
        btn.setStyleSheet(f"""
            QPushButton {{
                padding: {self.scaled(6)}px {self.scaled(16)}px;
                font-size: {fs}pt;
                min-height: {min_height}px;
                border-radius: {self.scaled(6)}px;
                font-weight: bold;
            }}
        """)
        return btn
    
    def create_input(self, placeholder: str = "") -> QLineEdit:
        """ایجاد فیلد ورودی با اندازه‌های داینامیک"""
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        min_height = self.scaled(32)
        fs = self.font_size(10)
        inp.setMinimumHeight(min_height)
        inp.setStyleSheet(f"""
            QLineEdit {{
                padding: {self.scaled(6)}px {self.scaled(10)}px;
                font-size: {fs}pt;
                min-height: {min_height}px;
                border-radius: {self.scaled(6)}px;
                border: 1px solid #dcdde1;
            }}
            QLineEdit:focus {{
                border-color: #1976D2;
                background-color: #f3f9ff;
            }}
        """)
        return inp
    
    def create_group(self, title: str) -> QGroupBox:
        """ایجاد گروه‌بندی با اندازه‌های داینامیک"""
        group = QGroupBox(title)
        fs = self.font_size(10)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: {fs}pt;
                border: 2px solid #dcdde1;
                border-radius: {self.scaled(8)}px;
                margin-top: {self.scaled(12)}px;
                padding-top: {self.scaled(10)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {self.scaled(10)}px;
                padding: 0 {self.scaled(10)}px;
                color: #1976D2;
            }}
        """)
        return group
    
    def create_label(self, text: str, object_name: str = "") -> QLabel:
        """ایجاد لیبل با اندازه‌های داینامیک"""
        label = QLabel(text)
        if object_name:
            label.setObjectName(object_name)
        
        if object_name == "titleLabel":
            label.setStyleSheet(f"""
                font-size: {self.font_size(16)}pt;
                font-weight: bold;
                padding: {self.scaled(10)}px;
                color: #1a2332;
            """)
        elif object_name == "subtitleLabel":
            label.setStyleSheet(f"""
                font-size: {self.font_size(12)}pt;
                font-weight: bold;
                padding: {self.scaled(5)}px;
                color: #2c3e50;
            """)
        else:
            label.setStyleSheet(f"""
                font-size: {self.font_size(10)}pt;
                padding: {self.scaled(4)}px;
                color: #2c3e50;
            """)
        
        return label
    
    def create_card(self) -> QWidget:
        """ایجاد کارت با اندازه‌های داینامیک"""
        card = QWidget()
        card.setObjectName("cardWidget")
        rd = self.scaled(8)
        pd = self.scaled(10)
        card.setStyleSheet(f"""
            QWidget#cardWidget {{
                background-color: white;
                border-radius: {rd}px;
                border: 1px solid #dcdde1;
                padding: {pd}px;
            }}
        """)
        return card
    
    def create_spinbox(self, min_val: int = 0, max_val: int = 100) -> QSpinBox:
        """ایجاد SpinBox با اندازه‌های داینامیک"""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        min_height = self.scaled(32)
        fs = self.font_size(10)
        spin.setMinimumHeight(min_height)
        spin.setStyleSheet(f"""
            QSpinBox {{
                padding: {self.scaled(4)}px {self.scaled(8)}px;
                font-size: {fs}pt;
                min-height: {min_height}px;
                border-radius: {self.scaled(6)}px;
                border: 1px solid #dcdde1;
            }}
            QSpinBox:focus {{
                border-color: #1976D2;
            }}
        """)
        return spin
    
    def create_combobox(self, items: list = None) -> QComboBox:
        """ایجاد ComboBox با اندازه‌های داینامیک"""
        combo = QComboBox()
        if items:
            combo.addItems(items)
        min_height = self.scaled(32)
        fs = self.font_size(10)
        combo.setMinimumHeight(min_height)
        combo.setStyleSheet(f"""
            QComboBox {{
                padding: {self.scaled(4)}px {self.scaled(8)}px;
                font-size: {fs}pt;
                min-height: {min_height}px;
                border-radius: {self.scaled(6)}px;
                border: 1px solid #dcdde1;
            }}
            QComboBox:focus {{
                border-color: #1976D2;
            }}
            QComboBox::drop-down {{
                border: none;
                width: {self.scaled(20)}px;
            }}
        """)
        return combo
    
    def create_textedit(self, placeholder: str = "") -> QTextEdit:
        """ایجاد TextEdit با اندازه‌های داینامیک"""
        text = QTextEdit()
        text.setPlaceholderText(placeholder)
        fs = self.font_size(10)
        text.setStyleSheet(f"""
            QTextEdit {{
                padding: {self.scaled(8)}px;
                font-size: {fs}pt;
                border-radius: {self.scaled(6)}px;
                border: 1px solid #dcdde1;
                background-color: white;
            }}
            QTextEdit:focus {{
                border-color: #1976D2;
            }}
        """)
        return text
