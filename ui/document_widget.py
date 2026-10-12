# ui/document_widget.py
# ============================================================
# ویجت یکپارچه خرید و فروش — نسخه 4.0
# ============================================================
# تغییرات v4.0:
# ✅ برگشت از فروش
# ✅ برگشت از خرید
# ✅ Migration خودکار
# ✅ اتصال به سند اصلی
# ✅ محدودیت برگشت (چک تعداد برگشتی)
# ✅ اسناد مرتبط در تب جدید
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

# PDF
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# فارسی
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    PERSIAN_SUPPORT = True
except ImportError:
    PERSIAN_SUPPORT = False


# ═══════════════════════════════════════════════════════════
# Migration
# ═══════════════════════════════════════════════════════════

def run_migration_if_needed():
    if not hasattr(run_migration_if_needed, '_done'):
        try:
            from ui.migrations_add_return_types import run_migration
            run_migration()
        except ImportError:
            logger.warning("⚠️ migrations_add_return_types یافت نشد")
        except Exception as e:
            logger.warning(f"⚠️ خطا در Migration: {e}")
        run_migration_if_needed._done = True


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def row_to_dict(row):
    if row is None:
        return {}
    try:
        return {key: row[key] for key in row.keys()}
    except Exception:
        return {}


def reshape_persian_text(text):
    """تبدیل متن فارسی برای PDF"""
    if not text:
        return ""
    if not PERSIAN_SUPPORT:
        return str(text)
    try:
        import re
        text_str = str(text)
        parts = re.split(r'([0-9]+|[a-zA-Z]+)', text_str)
        result = []
        for part in parts:
            if part.isdigit() or (part.isalpha() and part.isascii()):
                result.append(part)
            else:
                try:
                    if part.strip():
                        result.append(arabic_reshaper.reshape(part))
                    else:
                        result.append(part)
                except Exception:
                    result.append(part)
        return get_display(''.join(result))
    except Exception:
        return str(text)


def get_doc_type_display(doc_type: str) -> str:
    types = {
        'sales': '📤 فروش',
        'purchase': '📥 خرید',
        'sales_return': '🔙 برگشت فروش',
        'purchase_return': '🔙 برگشت خرید',
    }
    return types.get(doc_type, doc_type)


def get_doc_type_prefix(doc_type: str) -> str:
    prefixes = {
        'sales': 'SAL',
        'purchase': 'PUR',
        'sales_return': 'RSL',
        'purchase_return': 'RPR',
    }
    return prefixes.get(doc_type, 'DOC')


def is_return_type(doc_type: str) -> bool:
    return doc_type in ('sales_return', 'purchase_return')


def get_original_type(return_type: str) -> str:
    map_ = {
        'sales_return': 'sales',
        'purchase_return': 'purchase',
    }
    return map_.get(return_type, '')


def is_sales_type(doc_type: str) -> bool:
    return doc_type in ('sales', 'sales_return')


