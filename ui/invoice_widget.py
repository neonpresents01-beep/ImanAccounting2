# invoice_widget.py
# ============================================================
# ویجت مدیریت فاکتورهای فروش (نسخه کامل با PDF فارسی و استاندارد)
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from datetime import datetime
from database import get_db, InvoiceHelper, InventoryHelper, ModuleLimitHelper
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali
import os
import csv

# ========== پشتیبانی از PDF (ReportLab) ==========
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ ReportLab نصب نیست. برای چاپ PDF: pip install reportlab")

# ========== پشتیبانی از فارسی ==========
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    PERSIAN_SUPPORT = True
except ImportError:
    PERSIAN_SUPPORT = False
    print("⚠️ کتابخانه‌های فارسی نصب نیستند. برای نصب: pip install arabic-reshaper python-bidi")


class InvoiceWidget(QWidget):
    """ویجت مدیریت فاکتورهای فروش با پشتیبانی کامل از تم و PDF"""
    
    def __init__(self, customer_name=""):
        super().__init__()
        self.customer_name = customer_name
        self.invoices_data = []
        self.products = []
        self.parties = []
        self.current_items = []
        self.current_invoice = None
        
        # تنظیمات
        self.tax_rate = self._get_tax_rate()
        self.company_info = self._get_company_info()
        
        self.init_ui()
        self.load_data()
    
    # ============================================================
    # توابع تنظیمات
    # ============================================================
    
    def _get_tax_rate(self) -> float:
        """دریافت نرخ مالیات از دیتابیس"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'tax_rate'")
                row = c.fetchone()
                return float(row[0]) / 100 if row else 0.09
        except:
            return 0.09
    
    def _get_company_info(self) -> dict:
        """دریافت اطلاعات شرکت از دیتابیس"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT key, value FROM settings WHERE key LIKE 'company_%'")
                rows = c.fetchall()
                info = {}
                for row in rows:
                    info[row['key']] = row['value']
                
                if not info or not info.get('company_name'):
                    info = {
                        'company_name': 'شرکت حسابداری پارسه',
                        'company_phone': '021-12345678',
                        'company_address': 'تهران، خیابان اصلی، پلاک 123'
                    }
                return info
        except:
            return {
                'company_name': 'شرکت حسابداری پارسه',
                'company_phone': '021-12345678',
                'company_address': 'تهران، خیابان اصلی، پلاک 123'
            }
    
    def check_invoice_limit(self):
        """بررسی محدودیت ماژول فروش"""
        if self.customer_name:
            allowed, current, limit, msg = ModuleLimitHelper.check_module_limit(self.customer_name, 'invoice')
            if not allowed:
                QMessageBox.warning(self, "خطا", 
                    f"❌ به سقف مجاز {limit} فاکتور فروش رسیده‌اید!\n"
                    "برای ثبت فاکتور جدید، لطفاً با مدیر سیستم تماس بگیرید.")
                return False
            elif limit > 0 and limit - current <= 3:
                QMessageBox.warning(self, "هشدار", 
                    f"⚠️ فقط {limit - current} فاکتور فروش دیگر تا رسیدن به سقف مجاز باقی مانده است.")
        return True
    
    # ============================================================
    # رابط کاربری
    # ============================================================
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        
        # ========== پنل راست (لیست فاکتورها) ==========
        right_panel = QWidget()
        right_panel.setStyleSheet("background: white; border-radius: 8px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        
        title = QLabel("📄 فاکتورهای فروش")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px; color: #2C3E50;")
        right_layout.addWidget(title)
        
        # نوار ابزار
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
        new_btn.clicked.connect(self.new_invoice)
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
        edit_btn.clicked.connect(self.edit_invoice)
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
        delete_btn.clicked.connect(self.delete_invoice)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 جستجو...")
        self.search_input.setMaximumWidth(200)
        self.search_input.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #ccc;")
        self.search_input.textChanged.connect(self.filter_invoices)
        toolbar.addWidget(self.search_input)
        
        right_layout.addLayout(toolbar)
        
        # جدول فاکتورها
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["شماره", "تاریخ", "مشتری", "کل", "تخفیف", "مالیات", "خالص"])
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
        self.table.clicked.connect(self.on_invoice_selected)
        right_layout.addWidget(self.table)
        
        # ========== پنل چپ (جزئیات فاکتور) ==========
        left_panel = QWidget()
        left_panel.setMaximumWidth(450)
        left_panel.setStyleSheet("background: white; border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("جزئیات فاکتور")
        self.details_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                background: #fafafa;
            }
        """)
        left_layout.addWidget(self.details_text)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        print_btn = QPushButton("🖨️ چاپ")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        print_btn.clicked.connect(self.print_invoice)
        btn_layout.addWidget(print_btn)
        
        pdf_btn = QPushButton("📄 PDF")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover { background-color: #1e8449; }
        """)
        pdf_btn.clicked.connect(self.save_as_pdf)
        btn_layout.addWidget(pdf_btn)
        
        left_layout.addLayout(btn_layout)
        
        layout.addWidget(right_panel, 2)
        layout.addWidget(left_panel, 1)
    
    # ============================================================
    # بارگذاری داده‌ها
    # ============================================================
    
    def load_data(self):
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('''
                SELECT i.*, p.name as party_name
                FROM invoices i
                JOIN parties p ON i.party_id = p.id
                ORDER BY i.id DESC
            ''')
            self.invoices_data = c.fetchall()
            
            # لیست کالاها (فقط موجودی دارها)
            c.execute('SELECT id, code, name, sale_price, stock FROM products WHERE stock > 0')
            self.products = c.fetchall()
            
            # لیست مشتریان
            c.execute('SELECT id, code, name FROM parties WHERE type = "customer" ORDER BY name')
            self.parties = c.fetchall()
        
        self.display_invoices()
    
    def display_invoices(self, data=None):
        """نمایش فاکتورها در جدول"""
        if data is None:
            data = self.invoices_data
        
        self.table.setRowCount(len(data))
        
        for i, inv in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(inv['invoice_no']))
            self.table.setItem(i, 1, QTableWidgetItem(safe_display_date(inv['date']) if inv['date'] else ""))
            self.table.setItem(i, 2, QTableWidgetItem(inv['party_name']))
            
            total_item = QTableWidgetItem(f"{inv['total_amount']:,.0f}")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 3, total_item)
            
            discount_item = QTableWidgetItem(f"{inv['discount']:,.0f}")
            discount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 4, discount_item)
            
            tax_item = QTableWidgetItem(f"{inv['tax']:,.0f}")
            tax_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 5, tax_item)
            
            net_item = QTableWidgetItem(f"{inv['net_amount']:,.0f}")
            net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            net_item.setForeground(QColor('#27ae60'))
            self.table.setItem(i, 6, net_item)
    
    def filter_invoices(self):
        """فیلتر فاکتورها"""
        text = self.search_input.text().lower()
        if not text:
            self.display_invoices(self.invoices_data)
            return
        
        filtered = []
        for inv in self.invoices_data:
            if (text in inv['invoice_no'].lower() or 
                text in (inv['party_name'] or "").lower()):
                filtered.append(inv)
        
        self.display_invoices(filtered)
    
    # ============================================================
    # انتخاب و نمایش جزئیات
    # ============================================================
    
    def on_invoice_selected(self):
        """نمایش جزئیات فاکتور انتخاب شده"""
        row = self.table.currentRow()
        if row < 0:
            return
        
        invoice_no = self.table.item(row, 0).text()
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT i.*, p.name as party_name, p.phone, p.address
                FROM invoices i
                JOIN parties p ON i.party_id = p.id
                WHERE i.invoice_no = ?
            ''', [invoice_no])
            invoice = c.fetchone()
            
            if not invoice:
                return
            
            c.execute('''
                SELECT ii.*, pr.name as product_name
                FROM invoice_items ii
                LEFT JOIN products pr ON ii.product_id = pr.id
                WHERE ii.invoice_id = ?
            ''', [invoice['id']])
            items = c.fetchall()
        
        self.current_invoice = invoice
        self.current_items = items
        
        display_date = safe_display_date(invoice['date']) if invoice['date'] else ""
        tax_percent = int(self.tax_rate * 100)
        
        html = f"""
        <div style='font-family: Tahoma; direction: rtl;'>
            <h3 style='text-align: center; color: #273c75;'>📄 فاکتور فروش</h3>
            <p><b>شماره:</b> {invoice['invoice_no']}</p>
            <p><b>تاریخ:</b> {display_date}</p>
            <hr>
            <p><b>مشتری:</b> {invoice['party_name']}</p>
            <p><b>تلفن:</b> {invoice['phone'] or '-'}</p>
            <p><b>آدرس:</b> {invoice['address'] or '-'}</p>
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
            <p><b>جمع کل:</b> {invoice['total_amount']:,.0f} ریال</p>
            <p><b>تخفیف:</b> {invoice['discount']:,.0f} ریال</p>
            <p><b>مالیات ({tax_percent}%):</b> {invoice['tax']:,.0f} ریال</p>
            <h3 style='color: #27ae60;'>💵 مبلغ قابل پرداخت: {invoice['net_amount']:,.0f} ریال</h3>
        </div>
        """
        
        self.details_text.setHtml(html)
    
    # ============================================================
    # عملیات اصلی (جدید، ویرایش، حذف)
    # ============================================================
    
    def new_invoice(self):
        """ایجاد فاکتور جدید با بررسی محدودیت"""
        if not self.check_invoice_limit():
            return
        
        if not self.products:
            QMessageBox.warning(self, "خطا", 
                "⚠️ هیچ کالایی با موجودی تعریف نشده است!\n"
                "لطفاً ابتدا از بخش انبار کالا تعریف کنید.")
            return
        
        dialog = InvoiceDialog(self.products, self.parties, self.customer_name, self.tax_rate)
        if dialog.exec_():
            self.load_data()
            QMessageBox.information(self, "موفق", "✅ فاکتور با موفقیت ثبت شد!")
    
    def edit_invoice(self):
        QMessageBox.information(self, "ویرایش", "✏️ قابلیت ویرایش به زودی اضافه می‌شود!")
    
    def delete_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک فاکتور انتخاب کنید!")
            return
        
        invoice_no = self.table.item(row, 0).text()
        reply = QMessageBox.question(self, "تأیید حذف", f"آیا از حذف فاکتور {invoice_no} اطمینان دارید؟",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute('SELECT id FROM invoices WHERE invoice_no = ?', [invoice_no])
                    row_data = c.fetchone()
                    if row_data:
                        invoice_id = row_data[0]
                        
                        # برگرداندن موجودی به انبار
                        c.execute('SELECT product_id, quantity FROM invoice_items WHERE invoice_id = ?', [invoice_id])
                        items = c.fetchall()
                        for item in items:
                            InventoryHelper.update_stock(item['product_id'], item['quantity'], 'in')
                        
                        c.execute('DELETE FROM invoice_items WHERE invoice_id = ?', [invoice_id])
                        c.execute('DELETE FROM invoices WHERE id = ?', [invoice_id])
                
                self.load_data()
                self.details_text.clear()
                QMessageBox.information(self, "موفق", "✅ فاکتور با موفقیت حذف شد!")
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ خطا در حذف: {str(e)}")
    
    # ============================================================
    # چاپ و PDF (نسخه استاندارد ERP با فارسی صحیح)
    # ============================================================
    
    def print_invoice(self):
        """چاپ فاکتور"""
        if not self.current_invoice:
            QMessageBox.warning(self, "خطا", "لطفاً یک فاکتور را انتخاب کنید!")
            return
        
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
            
            # پیش‌نمایش چاپ
            preview_dialog = QPrintPreviewDialog(printer, self)
            preview_dialog.paintRequested.connect(self._print_preview)
            preview_dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در چاپ: {str(e)}")
    
    def _print_preview(self, printer):
        """رندر چاپ"""
        html_content = self._generate_print_html()
        doc = QTextDocument()
        doc.setHtml(html_content)
        doc.print_(printer)
    
    def _generate_print_html(self) -> str:
        """تولید HTML برای چاپ"""
        invoice = self.current_invoice
        if not invoice:
            return ""
        
        items = self.current_items
        tax_percent = int(self.tax_rate * 100)
        
        display_date = safe_display_date(invoice['date']) if invoice['date'] else ""
        
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
                font-size: 16pt;
                font-weight: bold;
                color: #273c75;
            }}
            .company-info {{
                font-size: 9pt;
                color: #555;
                margin-top: 5px;
            }}
            .title {{
                font-size: 14pt;
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
                font-size: 13pt;
                font-weight: bold;
                color: #27ae60;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 8pt;
                color: #999;
                border-top: 1px solid #ddd;
                padding-top: 10px;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">{self.company_info.get('company_name', 'شرکت حسابداری پارسه')}</div>
                <div class="company-info">
                    {f'تلفن: {self.company_info.get("company_phone", "")}' if self.company_info.get("company_phone") else ''}
                    {f'<br>آدرس: {self.company_info.get("company_address", "")}' if self.company_info.get("company_address") else ''}
                </div>
                <div class="title">فاکتور فروش</div>
                <div>شماره: {invoice['invoice_no']}</div>
            </div>
            <div class="info">
                <table>
                    <tr>
                        <td><b>تاریخ:</b> {display_date}</td>
                        <td><b>مشتری:</b> {invoice['party_name']}</td>
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
                    <tr><td><b>جمع کل:</b></td><td align="left">{invoice['total_amount']:,.0f} ریال</td></tr>
                    <tr><td><b>تخفیف:</b></td><td align="left">{invoice['discount']:,.0f} ریال</td></tr>
                    <tr><td><b>مالیات ({tax_percent}%):</b></td><td align="left">{invoice['tax']:,.0f} ریال</td></tr>
                    <tr><td colspan="2"><hr></td></tr>
                    <tr><td><b>مبلغ قابل پرداخت:</b></td><td align="left" class="net">{invoice['net_amount']:,.0f} ریال</td></tr>
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
    
    def save_as_pdf(self):
        """ذخیره فاکتور به صورت PDF (با گزارش‌گیری استاندارد ERP)"""
        if not self.current_invoice:
            QMessageBox.warning(self, "خطا", "لطفاً یک فاکتور را انتخاب کنید!")
            return
        
        if not PDF_AVAILABLE:
            QMessageBox.warning(self, "خطا", 
                "کتابخانه ReportLab نصب نیست!\nبرای نصب: pip install reportlab")
            return
        
        default_name = f"فاکتور_فروش_{self.current_invoice['invoice_no']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره فاکتور به صورت PDF", 
            default_name, "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            self._generate_pdf(file_path)
            QMessageBox.information(self, "موفق", f"✅ فاکتور در {file_path} ذخیره شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره PDF: {str(e)}")
    
    def _generate_pdf(self, file_path):
        """تولید PDF با ReportLab (جدول استاندارد با فارسی صحیح)"""
        invoice = self.current_invoice
        items = self.current_items
        tax_percent = int(self.tax_rate * 100)
        
        try:
            # ========== بارگذاری فونت ==========
            font_path = "fonts/tahoma.ttf"
            if not os.path.exists(font_path):
                font_path = "C:/Windows/Fonts/tahoma.ttf"
            if not os.path.exists(font_path):
                font_path = "C:/Windows/Fonts/arial.ttf"
            
            pdfmetrics.registerFont(TTFont('PersianFont', font_path))
            
            # ========== توابع تبدیل متن فارسی ==========
            def fa(text):
                if text is None:
                    text = ""
                reshaped = arabic_reshaper.reshape(str(text))
                return get_display(reshaped)
            
            # ========== تنظیمات استایل ==========
            styles = getSampleStyleSheet()
            right_style = ParagraphStyle(
                'Right', parent=styles['Normal'],
                fontName='PersianFont', fontSize=10,
                alignment=TA_RIGHT, leading=16
            )
            center_style = ParagraphStyle(
                'Center', parent=styles['Normal'],
                fontName='PersianFont', fontSize=12,
                alignment=TA_CENTER, leading=18
            )
            bold_center_style = ParagraphStyle(
                'BoldCenter', parent=center_style,
                fontSize=14, fontName='PersianFont'
            )
            
            # ========== ساخت سند ==========
            doc_builder = SimpleDocTemplate(
                file_path, pagesize=A4,
                rightMargin=15*mm, leftMargin=15*mm,
                topMargin=15*mm, bottomMargin=15*mm
            )
            
            elements = []
            
            # ========== هدر ==========
            elements.append(Paragraph(fa(self.company_info.get('company_name', 'شرکت حسابداری پارسه')), bold_center_style))
            elements.append(Spacer(1, 5))
            if self.company_info.get('company_phone'):
                elements.append(Paragraph(fa(f"تلفن: {self.company_info.get('company_phone')}"), center_style))
            if self.company_info.get('company_address'):
                elements.append(Paragraph(fa(f"آدرس: {self.company_info.get('company_address')}"), center_style))
            
            elements.append(Spacer(1, 15))
            
            # ========== اطلاعات سند ==========
            display_date = safe_display_date(invoice['date']) if invoice['date'] else ""
            
            info_data = [
                [Paragraph(fa(f"شماره: {invoice['invoice_no']}"), right_style), 
                 Paragraph(fa(f"تاریخ: {display_date}"), right_style)],
                [Paragraph(fa(f"مشتری: {invoice['party_name']}"), right_style), 
                 Paragraph(fa(""), right_style)]
            ]
            
            info_table = Table(info_data, colWidths=[doc_builder.width/2.0]*2)
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'PersianFont'),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 15))
            
            # ========== جدول اقلام ==========
            items_data = [
                [Paragraph(fa("ردیف"), right_style),
                 Paragraph(fa("کالا"), right_style),
                 Paragraph(fa("تعداد"), right_style),
                 Paragraph(fa("قیمت واحد"), right_style),
                 Paragraph(fa("جمع"), right_style)]
            ]
            
            for i, item in enumerate(items, 1):
                items_data.append([
                    Paragraph(fa(str(i)), right_style),
                    Paragraph(fa(item.get('product_name', '')), right_style),
                    Paragraph(fa(f"{item.get('quantity', 0):,.2f}"), right_style),
                    Paragraph(fa(f"{item.get('unit_price', 0):,.0f}"), right_style),
                    Paragraph(fa(f"{item.get('total_price', 0):,.0f}"), right_style)
                ])
            
            items_table = Table(items_data, colWidths=[doc_builder.width*0.08, doc_builder.width*0.42, doc_builder.width*0.15, doc_builder.width*0.15, doc_builder.width*0.20])
            items_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'PersianFont'),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.15, 0.17, 0.46)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(items_table)
            elements.append(Spacer(1, 15))
            
            # ========== جمع‌ها ==========
            totals_data = [
                [Paragraph(fa("جمع کل:"), right_style), Paragraph(fa(f"{invoice['total_amount']:,.0f}"), right_style)],
                [Paragraph(fa("تخفیف:"), right_style), Paragraph(fa(f"{invoice['discount']:,.0f}"), right_style)],
                [Paragraph(fa(f"مالیات ({tax_percent}%):"), right_style), Paragraph(fa(f"{invoice['tax']:,.0f}"), right_style)],
            ]
            
            totals_table = Table(totals_data, colWidths=[doc_builder.width*0.7, doc_builder.width*0.3])
            totals_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'PersianFont'),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(totals_table)
            elements.append(Spacer(1, 10))
            
            # ========== مبلغ قابل پرداخت ==========
            net_para = Paragraph(
                fa(f"💵 مبلغ قابل پرداخت: {invoice['net_amount']:,.0f} ریال"),
                ParagraphStyle('Net', parent=right_style, fontSize=14, textColor=colors.green)
            )
            elements.append(net_para)
            elements.append(Spacer(1, 20))
            
            # ========== فوتر ==========
            footer_text = f"تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')} | ImanAccount - حسابداری هوشمند"
            elements.append(Paragraph(fa(footer_text), 
                ParagraphStyle('Footer', parent=center_style, fontSize=8, textColor=colors.grey)))
            
            doc_builder.build(elements)
            
        except Exception as e:
            raise e


# ============================================================
# دیالوگ ایجاد فاکتور فروش
# ============================================================

class InvoiceDialog(QDialog):
    """دیالوگ ایجاد فاکتور فروش"""
    
    def __init__(self, products, parties, customer_name="", tax_rate=0.09, parent=None):
        super().__init__(parent)
        self.products = products
        self.parties = parties
        self.customer_name = customer_name
        self.tax_rate = tax_rate
        self.items = []
        self._total_amount = 0
        self._discount = 0
        self._tax = 0
        self._net_amount = 0
        
        self.setWindowTitle("➕ فاکتور فروش جدید")
        self.setGeometry(200, 100, 850, 650)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # فرم اطلاعات اصلی
        form_widget = QWidget()
        form_widget.setStyleSheet("background: #f8f9fa; border-radius: 8px; padding: 5px;")
        form_layout = QHBoxLayout(form_widget)
        
        self.date = ShamsiDateEdit()
        self.date.setStyleSheet("padding: 5px; border-radius: 5px;")
        form_layout.addWidget(QLabel("📅 تاریخ:"))
        form_layout.addWidget(self.date)
        
        self.party_combo = QComboBox()
        self.party_combo.setMinimumWidth(200)
        self.party_combo.setStyleSheet("padding: 5px; border-radius: 5px;")
        for p in self.parties:
            self.party_combo.addItem(f"{p['code']} - {p['name']}", p['id'])
        form_layout.addWidget(QLabel("👤 مشتری:"))
        form_layout.addWidget(self.party_combo)
        form_layout.addStretch()
        
        layout.addWidget(form_widget)
        
        # جدول اقلام
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
        
        # جمع‌ها
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
        
        tax_percent = int(self.tax_rate * 100)
        tax_info = QLabel(f"ℹ️ نرخ مالیات: {tax_percent}%")
        tax_info.setStyleSheet("color: #7f8c8d; font-size: 9pt; font-style: italic;")
        totals_layout.addWidget(tax_info, 4, 0, 1, 2)
        
        totals_layout.setColumnStretch(2, 1)
        layout.addWidget(totals_widget)
        
        # دکمه‌ها
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
        save_btn.clicked.connect(self.save_invoice)
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
            add_btn.setToolTip("هیچ کالایی با موجودی وجود ندارد!")
    
    def add_product_row(self):
        if len(self.products) == 0:
            QMessageBox.warning(self, "خطا", 
                "⚠️ هیچ کالایی با موجودی در سیستم وجود ندارد!")
            return
        
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        # انتخاب کالا
        combo = QComboBox()
        combo.setStyleSheet("padding: 5px; border-radius: 5px;")
        for p in self.products:
            stock = p['stock'] or 0
            combo.addItem(f"{p['code']} - {p['name']} ({stock:,.0f})", p['id'])
        self.items_table.setCellWidget(row, 0, combo)
        
        # تعداد
        quantity_spin = QDoubleSpinBox()
        quantity_spin.setRange(0.01, 999999)
        quantity_spin.setValue(1)
        quantity_spin.setDecimals(2)
        quantity_spin.setSingleStep(1)
        quantity_spin.setStyleSheet("padding: 5px; border-radius: 5px;")
        quantity_spin.valueChanged.connect(self.calculate_totals)
        self.items_table.setCellWidget(row, 1, quantity_spin)
        
        # قیمت واحد
        price_edit = QLineEdit()
        price_edit.setAlignment(Qt.AlignRight)
        price_edit.setPlaceholderText("قیمت فروش")
        price_edit.setStyleSheet("padding: 5px; border-radius: 5px; border: 1px solid #ccc;")
        price_edit.textChanged.connect(self.calculate_totals)
        self.items_table.setCellWidget(row, 2, price_edit)
        
        # جمع
        total_label = QLabel("۰")
        total_label.setAlignment(Qt.AlignRight)
        total_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        self.items_table.setCellWidget(row, 3, total_label)
        
        # دکمه حذف
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
        
        # اتصال رویدادها
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
                        price_widget.setText(f"{p['sale_price']:,}")
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
        
        tax = int(total * self.tax_rate)
        net = total - discount + tax
        
        self.total_label.setText(f"{total:,.0f}")
        self.tax_label.setText(f"{tax:,.0f}")
        self.net_label.setText(f"{net:,.0f} ریال")
        
        self._total_amount = total
        self._discount = discount
        self._tax = tax
        self._net_amount = net
    
    def save_invoice(self):
        """ذخیره فاکتور"""
        if self.party_combo.currentIndex() < 0:
            QMessageBox.warning(self, "خطا", "لطفاً مشتری را انتخاب کنید!")
            return
        
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "حداقل یک کالا به فاکتور اضافه کنید!")
            return
        
        items = []
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 0)
            quantity_spin = self.items_table.cellWidget(row, 1)
            price_widget = self.items_table.cellWidget(row, 2)
            
            if combo and combo.currentIndex() >= 0:
                product_id = combo.currentData()
                quantity = quantity_spin.value()
                price_text = price_widget.text().replace(',', '')
                unit_price = int(price_text) if price_text else 0
                total_price = quantity * unit_price
                
                if unit_price > 0 and quantity > 0:
                    items.append({
                        'product_id': product_id,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total_price': total_price
                    })
        
        if not items:
            QMessageBox.warning(self, "خطا", "هیچ آیتم معتبری وجود ندارد!")
            return
        
        party_id = self.party_combo.currentData()
        shamsi_date = self.date.get_shamsi()
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                # تولید شماره فاکتور
                c.execute("SELECT MAX(CAST(SUBSTR(invoice_no, 4) AS INTEGER)) FROM invoices WHERE invoice_no LIKE 'INV%'")
                max_no = c.fetchone()[0]
                invoice_no = f"INV{(max_no or 0) + 1:06d}"
                
                c.execute('''
                    INSERT INTO invoices (invoice_no, date, party_id, total_amount, discount, tax, net_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', [invoice_no, shamsi_date, party_id, self._total_amount, self._discount, self._tax, self._net_amount])
                
                invoice_id = c.lastrowid
                
                for item in items:
                    c.execute('''
                        INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [invoice_id, item['product_id'], item['quantity'], item['unit_price'], item['total_price']])
                    
                    # کاهش موجودی
                    InventoryHelper.update_stock(item['product_id'], item['quantity'], 'out')
                
                conn.commit()
            
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا در ذخیره فاکتور: {str(e)}")
