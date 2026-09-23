#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
purchase_widget.py - ویجت مدیریت فاکتورهای خرید
نسخه کامل با پشتیبانی از:
- فارسی (arabic_reshaper + bidi)
- اطلاعات شرکت از تنظیمات
- نرخ مالیات پویا از تنظیمات
- قالب تصویری فاکتور
- چاپ مستقیم و PDF
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from database import get_db, InventoryHelper, ModuleLimitHelper
from shamsi_date import ShamsiDateEdit, safe_display_date
import os
import re
from datetime import datetime

# ========== پشتیبانی از فارسی ==========
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    PERSIAN_SUPPORT = True
except ImportError:
    PERSIAN_SUPPORT = False
    print("⚠️ کتابخانه‌های فارسی نصب نیستند.")
    print("   برای نصب: pip install python-bidi arabic-reshaper")

def reshape_persian_text(text):
    """
    تبدیل متن فارسی به شکل صحیح برای نمایش در PDF
    فقط حروف فارسی رو بازسازی میکنه و اعداد و علائم رو حفظ میکنه
    """
    if not text:
        return ""
    if not PERSIAN_SUPPORT:
        return str(text)
    try:
        text_str = str(text)
        
        # جدا کردن اعداد و حروف انگلیسی از متن
        parts = re.split(r'([0-9]+|[a-zA-Z]+)', text_str)
        result = []
        
        for part in parts:
            if part.isdigit() or (part.isalpha() and part.isascii()):
                result.append(part)
            else:
                try:
                    if part.strip():
                        reshaped = arabic_reshaper.reshape(part)
                        result.append(reshaped)
                    else:
                        result.append(part)
                except:
                    result.append(part)
        
        final_text = ''.join(result)
        return get_display(final_text)
        
    except Exception as e:
        print(f"⚠️ خطا در reshape: {e}")
        return str(text)

# ========== Import برای PDF ==========
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from PIL import Image
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ ReportLab یا PIL نصب نیست. برای چاپ PDF: pip install reportlab pillow")