# ═══════════════════════════════════════════════════════════
# ویجت اصلی
# ═══════════════════════════════════════════════════════════

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
        
        run_migration_if_needed()
        
        self.tax_rate = self._get_tax_rate()
        self.company_info = self._get_company_info()
        
        self.setup_ui()
        self.load_data()
        self.update_ui_by_permission()
        self.apply_theme()
    
    def _get_tax_rate(self) -> float:
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'tax_rate'")
                row = c.fetchone()
                return float(row[0]) / 100 if row else 0.09
        except Exception:
            return 0.09
    
    def _get_company_info(self) -> dict:
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT key, value FROM settings WHERE key LIKE 'company_%'")
                info = {row['key']: row['value'] for row in c.fetchall()}
                if not info.get('company_name'):
                    info['company_name'] = 'شرکت حسابداری پارسه'
                return info
        except Exception:
            return {'company_name': 'شرکت حسابداری پارسه'}
    
    def set_user_level(self, level: str):
        self.user_level = level
        self.update_ui_by_permission()
    
    def update_ui_by_permission(self):
        can_edit = self.user_level in ['admin', 'accountant', 'inventory']
        can_delete = self.user_level in ['admin', 'accountant']
        
        for btn_name in ['new_btn', 'edit_btn', 'return_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setVisible(can_edit)
        
        if hasattr(self, 'delete_btn'):
            self.delete_btn.setVisible(can_delete)
    
    # ═══════════════════════════════════════════════════════
    # UI
    # ═══════════════════════════════════════════════════════
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(
            self.margin(10), self.margin(10),
            self.margin(10), self.margin(10)
        )
        
        # ═══ پنل راست ═══
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
        self.doc_type_combo.addItems([
            "📤 فاکتور فروش",
            "📥 فاکتور خرید",
            "🔙 برگشت از فروش",
            "🔙 برگشت از خرید",
        ])
        self.doc_type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.doc_type_combo.setMinimumHeight(self.scaled(32))
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
        
        self.stats_label = QLabel("📊 مجموع: ۰ سند | ۰ ریال")
        self.stats_label.setStyleSheet("""
            font-weight: bold;
            padding: 8px 12px;
            background: #f0f0f0;
            border-radius: 5px;
            color: #2c3e50;
        """)
        right_layout.addWidget(self.stats_label)
        
        # ═══ پنل چپ ═══
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
        
        self.related_text = QTextEdit()
        self.related_text.setReadOnly(True)
        self.related_text.setPlaceholderText("سند مرتبطی وجود ندارد")
        self.detail_tabs.addTab(self.related_text, "🔗 اسناد مرتبط")
        
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
        
        self.return_btn = self.create_button("🔙 برگشت", "infoBtn")
        self.return_btn.setToolTip("ثبت برگشت از سند انتخاب‌شده")
        self.return_btn.clicked.connect(self.create_return)
        toolbar.addWidget(self.return_btn)
        
        self.delete_btn = self.create_button("🗑️ حذف", "dangerBtn")
        self.delete_btn.clicked.connect(self.delete_document)
        toolbar.addWidget(self.delete_btn)
        
        toolbar.addStretch()
        
        refresh_btn = self.create_button("🔄 بروزرسانی", "infoBtn")
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)
        
        return toolbar
    
    # ═══════════════════════════════════════════════════════
    # Load Data
    # ═══════════════════════════════════════════════════════
    
    def load_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                # اسناد
                c.execute("""
                    SELECT d.*, p.name as party_name 
                    FROM documents d 
                    JOIN parties p ON d.party_id = p.id 
                    WHERE d.doc_type = ? 
                    ORDER BY d.id DESC
                """, [self.current_doc_type])
                self.documents_data = [row_to_dict(row) for row in c.fetchall()]
                
                # کالاها
                price_col = 'sale_price' if is_sales_type(self.current_doc_type) else 'purchase_price'
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
                party_type = "customer" if is_sales_type(self.current_doc_type) else "supplier"
                c.execute(
                    'SELECT id, code, name FROM parties WHERE type = ? ORDER BY name',
                    [party_type]
                )
                self.parties = [row_to_dict(row) for row in c.fetchall()]
            
            self.display_documents()
            self.update_stats()
        
        except Exception as e:
            logger.error(f"خطا در بارگذاری: {e}", exc_info=True)
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
        type_text = get_doc_type_display(self.current_doc_type)
        self.stats_label.setText(
            f"📊 {type_text} | {total_count} سند | {total_amount:,.0f} ریال"
        )
    
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
                doc_no = str(doc.get('doc_no', '')).lower()
                party_name = str(doc.get('party_name', '')).lower()
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
    
    # ═══════════════════════════════════════════════════════
    # Selection
    # ═══════════════════════════════════════════════════════
    
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
            
            # HTML
            html = self._generate_detail_html(doc, self.current_items)
            self.details_text.setHtml(html)
            self.display_items_table(self.current_items)
            
            # اسناد مرتبط
            self._show_related_documents(doc.get('id'))
            
            status_text = "✅ تأیید شده" if doc.get('is_approved', 0) else "⏳ در انتظار تأیید"
            self.detail_status.setText(f"📌 وضعیت: {status_text}")
        
        except Exception as e:
            logger.error(f"خطا در نمایش جزئیات: {e}", exc_info=True)
            self.details_text.setText(f"⚠️ خطا: {str(e)}")
    
    def _generate_detail_html(self, doc, items):
        doc_type_text = get_doc_type_display(doc.get('doc_type', ''))
        party_type_text = "مشتری" if is_sales_type(doc.get('doc_type', '')) else "تأمین‌کننده"
        
        html = f"""
        <div style='font-family: Tahoma; direction: rtl; font-size: 10pt;'>
            <h3 style='text-align: center; color: #273c75;'>{doc_type_text}</h3>
            
            <table width='100%' style='margin: 10px 0;'>
                <tr><td><b>شماره:</b></td><td>{doc.get('doc_no', '')}</td></tr>
                <tr><td><b>تاریخ:</b></td><td>{safe_display_date(doc.get('date', ''))}</td></tr>
                <tr><td><b>{party_type_text}:</b></td><td>{doc.get('party_name', '')}</td></tr>
            </table>
            
            <hr>
            
            <h4>📦 اقلام:</h4>
            <table width='100%' border='1' style='border-collapse: collapse;'>
                <tr style='background: #273c75; color: white;'>
                    <th>کد</th><th>کالا</th><th>تعداد</th><th>فی</th><th>جمع</th>
                </tr>
        """
        
        for item in items:
            returned = item.get('returned_qty', 0) or 0
            qty = item.get('quantity', 0)
            return_info = f" (برگشتی: {returned})" if returned > 0 else ""
            
            html += f"""
                <tr>
                    <td>{item.get('product_code', '')}</td>
                    <td>{item.get('product_name', '')}</td>
                    <td style='text-align: center;'>{qty:,.2f}{return_info}</td>
                    <td style='text-align: left;'>{item.get('unit_price', 0):,.0f}</td>
                    <td style='text-align: left;'>{item.get('total_price', 0):,.0f}</td>
                </tr>
            """
        
        tax_percent = int(self.tax_rate * 100)
        html += f"""
            </table>
            <hr>
            <table width='100%'>
                <tr><td><b>جمع کل:</b></td><td style='text-align: left;'>{doc.get('total_amount', 0):,.0f}</td></tr>
                <tr><td><b>تخفیف:</b></td><td style='text-align: left;'>{doc.get('discount', 0):,.0f}</td></tr>
                <tr><td><b>مالیات ({tax_percent}%):</b></td><td style='text-align: left;'>{doc.get('tax', 0):,.0f}</td></tr>
                <tr style='font-weight: bold; font-size: 12pt;'>
                    <td style='color: #27ae60;'>💵 مبلغ نهایی:</td>
                    <td style='text-align: left; color: #27ae60;'>{doc.get('net_amount', 0):,.0f}</td>
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
            
            returned = item.get('returned_qty', 0) or 0
            qty_text = f"{item.get('quantity', 0):,.2f}"
            if returned > 0:
                qty_text += f" (برگشتی: {returned:,.2f})"
            
            qty_item = QTableWidgetItem(qty_text)
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_detail_table.setItem(i, 2, qty_item)
            
            price_item = QTableWidgetItem(f"{item.get('unit_price', 0):,.0f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_detail_table.setItem(i, 3, price_item)
            
            total_item = QTableWidgetItem(f"{item.get('total_price', 0):,.0f}")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            total_item.setForeground(QColor('#27ae60'))
            self.items_detail_table.setItem(i, 4, total_item)
    
    def _show_related_documents(self, doc_id):
        """نمایش اسناد مرتبط (برگشتی)"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                # اسناد برگشتی از این سند
                c.execute("""
                    SELECT d.doc_no, d.date, d.net_amount, dr.reason
                    FROM document_returns dr
                    JOIN documents d ON dr.return_doc_id = d.id
                    WHERE dr.original_doc_id = ?
                """, [doc_id])
                returns_from = c.fetchall()
                
                # سند اصلی این برگشت
                c.execute("""
                    SELECT d.doc_no, d.date, d.net_amount, dr.reason
                    FROM document_returns dr
                    JOIN documents d ON dr.original_doc_id = d.id
                    WHERE dr.return_doc_id = ?
                """, [doc_id])
                returns_to = c.fetchall()
            
            html = "<div style='font-family: Tahoma; direction: rtl; padding: 10px;'>"
            
            if returns_from:
                html += "<h4>🔙 برگشت‌های این سند:</h4><ul>"
                for r in returns_from:
                    r_dict = row_to_dict(r)
                    html += f"<li>سند {r_dict.get('doc_no', '')} - تاریخ {safe_display_date(r_dict.get('date', ''))} - مبلغ {r_dict.get('net_amount', 0):,.0f}</li>"
                html += "</ul>"
            
            if returns_to:
                html += "<h4>📄 سند اصلی:</h4><ul>"
                for r in returns_to:
                    r_dict = row_to_dict(r)
                    html += f"<li>سند {r_dict.get('doc_no', '')} - تاریخ {safe_display_date(r_dict.get('date', ''))} - مبلغ {r_dict.get('net_amount', 0):,.0f}</li>"
                html += "</ul>"
            
            if not returns_from and not returns_to:
                html += "<p style='color: #888; text-align: center; padding: 20px;'>سند مرتبطی وجود ندارد</p>"
            
            html += "</div>"
            self.related_text.setHtml(html)
        
        except Exception as e:
            logger.warning(f"خطا در نمایش اسناد مرتبط: {e}")
    
    # ═══════════════════════════════════════════════════════
    # Actions
    # ═══════════════════════════════════════════════════════
    
    def on_type_changed(self):
        idx = self.doc_type_combo.currentIndex()
        types = ['sales', 'purchase', 'sales_return', 'purchase_return']
        self.current_doc_type = types[idx]
        self.load_data()
        self.clear_details()
    
    def clear_details(self):
        self.details_text.clear()
        self.items_detail_table.setRowCount(0)
        self.related_text.clear()
        self.detail_status.setText("")
        self.current_document = None
        self.current_items = []
    
    def new_document(self):
        if not self.check_document_limit():
            return
        
        if not self.products:
            QMessageBox.warning(self, "خطا",
                "⚠️ هیچ کالایی در سیستم تعریف نشده است!")
            return
        
        if not self.parties:
            QMessageBox.warning(self, "خطا",
                "⚠️ هیچ طرف حسابی تعریف نشده است!")
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
            QMessageBox.information(self, "موفق", "✅ سند ثبت شد!")
    
    def edit_document(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        if self.user_level not in ['admin', 'accountant']:
            QMessageBox.warning(self, "دسترسی محدود",
                "⚠️ فقط مدیر و حسابدار می‌توانند ویرایش کنند!")
            return
        
        doc_no = self.table.item(row, 0).text()
        doc = None
        for d in self.documents_data:
            if d.get('doc_no') == doc_no:
                doc = d
                break
        
        if not doc:
            return
        
        if is_return_type(doc.get('doc_type', '')):
            QMessageBox.warning(self, "خطا",
                "⚠️ اسناد برگشتی قابل ویرایش نیستند!\n"
                "برای اصلاح، سند برگشتی را حذف و مجدد ثبت کنید.")
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
            QMessageBox.information(self, "موفق", "✅ سند ویرایش شد!")
    
    # ═══════════════════════════════════════════════════════
    # 🔙 برگشت — قابلیت جدید
    # ═══════════════════════════════════════════════════════
    
    def create_return(self):
        """ثبت برگشت از سند انتخاب‌شده"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        if self.user_level not in ['admin', 'accountant']:
            QMessageBox.warning(self, "دسترسی محدود",
                "⚠️ فقط مدیر و حسابدار می‌توانند برگشت ثبت کنند!")
            return
        
        doc = self.documents_data[row]
        
        # چک نوع سند
        if is_return_type(doc.get('doc_type', '')):
            QMessageBox.warning(self, "خطا",
                "⚠️ اسناد برگشتی، برگشت‌پذیر نیستند!")
            return
        
        # باز کردن دیالوگ برگشت
        dialog = ReturnDialog(
            document=doc,
            parent=self
        )
        
        if dialog.exec_():
            self.load_data()
            self.document_changed.emit()
            QMessageBox.information(self, "موفق", 
                "✅ سند برگشتی ثبت شد و موجودی/حساب‌ها اصلاح شدند!")
    
    def delete_document(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        if self.user_level not in ['admin', 'accountant']:
            QMessageBox.warning(self, "دسترسی محدود",
                "⚠️ فقط مدیر و حسابدار!")
            return
        
        doc_no = self.table.item(row, 0).text()
        doc_type = self.current_doc_type
        
        # چک اسناد برگشتی
        doc_id = self.documents_data[row].get('id')
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT COUNT(*) FROM document_returns
                WHERE original_doc_id = ? OR return_doc_id = ?
            """, [doc_id, doc_id])
            return_count = c.fetchone()[0] or 0
        
        if return_count > 0:
            QMessageBox.warning(self, "خطا",
                f"⚠️ این سند {return_count} سند برگشتی مرتبط دارد!\n"
                f"ابتدا اسناد برگشتی را حذف کنید.")
            return
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف سند {doc_no} اطمینان دارید؟\n"
            f"این عمل قابل بازگشت نیست!",
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
                    return
                
                doc_id = row_data['id'] if hasattr(row_data, 'keys') else row_data[0]
                
                # برگرداندن موجودی
                c.execute("SELECT product_id, quantity FROM document_items WHERE document_id = ?", [doc_id])
                
                for item in c.fetchall():
                    product_id = item['product_id'] if hasattr(item, 'keys') else item[0]
                    quantity = item['quantity'] if hasattr(item, 'keys') else item[1]
                    
                    if is_sales_type(doc_type):
                        # فروش حذف میشه → موجودی زیاد میشه
                        c.execute(
                            "UPDATE products SET stock = stock + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            [quantity, product_id]
                        )
                        c.execute("""
                            UPDATE warehouse_stock 
                            SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP
                            WHERE product_id = ?
                        """, [quantity, product_id])
                    else:
                        # خرید حذف میشه → موجودی کم میشه
                        c.execute(
                            "UPDATE products SET stock = stock - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            [quantity, product_id]
                        )
                        c.execute("""
                            UPDATE warehouse_stock 
                            SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP
                            WHERE product_id = ?
                        """, [quantity, product_id])
                
                c.execute('DELETE FROM document_items WHERE document_id = ?', [doc_id])
                c.execute('DELETE FROM documents WHERE id = ?', [doc_id])
                conn.commit()
            
            self.load_data()
            self.clear_details()
            self.document_changed.emit()
            QMessageBox.information(self, "موفق", "✅ سند حذف شد!")
        
        except Exception as e:
            logger.error(f"خطا در حذف: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def check_document_limit(self) -> bool:
        if self.customer_name:
            module_name = 'invoice' if is_sales_type(self.current_doc_type) else 'purchase'
            allowed, current, limit, msg = ModuleLimitHelper.check_module_limit(
                self.customer_name, module_name
            )
            if not allowed:
                QMessageBox.warning(self, "خطا",
                    f"❌ به سقف مجاز {limit} فاکتور رسیده‌اید!")
                return False
        return True
    
    # ═══════════════════════════════════════════════════════
    # Print / PDF / Excel
    # ═══════════════════════════════════════════════════════
    
    def print_document(self):
        if not self.current_document:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
            
            preview_dialog = QPrintPreviewDialog(printer, self)
            preview_dialog.paintRequested.connect(self._print_preview)
            preview_dialog.exec_()
        except Exception as e:
            logger.error(f"خطا در چاپ: {e}")
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
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
        doc_type_text = get_doc_type_display(doc.get('doc_type', ''))
        party_type = "مشتری" if is_sales_type(doc.get('doc_type', '')) else "تأمین‌کننده"
        
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
            .company-name {{ font-size: 16pt; font-weight: bold; color: #273c75; }}
            .company-info {{ font-size: 9pt; color: #555; margin-top: 5px; }}
            .title {{ font-size: 14pt; font-weight: bold; color: #2c3e50; margin-top: 10px; }}
            .info {{ margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
            .info table {{ width: 100%; }}
            .info td {{ padding: 3px 5px; }}
            table.items {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            table.items th {{ background-color: #273c75; color: white; padding: 8px; text-align: center; }}
            table.items td {{ border: 1px solid #ddd; padding: 6px; text-align: center; }}
            .totals {{ margin-top: 15px; padding: 10px; background: #f0f0f0; border-radius: 5px; }}
            .net {{ font-size: 13pt; font-weight: bold; color: #27ae60; }}
            .footer {{
                margin-top: 30px; text-align: center;
                font-size: 8pt; color: #999;
                border-top: 1px solid #ddd; padding-top: 10px;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">{self.company_info.get('company_name', 'شرکت')}</div>
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
                        <td><b>تاریخ:</b> {safe_display_date(doc.get('date', ''))}</td>
                        <td><b>{party_type}:</b> {doc.get('party_name', '')}</td>
                    </tr>
                </table>
            </div>
            
            <table class="items">
                <thead>
                    <tr><th>ردیف</th><th>کالا</th><th>تعداد</th><th>فی</th><th>جمع</th></tr>
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
                    <tr><td><b>مبلغ نهایی:</b></td><td align="left" class="net">{doc.get('net_amount', 0):,.0f} ریال</td></tr>
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
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        default_name = f"{self.current_document.get('doc_no', 'snd')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره PDF", default_name, "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            from PyQt5.QtPrintSupport import QPrinter
            from PyQt5.QtGui import QTextDocument
            from PyQt5.QtCore import QSizeF
            
            printer = QPrinter(QPrinter.ScreenResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
            
            doc = QTextDocument()
            doc.setHtml(self._generate_print_html())
            
            rect = printer.pageRect(QPrinter.DevicePixel)
            doc.setPageSize(QSizeF(rect.width(), rect.height()))
            doc.print_(printer)
            
            QMessageBox.information(self, "موفق", f"✅ PDF ذخیره شد:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def export_to_excel(self):
        if not self.current_document:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره Excel",
            f"{self.current_document.get('doc_no', 'snd')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not file_name:
            return
        
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ردیف", "کد", "کالا", "تعداد", "فی", "جمع"])
                
                for i, item in enumerate(self.current_items, 1):
                    writer.writerow([
                        i,
                        item.get('product_code', ''),
                        item.get('product_name', ''),
                        item.get('quantity', 0),
                        item.get('unit_price', 0),
                        item.get('total_price', 0)
                    ])
            
            QMessageBox.information(self, "موفق", f"✅ ذخیره شد:\n{file_name}")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")


# ═══════════════════════════════════════════════════════════
# ReturnDialog — دیالوگ برگشت
# ═══════════════════════════════════════════════════════════

class ReturnDialog(BaseDialog):
    """دیالوگ برگشت از فروش/خرید"""
    
    def __init__(self, document: dict, parent=None):
        super().__init__(parent, base_width=800, base_height=650)
        
        self.document = document
        self.original_items = []
        self.return_items = []
        
        doc_type = document.get('doc_type', 'sales')
        type_text = "فروش" if doc_type == 'sales' else "خرید"
        
        self.setWindowTitle(f"🔙 برگشت از {type_text} — سند {document.get('doc_no', '')}")
        self.setModal(True)
        
        self._load_original_items()
        self.setup_ui()
        self.apply_theme()
    
    def _load_original_items(self):
        """بارگذاری اقلام سند اصلی"""
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT di.*, p.code as product_code, p.name as product_name
                    FROM document_items di
                    JOIN products p ON di.product_id = p.id
                    WHERE di.document_id = ?
                """, [self.document.get('id')])
                
                self.original_items = []
                for row in c.fetchall():
                    item = row_to_dict(row)
                    # مقدار برگشت‌پذیر
                    item['available'] = (item.get('quantity', 0) or 0) - (item.get('returned_qty', 0) or 0)
                    self.original_items.append(item)
        
        except Exception as e:
            logger.error(f"خطا در بارگذاری اقلام: {e}")
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # هدر
        header = QLabel(
            f"<h3 style='color: #e74c3c; text-align: center;'>🔙 برگشت از سند</h3>"
            f"<p style='text-align: center; color: #666;'>"
            f"سند اصلی: <b>{self.document.get('doc_no', '')}</b> — "
            f"{self.document.get('party_name', '')} — "
            f"{safe_display_date(self.document.get('date', ''))}"
            f"</p>"
        )
        header.setTextFormat(Qt.RichText)
        layout.addWidget(header)
        
        # تاریخ برگشت
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("📅 تاریخ برگشت:"))
        self.return_date = ShamsiDateEdit()
        self.return_date.set_date(get_today_jalali())
        self.return_date.setMinimumHeight(self.scaled(32))
        date_layout.addWidget(self.return_date)
        date_layout.addStretch()
        layout.addLayout(date_layout)
        
        # جدول اقلام
        layout.addWidget(QLabel("📦 اقلام قابل برگشت:"))
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels([
            "کالا", "تعداد اصلی", "برگشتی قبلی", "قابل برگشت", "تعداد برگشت", "مبلغ"
        ])
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setColumnWidth(0, self.scaled(200))
        self.items_table.setColumnWidth(1, self.scaled(90))
        self.items_table.setColumnWidth(2, self.scaled(90))
        self.items_table.setColumnWidth(3, self.scaled(90))
        self.items_table.setColumnWidth(4, self.scaled(120))
        
        layout.addWidget(self.items_table, 1)
        
        # دلیل برگشت
        reason_layout = QHBoxLayout()
        reason_layout.addWidget(QLabel("📝 دلیل برگشت:"))
        self.reason_input = QTextEdit()
        self.reason_input.setPlaceholderText("مثال: کالای معیوب، اشتباه در سفارش...")
        self.reason_input.setMaximumHeight(self.scaled(70))
        reason_layout.addWidget(self.reason_input)
        layout.addLayout(reason_layout)
        
        # خلاصه
        self.summary_label = QLabel("💰 جمع برگشت: ۰ ریال")
        self.summary_label.setStyleSheet("""
            background: #fff3cd;
            color: #856404;
            padding: 10px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 12pt;
        """)
        self.summary_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.summary_label)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("✅ ثبت برگشت")
        save_btn.setObjectName("successBtn")
        save_btn.setMinimumHeight(self.scaled(42))
        save_btn.setMinimumWidth(self.scaled(160))
        save_btn.setStyleSheet("""
            QPushButton {
                background: #27ae60; color: white;
                border: none; border-radius: 8px;
                font-weight: bold; font-size: 12pt;
            }
        """)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.setMinimumHeight(self.scaled(42))
        cancel_btn.setMinimumWidth(self.scaled(120))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c; color: white;
                border: none; border-radius: 8px;
                font-weight: bold; font-size: 12pt;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # پر کردن جدول
        self._populate_items()
    
    def _populate_items(self):
        """پر کردن جدول اقلام"""
        self.items_table.setRowCount(len(self.original_items))
        self.return_spins = []
        
        font = QFont("Tahoma", self.font_size(10))
        
        for i, item in enumerate(self.original_items):
            # کالا
            name_item = QTableWidgetItem(
                f"{item.get('product_code', '')} - {item.get('product_name', '')}"
            )
            name_item.setFont(font)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(i, 0, name_item)
            
            # تعداد اصلی
            qty_item = QTableWidgetItem(f"{item.get('quantity', 0):,.2f}")
            qty_item.setFont(font)
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            qty_item.setFlags(qty_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(i, 1, qty_item)
            
            # برگشتی قبلی
            returned_item = QTableWidgetItem(f"{item.get('returned_qty', 0) or 0:,.2f}")
            returned_item.setFont(font)
            returned_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            returned_item.setFlags(returned_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(i, 2, returned_item)
            
            # قابل برگشت
            available_item = QTableWidgetItem(f"{item['available']:,.2f}")
            available_item.setFont(font)
            available_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            available_item.setForeground(QColor('#27ae60'))
            available_item.setFlags(available_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(i, 3, available_item)
            
            # تعداد برگشت (قابل ویرایش)
            spin = QDoubleSpinBox()
            spin.setRange(0, item['available'])
            spin.setValue(item['available'])
            spin.setDecimals(2)
            spin.setSingleStep(1)
            spin.setFont(font)
            spin.setStyleSheet("""
                QDoubleSpinBox {
                    background: white;
                    border: 2px solid #1976D2;
                    border-radius: 4px;
                    padding: 4px;
                    min-height: 26px;
                }
            """)
            spin.valueChanged.connect(lambda v, r=i: self._update_row(r, v))
            self.items_table.setCellWidget(i, 4, spin)
            self.return_spins.append(spin)
            
            # مبلغ
            amount = (item.get('unit_price', 0) or 0) * item['available']
            amount_item = QTableWidgetItem(f"{amount:,.0f}")
            amount_item.setFont(font)
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amount_item.setFlags(amount_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(i, 5, amount_item)
        
        self._update_summary()
    
    def _update_row(self, row: int, value: float):
        """بروزرسانی یک ردیف"""
        item = self.original_items[row]
        amount = (item.get('unit_price', 0) or 0) * value
        self.items_table.item(row, 5).setText(f"{amount:,.0f}")
        self._update_summary()
    
    def _update_summary(self):
        """بروزرسانی خلاصه"""
        total = 0
        for i, item in enumerate(self.original_items):
            qty = self.return_spins[i].value()
            price = item.get('unit_price', 0) or 0
            total += qty * price
        
        self.summary_label.setText(f"💰 جمع برگشت: {total:,.0f} ریال")
    
    def accept(self):
        """ثبت برگشت"""
        # جمع‌آوری اقلام برگشتی
        items_to_return = []
        total_amount = 0
        
        for i, item in enumerate(self.original_items):
            qty = self.return_spins[i].value()
            if qty <= 0:
                continue
            
            price = item.get('unit_price', 0) or 0
            total = qty * price
            
            items_to_return.append({
                'product_id': item.get('product_id'),
                'quantity': qty,
                'unit_price': price,
                'total_price': total,
                'original_item_id': item.get('id'),
            })
            
            total_amount += total
        
        if not items_to_return:
            QMessageBox.warning(self, "خطا", "حداقل یک قلم را برای برگشت انتخاب کنید!")
            return
        
        reason = self.reason_input.toPlainText().strip()
        return_date = self.return_date.get_shamsi()
        
        try:
            # محاسبه مالیات و تخفیف نسبی
            original_total = self.document.get('total_amount', 0) or 0
            if original_total > 0:
                ratio = total_amount / original_total
                original_discount = self.document.get('discount', 0) or 0
                original_tax = self.document.get('tax', 0) or 0
                
                discount = int(original_discount * ratio)
                tax = int(original_tax * ratio)
            else:
                discount = 0
                tax = 0
            
            net_amount = total_amount - discount + tax
            
            # تعیین نوع سند برگشتی
            doc_type = self.document.get('doc_type', 'sales')
            return_type = 'sales_return' if doc_type == 'sales' else 'purchase_return'
            prefix = get_doc_type_prefix(return_type)
            
            with get_db() as conn:
                c = conn.cursor()
                
                # شماره سند
                c.execute(f"""
                    SELECT MAX(CAST(SUBSTR(doc_no, 4) AS INTEGER))
                    FROM documents WHERE doc_no LIKE '{prefix}%'
                """)
                max_no = c.fetchone()[0] or 0
                doc_no = f"{prefix}{(max_no + 1):06d}"
                
                # درج سند
                c.execute("""
                    INSERT INTO documents
                    (doc_no, doc_type, date, party_id, total_amount, discount, tax, net_amount, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    doc_no,
                    return_type,
                    return_date,
                    self.document.get('party_id'),
                    total_amount,
                    discount,
                    tax,
                    net_amount,
                    f"برگشت از {self.document.get('doc_no', '')}: {reason}"
                ])
                
                return_doc_id = c.lastrowid
                
                # درج اقلام برگشتی
                for item in items_to_return:
                    c.execute("""
                        INSERT INTO document_items
                        (document_id, product_id, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    """, [
                        return_doc_id,
                        item['product_id'],
                        item['quantity'],
                        item['unit_price'],
                        item['total_price']
                    ])
                    
                    # بروزرسانی returned_qty در سند اصلی
                    c.execute("""
                        UPDATE document_items
                        SET returned_qty = COALESCE(returned_qty, 0) + ?,
                            return_doc_id = ?
                        WHERE id = ?
                    """, [item['quantity'], return_doc_id, item['original_item_id']])
                    
                    # بروزرسانی انبار
                    if doc_type == 'sales':
                        # برگشت از فروش → موجودی زیاد میشه
                        c.execute(
                            "UPDATE products SET stock = stock + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            [item['quantity'], item['product_id']]
                        )
                        c.execute("""
                            UPDATE warehouse_stock 
                            SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP
                            WHERE product_id = ?
                        """, [item['quantity'], item['product_id']])
                    else:
                        # برگشت از خرید → موجودی کم میشه
                        c.execute(
                            "UPDATE products SET stock = stock - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            [item['quantity'], item['product_id']]
                        )
                        c.execute("""
                            UPDATE warehouse_stock 
                            SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP
                            WHERE product_id = ?
                        """, [item['quantity'], item['product_id']])
                
                # ثبت در جدول ربط
                c.execute("""
                    INSERT INTO document_returns
                    (original_doc_id, return_doc_id, reason)
                    VALUES (?, ?, ?)
                """, [self.document.get('id'), return_doc_id, reason])
                
                conn.commit()
            
            QMessageBox.information(
                self, "موفق",
                f"✅ برگشت ثبت شد!\n"
                f"شماره سند برگشتی: {doc_no}\n"
                f"مبلغ: {net_amount:,.0f} ریال"
            )
            
            super().accept()
        
        except Exception as e:
            logger.error(f"خطا در برگشت: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def apply_theme(self):
        """تم ساده"""
        self.setStyleSheet("""
            QDialog { background: #f5f6fa; }
            QLabel { color: #1a1a2e; }
            QTableWidget {
                background: white;
                color: #1a1a2e;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                gridline-color: #dcdde1;
            }
            QHeaderView::section {
                background: #e8e8e8;
                color: #1a1a2e;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QLineEdit, QTextEdit, QComboBox {
                background: white;
                color: #1a1a2e;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 28px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 2px solid #1976D2;
            }
        """)


# ═══════════════════════════════════════════════════════════
# DocumentDialog — دیالوگ سند جدید/ویرایش
# ═══════════════════════════════════════════════════════════

class DocumentDialog(BaseDialog):
    """دیالوگ سند جدید/ویرایش"""
    
    def __init__(self, products, parties, doc_type, parent=None,
                 customer_name="", tax_rate=0.09, doc_id=None):
        super().__init__(parent, base_width=900, base_height=750)
        
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
        
        type_text = get_doc_type_display(doc_type)
        self.setWindowTitle(f"{'✏️ ویرایش' if self._editing else '➕'} {type_text}")
        self.setModal(True)
        
        self.setup_ui()
        
        if self._editing:
            self.load_document_data()
        
        self.apply_theme()
    
    def scaled(self, value):
        return self.screen_manager.get_scaled(value)
    
    def spacing(self, value=10):
        return self.screen_manager.get_spacing(value)
    
    def margin(self, value=10):
        return self.screen_manager.get_margin(value)
    
    def font_size(self, size):
        return self.screen_manager.get_font_size(size)
    
    def create_button(self, text, object_name=""):
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        btn.setMinimumHeight(self.scaled(32))
        return btn
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # اطلاعات سند
        info_group = QGroupBox("📋 اطلاعات سند")
        info_layout = QHBoxLayout(info_group)
        info_layout.setSpacing(10)
        
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
        info_layout.addWidget(QLabel("👤 طرف حساب:"))
        info_layout.addWidget(self.party_combo)
        
        info_layout.addStretch()
        layout.addWidget(info_group)
        
        # اقلام
        items_group = QGroupBox("📦 اقلام سند")
        items_layout = QVBoxLayout(items_group)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels([
            "کد", "کالا", "تعداد", "قیمت واحد", "جمع", "موجودی", "عملیات"
        ])
        self.items_table.setAlternatingRowColors(True)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setMinimumHeight(self.scaled(250))
        items_layout.addWidget(self.items_table)
        
        btn_row = QHBoxLayout()
        
        add_btn = self.create_button("➕ افزودن کالا", "successBtn")
        add_btn.clicked.connect(self.add_product_row)
        btn_row.addWidget(add_btn)
        
        remove_btn = self.create_button("🗑️ حذف", "dangerBtn")
        remove_btn.clicked.connect(self.remove_selected_row)
        btn_row.addWidget(remove_btn)
        
        clear_btn = self.create_button("🧹 پاک کردن", "warningBtn")
        clear_btn.clicked.connect(self.clear_all_rows)
        btn_row.addWidget(clear_btn)
        
        btn_row.addStretch()
        items_layout.addLayout(btn_row)
        
        layout.addWidget(items_group)
        
        # جمع‌ها
        totals_group = QGroupBox("💰 جمع‌ها")
        totals_layout = QGridLayout(totals_group)
        
        totals_layout.addWidget(QLabel("جمع کل:"), 0, 0, Qt.AlignRight)
        self.total_label = QLabel("۰")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self.total_label.setAlignment(Qt.AlignRight)
        totals_layout.addWidget(self.total_label, 0, 1)
        
        totals_layout.addWidget(QLabel("تخفیف:"), 1, 0, Qt.AlignRight)
        self.discount_input = QLineEdit("0")
        self.discount_input.setAlignment(Qt.AlignRight)
        self.discount_input.setMaximumWidth(self.scaled(150))
        self.discount_input.textChanged.connect(self.calculate_totals)
        totals_layout.addWidget(self.discount_input, 1, 1)
        
        tax_pct = int(self.tax_rate * 100)
        totals_layout.addWidget(QLabel(f"مالیات ({tax_pct}%):"), 2, 0, Qt.AlignRight)
        self.tax_label = QLabel("۰")
        self.tax_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        self.tax_label.setAlignment(Qt.AlignRight)
        totals_layout.addWidget(self.tax_label, 2, 1)
        
        totals_layout.addWidget(QLabel("مبلغ نهایی:"), 3, 0, Qt.AlignRight)
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
        save_btn.setMinimumHeight(self.scaled(42))
        save_btn.setMinimumWidth(self.scaled(130))
        save_btn.clicked.connect(self.save_document)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = self.create_button("❌ انصراف", "dangerBtn")
        cancel_btn.setMinimumHeight(self.scaled(42))
        cancel_btn.setMinimumWidth(self.scaled(120))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def add_product_row(self, product_data=None):
        if not self.products:
            QMessageBox.warning(self, "خطا", "هیچ کالایی وجود ندارد!")
            return
        
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        self.items_table.setRowHeight(row, self.scaled(38))
        
        # کد
        code_label = QLabel("-")
        code_label.setAlignment(Qt.AlignCenter)
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
        qty = QDoubleSpinBox()
        qty.setRange(0.01, 999999)
        qty.setValue(1)
        qty.setDecimals(2)
        qty.valueChanged.connect(lambda v, r=row: self.calculate_row_total(r))
        self.items_table.setCellWidget(row, 2, qty)
        
        # قیمت
        price = QLineEdit()
        price.setAlignment(Qt.AlignRight)
        price.setPlaceholderText("فی")
        price.textChanged.connect(lambda t, r=row: self.calculate_row_total(r))
        self.items_table.setCellWidget(row, 3, price)
        
        # جمع
        total = QLabel("۰")
        total.setAlignment(Qt.AlignRight)
        total.setStyleSheet("font-weight: bold; color: #27ae60;")
        self.items_table.setCellWidget(row, 4, total)
        
        # موجودی
        stock_label = QLabel("")
        stock_label.setAlignment(Qt.AlignCenter)
        self.items_table.setCellWidget(row, 5, stock_label)
        
        # حذف
        del_btn = QPushButton("🗑️")
        del_btn.setMaximumWidth(self.scaled(40))
        del_btn.setStyleSheet("background: #e74c3c; color: white; border-radius: 4px;")
        del_btn.clicked.connect(lambda: self.remove_row(row))
        self.items_table.setCellWidget(row, 6, del_btn)
        
        if product_data:
            idx = combo.findData(product_data.get('product_id'))
            if idx >= 0:
                combo.setCurrentIndex(idx)
            qty.setValue(product_data.get('quantity', 1))
            price.setText(f"{int(product_data.get('unit_price', 0)):,}")
    
    def on_product_changed(self, row):
        combo = self.items_table.cellWidget(row, 1)
        if not combo or combo.currentIndex() <= 0:
            return
        
        product_id = combo.currentData()
        product = next((p for p in self.products if p.get('id') == product_id), None)
        if not product:
            return
        
        code_label = self.items_table.cellWidget(row, 0)
        if code_label:
            code_label.setText(product.get('code', ''))
        
        stock_label = self.items_table.cellWidget(row, 5)
        if stock_label:
            stock = product.get('real_stock', product.get('stock', 0)) or 0
            if is_sales_type(self.doc_type):
                if stock <= 0:
                    stock_label.setText("⚠️ ناموجود")
                    stock_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    stock_label.setText(f"✅ {stock:,.2f}")
                    stock_label.setStyleSheet("color: #27ae60;")
            else:
                stock_label.setText(f"📦 {stock:,.2f}")
        
        price_edit = self.items_table.cellWidget(row, 3)
        if price_edit and not price_edit.text():
            price = product.get('price', 0)
            price_edit.setText(f"{int(price):,}")
        
        self.calculate_row_total(row)
    
    def calculate_row_total(self, row):
        qty = self.items_table.cellWidget(row, 2)
        price = self.items_table.cellWidget(row, 3)
        total = self.items_table.cellWidget(row, 4)
        
        if qty and price and total:
            try:
                q = qty.value()
                p_text = price.text().replace(',', '').strip()
                p = int(float(p_text)) if p_text else 0
                t = q * p
                total.setText(f"{t:,.0f}")
            except Exception:
                total.setText("۰")
        
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
        if QMessageBox.question(self, "تأیید", "همه اقلام پاک شوند؟",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.items_table.setRowCount(0)
            self.calculate_totals()
    
    def reindex_rows(self):
        for row in range(self.items_table.rowCount()):
            btn = self.items_table.cellWidget(row, 6)
            if btn:
                try:
                    btn.clicked.disconnect()
                except Exception:
                    pass
                btn.clicked.connect(lambda checked, r=row: self.remove_row(r))
    
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
        
        return total, tax
    
    def load_document_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('SELECT * FROM documents WHERE id = ?', [self.doc_id])
                doc = row_to_dict(c.fetchone())
                if not doc:
                    return
                
                if doc.get('date'):
                    self.date.set_date(doc.get('date'))
                
                idx = self.party_combo.findData(doc.get('party_id'))
                if idx >= 0:
                    self.party_combo.setCurrentIndex(idx)
                
                if doc.get('discount'):
                    self.discount_input.setText(f"{int(doc.get('discount')):,}")
                
                c.execute("""
                    SELECT product_id, quantity, unit_price
                    FROM document_items WHERE document_id = ?
                """, [self.doc_id])
                
                for item in c.fetchall():
                    self.add_product_row(row_to_dict(item))
                
                self.calculate_totals()
        except Exception as e:
            logger.error(f"خطا در بارگذاری: {e}")
    
    def save_document(self):
        if self.party_combo.currentIndex() < 0:
            QMessageBox.warning(self, "خطا", "طرف حساب را انتخاب کنید!")
            return
        
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "حداقل یک کالا اضافه کنید!")
            return
        
        # جمع‌آوری اقلام
        items = []
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 1)
            qty = self.items_table.cellWidget(row, 2)
            price = self.items_table.cellWidget(row, 3)
            
            if not combo or combo.currentIndex() <= 0:
                continue
            
            try:
                q = qty.value() if qty else 0
                p_text = price.text().replace(',', '').strip() if price else "0"
                p = int(float(p_text)) if p_text else 0
                
                if q > 0 and p > 0:
                    items.append({
                        'product_id': combo.currentData(),
                        'quantity': q,
                        'unit_price': p,
                        'total_price': q * p
                    })
            except Exception:
                continue
        
        if not items:
            QMessageBox.warning(self, "خطا", "هیچ آیتم معتبری وجود ندارد!")
            return
        
        # چک موجودی برای فروش
        if is_sales_type(self.doc_type):
            with get_db() as conn:
                c = conn.cursor()
                for item in items:
                    c.execute("""
                        SELECT COALESCE(SUM(quantity), 0) FROM warehouse_stock
                        WHERE product_id = ?
                    """, [item['product_id']])
                    row_data = c.fetchone()
                    available = float(row_data[0]) if row_data else 0
                    
                    if self._editing:
                        c.execute("""
                            SELECT COALESCE(quantity, 0) FROM document_items
                            WHERE document_id = ? AND product_id = ?
                        """, [self.doc_id, item['product_id']])
                        old = c.fetchone()
                        if old:
                            available += float(old[0] or 0)
                    
                    if item['quantity'] > available:
                        product = next((p for p in self.products if p['id'] == item['product_id']), None)
                        name = product['name'] if product else f"#{item['product_id']}"
                        QMessageBox.warning(self, "موجودی ناکافی",
                            f"⚠️ موجودی '{name}' کافی نیست!\n"
                            f"موجودی: {available:,.2f} | درخواست: {item['quantity']:,.2f}")
                        return
        
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                party_id = self.party_combo.currentData()
                shamsi_date = self.date.get_shamsi()
                
                if self._editing:
                    # برگرداندن موجودی قبلی
                    c.execute("SELECT product_id, quantity FROM document_items WHERE document_id = ?",
                             [self.doc_id])
                    for old in c.fetchall():
                        old_dict = row_to_dict(old)
                        old_pid = old_dict.get('product_id')
                        old_qty = old_dict.get('quantity', 0)
                        
                        if is_sales_type(self.doc_type):
                            c.execute("UPDATE products SET stock = stock + ? WHERE id = ?",
                                     [old_qty, old_pid])
                        else:
                            c.execute("UPDATE products SET stock = stock - ? WHERE id = ?",
                                     [old_qty, old_pid])
                    
                    c.execute('DELETE FROM document_items WHERE document_id = ?', [self.doc_id])
                    
                    c.execute("""
                        UPDATE documents 
                        SET date = ?, party_id = ?, total_amount = ?, 
                            discount = ?, tax = ?, net_amount = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, [shamsi_date, party_id, self._total_amount,
                          self._discount, self._tax, self._net_amount, self.doc_id])
                    
                    doc_id = self.doc_id
                else:
                    prefix = get_doc_type_prefix(self.doc_type)
                    c.execute(f"""
                        SELECT MAX(CAST(SUBSTR(doc_no, 4) AS INTEGER))
                        FROM documents WHERE doc_no LIKE '{prefix}%'
                    """)
                    max_no = c.fetchone()[0] or 0
                    doc_no = f"{prefix}{(max_no + 1):06d}"
                    
                    c.execute("""
                        INSERT INTO documents 
                        (doc_no, doc_type, date, party_id, total_amount, 
                         discount, tax, net_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [doc_no, self.doc_type, shamsi_date, party_id,
                          self._total_amount, self._discount,
                          self._tax, self._net_amount])
                    
                    doc_id = c.lastrowid
                
                # درج اقلام + بروزرسانی انبار
                for item in items:
                    c.execute("""
                        INSERT INTO document_items 
                        (document_id, product_id, quantity, unit_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    """, [doc_id, item['product_id'], item['quantity'],
                          item['unit_price'], item['total_price']])
                    
                    if is_sales_type(self.doc_type):
                        c.execute("UPDATE products SET stock = stock - ? WHERE id = ?",
                                 [item['quantity'], item['product_id']])
                        c.execute("""
                            UPDATE warehouse_stock 
                            SET quantity = quantity - ?
                            WHERE product_id = ?
                        """, [item['quantity'], item['product_id']])
                    else:
                        c.execute("UPDATE products SET stock = stock + ? WHERE id = ?",
                                 [item['quantity'], item['product_id']])
                        c.execute("""
                            UPDATE warehouse_stock 
                            SET quantity = quantity + ?
                            WHERE product_id = ?
                        """, [item['quantity'], item['product_id']])
                
                conn.commit()
            
            super().accept()
        except Exception as e:
            logger.error(f"خطا در ذخیره: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def apply_theme(self):
        self.setStyleSheet("""
            QDialog { background: #f5f6fa; }
            QGroupBox {
                background: white; color: #1a1a2e;
                border: 1px solid #dcdde1; border-radius: 6px;
                margin-top: 12px; padding: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #1976D2; padding: 0 8px;
                subcontrol-origin: margin; left: 10px;
            }
            QTableWidget {
                background: white; color: #1a1a2e;
                border: 1px solid #dcdde1; border-radius: 6px;
                gridline-color: #dcdde1;
            }
            QHeaderView::section {
                background: #e8e8e8; color: #1a1a2e;
                padding: 8px; border: none; font-weight: bold;
            }
            QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox {
                background: white; color: #1a1a2e;
                border: 1px solid #dcdde1; border-radius: 6px;
                padding: 6px 10px; min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #1976D2;
            }
        """)
