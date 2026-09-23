# ui/document_widget.py
# ============================================================
# ویجت یکپارچه خرید و فروش - نسخه 3.0 (Refactored)
# با پشتیبانی کامل از warehouse_stock و Migration خودکار
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from ui.base_widgets import BaseWidget, BaseDialog
from database import get_db, DocumentHelper, ModuleLimitHelper
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali
from screen_utils import ScreenManager
import os
import csv
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ========== پشتیبانی از PDF ==========
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    from PIL import Image
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("ReportLab یا PIL نصب نیست. برای چاپ PDF: pip install reportlab pillow")

# ========== پشتیبانی از فارسی ==========
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    PERSIAN_SUPPORT = True
except ImportError:
    PERSIAN_SUPPORT = False
    logger.warning("کتابخانه‌های فارسی نصب نیستند.")


# ============================================================
# ========== Migration ==========
# ============================================================

def _migrate_products_stock_to_warehouse() -> dict:
    """
    اطمینان از همگام‌سازی products.stock با warehouse_stock.
    
    این تابع باید یک بار هنگام راه‌اندازی برنامه اجرا بشه.
    
    Returns:
        dict: {'migrated': N, 'fixed': M, 'errors': [...]}
    """
    result = {'migrated': 0, 'fixed': 0, 'errors': []}
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # 1. پیدا کردن انبار پیش‌فرض
            default_warehouse_id = None
            for query in [
                "SELECT id FROM warehouses WHERE is_default = 1 AND is_active = 1 LIMIT 1",
                "SELECT id FROM warehouses WHERE is_active = 1 ORDER BY id LIMIT 1",
            ]:
                c.execute(query)
                row = c.fetchone()
                if row:
                    default_warehouse_id = row[0] if not hasattr(row, 'keys') else row['id']
                    break
            
            if not default_warehouse_id:
                result['errors'].append("هیچ انبار فعالی یافت نشد")
                logger.warning("Migration: هیچ انبار فعالی وجود ندارد — رد شد")
                return result
            
            # 2. کالاهایی که در warehouse_stock هیچ رکوردی ندارند ولی موجودی دارند
            c.execute("""
                SELECT p.id, p.code, p.name, p.stock
                FROM products p
                WHERE p.stock > 0
                  AND NOT EXISTS (
                      SELECT 1 FROM warehouse_stock ws 
                      WHERE ws.product_id = p.id AND ws.warehouse_id = ?
                  )
            """, [default_warehouse_id])
            
            for r in c.fetchall():
                product_id = r['id'] if hasattr(r, 'keys') else r[0]
                product_code = r['code'] if hasattr(r, 'keys') else r[1]
                product_stock = r['stock'] if hasattr(r, 'keys') else r[3]
                
                c.execute("""
                    INSERT INTO warehouse_stock 
                    (product_id, warehouse_id, quantity, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, [product_id, default_warehouse_id, product_stock])
                
                result['migrated'] += 1
                logger.info(f"Migration: {product_code} → {product_stock:,.2f} واحد منتقل شد")
            
            # 3. بررسی اختلاف بین products.stock و مجموع warehouse_stock
            c.execute("""
                SELECT p.id, p.code, p.stock,
                       COALESCE(
                           (SELECT SUM(quantity) FROM warehouse_stock WHERE product_id = p.id),
                           0
                       ) as ws_total
                FROM products p
                WHERE p.stock > 0
            """)
            
            for r in c.fetchall():
                product_id = r['id'] if hasattr(r, 'keys') else r[0]
                product_code = r['code'] if hasattr(r, 'keys') else r[1]
                product_stock = r['stock'] if hasattr(r, 'keys') else r[2]
                ws_total = r['ws_total'] if hasattr(r, 'keys') else r[3]
                
                diff = product_stock - ws_total
                if abs(diff) > 0.01:
                    c.execute("""
                        INSERT INTO warehouse_stock 
                        (product_id, warehouse_id, quantity, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(product_id, warehouse_id) DO UPDATE SET
                            quantity = quantity + ?,
                            updated_at = CURRENT_TIMESTAMP
                    """, [product_id, default_warehouse_id, diff, diff])
                    
                    result['fixed'] += 1
                    logger.info(f"Migration: {product_code}: اختلاف {diff:,.2f} اصلاح شد")
            
            conn.commit()
            
            if result['migrated'] or result['fixed']:
                logger.info(f"✅ Migration: {result['migrated']} منتقل، {result['fixed']} اصلاح")
            else:
                logger.info("✅ Migration: همه چیز همگام است")
            
            return result
    
    except Exception as e:
        logger.error(f"خطا در Migration: {e}", exc_info=True)
        result['errors'].append(str(e))
        return result


def run_migration_if_needed():
    """اجرای Migration فقط یک بار در طول اجرای برنامه."""
    if not hasattr(run_migration_if_needed, '_done'):
        _migrate_products_stock_to_warehouse()
        run_migration_if_needed._done = True


# ============================================================
# ========== توابع کمکی ==========
# ============================================================

def row_to_dict(row):
    """تبدیل sqlite3.Row به dict"""
    if row is None:
        return {}
    try:
        return {key: row[key] for key in row.keys()}
    except Exception:
        return {}


def get_default_warehouse_id(cursor) -> int:
    """
    دریافت شناسه انبار پیش‌فرض.
    اگر انبار پیش‌فرض نبود، اولین انبار فعال را برمی‌گرداند.
    """
    try:
        cursor.execute(
            "SELECT id FROM warehouses WHERE is_default = 1 AND is_active = 1 LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return row['id'] if hasattr(row, 'keys') else row[0]
        
        cursor.execute(
            "SELECT id FROM warehouses WHERE is_active = 1 ORDER BY id LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return row['id'] if hasattr(row, 'keys') else row[0]
    except Exception as e:
        logger.error(f"خطا در دریافت انبار پیش‌فرض: {e}")
    
    return None


def get_product_real_stock(product_id: int, warehouse_id: int = None) -> float:
    """
    دریافت موجودی واقعی کالا از warehouse_stock.
    اگر warehouse_id داده نشود، مجموع همه انبارها را برمی‌گرداند.
    """
    try:
        with get_db() as conn:
            c = conn.cursor()
            if warehouse_id:
                c.execute(
                    "SELECT COALESCE(quantity, 0) FROM warehouse_stock "
                    "WHERE product_id = ? AND warehouse_id = ?",
                    [product_id, warehouse_id]
                )
            else:
                c.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM warehouse_stock "
                    "WHERE product_id = ?",
                    [product_id]
                )
            row = c.fetchone()
            return float(row[0]) if row else 0.0
    except Exception as e:
        logger.error(f"خطا در دریافت موجودی: {e}")
        return 0.0


def update_inventory(cursor, product_id: int, quantity: float,
                     doc_type: str, reverse: bool = False) -> bool:
    """
    به‌روزرسانی همزمان products.stock و warehouse_stock.
    
    Args:
        cursor: نشانگر دیتابیس
        product_id: شناسه کالا
        quantity: مقدار (همیشه مثبت)
        doc_type: 'sales' یا 'purchase'
        reverse: اگر True باشد، عمل برعکس انجام می‌شود (برای حذف/ویرایش)
    
    Returns:
        True اگر موفق، False در غیر این صورت
    """
    try:
        warehouse_id = get_default_warehouse_id(cursor)
        
        # فروش: کاهش موجودی | خرید: افزایش موجودی
        # reverse=True: عمل برعکس
        if doc_type == 'sales':
            is_increase = reverse
        else:
            is_increase = not reverse
        
        # ===== 1. products.stock =====
        if is_increase:
            cursor.execute(
                "UPDATE products SET stock = stock + ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [quantity, product_id]
            )
        else:
            cursor.execute(
                "UPDATE products SET stock = stock - ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [quantity, product_id]
            )
        
        # ===== 2. warehouse_stock =====
        if warehouse_id:
            if is_increase:
                cursor.execute("""
                    INSERT INTO warehouse_stock 
                    (product_id, warehouse_id, quantity, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(product_id, warehouse_id) DO UPDATE SET
                        quantity = quantity + ?,
                        updated_at = CURRENT_TIMESTAMP
                """, [product_id, warehouse_id, quantity, quantity])
            else:
                cursor.execute("""
                    UPDATE warehouse_stock 
                    SET quantity = quantity - ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ? AND warehouse_id = ?
                """, [quantity, product_id, warehouse_id])
                
                # اگر رکورد وجود نداشت، بساز (با مقدار منفی برای ردیابی)
                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO warehouse_stock 
                        (product_id, warehouse_id, quantity, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """, [product_id, warehouse_id, -quantity])
        
        return True
    
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی موجودی: {e}", exc_info=True)
        return False


# ============================================================
# ========== ویجت اصلی ============
# ============================================================

class DocumentWidget(BaseWidget):
    """ویجت یکپارچه خرید و فروش"""
    
    document_changed = pyqtSignal()
    
    def __init__(self, customer_name: str = "", user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        self.customer_name = customer_name
        self.user_level = user_level
        self.documents_data = []
        self.products = []
        self.parties = []
        self.current_doc_type = "sales"
        self.current_document = None
        self.current_items = []
        self.screen_manager = ScreenManager()
        
        # اجرای Migration یک بار
        run_migration_if_needed()
        
        self.tax_rate = self._get_tax_rate()
        self.company_info = self._get_company_info()
        
        self.setup_ui()
        self.load_data()
        self.update_ui_by_permission()
        self.apply_theme()
    
    # ============================================================
    # تنظیمات
    # ============================================================
    
    def _get_tax_rate(self) -> float:
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'tax_rate'")
                row = c.fetchone()
                if row:
                    return float(row[0]) / 100
                return 0.09
        except Exception as e:
            logger.warning(f"خطا در دریافت نرخ مالیات: {e}")
            return 0.09
    
    def _get_company_info(self) -> dict:
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT key, value FROM settings WHERE key LIKE 'company_%'")
                info = {}
                for row in c.fetchall():
                    info[row['key']] = row['value']
                
                if not info.get('company_name'):
                    info['company_name'] = 'شرکت حسابداری پارسه'
                return info
        except Exception as e:
            logger.warning(f"خطا در دریافت اطلاعات شرکت: {e}")
            return {
                'company_name': 'شرکت حسابداری پارسه',
                'company_phone': '021-12345678',
                'company_address': 'تهران، خیابان اصلی، پلاک 123'
            }
    
    # ============================================================
    # مدیریت سطح دسترسی
    # ============================================================
    
    def set_user_level(self, level: str):
        self.user_level = level
        self.update_ui_by_permission()
    
    def update_ui_by_permission(self):
        can_edit = self.user_level in ['admin', 'accountant', 'inventory']
        can_view = self.user_level in ['admin', 'accountant', 'inventory', 'viewer']
        can_delete = self.user_level in ['admin', 'accountant']
        
        if hasattr(self, 'new_btn'):
            self.new_btn.setVisible(can_edit)
        if hasattr(self, 'edit_btn'):
            self.edit_btn.setVisible(can_edit)
        if hasattr(self, 'delete_btn'):
            self.delete_btn.setVisible(can_delete)
        if hasattr(self, 'print_btn'):
            self.print_btn.setVisible(can_view)
        if hasattr(self, 'pdf_btn'):
            self.pdf_btn.setVisible(can_view)
        
        if hasattr(self, 'table'):
            if not can_edit:
                self.table.setEditTriggers(QTableWidget.NoEditTriggers)
            else:
                self.table.setEditTriggers(
                    QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
                )
    
    # ============================================================
    # رابط کاربری
    # ============================================================
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(self.margin(10), self.margin(10),
                                  self.margin(10), self.margin(10))
        
        # ========== پنل راست ==========
        right_panel = QWidget()
        right_panel.setObjectName("cardWidget")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(self.spacing(10))
        
        title_layout = QHBoxLayout()
        title = QLabel("📄 اسناد خرید و فروش")
        title.setObjectName("titleLabel")
        title_layout.addWidget(title)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 9pt; padding: 5px;")
        title_layout.addWidget(self.status_label)
        title_layout.addStretch()
        
        right_layout.addLayout(title_layout)
        
        toolbar = self._create_toolbar()
        right_layout.addLayout(toolbar)
        
        # نوع سند
        type_layout = QHBoxLayout()
        type_layout.setSpacing(self.spacing(8))
        type_layout.addWidget(QLabel("📂 نوع سند:"))
        
        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItems(["📤 فاکتور فروش", "📥 فاکتور خرید"])
        self.doc_type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.doc_type_combo.setMinimumHeight(self.scaled(32))
        self.doc_type_combo.setStyleSheet("padding: 5px; border-radius: 5px;")
        type_layout.addWidget(self.doc_type_combo)
        
        type_layout.addStretch()
        right_layout.addLayout(type_layout)
        
        # فیلترها
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(self.spacing(8))
        
        filter_layout.addWidget(QLabel("🔍 جستجو:"))
        self.search_input = self.create_input("شماره سند، طرف حساب...")
        self.search_input.textChanged.connect(self.filter_documents)
        filter_layout.addWidget(self.search_input)
        
        filter_layout.addWidget(QLabel("از:"))
        self.filter_from_date = ShamsiDateEdit()
        self.filter_from_date.dateChanged.connect(self.filter_documents)
        filter_layout.addWidget(self.filter_from_date)
        
        filter_layout.addWidget(QLabel("تا:"))
        self.filter_to_date = ShamsiDateEdit()
        self.filter_to_date.dateChanged.connect(self.filter_documents)
        filter_layout.addWidget(self.filter_to_date)
        
        clear_filter_btn = self.create_button("✖️", "dangerBtn")
        clear_filter_btn.setMaximumWidth(self.scaled(30))
        clear_filter_btn.setToolTip("پاک کردن فیلترها")
        clear_filter_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_filter_btn)
        
        right_layout.addLayout(filter_layout)
        
        # جدول
        self.table = self.create_table(
            ["شماره", "تاریخ", "طرف حساب", "کل", "تخفیف", "مالیات", "خالص", "وضعیت"],
            stretch_last=True
        )
        self.table.setColumnWidth(0, self.scaled(100))
        self.table.setColumnWidth(1, self.scaled(100))
        self.table.setColumnWidth(2, self.scaled(150))
        self.table.clicked.connect(self.on_document_selected)
        self.table.doubleClicked.connect(self.edit_document)
        right_layout.addWidget(self.table)
        
        # آمار
        self.stats_label = QLabel("📊 مجموع: ۰ سند | ۰ ریال")
        self.stats_label.setStyleSheet("""
            font-weight: bold;
            padding: 8px 12px;
            background: #f0f0f0;
            border-radius: 5px;
            color: #2c3e50;
        """)
        right_layout.addWidget(self.stats_label)
        
        # ========== پنل چپ ==========
        left_panel = QWidget()
        left_panel.setObjectName("cardWidget")
        left_panel.setMaximumWidth(self.scaled(500))
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(self.spacing(10))
        
        detail_title = QLabel("📋 جزئیات سند")
        detail_title.setObjectName("subtitleLabel")
        left_layout.addWidget(detail_title)
        
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setDocumentMode(True)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("یک سند را انتخاب کنید...")
        self.details_text.setStyleSheet("""
            QTextEdit {
                font-family: Tahoma;
                font-size: 10pt;
                padding: 10px;
                background: #fafafa;
                border: none;
            }
        """)
        self.detail_tabs.addTab(self.details_text, "📄 اطلاعات")
        
        self.items_detail_table = self.create_table(
            ["کد", "کالا", "تعداد", "فی", "جمع"],
            stretch_last=True
        )
        self.detail_tabs.addTab(self.items_detail_table, "📦 اقلام")
        
        left_layout.addWidget(self.detail_tabs)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(self.spacing(8))
        
        self.print_btn = self.create_button("🖨️ چاپ", "infoBtn")
        self.print_btn.clicked.connect(self.print_document)
        btn_layout.addWidget(self.print_btn)
        
        self.pdf_btn = self.create_button("📄 PDF", "successBtn")
        self.pdf_btn.clicked.connect(self.save_as_pdf)
        btn_layout.addWidget(self.pdf_btn)
        
        btn_layout.addStretch()
        
        excel_btn = self.create_button("📊 Excel", "warningBtn")
        excel_btn.clicked.connect(self.export_to_excel)
        btn_layout.addWidget(excel_btn)
        
        left_layout.addLayout(btn_layout)
        
        self.detail_status = QLabel("")
        self.detail_status.setStyleSheet("color: #888; font-size: 9pt; padding: 5px;")
        left_layout.addWidget(self.detail_status)
        
        layout.addWidget(right_panel, 2)
        layout.addWidget(left_panel, 1)
        
        # تاریخ‌های فیلتر
        today = get_today_jalali()
        self.filter_from_date.set_date(today)
        self.filter_to_date.set_date(today)
        
        self.apply_theme()
    
    def _create_toolbar(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(self.spacing(8))
        
        self.new_btn = self.create_button("➕ سند جدید", "successBtn")
        self.new_btn.clicked.connect(self.new_document)
        toolbar.addWidget(self.new_btn)
        
        self.edit_btn = self.create_button("✏️ ویرایش", "warningBtn")
        self.edit_btn.clicked.connect(self.edit_document)
        toolbar.addWidget(self.edit_btn)
        
        self.delete_btn = self.create_button("🗑️ حذف", "dangerBtn")
        self.delete_btn.clicked.connect(self.delete_document)
        toolbar.addWidget(self.delete_btn)
        
        toolbar.addStretch()
        
        refresh_btn = self.create_button("🔄 بروزرسانی", "infoBtn")
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        return toolbar
    
    # ============================================================
    # بارگذاری داده‌ها
    # ============================================================
    
    def load_data(self):
        doc_type = "sales" if self.current_doc_type == "sales" else "purchase"
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT d.*, p.name as party_name 
                    FROM documents d 
                    JOIN parties p ON d.party_id = p.id 
                    WHERE d.doc_type = ? 
                    ORDER BY d.id DESC
                """, [doc_type])
                self.documents_data = [row_to_dict(row) for row in c.fetchall()]
                
                # کالاها با موجودی واقعی
                price_col = 'sale_price' if self.current_doc_type == "sales" else 'purchase_price'
                c.execute(f"""
                    SELECT p.id, p.code, p.name, p.{price_col} as price,
                           p.stock,
                           COALESCE(
                               (SELECT SUM(quantity) FROM warehouse_stock 
                                WHERE product_id = p.id), 
                               0
                           ) as real_stock
                    FROM products p
                    ORDER BY p.code
                """)
                self.products = [row_to_dict(row) for row in c.fetchall()]
                
                # اشخاص
                party_type = "customer" if doc_type == "sales" else "supplier"
                c.execute(
                    'SELECT id, code, name FROM parties WHERE type = ? ORDER BY name',
                    [party_type]
                )
                self.parties = [row_to_dict(row) for row in c.fetchall()]
            
            self.display_documents()
            self.update_stats()
        
        except Exception as e:
            logger.error(f"خطا در بارگذاری داده‌ها: {e}", exc_info=True)
            self.documents_data = []
            self.display_documents([])
    
    def display_documents(self, data=None):
        data = data if data is not None else self.documents_data
        self.table.setRowCount(len(data))
        
        for i, doc in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(doc.get('doc_no', '')))
            self.table.setItem(i, 1, QTableWidgetItem(
                safe_display_date(doc.get('date', '')) if doc.get('date') else ''
            ))
            self.table.setItem(i, 2, QTableWidgetItem(doc.get('party_name', '')))
            
            for col_idx, key in enumerate(
                ['total_amount', 'discount', 'tax', 'net_amount'], start=3
            ):
                value = doc.get(key, 0) or 0
                item = QTableWidgetItem(f"{value:,.0f}")
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col_idx == 6:
                    if value > 0:
                        item.setForeground(QColor('#27ae60'))
                    else:
                        item.setForeground(QColor('#e74c3c'))
                self.table.setItem(i, col_idx, item)
            
            status = "✅ تأیید" if doc.get('is_approved', 0) else "⏳ در انتظار"
            status_item = QTableWidgetItem(status)
            if doc.get('is_approved', 0):
                status_item.setForeground(QColor('#27ae60'))
            else:
                status_item.setForeground(QColor('#f39c12'))
            self.table.setItem(i, 7, status_item)
    
    def update_stats(self):
        total_count = len(self.documents_data)
        total_amount = sum(doc.get('net_amount', 0) or 0 for doc in self.documents_data)
        doc_type_text = "فروش" if self.current_doc_type == "sales" else "خرید"
        self.stats_label.setText(
            f"📊 مجموع: {total_count} سند {doc_type_text} | {total_amount:,.0f} ریال"
        )
    
    # ============================================================
    # فیلتر
    # ============================================================
    
    def filter_documents(self):
        search_text = self.search_input.text().strip().lower()
        from_date = self.filter_from_date.get_shamsi()
        to_date = self.filter_to_date.get_shamsi()
        
        if not search_text and not from_date and not to_date:
            self.display_documents(self.documents_data)
            return
        
        filtered = []
        for doc in self.documents_data:
            match_search = True
            if search_text:
                doc_no = doc.get('doc_no', '').lower()
                party_name = doc.get('party_name', '').lower()
                match_search = search_text in doc_no or search_text in party_name
            
            match_date = True
            doc_date = doc.get('date', '') or ''
            if from_date and doc_date < from_date:
                match_date = False
            if to_date and doc_date > to_date:
                match_date = False
            
            if match_search and match_date:
                filtered.append(doc)
        
        self.display_documents(filtered)
    
    def clear_filters(self):
        self.search_input.clear()
        today = get_today_jalali()
        self.filter_from_date.set_date(today)
        self.filter_to_date.set_date(today)
        self.display_documents(self.documents_data)
    
    # ============================================================
    # نمایش جزئیات
    # ============================================================
    
    def on_document_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        
        doc_no = self.table.item(row, 0).text()
        for doc in self.documents_data:
            if doc.get('doc_no') == doc_no:
                self.current_document = doc
                self.show_document_details(doc)
                break
    
    def show_document_details(self, doc):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT di.*, p.code as product_code, p.name as product_name
                    FROM document_items di
                    JOIN products p ON di.product_id = p.id
                    WHERE di.document_id = ?
                """, [doc.get('id')])
                self.current_items = [row_to_dict(row) for row in c.fetchall()]
            
            html = self._generate_detail_html(doc, self.current_items)
            self.details_text.setHtml(html)
            self.display_items_table(self.current_items)
            
            status_text = "✅ تأیید شده" if doc.get('is_approved', 0) else "⏳ در انتظار تأیید"
            self.detail_status.setText(f"📌 وضعیت: {status_text}")
            if doc.get('is_approved', 0):
                self.detail_status.setStyleSheet("color: #27ae60; font-size: 9pt; padding: 5px;")
            else:
                self.detail_status.setStyleSheet("color: #f39c12; font-size: 9pt; padding: 5px;")
        
        except Exception as e:
            logger.error(f"خطا در نمایش جزئیات: {e}", exc_info=True)
            self.details_text.setText(f"⚠️ خطا: {str(e)}")
    
    def _generate_detail_html(self, doc, items):
        doc_type_text = "فروش" if doc.get('doc_type') == 'sales' else "خرید"
        party_type_text = "مشتری" if doc.get('doc_type') == 'sales' else "تأمین‌کننده"
        
        html = f"""
        <div style='font-family: Tahoma; direction: rtl; font-size: 10pt;'>
            <h3 style='text-align: center; color: #273c75;'>📄 فاکتور {doc_type_text}</h3>
            
            <table width='100%' style='margin: 10px 0;'>
                <tr><td><b>شماره:</b></td><td>{doc.get('doc_no', '')}</td></tr>
                <tr><td><b>تاریخ:</b></td><td>{safe_display_date(doc.get('date', '')) if doc.get('date') else ''}</td></tr>
                <tr><td><b>{party_type_text}:</b></td><td>{doc.get('party_name', '')}</td></tr>
            </table>
            
            <hr>
            
            <h4>📦 اقلام فاکتور:</h4>
            <table width='100%' border='1' style='border-collapse: collapse;'>
                <tr style='background: #273c75; color: white;'>
                    <th>کد</th><th>کالا</th><th>تعداد</th><th>قیمت واحد</th><th>جمع</th>
                </tr>
        """
        
        for item in items:
            html += f"""
                <tr>
                    <td>{item.get('product_code', '')}</td>
                    <td>{item.get('product_name', '')}</td>
                    <td style='text-align: center;'>{item.get('quantity', 0):,.2f}</td>
                    <td style='text-align: left;'>{item.get('unit_price', 0):,.0f}</td>
                    <td style='text-align: left;'>{item.get('total_price', 0):,.0f}</td>
                </tr>
            """
        
        tax_percent = int(self.tax_rate * 100)
        html += f"""
            </table>
            <hr>
            <table width='100%'>
                <tr><td><b>جمع کل:</b></td><td style='text-align: left;'>{doc.get('total_amount', 0):,.0f} ریال</td></tr>
                <tr><td><b>تخفیف:</b></td><td style='text-align: left;'>{doc.get('discount', 0):,.0f} ریال</td></tr>
                <tr><td><b>مالیات ({tax_percent}%):</b></td><td style='text-align: left;'>{doc.get('tax', 0):,.0f} ریال</td></tr>
                <tr style='font-weight: bold; font-size: 12pt;'>
                    <td style='color: #27ae60;'>💵 مبلغ قابل پرداخت:</td>
                    <td style='text-align: left; color: #27ae60;'>{doc.get('net_amount', 0):,.0f} ریال</td>
                </tr>
            </table>
        </div>
        """
        return html
    
    def display_items_table(self, items):
        self.items_detail_table.setRowCount(len(items))
        
        for i, item in enumerate(items):
            self.items_detail_table.setItem(i, 0, QTableWidgetItem(item.get('product_code', '')))
            self.items_detail_table.setItem(i, 1, QTableWidgetItem(item.get('product_name', '')))
            
            qty_item = QTableWidgetItem(f"{item.get('quantity', 0):,.2f}")
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_detail_table.setItem(i, 2, qty_item)
            
            price_item = QTableWidgetItem(f"{item.get('unit_price', 0):,.0f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_detail_table.setItem(i, 3, price_item)
            
            total_item = QTableWidgetItem(f"{item.get('total_price', 0):,.0f}")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            total_item.setForeground(QColor('#27ae60'))
            self.items_detail_table.setItem(i, 4, total_item)
    
    # ============================================================
    # عملیات اصلی
    # ============================================================
    
    def on_type_changed(self):
        self.current_doc_type = "sales" if self.doc_type_combo.currentIndex() == 0 else "purchase"
        self.load_data()
        self.clear_details()
    
    def new_document(self):
        if not self.check_document_limit():
            return
        
        if not self.products:
            QMessageBox.warning(self, "خطا",
                "⚠️ هیچ کالایی در سیستم تعریف نشده است!\n"
                "لطفاً ابتدا از بخش انبار کالا تعریف کنید.")
            return
        
        if not self.parties:
            QMessageBox.warning(self, "خطا",
                "⚠️ هیچ طرف حسابی در سیستم تعریف نشده است!\n"
                "لطفاً ابتدا از بخش اشخاص تعریف کنید.")
            return
        
        dialog = DocumentDialog(
            self.products,
            self.parties,
            self.current_doc_type,
            self,
            self.customer_name,
            self.tax_rate
        )
        
        if dialog.exec_():
            self.load_data()
            self.document_changed.emit()
            QMessageBox.information(self, "موفق", "✅ سند با موفقیت ثبت شد!")
    
    def edit_document(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک سند را انتخاب کنید!")
            return
        
        if self.user_level not in ['admin', 'accountant']:
            QMessageBox.warning(self, "دسترسی محدود",
                "⚠️ فقط مدیر سیستم و حسابدار می‌توانند اسناد را ویرایش کنند!")
            return
        
        doc_no = self.table.item(row, 0).text()
        doc = None
        for d in self.documents_data:
            if d.get('doc_no') == doc_no:
                doc = d
                break
        
        if not doc:
            QMessageBox.warning(self, "خطا", "سند پیدا نشد!")
            return
        
        dialog = DocumentDialog(
            self.products,
            self.parties,
            self.current_doc_type,
            self,
            self.customer_name,
            self.tax_rate,
            doc.get('id')
        )
        
        if dialog.exec_():
            self.load_data()
            self.document_changed.emit()
            QMessageBox.information(self, "موفق", "✅ سند با موفقیت ویرایش شد!")
    
    def delete_document(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک سند را انتخاب کنید!")
            return
        
        if self.user_level not in ['admin', 'accountant']:
            QMessageBox.warning(self, "دسترسی محدود",
                "⚠️ فقط مدیر سیستم و حسابدار می‌توانند اسناد را حذف کنند!")
            return
        
        doc_no = self.table.item(row, 0).text()
        doc_type = self.current_doc_type
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف سند {doc_no} اطمینان دارید؟\n"
            f"این عمل غیرقابل بازگشت است!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute("SELECT id FROM documents WHERE doc_no = ?", [doc_no])
                row_data = c.fetchone()
                if not row_data:
                    QMessageBox.warning(self, "خطا", "سند پیدا نشد!")
                    return
                
                doc_id = row_data['id'] if hasattr(row_data, 'keys') else row_data[0]
                
                # برگرداندن موجودی
                c.execute("""
                    SELECT product_id, quantity 
                    FROM document_items 
                    WHERE document_id = ?
                """, [doc_id])
                
                for item in c.fetchall():
                    product_id = item['product_id'] if hasattr(item, 'keys') else item[0]
                    quantity = item['quantity'] if hasattr(item, 'keys') else item[1]
                    
                    update_inventory(c, product_id, quantity, doc_type, reverse=True)
                
                c.execute('DELETE FROM document_items WHERE document_id = ?', [doc_id])
                c.execute('DELETE FROM documents WHERE id = ?', [doc_id])
                conn.commit()
            
            self.load_data()
            self.clear_details()
            self.document_changed.emit()
            QMessageBox.information(self, "موفق", "✅ سند با موفقیت حذف شد!")
        
        except Exception as e:
            logger.error(f"خطا در حذف سند: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ خطا در حذف سند: {str(e)}")
    
    def clear_details(self):
        self.details_text.clear()
        self.items_detail_table.setRowCount(0)
        self.detail_status.setText("")
        self.current_document = None
        self.current_items = []
    
    # ============================================================
    # محدودیت‌ها
    # ============================================================
    
    def check_document_limit(self) -> bool:
        if self.customer_name:
            module_name = 'invoice' if self.current_doc_type == 'sales' else 'purchase'
            allowed, current, limit, msg = ModuleLimitHelper.check_module_limit(
                self.customer_name, module_name
            )
            if not allowed:
                QMessageBox.warning(self, "خطا",
                    f"❌ به سقف مجاز {limit} فاکتور رسیده‌اید!\n"
                    "برای ثبت فاکتور جدید، لطفاً با مدیر سیستم تماس بگیرید.")
                return False
            elif limit > 0 and limit - current <= 3:
                QMessageBox.warning(self, "هشدار",
                    f"⚠️ فقط {limit - current} فاکتور دیگر تا سقف مجاز باقی مانده.")
        return True
    
    # ============================================================
    # چاپ
    # ============================================================
    
    def print_document(self):
        if not self.current_document:
            QMessageBox.warning(self, "خطا", "لطفاً یک سند را انتخاب کنید!")
            return
        
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
            
            preview_dialog = QPrintPreviewDialog(printer, self)
            preview_dialog.paintRequested.connect(self._print_preview)
            preview_dialog.exec_()
        except Exception as e:
            logger.error(f"خطا در چاپ: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ خطا در چاپ: {str(e)}")
    
    def _print_preview(self, printer):
        html_content = self._generate_print_html()
        doc = QTextDocument()
        doc.setHtml(html_content)
        doc.print_(printer)
    
    def _generate_print_html(self) -> str:
        doc = self.current_document
        if not doc:
            return ""
        
        items = self.current_items
        tax_percent = int(self.tax_rate * 100)
        
        doc_type_text = "فاکتور فروش" if doc.get('doc_type') == 'sales' else "فاکتور خرید"
        party_type = "مشتری" if doc.get('doc_type') == 'sales' else "تأمین‌کننده"
        
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
                font-size: 10pt;
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
                <div class="title">{doc_type_text}</div>
                <div>شماره: {doc.get('doc_no', '')}</div>
            </div>
            
            <div class="info">
                <table>
                    <tr>
                        <td><b>تاریخ:</b> {safe_display_date(doc.get('date', '')) if doc.get('date') else ''}</td>
                        <td><b>{party_type}:</b> {doc.get('party_name', '')}</td>
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
                    <td>{item.get('product_name', '')}</td>
                    <td>{item.get('quantity', 0):,.2f}</td>
                    <td>{item.get('unit_price', 0):,.0f}</td>
                    <td>{item.get('total_price', 0):,.0f}</td>
                </tr>
            """
        
        html += f"""
                </tbody>
            </table>
            
            <div class="totals">
                <table width="100%">
                    <tr><td><b>جمع کل:</b></td><td align="left">{doc.get('total_amount', 0):,.0f} ریال</td></tr>
                    <tr><td><b>تخفیف:</b></td><td align="left">{doc.get('discount', 0):,.0f} ریال</td></tr>
                    <tr><td><b>مالیات ({tax_percent}%):</b></td><td align="left">{doc.get('tax', 0):,.0f} ریال</td></tr>
                    <tr><td colspan="2"><hr></td></tr>
                    <tr><td><b>مبلغ قابل پرداخت:</b></td><td align="left" class="net">{doc.get('net_amount', 0):,.0f} ریال</td></tr>
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
        if not self.current_document:
            QMessageBox.warning(self, "خطا", "لطفاً یک سند را انتخاب کنید!")
            return
        
        if not PDF_AVAILABLE:
            QMessageBox.warning(self, "خطا",
                "کتابخانه ReportLab یا PIL نصب نیست!\n"
                "برای نصب: pip install reportlab pillow")
            return
        
        default_name = f"{self.current_document.get('doc_no', 'snd')}_{datetime.now().strftime('%Y%m%d')}.pdf"
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
            logger.error(f"خطا در ذخیره PDF: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره PDF: {str(e)}")
    
    def _generate_pdf(self, file_path):
        doc = self.current_document
        items = self.current_items
        tax_percent = int(self.tax_rate * 100)
        
        try:
            # بارگذاری فونت
            font_path = "fonts/tahoma.ttf"
            if not os.path.exists(font_path):
                font_path = "C:/Windows/Fonts/tahoma.ttf"
            if not os.path.exists(font_path):
                font_path = "C:/Windows/Fonts/arial.ttf"
            
            pdfmetrics.registerFont(TTFont('PersianFont', font_path))
            
            def fa(text):
                if text is None:
                    text = ""
                reshaped = arabic_reshaper.reshape(str(text))
                return get_display(reshaped)
            
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
            
            doc_builder = SimpleDocTemplate(
                file_path, pagesize=A4,
                rightMargin=15*mm, leftMargin=15*mm,
                topMargin=15*mm, bottomMargin=15*mm
            )
            
            elements = []
            
            # هدر
            elements.append(Paragraph(
                fa(self.company_info.get('company_name', 'شرکت حسابداری پارسه')),
                bold_center_style
            ))
            elements.append(Spacer(1, 5))
            if self.company_info.get('company_phone'):
                elements.append(Paragraph(
                    fa(f"تلفن: {self.company_info.get('company_phone')}"),
                    center_style
                ))
            if self.company_info.get('company_address'):
                elements.append(Paragraph(
                    fa(f"آدرس: {self.company_info.get('company_address')}"),
                    center_style
                ))
            
            elements.append(Spacer(1, 15))
            
            # اطلاعات سند
            doc_type_text = "فاکتور فروش" if doc.get('doc_type') == 'sales' else "فاکتور خرید"
            party_type = "مشتری" if doc.get('doc_type') == 'sales' else "تأمین‌کننده"
            shamsi_date = safe_display_date(doc.get('date', '')) if doc.get('date') else ""
            
            info_data = [
                [Paragraph(fa(f"شماره: {doc.get('doc_no', '')}"), right_style),
                 Paragraph(fa(f"تاریخ: {shamsi_date}"), right_style)],
                [Paragraph(fa(f"{party_type}: {doc.get('party_name', '')}"), right_style),
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
            
            # جدول اقلام
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
            
            items_table = Table(items_data, colWidths=[
                doc_builder.width*0.08, doc_builder.width*0.42,
                doc_builder.width*0.15, doc_builder.width*0.15,
                doc_builder.width*0.20
            ])
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
            
            # جمع‌ها
            totals_data = [
                [Paragraph(fa("جمع کل:"), right_style), Paragraph(fa(f"{doc.get('total_amount', 0):,.0f}"), right_style)],
                [Paragraph(fa("تخفیف:"), right_style), Paragraph(fa(f"{doc.get('discount', 0):,.0f}"), right_style)],
                [Paragraph(fa(f"مالیات ({tax_percent}%):"), right_style), Paragraph(fa(f"{doc.get('tax', 0):,.0f}"), right_style)],
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
            
            net_para = Paragraph(
                fa(f"💵 مبلغ قابل پرداخت: {doc.get('net_amount', 0):,.0f} ریال"),
                ParagraphStyle('Net', parent=right_style, fontSize=14, textColor=colors.green)
            )
            elements.append(net_para)
            elements.append(Spacer(1, 20))
            
            footer_text = f"تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')} | ImanAccount - حسابداری هوشمند"
            elements.append(Paragraph(
                fa(footer_text),
                ParagraphStyle('Footer', parent=center_style, fontSize=8, textColor=colors.grey)
            ))
            
            doc_builder.build(elements)
        
        except Exception as e:
            logger.error(f"خطا در تولید PDF: {e}", exc_info=True)
            raise
    
    def export_to_excel(self):
        if not self.current_document:
            QMessageBox.warning(self, "خطا", "لطفاً یک سند را انتخاب کنید!")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره خروجی Excel",
            f"{self.current_document.get('doc_no', 'snd')}_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not file_name:
            return
        
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ردیف", "کد", "کالا", "تعداد", "قیمت واحد", "جمع"])
                
                for i, item in enumerate(self.current_items, 1):
                    writer.writerow([
                        i,
                        item.get('product_code', ''),
                        item.get('product_name', ''),
                        item.get('quantity', 0),
                        item.get('unit_price', 0),
                        item.get('total_price', 0)
                    ])
                
                writer.writerow([])
                writer.writerow(["شماره سند:", self.current_document.get('doc_no', '')])
                writer.writerow(["تاریخ:", safe_display_date(self.current_document.get('date', '')) if self.current_document.get('date') else ''])
                writer.writerow(["جمع کل:", f"{self.current_document.get('total_amount', 0):,.0f}"])
                writer.writerow(["تخفیف:", f"{self.current_document.get('discount', 0):,.0f}"])
                writer.writerow(["مالیات:", f"{self.current_document.get('tax', 0):,.0f}"])
                writer.writerow(["مبلغ قابل پرداخت:", f"{self.current_document.get('net_amount', 0):,.0f}"])
            
            QMessageBox.information(self, "موفق", f"✅ خروجی در {file_name} ذخیره شد!")
        except Exception as e:
            logger.error(f"خطا در ذخیره: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")


# ============================================================
# دیالوگ ایجاد/ویرایش سند
# ============================================================

class DocumentDialog(BaseDialog):
    """دیالوگ ایجاد و ویرایش سند با به‌روزرسانی صحیح انبار"""
    
    def __init__(self, products, parties, doc_type, parent=None,
                 customer_name="", tax_rate=0.09, doc_id=None):
        super().__init__(parent, base_width=850, base_height=700)
        self.products = products
        self.parties = parties
        self.doc_type = doc_type
        self.customer_name = customer_name
        self.tax_rate = tax_rate
        self.doc_id = doc_id
        self.parent_widget = parent
        self.screen_manager = ScreenManager()
        
        self._total_amount = 0
        self._discount = 0
        self._tax = 0
        self._net_amount = 0
        self._editing = doc_id is not None
        
        doc_type_name = "فروش" if doc_type == 'sales' else "خرید"
        self.setWindowTitle(
            f"✏️ ویرایش سند {doc_type_name}" if self._editing
            else f"➕ سند جدید {doc_type_name}"
        )
        self.setModal(True)
        
        self.setup_ui()
        
        if self._editing:
            self.load_document_data()
        
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(self.margin(10), self.margin(10),
                                  self.margin(10), self.margin(10))
        
        # اطلاعات اصلی
        info_group = QGroupBox("📋 اطلاعات سند")
        info_layout = QHBoxLayout(info_group)
        info_layout.setSpacing(self.spacing(10))
        
        self.date = ShamsiDateEdit()
        self.date.setMinimumHeight(self.scaled(32))
        info_layout.addWidget(QLabel("📅 تاریخ:"))
        info_layout.addWidget(self.date)
        
        self.party_combo = QComboBox()
        self.party_combo.setMinimumWidth(self.scaled(200))
        self.party_combo.setMinimumHeight(self.scaled(32))
        for p in self.parties:
            self.party_combo.addItem(
                f"{p.get('code', '')} - {p.get('name', '')}", p.get('id')
            )
        info_layout.addWidget(QLabel("🏢 طرف حساب:"))
        info_layout.addWidget(self.party_combo)
        
        info_layout.addStretch()
        layout.addWidget(info_group)
        
        # اقلام
        items_group = QGroupBox("📦 اقلام سند")
        items_layout = QVBoxLayout(items_group)
        items_layout.setSpacing(self.spacing(8))
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels([
            "کد", "کالا", "تعداد", "قیمت واحد", "جمع", "موجودی", "عملیات"
        ])
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setMinimumHeight(self.scaled(200))
        items_layout.addWidget(self.items_table)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(self.spacing(8))
        
        add_btn = self.create_button("➕ افزودن کالا", "successBtn")
        add_btn.clicked.connect(self.add_product_row)
        btn_row.addWidget(add_btn)
        
        remove_btn = self.create_button("🗑️ حذف انتخاب", "dangerBtn")
        remove_btn.clicked.connect(self.remove_selected_row)
        btn_row.addWidget(remove_btn)
        
        clear_btn = self.create_button("🧹 پاک کردن همه", "warningBtn")
        clear_btn.clicked.connect(self.clear_all_rows)
        btn_row.addWidget(clear_btn)
        
        btn_row.addStretch()
        items_layout.addLayout(btn_row)
        
        layout.addWidget(items_group)
        
        # جمع‌ها
        totals_group = QGroupBox("💰 جمع‌ها")
        totals_layout = QGridLayout(totals_group)
        totals_layout.setSpacing(self.spacing(10))
        totals_layout.setVerticalSpacing(self.spacing(8))
        
        totals_layout.addWidget(QLabel("جمع کل:"), 0, 0, Qt.AlignRight)
        self.total_label = QLabel("۰")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #2c3e50;")
        self.total_label.setAlignment(Qt.AlignRight)
        totals_layout.addWidget(self.total_label, 0, 1)
        
        totals_layout.addWidget(QLabel("تخفیف (ریال):"), 1, 0, Qt.AlignRight)
        self.discount_input = QLineEdit()
        self.discount_input.setPlaceholderText("۰")
        self.discount_input.setAlignment(Qt.AlignRight)
        self.discount_input.setMaximumWidth(self.scaled(150))
        self.discount_input.setMinimumHeight(self.scaled(32))
        self.discount_input.textChanged.connect(self.calculate_totals)
        totals_layout.addWidget(self.discount_input, 1, 1)
        
        tax_percent = int(self.tax_rate * 100)
        totals_layout.addWidget(QLabel(f"مالیات ({tax_percent}%):"), 2, 0, Qt.AlignRight)
        self.tax_label = QLabel("۰")
        self.tax_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        self.tax_label.setAlignment(Qt.AlignRight)
        totals_layout.addWidget(self.tax_label, 2, 1)
        
        totals_layout.addWidget(QLabel("مبلغ قابل پرداخت:"), 3, 0, Qt.AlignRight)
        self.net_label = QLabel("۰ ریال")
        self.net_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: #27ae60;")
        self.net_label.setAlignment(Qt.AlignRight)
        totals_layout.addWidget(self.net_label, 3, 1)
        
        totals_layout.setColumnStretch(2, 1)
        layout.addWidget(totals_group)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = self.create_button("💾 ذخیره", "successBtn")
        save_btn.setMinimumHeight(self.scaled(40))
        save_btn.setMinimumWidth(self.scaled(120))
        save_btn.clicked.connect(self.save_document)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = self.create_button("❌ انصراف", "dangerBtn")
        cancel_btn.setMinimumHeight(self.scaled(40))
        cancel_btn.setMinimumWidth(self.scaled(120))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        if not self.products:
            add_btn.setEnabled(False)
            add_btn.setToolTip("هیچ کالایی در سیستم وجود ندارد!")
    
    # ============================================================
    # توابع کمکی
    # ============================================================
    
    def scaled(self, value):
        return self.screen_manager.get_scaled(value)
    
    def spacing(self, value=10):
        return self.screen_manager.get_spacing(value)
    
    def margin(self, value=10):
        return self.screen_manager.get_margin(value)
    
    def create_button(self, text, object_name=""):
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        btn.setMinimumHeight(self.scaled(32))
        return btn
    
    # ============================================================
    # مدیریت اقلام
    # ============================================================
    
    def add_product_row(self, product_data=None):
        if not self.products:
            QMessageBox.warning(self, "خطا",
                "⚠️ هیچ کالایی در سیستم وجود ندارد!\n"
                "لطفاً ابتدا از بخش انبار کالا تعریف کنید.")
            return
        
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        self.items_table.setRowHeight(row, self.scaled(35))
        
        # کد
        code_label = QLabel("-")
        code_label.setAlignment(Qt.AlignCenter)
        code_label.setStyleSheet("font-weight: bold; color: #273c75;")
        self.items_table.setCellWidget(row, 0, code_label)
        
        # کالا
        combo = QComboBox()
        combo.setMinimumHeight(self.scaled(30))
        combo.addItem("-- انتخاب کالا --", "")
        for p in self.products:
            stock = p.get('real_stock', p.get('stock', 0)) or 0
            stock_text = f" (موجودی: {stock:,.2f})" if stock > 0 else " (ناموجود)"
            combo.addItem(
                f"{p.get('code', '')} - {p.get('name', '')}{stock_text}",
                p.get('id')
            )
        combo.currentIndexChanged.connect(lambda idx, r=row: self.on_product_changed(r))
        self.items_table.setCellWidget(row, 1, combo)
        
        # تعداد
        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0.01, 999999)
        qty_spin.setValue(1)
        qty_spin.setDecimals(2)
        qty_spin.setSingleStep(1)
        qty_spin.valueChanged.connect(lambda v, r=row: self.calculate_row_total(r))
        self.items_table.setCellWidget(row, 2, qty_spin)
        
        # قیمت
        price_edit = QLineEdit()
        price_edit.setAlignment(Qt.AlignRight)
        price_edit.setPlaceholderText("فی")
        price_edit.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; padding: 5px;")
        price_edit.textChanged.connect(lambda t, r=row: self.calculate_row_total(r))
        self.items_table.setCellWidget(row, 3, price_edit)
        
        # جمع
        total_label = QLabel("۰")
        total_label.setAlignment(Qt.AlignRight)
        total_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        self.items_table.setCellWidget(row, 4, total_label)
        
        # موجودی
        stock_label = QLabel("")
        stock_label.setAlignment(Qt.AlignCenter)
        stock_label.setStyleSheet("font-size: 9pt;")
        self.items_table.setCellWidget(row, 5, stock_label)
        
        # حذف
        remove_btn = QPushButton("🗑️")
        remove_btn.setMaximumWidth(self.scaled(40))
        remove_btn.setMinimumHeight(self.scaled(30))
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        remove_btn.clicked.connect(lambda checked, r=row: self.remove_row(r))
        self.items_table.setCellWidget(row, 6, remove_btn)
        
        if product_data:
            combo_idx = combo.findData(product_data.get('product_id'))
            if combo_idx >= 0:
                combo.setCurrentIndex(combo_idx)
            qty_spin.setValue(product_data.get('quantity', 1))
            price_edit.setText(f"{int(product_data.get('unit_price', 0)):,}")
        else:
            self.on_product_changed(row)
    
    def on_product_changed(self, row):
        """هنگام تغییر کالا — چک موجودی واقعی از warehouse_stock"""
        combo = self.items_table.cellWidget(row, 1)
        if not combo or combo.currentIndex() <= 0:
            return
        
        product_id = combo.currentData()
        product = next((p for p in self.products if p.get('id') == product_id), None)
        if not product:
            return
        
        # کد
        code_label = self.items_table.cellWidget(row, 0)
        if code_label:
            code_label.setText(product.get('code', ''))
        
        # موجودی
        stock_label = self.items_table.cellWidget(row, 5)
        qty_spin = self.items_table.cellWidget(row, 2)
        price_edit = self.items_table.cellWidget(row, 3)
        
        real_stock = product.get('real_stock', product.get('stock', 0)) or 0
        current_qty = qty_spin.value() if qty_spin else 0
        
        if self.doc_type == "sales":
            if real_stock <= 0:
                stock_label.setText("⚠️ ناموجود")
                stock_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 9pt;")
            elif current_qty > real_stock:
                stock_label.setText(f"⚠️ موجودی: {real_stock:,.2f}")
                stock_label.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 9pt;")
            else:
                stock_label.setText(f"✅ {real_stock:,.2f}")
                stock_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 9pt;")
        else:
            stock_label.setText(f"📦 {real_stock:,.2f}")
            stock_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 9pt;")
        
        # قیمت
        if price_edit and not price_edit.text():
            price = product.get('price', 0)
            price_edit.setText(f"{int(price):,}")
        
        self.calculate_row_total(row)
    
    def calculate_row_total(self, row):
        qty_spin = self.items_table.cellWidget(row, 2)
        price_edit = self.items_table.cellWidget(row, 3)
        total_label = self.items_table.cellWidget(row, 4)
        
        if qty_spin and price_edit and total_label:
            try:
                qty = qty_spin.value()
                price_text = price_edit.text().replace(',', '').strip()
                total = qty * (int(float(price_text)) if price_text else 0)
                total_label.setText(f"{total:,.0f}")
            except Exception:
                total_label.setText("۰")
        
        self.calculate_totals()
    
    def remove_row(self, row):
        self.items_table.removeRow(row)
        self.reindex_rows()
        self.calculate_totals()
    
    def remove_selected_row(self):
        row = self.items_table.currentRow()
        if row >= 0:
            self.remove_row(row)
    
    def clear_all_rows(self):
        if self.items_table.rowCount() == 0:
            return
        
        reply = QMessageBox.question(self, "تأیید",
            "آیا از پاک کردن همه اقلام اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.items_table.setRowCount(0)
            self.calculate_totals()
    
    def reindex_rows(self):
        for row in range(self.items_table.rowCount()):
            remove_btn = self.items_table.cellWidget(row, 6)
            if remove_btn:
                try:
                    remove_btn.clicked.disconnect()
                except Exception:
                    pass
                remove_btn.clicked.connect(lambda checked, r=row: self.remove_row(r))
    
    # ============================================================
    # محاسبات
    # ============================================================
    
    def calculate_totals(self):
        total = 0
        
        for row in range(self.items_table.rowCount()):
            total_label = self.items_table.cellWidget(row, 4)
            if total_label:
                try:
                    total += int(float(total_label.text().replace(',', '')) or 0)
                except Exception:
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
    
    # ============================================================
    # بارگذاری داده ویرایش
    # ============================================================
    
    def load_document_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                c.execute('SELECT * FROM documents WHERE id = ?', [self.doc_id])
                row = c.fetchone()
                if not row:
                    return
                doc = row_to_dict(row)
                
                if doc.get('date'):
                    self.date.set_date(doc.get('date'))
                
                party_idx = self.party_combo.findData(doc.get('party_id'))
                if party_idx >= 0:
                    self.party_combo.setCurrentIndex(party_idx)
                
                if doc.get('discount'):
                    self.discount_input.setText(f"{int(doc.get('discount')):,}")
                
                c.execute("""
                    SELECT product_id, quantity, unit_price, total_price
                    FROM document_items
                    WHERE document_id = ?
                """, [self.doc_id])
                
                for item in c.fetchall():
                    if hasattr(item, 'keys'):
                        item_dict = {
                            'product_id': item['product_id'],
                            'quantity': item['quantity'],
                            'unit_price': item['unit_price'],
                            'total_price': item['total_price']
                        }
                    else:
                        item_dict = {
                            'product_id': item[0],
                            'quantity': item[1],
                            'unit_price': item[2],
                            'total_price': item[3]
                        }
                    self.add_product_row(item_dict)
                
                self.calculate_totals()
        
        except Exception as e:
            logger.error(f"خطا در بارگذاری سند: {e}", exc_info=True)
    
    # ============================================================
    # ذخیره
    # ============================================================
    
    def save_document(self):
        if self.party_combo.currentIndex() < 0:
            QMessageBox.warning(self, "خطا", "لطفاً طرف حساب را انتخاب کنید!")
            return
        
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "حداقل یک کالا اضافه کنید!")
            return
        
        # جمع‌آوری اقلام
        items = []
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 1)
            qty_spin = self.items_table.cellWidget(row, 2)
            price_edit = self.items_table.cellWidget(row, 3)
            
            if not combo or combo.currentIndex() <= 0:
                continue
            
            product_id = combo.currentData()
            qty = qty_spin.value() if qty_spin else 0
            price_text = price_edit.text().replace(',', '').strip() if price_edit else "0"
            unit_price = int(float(price_text)) if price_text else 0
            
            if qty > 0 and unit_price > 0:
                items.append({
                    'product_id': product_id,
                    'quantity': qty,
                    'unit_price': unit_price,
                    'total_price': qty * unit_price
                })
        
        if not items:
            QMessageBox.warning(self, "خطا", "هیچ آیتم معتبری وجود ندارد!")
            return
        
        # بررسی موجودی کافی برای فروش
        if self.doc_type == 'sales':
            with get_db() as conn:
                c = conn.cursor()
                for item in items:
                    c.execute("""
                        SELECT COALESCE(SUM(quantity), 0) FROM warehouse_stock
                        WHERE product_id = ?
                    """, [item['product_id']])
                    row = c.fetchone()
                    available = float(row[0]) if row else 0
                    
                    if self._editing:
                        c.execute("""
                            SELECT COALESCE(quantity, 0) 
                            FROM document_items 
                            WHERE document_id = ? AND product_id = ?
                        """, [self.doc_id, item['product_id']])
                        old_row = c.fetchone()
                        old_qty = float(old_row[0]) if old_row else 0
                        available += old_qty
                    
                    if item['quantity'] > available:
                        product = next(
                            (p for p in self.products if p['id'] == item['product_id']),
                            None
                        )
                        pname = product['name'] if product else f"کالا #{item['product_id']}"
                        QMessageBox.warning(
                            self, "موجودی ناکافی",
                            f"⚠️ موجودی کالای '{pname}' کافی نیست!\n\n"
                            f"موجودی فعلی: {available:,.2f}\n"
                            f"درخواستی: {item['quantity']:,.2f}"
                        )
                        return
        
        # ذخیره
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                party_id = self.party_combo.currentData()
                shamsi_date = self.date.get_shamsi()
                doc_type = 'sales' if self.doc_type == 'sales' else 'purchase'
                
                if self._editing:
                    # برگرداندن موجودی قبلی
                    c.execute("""
                        SELECT product_id, quantity 
                        FROM document_items 
                        WHERE document_id = ?
                    """, [self.doc_id])
                    old_items = c.fetchall()
                    
                    for old_item in old_items:
                        old_pid = old_item['product_id'] if hasattr(old_item, 'keys') else old_item[0]
                        old_qty = old_item['quantity'] if hasattr(old_item, 'keys') else old_item[1]
                        
                        update_inventory(c, old_pid, old_qty, doc_type, reverse=True)
                    
                    c.execute('DELETE FROM document_items WHERE document_id = ?', [self.doc_id])
                    
                    c.execute("""
                        UPDATE documents 
                        SET date = ?, party_id = ?, total_amount = ?, 
                            discount = ?, tax = ?, net_amount = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, [
                        shamsi_date, party_id, self._total_amount,
                        self._discount, self._tax, self._net_amount,
                        self.doc_id
                    ])
                    
                    doc_id = self.doc_id
                
                else:
                    # ✅ کوئری امن با پارامتر
                    prefix = "SAL" if doc_type == 'sales' else "PUR"
                    c.execute("""
                        SELECT MAX(CAST(SUBSTR(doc_no, 4) AS INTEGER)) 
                        FROM documents 
                        WHERE doc_no LIKE ?
                    """, [f"{prefix}%"])
                    max_no_row = c.fetchone()
                    max_no = max_no_row[0] if max_no_row else 0
                    doc_no = f"{prefix}{(max_no + 1) if max_no else 1:06d}"
                    
                    c.execute("""
                        INSERT INTO documents 
                        (doc_no, doc_type, date, party_id, total_amount, 
                         discount, tax, net_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        doc_no, doc_type, shamsi_date, party_id,
                        self._total_amount, self._discount,
                        self._tax, self._net_amount
                    ])
                    doc_id = c.lastrowid
                
                # ذخیره اقلام + به‌روزرسانی موجودی
                for item in items:
                    c.execute("""
                        INSERT INTO document_items 
                        (document_id, product_id, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    """, [
                        doc_id, item['product_id'], item['quantity'],
                        item['unit_price'], item['total_price']
                    ])
                    
                    update_inventory(c, item['product_id'], item['quantity'], doc_type)
                
                conn.commit()
            
            super().accept()
        
        except Exception as e:
            logger.error(f"خطا در ذخیره سند: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره سند: {str(e)}")