class PurchaseWidget(QWidget):
    """ویجت مدیریت فاکتورهای خرید"""
    
    def __init__(self, customer_name=""):
        super().__init__()
        self.customer_name = customer_name
        self.orders_data = []
        self.products = []
        self.suppliers = []
        self.current_order = None
        self.init_ui()
        self.load_data()
    
    def get_company_info(self):
        """دریافت اطلاعات شرکت از دیتابیس"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT key, value FROM settings WHERE key LIKE 'company_%'")
                rows = c.fetchall()
                info = {}
                for row in rows:
                    info[row['key']] = row['value']
                
                # اگر اطلاعاتی نبود، از پیش‌فرض استفاده کن
                if not info or not info.get('company_name'):
                    info = {
                        'company_name': 'شرکت حسابداری پارسه',
                        'company_economic': '1234567890',
                        'company_phone': '021-12345678',
                        'company_address': 'تهران، خیابان اصلی، پلاک 123'
                    }
                return info
        except Exception as e:
            print(f"⚠️ خطا در دریافت اطلاعات شرکت: {e}")
            return {
                'company_name': 'شرکت حسابداری پارسه',
                'company_economic': '1234567890',
                'company_phone': '021-12345678',
                'company_address': 'تهران، خیابان اصلی، پلاک 123'
            }
    
    def get_tax_rate(self):
        """دریافت نرخ مالیات از دیتابیس"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'tax_rate'")
                row = c.fetchone()
                if row:
                    return float(row[0]) / 100
                return 0.09
        except Exception as e:
            print(f"⚠️ خطا در دریافت نرخ مالیات: {e}")
            return 0.09
    
    def get_template_info(self):
        """دریافت اطلاعات قالب فاکتور از دیتابیس"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT key, value FROM settings WHERE key IN ('template_path', 'template_position', 'template_opacity')")
                rows = c.fetchall()
                info = {}
                for row in rows:
                    info[row['key']] = row['value']
                return info
        except Exception as e:
            print(f"⚠️ خطا در دریافت اطلاعات قالب: {e}")
            return {}
    
    def check_purchase_limit(self):
        if self.customer_name:
            allowed, current, limit, msg = ModuleLimitHelper.check_module_limit(self.customer_name, 'purchase')
            if not allowed:
                QMessageBox.warning(self, "خطا", f"❌ به سقف مجاز {limit} فاکتور خرید رسیده‌اید!")
                return False
        return True
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        
        # ========== پنل راست (لیست اسناد) ==========
        right_panel = QWidget()
        right_panel.setStyleSheet("background: white; border-radius: 8px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        
        title = QLabel("📥 فاکتورهای خرید")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px; color: #2C3E50;")
        right_layout.addWidget(title)
        
        toolbar = QHBoxLayout()
        
        new_btn = QPushButton("➕ فاکتور جدید")
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        new_btn.clicked.connect(self.new_order)
        toolbar.addWidget(new_btn)
        
        edit_btn = QPushButton("✏️ ویرایش")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E68900; }
        """)
        edit_btn.clicked.connect(self.edit_order)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ حذف")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        delete_btn.clicked.connect(self.delete_order)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 جستجو...")
        self.search_input.setMaximumWidth(200)
        self.search_input.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #ccc;")
        self.search_input.textChanged.connect(self.filter_orders)
        toolbar.addWidget(self.search_input)
        
        right_layout.addLayout(toolbar)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["شماره", "تاریخ", "تأمین‌کننده", "کل", "تخفیف", "مالیات", "خالص"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #4a90d9;
                color: white;
            }
            QHeaderView::section {
                background-color: #273c75;
                color: white;
                padding: 5px;
                border: none;
            }
        """)
        self.table.clicked.connect(self.on_order_selected)
        right_layout.addWidget(self.table)
        
        # ========== پنل چپ (جزئیات) ==========
        left_panel = QWidget()
        left_panel.setMaximumWidth(450)
        left_panel.setStyleSheet("background: white; border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        detail_title = QLabel("📋 جزئیات فاکتور")
        detail_title.setStyleSheet("font-size: 12pt; font-weight: bold; padding: 5px; color: #2C3E50;")
        left_layout.addWidget(detail_title)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("یک فاکتور را انتخاب کنید...")
        self.details_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                background: #fafafa;
            }
        """)
        left_layout.addWidget(self.details_text)
        
        print_btn = QPushButton("🖨️ چاپ فاکتور")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        print_btn.clicked.connect(self.print_order)
        left_layout.addWidget(print_btn)
        
        layout.addWidget(right_panel, 2)
        layout.addWidget(left_panel, 1)
    
    def load_data(self):
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('''
                SELECT po.*, p.name as party_name
                FROM purchase_orders po
                JOIN parties p ON po.party_id = p.id
                ORDER BY po.id DESC
            ''')
            self.orders_data = c.fetchall()
            
            c.execute('SELECT id, code, name, purchase_price FROM products')
            self.products = c.fetchall()
            
            c.execute('SELECT id, code, name FROM parties WHERE type = "supplier" ORDER BY name')
            self.suppliers = c.fetchall()
        
        self.display_orders()
    
    def display_orders(self, data=None):
        if data is None:
            data = self.orders_data
        
        self.table.setRowCount(len(data))
        
        for i, order in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(order['order_no']))
            display_date = safe_display_date(order['date'])
            self.table.setItem(i, 1, QTableWidgetItem(display_date))
            self.table.setItem(i, 2, QTableWidgetItem(order['party_name']))
            
            total_item = QTableWidgetItem(f"{order['total_amount']:,.0f}")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 3, total_item)
            
            discount_item = QTableWidgetItem(f"{order['discount']:,.0f}")
            discount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 4, discount_item)
            
            tax_item = QTableWidgetItem(f"{order['tax']:,.0f}")
            tax_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 5, tax_item)
            
            net_item = QTableWidgetItem(f"{order['net_amount']:,.0f}")
            net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            net_item.setForeground(QColor('#27ae60'))
            self.table.setItem(i, 6, net_item)
    
    def filter_orders(self):
        text = self.search_input.text().lower()
        if not text:
            self.display_orders(self.orders_data)
            return
        
        filtered = []
        for order in self.orders_data:
            if (text in order['order_no'].lower() or 
                text in (order['party_name'] or "").lower()):
                filtered.append(order)
        self.display_orders(filtered)
    
    def on_order_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        
        order = self.orders_data[row]
        self.current_order = order
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT poi.*, pr.name as product_name
                FROM purchase_order_items poi
                LEFT JOIN products pr ON poi.product_id = pr.id
                WHERE poi.order_id = ?
            ''', [order['id']])
            items = c.fetchall()
        
        display_date = safe_display_date(order['date'])
        
        tax_rate = self.get_tax_rate()
        tax_percent = int(tax_rate * 100)
        
        html = f"""
        <div style='font-family: Tahoma; direction: rtl;'>
            <h3 style='text-align: center; color: #273c75;'>📄 فاکتور خرید</h3>
            <p><b>شماره:</b> {order['order_no']}</p>
            <p><b>تاریخ:</b> {display_date}</p>
            <hr>
            <p><b>تأمین‌کننده:</b> {order['party_name']}</p>
            <hr>
            <h4>اقلام فاکتور:</h4>
            <table width='100%' border='1' style='border-collapse: collapse;'>
            <tr style='background: #273c75; color: white;'>
                <th>کالا</th><th>تعداد</th><th>قیمت واحد</th><th>جمع</th>
            </tr>
        """
        
        for item in items:
            html += f"""
            <tr>
                <td style='padding: 5px;'>{item['product_name'] or '-'}</td>
                <td style='text-align: center; padding: 5px;'>{item['quantity']:,.2f}</td>
                <td style='text-align: left; padding: 5px;'>{item['unit_price']:,.0f}</td>
                <td style='text-align: left; padding: 5px;'>{item['total_price']:,.0f}</td>
            </tr>
            """
        
        html += f"""
            </table>
            <hr>
            <p><b>جمع کل:</b> {order['total_amount']:,.0f} ریال</p>
            <p><b>تخفیف:</b> {order['discount']:,.0f} ریال</p>
            <p><b>مالیات ({tax_percent}%):</b> {order['tax']:,.0f} ریال</p>
            <h3 style='color: #27ae60;'>💵 مبلغ قابل پرداخت: {order['net_amount']:,.0f} ریال</h3>
        </div>
        """
        
        self.details_text.setHtml(html)
    
    def new_order(self):
        if not self.check_purchase_limit():
            return
        
        if len(self.products) == 0:
            QMessageBox.warning(self, "خطا", 
                "⚠️ هیچ کالایی در سیستم تعریف نشده است!\n"
                "لطفاً ابتدا از بخش انبار کالا تعریف کنید.")
            return
        
        dialog = PurchaseDialog(self.products, self.suppliers, self.customer_name)
        if dialog.exec_():
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ فاکتور خرید با موفقیت ثبت شد!")
    
    def edit_order(self):
        QMessageBox.information(self, "ویرایش", "✏️ قابلیت ویرایش به زودی اضافه می‌شود!")
    
    def delete_order(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک فاکتور انتخاب کنید!")
            return
        
        order = self.orders_data[row]
        reply = QMessageBox.question(self, "تأیید حذف", 
            f"آیا از حذف فاکتور {order['order_no']} اطمینان دارید؟\nاین عمل غیرقابل بازگشت است!",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('SELECT product_id, quantity FROM purchase_order_items WHERE order_id = ?', [order['id']])
                items = c.fetchall()
                for item in items:
                    InventoryHelper.update_stock(item['product_id'], item['quantity'], 'out')
                
                c.execute('DELETE FROM purchase_order_items WHERE order_id = ?', [order['id']])
                c.execute('DELETE FROM purchase_orders WHERE id = ?', [order['id']])
            
            self.load_data()
            self.details_text.clear()
            QMessageBox.information(self, "موفق", "✅ فاکتور با موفقیت حذف شد!")
    
    # ======================== چاپ ========================
    
    def print_order(self):
        if not self.current_order:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا یک فاکتور را انتخاب کنید!")
            return
        
        dialog = PrintDialog(self)
        result = dialog.exec_()
        
        if result == 1:
            self.print_direct()
        elif result == 2:
            self.save_as_pdf()
    
    def print_direct(self):
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
            
            print_dialog = QPrintDialog(printer, self)
            if print_dialog.exec_() == QPrintDialog.Accepted:
                html_content = self.generate_print_html()
                doc = QTextDocument()
                doc.setHtml(html_content)
                doc.print_(printer)
                QMessageBox.information(self, "موفق", "✅ فاکتور با موفقیت چاپ شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در چاپ: {str(e)}")
    
    def save_as_pdf(self):
        if not PDF_AVAILABLE:
            QMessageBox.warning(self, "خطا", 
                "کتابخانه ReportLab یا PIL نصب نیست!\n"
                "برای نصب: pip install reportlab pillow")
            return
        
        default_name = f"فاکتور_خرید_{self.current_order['order_no']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره فاکتور به صورت PDF", 
            default_name, "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            self.generate_pdf(file_path)
            QMessageBox.information(self, "موفق", f"✅ فاکتور در {file_path} ذخیره شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره PDF: {str(e)}")
    
    def generate_pdf(self, file_path):
        """تولید PDF با اطلاعات شرکت، نرخ مالیات و قالب تصویری"""
        order = self.current_order
        
        if not order:
            return
        
        # ====== دریافت اطلاعات ======
        company_info = self.get_company_info()
        template_info = self.get_template_info()
        tax_rate = self.get_tax_rate()
        tax_percent = int(tax_rate * 100)
        
        print(f"📋 اطلاعات شرکت: {company_info}")
        print(f"🖼️ قالب: {template_info.get('template_path', '')}")
        print(f"📊 نرخ مالیات: {tax_percent}%")
        
        template_path = template_info.get('template_path', '')
        template_position = template_info.get('template_position', 'پس‌زمینه کامل')
        template_opacity = int(template_info.get('template_opacity', 30)) / 100
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT poi.*, pr.name as product_name
                FROM purchase_order_items poi
                LEFT JOIN products pr ON poi.product_id = pr.id
                WHERE poi.order_id = ?
            ''', [order['id']])
            items = c.fetchall()
        
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib import colors
            
            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4
            margin = 20 * mm
            x = margin
            y = height - margin
            
            # ====== بارگذاری فونت ======
            font_loaded = False
            font_paths = [
                os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'tahoma.ttf'),
                os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'B Nazanin.ttf'),
                os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'BNazanin.ttf'),
                os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'Vazir.ttf')
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('PersianFont', font_path))
                        c.setFont('PersianFont', 10)
                        font_loaded = True
                        print(f"✅ فونت {font_path} بارگذاری شد")
                        break
                    except Exception as e:
                        print(f"⚠️ خطا در بارگذاری فونت {font_path}: {e}")
                        continue
            
            if not font_loaded:
                print("⚠️ هیچ فونتی بارگذاری نشد! از Helvetica استفاده می‌شود.")
                c.setFont('Helvetica', 10)
            
            # ====== رسم قالب تصویری ======
            if template_path and os.path.exists(template_path):
                try:
                    from PIL import Image
                    
                    img = Image.open(template_path)
                    
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    pixels = img.load()
                    for i in range(img.size[0]):
                        for j in range(img.size[1]):
                            r, g, b, a = pixels[i, j]
                            new_a = int(a * template_opacity)
                            pixels[i, j] = (r, g, b, new_a)
                    
                    temp_path = file_path.replace('.pdf', '_temp.png')
                    img.save(temp_path, 'PNG')
                    
                    if template_position == "پس‌زمینه کامل":
                        c.drawImage(temp_path, 0, 0, width, height, mask='auto', preserveAspectRatio=True)
                    elif template_position == "هدر (بالا)":
                        c.drawImage(temp_path, 0, height - 100*mm, width, 100*mm, mask='auto', preserveAspectRatio=True)
                    elif template_position == "فوتر (پایین)":
                        c.drawImage(temp_path, 0, 0, width, 80*mm, mask='auto', preserveAspectRatio=True)
                    elif template_position == "کنار (چپ)":
                        c.drawImage(temp_path, 0, 0, 80*mm, height, mask='auto', preserveAspectRatio=True)
                    elif template_position == "کنار (راست)":
                        c.drawImage(temp_path, width - 80*mm, 0, 80*mm, height, mask='auto', preserveAspectRatio=True)
                    
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                    print("✅ قالب تصویری با موفقیت اعمال شد")
                    
                except Exception as e:
                    print(f"⚠️ خطا در اعمال قالب: {e}")
            
            # ====== هدر با اطلاعات شرکت ======
            # نام شرکت
            c.setFont('Helvetica-Bold' if not font_loaded else 'PersianFont', 16)
            company_name = company_info.get('company_name', 'شرکت حسابداری پارسه')
            company_name_reshaped = reshape_persian_text(str(company_name))
            c.drawCentredString(width/2, y, company_name_reshaped)
            y -= 7 * mm
            
            # کد اقتصادی
            c.setFont('Helvetica' if not font_loaded else 'PersianFont', 9)
            economic = company_info.get('company_economic', '')
            if economic:
                text = reshape_persian_text(f"کد اقتصادی: {str(economic)}")
                c.drawCentredString(width/2, y, text)
                y -= 5 * mm
            
            # تلفن
            phone = company_info.get('company_phone', '')
            if phone:
                text = reshape_persian_text(f"تلفن: {str(phone)}")
                c.drawCentredString(width/2, y, text)
                y -= 5 * mm
            
            # آدرس
            address = company_info.get('company_address', '')
            if address:
                address_str = str(address)
                if len(address_str) > 50:
                    text = reshape_persian_text(f"آدرس: {address_str[:50]}...")
                else:
                    text = reshape_persian_text(f"آدرس: {address_str}")
                c.drawCentredString(width/2, y, text)
                y -= 5 * mm
            
            # خط جداکننده
            c.line(x, y, width - margin, y)
            y -= 5 * mm
            
            # ====== عنوان فاکتور ======
            c.setFont('Helvetica-Bold' if not font_loaded else 'PersianFont', 16)
            title_text = reshape_persian_text("فاکتور خرید")
            c.drawCentredString(width/2, y, title_text)
            y -= 8 * mm
            
            c.setFont('Helvetica' if not font_loaded else 'PersianFont', 10)
            doc_no_text = reshape_persian_text(f"شماره: {order['order_no']}")
            c.drawCentredString(width/2, y, doc_no_text)
            y -= 10 * mm
            
            # ====== اطلاعات ======
            display_date = safe_display_date(order['date']) if order['date'] else ""
            
            date_text = reshape_persian_text(f"تاریخ: {display_date}")
            c.drawString(x, y, date_text)
            y -= 6 * mm
            
            party_text = reshape_persian_text(f"تأمین‌کننده: {order['party_name']}")
            c.drawString(x, y, party_text)
            y -= 8 * mm
            
            c.line(x, y, width - margin, y)
            y -= 5 * mm
            
            # ====== جدول ======
            c.setFont('Helvetica-Bold' if not font_loaded else 'PersianFont', 10)
            
            col1_x = x                      # ردیف
            col2_x = x + 15 * mm            # کالا
            col3_x = x + 60 * mm            # تعداد
            col4_x = x + 78 * mm            # فی
            col5_x = x + 98 * mm            # جمع
            
            c.drawString(col1_x, y, reshape_persian_text("ردیف"))
            c.drawString(col2_x, y, reshape_persian_text("کالا"))
            c.drawString(col3_x, y, reshape_persian_text("تعداد"))
            c.drawString(col4_x, y, reshape_persian_text("فی"))
            c.drawString(col5_x, y, reshape_persian_text("جمع"))
            y -= 5 * mm
            
            c.line(x, y, width - margin, y)
            y -= 3 * mm
            
            # ====== اقلام ======
            c.setFont('Helvetica' if not font_loaded else 'PersianFont', 9)
            for i, item in enumerate(items, 1):
                if y < 30 * mm:
                    c.showPage()
                    y = height - margin
                    c.setFont('Helvetica' if not font_loaded else 'PersianFont', 9)
                
                c.drawString(col1_x, y, str(i))
                product_name = item['product_name'][:20] if item['product_name'] else '-'
                c.drawString(col2_x, y, reshape_persian_text(product_name))
                c.drawString(col3_x, y, f"{item['quantity']:,.2f}")
                c.drawString(col4_x, y, f"{item['unit_price']:,.0f}")
                c.drawRightString(col5_x + 10 * mm, y, f"{item['total_price']:,.0f}")
                y -= 6 * mm
            
            # ====== جمع‌ها ======
            y -= 5 * mm
            c.line(x, y, width - margin, y)
            y -= 5 * mm
            
            c.setFont('Helvetica-Bold' if not font_loaded else 'PersianFont', 10)
            
            label_x = x + 75 * mm
            value_x = width - margin - 10 * mm
            
            c.drawString(label_x, y, reshape_persian_text("جمع کل:"))
            c.drawRightString(value_x, y, f"{order['total_amount']:,.0f}")
            y -= 6 * mm
            
            c.drawString(label_x, y, reshape_persian_text("تخفیف:"))
            c.drawRightString(value_x, y, f"{order['discount']:,.0f}")
            y -= 6 * mm
            
            tax_label = reshape_persian_text(f"مالیات ({tax_percent}%):")
            c.drawString(label_x, y, tax_label)
            c.drawRightString(value_x, y, f"{order['tax']:,.0f}")
            y -= 6 * mm
            
            c.line(x, y, width - margin, y)
            y -= 6 * mm
            
            # ====== مبلغ قابل پرداخت ======
            c.setFont('Helvetica-Bold' if not font_loaded else 'PersianFont', 12)
            c.setFillColor(colors.green)
            
            label_x_pay = x + 55 * mm
            value_x_pay = width - margin - 10 * mm
            
            c.drawString(label_x_pay, y, reshape_persian_text("مبلغ قابل پرداخت:"))
            c.drawRightString(value_x_pay, y, f"{order['net_amount']:,.0f}   ریال")
            
            c.setFillColor(colors.black)
            
            # ====== فوتر ======
            y = 20 * mm
            c.setFont('Helvetica' if not font_loaded else 'PersianFont', 8)
            footer_text = reshape_persian_text(f"تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')}")
            c.drawCentredString(width/2, y, footer_text)
            y -= 5 * mm
            c.drawCentredString(width/2, y, reshape_persian_text("ImanAccount - حسابداری هوشمند"))
            
            c.save()
            print("✅ PDF با موفقیت ساخته شد")
            
        except Exception as e:
            print(f"⚠️ خطا در تولید PDF: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def generate_print_html(self):
        """تولید HTML برای چاپ با اطلاعات شرکت و نرخ مالیات پویا"""
        order = self.current_order
        
        company_info = self.get_company_info()
        tax_rate = self.get_tax_rate()
        tax_percent = int(tax_rate * 100)
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT poi.*, pr.name as product_name
                FROM purchase_order_items poi
                LEFT JOIN products pr ON poi.product_id = pr.id
                WHERE poi.order_id = ?
            ''', [order['id']])
            items = c.fetchall()
        
        display_date = safe_display_date(order['date']) if order['date'] else ""
        
        company_name = company_info.get('company_name', 'شرکت حسابداری پارسه')
        company_economic = company_info.get('company_economic', '')
        company_phone = company_info.get('company_phone', '')
        company_address = company_info.get('company_address', '')
        
        html = f"""
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Tahoma, sans-serif;
                direction: rtl;
                padding: 20px;
                color: #2c3e50;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #273c75;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            .company-name {{
                font-size: 18pt;
                font-weight: bold;
                color: #273c75;
            }}
            .company-info {{
                font-size: 10pt;
                color: #555;
                margin-top: 5px;
            }}
            .title {{
                font-size: 16pt;
                font-weight: bold;
                color: #2c3e50;
                margin-top: 10px;
            }}
            .info {{
                margin-bottom: 15px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 5px;
            }}
            .info table {{ width: 100%; }}
            .info td {{ padding: 3px 5px; }}
            table.items {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            table.items th {{
                background-color: #273c75;
                color: white;
                padding: 8px;
                text-align: center;
            }}
            table.items td {{
                border: 1px solid #ddd;
                padding: 6px;
                text-align: center;
            }}
            .totals {{
                margin-top: 15px;
                padding: 10px;
                background: #f0f0f0;
                border-radius: 5px;
            }}
            .net {{
                font-size: 14pt;
                font-weight: bold;
                color: #27ae60;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 9pt;
                color: #999;
                border-top: 1px solid #ddd;
                padding-top: 10px;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">{company_name}</div>
                <div class="company-info">
                    {f'کد اقتصادی: {company_economic} | ' if company_economic else ''}
                    {f'تلفن: {company_phone}' if company_phone else ''}
                    {f'<br>آدرس: {company_address}' if company_address else ''}
                </div>
                <div class="title">فاکتور خرید</div>
                <div>شماره: {order['order_no']}</div>
            </div>
            <div class="info">
                <table>
                    <tr>
                        <td><b>تاریخ:</b> {display_date}</td>
                        <td><b>تأمین‌کننده:</b> {order['party_name']}</td>
                    </tr>
                </table>
            </div>
            <table class="items">
                <thead>
                    <tr><th>ردیف</th><th>کالا</th><th>تعداد</th><th>قیمت واحد</th><th>جمع</th></tr>
                </thead>
                <tbody>
        """
        
        for i, item in enumerate(items, 1):
            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{item['product_name'] or '-'}</td>
                    <td>{item['quantity']:,.2f}</td>
                    <td>{item['unit_price']:,.0f}</td>
                    <td>{item['total_price']:,.0f}</td>
                </tr>
            """
        
        html += f"""
                </tbody>
            </table>
            <div class="totals">
                <table width="100%">
                    <tr><td><b>جمع کل:</b></td><td align="left">{order['total_amount']:,.0f} ریال</td></tr>
                    <tr><td><b>تخفیف:</b></td><td align="left">{order['discount']:,.0f} ریال</td></tr>
                    <tr><td><b>مالیات ({tax_percent}%):</b></td><td align="left">{order['tax']:,.0f} ریال</td></tr>
                    <tr><td colspan="2"><hr></td></tr>
                    <tr><td><b>مبلغ قابل پرداخت:</b></td><td align="left" class="net">{order['net_amount']:,.0f} ریال</td></tr>
                </table>
            </div>
            <div class="footer">
                <p>تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')}</p>
                <p>ImanAccount - حسابداری هوشمند</p>
            </div>
        </body>
        </html>
        """
        return html


class PrintDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🖨️ چاپ فاکتور")
        self.setModal(True)
        self.setFixedSize(400, 220)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("🖨️ انتخاب روش چاپ")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #273c75;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel("لطفاً روش مورد نظر برای چاپ فاکتور را انتخاب کنید:")
        desc.setStyleSheet("color: #555;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        
        self.print_btn = QPushButton("🖨️ چاپ مستقیم")
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        self.print_btn.clicked.connect(lambda: self.done(1))
        btn_layout.addWidget(self.print_btn)
        
        self.pdf_btn = QPushButton("📄 ذخیره PDF")
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.pdf_btn.clicked.connect(lambda: self.done(2))
        btn_layout.addWidget(self.pdf_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setStyleSheet("padding: 8px 15px;")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignCenter)
        
        if not PDF_AVAILABLE:
            warn = QLabel("⚠️ کتابخانه ReportLab یا PIL نصب نیست.")
            warn.setStyleSheet("color: #e74c3c; font-size: 9pt;")
            layout.addWidget(warn)
            self.pdf_btn.setEnabled(False)


class PurchaseDialog(QDialog):
    """دیالوگ ایجاد فاکتور خرید با نرخ مالیات پویا"""
    
    def __init__(self, products, suppliers, customer_name="", parent=None):
        super().__init__(parent)
        self.products = products
        self.suppliers = suppliers
        self.customer_name = customer_name
        self._total_amount = 0
        self._discount = 0
        self._tax = 0
        self._net_amount = 0
        
        self.setWindowTitle("➕ فاکتور خرید جدید")
        self.setGeometry(200, 100, 850, 650)
        self.init_ui()
    
    def get_tax_rate(self):
        """دریافت نرخ مالیات از دیتابیس"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'tax_rate'")
                row = c.fetchone()
                if row:
                    return float(row[0]) / 100
                return 0.09
        except Exception as e:
            print(f"⚠️ خطا در دریافت نرخ مالیات: {e}")
            return 0.09
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        form_widget = QWidget()
        form_widget.setStyleSheet("background: #f8f9fa; border-radius: 8px; padding: 5px;")
        form_layout = QHBoxLayout(form_widget)
        
        self.date = ShamsiDateEdit()
        self.date.setStyleSheet("padding: 5px; border-radius: 5px;")
        form_layout.addWidget(QLabel("📅 تاریخ:"))
        form_layout.addWidget(self.date)
        
        self.supplier_combo = QComboBox()
        self.supplier_combo.setMinimumWidth(200)
        self.supplier_combo.setStyleSheet("padding: 5px; border-radius: 5px;")
        for s in self.suppliers:
            self.supplier_combo.addItem(f"{s['code']} - {s['name']}", s['id'])
        form_layout.addWidget(QLabel("🏢 تأمین‌کننده:"))
        form_layout.addWidget(self.supplier_combo)
        form_layout.addStretch()
        
        layout.addWidget(form_widget)
        
        items_group = QGroupBox("📦 اقلام فاکتور")
        items_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #273c75;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px;
            }
        """)
        items_layout = QVBoxLayout(items_group)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(["کالا", "تعداد", "قیمت واحد", "جمع", "عملیات"])
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                border: none;
            }
            QHeaderView::section {
                background-color: #273c75;
                color: white;
                padding: 5px;
                border: none;
            }
        """)
        items_layout.addWidget(self.items_table)
        
        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ افزودن کالا")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        add_btn.clicked.connect(self.add_product_row)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        items_layout.addLayout(btn_row)
        
        layout.addWidget(items_group)
        
        totals_widget = QWidget()
        totals_widget.setStyleSheet("background: #f8f9fa; border-radius: 8px; padding: 10px;")
        totals_layout = QGridLayout(totals_widget)
        totals_layout.setSpacing(10)
        
        self.total_label = QLabel("۰")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: #2c3e50;")
        totals_layout.addWidget(QLabel("💰 جمع کل:"), 0, 0)
        totals_layout.addWidget(self.total_label, 0, 1)
        
        self.discount_input = QLineEdit()
        self.discount_input.setPlaceholderText("۰")
        self.discount_input.setAlignment(Qt.AlignRight)
        self.discount_input.setMaximumWidth(150)
        self.discount_input.setStyleSheet("padding: 5px; border-radius: 5px; border: 1px solid #ccc;")
        self.discount_input.textChanged.connect(self.calculate_totals)
        totals_layout.addWidget(QLabel("🏷️ تخفیف:"), 1, 0)
        totals_layout.addWidget(self.discount_input, 1, 1)
        
        self.tax_label = QLabel("۰")
        self.tax_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        totals_layout.addWidget(QLabel("📊 مالیات:"), 2, 0)
        totals_layout.addWidget(self.tax_label, 2, 1)
        
        self.net_label = QLabel("۰")
        self.net_label.setStyleSheet("font-weight: bold; font-size: 16pt; color: #27ae60;")
        totals_layout.addWidget(QLabel("💵 مبلغ قابل پرداخت:"), 3, 0)
        totals_layout.addWidget(self.net_label, 3, 1)
        
        tax_rate = self.get_tax_rate()
        tax_percent = int(tax_rate * 100)
        tax_info = QLabel(f"ℹ️ نرخ مالیات: {tax_percent}% (از تنظیمات)")
        tax_info.setStyleSheet("color: #7f8c8d; font-size: 9pt; font-style: italic;")
        totals_layout.addWidget(tax_info, 4, 0, 1, 2)
        
        totals_layout.setColumnStretch(2, 1)
        layout.addWidget(totals_widget)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره فاکتور")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        save_btn.clicked.connect(self.save_order)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        if len(self.products) == 0:
            add_btn.setEnabled(False)
            add_btn.setToolTip("هیچ کالایی در سیستم وجود ندارد. ابتدا از بخش انبار کالا تعریف کنید.")
    
    def add_product_row(self):
        if len(self.products) == 0:
            QMessageBox.warning(self, "خطا", 
                "⚠️ هیچ کالایی در سیستم وجود ندارد!\n"
                "لطفاً ابتدا از بخش انبار کالا تعریف کنید.")
            return
        
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        combo = QComboBox()
        combo.setStyleSheet("padding: 5px; border-radius: 5px;")
        for p in self.products:
            combo.addItem(f"{p['code']} - {p['name']}", p['id'])
        self.items_table.setCellWidget(row, 0, combo)
        
        quantity_spin = QDoubleSpinBox()
        quantity_spin.setRange(0.01, 999999)
        quantity_spin.setValue(1)
        quantity_spin.setDecimals(2)
        quantity_spin.setSingleStep(1)
        quantity_spin.setStyleSheet("padding: 5px; border-radius: 5px;")
        quantity_spin.valueChanged.connect(self.calculate_totals)
        self.items_table.setCellWidget(row, 1, quantity_spin)
        
        price_edit = QLineEdit()
        price_edit.setAlignment(Qt.AlignRight)
        price_edit.setPlaceholderText("قیمت خرید")
        price_edit.setStyleSheet("padding: 5px; border-radius: 5px; border: 1px solid #ccc;")
        price_edit.textChanged.connect(self.calculate_totals)
        self.items_table.setCellWidget(row, 2, price_edit)
        
        total_label = QLabel("۰")
        total_label.setAlignment(Qt.AlignRight)
        total_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        self.items_table.setCellWidget(row, 3, total_label)
        
        remove_btn = QPushButton("🗑️")
        remove_btn.setMaximumWidth(40)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        remove_btn.clicked.connect(lambda: self.remove_row(row))
        self.items_table.setCellWidget(row, 4, remove_btn)
        
        combo.currentIndexChanged.connect(lambda: self.update_product_price(row))
        quantity_spin.valueChanged.connect(lambda: self.update_row_total(row))
        price_edit.textChanged.connect(lambda: self.update_row_total(row))
        
        self.update_product_price(row)
    
    def remove_row(self, row):
        self.items_table.removeRow(row)
        self.reindex_rows()
        self.calculate_totals()
    
    def reindex_rows(self):
        for row in range(self.items_table.rowCount()):
            btn = self.items_table.cellWidget(row, 4)
            if btn:
                try:
                    btn.clicked.disconnect()
                except:
                    pass
                btn.clicked.connect(lambda checked, r=row: self.remove_row(r))
    
    def update_product_price(self, row):
        combo = self.items_table.cellWidget(row, 0)
        if combo and combo.currentIndex() >= 0:
            product_id = combo.currentData()
            for p in self.products:
                if p['id'] == product_id:
                    price_widget = self.items_table.cellWidget(row, 2)
                    if price_widget and not price_widget.text():
                        price_widget.setText(f"{p['purchase_price']:,}")
                    self.update_row_total(row)
                    break
    
    def update_row_total(self, row):
        quantity_spin = self.items_table.cellWidget(row, 1)
        price_edit = self.items_table.cellWidget(row, 2)
        total_label = self.items_table.cellWidget(row, 3)
        
        if quantity_spin and price_edit and total_label:
            try:
                quantity = quantity_spin.value()
                price_text = price_edit.text().replace(',', '').strip()
                unit_price = int(float(price_text)) if price_text else 0
                total = quantity * unit_price
                total_label.setText(f"{total:,.0f}")
            except:
                total_label.setText("۰")
        
        self.calculate_totals()
    
    def calculate_totals(self):
        total = 0
        
        for row in range(self.items_table.rowCount()):
            total_label = self.items_table.cellWidget(row, 3)
            if total_label:
                text = total_label.text().replace(',', '')
                try:
                    total += int(float(text)) if text else 0
                except:
                    pass
        
        discount_text = self.discount_input.text().replace(',', '').strip()
        discount = int(float(discount_text)) if discount_text else 0
        
        tax_rate = self.get_tax_rate()
        tax = int(total * tax_rate)
        net = total - discount + tax
        
        self.total_label.setText(f"{total:,.0f}")
        self.tax_label.setText(f"{tax:,.0f}")
        self.net_label.setText(f"{net:,.0f} ریال")
        
        self._total_amount = total
        self._discount = discount
        self._tax = tax
        self._net_amount = net
    
    def save_order(self):
        if self.supplier_combo.currentIndex() < 0:
            QMessageBox.warning(self, "خطا", "لطفاً تأمین‌کننده را انتخاب کنید!")
            return
        
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "حداقل یک کالا اضافه کنید!")
            return
        
        valid_items = False
        for row in range(self.items_table.rowCount()):
            price_widget = self.items_table.cellWidget(row, 2)
            if price_widget and price_widget.text():
                valid_items = True
                break
        
        if not valid_items:
            QMessageBox.warning(self, "خطا", "حداقل یک کالا با قیمت معتبر وارد کنید!")
            return
        
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute("SELECT MAX(CAST(SUBSTR(order_no, 4) AS INTEGER)) FROM purchase_orders WHERE order_no LIKE 'PO%'")
            max_no = c.fetchone()[0]
            order_no = f"PO{(max_no or 0) + 1:06d}"
            
            supplier_id = self.supplier_combo.currentData()
            shamsi_date = self.date.get_shamsi()
            
            c.execute('''
                INSERT INTO purchase_orders (order_no, date, party_id, total_amount, discount, tax, net_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', [order_no, shamsi_date, supplier_id, self._total_amount, self._discount, self._tax, self._net_amount])
            
            order_id = c.lastrowid
            
            for row in range(self.items_table.rowCount()):
                combo = self.items_table.cellWidget(row, 0)
                quantity_spin = self.items_table.cellWidget(row, 1)
                price_widget = self.items_table.cellWidget(row, 2)
                
                product_id = combo.currentData()
                quantity = quantity_spin.value()
                price_text = price_widget.text().replace(',', '').strip()
                unit_price = int(float(price_text)) if price_text else 0
                total_price = quantity * unit_price
                
                if unit_price > 0 and quantity > 0:
                    c.execute('''
                        INSERT INTO purchase_order_items (order_id, product_id, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [order_id, product_id, quantity, unit_price, total_price])
                    
                    InventoryHelper.update_stock(product_id, quantity, 'in')
            
            conn.commit()
            super().accept()
