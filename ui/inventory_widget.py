# ui/inventory_widget.py
# ============================================================
# ویجت انبارداری پیشرفته ImanAccount — نسخه 10.0
# ============================================================
# تغییرات نسبت به v9.0:
# ✅ اضافه شدن انبارگردانی (Inventory Count)
# ✅ InventoryCountListDialog — لیست اسناد
# ✅ InventoryCountDialog — ایجاد/ویرایش سند
# ✅ چاپ برگه انبارگردانی
# ✅ تأیید سند و اصلاح خودکار موجودی
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from ui.base_widgets import BaseWidget, BaseDialog
from database import get_db, InventoryHelper, safe_display_date, get_today_jalali
from shamsi_date import ShamsiDateEdit
import csv
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


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

        # ✅ موجودی اولیه (فقط برای کالای جدید)
        self.initial_stock = QDoubleSpinBox()
        self.initial_stock.setRange(0, 999999)
        self.initial_stock.setDecimals(2)
        self.initial_stock.setStyleSheet("padding: 8px; border: 2px solid #1976D2; border-radius: 4px;")
        self.initial_stock.setToolTip("فقط برای کالای جدید — موجودی اولیه انبار")
        price_layout.addRow("📦 موجودی اولیه:", self.initial_stock)

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
                
                # ✅ در حالت ویرایش، فیلد موجودی اولیه غیرفعال
                self.initial_stock.setEnabled(False)
                self.initial_stock.setValue(0)
                self.initial_stock.setStyleSheet("padding: 8px; border: 1px solid #ddd; background: #f0f0f0; border-radius: 4px;")
                
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

        warehouse_id = self.warehouse_combo.currentData()
        
        # ✅ اگر کالای جدید و انبار انتخاب نشده، از انبار پیش‌فرض استفاده کن
        if not self.product_id and not warehouse_id:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT id FROM warehouses WHERE is_default = 1 AND is_active = 1 LIMIT 1")
                row = c.fetchone()
                if row:
                    warehouse_id = row['id']
                else:
                    c.execute("SELECT id FROM warehouses WHERE is_active = 1 ORDER BY id LIMIT 1")
                    row = c.fetchone()
                    if row:
                        warehouse_id = row['id']

        try:
            with get_db() as conn:
                c = conn.cursor()
                
                if self.product_id:
                    # ─── ویرایش ───
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
                        warehouse_id, self.product_id
                    ])
                    
                    # ✅ همگام‌سازی
                    InventoryHelper.sync_product_stock(self.product_id, conn=conn)
                    
                else:
                    # ─── ایجاد جدید ───
                    c.execute('''
                        INSERT INTO products (
                            code, name, category, unit, brand, model, color, size,
                            weight, barcode, has_serial, expiry_date, location,
                            purchase_price, sale_price, min_stock, max_stock, 
                            warehouse_id, stock
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [
                        code, self.name.text().strip(), self.category.currentText(),
                        self.unit.currentText(), self.brand.text().strip(),
                        self.model.text().strip(), self.color.text().strip(),
                        self.size.text().strip(), self.weight.value(),
                        self.barcode.text().strip(), 1 if self.has_serial.isChecked() else 0,
                        self.expiry_date.get_shamsi(), self.location.text().strip(),
                        self.purchase_price.value(), self.sale_price.value(),
                        self.min_stock.value(), self.max_stock.value(),
                        warehouse_id, 0  # stock موقتاً صفر
                    ])
                    
                    product_id = c.lastrowid
                    
                    # ✅ اگر موجودی اولیه وارد شده، رکورد warehouse_stock بساز
                    initial_stock = self.initial_stock.value()
                    if initial_stock > 0 and warehouse_id:
                        c.execute('''
                            INSERT INTO warehouse_stock 
                            (product_id, warehouse_id, quantity, updated_at)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ''', [product_id, warehouse_id, initial_stock])
                        
                        # ✅ ثبت تراکنش موجودی اولیه
                        c.execute('''
                            INSERT INTO stock_transactions
                            (date, product_id, warehouse_id, type, quantity,
                             unit_price, total_price, description)
                            VALUES (?, ?, ?, 'in', ?, ?, ?, ?)
                        ''', [
                            get_today_jalali(), product_id, warehouse_id,
                            initial_stock,
                            self.purchase_price.value(),
                            initial_stock * self.purchase_price.value(),
                            'موجودی اولیه'
                        ])
                    
                    # ✅ همگام‌سازی نهایی
                    InventoryHelper.sync_product_stock(product_id, conn=conn)
                
                conn.commit()
            
            super().accept()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {e}")


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
        
        warehouse_id = self.warehouse_combo.currentData()
        if not warehouse_id:
            QMessageBox.warning(self, "خطا", "لطفاً انبار را انتخاب کنید!")
            return

        # ✅ چک موجودی از warehouse_stock
        if self.trans_type == 'out':
            available = InventoryHelper.get_stock(self.product['id'], warehouse_id)
            if self.quantity.value() > available:
                QMessageBox.warning(
                    self, "خطا",
                    f"موجودی انبار کافی نیست!\n"
                    f"موجودی این انبار: {available:,.2f}"
                )
                return

        try:
            with get_db() as conn:
                c = conn.cursor()
                
                # ✅ ۱. به‌روزرسانی موجودی با تابع مرکزی
                InventoryHelper.adjust_stock(
                    self.product['id'],
                    self.quantity.value(),
                    self.trans_type,
                    warehouse_id=warehouse_id,
                    conn=conn
                )
                
                # ✅ ۲. ثبت تراکنش
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
                
                conn.commit()
            
            super().accept()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "خطا", f"❌ خطا در ثبت تراکنش: {e}")


# ============================================================
# دیالوگ انتقال بین انبارها
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

        self.from_warehouse = QComboBox()
        self.from_warehouse.currentIndexChanged.connect(self.update_available_stock)
        layout.addRow("🏢 انبار مبدا:", self.from_warehouse)

        self.available_stock_label = QLabel("موجودی قابل انتقال: ۰")
        self.available_stock_label.setStyleSheet("font-weight: bold; color: #273c75; padding: 5px;")
        layout.addRow(self.available_stock_label)

        self.to_warehouse = QComboBox()
        layout.addRow("🏢 انبار مقصد:", self.to_warehouse)

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

        self.update_available_stock()

    def load_warehouses(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id, code, name FROM warehouses "
                    "WHERE is_active = 1 ORDER BY code"
                )
                rows = c.fetchall()

                if hasattr(self, 'from_warehouse') and self.from_warehouse is not None:
                    self.from_warehouse.blockSignals(True)
                    self.from_warehouse.clear()
                    for row in rows:
                        self.from_warehouse.addItem(
                            f"{row['code']} - {row['name']}", row['id']
                        )
                    self.from_warehouse.blockSignals(False)

                if hasattr(self, 'to_warehouse') and self.to_warehouse is not None:
                    self.to_warehouse.clear()
                    for row in rows:
                        self.to_warehouse.addItem(
                            f"{row['code']} - {row['name']}", row['id']
                        )
                    if len(rows) >= 2:
                        self.to_warehouse.setCurrentIndex(1)

                if len(rows) < 2:
                    QMessageBox.warning(
                        self, "توجه",
                        "⚠️ برای انتقال، حداقل ۲ انبار نیازه!\n\n"
                        "از دکمه «🏢 مدیریت انبارها» یه انبار جدید بساز."
                    )
        except Exception as e:
            print(f"⚠️ خطا در load_warehouses: {e}")

    def update_available_stock(self):
        warehouse_id = self.from_warehouse.currentData()
        if not warehouse_id:
            self.available_stock_label.setText("موجودی قابل انتقال: ۰")
            self.quantity.setEnabled(False)
            return

        try:
            stock = InventoryHelper.get_stock(self.product['id'], warehouse_id)

            self.available_stock_label.setText(
                f"موجودی قابل انتقال: {stock:,.2f} {self.product.get('unit', 'عدد')}"
            )

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

                available = InventoryHelper.get_stock(self.product['id'], from_warehouse_id)

                if available <= 0:
                    QMessageBox.warning(self, "خطا", "موجودی انبار مبدا صفره!")
                    return

                if quantity > available:
                    QMessageBox.warning(
                        self, "خطا",
                        f"موجودی کافی نیست!\n"
                        f"موجودی فعلی: {available:,.2f}\n"
                        f"درخواستی: {quantity:,.2f}"
                    )
                    return

                # ✅ استفاده از تابع مرکزی
                InventoryHelper.adjust_stock(
                    self.product['id'], quantity, 'out',
                    warehouse_id=from_warehouse_id, conn=conn
                )
                
                InventoryHelper.adjust_stock(
                    self.product['id'], quantity, 'in',
                    warehouse_id=to_warehouse_id, conn=conn
                )

                # ثبت تراکنش
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

                conn.commit()

            print(f"✅ انتقال موفق: {quantity} از {from_warehouse_id} به {to_warehouse_id}")
            super().accept()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "خطا", f"❌ خطا در انتقال: {e}")
# ============================================================
# دیالوگ لیست اسناد انبارگردانی
# ============================================================

class InventoryCountListDialog(BaseDialog):
    """دیالوگ لیست اسناد انبارگردانی"""
    
    def __init__(self, parent=None):
        super().__init__(parent, base_width=1100, base_height=700)
        self.setWindowTitle("📋 اسناد انبارگردانی")
        self.setModal(True)
        self.setup_ui()
        self.load_data()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # ─── هدر ───
        header = QHBoxLayout()
        
        title = QLabel("📋 اسناد انبارگردانی")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #273c75;")
        header.addWidget(title)
        
        header.addStretch()
        
        # فیلتر انبار
        header.addWidget(QLabel("انبار:"))
        self.warehouse_filter = QComboBox()
        self.warehouse_filter.addItem("همه انبارها", "")
        self.load_warehouses()
        self.warehouse_filter.currentIndexChanged.connect(self.load_data)
        self.warehouse_filter.setMinimumWidth(150)
        header.addWidget(self.warehouse_filter)
        
        # فیلتر وضعیت
        header.addWidget(QLabel("وضعیت:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("همه", "")
        self.status_filter.addItem("📝 پیش‌نویس", "draft")
        self.status_filter.addItem("✅ تأیید شده", "approved")
        self.status_filter.addItem("❌ لغو شده", "cancelled")
        self.status_filter.currentIndexChanged.connect(self.load_data)
        header.addWidget(self.status_filter)
        
        layout.addLayout(header)
        
        # ─── نوار ابزار ───
        toolbar = QHBoxLayout()
        
        new_btn = QPushButton("➕ سند جدید")
        new_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50; color: white; padding: 10px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background: #388E3C; }
        """)
        new_btn.clicked.connect(self.new_count)
        toolbar.addWidget(new_btn)
        
        open_btn = QPushButton("👁️ مشاهده/ویرایش")
        open_btn.setStyleSheet("""
            QPushButton {
                background: #FF9800; color: white; padding: 10px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background: #E68900; }
        """)
        open_btn.clicked.connect(self.open_count)
        toolbar.addWidget(open_btn)
        
        delete_btn = QPushButton("🗑️ حذف")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c; color: white; padding: 10px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        delete_btn.clicked.connect(self.delete_count)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #3498db; color: white; padding: 10px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        # ─── جدول ───
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "شماره", "تاریخ", "انبار", "تعداد اقلام",
            "اقلام مغایرت‌دار", "ارزش مغایرت", "وضعیت", "ایجادکننده"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 120)
        self.table.setColumnWidth(5, 130)
        self.table.setColumnWidth(6, 120)
        self.table.doubleClicked.connect(self.open_count)
        layout.addWidget(self.table)
        
        # ─── خلاصه ───
        self.summary_label = QLabel("📊 در حال بارگذاری...")
        self.summary_label.setStyleSheet("""
            background: #f0f0f0; padding: 10px; border-radius: 6px;
            font-weight: bold; color: #2c3e50;
        """)
        layout.addWidget(self.summary_label)
        
        # ─── دکمه بستن ───
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("❌ بستن")
        close_btn.setMinimumWidth(120)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #95a5a6; color: white; padding: 10px 20px;
                border: none; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background: #7f8c8d; }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    
    def load_warehouses(self):
        """بارگذاری انبارها"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY code")
            for row in c.fetchall():
                self.warehouse_filter.addItem(
                    f"{row['code']} - {row['name']}", row['id']
                )
    
    def load_data(self):
        """بارگذاری لیست اسناد"""
        try:
            warehouse_id = self.warehouse_filter.currentData()
            status = self.status_filter.currentData()
            
            query = """
                SELECT ic.*, w.name as warehouse_name
                FROM inventory_counts ic
                LEFT JOIN warehouses w ON ic.warehouse_id = w.id
                WHERE 1=1
            """
            params = []
            
            if warehouse_id:
                query += " AND ic.warehouse_id = ?"
                params.append(warehouse_id)
            
            if status:
                query += " AND ic.status = ?"
                params.append(status)
            
            query += " ORDER BY ic.id DESC"
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute(query, params)
                counts = [dict(row) for row in c.fetchall()]
            
            self.table.setRowCount(len(counts))
            
            total_variance = 0
            
            for i, count in enumerate(counts):
                self.table.setItem(i, 0, QTableWidgetItem(count.get('count_no', '')))
                self.table.setItem(i, 1, QTableWidgetItem(
                    safe_display_date(count.get('date', ''))
                ))
                self.table.setItem(i, 2, QTableWidgetItem(
                    count.get('warehouse_name', '-')
                ))
                
                total_items = QTableWidgetItem(str(count.get('total_items', 0)))
                total_items.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 3, total_items)
                
                variance_items = QTableWidgetItem(str(count.get('variance_items', 0)))
                variance_items.setTextAlignment(Qt.AlignCenter)
                if count.get('variance_items', 0) > 0:
                    variance_items.setForeground(QColor('#e74c3c'))
                    variance_items.setFont(QFont("Tahoma", 10, QFont.Bold))
                self.table.setItem(i, 4, variance_items)
                
                var_value = count.get('total_variance_value', 0) or 0
                var_item = QTableWidgetItem(f"{var_value:,.0f}")
                var_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if var_value != 0:
                    var_item.setForeground(
                        QColor('#e74c3c') if var_value > 0 else QColor('#27ae60')
                    )
                self.table.setItem(i, 5, var_item)
                total_variance += abs(var_value)
                
                status_map = {
                    'draft': ('📝 پیش‌نویس', '#f39c12'),
                    'approved': ('✅ تأیید شده', '#27ae60'),
                    'cancelled': ('❌ لغو شده', '#95a5a6'),
                }
                status_text, status_color = status_map.get(
                    count.get('status', 'draft'), ('❓', '#666')
                )
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QColor(status_color))
                status_item.setFont(QFont("Tahoma", 9, QFont.Bold))
                self.table.setItem(i, 6, status_item)
                
                self.table.setItem(i, 7, QTableWidgetItem(
                    count.get('created_by', '-') or '-'
                ))
            
            self.summary_label.setText(
                f"📊 {len(counts)} سند | "
                f"مجموع ارزش مغایرت: {total_variance:,.0f} ریال"
            )
        
        except Exception as e:
            logger.error(f"خطا در بارگذاری: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def new_count(self):
        """ایجاد سند جدید"""
        dialog = InventoryCountDialog(parent=self)
        if dialog.exec_():
            self.load_data()
    
    def open_count(self):
        """باز کردن سند انتخاب‌شده"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        count_no = self.table.item(row, 0).text()
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM inventory_counts WHERE count_no = ?", [count_no])
            row_data = c.fetchone()
            if not row_data:
                return
            count_id = row_data['id']
        
        dialog = InventoryCountDialog(count_id=count_id, parent=self)
        if dialog.exec_():
            self.load_data()
    
    def delete_count(self):
        """حذف سند"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        count_no = self.table.item(row, 0).text()
        status = self.table.item(row, 6).text()
        
        if 'تأیید' in status:
            QMessageBox.warning(
                self, "خطا",
                "❌ اسناد تأییدشده قابل حذف نیستند!\n\n"
                "برای بی‌اثر کردن، سند را لغو کنید."
            )
            return
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف سند {count_no} اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM inventory_counts WHERE count_no = ?", [count_no])
                conn.commit()
            
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ سند حذف شد!")
        
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def apply_theme(self):
        """تم ساده"""
        self.setStyleSheet("""
            QDialog { background: #f5f6fa; }
            QLabel { color: #1a1a2e; }
            QTableWidget {
                background: white; color: #1a1a2e;
                border: 1px solid #dcdde1; border-radius: 6px;
                gridline-color: #dcdde1;
            }
            QTableWidget::item:selected {
                background: #1976D2; color: white;
            }
            QHeaderView::section {
                background: #273c75; color: white;
                padding: 8px; border: none; font-weight: bold;
            }
            QLineEdit, QComboBox {
                background: white; color: #1a1a2e;
                border: 1px solid #dcdde1; border-radius: 6px;
                padding: 6px 10px; min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #1976D2;
            }
        """)


# ============================================================
# دیالوگ ایجاد/ویرایش سند انبارگردانی
# ============================================================

class InventoryCountDialog(BaseDialog):
    """دیالوگ سند انبارگردانی"""
    
    def __init__(self, count_id=None, parent=None):
        super().__init__(parent, base_width=1150, base_height=800)
        self.count_id = count_id
        self.is_new = count_id is None
        self.current_status = 'draft'
        self.items_data = []
        
        if self.is_new:
            self.setWindowTitle("📋 سند انبارگردانی جدید")
        else:
            self.setWindowTitle("📋 ویرایش سند انبارگردانی")
        
        self.setModal(True)
        self.setup_ui()
        
        if self.is_new:
            self.prepare_new()
        else:
            self.load_data()
        
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # ═══════════════════════════════════════════════════
        # اطلاعات سند
        # ═══════════════════════════════════════════════════
        info_group = QGroupBox("📋 اطلاعات سند")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 2px solid #273c75;
                border-radius: 8px; margin-top: 10px;
                padding-top: 15px; background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px;
                padding: 0 10px; color: #273c75;
            }
        """)
        info_layout = QHBoxLayout(info_group)
        info_layout.setSpacing(15)
        
        # شماره سند
        info_layout.addWidget(QLabel("🔢 شماره:"))
        self.count_no_input = QLineEdit()
        self.count_no_input.setReadOnly(True)
        self.count_no_input.setMaximumWidth(150)
        self.count_no_input.setStyleSheet(
            "padding: 8px; background: #f0f0f0; border-radius: 4px; font-weight: bold;"
        )
        info_layout.addWidget(self.count_no_input)
        
        # تاریخ
        info_layout.addWidget(QLabel("📅 تاریخ:"))
        self.date_input = ShamsiDateEdit()
        self.date_input.setMinimumWidth(130)
        info_layout.addWidget(self.date_input)
        
        # انبار
        info_layout.addWidget(QLabel("🏢 انبار:"))
        self.warehouse_combo = QComboBox()
        self.warehouse_combo.setMinimumWidth(200)
        self.warehouse_combo.currentIndexChanged.connect(self.on_warehouse_changed)
        info_layout.addWidget(self.warehouse_combo)
        
        info_layout.addStretch()
        
        # وضعیت
        self.status_label = QLabel("📝 پیش‌نویس")
        self.status_label.setStyleSheet("""
            background: #f39c12; color: white;
            padding: 8px 16px; border-radius: 6px;
            font-weight: bold; font-size: 11pt;
        """)
        info_layout.addWidget(self.status_label)
        
        layout.addWidget(info_group)
        
        # ═══════════════════════════════════════════════════
        # نوار فیلتر
        # ═══════════════════════════════════════════════════
        filter_bar = QHBoxLayout()
        
        filter_bar.addWidget(QLabel("🔍 جستجو:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("کد یا نام کالا...")
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self.filter_items)
        filter_bar.addWidget(self.search_input)
        
        self.show_only_variance = QCheckBox("فقط کالاهای مغایرت‌دار")
        self.show_only_variance.stateChanged.connect(self.filter_items)
        filter_bar.addWidget(self.show_only_variance)
        
        filter_bar.addStretch()
        
        # آمار سریع
        self.quick_stats = QLabel("")
        self.quick_stats.setStyleSheet(
            "color: #666; font-size: 10pt; font-weight: bold;"
        )
        filter_bar.addWidget(self.quick_stats)
        
        layout.addLayout(filter_bar)
        
        # ═══════════════════════════════════════════════════
        # جدول اقلام
        # ═══════════════════════════════════════════════════
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(8)
        self.items_table.setHorizontalHeaderLabels([
            "کد", "نام کالا", "واحد",
            "موجودی سیستم", "موجودی واقعی", "مغایرت",
            "قیمت واحد", "ارزش مغایرت"
        ])
        self.items_table.setAlternatingRowColors(True)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setColumnWidth(0, 100)
        self.items_table.setColumnWidth(1, 250)
        self.items_table.setColumnWidth(2, 70)
        self.items_table.setColumnWidth(3, 120)
        self.items_table.setColumnWidth(4, 130)
        self.items_table.setColumnWidth(5, 110)
        self.items_table.setColumnWidth(6, 120)
        self.items_table.setMinimumHeight(380)
        layout.addWidget(self.items_table)
        
        # ═══════════════════════════════════════════════════
        # خلاصه
        # ═══════════════════════════════════════════════════
        summary_group = QGroupBox("📊 خلاصه")
        summary_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; border: 2px solid #27ae60;
                border-radius: 8px; margin-top: 10px;
                padding-top: 15px; background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px;
                padding: 0 10px; color: #27ae60;
            }
        """)
        summary_layout = QGridLayout(summary_group)
        summary_layout.setSpacing(15)
        
        # تعداد کل
        summary_layout.addWidget(QLabel("📦 تعداد کل کالا:"), 0, 0)
        self.total_items_label = QLabel("0")
        self.total_items_label.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: #273c75;"
        )
        summary_layout.addWidget(self.total_items_label, 0, 1)
        
        # اقلام مغایرت‌دار
        summary_layout.addWidget(QLabel("⚠️ اقلام مغایرت‌دار:"), 0, 2)
        self.variance_items_label = QLabel("0")
        self.variance_items_label.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: #e74c3c;"
        )
        summary_layout.addWidget(self.variance_items_label, 0, 3)
        
        # کمبود
        summary_layout.addWidget(QLabel("📉 کمبود (خروج):"), 1, 0)
        self.shortage_label = QLabel("0 ریال")
        self.shortage_label.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: #e74c3c;"
        )
        summary_layout.addWidget(self.shortage_label, 1, 1)
        
        # اضافه
        summary_layout.addWidget(QLabel("📈 اضافه (ورود):"), 1, 2)
        self.surplus_label = QLabel("0 ریال")
        self.surplus_label.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: #27ae60;"
        )
        summary_layout.addWidget(self.surplus_label, 1, 3)
        
        summary_layout.setColumnStretch(4, 1)
        layout.addWidget(summary_group)
        
        # ═══════════════════════════════════════════════════
        # دکمه‌ها
        # ═══════════════════════════════════════════════════
        btn_layout = QHBoxLayout()
        
        print_btn = QPushButton("🖨️ چاپ برگه")
        print_btn.setStyleSheet("""
            QPushButton {
                background: #3498db; color: white; padding: 12px 24px;
                border: none; border-radius: 6px; font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        print_btn.clicked.connect(self.print_sheet)
        btn_layout.addWidget(print_btn)
        
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("💾 ذخیره")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50; color: white; padding: 12px 24px;
                border: none; border-radius: 6px; font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background: #388E3C; }
        """)
        self.save_btn.clicked.connect(self.save_draft)
        btn_layout.addWidget(self.save_btn)
        
        self.approve_btn = QPushButton("✅ تأیید و اصلاح موجودی")
        self.approve_btn.setStyleSheet("""
            QPushButton {
                background: #e94560; color: white; padding: 12px 24px;
                border: none; border-radius: 6px; font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        self.approve_btn.clicked.connect(self.approve_and_apply)
        btn_layout.addWidget(self.approve_btn)
        
        cancel_btn = QPushButton("❌ بستن")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #95a5a6; color: white; padding: 12px 24px;
                border: none; border-radius: 6px; font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background: #7f8c8d; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    # ═══════════════════════════════════════════════════════
    # آماده‌سازی سند جدید
    # ═══════════════════════════════════════════════════════
    
    def prepare_new(self):
        """آماده‌سازی سند جدید"""
        self.count_no_input.setText(self._generate_count_no())
        self.date_input.set_date(get_today_jalali())
        self._load_warehouses()
    
    def _generate_count_no(self) -> str:
        """تولید شماره سند بعدی"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT MAX(CAST(SUBSTR(count_no, 5) AS INTEGER))
                FROM inventory_counts WHERE count_no LIKE 'INV-%'
            """)
            max_no = c.fetchone()[0] or 0
            return f"INV-{(max_no + 1):05d}"
    
    def _load_warehouses(self):
        """بارگذاری انبارها"""
        self.warehouse_combo.blockSignals(True)
        self.warehouse_combo.clear()
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, code, name, is_default
                FROM warehouses WHERE is_active = 1 ORDER BY code
            """)
            rows = c.fetchall()
            
            default_idx = -1
            for i, row in enumerate(rows):
                self.warehouse_combo.addItem(
                    f"{row['code']} - {row['name']}", row['id']
                )
                if row['is_default']:
                    default_idx = i
            
            if default_idx >= 0:
                self.warehouse_combo.setCurrentIndex(default_idx)
        
        self.warehouse_combo.blockSignals(False)
        
        if self.warehouse_combo.count() > 0:
            self.on_warehouse_changed()
    
    def on_warehouse_changed(self):
        """وقتی انبار تغییر کرد"""
        if self.is_new:
            self.load_items_for_count()
    
    # ═══════════════════════════════════════════════════════
    # بارگذاری اقلام
    # ═══════════════════════════════════════════════════════
    
    def load_items_for_count(self):
        """بارگذاری کالاهای موجود در انبار"""
        warehouse_id = self.warehouse_combo.currentData()
        if not warehouse_id:
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute("""
                    SELECT 
                        p.id, p.code, p.name, p.unit,
                        COALESCE(ws.quantity, 0) as system_qty,
                        COALESCE(p.purchase_price, 0) as unit_price
                    FROM products p
                    LEFT JOIN warehouse_stock ws 
                        ON p.id = ws.product_id AND ws.warehouse_id = ?
                    WHERE p.is_active = 1
                    ORDER BY p.code
                """, [warehouse_id])
                
                self.items_data = []
                for row in c.fetchall():
                    self.items_data.append({
                        'product_id': row['id'],
                        'code': row['code'],
                        'name': row['name'],
                        'unit': row['unit'] or 'عدد',
                        'system_qty': float(row['system_qty'] or 0),
                        'actual_qty': float(row['system_qty'] or 0),
                        'unit_price': float(row['unit_price'] or 0),
                        'counted': 0,
                        'notes': '',
                    })
            
            self.render_table()
        
        except Exception as e:
            logger.error(f"خطا در بارگذاری اقلام: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def render_table(self):
        """رندر جدول اقلام"""
        self.items_table.blockSignals(True)
        self.items_table.setRowCount(0)
        
        search_text = self.search_input.text().strip().lower()
        only_variance = self.show_only_variance.isChecked()
        
        visible_items = []
        for item in self.items_data:
            if search_text:
                if search_text not in item['code'].lower() and \
                   search_text not in item['name'].lower():
                    continue
            
            if only_variance:
                variance = item['actual_qty'] - item['system_qty']
                if abs(variance) < 0.001:
                    continue
            
            visible_items.append(item)
        
        self.items_table.setRowCount(len(visible_items))
        
        for i, item in enumerate(visible_items):
            # ─── کد ───
            code_item = QTableWidgetItem(item['code'])
            code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(i, 0, code_item)
            
            # ─── نام ───
            name_item = QTableWidgetItem(item['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(i, 1, name_item)
            
            # ─── واحد ───
            unit_item = QTableWidgetItem(item['unit'])
            unit_item.setFlags(unit_item.flags() & ~Qt.ItemIsEditable)
            unit_item.setTextAlignment(Qt.AlignCenter)
            self.items_table.setItem(i, 2, unit_item)
            
            # ─── موجودی سیستم ───
            sys_item = QTableWidgetItem(f"{item['system_qty']:,.2f}")
            sys_item.setFlags(sys_item.flags() & ~Qt.ItemIsEditable)
            sys_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            sys_item.setForeground(QColor('#666'))
            self.items_table.setItem(i, 3, sys_item)
            
            # ─── موجودی واقعی (قابل ویرایش) ───
            actual_widget = QDoubleSpinBox()
            actual_widget.setRange(0, 9999999)
            actual_widget.setDecimals(2)
            actual_widget.setValue(item['actual_qty'])
            actual_widget.setStyleSheet("""
                QDoubleSpinBox {
                    background: #fff9e6;
                    border: 2px solid #f39c12;
                    border-radius: 4px;
                    padding: 4px;
                    font-weight: bold;
                    min-height: 28px;
                }
                QDoubleSpinBox:focus {
                    background: #fff3cd;
                    border-color: #e67e22;
                }
            """)
            actual_widget.valueChanged.connect(
                lambda v, idx=i, it=item: self._on_actual_changed(idx, v, it)
            )
            self.items_table.setCellWidget(i, 4, actual_widget)
            
            # ─── مغایرت ───
            variance = item['actual_qty'] - item['system_qty']
            var_item = QTableWidgetItem(f"{variance:+,.2f}")
            var_item.setFlags(var_item.flags() & ~Qt.ItemIsEditable)
            var_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            var_item.setFont(QFont("Tahoma", 10, QFont.Bold))
            if abs(variance) < 0.001:
                var_item.setForeground(QColor('#95a5a6'))
            elif variance < 0:
                var_item.setForeground(QColor('#e74c3c'))
            else:
                var_item.setForeground(QColor('#27ae60'))
            self.items_table.setItem(i, 5, var_item)
            
            # ─── قیمت واحد ───
            price_item = QTableWidgetItem(f"{item['unit_price']:,.0f}")
            price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(i, 6, price_item)
            
            # ─── ارزش مغایرت ───
            var_value = variance * item['unit_price']
            value_item = QTableWidgetItem(
                f"{var_value:+,.0f}" if abs(var_value) > 0.5 else "-"
            )
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if abs(var_value) > 0.5:
                value_item.setForeground(
                    QColor('#27ae60') if var_value > 0 else QColor('#e74c3c')
                )
            self.items_table.setItem(i, 7, value_item)
        
        self.items_table.blockSignals(False)
        self._update_summary()
    
    def _on_actual_changed(self, row: int, value: float, item: dict):
        """وقتی موجودی واقعی تغییر کرد"""
        item['actual_qty'] = value
        item['counted'] = 1
        
        variance = value - item['system_qty']
        
        var_item = self.items_table.item(row, 5)
        if var_item:
            var_item.setText(f"{variance:+,.2f}")
            if abs(variance) < 0.001:
                var_item.setForeground(QColor('#95a5a6'))
            elif variance < 0:
                var_item.setForeground(QColor('#e74c3c'))
            else:
                var_item.setForeground(QColor('#27ae60'))
        
        var_value = variance * item['unit_price']
        value_item = self.items_table.item(row, 7)
        if value_item:
            value_item.setText(
                f"{var_value:+,.0f}" if abs(var_value) > 0.5 else "-"
            )
            if abs(var_value) > 0.5:
                value_item.setForeground(
                    QColor('#27ae60') if var_value > 0 else QColor('#e74c3c')
                )
            else:
                value_item.setForeground(QColor('#1a1a2e'))
        
        self._update_summary()
    
    def filter_items(self):
        """فیلتر اقلام"""
        self.render_table()
    
    def _update_summary(self):
        """به‌روزرسانی خلاصه"""
        total_items = len(self.items_data)
        variance_items = 0
        shortage_value = 0.0
        surplus_value = 0.0
        
        for item in self.items_data:
            variance = item['actual_qty'] - item['system_qty']
            if abs(variance) >= 0.001:
                variance_items += 1
            
            var_value = variance * item['unit_price']
            if var_value > 0:
                surplus_value += var_value
            elif var_value < 0:
                shortage_value += abs(var_value)
        
        self.total_items_label.setText(str(total_items))
        self.variance_items_label.setText(str(variance_items))
        self.shortage_label.setText(f"{shortage_value:,.0f} ریال")
        self.surplus_label.setText(f"{surplus_value:,.0f} ریال")
        
        if variance_items > 0:
            self.quick_stats.setText(
                f"⚠️ {variance_items} قلم مغایرت | "
                f"📉 {shortage_value:,.0f} | "
                f"📈 {surplus_value:,.0f}"
            )
            self.quick_stats.setStyleSheet(
                "color: #e74c3c; font-size: 10pt; font-weight: bold;"
            )
        else:
            self.quick_stats.setText("✅ همه اقلام مطابق")
            self.quick_stats.setStyleSheet(
                "color: #27ae60; font-size: 10pt; font-weight: bold;"
            )
    
    # ═══════════════════════════════════════════════════════
    # بارگذاری سند موجود
    # ═══════════════════════════════════════════════════════
    
    def load_data(self):
        """بارگذاری سند موجود"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute("SELECT * FROM inventory_counts WHERE id = ?", [self.count_id])
                count = c.fetchone()
                if not count:
                    QMessageBox.warning(self, "خطا", "سند یافت نشد!")
                    self.reject()
                    return
                
                count = dict(count)
                self.current_status = count.get('status', 'draft')
                
                self.count_no_input.setText(count.get('count_no', ''))
                if count.get('date'):
                    self.date_input.set_date(count['date'])
                
                self._load_warehouses()
                
                idx = self.warehouse_combo.findData(count.get('warehouse_id'))
                if idx >= 0:
                    self.warehouse_combo.setCurrentIndex(idx)
                self.warehouse_combo.setEnabled(False)
                
                c.execute("""
                    SELECT ici.*, p.code, p.name, p.unit
                    FROM inventory_count_items ici
                    JOIN products p ON ici.product_id = p.id
                    WHERE ici.count_id = ?
                    ORDER BY p.code
                """, [self.count_id])
                
                self.items_data = []
                for row in c.fetchall():
                    r = dict(row)
                    self.items_data.append({
                        'product_id': r['product_id'],
                        'code': r['code'],
                        'name': r['name'],
                        'unit': r['unit'] or 'عدد',
                        'system_qty': float(r['system_qty'] or 0),
                        'actual_qty': float(r['actual_qty'] or 0),
                        'unit_price': float(r['unit_price'] or 0),
                        'counted': r.get('counted', 0),
                        'notes': r.get('notes', ''),
                    })
                
                self.render_table()
                self._update_status_ui()
            
            if self.current_status != 'draft':
                self._lock_ui()
        
        except Exception as e:
            logger.error(f"خطا در بارگذاری: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def _update_status_ui(self):
        """به‌روزرسانی UI بر اساس وضعیت"""
        status_map = {
            'draft': ('📝 پیش‌نویس', '#f39c12'),
            'approved': ('✅ تأیید شده', '#27ae60'),
            'cancelled': ('❌ لغو شده', '#95a5a6'),
        }
        text, color = status_map.get(self.current_status, ('❓', '#666'))
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"""
            background: {color}; color: white;
            padding: 8px 16px; border-radius: 6px;
            font-weight: bold; font-size: 11pt;
        """)
    
    def _lock_ui(self):
        """قفل کردن UI برای اسناد تأییدشده"""
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for i in range(self.items_table.rowCount()):
            w = self.items_table.cellWidget(i, 4)
            if w:
                w.setEnabled(False)
        
        self.save_btn.setEnabled(False)
        self.approve_btn.setEnabled(False)
    
    # ═══════════════════════════════════════════════════════
    # ذخیره پیش‌نویس
    # ═══════════════════════════════════════════════════════
    
    def save_draft(self):
        """ذخیره سند به‌صورت پیش‌نویس"""
        if self.current_status != 'draft':
            QMessageBox.warning(self, "خطا", "فقط پیش‌نویس قابل ذخیره است!")
            return
        
        warehouse_id = self.warehouse_combo.currentData()
        if not warehouse_id:
            QMessageBox.warning(self, "خطا", "انبار را انتخاب کنید!")
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                count_no = self.count_no_input.text().strip()
                date = self.date_input.get_shamsi()
                
                variance_items = sum(
                    1 for item in self.items_data
                    if abs(item['actual_qty'] - item['system_qty']) >= 0.001
                )
                total_variance_value = sum(
                    (item['actual_qty'] - item['system_qty']) * item['unit_price']
                    for item in self.items_data
                )
                
                if self.is_new:
                    c.execute("""
                        INSERT INTO inventory_counts 
                        (count_no, warehouse_id, date, status, 
                         total_items, counted_items, variance_items, 
                         total_variance_value, created_by)
                        VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?)
                    """, [
                        count_no, warehouse_id, date,
                        len(self.items_data),
                        sum(1 for item in self.items_data if item.get('counted')),
                        variance_items,
                        int(total_variance_value),
                        'کاربر'
                    ])
                    self.count_id = c.lastrowid
                    self.is_new = False
                else:
                    c.execute("""
                        UPDATE inventory_counts 
                        SET total_items = ?, counted_items = ?,
                            variance_items = ?, total_variance_value = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, [
                        len(self.items_data),
                        sum(1 for item in self.items_data if item.get('counted')),
                        variance_items,
                        int(total_variance_value),
                        self.count_id
                    ])
                    
                    c.execute("DELETE FROM inventory_count_items WHERE count_id = ?",
                             [self.count_id])
                
                for item in self.items_data:
                    variance = item['actual_qty'] - item['system_qty']
                    variance_value = variance * item['unit_price']
                    
                    c.execute("""
                        INSERT INTO inventory_count_items 
                        (count_id, product_id, system_qty, actual_qty,
                         variance, unit_price, variance_value, notes, counted)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        self.count_id, item['product_id'],
                        item['system_qty'], item['actual_qty'],
                        variance, item['unit_price'], variance_value,
                        item.get('notes', ''), item.get('counted', 0)
                    ])
                
                conn.commit()
            
            QMessageBox.information(
                self, "موفق",
                f"✅ سند پیش‌نویس ذخیره شد!\n\n"
                f"شماره: {count_no}\n"
                f"اقلام مغایرت‌دار: {variance_items}\n"
                f"ارزش مغایرت: {total_variance_value:,.0f} ریال"
            )
            
            self.setWindowTitle(f"📋 ویرایش سند {count_no}")
        
        except Exception as e:
            logger.error(f"خطا در ذخیره: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    # ═══════════════════════════════════════════════════════
    # تأیید و اصلاح موجودی
    # ═══════════════════════════════════════════════════════
    
    def approve_and_apply(self):
        """تأیید سند و اصلاح موجودی"""
        if self.is_new:
            QMessageBox.warning(
                self, "خطا",
                "ابتدا سند را ذخیره کنید (دکمه 💾 ذخیره)، سپس تأیید کنید."
            )
            return
        
        if self.current_status != 'draft':
            QMessageBox.warning(self, "خطا", "فقط پیش‌نویس قابل تأیید است!")
            return
        
        variance_items = [
            item for item in self.items_data
            if abs(item['actual_qty'] - item['system_qty']) >= 0.001
        ]
        
        if not variance_items:
            reply = QMessageBox.question(
                self, "تأیید",
                "هیچ مغایرتی وجود ندارد. آیا سند را تأیید می‌کنید؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        else:
            total_shortage = sum(
                abs((item['actual_qty'] - item['system_qty']) * item['unit_price'])
                for item in variance_items
                if item['actual_qty'] < item['system_qty']
            )
            total_surplus = sum(
                (item['actual_qty'] - item['system_qty']) * item['unit_price']
                for item in variance_items
                if item['actual_qty'] > item['system_qty']
            )
            
            msg = (
                f"⚠️ تأیید سند انبارگردانی\n\n"
                f"تعداد اقلام مغایرت‌دار: {len(variance_items)}\n"
                f"📉 ارزش کمبود: {total_shortage:,.0f} ریال\n"
                f"📈 ارزش اضافه: {total_surplus:,.0f} ریال\n\n"
                f"⚠️ با تأیید، موجودی سیستم اصلاح می‌شود.\n"
                f"این عمل قابل بازگشت نیست!\n\n"
                f"آیا مطمئن هستید؟"
            )
            
            reply = QMessageBox.warning(
                self, "تأیید نهایی",
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                warehouse_id = self.warehouse_combo.currentData()
                date = self.date_input.get_shamsi()
                
                for item in self.items_data:
                    variance = item['actual_qty'] - item['system_qty']
                    
                    if abs(variance) < 0.001:
                        continue
                    
                    transaction_type = 'in' if variance > 0 else 'out'
                    
                    InventoryHelper.adjust_stock(
                        product_id=item['product_id'],
                        quantity=abs(variance),
                        transaction_type=transaction_type,
                        warehouse_id=warehouse_id,
                        conn=conn
                    )
                    
                    c.execute("""
                        INSERT INTO stock_transactions 
                        (date, product_id, warehouse_id, type, quantity,
                         unit_price, total_price, description)
                        VALUES (?, ?, ?, 'adjustment', ?, ?, ?, ?)
                    """, [
                        date, item['product_id'], warehouse_id,
                        abs(variance), item['unit_price'],
                        abs(variance) * item['unit_price'],
                        f"اصلاح انبارگردانی {self.count_no_input.text()}"
                    ])
                
                c.execute("""
                    UPDATE inventory_counts
                    SET status = 'approved',
                        approved_by = 'کاربر',
                        approved_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, [self.count_id])
                
                conn.commit()
            
            self.current_status = 'approved'
            self._update_status_ui()
            self._lock_ui()
            
            QMessageBox.information(
                self, "موفق",
                f"✅ سند تأیید شد و موجودی اصلاح گردید!\n\n"
                f"تعداد اقلام اصلاح‌شده: {len(variance_items)}"
            )
            
            self._update_summary()
        
        except Exception as e:
            logger.error(f"خطا در تأیید: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    # ═══════════════════════════════════════════════════════
    # چاپ برگه انبارگردانی
    # ═══════════════════════════════════════════════════════
    
    def print_sheet(self):
        """چاپ برگه انبارگردانی"""
        try:
            html = self._generate_print_html()
            
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
            
            preview = QPrintPreviewDialog(printer, self)
            preview.paintRequested.connect(
                lambda p: self._print_preview(p, html)
            )
            preview.exec_()
        
        except Exception as e:
            logger.error(f"خطا در چاپ: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def _print_preview(self, printer, html):
        doc = QTextDocument()
        doc.setHtml(html)
        doc.print_(printer)
    
    def _generate_print_html(self) -> str:
        """تولید HTML برگه انبارگردانی"""
        count_no = self.count_no_input.text()
        date = self.date_input.get_shamsi()
        warehouse_name = self.warehouse_combo.currentText()
        
        status_text = 'پیش‌نویس' if self.current_status == 'draft' else 'تأیید شده'
        
        html = f"""
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Tahoma, sans-serif;
                direction: rtl;
                padding: 15px;
                color: #2c3e50;
                font-size: 10pt;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #273c75;
                padding-bottom: 10px;
                margin-bottom: 15px;
            }}
            .title {{
                font-size: 16pt;
                font-weight: bold;
                color: #273c75;
            }}
            .subtitle {{
                font-size: 12pt;
                color: #2c3e50;
                margin-top: 5px;
            }}
            .info {{
                padding: 10px;
                background: #f8f9fa;
                border-radius: 6px;
                margin-bottom: 15px;
            }}
            .info table {{
                width: 100%;
            }}
            .info td {{
                padding: 5px;
                font-size: 11pt;
            }}
            table.items {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            table.items th {{
                background-color: #273c75;
                color: white;
                padding: 8px 5px;
                text-align: center;
                font-size: 10pt;
                border: 1px solid #1a252f;
            }}
            table.items td {{
                border: 1px solid #ccc;
                padding: 8px 5px;
                text-align: center;
                font-size: 10pt;
                height: 25px;
            }}
            .empty-cell {{
                background: #fffbea;
            }}
            .footer {{
                margin-top: 20px;
                text-align: center;
                font-size: 9pt;
                color: #666;
                border-top: 1px solid #ddd;
                padding-top: 10px;
            }}
            .sig-box {{
                margin-top: 40px;
                width: 100%;
            }}
            .sig-box table {{
                width: 100%;
            }}
            .sig-item {{
                width: 33%;
                text-align: center;
                font-size: 10pt;
                vertical-align: bottom;
            }}
            .sig-line {{
                border-bottom: 1px solid #666;
                height: 40px;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <div class="title">📋 برگه انبارگردانی</div>
                <div class="subtitle">شماره سند: {count_no}</div>
            </div>
            
            <div class="info">
                <table>
                    <tr>
                        <td><b>📅 تاریخ:</b> {date}</td>
                        <td><b>🏢 انبار:</b> {warehouse_name}</td>
                        <td><b>📝 وضعیت:</b> {status_text}</td>
                    </tr>
                </table>
            </div>
            
            <table class="items">
                <thead>
                    <tr>
                        <th style="width: 6%;">ردیف</th>
                        <th style="width: 15%;">کد کالا</th>
                        <th style="width: 30%;">نام کالا</th>
                        <th style="width: 10%;">واحد</th>
                        <th style="width: 13%;">موجودی سیستم</th>
                        <th style="width: 13%;">موجودی واقعی</th>
                        <th style="width: 13%;">مغایرت</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for i, item in enumerate(self.items_data, 1):
            variance = item['actual_qty'] - item['system_qty']
            
            if abs(variance) < 0.001:
                var_text = "-"
                var_style = "color: #999;"
            elif variance < 0:
                var_text = f"{variance:+,.2f}"
                var_style = "color: #e74c3c; font-weight: bold;"
            else:
                var_text = f"{variance:+,.2f}"
                var_style = "color: #27ae60; font-weight: bold;"
            
            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{item['code']}</td>
                    <td style="text-align: right; padding-right: 15px;">{item['name']}</td>
                    <td>{item['unit']}</td>
                    <td style="background: #f0f0f0;">{item['system_qty']:,.2f}</td>
                    <td class="empty-cell">{item['actual_qty']:,.2f}</td>
                    <td style="{var_style}">{var_text}</td>
                </tr>
            """
        
        html += f"""
                </tbody>
            </table>
            
            <div class="sig-box">
                <table>
                    <tr>
                        <td class="sig-item">
                            <div class="sig-line"></div>
                            شمارش‌کننده
                        </td>
                        <td class="sig-item">
                            <div class="sig-line"></div>
                            مسئول انبار
                        </td>
                        <td class="sig-item">
                            <div class="sig-line"></div>
                            تأییدکننده
                        </td>
                    </tr>
                </table>
            </div>
            
            <div class="footer">
                تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')} | ImanAccount
            </div>
        </body>
        </html>
        """
        
        return html
    
    # ═══════════════════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════════════════
    
    def apply_theme(self):
        self.setStyleSheet("""
            QDialog { background: #f5f6fa; }
            QLabel { color: #1a1a2e; }
            QLineEdit, QComboBox {
                background: white; color: #1a1a2e;
                border: 1px solid #dcdde1; border-radius: 6px;
                padding: 6px 10px; min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #1976D2;
            }
            QLineEdit[readOnly="true"] {
                background: #f0f0f0;
            }
            QTableWidget {
                background: white; color: #1a1a2e;
                border: 1px solid #dcdde1; border-radius: 6px;
                gridline-color: #dcdde1;
            }
            QTableWidget::item:selected {
                background: #1976D2; color: white;
            }
            QHeaderView::section {
                background: #273c75; color: white;
                padding: 8px; border: none; font-weight: bold;
            }
            QCheckBox {
                color: #1a1a2e; padding: 5px; spacing: 8px;
            }
        """)


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
        methods = {
            'simple': 'ساده', 'fifo': 'FIFO',
            'lifo': 'LIFO', 'weighted_average': 'میانگین موزون'
        }
        return methods.get(self.valuation_method, 'ساده')

    def set_user_level(self, level: str):
        self.user_level = level
        self.update_ui_by_permission()

    def update_ui_by_permission(self):
        can_edit = self.user_level in ['admin', 'inventory']
        for btn_name in [
            'new_btn', 'edit_btn', 'delete_btn',
            'stock_in_btn', 'stock_out_btn', 'transfer_btn',
            'count_btn'  # ✅ دکمه انبارگردانی
        ]:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setVisible(can_edit)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

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

        # ✅ دکمه انبارگردانی
        self.count_btn = self.create_button("📋 انبارگردانی", "warningBtn")
        self.count_btn.setToolTip("شمارش فیزیکی موجودی و اصلاح مغایرت‌ها")
        self.count_btn.clicked.connect(self.open_inventory_count)
        toolbar.addWidget(self.count_btn)

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

        # جدول
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
        try:
            warehouse_id = self.warehouse_filter.currentData()
            category = self.category_filter.currentData()
            search = self.search_input.text().strip()

            with get_db() as conn:
                c = conn.cursor()
                
                if warehouse_id:
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

                self.products_data = [dict(row) for row in rows]

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

        self.total_label.setText(
            f"مجموع کالاها: {len(self.products_data):,} | "
            f"ارزش کل: {total_value:,.0f} ریال"
        )

    def clear_filters(self):
        self.search_input.clear()
        self.category_filter.setCurrentIndex(0)
        self.warehouse_filter.setCurrentIndex(0)
        self.load_products()

    def update_stats(self):
        total_products = len(self.products_data)
        low_stock = sum(
            1 for p in self.products_data 
            if (p.get('current_stock', p.get('stock', 0)) or 0) <= (p.get('min_stock', 0) or 0) 
            and p.get('min_stock', 0) > 0
        )
        self.status_label.setText(
            f"✅ {total_products} کالا | ⚠️ {low_stock} کالا با موجودی کم"
        )

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

                c.execute("SELECT COUNT(*) FROM stock_transactions WHERE product_id = ?",
                         [product['id']])
                trans_count = c.fetchone()[0]

                c.execute("SELECT COUNT(*) FROM document_items WHERE product_id = ?",
                         [product['id']])
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
                        c.execute("UPDATE products SET is_active = 0 WHERE id = ?",
                                 [product['id']])
                        conn.commit()
                        self.load_products()
                        QMessageBox.information(self, "موفق", "✅ کالا غیرفعال شد!")
                    return

                c.execute("DELETE FROM warehouse_stock WHERE product_id = ?",
                         [product['id']])
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

    # ✅ متد انبارگردانی
    def open_inventory_count(self):
        """باز کردن دیالوگ لیست اسناد انبارگردانی"""
        dialog = InventoryCountListDialog(parent=self)
        dialog.exec_()
        # بعد از بستن، موجودی‌ها را بروزرسانی کن
        self.load_products()

    def export_to_excel(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره خروجی",
            f"inventory_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        if not file_name:
            return
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "کد", "نام", "دسته", "برند", "مدل", "سایز", "رنگ", "واحد",
                    "موجودی", "انبار", "قیمت خرید", "قیمت فروش", "ارزش"
                ])
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


# ============================================================
# تست
# ============================================================

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from database import DatabaseManager
    
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    
    # راه‌اندازی دیتابیس
    DatabaseManager.init_db()
    
    # نمایش ویجت
    widget = InventoryWidget(user_level='admin')
    widget.resize(1200, 750)
    widget.setWindowTitle("📦 انبارداری ImanAccount — تست")
    widget.show()
    
    sys.exit(app.exec_())            
