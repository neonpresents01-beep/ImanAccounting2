# ui/coding_manager.py
"""
مدیریت ساختار کدینگ حسابداری (سطوح نامحدود)
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import json
import os


class CodingStructure:
    """ساختار کدینگ (تعداد سطوح، طول هر سطح، جداکننده)"""
    
    def __init__(self):
        self.levels = []  # [(length, color, name), ...]
        self.separator = "-"
        self.load()
    
    def get_settings_path(self):
        return os.path.join(os.path.dirname(__file__), "..", "coding_structure.json")
    
    def save(self):
        data = {
            'levels': self.levels,
            'separator': self.separator
        }
        with open(self.get_settings_path(), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self):
        if os.path.exists(self.get_settings_path()):
            with open(self.get_settings_path(), 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.levels = data.get('levels', [])
                self.separator = data.get('separator', '-')
    
    def get_default_structure(self):
        """ساختار پیش‌فرض (برای نصب اول)"""
        if not self.levels:
            self.levels = [
                {'length': 2, 'color': '#3498db', 'name': 'کل'},
                {'length': 3, 'color': '#2ecc71', 'name': 'معین'},
                {'length': 3, 'color': '#e74c3c', 'name': 'تفصیلی'}
            ]
            self.save()
    
    def get_level_count(self):
        return len(self.levels)
    
    def get_code_length(self):
        """طول کل کد (بدون احتساب جداکننده)"""
        return sum(level['length'] for level in self.levels)
    
    def format_code(self, parts):
        """دریافت لیست بخش‌ها و بازگرداندن کد فرمت شده"""
        return self.separator.join(parts)
    
    def parse_code(self, code):
        """دریافت کد و بازگرداندن بخش‌ها"""
        return code.split(self.separator)
    
    def validate_parts(self, parts):
        """بررسی معتبر بودن بخش‌ها"""
        if len(parts) != len(self.levels):
            return False
        for i, part in enumerate(parts):
            if not part.isdigit():
                return False
            if len(part) != self.levels[i]['length']:
                return False
        return True


class CodingStructureDialog(QDialog):
    """دیالوگ تنظیم ساختار کدینگ"""
    
    def __init__(self, coding_structure, parent=None):
        super().__init__(parent)
        self.coding = coding_structure
        self.setWindowTitle("⚙️ تنظیمات ساختار کدینگ")
        self.setModal(True)
        self.setGeometry(400, 300, 600, 500)
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # توضیحات
        info = QLabel("تنظیم تعداد سطوح حساب، طول هر سطح و رنگ‌ها")
        info.setStyleSheet("font-size: 12pt; font-weight: bold; padding: 10px;")
        layout.addWidget(info)
        
        # جداکننده
        sep_layout = QHBoxLayout()
        sep_layout.addWidget(QLabel("جداکننده بین سطوح:"))
        self.separator_combo = QComboBox()
        self.separator_combo.addItems(["-", ".", "/", "_", " "])
        sep_layout.addWidget(self.separator_combo)
        sep_layout.addStretch()
        layout.addLayout(sep_layout)
        
        # جدول سطوح
        self.levels_table = QTableWidget()
        self.levels_table.setColumnCount(4)
        self.levels_table.setHorizontalHeaderLabels(["سطح", "طول (تعداد رقم)", "رنگ", "نام سطح"])
        self.levels_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.levels_table)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ افزودن سطح")
        add_btn.clicked.connect(self.add_level)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("➖ حذف سطح")
        remove_btn.clicked.connect(self.remove_level)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("background-color: #4CAF50;")
        save_btn.clicked.connect(self.save_structure)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        # هشدار
        warning = QLabel("⚠️ توجه: تغییر ساختار کدینگ بر روی حساب‌های موجود تأثیر می‌گذارد!")
        warning.setStyleSheet("color: #e74c3c; padding: 10px;")
        layout.addWidget(warning)
    
    def load_data(self):
        self.separator_combo.setCurrentText(self.coding.separator)
        
        self.levels_table.setRowCount(len(self.coding.levels))
        
        for i, level in enumerate(self.coding.levels):
            # شماره سطح
            self.levels_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            # طول
            length_spin = QSpinBox()
            length_spin.setRange(1, 6)
            length_spin.setValue(level['length'])
            self.levels_table.setCellWidget(i, 1, length_spin)
            
            # رنگ
            color_btn = QPushButton("انتخاب رنگ")
            color_btn.setStyleSheet(f"background-color: {level['color']};")
            color_btn.clicked.connect(lambda checked, row=i: self.select_color(row))
            self.levels_table.setCellWidget(i, 2, color_btn)
            
            # نام سطح
            name_edit = QLineEdit(level['name'])
            self.levels_table.setCellWidget(i, 3, name_edit)
    
    def select_color(self, row):
        color = QColorDialog.getColor()
        if color.isValid():
            btn = self.levels_table.cellWidget(row, 2)
            btn.setStyleSheet(f"background-color: {color.name()};")
    
    def add_level(self):
        row = self.levels_table.rowCount()
        self.levels_table.insertRow(row)
        
        self.levels_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        
        length_spin = QSpinBox()
        length_spin.setRange(1, 6)
        length_spin.setValue(2)
        self.levels_table.setCellWidget(row, 1, length_spin)
        
        color_btn = QPushButton("انتخاب رنگ")
        color_btn.setStyleSheet("background-color: #3498db;")
        color_btn.clicked.connect(lambda checked, r=row: self.select_color(r))
        self.levels_table.setCellWidget(row, 2, color_btn)
        
        name_edit = QLineEdit(f"سطح {row + 1}")
        self.levels_table.setCellWidget(row, 3, name_edit)
        
        # به‌روزرسانی شماره سطوح
        self.update_level_numbers()
    
    def remove_level(self):
        row = self.levels_table.currentRow()
        if row >= 0:
            self.levels_table.removeRow(row)
            self.update_level_numbers()
    
    def update_level_numbers(self):
        for row in range(self.levels_table.rowCount()):
            self.levels_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
    
    def save_structure(self):
        levels = []
        
        for row in range(self.levels_table.rowCount()):
            length_spin = self.levels_table.cellWidget(row, 1)
            color_btn = self.levels_table.cellWidget(row, 2)
            name_edit = self.levels_table.cellWidget(row, 3)
            
            # استخراج رنگ از استایل
            style = color_btn.styleSheet()
            color = "#3498db"
            if "background-color:" in style:
                color = style.split("background-color: ")[1].split(";")[0]
            
            levels.append({
                'length': length_spin.value(),
                'color': color,
                'name': name_edit.text()
            })
        
        if not levels:
            QMessageBox.warning(self, "خطا", "حداقل یک سطح باید وجود داشته باشد!")
            return
        
        self.coding.levels = levels
        self.coding.separator = self.separator_combo.currentText()
        self.coding.save()
        
        QMessageBox.information(self, "موفقیت", "ساختار کدینگ ذخیره شد!")
        self.accept()