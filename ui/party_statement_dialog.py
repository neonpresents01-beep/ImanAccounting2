# ui/party_statement_dialog.py
# ============================================================
# دیالوگ صورت حساب اشخاص
# ============================================================

import csv
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from ui.base_widgets import BaseDialog
from database import get_db, DateConverter
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali


class PartyStatementDialog(BaseDialog):
    """دیالوگ صورت حساب یک شخص"""
    
    def __init__(self, party_id: int, party_name: str, 
                 party_type: str = 'customer', parent=None):
        super().__init__(parent, base_width=950, base_height=700)
        
        self.party_id = party_id
        self.party_name = party_name
        self.party_type = party_type
        
        self.setWindowTitle(f"📊 صورت حساب — {party_name}")
        self.setModal(True)
        
        self.setup_ui()
        self.load_statement()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QHBoxLayout()
        
        icon = QLabel("👤" if self.party_type == 'customer' else "🏢")
        icon.setStyleSheet("font-size: 32pt;")
        header.addWidget(icon)
        
        title_layout = QVBoxLayout()
        title = QLabel(self.party_name)
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        title_layout.addWidget(title)
        
        subtitle = QLabel(
            f"{'مشتری' if self.party_type == 'customer' else 'فروشنده'}"
        )
        subtitle.setStyleSheet("color: #888; font-size: 10pt;")
        title_layout.addWidget(subtitle)
        
        header.addLayout(title_layout)
        header.addStretch()
        
        self.balance_badge = QLabel("مانده: 0 ریال")
        self.balance_badge.setStyleSheet("""
            background: #1976D2; color: white; padding: 10px 20px;
            border-radius: 8px; font-weight: bold; font-size: 12pt;
        """)
        header.addWidget(self.balance_badge)
        
        layout.addLayout(header)
        
        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        filter_layout.addWidget(QLabel("📅 از:"))
        self.from_date = ShamsiDateEdit()
        
        try:
            from persiantools.jdatetime import JalaliDate
            six_months_ago = JalaliDate.today() - timedelta(days=180)
            self.from_date.set_date(six_months_ago.strftime("%Y/%m/%d"))
        except Exception:
            self.from_date.set_date(get_today_jalali())
        
        self.from_date.dateChanged.connect(self.load_statement)
        filter_layout.addWidget(self.from_date)
        
        filter_layout.addWidget(QLabel("تا:"))
        self.to_date = ShamsiDateEdit()
        self.to_date.set_date(get_today_jalali())
        self.to_date.dateChanged.connect(self.load_statement)
        filter_layout.addWidget(self.to_date)
        
        filter_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setObjectName("infoBtn")
        refresh_btn.clicked.connect(self.load_statement)
        filter_layout.addWidget(refresh_btn)
        
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "تاریخ", "نوع", "شرح", "بدهکار", "بستانکار", "مانده", "مرجع"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        
        # Summary
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("""
            background: #f0f0f0; padding: 12px;
            border-radius: 6px; font-weight: bold; font-size: 11pt;
        """)
        layout.addWidget(self.summary_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        pdf_btn = QPushButton("📄 PDF")
        pdf_btn.setObjectName("successBtn")
        pdf_btn.clicked.connect(self.export_to_pdf)
        btn_layout.addWidget(pdf_btn)
        
        csv_btn = QPushButton("📎 Excel")
        csv_btn.setObjectName("warningBtn")
        csv_btn.clicked.connect(self.export_to_csv)
        btn_layout.addWidget(csv_btn)
        
        close_btn = QPushButton("❌ بستن")
        close_btn.setObjectName("dangerBtn")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def load_statement(self):
        """بارگذاری صورت حساب"""
        try:
            from_date = self.from_date.get_shamsi()
            to_date = self.to_date.get_shamsi()
            from_g = DateConverter.for_db(from_date)
            to_g = DateConverter.for_db(to_date)
            
            transactions = []
            
            with get_db() as conn:
                c = conn.cursor()
                
                # فاکتورها
                try:
                    c.execute("""
                        SELECT d.date, d.doc_type, d.doc_no, d.net_amount, d.description
                        FROM documents d
                        WHERE d.party_id = ? AND d.date >= ? AND d.date <= ?
                        ORDER BY d.date ASC
                    """, [self.party_id, from_g, to_g])
                    
                    for row in c.fetchall():
                        r = dict(row)
                        is_sale = r['doc_type'] == 'sales'
                        transactions.append({
                            'date': r['date'],
                            'type': 'فروش' if is_sale else 'خرید',
                            'description': f"{'فاکتور فروش' if is_sale else 'فاکتور خرید'} {r['doc_no']}: {r['description'] or ''}",
                            'debit': r['net_amount'] if is_sale else 0,
                            'credit': 0 if is_sale else r['net_amount'],
                            'ref': r['doc_no'],
                            'icon': '📤' if is_sale else '📥',
                        })
                except Exception as e:
                    print(f"خطا در فاکتورها: {e}")
                
                # تراکنش‌های مالی
                try:
                    c.execute("""
                        SELECT t.date, t.type, t.amount, t.description, t.transaction_no
                        FROM finance_transactions t
                        WHERE t.party_id = ? AND t.date >= ? AND t.date <= ?
                        ORDER BY t.date ASC
                    """, [self.party_id, from_g, to_g])
                    
                    type_names = {
                        'receipt': 'دریافت', 'payment': 'پرداخت',
                        'income': 'درآمد', 'expense': 'هزینه',
                        'transfer': 'انتقال', 'capital': 'سرمایه',
                    }
                    
                    for row in c.fetchall():
                        r = dict(row)
                        is_receipt = r['type'] in ('receipt', 'income')
                        transactions.append({
                            'date': r['date'],
                            'type': type_names.get(r['type'], r['type']),
                            'description': r['description'] or f"تراکنش {r['transaction_no']}",
                            'debit': 0 if is_receipt else r['amount'],
                            'credit': r['amount'] if is_receipt else 0,
                            'ref': r['transaction_no'],
                            'icon': '💰' if is_receipt else '💸',
                        })
                except Exception as e:
                    print(f"خطا در تراکنش‌ها: {e}")
                
                # چک‌ها
                try:
                    c.execute("""
                        SELECT c.issue_date, c.check_number, c.type, c.amount,
                               c.status, c.bank_name
                        FROM checks c
                        WHERE c.party_id = ? AND c.issue_date >= ? AND c.issue_date <= ?
                        ORDER BY c.issue_date ASC
                    """, [self.party_id, from_g, to_g])
                    
                    status_map = {
                        'pending': 'در جریان', 'collected': 'وصول شده',
                        'bounced': 'برگشتی', 'cancelled': 'ابطالی',
                        'postponed': 'به تعویق',
                    }
                    
                    for row in c.fetchall():
                        r = dict(row)
                        is_received = r['type'] == 'received'
                        transactions.append({
                            'date': r['issue_date'],
                            'type': 'چک دریافتی' if is_received else 'چک پرداختی',
                            'description': f"چک {r['check_number']} - {r['bank_name'] or ''} ({status_map.get(r['status'], r['status'])})",
                            'debit': 0 if is_received else r['amount'],
                            'credit': r['amount'] if is_received else 0,
                            'ref': r['check_number'],
                            'icon': '📥' if is_received else '📤',
                        })
                except Exception as e:
                    print(f"خطا در چک‌ها: {e}")
            
            transactions.sort(key=lambda x: x.get('date', ''))
            
            self.table.setRowCount(len(transactions))
            balance = 0
            
            for i, t in enumerate(transactions):
                self.table.setItem(i, 0, QTableWidgetItem(safe_display_date(t['date'])))
                self.table.setItem(i, 1, QTableWidgetItem(f"{t['icon']} {t['type']}"))
                self.table.setItem(i, 2, QTableWidgetItem(t['description']))
                
                if t['debit'] > 0:
                    item = QTableWidgetItem(f"{t['debit']:,.0f}")
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setForeground(QColor('#27ae60'))
                    self.table.setItem(i, 3, item)
                else:
                    self.table.setItem(i, 3, QTableWidgetItem("-"))
                
                if t['credit'] > 0:
                    item = QTableWidgetItem(f"{t['credit']:,.0f}")
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setForeground(QColor('#e74c3c'))
                    self.table.setItem(i, 4, item)
                else:
                    self.table.setItem(i, 4, QTableWidgetItem("-"))
                
                balance += t['debit'] - t['credit']
                bal_item = QTableWidgetItem(f"{balance:,.0f}")
                bal_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if balance > 0:
                    bal_item.setForeground(QColor('#e74c3c'))
                elif balance < 0:
                    bal_item.setForeground(QColor('#27ae60'))
                self.table.setItem(i, 5, bal_item)
                
                self.table.setItem(i, 6, QTableWidgetItem(t.get('ref', '')))
            
            # خلاصه
            total_debit = sum(t['debit'] for t in transactions)
            total_credit = sum(t['credit'] for t in transactions)
            final_balance = total_debit - total_credit
            
            balance_text = (
                f"{final_balance:,.0f} ریال بدهکار" if final_balance > 0
                else f"{abs(final_balance):,.0f} ریال بستانکار" if final_balance < 0
                else "تسویه شده"
            )
            
            self.summary_label.setText(
                f"📊 تعداد: {len(transactions)} | "
                f"💰 جمع بدهکار: {total_debit:,.0f} | "
                f"💸 جمع بستانکار: {total_credit:,.0f} | "
                f"📈 مانده: {balance_text}"
            )
            
            if final_balance > 0:
                self.balance_badge.setText(f"بدهکار: {final_balance:,.0f} ریال")
                self.balance_badge.setStyleSheet("""
                    background: #e74c3c; color: white; padding: 10px 20px;
                    border-radius: 8px; font-weight: bold; font-size: 12pt;
                """)
            elif final_balance < 0:
                self.balance_badge.setText(f"بستانکار: {abs(final_balance):,.0f} ریال")
                self.balance_badge.setStyleSheet("""
                    background: #27ae60; color: white; padding: 10px 20px;
                    border-radius: 8px; font-weight: bold; font-size: 12pt;
                """)
            else:
                self.balance_badge.setText("تسویه شده")
                self.balance_badge.setStyleSheet("""
                    background: #95a5a6; color: white; padding: 10px 20px;
                    border-radius: 8px; font-weight: bold; font-size: 12pt;
                """)
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "خطا", f"❌ خطا:\n{str(e)}")
    
    def export_to_pdf(self):
        try:
            from ui.accounting_pdf import AccountingPDFGenerator
            
            default_name = f"صورت_حساب_{self.party_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
            file_path = AccountingPDFGenerator.ask_save_path(self, default_name)
            if not file_path:
                return
            
            html = self._generate_html()
            
            from PyQt5.QtPrintSupport import QPrinter
            from PyQt5.QtGui import QTextDocument
            from PyQt5.QtCore import QSizeF
            
            printer = QPrinter(QPrinter.ScreenResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
            
            doc = QTextDocument()
            doc.setHtml(html)
            rect = printer.pageRect(QPrinter.DevicePixel)
            doc.setPageSize(QSizeF(rect.width(), rect.height()))
            doc.print_(printer)
            
            QMessageBox.information(self, "موفق", f"✅ ذخیره شد:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "خطا", str(e))
    
    def export_to_csv(self):
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "ذخیره",
                f"صورت_حساب_{self.party_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                "CSV Files (*.csv)"
            )
            if not file_name:
                return
            
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["تاریخ", "نوع", "شرح", "بدهکار", "بستانکار", "مانده", "مرجع"])
                
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "موفق", f"✅ ذخیره شد:\n{file_name}")
        except Exception as e:
            QMessageBox.warning(self, "خطا", str(e))
    
    def _generate_html(self) -> str:
        headers = []
        for col in range(self.table.columnCount()):
            h = self.table.horizontalHeaderItem(col)
            headers.append(h.text() if h else "")
        
        rows_html = ""
        for row in range(self.table.rowCount()):
            row_html = "<tr>"
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                text = item.text() if item else ""
                row_html += f"<td style='padding:6px; border:1px solid #ddd;'>{text}</td>"
            row_html += "</tr>"
            rows_html += row_html
        
        headers_html = "".join([
            f"<th style='padding:8px; border:1px solid #ddd; background:#273c75; color:white;'>{h}</th>"
            for h in headers
        ])
        
        return f"""
        <html><head><meta charset="UTF-8"></head>
        <body style="font-family: Tahoma; direction: rtl; padding: 20px;">
            <h2 style="text-align:center; color:#273c75;">📊 صورت حساب</h2>
            <p style="text-align:center; font-size:14pt;"><b>{self.party_name}</b></p>
            <p style="text-align:center; color:#666;">
                از {self.from_date.get_shamsi()} تا {self.to_date.get_shamsi()}
            </p>
            <hr>
            <table style="width:100%; border-collapse:collapse; font-size:9pt;">
                <thead><tr>{headers_html}</tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            <hr>
            <p style="text-align:center; color:#888; font-size:9pt;">
                تاریخ چاپ: {datetime.now().strftime('%Y/%m/%d %H:%M')} | ImanAccount
            </p>
        </body></html>
        """
    
    def apply_theme(self):
        pass
