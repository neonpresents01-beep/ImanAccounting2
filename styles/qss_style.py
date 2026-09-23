# styles/qss_style.py
# -*- coding: utf-8 -*-

"""
استایل‌های حرفه‌ای برای ImanAccount
تم مدرن و مناسب برای نرم‌افزار حسابداری
"""

import os
from PyQt5.QtCore import QFile, QTextStream


def get_professional_style(dark_mode=False):
    """
    دریافت استایل حرفه‌ای
    
    Args:
        dark_mode: حالت تاریک (False = روشن)
    
    Returns:
        str: کد QSS کامل
    """
    
    if dark_mode:
        return _get_dark_style()
    else:
        return _get_light_style()


def load_qss_from_file(file_path):
    """بارگذاری استایل از فایل QSS"""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def _get_light_style():
    """استایل روشن و حرفه‌ای - کامل برای کل برنامه"""
    return """
    /* ============================================================
       استایل کامل ImanAccount - نسخه حرفه‌ای
       تم: روشن و مدرن
       قابل اعمال در کل برنامه و همه تب‌ها
       ============================================================ */
    
    /* ============================================================
       1. پنجره اصلی و پس‌زمینه
       ============================================================ */
    
    QMainWindow, QDialog, QWidget {
        background-color: #f0f2f5;
        font-family: 'Segoe UI', 'Tahoma', 'Vazir', sans-serif;
        font-size: 10pt;
        color: #2c3e50;
    }
    
    QWidget#centralWidget {
        background-color: #f0f2f5;
    }
    
    /* ============================================================
       2. هدر
       ============================================================ */
    
    QWidget#headerWidget {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #1a237e, stop:0.5 #283593, stop:1 #3949ab);
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
        min-height: 60px;
    }
    
    QLabel#headerTitle {
        font-size: 18pt;
        font-weight: bold;
        color: white;
        background: transparent;
    }
    
    QLabel#headerSubtitle {
        font-size: 10pt;
        color: #b3c6e7;
        background: transparent;
    }
    
    QLabel#headerDate {
        font-size: 11pt;
        font-weight: bold;
        color: #1a237e;
        background-color: white;
        padding: 6px 16px;
        border-radius: 20px;
    }
    
    QLabel#headerDays {
        font-size: 10pt;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: bold;
        color: white;
    }
    
    QLabel#headerKeyStatus {
        font-size: 14px;
        background: transparent;
    }
    
    /* ============================================================
       3. تب‌ها (TabWidget)
       ============================================================ */
    
    QTabWidget::pane {
        border: 1px solid #d0d3d9;
        border-radius: 10px;
        background-color: white;
        margin-top: -1px;
        padding: 4px;
    }
    
    QTabBar::tab {
        background-color: #e8eaed;
        color: #5f6368;
        padding: 10px 24px;
        margin-right: 3px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: 600;
        font-size: 10.5pt;
        border: none;
        min-width: 80px;
    }
    
    QTabBar::tab:selected {
        background-color: white;
        color: #1a237e;
        border-bottom: 3px solid #1a237e;
    }
    
    QTabBar::tab:hover:!selected {
        background-color: #dde1e6;
    }
    
    QTabBar::tab:disabled {
        color: #b0bec5;
    }
    
    /* تب‌های داخلی (ثانویه) */
    QTabWidget#innerTabs::pane {
        border: none;
        background-color: transparent;
        padding: 0;
    }
    
    QTabWidget#innerTabs QTabBar::tab {
        background-color: #f0f2f5;
        padding: 6px 16px;
        font-size: 9pt;
        border-radius: 4px;
        margin-right: 2px;
        min-width: 60px;
    }
    
    QTabWidget#innerTabs QTabBar::tab:selected {
        background-color: #3949ab;
        color: white;
    }
    
    /* ============================================================
       4. دکمه‌ها (همه انواع)
       ============================================================ */
    
    QPushButton {
        background-color: #3949ab;
        color: white;
        border: none;
        padding: 8px 18px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 10pt;
        min-height: 32px;
        min-width: 60px;
    }
    
    QPushButton:hover {
        background-color: #1a237e;
    }
    
    QPushButton:pressed {
        background-color: #0d1442;
    }
    
    QPushButton:disabled {
        background-color: #b0bec5;
        color: #78909c;
    }
    
    /* دکمه موفقیت (سبز) */
    QPushButton#successBtn, QPushButton[objectName="successBtn"] {
        background-color: #43a047;
    }
    QPushButton#successBtn:hover, QPushButton[objectName="successBtn"]:hover {
        background-color: #2e7d32;
    }
    
    /* دکمه حذف (قرمز) */
    QPushButton#dangerBtn, QPushButton[objectName="dangerBtn"],
    QPushButton#deleteBtn, QPushButton[objectName="deleteBtn"] {
        background-color: #e53935;
    }
    QPushButton#dangerBtn:hover, QPushButton[objectName="dangerBtn"]:hover,
    QPushButton#deleteBtn:hover, QPushButton[objectName="deleteBtn"]:hover {
        background-color: #c62828;
    }
    
    /* دکمه هشدار (نارنجی) */
    QPushButton#warningBtn, QPushButton[objectName="warningBtn"],
    QPushButton#editBtn, QPushButton[objectName="editBtn"] {
        background-color: #fb8c00;
    }
    QPushButton#warningBtn:hover, QPushButton[objectName="warningBtn"]:hover,
    QPushButton#editBtn:hover, QPushButton[objectName="editBtn"]:hover {
        background-color: #e65100;
    }
    
    /* دکمه اطلاعات (آبی) */
    QPushButton#infoBtn, QPushButton[objectName="infoBtn"] {
        background-color: #1e88e5;
    }
    QPushButton#infoBtn:hover, QPushButton[objectName="infoBtn"]:hover {
        background-color: #0d47a1;
    }
    
    /* دکمه AI (صورتی) */
    QPushButton#aiBtn, QPushButton[objectName="aiBtn"] {
        background-color: #e94560;
    }
    QPushButton#aiBtn:hover, QPushButton[objectName="aiBtn"]:hover {
        background-color: #c62a40;
    }
    
    /* دکمه بنفش */
    QPushButton#purpleBtn, QPushButton[objectName="purpleBtn"] {
        background-color: #7c4dff;
    }
    QPushButton#purpleBtn:hover, QPushButton[objectName="purpleBtn"]:hover {
        background-color: #536dfe;
    }
    
    /* دکمه پیش‌فرض (برای دیالوگ‌ها) */
    QDialogButtonBox QPushButton {
        min-width: 80px;
        padding: 8px 20px;
    }
    
    /* ============================================================
       5. جدول‌ها (همه انواع)
       ============================================================ */
    
    QTableWidget, QTableView {
        background-color: white;
        border: 1px solid #d0d3d9;
        border-radius: 8px;
        gridline-color: #e8eaed;
        selection-background-color: #e3f2fd;
        selection-color: #1a237e;
        alternate-background-color: #f8f9fa;
        padding: 4px;
    }
    
    QTableWidget::item, QTableView::item {
        padding: 6px 10px;
    }
    
    QTableWidget::item:selected, QTableView::item:selected {
        background-color: #e3f2fd;
        color: #1a237e;
    }
    
    QTableWidget::item:hover, QTableView::item:hover {
        background-color: #f5f5f5;
    }
    
    QHeaderView::section {
        background-color: #1a237e;
        color: white;
        padding: 8px 14px;
        border: none;
        font-weight: 600;
        font-size: 9.5pt;
    }
    
    QHeaderView::section:hover {
        background-color: #0d1442;
    }
    
    /* ============================================================
       6. ورودی‌ها
       ============================================================ */
    
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit,
    QDateTimeEdit, QTimeEdit {
        background-color: white;
        border: 1.5px solid #d0d3d9;
        border-radius: 6px;
        padding: 7px 12px;
        font-size: 10pt;
        color: #2c3e50;
        selection-background-color: #1a237e;
        selection-color: white;
        min-height: 20px;
    }
    
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, 
    QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QTimeEdit:focus {
        border-color: #3949ab;
        box-shadow: 0 0 0 3px rgba(57, 73, 171, 0.15);
    }
    
    QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
        background-color: #f5f5f5;
        color: #9e9e9e;
    }
    
    QLineEdit::placeholder {
        color: #b0bec5;
        font-style: italic;
    }
    
    /* ============================================================
       7. کامبوباکس
       ============================================================ */
    
    QComboBox::drop-down {
        border: none;
        width: 30px;
    }
    
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #5f6368;
        margin-right: 8px;
    }
    
    QComboBox QAbstractItemView {
        background-color: white;
        border: 1px solid #d0d3d9;
        border-radius: 6px;
        padding: 4px;
        selection-background-color: #e3f2fd;
        selection-color: #1a237e;
    }
    
    QComboBox QAbstractItemView::item {
        padding: 6px 12px;
        border-radius: 4px;
    }
    
    QComboBox QAbstractItemView::item:hover {
        background-color: #f0f2f5;
    }
    
    /* ============================================================
       8. گروه‌باکس
       ============================================================ */
    
    QGroupBox {
        font-weight: 600;
        border: 2px solid #d0d3d9;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 10px;
        background-color: white;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 12px;
        color: #1a237e;
        font-size: 11pt;
    }
    
    /* ============================================================
       9. لیبل‌ها
       ============================================================ */
    
    QLabel {
        color: #2c3e50;
        background: transparent;
    }
    
    QLabel#titleLabel {
        font-size: 16pt;
        font-weight: bold;
        color: #1a237e;
        padding: 10px;
    }
    
    QLabel#subtitleLabel {
        font-size: 12pt;
        color: #5f6368;
        padding: 5px;
    }
    
    QLabel#infoLabel {
        color: #5f6368;
        font-size: 9pt;
        padding: 5px;
        background-color: #f8f9fa;
        border-radius: 4px;
    }
    
    QLabel#successLabel {
        color: #43a047;
        font-weight: bold;
    }
    
    QLabel#warningLabel {
        color: #fb8c00;
        font-weight: bold;
    }
    
    QLabel#dangerLabel {
        color: #e53935;
        font-weight: bold;
    }
    
    /* ============================================================
       10. اسکرول بار
       ============================================================ */
    
    QScrollBar:vertical {
        background-color: #f0f2f5;
        width: 10px;
        border-radius: 5px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #b0bec5;
        border-radius: 5px;
        min-height: 30px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #78909c;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    
    QScrollBar:horizontal {
        background-color: #f0f2f5;
        height: 10px;
        border-radius: 5px;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #b0bec5;
        border-radius: 5px;
        min-width: 30px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #78909c;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }
    
    /* ============================================================
       11. منو بار
       ============================================================ */
    
    QMenuBar {
        background-color: white;
        border-bottom: 1px solid #d0d3d9;
        padding: 4px 0;
    }
    
    QMenuBar::item {
        padding: 6px 16px;
        background-color: transparent;
        border-radius: 4px;
        font-weight: 500;
    }
    
    QMenuBar::item:selected {
        background-color: #e3f2fd;
        color: #1a237e;
    }
    
    QMenuBar::item:pressed {
        background-color: #1a237e;
        color: white;
    }
    
    QMenu {
        background-color: white;
        border: 1px solid #d0d3d9;
        border-radius: 8px;
        padding: 4px;
    }
    
    QMenu::item {
        padding: 6px 24px 6px 12px;
        border-radius: 4px;
        font-weight: 500;
    }
    
    QMenu::item:selected {
        background-color: #e3f2fd;
        color: #1a237e;
    }
    
    QMenu::separator {
        height: 1px;
        background-color: #d0d3d9;
        margin: 4px 8px;
    }
    
    /* ============================================================
       12. استاتوس بار
       ============================================================ */
    
    QStatusBar {
        background-color: #1a237e;
        color: white;
        font-weight: 500;
        font-size: 9.5pt;
        padding: 4px 12px;
    }
    
    QStatusBar::item {
        border: none;
    }
    
    /* ============================================================
       13. پیام باکس
       ============================================================ */
    
    QMessageBox {
        background-color: white;
    }
    
    QMessageBox QPushButton {
        min-width: 80px;
        padding: 6px 16px;
    }
    
    /* ============================================================
       14. لیست ویجت
       ============================================================ */
    
    QListWidget, QListView {
        background-color: white;
        border: 1px solid #d0d3d9;
        border-radius: 6px;
        padding: 4px;
        alternate-background-color: #f8f9fa;
    }
    
    QListWidget::item, QListView::item {
        padding: 6px 10px;
        border-radius: 4px;
    }
    
    QListWidget::item:selected, QListView::item:selected {
        background-color: #e3f2fd;
        color: #1a237e;
    }
    
    QListWidget::item:hover, QListView::item:hover {
        background-color: #f5f5f5;
    }
    
    /* ============================================================
       15. تکس ادیت
       ============================================================ */
    
    QTextEdit, QPlainTextEdit {
        background-color: white;
        border: 1.5px solid #d0d3d9;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 10pt;
    }
    
    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #3949ab;
        box-shadow: 0 0 0 3px rgba(57, 73, 171, 0.15);
    }
    
    /* ============================================================
       16. چک باکس
       ============================================================ */
    
    QCheckBox {
        spacing: 8px;
        font-weight: 500;
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid #d0d3d9;
        background-color: white;
    }
    
    QCheckBox::indicator:checked {
        background-color: #3949ab;
        border-color: #3949ab;
    }
    
    QCheckBox::indicator:hover {
        border-color: #1a237e;
    }
    
    /* ============================================================
       17. رادیو باتن
       ============================================================ */
    
    QRadioButton {
        spacing: 8px;
        font-weight: 500;
    }
    
    QRadioButton::indicator {
        width: 18px;
        height: 18px;
        border-radius: 10px;
        border: 2px solid #d0d3d9;
        background-color: white;
    }
    
    QRadioButton::indicator:checked {
        background-color: #3949ab;
        border-color: #3949ab;
    }
    
    /* ============================================================
       18. اسپین باکس
       ============================================================ */
    
    QSpinBox::up-button, QDoubleSpinBox::up-button {
        background-color: #f0f2f5;
        border: none;
        border-top-right-radius: 4px;
        height: 14px;
    }
    
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        background-color: #f0f2f5;
        border: none;
        border-bottom-right-radius: 4px;
        height: 14px;
    }
    
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background-color: #d0d3d9;
    }
    
    /* ============================================================
       19. کارت‌های داشبورد
       ============================================================ */
    
    QFrame#cardFrame {
        background-color: white;
        border-radius: 12px;
        border: 1px solid #e8eaed;
        padding: 16px;
    }
    
    QFrame#cardFrame:hover {
        border-color: #3949ab;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    /* ============================================================
       20. خط جداکننده
       ============================================================ */
    
    QFrame#line {
        background-color: #d0d3d9;
        max-height: 1px;
        min-height: 1px;
    }
    
    /* ============================================================
       21. پیام‌های خطا و موفقیت
       ============================================================ */
    
    QLabel#errorLabel {
        color: #e53935;
        font-weight: bold;
        background-color: #ffebee;
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 4px solid #e53935;
    }
    
    QLabel#successMessage {
        color: #43a047;
        font-weight: bold;
        background-color: #e8f5e9;
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 4px solid #43a047;
    }
    
    /* ============================================================
       22. اسکرول Area
       ============================================================ */
    
    QScrollArea {
        border: none;
        background-color: transparent;
    }
    
    QScrollArea > QWidget > QWidget {
        background-color: transparent;
    }
    
    /* ============================================================
       23. Progress Bar
       ============================================================ */
    
    QProgressBar {
        border: none;
        border-radius: 6px;
        background-color: #f0f2f5;
        height: 12px;
        text-align: center;
        color: #1a237e;
        font-weight: bold;
    }
    
    QProgressBar::chunk {
        background-color: #3949ab;
        border-radius: 6px;
    }
    
    /* ============================================================
       24. ToolTip
       ============================================================ */
    
    QToolTip {
        background-color: #2c3e50;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 9pt;
    }
    
    /* ============================================================
       25. Calendar Widget
       ============================================================ */
    
    QCalendarWidget {
        background-color: white;
        border: 1px solid #d0d3d9;
        border-radius: 8px;
    }
    
    QCalendarWidget QWidget {
        background-color: transparent;
    }
    
    QCalendarWidget QTableView {
        border: none;
    }
    
    QCalendarWidget QHeaderView::section {
        background-color: #1a237e;
        color: white;
    }
    
    /* ============================================================
       26. Splitter
       ============================================================ */
    
    QSplitter::handle {
        background-color: #d0d3d9;
        width: 2px;
    }
    
    QSplitter::handle:hover {
        background-color: #3949ab;
    }
    
    /* ============================================================
       27. Stacked Widget
       ============================================================ */
    
    QStackedWidget {
        background-color: transparent;
    }
    
    /* ============================================================
       28. Dock Widget
       ============================================================ */
    
    QDockWidget {
        border: 1px solid #d0d3d9;
        border-radius: 8px;
        background-color: white;
        titlebar-close-icon: none;
    }
    
    QDockWidget::title {
        background-color: #1a237e;
        color: white;
        padding: 8px 12px;
        font-weight: bold;
    }
    
    QDockWidget::close-button, QDockWidget::float-button {
        background-color: transparent;
        border: none;
        icon-size: 12px;
    }
    
    /* ============================================================
       29. Tab Bar (تب‌های اضافی)
       ============================================================ */
    
    QTabBar {
        background-color: transparent;
    }
    
    QTabBar::close-button {
        subcontrol-origin: padding;
        subcontrol-position: right;
        icon-size: 12px;
    }
    
    QTabBar::close-button:hover {
        background-color: #e53935;
        border-radius: 4px;
    }
    """


