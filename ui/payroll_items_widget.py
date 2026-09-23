#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ویجت مدیریت اقلام حقوق و دستمزد - نسخه کامل با دو تب
تب 1: 📋 مزایا
تب 2: 📉 کسورات
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from database import get_db
import sqlite3


class PayrollItemsWidget(QWidget):
    """ویجت مدیریت اقلام حقوقی با دو تب (مزایا و کسورات)"""
    
    items_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.benefits_data = []
        self.deductions_data = []
        self.open_dialogs = []
        self.init_ui()
        self.load_items()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # عنوان
        title = QLabel("💰 مدیریت اقلام حقوق و دستمزد")
        title.setStyleSheet("""
            font-size: 16pt; 
            font-weight: bold; 
            padding: 10px; 
            color: #e94560;
        """)
        layout.addWidget(title)
        
        # تب‌ها
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #0f3460;
                border-radius: 8px;
                padding: 5px;
                background: #1a1a2e;
            }
            QTabBar::tab {
                padding: 10px 25px;
                margin: 2px;
                border-radius: 5px;
                font-weight: bold;
                background: #0f3460;
                color: #888;
            }
            QTabBar::tab:selected {
                background: #e94560;
                color: white;
            }
            QTabBar::tab:hover {
                background: #533483;
                color: white;
            }
        """)
        layout.addWidget(self.tabs)
        
        # تب 1: مزایا
        self.benefits_tab = self.create_items_tab("benefits")
        self.tabs.addTab(self.benefits_tab, "📋 مزایا")
        
        # تب 2: کسورات
        self.deductions_tab = self.create_items_tab("deductions")
        self.tabs.addTab(self.deductions_tab, "📉 کسورات")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # راهنما
        hint_label = QLabel(
            "💡 می‌توانید اقلام مزایا و کسورات را جداگانه مدیریت کنید.\n"
            "نوع قلم می‌تواند 'مبلغ ثابت' یا 'درصد' باشد."
        )
        hint_label.setStyleSheet("color: #888; font-size: 9pt; padding: 10px;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
    
    def create_items_tab(self, tab_type):
        """ایجاد تب برای مزایا یا کسورات"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # نوار ابزار
        toolbar = self._create_toolbar(tab_type)
        layout.addLayout(toolbar)
        
        # جدول
        table = self._create_table()
        layout.addWidget(table)
        
        widget.table = table
        widget.tab_type = tab_type
        
        return widget
    
    def _create_toolbar(self, tab_type):
        """ایجاد نوار ابزار"""
        toolbar = QHBoxLayout()
        
        buttons = [
            ("➕ قلم جدید", lambda: self.new_item(tab_type), "#4CAF50"),
            ("✏️ ویرایش", lambda: self.edit_item(tab_type), "#FF9800"),
            ("🗑️ حذف", lambda: self.delete_item(tab_type), "#e74c3c"),
        ]
        
        for text, callback, color in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 8px 15px;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ opacity: 0.8; }}
            """)
            btn.clicked.connect(callback)
            toolbar.addWidget(btn)
        
        toolbar.addStretch()
        
        search_label = QLabel("🔍 جستجو:")
        toolbar.addWidget(search_label)
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("نام قلم...")
        search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border-radius: 5px;
                border: 1px solid #0f3460;
                background-color: #1a1a3e;
                color: #e0e0e0;
                min-width: 200px;
            }
            QLineEdit:focus {
                border-color: #e94560;
            }
        """)
        search_input.textChanged.connect(lambda text: self.filter_items(tab_type, text))
        toolbar.addWidget(search_input)
        
        toolbar.search_input = search_input
        
        return toolbar
    
    def _create_table(self):
        """ایجاد جدول"""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["کد", "نام قلم", "نوع", "مقدار/نرخ", "واحد"])
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #0f3460;
                border: 1px solid #0f3460;
                border-radius: 8px;
                background-color: #1a1a3e;
                color: #e0e0e0;
                alternate-background-color: #0f0f23;
            }
            QTableWidget::item:selected {
                background-color: #533483;
                color: white;
            }
            QHeaderView::section {
                background-color: #0f3460;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        return table
    
    def load_items(self):
        """بارگذاری لیست اقلام از دیتابیس"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute("PRAGMA table_info(payroll_items)")
                columns = [col[1] for col in c.fetchall()]
                has_category = 'category' in columns
                
                # ========== مزایا ==========
                if has_category:
                    c.execute('''
                        SELECT code, name, type, value, unit, category
                        FROM payroll_items
                        WHERE category = 'benefit' OR category IS NULL
                        ORDER BY code
                    ''')
                else:
                    c.execute('''
                        SELECT code, name, type, value, unit
                        FROM payroll_items
                        ORDER BY code
                    ''')
                
                rows = c.fetchall()
                self.benefits_data = []
                for row in rows:
                    item = {
                        'code': row['code'] if row['code'] is not None else '',
                        'name': row['name'] if row['name'] is not None else '',
                        'type': row['type'] if row['type'] is not None else 'fixed',
                        'value': row['value'] if row['value'] is not None else 0,
                        'unit': row['unit'] if row['unit'] is not None else ''
                    }
                    if has_category and len(row) > 5:
                        item['category'] = row['category'] if row['category'] is not None else 'benefit'
                    else:
                        item['category'] = 'benefit'
                    self.benefits_data.append(item)
                
                # ========== کسورات ==========
                if has_category:
                    c.execute('''
                        SELECT code, name, type, value, unit, category
                        FROM payroll_items
                        WHERE category = 'deduction'
                        ORDER BY code
                    ''')
                    rows = c.fetchall()
                    self.deductions_data = []
                    for row in rows:
                        item = {
                            'code': row['code'] if row['code'] is not None else '',
                            'name': row['name'] if row['name'] is not None else '',
                            'type': row['type'] if row['type'] is not None else 'fixed',
                            'value': row['value'] if row['value'] is not None else 0,
                            'unit': row['unit'] if row['unit'] is not None else '',
                            'category': row['category'] if row['category'] is not None else 'deduction'
                        }
                        self.deductions_data.append(item)
                else:
                    deduction_codes = ['INSURANCE', 'TAX', 'LOAN', 'ADVANCE', 'DEDUCTION', 'PENALTY']
                    self.deductions_data = []
                    for item in self.benefits_data[:]:
                        if item['code'] in deduction_codes or 'کسورات' in item['name'] or 'کسر' in item['name']:
                            self.deductions_data.append(item)
                            self.benefits_data.remove(item)
                
                if not self.benefits_data and not self.deductions_data:
                    self._insert_default_items()
                    self.load_items()
                    return
                
                self.display_items('benefits')
                self.display_items('deductions')
                print(f"✅ {len(self.benefits_data)} قلم مزایا و {len(self.deductions_data)} قلم کسورات بارگذاری شد")
                
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری اقلام: {e}")
            import traceback
            traceback.print_exc()
            self.benefits_data = []
            self.deductions_data = []
    
    def _insert_default_items(self):
        """درج اقلام پیش‌فرض"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("PRAGMA table_info(payroll_items)")
                columns = [col[1] for col in c.fetchall()]
                has_category = 'category' in columns
                
                default_items = [
                    ('OVERTIME', 'اضافه کاری', 'percent', 1.5, 'برابر', 'benefit'),
                    ('NIGHT', 'شب کاری', 'percent', 0.35, 'درصد', 'benefit'),
                    ('FRIDAY', 'جمعه کاری', 'percent', 1.5, 'برابر', 'benefit'),
                    ('SHIFT', 'نوبت کاری', 'percent', 0.1, 'درصد', 'benefit'),
                    ('CHILD', 'حق اولاد', 'fixed', 0, 'ریال', 'benefit'),
                    ('HOUSING', 'حق مسکن', 'fixed', 0, 'ریال', 'benefit'),
                    ('MEAL', 'بن کارگری', 'fixed', 0, 'ریال', 'benefit'),
                    ('SENIORITY', 'پایه سنوات', 'fixed', 0, 'ریال', 'benefit'),
                    ('SPOUSE', 'حق همسر', 'fixed', 0, 'ریال', 'benefit'),
                    ('RESPONSIBILITY', 'حق مسئولیت', 'fixed', 0, 'ریال', 'benefit'),
                    ('BONUS', 'پاداش', 'fixed', 0, 'ریال', 'benefit'),
                    ('MISSION', 'حق ماموریت', 'fixed', 0, 'ریال', 'benefit'),
                    ('INSURANCE', 'بیمه سهم کارمند', 'percent', 0.07, 'درصد', 'deduction'),
                    ('TAX', 'مالیات بر درآمد', 'percent', 0.1, 'درصد', 'deduction'),
                    ('LOAN', 'قسط وام', 'fixed', 0, 'ریال', 'deduction'),
                    ('ADVANCE', 'مساعده', 'fixed', 0, 'ریال', 'deduction'),
                    ('DEDUCTION', 'سایر کسورات', 'fixed', 0, 'ریال', 'deduction'),
                    ('PENALTY', 'جریمه', 'fixed', 0, 'ریال', 'deduction'),
                ]
                
                for item in default_items:
                    if has_category:
                        c.execute('''
                            INSERT OR IGNORE INTO payroll_items (code, name, type, value, unit, category)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', item)
                    else:
                        c.execute('''
                            INSERT OR IGNORE INTO payroll_items (code, name, type, value, unit)
                            VALUES (?, ?, ?, ?, ?)
                        ''', item[:5])
                
                conn.commit()
                print("✅ اقلام پیش‌فرض درج شد")
                
        except Exception as e:
            print(f"⚠️ خطا در درج اقلام پیش‌فرض: {e}")
    
    def display_items(self, tab_type):
        """نمایش اقلام در تب مربوطه"""
        data = self.benefits_data if tab_type == 'benefits' else self.deductions_data
        widget = self.benefits_tab if tab_type == 'benefits' else self.deductions_tab
        table = widget.table
        
        table.setRowCount(len(data))
        
        type_names = {'fixed': '💰 مبلغ ثابت', 'percent': '📊 درصد'}
        
        for i, item in enumerate(data):
            table.setItem(i, 0, QTableWidgetItem(str(item.get('code', ''))))
            table.setItem(i, 1, QTableWidgetItem(str(item.get('name', ''))))
            type_text = type_names.get(item.get('type', 'fixed'), item.get('type', 'fixed'))
            table.setItem(i, 2, QTableWidgetItem(type_text))
            
            value = item.get('value', 0)
            if item.get('type') == 'percent':
                value_str = f"{value}%"
            else:
                value_str = f"{value:,.0f}" if value else "0"
            table.setItem(i, 3, QTableWidgetItem(value_str))
            
            unit = str(item.get('unit', '-'))
            table.setItem(i, 4, QTableWidgetItem(unit if unit else '-'))
    
    def filter_items(self, tab_type, text):
        """فیلتر اقلام"""
        data = self.benefits_data if tab_type == 'benefits' else self.deductions_data
        widget = self.benefits_tab if tab_type == 'benefits' else self.deductions_tab
        
        if not text:
            self.display_items(tab_type)
            return
        
        filtered = [item for item in data if text.lower() in str(item.get('name', '')).lower() or text.lower() in str(item.get('code', '')).lower()]
        table = widget.table
        table.setRowCount(len(filtered))
        
        type_names = {'fixed': '💰 مبلغ ثابت', 'percent': '📊 درصد'}
        
        for i, item in enumerate(filtered):
            table.setItem(i, 0, QTableWidgetItem(str(item.get('code', ''))))
            table.setItem(i, 1, QTableWidgetItem(str(item.get('name', ''))))
            type_text = type_names.get(item.get('type', 'fixed'), item.get('type', 'fixed'))
            table.setItem(i, 2, QTableWidgetItem(type_text))
            
            value = item.get('value', 0)
            if item.get('type') == 'percent':
                value_str = f"{value}%"
            else:
                value_str = f"{value:,.0f}" if value else "0"
            table.setItem(i, 3, QTableWidgetItem(value_str))
            
            unit = str(item.get('unit', '-'))
            table.setItem(i, 4, QTableWidgetItem(unit if unit else '-'))
    
    def on_tab_changed(self, index):
        """بروزرسانی هنگام تغییر تب"""
        if index == 0:
            self.display_items('benefits')
        else:
            self.display_items('deductions')
    
    def get_current_tab_type(self):
        """دریافت نوع تب فعلی"""
        return 'benefits' if self.tabs.currentIndex() == 0 else 'deductions'
    
    def get_current_data(self):
        """دریافت داده‌های تب فعلی"""
        return self.benefits_data if self.tabs.currentIndex() == 0 else self.deductions_data
    
    def get_current_widget(self):
        """دریافت ویجت تب فعلی"""
        return self.benefits_tab if self.tabs.currentIndex() == 0 else self.deductions_tab
    
    def new_item(self, tab_type=None):
        """ایجاد قلم جدید"""
        if tab_type is None:
            tab_type = self.get_current_tab_type()
        
        dialog = PayrollItemDialog(tab_type=tab_type, parent=self)
        dialog.finished.connect(self.on_dialog_closed)
        self.open_dialogs.append(dialog)
        
        if dialog.exec_():
            self.load_items()
            self.items_changed.emit()
            tab_name = "کسورات" if tab_type == 'deductions' else "مزایا"
            QMessageBox.information(self, "موفق", f"✅ قلم جدید {tab_name} اضافه شد!")
    
    def edit_item(self, tab_type=None):
        """ویرایش قلم"""
        if tab_type is None:
            tab_type = self.get_current_tab_type()
        
        widget = self.get_current_widget()
        row = widget.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک قلم را انتخاب کنید!")
            return
        
        data = self.get_current_data()
        if row >= len(data):
            return
        
        code = data[row].get('code', '')
        dialog = PayrollItemDialog(code, tab_type, parent=self)
        dialog.finished.connect(self.on_dialog_closed)
        self.open_dialogs.append(dialog)
        
        if dialog.exec_():
            self.load_items()
            self.items_changed.emit()
            QMessageBox.information(self, "موفق", "✅ قلم با موفقیت ویرایش شد!")
    
    def delete_item(self, tab_type=None):
        """حذف قلم"""
        if tab_type is None:
            tab_type = self.get_current_tab_type()
        
        widget = self.get_current_widget()
        row = widget.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک قلم را انتخاب کنید!")
            return
        
        data = self.get_current_data()
        if row >= len(data):
            return
        
        item = data[row]
        code = item.get('code', '')
        name = item.get('name', '')
        
        reply = QMessageBox.question(self, "تأیید حذف", f"آیا از حذف قلم '{name}' اطمینان دارید؟", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM payroll_items WHERE code = ?", [code])
                self.load_items()
                self.items_changed.emit()
                QMessageBox.information(self, "موفق", "✅ قلم حذف شد!")
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"خطا در حذف: {str(e)}")
    
    def on_dialog_closed(self):
        """حذف دیالوگ از لیست"""
        sender = self.sender()
        if sender in self.open_dialogs:
            self.open_dialogs.remove(sender)


class PayrollItemDialog(QDialog):
    """دیالوگ ایجاد/ویرایش قلم حقوقی"""
    
    def __init__(self, code=None, tab_type='benefits', parent=None):
        super().__init__(parent)
        self.item_code = code
        self.tab_type = tab_type
        
        tab_name = "مزایا" if tab_type == 'benefits' else "کسورات"
        self.setWindowTitle(f"✏️ ویرایش قلم {tab_name}" if code else f"➕ قلم جدید {tab_name}")
        self.setGeometry(300, 200, 450, 380)
        self.init_ui()
        if code:
            self.load_item_data()
    
    def init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.code = QLineEdit()
        self.code.setPlaceholderText("مثال: HOUSING")
        self.code.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #0f3460; background-color: #1a1a3e; color: #e0e0e0;")
        if self.item_code:
            self.code.setReadOnly(True)
            self.code.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #0f3460; background: #2d2d4e; color: #888;")
        layout.addRow("کد قلم *:", self.code)
        
        self.name = QLineEdit()
        self.name.setPlaceholderText("مثال: حق مسکن")
        self.name.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #0f3460; background-color: #1a1a3e; color: #e0e0e0;")
        layout.addRow("نام قلم *:", self.name)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["مبلغ ثابت (fixed)", "درصد (percent)"])
        self.type_combo.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #0f3460; background-color: #1a1a3e; color: #e0e0e0;")
        layout.addRow("نوع:", self.type_combo)
        
        self.value = QLineEdit()
        self.value.setPlaceholderText("مقدار (مبلغ یا درصد)")
        self.value.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #0f3460; background-color: #1a1a3e; color: #e0e0e0;")
        layout.addRow("مقدار:", self.value)
        
        self.unit = QLineEdit()
        self.unit.setPlaceholderText("مثال: ریال, ساعت, روز")
        self.unit.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #0f3460; background-color: #1a1a3e; color: #e0e0e0;")
        layout.addRow("واحد:", self.unit)
        
        category_label = QLabel("مزایا" if self.tab_type == 'benefits' else "کسورات")
        category_label.setStyleSheet("color: #e94560; font-weight: bold; padding: 5px; background: #0f3460; border-radius: 5px;")
        layout.addRow("دسته‌بندی:", category_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold; font-size: 11pt;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold; font-size: 11pt;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
    
    def load_item_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM payroll_items WHERE code = ?", [self.item_code])
                row = c.fetchone()
                if row:
                    self.code.setText(row['code'] if row['code'] is not None else '')
                    self.name.setText(row['name'] if row['name'] is not None else '')
                    type_val = row['type'] if row['type'] is not None else 'fixed'
                    self.type_combo.setCurrentText("مبلغ ثابت (fixed)" if type_val == 'fixed' else "درصد (percent)")
                    self.value.setText(str(row['value']) if row['value'] is not None else '0')
                    self.unit.setText(row['unit'] if row['unit'] is not None else '')
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری قلم: {e}")
    
    def accept(self):
        if not self.code.text().strip() or not self.name.text().strip():
            QMessageBox.warning(self, "خطا", "کد و نام قلم الزامی است!")
            return
        
        type_val = "fixed" if "fixed" in self.type_combo.currentText() else "percent"
        try:
            value = float(self.value.text().strip()) if self.value.text().strip() else 0
        except ValueError:
            QMessageBox.warning(self, "خطا", "مقدار نامعتبر است!")
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute("PRAGMA table_info(payroll_items)")
                columns = [col[1] for col in c.fetchall()]
                has_category = 'category' in columns
                
                category = 'deduction' if self.tab_type == 'deductions' else 'benefit'
                
                if self.item_code:
                    if has_category:
                        c.execute('''
                            UPDATE payroll_items
                            SET name=?, type=?, value=?, unit=?, category=?
                            WHERE code=?
                        ''', (
                            self.name.text().strip(),
                            type_val,
                            value,
                            self.unit.text().strip(),
                            category,
                            self.item_code
                        ))
                    else:
                        c.execute('''
                            UPDATE payroll_items
                            SET name=?, type=?, value=?, unit=?
                            WHERE code=?
                        ''', (
                            self.name.text().strip(),
                            type_val,
                            value,
                            self.unit.text().strip(),
                            self.item_code
                        ))
                else:
                    try:
                        if has_category:
                            c.execute('''
                                INSERT INTO payroll_items (code, name, type, value, unit, category)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (
                                self.code.text().strip(),
                                self.name.text().strip(),
                                type_val,
                                value,
                                self.unit.text().strip(),
                                category
                            ))
                        else:
                            c.execute('''
                                INSERT INTO payroll_items (code, name, type, value, unit)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (
                                self.code.text().strip(),
                                self.name.text().strip(),
                                type_val,
                                value,
                                self.unit.text().strip()
                            ))
                    except sqlite3.IntegrityError:
                        QMessageBox.warning(self, "خطا", "کد تکراری است!")
                        return
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا در ذخیره: {str(e)}")
