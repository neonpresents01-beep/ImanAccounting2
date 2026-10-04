# ui/inventory_widget.py
# ============================================================
# ویجت انبارداری پیشرفته ImanAccount
# نسخه کامل با رفع تمام خطاها + رفع مشکل انتقال انبار
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui.base_widgets import BaseWidget, BaseDialog
from database import get_db
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali
import csv
from datetime import datetime


# ============================================================
# کلاس MoneyLineEdit - ورودی مبلغ با فرمت هزارگان
# ============================================================

class MoneyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_value = 0
        self.setAlignment(Qt.AlignRight)
        self.setPlaceholderText("مبلغ به ریال")
        self.textChanged.connect(self._format_text)
        self.setStyleSheet("padding: 5px; border: 1px solid #ddd; border-radius: 4px;")

    def _format_text(self):
        text = self.text().replace(',', '').strip()
        if not text:
            self._current_value = 0
            return
        if text.isdigit():
            self._current_value = int(text)
            formatted = f"{self._current_value:,}"
            if formatted != self.text():
                self.blockSignals(True)
                self.setText(formatted)
                self.blockSignals(False)

    def get_value(self) -> int:
        return self._current_value

    def set_value(self, value: int):
        self._current_value = value if value else 0
        self.blockSignals(True)
        self.setText(f"{self._current_value:,}" if self._current_value > 0 else "")
        self.blockSignals(False)

    def value(self) -> int:
        return self.get_value()

    def setValue(self, value: int):
        self.set_value(value)


# ============================================================
# دیالوگ مدیریت انبارها
# ============================================================