def _get_dark_style():
    """استایل تاریک و حرفه‌ای - کامل برای کل برنامه"""
    return """
    /* ============================================================
       استایل کامل ImanAccount - نسخه تاریک
       تم: مدرن و چشمنواز
       ============================================================ */
    
    QMainWindow, QDialog, QWidget {
        background-color: #121212;
        font-family: 'Segoe UI', 'Tahoma', 'Vazir', sans-serif;
        font-size: 10pt;
        color: #e0e0e0;
    }
    
    QWidget#centralWidget {
        background-color: #121212;
    }
    
    /* ---------- هدر ---------- */
    QWidget#headerWidget {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0d0d2b, stop:0.5 #1a1a3e, stop:1 #2d2d5e);
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
        min-height: 60px;
    }
    
    /* ---------- تب‌ها ---------- */
    QTabWidget::pane {
        border: 1px solid #2d2d3d;
        border-radius: 10px;
        background-color: #1a1a2e;
    }
    
    QTabBar::tab {
        background-color: #1a1a2e;
        color: #888;
        padding: 10px 24px;
        margin-right: 3px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: 600;
        border: none;
    }
    
    QTabBar::tab:selected {
        background-color: #2d2d4e;
        color: #e94560;
        border-bottom: 3px solid #e94560;
    }
    
    QTabBar::tab:hover:!selected {
        background-color: #2d2d3d;
        color: #ccc;
    }
    
    /* ---------- دکمه‌ها ---------- */
    QPushButton {
        background-color: #3949ab;
        color: white;
        border: none;
        padding: 8px 18px;
        border-radius: 6px;
        font-weight: 600;
    }
    
    QPushButton:hover {
        background-color: #1a237e;
    }
    
    QPushButton:pressed {
        background-color: #0d1442;
    }
    
    QPushButton:disabled {
        background-color: #2d2d3d;
        color: #666;
    }
    
    QPushButton#successBtn {
        background-color: #43a047;
    }
    QPushButton#successBtn:hover {
        background-color: #2e7d32;
    }
    
    QPushButton#dangerBtn, QPushButton#deleteBtn {
        background-color: #e53935;
    }
    QPushButton#dangerBtn:hover, QPushButton#deleteBtn:hover {
        background-color: #c62828;
    }
    
    QPushButton#aiBtn {
        background-color: #e94560;
    }
    QPushButton#aiBtn:hover {
        background-color: #c62a40;
    }
    
    /* ---------- جدول‌ها ---------- */
    QTableWidget, QTableView {
        background-color: #1a1a2e;
        border: 1px solid #2d2d3d;
        border-radius: 8px;
        gridline-color: #2d2d3d;
        selection-background-color: #2d2d5e;
        selection-color: #e94560;
        alternate-background-color: #1f1f33;
    }
    
    QTableWidget::item:selected, QTableView::item:selected {
        background-color: #2d2d5e;
        color: #e94560;
    }
    
    QHeaderView::section {
        background-color: #0d0d1a;
        color: #e0e0e0;
        padding: 8px 12px;
        border: none;
        font-weight: 600;
    }
    
    /* ---------- ورودی‌ها ---------- */
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {
        background-color: #1a1a2e;
        border: 1.5px solid #2d2d3d;
        border-radius: 6px;
        padding: 7px 12px;
        color: #e0e0e0;
        selection-background-color: #e94560;
    }
    
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, 
    QComboBox:focus, QDateEdit:focus {
        border-color: #e94560;
        box-shadow: 0 0 0 3px rgba(233, 69, 96, 0.15);
    }
    
    QLineEdit:disabled {
        background-color: #1a1a1a;
        color: #666;
    }
    
    /* ---------- گروه‌باکس ---------- */
    QGroupBox {
        font-weight: 600;
        border: 2px solid #2d2d3d;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 10px;
        background-color: #1a1a2e;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 12px;
        color: #e94560;
        font-size: 11pt;
    }
    
    /* ---------- لیبل‌ها ---------- */
    QLabel {
        color: #e0e0e0;
    }
    
    QLabel#titleLabel {
        font-size: 16pt;
        font-weight: bold;
        color: #e94560;
        padding: 10px;
    }
    
    /* ---------- استاتوس بار ---------- */
    QStatusBar {
        background-color: #0d0d1a;
        color: #e0e0e0;
        font-weight: 500;
        padding: 4px 12px;
    }
    
    /* ---------- منو بار ---------- */
    QMenuBar {
        background-color: #0d0d1a;
        border-bottom: 1px solid #2d2d3d;
    }
    
    QMenuBar::item:selected {
        background-color: #2d2d5e;
        color: #e94560;
    }
    
    QMenu {
        background-color: #0d0d1a;
        border: 1px solid #2d2d3d;
        border-radius: 8px;
    }
    
    QMenu::item:selected {
        background-color: #2d2d5e;
        color: #e94560;
    }
    
    /* ---------- اسکرول بار ---------- */
    QScrollBar:vertical {
        background-color: #1a1a2e;
        width: 10px;
        border-radius: 5px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #2d2d4e;
        border-radius: 5px;
        min-height: 30px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #3949ab;
    }
    
    /* ---------- کامبوباکس ---------- */
    QComboBox QAbstractItemView {
        background-color: #1a1a2e;
        border: 1px solid #2d2d3d;
        border-radius: 6px;
        selection-background-color: #2d2d5e;
        selection-color: #e94560;
    }
    
    /* ---------- Progress Bar ---------- */
    QProgressBar {
        border: none;
        border-radius: 6px;
        background-color: #1a1a2e;
        height: 12px;
        text-align: center;
        color: #e94560;
        font-weight: bold;
    }
    
    QProgressBar::chunk {
        background-color: #e94560;
        border-radius: 6px;
    }
    
    /* ---------- ToolTip ---------- */
    QToolTip {
        background-color: #2d2d3d;
        color: #e0e0e0;
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
    }
    """