class WarehouseDialog(BaseDialog):
    def __init__(self, warehouse_id=None, parent=None):
        super().__init__(parent, base_width=500, base_height=450)
        self.warehouse_id = warehouse_id
        self.setWindowTitle("✏️ ویرایش انبار" if warehouse_id else "➕ انبار جدید")
        self.setModal(True)
        self.setup_ui()
        if warehouse_id:
            self.load_data()
        self.apply_theme()

    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)

        self.code = QLineEdit()
        self.code.setPlaceholderText("مثال: WH-002")
        self.code.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        layout.addRow("کد انبار *:", self.code)

        self.name = QLineEdit()
        self.name.setPlaceholderText("نام انبار")
        self.name.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        layout.addRow("نام انبار *:", self.name)

        self.address = QTextEdit()
        self.address.setPlaceholderText("آدرس کامل انبار")
        self.address.setMaximumHeight(60)
        layout.addRow("آدرس:", self.address)

        self.manager = QLineEdit()
        self.manager.setPlaceholderText("نام مسئول انبار")
        self.manager.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        layout.addRow("مسئول انبار:", self.manager)

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("تلفن انبار")
        self.phone.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        layout.addRow("تلفن:", self.phone)

        self.is_default = QCheckBox("انبار پیش‌فرض")
        self.is_default.setStyleSheet("padding: 8px;")
        layout.addRow("", self.is_default)

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.addStretch()
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow(btn_widget)

    def load_data(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM warehouses WHERE id = ?", [self.warehouse_id])
            row = c.fetchone()
            if row:
                self.code.setText(row['code'])
                self.name.setText(row['name'])
                self.address.setText(row['address'] or '')
                self.manager.setText(row['manager'] or '')
                self.phone.setText(row['phone'] or '')
                self.is_default.setChecked(row['is_default'] == 1)

    def get_next_code(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code FROM warehouses ORDER BY code DESC LIMIT 1")
            last = c.fetchone()
            if last:
                try:
                    num = int(last['code'].replace('WH-', '')) + 1
                    return f"WH-{num:03d}"
                except:
                    pass
            return "WH-001"

    def accept(self):
        if not self.code.text().strip():
            self.code.setText(self.get_next_code())
        if not self.name.text().strip():
            QMessageBox.warning(self, "خطا", "نام انبار را وارد کنید!")
            return

        with get_db() as conn:
            c = conn.cursor()
            if self.is_default.isChecked():
                c.execute("UPDATE warehouses SET is_default = 0 WHERE is_default = 1")
            if self.warehouse_id:
                c.execute('''
                    UPDATE warehouses SET code=?, name=?, address=?, manager=?, phone=?, is_default=?
                    WHERE id=?
                ''', [self.code.text().strip(), self.name.text().strip(),
                      self.address.toPlainText().strip(), self.manager.text().strip(),
                      self.phone.text().strip(), 1 if self.is_default.isChecked() else 0,
                      self.warehouse_id])
            else:
                c.execute('''
                    INSERT INTO warehouses (code, name, address, manager, phone, is_default)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', [self.code.text().strip(), self.name.text().strip(),
                      self.address.toPlainText().strip(), self.manager.text().strip(),
                      self.phone.text().strip(), 1 if self.is_default.isChecked() else 0])
            conn.commit()
        super().accept()


# ============================================================
# دیالوگ افزودن/ویرایش کالا
# ============================================================

class ProductDialog(BaseDialog):
    def __init__(self, product_id=None, customer_name="", parent=None):
        super().__init__(parent, base_width=700, base_height=750)
        self.product_id = product_id
        self.customer_name = customer_name
        self.setWindowTitle("✏️ ویرایش کالا" if product_id else "➕ کالای جدید")
        self.setModal(True)
        self.setup_ui()
        if product_id:
            self.load_data()
        self.apply_theme()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # تب اطلاعات اصلی
        basic_tab = QWidget()
        basic_layout = QFormLayout(basic_tab)
        basic_layout.setSpacing(8)
        basic_layout.setLabelAlignment(Qt.AlignRight)

        self.code = QLineEdit()
        self.code.setPlaceholderText("خودکار")
        self.code.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        basic_layout.addRow("📋 کد کالا:", self.code)

        self.name = QLineEdit()
        self.name.setPlaceholderText("نام کالا")
        self.name.setStyleSheet("padding: 8px; border: 2px solid #27ae60; border-radius: 4px;")
        basic_layout.addRow("📛 نام کالا *:", self.name)

        self.category = QComboBox()
        self.category.setEditable(True)
        categories = ["", "الکترونیک", "ابزارآلات", "لاستیک", "پوشاک", "مواد غذایی", "صنعتی", "خدماتی", "سایر"]
        self.category.addItems(categories)
        self.category.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        basic_layout.addRow("📂 دسته‌بندی:", self.category)

        self.unit = QComboBox()
        self.unit.setEditable(True)
        units = ["عدد", "کیلوگرم", "متر", "لیتر", "بسته", "کارتن", "شاخه", "جفت", "کیسه", "قوطی"]
        self.unit.addItems(units)
        self.unit.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        basic_layout.addRow("📏 واحد:", self.unit)

        self.tabs.addTab(basic_tab, "📋 اطلاعات اصلی")

        # تب مشخصات تکمیلی
        advanced_tab = QWidget()
        advanced_layout = QFormLayout(advanced_tab)
        advanced_layout.setSpacing(8)
        advanced_layout.setLabelAlignment(Qt.AlignRight)

        self.brand = QLineEdit()
        self.brand.setPlaceholderText("برند کالا")
        self.brand.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        advanced_layout.addRow("🏷️ برند:", self.brand)

        self.model = QLineEdit()
        self.model.setPlaceholderText("مدل کالا")
        self.model.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        advanced_layout.addRow("📐 مدل:", self.model)

        self.color = QLineEdit()
        self.color.setPlaceholderText("رنگ")
        self.color.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        advanced_layout.addRow("🎨 رنگ:", self.color)

        self.size = QLineEdit()
        self.size.setPlaceholderText("سایز (مثلاً: 42, XL, 15x20)")
        self.size.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        advanced_layout.addRow("📏 سایز:", self.size)

        self.weight = QDoubleSpinBox()
        self.weight.setRange(0, 99999)
        self.weight.setDecimals(2)
        self.weight.setSuffix(" کیلوگرم")
        self.weight.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        advanced_layout.addRow("⚖️ وزن:", self.weight)

        self.barcode = QLineEdit()
        self.barcode.setPlaceholderText("کد بارکد (13 رقم)")
        self.barcode.setMaxLength(13)
        self.barcode.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        advanced_layout.addRow("📱 بارکد:", self.barcode)

        self.has_serial = QCheckBox("دارای سریال‌نمبر")
        self.has_serial.setStyleSheet("padding: 8px;")
        advanced_layout.addRow("🔢 سریال‌نمبر:", self.has_serial)

        self.expiry_date = ShamsiDateEdit()
        self.expiry_date.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        advanced_layout.addRow("📅 تاریخ انقضا:", self.expiry_date)

        self.location = QLineEdit()
        self.location.setPlaceholderText("محل نگهداری (قفسه، ردیف)")
        self.location.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        advanced_layout.addRow("📍 محل انبار:", self.location)

        self.tabs.addTab(advanced_tab, "🔧 مشخصات تکمیلی")

        # تب قیمت و موجودی
        price_tab = QWidget()
        price_layout = QFormLayout(price_tab)
        price_layout.setSpacing(8)
        price_layout.setLabelAlignment(Qt.AlignRight)

        self.purchase_price = MoneyLineEdit()
        price_layout.addRow("💰 قیمت خرید (ریال):", self.purchase_price)

        self.sale_price = MoneyLineEdit()
        price_layout.addRow("💰 قیمت فروش (ریال):", self.sale_price)

        self.min_stock = QDoubleSpinBox()
        self.min_stock.setRange(0, 999999)
        self.min_stock.setDecimals(2)
        self.min_stock.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        price_layout.addRow("📉 حداقل موجودی:", self.min_stock)

        self.max_stock = QDoubleSpinBox()
        self.max_stock.setRange(0, 999999)
        self.max_stock.setDecimals(2)
        self.max_stock.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        price_layout.addRow("📈 حداکثر موجودی:", self.max_stock)

        self.warehouse_combo = QComboBox()
        self.warehouse_combo.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        self.load_warehouses()
        price_layout.addRow("🏢 انبار پیش‌فرض:", self.warehouse_combo)

        self.tabs.addTab(price_tab, "💰 قیمت و موجودی")

        main_layout.addWidget(self.tabs)

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.addStretch()
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        main_layout.addWidget(btn_widget)

    def load_warehouses(self):
        self.warehouse_combo.clear()
        self.warehouse_combo.addItem("-- انتخاب انبار --", "")
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY code")
            rows = c.fetchall()
            for row in rows:
                self.warehouse_combo.addItem(f"{row['code']} - {row['name']}", row['id'])

    def load_data(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM products WHERE id = ?", [self.product_id])
            row = c.fetchone()
            if row:
                self.code.setText(row['code'])
                self.name.setText(row['name'])
                self.category.setCurrentText(row['category'] or '')
                self.unit.setCurrentText(row['unit'] or 'عدد')
                self.brand.setText(row['brand'] or '')
                self.model.setText(row['model'] or '')
                self.color.setText(row['color'] or '')
                self.size.setText(row['size'] or '')
                self.weight.setValue(row['weight'] or 0)
                self.barcode.setText(row['barcode'] or '')
                self.has_serial.setChecked(row['has_serial'] == 1)
                if row['expiry_date']:
                    self.expiry_date.set_date(row['expiry_date'])
                self.location.setText(row['location'] or '')
                self.purchase_price.setValue(row['purchase_price'] or 0)
                self.sale_price.setValue(row['sale_price'] or 0)
                self.min_stock.setValue(row['min_stock'] or 0)
                self.max_stock.setValue(row['max_stock'] or 0)
                if row['warehouse_id']:
                    idx = self.warehouse_combo.findData(row['warehouse_id'])
                    if idx >= 0:
                        self.warehouse_combo.setCurrentIndex(idx)

    def get_next_code(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code FROM products ORDER BY code DESC LIMIT 1")
            last = c.fetchone()
            if last:
                try:
                    num = int(last['code'].replace('KALA-', '')) + 1
                    return f"KALA-{num:04d}"
                except:
                    pass
            return "KALA-0001"

    def accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "خطا", "نام کالا را وارد کنید!")
            return

        code = self.code.text().strip()
        if not code:
            code = self.get_next_code()

        with get_db() as conn:
            c = conn.cursor()
            if self.product_id:
                c.execute('''
                    UPDATE products SET
                        code=?, name=?, category=?, unit=?, brand=?, model=?,
                        color=?, size=?, weight=?, barcode=?, has_serial=?,
                        expiry_date=?, location=?, purchase_price=?, sale_price=?,
                        min_stock=?, max_stock=?, warehouse_id=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                ''', [
                    code, self.name.text().strip(), self.category.currentText(),
                    self.unit.currentText(), self.brand.text().strip(),
                    self.model.text().strip(), self.color.text().strip(),
                    self.size.text().strip(), self.weight.value(),
                    self.barcode.text().strip(), 1 if self.has_serial.isChecked() else 0,
                    self.expiry_date.get_shamsi(), self.location.text().strip(),
                    self.purchase_price.value(), self.sale_price.value(),
                    self.min_stock.value(), self.max_stock.value(),
                    self.warehouse_combo.currentData(), self.product_id
                ])
            else:
                c.execute('''
                    INSERT INTO products (
                        code, name, category, unit, brand, model, color, size,
                        weight, barcode, has_serial, expiry_date, location,
                        purchase_price, sale_price, min_stock, max_stock, warehouse_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    code, self.name.text().strip(), self.category.currentText(),
                    self.unit.currentText(), self.brand.text().strip(),
                    self.model.text().strip(), self.color.text().strip(),
                    self.size.text().strip(), self.weight.value(),
                    self.barcode.text().strip(), 1 if self.has_serial.isChecked() else 0,
                    self.expiry_date.get_shamsi(), self.location.text().strip(),
                    self.purchase_price.value(), self.sale_price.value(),
                    self.min_stock.value(), self.max_stock.value(),
                    self.warehouse_combo.currentData()
                ])
            conn.commit()
        super().accept()


# ============================================================
# دیالوگ تراکنش انبار (رسید/حواله)
# ============================================================

class StockTransactionDialog(BaseDialog):
    def __init__(self, product, trans_type):
        super().__init__(base_width=550, base_height=620)
        self.product = product
        self.trans_type = trans_type
        self._total_value = 0
        self.setWindowTitle("📥 رسید انبار" if trans_type == 'in' else "📤 حواله انبار")
        self.setModal(True)
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)

        title = QLabel(f"<h3>{self.product['name']}</h3>")
        title.setAlignment(Qt.AlignCenter)
        layout.addRow(title)

        self.warehouse_combo = QComboBox()
        self.load_warehouses()
        layout.addRow("🏢 انبار:", self.warehouse_combo)

        stock_info = QLabel(f"موجودی فعلی: {self.product.get('stock', 0):,.2f} {self.product.get('unit', 'عدد')}")
        stock_info.setStyleSheet("font-weight: bold;")
        layout.addRow(stock_info)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addRow(line)

        self.date = ShamsiDateEdit()
        layout.addRow("تاریخ:", self.date)

        self.quantity = QDoubleSpinBox()
        self.quantity.setRange(0.01, 999999)
        self.quantity.setDecimals(2)
        self.quantity.setValue(1)
        self.quantity.setSuffix(f" {self.product.get('unit', 'عدد')}")
        self.quantity.valueChanged.connect(self.calculate_total)
        layout.addRow("مقدار *:", self.quantity)

        self.unit_price = MoneyLineEdit()
        if self.trans_type == 'in':
            self.unit_price.setValue(self.product.get('purchase_price', 0))
        else:
            self.unit_price.setValue(self.product.get('sale_price', 0))
        self.unit_price.textChanged.connect(self.calculate_total)
        layout.addRow("فی (ریال) *:", self.unit_price)

        self.total_price_label = QLabel("۰ ریال")
        self.total_price_label.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 12pt;")
        layout.addRow("مبلغ کل:", self.total_price_label)

        self.serial_numbers = QTextEdit()
        self.serial_numbers.setPlaceholderText("شماره سریال‌ها (هر سریال در یک خط)")
        self.serial_numbers.setMaximumHeight(60)
        layout.addRow("🔢 سریال‌نمبرها:", self.serial_numbers)

        self.ref_no = QLineEdit()
        self.ref_no.setPlaceholderText("شماره مرجع (اختیاری)")
        layout.addRow("شماره مرجع:", self.ref_no)

        self.description = QTextEdit()
        self.description.setPlaceholderText("توضیحات (اختیاری)")
        self.description.setMaximumHeight(60)
        layout.addRow("شرح:", self.description)

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.addStretch()
        save_btn = QPushButton("💾 ثبت")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow(btn_widget)

        self.calculate_total()

    def load_warehouses(self):
        self.warehouse_combo.clear()
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY code")
            rows = c.fetchall()
            for row in rows:
                self.warehouse_combo.addItem(f"{row['code']} - {row['name']}", row['id'])

    def calculate_total(self):
        qty = self.quantity.value()
        price = self.unit_price.value()
        total = qty * price
        self.total_price_label.setText(f"{total:,.0f} ریال")
        self._total_value = total

    def accept(self):
        if self.quantity.value() == 0:
            QMessageBox.warning(self, "خطا", "مقدار باید بیشتر از صفر باشد!")
            return
        if self.unit_price.value() == 0:
            QMessageBox.warning(self, "خطا", "قیمت واحد باید بیشتر از صفر باشد!")
            return
        if self.trans_type == 'out' and self.quantity.value() > self.product.get('stock', 0):
            QMessageBox.warning(self, "خطا", f"موجودی کافی نیست! موجودی: {self.product.get('stock', 0):,.2f}")
            return

        warehouse_id = self.warehouse_combo.currentData()
        if not warehouse_id:
            QMessageBox.warning(self, "خطا", "لطفاً انبار را انتخاب کنید!")
            return

        try:
            with get_db() as conn:
                c = conn.cursor()

                if self.trans_type == 'in':
                    # ✅ افزودن به انبار
                    c.execute('''
                        INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(product_id, warehouse_id) DO UPDATE SET
                            quantity = quantity + ?,
                            updated_at = CURRENT_TIMESTAMP
                    ''', [self.product['id'], warehouse_id, self.quantity.value(), self.quantity.value()])
                else:
                    # ✅ کم کردن از انبار
                    c.execute('''
                        UPDATE warehouse_stock 
                        SET quantity = MAX(0, quantity - ?), updated_at = CURRENT_TIMESTAMP
                        WHERE product_id = ? AND warehouse_id = ?
                    ''', [self.quantity.value(), self.product['id'], warehouse_id])

                # ✅ ثبت تراکنش
                c.execute('''
                    INSERT INTO stock_transactions (
                        date, product_id, warehouse_id, type, quantity,
                        unit_price, total_price, ref_no, description, serial_numbers
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    self.date.get_shamsi(), self.product['id'], warehouse_id,
                    self.trans_type, self.quantity.value(),
                    self.unit_price.value(), self._total_value,
                    self.ref_no.text(), self.description.toPlainText(),
                    self.serial_numbers.toPlainText()
                ])

                # ✅ بروزرسانی موجودی کل محصول
                c.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM warehouse_stock WHERE product_id = ?",
                    [self.product['id']]
                )
                total_stock = c.fetchone()[0] or 0
                c.execute(
                    "UPDATE products SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [total_stock, self.product['id']]
                )

                conn.commit()
            super().accept()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "خطا", f"❌ خطا در ثبت تراکنش: {e}")


# ============================================================
# دیالوگ انتقال بین انبارها
# ✅ رفع خطای ۲ + رفع مشکل انتقال
# ============================================================

class StockTransferDialog(BaseDialog):
    def __init__(self, product):
        super().__init__(base_width=550, base_height=580)
        self.product = product
        self.setWindowTitle("🔄 انتقال کالا بین انبارها")
        self.setModal(True)
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)

        title = QLabel(f"<h3>انتقال {self.product['name']}</h3>")
        title.setAlignment(Qt.AlignCenter)
        layout.addRow(title)

        # ✅ اول from_warehouse رو بساز
        self.from_warehouse = QComboBox()
        self.from_warehouse.currentIndexChanged.connect(self.update_available_stock)
        layout.addRow("🏢 انبار مبدا:", self.from_warehouse)

        self.available_stock_label = QLabel("موجودی قابل انتقال: ۰")
        self.available_stock_label.setStyleSheet("font-weight: bold; color: #273c75; padding: 5px;")
        layout.addRow(self.available_stock_label)

        # ✅ بعد to_warehouse رو بساز
        self.to_warehouse = QComboBox()
        layout.addRow("🏢 انبار مقصد:", self.to_warehouse)

        # ✅ حالا که هر دو ساخته شدن، load_warehouses رو صدا بزن
        self.load_warehouses()

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addRow(line)

        self.date = ShamsiDateEdit()
        layout.addRow("تاریخ:", self.date)

        self.quantity = QDoubleSpinBox()
        self.quantity.setRange(0.01, 999999)
        self.quantity.setDecimals(2)
        self.quantity.setValue(1)
        self.quantity.setSuffix(f" {self.product.get('unit', 'عدد')}")
        layout.addRow("مقدار:", self.quantity)

        self.description = QTextEdit()
        self.description.setPlaceholderText("دلیل انتقال (اختیاری)")
        self.description.setMaximumHeight(60)
        layout.addRow("شرح:", self.description)

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.addStretch()
        transfer_btn = QPushButton("🔄 انتقال")
        transfer_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold;")
        transfer_btn.clicked.connect(self.accept)
        btn_layout.addWidget(transfer_btn)

        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px 25px; border: none; border-radius: 5px; font-weight: bold;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow(btn_widget)

        # ✅ بروزرسانی موجودی اولیه
        self.update_available_stock()

    def load_warehouses(self):
        """بارگذاری لیست انبارها با چک ایمن برای هر دو combo"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id, code, name FROM warehouses "
                    "WHERE is_active = 1 ORDER BY code"
                )
                rows = c.fetchall()

                # ✅ چک from_warehouse
                if hasattr(self, 'from_warehouse') and self.from_warehouse is not None:
                    self.from_warehouse.blockSignals(True)
                    self.from_warehouse.clear()
                    for row in rows:
                        self.from_warehouse.addItem(
                            f"{row['code']} - {row['name']}", row['id']
                        )
                    self.from_warehouse.blockSignals(False)

                # ✅ چک to_warehouse
                if hasattr(self, 'to_warehouse') and self.to_warehouse is not None:
                    self.to_warehouse.clear()
                    for row in rows:
                        self.to_warehouse.addItem(
                            f"{row['code']} - {row['name']}", row['id']
                        )
                    # ✅ اگه بیش از ۱ انبار، دومی رو انتخاب کن به عنوان پیش‌فرض مقصد
                    if len(rows) >= 2:
                        self.to_warehouse.setCurrentIndex(1)

                # اگه حداقل ۲ انبار نیست
                if len(rows) < 2:
                    QMessageBox.warning(
                        self, "توجه",
                        "⚠️ برای انتقال، حداقل ۲ انبار نیازه!\n\n"
                        "از دکمه «🏢 مدیریت انبارها» یه انبار جدید بساز."
                    )
        except Exception as e:
            print(f"⚠️ خطا در load_warehouses: {e}")

    def update_available_stock(self):
        """بروزرسانی موجودی قابل انتقال — با غیرفعال کردن quantity در صورت صفر بودن"""
        warehouse_id = self.from_warehouse.currentData()
        if not warehouse_id:
            self.available_stock_label.setText("موجودی قابل انتقال: ۰")
            self.quantity.setEnabled(False)
            return

        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT quantity FROM warehouse_stock "
                    "WHERE product_id = ? AND warehouse_id = ?",
                    [self.product['id'], warehouse_id]
                )
                row = c.fetchone()
                stock = float(row[0]) if row and row[0] else 0

                self.available_stock_label.setText(
                    f"موجودی قابل انتقال: {stock:,.2f} {self.product.get('unit', 'عدد')}"
                )

                # ✅ اگه موجودی صفره، quantity رو غیرفعال کن
                if stock <= 0:
                    self.quantity.setMaximum(0)
                    self.quantity.setValue(0)
                    self.quantity.setEnabled(False)
                    self.available_stock_label.setStyleSheet(
                        "font-weight: bold; color: #e84118; padding: 5px;"
                    )
                else:
                    self.quantity.setEnabled(True)
                    self.quantity.setMaximum(stock)
                    if self.quantity.value() > stock or self.quantity.value() <= 0:
                        self.quantity.setValue(min(1, stock))
                    self.available_stock_label.setStyleSheet(
                        "font-weight: bold; color: #273c75; padding: 5px;"
                    )
        except Exception as e:
            print(f"⚠️ خطا در update_available_stock: {e}")

    def accept(self):
        from_warehouse_id = self.from_warehouse.currentData()
        to_warehouse_id = self.to_warehouse.currentData()
        quantity = self.quantity.value()

        # ===== 🔍 دیباگ =====
        print("=" * 50)
        print(f"🔍 DEBUG انتقال:")
        print(f"  product_id: {self.product.get('id')}")
        print(f"  product_name: {self.product.get('name')}")
        print(f"  from_warehouse_id: {from_warehouse_id}")
        print(f"  to_warehouse_id: {to_warehouse_id}")
        print(f"  quantity: {quantity}")
        print("=" * 50)

        # ===== اعتبارسنجی =====
        if not from_warehouse_id or not to_warehouse_id:
            QMessageBox.warning(self, "خطا", "لطفاً هر دو انبار را انتخاب کنید!")
            return
        if from_warehouse_id == to_warehouse_id:
            QMessageBox.warning(self, "خطا", "انبار مبدا و مقصد نمی‌توانند یکسان باشند!")
            return
        if quantity <= 0:
            QMessageBox.warning(self, "خطا", "مقدار باید بیشتر از صفر باشد!")
            return

        try:
            with get_db() as conn:
                c = conn.cursor()

                # ✅ چک موجودی مبدا
                c.execute(
                    "SELECT quantity FROM warehouse_stock "
                    "WHERE product_id = ? AND warehouse_id = ?",
                    [self.product['id'], from_warehouse_id]
                )
                row = c.fetchone()
                available = float(row[0]) if row and row[0] else 0

                if available <= 0:
                    QMessageBox.warning(
                        self, "خطا",
                        "موجودی انبار مبدا صفره!"
                    )
                    return

                if quantity > available:
                    QMessageBox.warning(
                        self, "خطا",
                        f"موجودی کافی نیست!\n"
                        f"موجودی فعلی: {available:,.2f}\n"
                        f"درخواستی: {quantity:,.2f}"
                    )
                    return

                # ✅ ۱. کم کردن از مبدا (بدون منفی شدن)
                c.execute('''
                    UPDATE warehouse_stock 
                    SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ? AND warehouse_id = ?
                ''', [quantity, self.product['id'], from_warehouse_id])

                # ✅ ۲. اضافه کردن به مقصد
                c.execute('''
                    INSERT INTO warehouse_stock (product_id, warehouse_id, quantity, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(product_id, warehouse_id) DO UPDATE SET
                        quantity = quantity + ?,
                        updated_at = CURRENT_TIMESTAMP
                ''', [self.product['id'], to_warehouse_id, quantity, quantity])

                # ✅ ۳. ثبت تراکنش
                c.execute('''
                    INSERT INTO stock_transactions (
                        date, product_id, from_warehouse_id, to_warehouse_id,
                        type, quantity, description
                    ) VALUES (?, ?, ?, ?, 'transfer', ?, ?)
                ''', [
                    self.date.get_shamsi(), self.product['id'],
                    from_warehouse_id, to_warehouse_id, quantity,
                    self.description.toPlainText()
                ])

                # ✅ ۴. بروزرسانی موجودی کل محصول
                c.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM warehouse_stock WHERE product_id = ?",
                    [self.product['id']]
                )
                total_stock = c.fetchone()[0] or 0
                c.execute(
                    "UPDATE products SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [total_stock, self.product['id']]
                )

                conn.commit()

            print(f"✅ انتقال موفق: {quantity} از {from_warehouse_id} به {to_warehouse_id}")
            super().accept()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "خطا", f"❌ خطا در انتقال: {e}")


# ============================================================
# ویجت اصلی انبارداری
# ============================================================

class InventoryWidget(BaseWidget):
    def __init__(self, customer_name: str = "", user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        self.customer_name = customer_name
        self.user_level = user_level
        self.products_data = []
        self.current_product = None
        self.warehouses = []
        self.valuation_method = self.get_valuation_method()

        self.setup_ui()
        self.load_warehouses()
        self.load_products()
        self.update_ui_by_permission()
        self.apply_theme()

    def get_valuation_method(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'valuation_method'")
                row = c.fetchone()
                return row[0] if row else "simple"
        except:
            return "simple"

    def get_valuation_method_display(self):
        methods = {'simple': 'ساده', 'fifo': 'FIFO', 'lifo': 'LIFO', 'weighted_average': 'میانگین موزون'}
        return methods.get(self.valuation_method, 'ساده')

    def set_user_level(self, level: str):
        self.user_level = level
        self.update_ui_by_permission()

    def update_ui_by_permission(self):
        can_edit = self.user_level in ['admin', 'inventory']
        for btn_name in ['new_btn', 'edit_btn', 'delete_btn', 'stock_in_btn', 'stock_out_btn', 'transfer_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setVisible(can_edit)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # عنوان
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title = QLabel("📦 مدیریت انبار پیشرفته")
        title.setObjectName("titleLabel")
        title_layout.addWidget(title)

        method_label = QLabel(f"📊 روش ارزشیابی: {self.get_valuation_method_display()}")
        method_label.setObjectName("subtitleLabel")
        title_layout.addStretch()
        title_layout.addWidget(method_label)

        main_layout.addWidget(title_widget)

        # نوار ابزار
        toolbar_widget = QWidget()
        toolbar = QHBoxLayout(toolbar_widget)
        toolbar.setSpacing(8)

        self.new_btn = self.create_button("➕ کالای جدید", "successBtn")
        self.new_btn.clicked.connect(self.new_product)
        toolbar.addWidget(self.new_btn)

        self.edit_btn = self.create_button("✏️ ویرایش", "warningBtn")
        self.edit_btn.clicked.connect(self.edit_product)
        toolbar.addWidget(self.edit_btn)

        self.delete_btn = self.create_button("🗑️ حذف", "dangerBtn")
        self.delete_btn.clicked.connect(self.delete_product)
        toolbar.addWidget(self.delete_btn)

        toolbar.addSpacing(10)

        self.stock_in_btn = self.create_button("📥 رسید", "infoBtn")
        self.stock_in_btn.clicked.connect(lambda: self.stock_transaction('in'))
        toolbar.addWidget(self.stock_in_btn)

        self.stock_out_btn = self.create_button("📤 حواله", "warningBtn")
        self.stock_out_btn.clicked.connect(lambda: self.stock_transaction('out'))
        toolbar.addWidget(self.stock_out_btn)

        self.transfer_btn = self.create_button("🔄 انتقال", "infoBtn")
        self.transfer_btn.clicked.connect(self.transfer_stock)
        toolbar.addWidget(self.transfer_btn)

        toolbar.addSpacing(10)

        warehouse_btn = self.create_button("🏢 مدیریت انبارها", "infoBtn")
        warehouse_btn.clicked.connect(self.manage_warehouses)
        toolbar.addWidget(warehouse_btn)

        toolbar.addStretch()

        export_btn = self.create_button("📎 خروجی Excel", "successBtn")
        export_btn.clicked.connect(self.export_to_excel)
        toolbar.addWidget(export_btn)

        refresh_btn = self.create_button("🔄 بروزرسانی", "infoBtn")
        refresh_btn.clicked.connect(self.load_products)
        toolbar.addWidget(refresh_btn)

        main_layout.addWidget(toolbar_widget)

        # فیلترها
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setSpacing(8)

        filter_layout.addWidget(QLabel("🔍 جستجو:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("کد، نام، برند، مدل...")
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self.load_products)
        filter_layout.addWidget(self.search_input)

        filter_layout.addWidget(QLabel("دسته:"))
        self.category_filter = QComboBox()
        self.category_filter.addItem("همه دسته‌ها", "")
        self.category_filter.currentIndexChanged.connect(self.load_products)
        filter_layout.addWidget(self.category_filter)

        filter_layout.addWidget(QLabel("انبار:"))
        self.warehouse_filter = QComboBox()
        self.warehouse_filter.addItem("همه انبارها", "")
        self.warehouse_filter.currentIndexChanged.connect(self.load_products)
        filter_layout.addWidget(self.warehouse_filter)

        filter_layout.addStretch()

        clear_btn = self.create_button("✖️ پاک کردن", "dangerBtn")
        clear_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_btn)

        main_layout.addWidget(filter_widget)

        # جدول اصلی
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(14)
        self.products_table.setHorizontalHeaderLabels([
            "کد", "نام", "دسته", "برند", "مدل", "سایز", "رنگ", "واحد",
            "موجودی", "انبار", "قیمت خرید", "قیمت فروش", "ارزش", "وضعیت"
        ])
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.setAlternatingRowColors(True)
        self.products_table.horizontalHeader().setStretchLastSection(True)
        self.products_table.clicked.connect(self.on_product_selected)
        self.products_table.doubleClicked.connect(self.edit_product)
        main_layout.addWidget(self.products_table)

        # پنل پایین
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)

        self.status_label = QLabel("✅ آماده")
        self.status_label.setStyleSheet("color: #888; padding: 5px; font-size: 9pt;")
        bottom_layout.addWidget(self.status_label)

        bottom_layout.addStretch()

        self.total_label = QLabel("مجموع کالاها: ۰ | ارزش کل: ۰ ریال")
        self.total_label.setStyleSheet("font-weight: bold; padding: 5px;")
        bottom_layout.addWidget(self.total_label)

        main_layout.addWidget(bottom_widget)

    def load_warehouses(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY code")
            self.warehouses = c.fetchall()

            self.warehouse_filter.clear()
            self.warehouse_filter.addItem("همه انبارها", "")
            for w in self.warehouses:
                self.warehouse_filter.addItem(f"{w['code']} - {w['name']}", w['id'])

            c.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category")
            categories = c.fetchall()
            self.category_filter.clear()
            self.category_filter.addItem("همه دسته‌ها", "")
            for cat in categories:
                self.category_filter.addItem(cat['category'], cat['category'])

    def load_products(self):
        """
        ✅ رفع مشکل: 
        - اگه فیلتر انبار فعال → موجودی همون انبار
        - وگرنه → مجموع همه انبارها
        """
        try:
            warehouse_id = self.warehouse_filter.currentData()
            category = self.category_filter.currentData()
            search = self.search_input.text().strip()

            with get_db() as conn:
                c = conn.cursor()
                
                if warehouse_id:
                    # ✅ حالت فیلتر انبار: فقط موجودی همون انبار
                    query = """
                        SELECT p.*, 
                               w.name as warehouse_name,
                               COALESCE(ws.quantity, 0) as current_stock,
                               COALESCE(ws.quantity, 0) * COALESCE(p.purchase_price, 0) as stock_value
                        FROM products p
                        LEFT JOIN warehouses w ON w.id = ?
                        LEFT JOIN warehouse_stock ws ON p.id = ws.product_id AND ws.warehouse_id = ?
                        WHERE p.is_active = 1
                    """
                    params = [warehouse_id, warehouse_id]
                else:
                    # ✅ حالت همه انبارها: مجموع
                    query = """
                        SELECT p.*, 
                               GROUP_CONCAT(w.name, ' + ') as warehouse_name,
                               COALESCE(SUM(ws.quantity), 0) as current_stock,
                               COALESCE(SUM(ws.quantity * COALESCE(p.purchase_price, 0)), 0) as stock_value
                        FROM products p
                        LEFT JOIN warehouse_stock ws ON p.id = ws.product_id
                        LEFT JOIN warehouses w ON ws.warehouse_id = w.id
                        WHERE p.is_active = 1
                    """
                    params = []

                if category:
                    query += " AND p.category = ?"
                    params.append(category)

                if search:
                    query += " AND (p.code LIKE ? OR p.name LIKE ? OR p.brand LIKE ? OR p.model LIKE ? OR p.barcode LIKE ?)"
                    search_term = f"%{search}%"
                    params.extend([search_term] * 5)

                if not warehouse_id:
                    query += " GROUP BY p.id"

                query += " ORDER BY p.code"
                c.execute(query, params)
                rows = c.fetchall()

                self.products_data = []
                for row in rows:
                    self.products_data.append(dict(row))

            self.display_products()
            self.update_stats()

        except Exception as e:
            print(f"⚠️ خطا در بارگذاری کالاها: {e}")
            import traceback
            traceback.print_exc()
            self.products_data = []
            self.display_products()

    def display_products(self):
        self.products_table.setRowCount(len(self.products_data))
        total_value = 0

        for i, p in enumerate(self.products_data):
            stock = p.get('current_stock', p.get('stock', 0)) or 0
            value = p.get('stock_value', stock * (p.get('purchase_price', 0) or 0))
            total_value += value

            self.products_table.setItem(i, 0, QTableWidgetItem(str(p.get('code', ''))))
            self.products_table.setItem(i, 1, QTableWidgetItem(str(p.get('name', ''))))
            self.products_table.setItem(i, 2, QTableWidgetItem(str(p.get('category', '-'))))
            self.products_table.setItem(i, 3, QTableWidgetItem(str(p.get('brand', '-'))))
            self.products_table.setItem(i, 4, QTableWidgetItem(str(p.get('model', '-'))))
            self.products_table.setItem(i, 5, QTableWidgetItem(str(p.get('size', '-'))))
            self.products_table.setItem(i, 6, QTableWidgetItem(str(p.get('color', '-'))))
            self.products_table.setItem(i, 7, QTableWidgetItem(str(p.get('unit', 'عدد'))))

            stock_item = QTableWidgetItem(f"{stock:,.2f}")
            stock_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if stock <= (p.get('min_stock', 0) or 0) and p.get('min_stock', 0) > 0:
                stock_item.setForeground(QColor('#e84118'))
            self.products_table.setItem(i, 8, stock_item)

            self.products_table.setItem(i, 9, QTableWidgetItem(str(p.get('warehouse_name') or '-')))

            purchase_item = QTableWidgetItem(f"{p.get('purchase_price', 0):,.0f}")
            purchase_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.products_table.setItem(i, 10, purchase_item)

            sale_item = QTableWidgetItem(f"{p.get('sale_price', 0):,.0f}")
            sale_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.products_table.setItem(i, 11, sale_item)

            value_item = QTableWidgetItem(f"{value:,.0f}")
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if value > 0:
                value_item.setForeground(QColor('#27ae60'))
            self.products_table.setItem(i, 12, value_item)

            status_item = QTableWidgetItem("🟢 فعال")
            if stock <= (p.get('min_stock', 0) or 0) and p.get('min_stock', 0) > 0:
                status_item.setText("🔴 موجودی کم")
                status_item.setForeground(QColor('#e84118'))
            elif stock == 0:
                status_item.setText("⚪ ناموجود")
                status_item.setForeground(QColor('#95a5a6'))
            else:
                status_item.setForeground(QColor('#27ae60'))
            self.products_table.setItem(i, 13, status_item)

        self.total_label.setText(f"مجموع کالاها: {len(self.products_data):,} | ارزش کل: {total_value:,.0f} ریال")

    def clear_filters(self):
        self.search_input.clear()
        self.category_filter.setCurrentIndex(0)
        self.warehouse_filter.setCurrentIndex(0)
        self.load_products()

    def update_stats(self):
        total_products = len(self.products_data)
        low_stock = sum(1 for p in self.products_data if (p.get('current_stock', p.get('stock', 0)) or 0) <= (p.get('min_stock', 0) or 0) and p.get('min_stock', 0) > 0)
        self.status_label.setText(f"✅ {total_products} کالا | ⚠️ {low_stock} کالا با موجودی کم")

    def on_product_selected(self):
        row = self.products_table.currentRow()
        if row >= 0 and row < len(self.products_data):
            self.current_product = self.products_data[row]

    def new_product(self):
        dialog = ProductDialog(customer_name=self.customer_name)
        if dialog.exec_():
            self.load_products()
            self.load_warehouses()
            QMessageBox.information(self, "موفق", "✅ کالای جدید ایجاد شد!")

    def edit_product(self):
        row = self.products_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک کالا را انتخاب کنید!")
            return
        product = self.products_data[row]
        dialog = ProductDialog(product['id'], self.customer_name)
        if dialog.exec_():
            self.load_products()
            QMessageBox.information(self, "موفق", "✅ کالا ویرایش شد!")

    def delete_product(self):
        row = self.products_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک کالا را انتخاب کنید!")
            return

        product = self.products_data[row]

        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف '{product['name']}' اطمینان دارید؟\n\n"
            f"⚠️ این عمل قابل بازگشت نیست!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            with get_db() as conn:
                c = conn.cursor()

                # ✅ چک کن کجا استفاده شده
                c.execute("SELECT COUNT(*) FROM stock_transactions WHERE product_id = ?", [product['id']])
                trans_count = c.fetchone()[0]

                c.execute("SELECT COUNT(*) FROM document_items WHERE product_id = ?", [product['id']])
                doc_count = c.fetchone()[0]

                if trans_count > 0 or doc_count > 0:
                    reply2 = QMessageBox.question(
                        self, "امکان حذف کامل نیست",
                        f"⚠️ این کالا قابل حذف کامل نیست!\n\n"
                        f"استفاده شده در:\n"
                        f"• تراکنش‌های انبار: {trans_count:,}\n"
                        f"• فاکتورها: {doc_count:,}\n\n"
                        f"💡 راه‌حل: به جای حذف، غیرفعالش کن.\n\n"
                        f"آیا می‌خواید غیرفعالش کنید؟",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply2 == QMessageBox.Yes:
                        c.execute("UPDATE products SET is_active = 0 WHERE id = ?", [product['id']])
                        conn.commit()
                        self.load_products()
                        QMessageBox.information(self, "موفق", "✅ کالا غیرفعال شد!")
                    return

                # ✅ اگه استفاده نشده → حذف کامل
                c.execute("DELETE FROM warehouse_stock WHERE product_id = ?", [product['id']])
                c.execute("DELETE FROM products WHERE id = ?", [product['id']])
                conn.commit()

            self.load_products()
            QMessageBox.information(self, "موفق", "✅ کالا حذف شد!")

        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در حذف: {e}")

    def stock_transaction(self, trans_type):
        row = self.products_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک کالا را انتخاب کنید!")
            return
        product = self.products_data[row]
        dialog = StockTransactionDialog(product, trans_type)
        if dialog.exec_():
            self.load_products()
            QMessageBox.information(self, "موفق", "✅ تراکنش ثبت شد!")

    def transfer_stock(self):
        row = self.products_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک کالا را انتخاب کنید!")
            return
        product = self.products_data[row]
        dialog = StockTransferDialog(product)
        if dialog.exec_():
            self.load_products()
            QMessageBox.information(self, "موفق", "✅ انتقال انجام شد!")

    def manage_warehouses(self):
        dialog = WarehouseDialog()
        if dialog.exec_():
            self.load_warehouses()
            self.load_products()
            QMessageBox.information(self, "موفق", "✅ انبار مدیریت شد!")

    def export_to_excel(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره خروجی", f"inventory_{datetime.now().strftime('%Y%m%d')}.csv", "CSV Files (*.csv)"
        )
        if not file_name:
            return
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["کد", "نام", "دسته", "برند", "مدل", "سایز", "رنگ", "واحد", "موجودی", "انبار", "قیمت خرید", "قیمت فروش", "ارزش"])
                for p in self.products_data:
                    stock = p.get('current_stock', p.get('stock', 0)) or 0
                    value = p.get('stock_value', stock * (p.get('purchase_price', 0) or 0))
                    writer.writerow([
                        p.get('code', ''),
                        p.get('name', ''),
                        p.get('category', ''),
                        p.get('brand', ''),
                        p.get('model', ''),
                        p.get('size', ''),
                        p.get('color', ''),
                        p.get('unit', 'عدد'),
                        f"{stock:,.2f}",
                        p.get('warehouse_name', ''),
                        f"{p.get('purchase_price', 0):,.0f}",
                        f"{p.get('sale_price', 0):,.0f}",
                        f"{value:,.0f}"
                    ])
            QMessageBox.information(self, "موفق", f"✅ خروجی در {file_name} ذخیره شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")
