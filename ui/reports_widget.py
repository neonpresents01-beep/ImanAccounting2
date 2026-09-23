# ui/reports_widget.py
# ============================================================
# ویجت گزارشات جامع حسابداری — نسخه 2.0 (Theme-Integrated)
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime, timedelta
from database import get_db, AccountingHelper
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali
from ui.base_widgets import BaseWidget
import csv
import logging

logger = logging.getLogger(__name__)


class ReportsWidget(BaseWidget):
    """ویجت گزارشات جامع — نسخه یکپارچه با تم"""
    
    def __init__(self, parent=None, user_level: str = 'viewer'):
        super().__init__(parent)
        self._user_level = user_level
        self.init_ui()
        self.refresh_all_reports()
        self._apply_widget_theme()
    
    # ============================================================
    # Theme — کامل و یکپارچه (مثل settings_widget)
    # ============================================================
    
    def _apply_widget_theme(self):
        """اعمال تم روی کل ویجت و همه فرزندان"""
        try:
            c = self.get_theme_colors()
            
            # 1. خود ویجت
            self.setStyleSheet(f"""
                QWidget {{
                    background: {c['bg']};
                    color: {c['text']};
                }}
            """)
            
            # 2. TabWidget
            if hasattr(self, 'tab_widget'):
                self.tab_widget.setStyleSheet(f"""
                    QTabWidget::pane {{
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                        background: {c['bg']};
                    }}
                    QTabBar::tab {{
                        padding: 10px 18px;
                        margin: 2px;
                        border-radius: 6px;
                        background: {c['bg_alt']};
                        color: {c['text']};
                        font-weight: bold;
                    }}
                    QTabBar::tab:selected {{
                        background: {c['selected']};
                        color: {c['selected_text']};
                    }}
                    QTabBar::tab:hover {{
                        background: {c['hover']};
                    }}
                """)
            
            # 3. QGroupBoxها
            for gb in self.findChildren(QGroupBox):
                gb.setStyleSheet(f"""
                    QGroupBox {{
                        background: {c['card']};
                        color: {c['text']};
                        border: 2px solid {c['border']};
                        border-radius: 8px;
                        margin-top: 15px;
                        padding: 15px 10px 10px 10px;
                        font-weight: bold;
                        font-size: 11pt;
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        subcontrol-position: top right;
                        right: 15px;
                        padding: 0 8px;
                        color: {c['selected']};
                        background: {c['bg']};
                    }}
                """)
            
            # 4. ScrollArea
            for sa in self.findChildren(QScrollArea):
                sa.setStyleSheet(f"""
                    QScrollArea {{
                        border: none;
                        background: transparent;
                    }}
                    QScrollBar:vertical {{
                        background: {c['bg_alt']};
                        width: 10px;
                        border-radius: 5px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: {c['border']};
                        border-radius: 5px;
                        min-height: 20px;
                    }}
                    QScrollBar::handle:vertical:hover {{
                        background: {c['selected']};
                    }}
                    QScrollBar:horizontal {{
                        background: {c['bg_alt']};
                        height: 10px;
                        border-radius: 5px;
                    }}
                    QScrollBar::handle:horizontal {{
                        background: {c['border']};
                        border-radius: 5px;
                        min-width: 20px;
                    }}
                """)
            
            # 5. QTableWidget — استایل کامل و یکپارچه
            for tbl in self.findChildren(QTableWidget):
                tbl.setStyleSheet(f"""
                    QTableWidget {{
                        background: {c['bg_alt']};
                        alternate-background-color: {c['bg']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        gridline-color: {c['border']};
                        selection-background-color: {c['selected']};
                        selection-color: {c['selected_text']};
                    }}
                    QTableWidget::item {{
                        padding: 6px;
                        border: none;
                    }}
                    QTableWidget::item:selected {{
                        background: {c['selected']};
                        color: {c['selected_text']};
                    }}
                    QHeaderView::section {{
                        background: {c['card']};
                        color: {c['text']};
                        padding: 8px;
                        border: none;
                        border-right: 1px solid {c['border']};
                        border-bottom: 1px solid {c['border']};
                        font-weight: bold;
                    }}
                    QHeaderView::section:hover {{
                        background: {c['hover']};
                    }}
                    QTableCornerButton::section {{
                        background: {c['card']};
                        border: 1px solid {c['border']};
                    }}
                """)
            
            # 6. QTextEditها
            for te in self.findChildren(QTextEdit):
                te.setStyleSheet(f"""
                    QTextEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                    }}
                """)
            
            # 7. QLineEditها
            for le in self.findChildren(QLineEdit):
                le.setStyleSheet(f"""
                    QLineEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 6px 10px;
                        min-height: 26px;
                    }}
                    QLineEdit:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
            # 8. QComboBoxها
            for cb in self.findChildren(QComboBox):
                cb.setStyleSheet(f"""
                    QComboBox {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 6px 10px;
                        min-height: 26px;
                    }}
                    QComboBox:focus {{
                        border: 2px solid {c['selected']};
                    }}
                    QComboBox::drop-down {{
                        border: none;
                        width: 24px;
                    }}
                    QComboBox QAbstractItemView {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        selection-background-color: {c['selected']};
                        selection-color: {c['selected_text']};
                        border: 1px solid {c['border']};
                    }}
                """)
            
            # 9. QSpinBox و QDoubleSpinBox
            for sb in self.findChildren((QSpinBox, QDoubleSpinBox)):
                sb.setStyleSheet(f"""
                    QSpinBox, QDoubleSpinBox {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 6px;
                        min-height: 26px;
                    }}
                    QSpinBox:focus, QDoubleSpinBox:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
            # 10. QPushButtonها — با objectName خاص
            button_styles = {
                'successBtn': (c['success'], '#ffffff'),
                'warningBtn': (c['warning'], '#000000'),
                'dangerBtn': (c['danger'], '#ffffff'),
                'infoBtn': (c['selected'], c['selected_text']),
            }
            
            for btn in self.findChildren(QPushButton):
                obj_name = btn.objectName()
                
                if obj_name in button_styles:
                    bg, fg = button_styles[obj_name]
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {bg};
                            color: {fg};
                            border: none;
                            border-radius: 6px;
                            padding: 8px 16px;
                            font-weight: bold;
                            min-height: 30px;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                            color: {c['text']};
                        }}
                        QPushButton:pressed {{
                            background: {c['border']};
                        }}
                        QPushButton:disabled {{
                            background: {c['bg_alt']};
                            color: {c['text_secondary']};
                        }}
                    """)
                else:
                    # دکمه‌های عادی
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {c['bg_alt']};
                            color: {c['text']};
                            border: 1px solid {c['border']};
                            border-radius: 6px;
                            padding: 8px 16px;
                            font-weight: bold;
                            min-height: 30px;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                            border: 1px solid {c['selected']};
                        }}
                        QPushButton:pressed {{
                            background: {c['selected']};
                            color: {c['selected_text']};
                        }}
                        QPushButton:disabled {{
                            background: {c['bg']};
                            color: {c['text_secondary']};
                        }}
                    """)
            
            # 11. QLabelهای عمومی (فقط متن‌ها، نه عنوان‌ها)
            for lbl in self.findChildren(QLabel):
                obj_name = lbl.objectName()
                
                if obj_name == 'titleLabel':
                    lbl.setStyleSheet(f"""
                        color: {c['selected']};
                        font-size: 18pt;
                        font-weight: bold;
                        padding: 10px;
                        background: transparent;
                    """)
                elif not lbl.styleSheet() or 'background' not in lbl.styleSheet():
                    text = lbl.text() or ""
                    # فقط لیبل‌های معمولی (نه اموجی‌های عنوان)
                    if not any(text.startswith(p) for p in [
                        '🏢', '🖼️', '🌍', '📋', '📊', '💰', '🤖',
                        '💾', '🔧', '📅', '⚙️', '📝', '💡', '✏️',
                        '📈', '🏦', '📉', '🔒', '👥', '📦', '💵',
                        '⚠️', '✅', '❌'
                    ]):
                        lbl.setStyleSheet(
                            f"color: {c['text']}; background: transparent; padding: 3px;"
                        )
            
            # 12. StatusBar
            if hasattr(self, 'statusBar'):
                self.statusBar.setStyleSheet(f"""
                    QStatusBar {{
                        background: {c['card']};
                        color: {c['text']};
                        font-weight: bold;
                        border-top: 1px solid {c['border']};
                    }}
                """)
            
            # 13. لیبل‌های جمع‌بندی (total_label)
            for attr in ['trial_total_label', 'adj_trial_total_label',
                         'opening_total_label', 'customers_total_label',
                         'inv_total_label', 'payroll_total_label']:
                if hasattr(self, attr):
                    getattr(self, attr).setStyleSheet(f"""
                        background: {c['card']};
                        color: {c['text']};
                        padding: 10px;
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        font-weight: bold;
                    """)
            
            # 14. لیبل‌های اطلاعاتی خاص
            for attr in ['closing_info', 'closing_result']:
                if hasattr(self, attr):
                    getattr(self, attr).setStyleSheet(f"""
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 8px;
                        font-family: Tahoma;
                    """)
            
            # 15. QTextEditهای گزارش متنی
            for attr in ['profit_loss_text', 'capital_text', 'bs_text',
                         'cash_flow_text', 'ratios_text']:
                if hasattr(self, attr):
                    getattr(self, attr).setStyleSheet(f"""
                        QTextEdit {{
                            background: {c['bg_alt']};
                            color: {c['text']};
                            font-family: Tahoma;
                            font-size: 11pt;
                            border: 1px solid {c['border']};
                            border-radius: 6px;
                            padding: 8px;
                        }}
                    """)
            
            # 16. فرم‌های QFormLayout — layout labels
            for form in self.findChildren(QFormLayout):
                for i in range(form.rowCount()):
                    label_item = form.itemAt(i, QFormLayout.LabelRole)
                    if label_item:
                        w = label_item.widget()
                        if isinstance(w, QLabel):
                            w.setStyleSheet(
                                f"color: {c['text']}; background: transparent; padding: 3px; font-weight: bold;"
                            )
        
        except Exception as e:
            print(f"⚠️ خطا در _apply_widget_theme: {e}")
    
    # ============================================================
    # Permission
    # ============================================================
    
    def set_user_level(self, level: str):
        self._user_level = level
    
    def get_user_level(self) -> str:
        return self._user_level
    
    # ============================================================
    # UI Setup
    # ============================================================
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("📊 گزارشات جامع حسابداری")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # Tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("reportsTabs")
        
        # گزارشات پایه
        self.tab_widget.addTab(self.create_trial_balance_tab(), "📋 تراز آزمایشی")
        self.tab_widget.addTab(self.create_adjusting_entries_tab(), "✏️ ثبت اصلاحیه")
        self.tab_widget.addTab(self.create_adjusted_trial_tab(), "📋 تراز آزمایشی (بعد از اصلاح)")
        self.tab_widget.addTab(self.create_profit_loss_tab(), "💰 صورت سود و زیان")
        self.tab_widget.addTab(self.create_capital_statement_tab(), "🏦 صورت سرمایه")
        self.tab_widget.addTab(self.create_balance_sheet_tab(), "📊 ترازنامه")
        self.tab_widget.addTab(self.create_closing_entries_tab(), "🔒 بستن حساب‌ها")
        self.tab_widget.addTab(self.create_opening_trial_tab(), "📋 تراز افتتاحیه")
        
        # گزارشات پیشرفته
        self.tab_widget.addTab(self.create_cash_flow_tab(), "💰 جریان نقدی")
        self.tab_widget.addTab(self.create_ratios_tab(), "📊 نسبت‌های مالی")
        self.tab_widget.addTab(self.create_customers_report_tab(), "👥 گزارش مشتریان")
        self.tab_widget.addTab(self.create_inventory_report_tab(), "📦 گزارش انبار")
        self.tab_widget.addTab(self.create_payroll_report_tab(), "💵 گزارش حقوق")
        
        layout.addWidget(self.tab_widget)
        
        # StatusBar
        self.statusBar = QStatusBar()
        self.statusBar.setObjectName("reportsStatusBar")
        layout.addWidget(self.statusBar)
        self.statusBar.showMessage("✅ آماده")
    
    def refresh_all_reports(self):
        """بروزرسانی همه گزارشات"""
        QTimer.singleShot(100, self.show_trial_balance)
        QTimer.singleShot(200, self.show_adjusted_trial_balance)
        QTimer.singleShot(300, self.show_profit_loss)
        QTimer.singleShot(400, self.show_capital_statement)
        QTimer.singleShot(500, self.show_balance_sheet)
        QTimer.singleShot(600, self.show_opening_trial_balance)
        QTimer.singleShot(700, self.show_inventory_report)
        QTimer.singleShot(800, self.show_payroll_report)
        QTimer.singleShot(900, self.show_cash_flow)
        QTimer.singleShot(1000, self.show_ratios)
        QTimer.singleShot(1100, self.show_customers_report)
    
    # ============================================================
    # Helper: دکمه‌های کنترلی استاندارد
    # ============================================================
    
    def _make_show_button(self, callback):
        btn = QPushButton("📊 نمایش")
        btn.setObjectName("infoBtn")
        btn.clicked.connect(callback)
        return btn
    
    def _make_export_button(self, callback):
        btn = QPushButton("📎 خروجی Excel")
        btn.setObjectName("successBtn")
        btn.clicked.connect(callback)
        return btn
    
    # ============================================================
    # تراز آزمایشی
    # ============================================================
    
    def create_trial_balance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("تاریخ:"))
        self.trial_date = ShamsiDateEdit()
        control_layout.addWidget(self.trial_date)
        
        control_layout.addWidget(self._make_show_button(self.show_trial_balance))
        control_layout.addWidget(self._make_export_button(
            lambda: self.export_table_to_excel(self.trial_table, "تراز_آزمایشی")
        ))
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.trial_table = QTableWidget()
        self.trial_table.setColumnCount(6)
        self.trial_table.setHorizontalHeaderLabels(
            ["کد", "نام حساب", "بدهکار", "بستانکار", "مانده بدهکار", "مانده بستانکار"]
        )
        self.trial_table.horizontalHeader().setStretchLastSection(True)
        self.trial_table.setAlternatingRowColors(True)
        layout.addWidget(self.trial_table)
        
        self.trial_total_label = QLabel()
        layout.addWidget(self.trial_total_label)
        
        return widget
    
    def show_trial_balance(self):
        shamsi_date = self.trial_date.get_shamsi()
        gregorian_date = self._shamsi_to_gregorian(shamsi_date)
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT a.code, a.name, a.type,
                       COALESCE(SUM(vi.debit), 0) as debit,
                       COALESCE(SUM(vi.credit), 0) as credit
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE v.date <= ? OR v.date IS NULL
                GROUP BY a.code, a.name, a.type
                ORDER BY a.code
            ''', [gregorian_date])
            data = c.fetchall()
        
        self._display_trial_balance(
            self.trial_table, self.trial_total_label, data, shamsi_date
        )
    
    def _display_trial_balance(self, table, label, data, date_str=""):
        table.setRowCount(len(data))
        
        total_debit = 0
        total_credit = 0
        total_balance_debit = 0
        total_balance_credit = 0
        
        for i, row in enumerate(data):
            table.setItem(i, 0, QTableWidgetItem(row['code']))
            table.setItem(i, 1, QTableWidgetItem(row['name']))
            
            debit = row['debit'] or 0
            credit = row['credit'] or 0
            
            debit_item = QTableWidgetItem(f"{debit:,.0f}")
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(i, 2, debit_item)
            
            credit_item = QTableWidgetItem(f"{credit:,.0f}")
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(i, 3, credit_item)
            
            if row['type'] in ['asset', 'expense']:
                balance = debit - credit
                balance_debit = balance if balance > 0 else 0
                balance_credit = -balance if balance < 0 else 0
            else:
                balance = credit - debit
                balance_debit = -balance if balance < 0 else 0
                balance_credit = balance if balance > 0 else 0
            
            bal_debit_item = QTableWidgetItem(
                f"{balance_debit:,.0f}" if balance_debit > 0 else "-"
            )
            bal_debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(i, 4, bal_debit_item)
            
            bal_credit_item = QTableWidgetItem(
                f"{balance_credit:,.0f}" if balance_credit > 0 else "-"
            )
            bal_credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(i, 5, bal_credit_item)
            
            total_debit += debit
            total_credit += credit
            total_balance_debit += balance_debit
            total_balance_credit += balance_credit
        
        title = f"📊 تراز آزمایشی - {date_str}" if date_str else "📊 تراز آزمایشی"
        label.setText(
            f"{title}\n"
            f"جمع گردش بدهکار: {total_debit:,.0f} | "
            f"جمع گردش بستانکار: {total_credit:,.0f} | "
            f"جمع مانده بدهکار: {total_balance_debit:,.0f} | "
            f"جمع مانده بستانکار: {total_balance_credit:,.0f}"
        )
    
    # ============================================================
    # ثبت اصلاحیه
    # ============================================================
    
    def create_adjusting_entries_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("✏️ ثبت سند اصلاحی (Adjusting Entry)")
        info.setObjectName("titleLabel")
        layout.addWidget(info)
        
        desc = QLabel("اصلاحات پایان دوره مانند استهلاک، پیش‌پرداخت‌ها، تعهدات و ...")
        layout.addWidget(desc)
        
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        
        self.adj_description = QLineEdit()
        self.adj_description.setPlaceholderText("شرح اصلاحیه (مثلاً: استهلاک دارایی)")
        form_layout.addRow("شرح:", self.adj_description)
        
        self.adj_date = ShamsiDateEdit()
        form_layout.addRow("تاریخ:", self.adj_date)
        
        self.load_accounts_for_combo()
        
        form_layout.addRow(QLabel("<b>اقلام سند اصلاحی:</b>"))
        
        self.adj_items_table = QTableWidget()
        self.adj_items_table.setColumnCount(5)
        self.adj_items_table.setHorizontalHeaderLabels(
            ["کد حساب", "نام حساب", "شرح", "بدهکار", "بستانکار"]
        )
        self.adj_items_table.setMinimumHeight(150)
        self.adj_items_table.horizontalHeader().setStretchLastSection(True)
        form_layout.addRow(self.adj_items_table)
        
        btn_layout = QHBoxLayout()
        
        add_row_btn = QPushButton("➕ افزودن ردیف")
        add_row_btn.setObjectName("infoBtn")
        add_row_btn.clicked.connect(self.add_adj_row)
        btn_layout.addWidget(add_row_btn)
        
        remove_row_btn = QPushButton("➖ حذف ردیف")
        remove_row_btn.setObjectName("dangerBtn")
        remove_row_btn.clicked.connect(self.remove_adj_row)
        btn_layout.addWidget(remove_row_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 ثبت اصلاحیه")
        save_btn.setObjectName("successBtn")
        save_btn.clicked.connect(self.save_adjusting_entry)
        btn_layout.addWidget(save_btn)
        
        form_layout.addRow(btn_layout)
        layout.addWidget(form_widget)
        
        return widget
    
    def load_accounts_for_combo(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code, name FROM accounts WHERE is_active = 1 ORDER BY code")
            self.accounts_list = c.fetchall()
    
    def add_adj_row(self):
        row = self.adj_items_table.rowCount()
        self.adj_items_table.insertRow(row)
        
        combo = QComboBox()
        for acc in self.accounts_list:
            combo.addItem(f"{acc['code']} - {acc['name']}", acc['code'])
        combo.currentIndexChanged.connect(lambda: self.update_account_name(row))
        self.adj_items_table.setCellWidget(row, 0, combo)
        
        name_item = QTableWidgetItem("")
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.adj_items_table.setItem(row, 1, name_item)
        
        self.adj_items_table.setItem(row, 2, QTableWidgetItem(""))
        
        debit_item = QTableWidgetItem("0")
        debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.adj_items_table.setItem(row, 3, debit_item)
        
        credit_item = QTableWidgetItem("0")
        credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.adj_items_table.setItem(row, 4, credit_item)
        
        if self.accounts_list:
            self.update_account_name(row)
    
    def update_account_name(self, row):
        combo = self.adj_items_table.cellWidget(row, 0)
        if combo:
            text = combo.currentText()
            if " - " in text:
                self.adj_items_table.item(row, 1).setText(text.split(" - ")[1])
    
    def remove_adj_row(self):
        row = self.adj_items_table.currentRow()
        if row >= 0:
            self.adj_items_table.removeRow(row)
    
    def save_adjusting_entry(self):
        if not self.adj_description.text():
            QMessageBox.warning(self, "خطا", "شرح اصلاحیه را وارد کنید!")
            return
        
        if self.adj_items_table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "حداقل یک ردیف اضافه کنید!")
            return
        
        total_debit = 0
        total_credit = 0
        items = []
        
        for row in range(self.adj_items_table.rowCount()):
            combo = self.adj_items_table.cellWidget(row, 0)
            if not combo:
                continue
            
            account_code = combo.currentData()
            description = self.adj_items_table.item(row, 2).text()
            
            try:
                debit = float(
                    self.adj_items_table.item(row, 3).text().replace(',', '') or 0
                )
                credit = float(
                    self.adj_items_table.item(row, 4).text().replace(',', '') or 0
                )
            except:
                QMessageBox.warning(self, "خطا", f"مقادیر ردیف {row+1} نامعتبر است!")
                return
            
            if debit == 0 and credit == 0:
                QMessageBox.warning(self, "خطا", f"ردیف {row+1} مبلغ ندارد!")
                return
            
            total_debit += debit
            total_credit += credit
            items.append({
                'account_code': account_code,
                'description': description,
                'debit': debit,
                'credit': credit
            })
        
        if abs(total_debit - total_credit) > 1:
            QMessageBox.warning(
                self, "خطا",
                f"سند موازنه نیست!\nاختلاف: {abs(total_debit - total_credit):,.0f}"
            )
            return
        
        gregorian_date = self._shamsi_to_gregorian(self.adj_date.get_shamsi())
        
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute("SELECT MAX(voucher_no) FROM vouchers")
            max_no = c.fetchone()[0] or 0
            voucher_no = max_no + 1
            
            c.execute('''
                INSERT INTO vouchers (voucher_no, date, description, type)
                VALUES (?, ?, ?, 'اصلاحی')
            ''', [voucher_no, gregorian_date,
                  f"اصلاحیه: {self.adj_description.text()}"])
            voucher_id = c.lastrowid
            
            for item in items:
                c.execute('''
                    INSERT INTO voucher_items 
                    (voucher_id, account_code, description, debit, credit)
                    VALUES (?, ?, ?, ?, ?)
                ''', [voucher_id, item['account_code'], item['description'],
                      item['debit'], item['credit']])
            
            conn.commit()
        
        QMessageBox.information(
            self, "موفق",
            f"✅ سند اصلاحی شماره {voucher_no} با موفقیت ثبت شد!"
        )
        
        self.adj_description.clear()
        self.adj_items_table.setRowCount(0)
        self.show_adjusted_trial_balance()
    
    # ============================================================
    # تراز آزمایشی اصلاح‌شده
    # ============================================================
    
    def create_adjusted_trial_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("تاریخ:"))
        self.adj_trial_date = ShamsiDateEdit()
        control_layout.addWidget(self.adj_trial_date)
        
        control_layout.addWidget(
            self._make_show_button(self.show_adjusted_trial_balance)
        )
        control_layout.addWidget(self._make_export_button(
            lambda: self.export_table_to_excel(
                self.adj_trial_table, "تراز_آزمایشی_اصلاح_شده"
            )
        ))
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.adj_trial_table = QTableWidget()
        self.adj_trial_table.setColumnCount(6)
        self.adj_trial_table.setHorizontalHeaderLabels(
            ["کد", "نام حساب", "بدهکار", "بستانکار", "مانده بدهکار", "مانده بستانکار"]
        )
        self.adj_trial_table.horizontalHeader().setStretchLastSection(True)
        self.adj_trial_table.setAlternatingRowColors(True)
        layout.addWidget(self.adj_trial_table)
        
        self.adj_trial_total_label = QLabel()
        layout.addWidget(self.adj_trial_total_label)
        
        return widget
    
    def show_adjusted_trial_balance(self):
        shamsi_date = self.adj_trial_date.get_shamsi()
        gregorian_date = self._shamsi_to_gregorian(shamsi_date)
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT a.code, a.name, a.type,
                       COALESCE(SUM(vi.debit), 0) as debit,
                       COALESCE(SUM(vi.credit), 0) as credit
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE v.date <= ? OR v.date IS NULL
                GROUP BY a.code, a.name, a.type
                ORDER BY a.code
            ''', [gregorian_date])
            data = c.fetchall()
        
        self._display_trial_balance(
            self.adj_trial_table, self.adj_trial_total_label, data, shamsi_date
        )
    
    # ============================================================
    # صورت سود و زیان
    # ============================================================
    
    def create_profit_loss_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("از تاریخ:"))
        self.pl_from_date = ShamsiDateEdit()
        control_layout.addWidget(self.pl_from_date)
        
        control_layout.addWidget(QLabel("تا تاریخ:"))
        self.pl_to_date = ShamsiDateEdit()
        control_layout.addWidget(self.pl_to_date)
        
        control_layout.addWidget(self._make_show_button(self.show_profit_loss))
        control_layout.addWidget(self._make_export_button(
            self.export_profit_loss_to_excel
        ))
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.profit_loss_text = QTextEdit()
        self.profit_loss_text.setReadOnly(True)
        layout.addWidget(self.profit_loss_text)
        
        return widget
    
    def show_profit_loss(self):
        from_date_shamsi = self.pl_from_date.get_shamsi()
        to_date_shamsi = self.pl_to_date.get_shamsi()
        from_date = self._shamsi_to_gregorian(from_date_shamsi)
        to_date = self._shamsi_to_gregorian(to_date_shamsi)
        
        c = self.get_theme_colors()
        
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.credit - vi.debit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'income' 
                AND (v.date BETWEEN ? AND ? OR v.date IS NULL)
                GROUP BY a.name
                ORDER BY a.name
            ''', [from_date, to_date])
            incomes = cur.fetchall()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.debit - vi.credit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'expense' 
                AND (v.date BETWEEN ? AND ? OR v.date IS NULL)
                GROUP BY a.name
                ORDER BY a.name
            ''', [from_date, to_date])
            expenses = cur.fetchall()
        
        total_income = sum(inc['balance'] or 0 for inc in incomes)
        total_expense = sum(exp['balance'] or 0 for exp in expenses)
        net_profit = total_income - total_expense
        
        html = f"<div style='font-family: Tahoma; color: {c['text']};'>"
        html += f"<h2 style='text-align: center; color: {c['selected']};'>📊 صورت سود و زیان</h2>"
        html += f"<p style='text-align: center; color: {c['text_secondary']};'>از {from_date_shamsi} تا {to_date_shamsi}</p><hr>"
        
        html += f"<h3 style='color: {c['success']};'>💰 درآمدها:</h3>"
        html += f"<table width='100%' border='1' style='border-collapse: collapse; border-color: {c['border']};'>"
        for inc in incomes:
            if inc['balance'] != 0:
                html += f"<tr><td style='padding:5px;'>{inc['name']}</td><td style='text-align: left;'>{inc['balance']:,.0f} ریال</td></tr>"
        html += f"<tr style='font-weight: bold; background: {c['card']};'><td style='padding:5px;'>جمع درآمدها</td><td style='text-align: left;'>{total_income:,.0f} ریال</td></tr>"
        html += "</table>"
        
        html += f"<h3 style='margin-top: 20px; color: {c['danger']};'>💸 هزینه‌ها:</h3>"
        html += f"<table width='100%' border='1' style='border-collapse: collapse; border-color: {c['border']};'>"
        for exp in expenses:
            if exp['balance'] != 0:
                html += f"<tr><td style='padding:5px;'>{exp['name']}</td><td style='text-align: left;'>{exp['balance']:,.0f} ریال</td></tr>"
        html += f"<tr style='font-weight: bold; background: {c['card']};'><td style='padding:5px;'>جمع هزینه‌ها</td><td style='text-align: left;'>{total_expense:,.0f} ریال</td></tr>"
        html += "</table><hr>"
        
        if net_profit >= 0:
            html += f"<h2 style='color: {c['success']}; text-align: center;'>✅ سود خالص: {net_profit:,.0f} ریال</h2>"
            html += f"<p style='text-align: center;'>📈 حاشیه سود: {(net_profit/total_income*100) if total_income > 0 else 0:.1f}%</p>"
        else:
            html += f"<h2 style='color: {c['danger']}; text-align: center;'>❌ زیان خالص: {abs(net_profit):,.0f} ریال</h2>"
        
        html += "</div>"
        self.profit_loss_text.setHtml(html)
    
    # ============================================================
    # صورت سرمایه
    # ============================================================
    
    def create_capital_statement_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("تاریخ:"))
        self.capital_date = ShamsiDateEdit()
        control_layout.addWidget(self.capital_date)
        
        control_layout.addWidget(self._make_show_button(self.show_capital_statement))
        control_layout.addWidget(self._make_export_button(self.export_capital_to_excel))
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.capital_text = QTextEdit()
        self.capital_text.setReadOnly(True)
        layout.addWidget(self.capital_text)
        
        return widget
    
    def show_capital_statement(self):
        shamsi_date = self.capital_date.get_shamsi()
        gregorian_date = self._shamsi_to_gregorian(shamsi_date)
        c = self.get_theme_colors()
        
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.credit - vi.debit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.code = '3101' AND (v.date <= ? OR v.date IS NULL)
            ''', [gregorian_date])
            initial_capital = cur.fetchone()[0] or 0
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.credit - vi.debit), 0) as income
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'income' AND (v.date <= ? OR v.date IS NULL)
            ''', [gregorian_date])
            total_income = cur.fetchone()[0] or 0
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.debit - vi.credit), 0) as expense
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'expense' AND (v.date <= ? OR v.date IS NULL)
            ''', [gregorian_date])
            total_expense = cur.fetchone()[0] or 0
            
            net_profit = total_income - total_expense
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.debit - vi.credit), 0) as withdrawal
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.code = '3102' AND (v.date <= ? OR v.date IS NULL)
            ''', [gregorian_date])
            withdrawal = cur.fetchone()[0] or 0
        
        ending_capital = initial_capital + net_profit - withdrawal
        
        html = f"<div style='font-family: Tahoma; color: {c['text']};'>"
        html += f"<h2 style='text-align: center; color: {c['selected']};'>📊 صورت تغییرات سرمایه</h2>"
        html += f"<p style='text-align: center; color: {c['text_secondary']};'>تاریخ: {shamsi_date}</p><hr>"
        html += f"<p><b>🏦 سرمایه اولیه:</b> {initial_capital:,.0f} ریال</p>"
        html += f"<p><b>➕ اضافه شدن سود خالص دوره:</b> {net_profit:,.0f} ریال</p>"
        
        if withdrawal > 0:
            html += f"<p><b>➖ کسر برداشت‌های انجام شده:</b> {withdrawal:,.0f} ریال</p>"
        
        html += "<hr>"
        html += f"<h3 style='color: {c['success']};'>💰 سرمایه پایان دوره: {ending_capital:,.0f} ریال</h3>"
        html += "</div>"
        
        self.capital_text.setHtml(html)
    
    # ============================================================
    # ترازنامه
    # ============================================================
    
    def create_balance_sheet_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("تاریخ:"))
        self.bs_date = ShamsiDateEdit()
        control_layout.addWidget(self.bs_date)
        
        control_layout.addWidget(self._make_show_button(self.show_balance_sheet))
        control_layout.addWidget(self._make_export_button(
            self.export_balance_sheet_to_excel
        ))
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.bs_text = QTextEdit()
        self.bs_text.setReadOnly(True)
        layout.addWidget(self.bs_text)
        
        return widget
    
    def show_balance_sheet(self):
        shamsi_date = self.bs_date.get_shamsi()
        gregorian_date = self._shamsi_to_gregorian(shamsi_date)
        c = self.get_theme_colors()
        
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.debit - vi.credit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'asset' AND (v.date <= ? OR v.date IS NULL)
                GROUP BY a.name ORDER BY a.name
            ''', [gregorian_date])
            assets = cur.fetchall()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.credit - vi.debit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'liability' AND (v.date <= ? OR v.date IS NULL)
                GROUP BY a.name ORDER BY a.name
            ''', [gregorian_date])
            liabilities = cur.fetchall()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.credit - vi.debit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'equity' AND (v.date <= ? OR v.date IS NULL)
                GROUP BY a.name ORDER BY a.name
            ''', [gregorian_date])
            equity = cur.fetchall()
        
        total_assets = sum(a['balance'] or 0 for a in assets)
        total_liabilities = sum(l['balance'] or 0 for l in liabilities)
        total_equity = sum(e['balance'] or 0 for e in equity)
        
        html = f"<div style='font-family: Tahoma; color: {c['text']};'>"
        html += f"<h2 style='text-align: center; color: {c['selected']};'>📊 ترازنامه</h2>"
        html += f"<p style='text-align: center; color: {c['text_secondary']};'>تاریخ: {shamsi_date}</p><hr>"
        
        html += f"<h3 style='color: {c['selected']};'>🏢 دارایی‌ها:</h3>"
        html += f"<table width='100%' border='1' style='border-collapse: collapse; border-color: {c['border']};'>"
        for asset in assets:
            if asset['balance'] != 0:
                html += f"<tr><td style='padding:5px;'>{asset['name']}</td><td style='text-align: left;'>{asset['balance']:,.0f} ریال</td></tr>"
        html += f"<tr style='font-weight: bold; background: {c['card']};'><td style='padding:5px;'>جمع دارایی‌ها</td><td style='text-align: left;'>{total_assets:,.0f} ریال</td></tr>"
        html += "</table>"
        
        html += f"<h3 style='color: {c['warning']}; margin-top: 20px;'>📋 بدهی‌ها:</h3>"
        html += f"<table width='100%' border='1' style='border-collapse: collapse; border-color: {c['border']};'>"
        for liab in liabilities:
            if liab['balance'] != 0:
                html += f"<tr><td style='padding:5px;'>{liab['name']}</td><td style='text-align: left;'>{liab['balance']:,.0f} ریال</td></tr>"
        html += f"<tr style='font-weight: bold; background: {c['card']};'><td style='padding:5px;'>جمع بدهی‌ها</td><td style='text-align: left;'>{total_liabilities:,.0f} ریال</td></tr>"
        html += "</table>"
        
        html += f"<h3 style='color: {c['success']}; margin-top: 20px;'>💰 سرمایه:</h3>"
        html += f"<table width='100%' border='1' style='border-collapse: collapse; border-color: {c['border']};'>"
        for eq in equity:
            if eq['balance'] != 0:
                html += f"<tr><td style='padding:5px;'>{eq['name']}</td><td style='text-align: left;'>{eq['balance']:,.0f} ریال</td></tr>"
        html += f"<tr style='font-weight: bold; background: {c['card']};'><td style='padding:5px;'>جمع سرمایه</td><td style='text-align: left;'>{total_equity:,.0f} ریال</td></tr>"
        html += "</table><hr>"
        
        html += f"<h3 style='text-align: center;'>📊 جمع بدهی‌ها و سرمایه: {total_liabilities + total_equity:,.0f} ریال</h3>"
        
        if abs(total_assets - (total_liabilities + total_equity)) < 1:
            html += f"<h3 style='text-align: center; color: {c['success']};'>✅ ترازنامه موازنه است</h3>"
        else:
            diff = total_assets - (total_liabilities + total_equity)
            html += f"<h3 style='text-align: center; color: {c['danger']};'>⚠️ عدم موازنه: {diff:,.0f} ریال</h3>"
        
        html += "</div>"
        self.bs_text.setHtml(html)
    
    # ============================================================
    # بستن حساب‌ها
    # ============================================================
    
    def create_closing_entries_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("🔒 بستن حساب‌های موقت (درآمد، هزینه، برداشت)")
        info.setObjectName("titleLabel")
        layout.addWidget(info)
        
        desc = QLabel("این عملیات حساب‌های درآمد، هزینه و برداشت را صفر کرده و مانده آنها را به حساب خلاصه سود و زیان منتقل می‌کند.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        self.closing_info = QTextEdit()
        self.closing_info.setReadOnly(True)
        self.closing_info.setMaximumHeight(150)
        layout.addWidget(self.closing_info)
        
        btn_layout = QHBoxLayout()
        
        preview_btn = QPushButton("👁️ پیش‌نمایش بستن حساب‌ها")
        preview_btn.setObjectName("infoBtn")
        preview_btn.clicked.connect(self.preview_closing_entries)
        btn_layout.addWidget(preview_btn)
        
        close_btn = QPushButton("🔒 اجرای بستن حساب‌ها")
        close_btn.setObjectName("warningBtn")
        close_btn.clicked.connect(self.execute_closing_entries)
        btn_layout.addWidget(close_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.closing_result = QTextEdit()
        self.closing_result.setReadOnly(True)
        layout.addWidget(self.closing_result)
        
        return widget
    
    def preview_closing_entries(self):
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT a.code, a.name, COALESCE(SUM(vi.credit - vi.debit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                WHERE a.type = 'income'
                GROUP BY a.code, a.name
                HAVING balance != 0
            ''')
            incomes = cur.fetchall()
            
            cur.execute('''
                SELECT a.code, a.name, COALESCE(SUM(vi.debit - vi.credit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                WHERE a.type = 'expense'
                GROUP BY a.code, a.name
                HAVING balance != 0
            ''')
            expenses = cur.fetchall()
            
            total_income = sum(i['balance'] or 0 for i in incomes)
            total_expense = sum(e['balance'] or 0 for e in expenses)
            net_profit = total_income - total_expense
        
        info = "📋 **پیش‌نمایش بستن حساب‌ها**\n\n"
        info += "=" * 50 + "\n\n"
        
        if incomes:
            info += "**درآمدها (بستن):**\n"
            for inc in incomes:
                info += f"  - {inc['name']}: {inc['balance']:,.0f} ریال (بدهکار)\n"
            info += "\n"
        
        if expenses:
            info += "**هزینه‌ها (بستن):**\n"
            for exp in expenses:
                info += f"  - {exp['name']}: {exp['balance']:,.0f} ریال (بستانکار)\n"
            info += "\n"
        
        info += "=" * 50 + "\n"
        info += f"**جمع درآمدها:** {total_income:,.0f} ریال\n"
        info += f"**جمع هزینه‌ها:** {total_expense:,.0f} ریال\n"
        info += f"**سود/زیان خالص:** {net_profit:,.0f} ریال\n"
        info += "=" * 50 + "\n\n"
        info += "⚠️ **توجه:** پس از اجرای بستن حساب‌ها، مانده حساب‌های موقت صفر می‌شوند و قابل بازگشت نیستند."
        
        self.closing_info.setText(info)
    
    def execute_closing_entries(self):
        reply = QMessageBox.question(
            self, "تأیید بستن حساب‌ها",
            "آیا از بستن حساب‌های موقت اطمینان دارید؟\nاین عملیات قابل بازگشت نیست!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT a.code, a.name, COALESCE(SUM(vi.credit - vi.debit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                WHERE a.type = 'income'
                GROUP BY a.code, a.name
                HAVING balance != 0
            ''')
            incomes = cur.fetchall()
            
            cur.execute('''
                SELECT a.code, a.name, COALESCE(SUM(vi.debit - vi.credit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                WHERE a.type = 'expense'
                GROUP BY a.code, a.name
                HAVING balance != 0
            ''')
            expenses = cur.fetchall()
            
            total_income = sum(i['balance'] or 0 for i in incomes)
            total_expense = sum(e['balance'] or 0 for e in expenses)
            net_profit = total_income - total_expense
            
            cur.execute("SELECT MAX(voucher_no) FROM vouchers")
            max_no = cur.fetchone()[0] or 0
            voucher_no = max_no + 1
            
            today_gregorian = datetime.now().strftime("%Y-%m-%d")
            
            cur.execute('''
                INSERT INTO vouchers (voucher_no, date, description, type)
                VALUES (?, ?, 'بستن حساب‌های موقت', 'اختتامیه')
            ''', [voucher_no, today_gregorian])
            voucher_id = cur.lastrowid
            
            for inc in incomes:
                if inc['balance'] != 0:
                    cur.execute('''
                        INSERT INTO voucher_items 
                        (voucher_id, account_code, description, debit, credit)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [voucher_id, inc['code'],
                          f"بستن حساب {inc['name']}", inc['balance'], 0])
            
            for exp in expenses:
                if exp['balance'] != 0:
                    cur.execute('''
                        INSERT INTO voucher_items 
                        (voucher_id, account_code, description, debit, credit)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [voucher_id, exp['code'],
                          f"بستن حساب {exp['name']}", 0, exp['balance']])
            
            if net_profit > 0:
                cur.execute('''
                    INSERT INTO voucher_items 
                    (voucher_id, account_code, description, debit, credit)
                    VALUES (?, '3101', 'انتقال سود خالص به سرمایه', 0, ?)
                ''', [voucher_id, net_profit])
            elif net_profit < 0:
                cur.execute('''
                    INSERT INTO voucher_items 
                    (voucher_id, account_code, description, debit, credit)
                    VALUES (?, '3101', 'انتقال زیان خالص به سرمایه', ?, 0)
                ''', [voucher_id, abs(net_profit)])
            
            conn.commit()
        
        display_today = safe_display_date(today_gregorian)
        self.closing_result.setText(f"""
✅ **حساب‌ها با موفقیت بسته شدند!**

📋 سند شماره: {voucher_no}
📅 تاریخ: {display_today}
💰 سود خالص منتقل شده به سرمایه: {net_profit:,.0f} ریال

⚠️ اکنون می‌توانید برای دوره جدید تراز افتتاحیه را مشاهده کنید.
        """)
        
        QMessageBox.information(
            self, "موفق",
            f"✅ بستن حساب‌ها با موفقیت انجام شد!\nسند شماره: {voucher_no}"
        )
    
    # ============================================================
    # تراز افتتاحیه
    # ============================================================
    
    def create_opening_trial_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("📋 تراز افتتاحیه دوره جدید")
        info.setObjectName("titleLabel")
        layout.addWidget(info)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("تاریخ شروع دوره جدید:"))
        self.opening_date = ShamsiDateEdit()
        control_layout.addWidget(self.opening_date)
        
        control_layout.addWidget(
            self._make_show_button(self.show_opening_trial_balance)
        )
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.opening_table = QTableWidget()
        self.opening_table.setColumnCount(4)
        self.opening_table.setHorizontalHeaderLabels(
            ["کد حساب", "نام حساب", "مانده بدهکار", "مانده بستانکار"]
        )
        self.opening_table.horizontalHeader().setStretchLastSection(True)
        self.opening_table.setAlternatingRowColors(True)
        layout.addWidget(self.opening_table)
        
        self.opening_total_label = QLabel()
        layout.addWidget(self.opening_total_label)
        
        return widget
    
    def show_opening_trial_balance(self):
        display_date = self.opening_date.get_shamsi()
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT a.code, a.name,
                       COALESCE(SUM(CASE WHEN a.type IN ('asset', 'expense') 
                                       THEN vi.debit - vi.credit ELSE 0 END), 0) as debit,
                       COALESCE(SUM(CASE WHEN a.type IN ('liability', 'equity', 'income') 
                                       THEN vi.credit - vi.debit ELSE 0 END), 0) as credit
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                GROUP BY a.code, a.name
                HAVING debit != 0 OR credit != 0
                ORDER BY a.code
            ''')
            data = c.fetchall()
        
        self.opening_table.setRowCount(len(data))
        
        total_debit = 0
        total_credit = 0
        
        for i, row in enumerate(data):
            self.opening_table.setItem(i, 0, QTableWidgetItem(row['code']))
            self.opening_table.setItem(i, 1, QTableWidgetItem(row['name']))
            
            debit = row['debit'] or 0
            credit = row['credit'] or 0
            
            debit_item = QTableWidgetItem(f"{debit:,.0f}" if debit > 0 else "-")
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.opening_table.setItem(i, 2, debit_item)
            
            credit_item = QTableWidgetItem(f"{credit:,.0f}" if credit > 0 else "-")
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.opening_table.setItem(i, 3, credit_item)
            
            total_debit += debit
            total_credit += credit
        
        self.opening_total_label.setText(
            f"📊 تراز افتتاحیه - {display_date}\n"
            f"جمع بدهکار: {total_debit:,.0f} ریال | جمع بستانکار: {total_credit:,.0f} ریال"
        )
    
    # ============================================================
    # جریان نقدی
    # ============================================================
    
    def create_cash_flow_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("از تاریخ:"))
        self.cf_from_date = ShamsiDateEdit()
        control_layout.addWidget(self.cf_from_date)
        
        control_layout.addWidget(QLabel("تا تاریخ:"))
        self.cf_to_date = ShamsiDateEdit()
        control_layout.addWidget(self.cf_to_date)
        
        control_layout.addWidget(self._make_show_button(self.show_cash_flow))
        control_layout.addWidget(self._make_export_button(self.export_cash_flow))
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.cash_flow_text = QTextEdit()
        self.cash_flow_text.setReadOnly(True)
        layout.addWidget(self.cash_flow_text)
        
        return widget
    
    def show_cash_flow(self):
        from_date = self._shamsi_to_gregorian(self.cf_from_date.get_shamsi())
        to_date = self._shamsi_to_gregorian(self.cf_to_date.get_shamsi())
        display_from = self.cf_from_date.get_shamsi()
        display_to = self.cf_to_date.get_shamsi()
        c = self.get_theme_colors()
        
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT 
                    COALESCE(SUM(CASE WHEN a.code IN ('1101', '1102') 
                                     THEN vi.debit - vi.credit ELSE 0 END), 0) as cash_in,
                    COALESCE(SUM(CASE WHEN a.code IN ('1101', '1102') 
                                     THEN vi.credit - vi.debit ELSE 0 END), 0) as cash_out
                FROM voucher_items vi
                JOIN vouchers v ON vi.voucher_id = v.id
                JOIN accounts a ON vi.account_code = a.code
                WHERE v.date BETWEEN ? AND ?
            ''', [from_date, to_date])
            row = cur.fetchone()
            cash_in = row['cash_in'] or 0
            cash_out = row['cash_out'] or 0
            net_cash = cash_in - cash_out
        
        html = f"<div style='font-family: Tahoma; color: {c['text']};'>"
        html += f"<h2 style='text-align: center; color: {c['selected']};'>💰 صورت جریان نقدی</h2>"
        html += f"<p style='text-align: center; color: {c['text_secondary']};'>از {display_from} تا {display_to}</p><hr>"
        
        html += f"<h3 style='color: {c['success']};'>📥 جریان ورودی نقد:</h3>"
        html += f"<p>• جمع دریافت‌ها: {cash_in:,.0f} ریال</p>"
        
        html += f"<h3 style='color: {c['danger']};'>📤 جریان خروجی نقد:</h3>"
        html += f"<p>• جمع پرداخت‌ها: {cash_out:,.0f} ریال</p>"
        
        html += "<hr>"
        if net_cash >= 0:
            html += f"<h2 style='color: {c['success']};'>✅ جریان نقدی خالص: {net_cash:,.0f} ریال</h2>"
        else:
            html += f"<h2 style='color: {c['danger']};'>❌ جریان نقدی خالص: {net_cash:,.0f} ریال</h2>"
        
        html += "</div>"
        self.cash_flow_text.setHtml(html)
    
    def export_cash_flow(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره گزارش جریان نقدی",
            "جریان_نقدی.csv", "CSV Files (*.csv)"
        )
        if file_name:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["جریان ورودی", "جریان خروجی", "جریان خالص"])
                writer.writerow([self.cash_flow_text.toPlainText()])
            QMessageBox.information(self, "موفق", "✅ گزارش ذخیره شد!")
    
    # ============================================================
    # نسبت‌های مالی
    # ============================================================
    
    def create_ratios_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("تاریخ:"))
        self.ratios_date = ShamsiDateEdit()
        control_layout.addWidget(self.ratios_date)
        
        control_layout.addWidget(self._make_show_button(self.show_ratios))
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.ratios_text = QTextEdit()
        self.ratios_text.setReadOnly(True)
        layout.addWidget(self.ratios_text)
        
        return widget
    
    def show_ratios(self):
        display_date = self.ratios_date.get_shamsi()
        c = self.get_theme_colors()
        
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.debit - vi.credit), 0)
                FROM voucher_items vi
                JOIN accounts a ON vi.account_code = a.code
                WHERE a.type = 'asset' AND a.code LIKE '1%'
            ''')
            current_assets = cur.fetchone()[0] or 0
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.credit - vi.debit), 0)
                FROM voucher_items vi
                JOIN accounts a ON vi.account_code = a.code
                WHERE a.type = 'liability' AND a.code LIKE '2%'
            ''')
            current_liabilities = cur.fetchone()[0] or 0
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.debit - vi.credit), 0)
                FROM voucher_items vi
                JOIN accounts a ON vi.account_code = a.code
                WHERE a.type = 'asset'
            ''')
            total_assets = cur.fetchone()[0] or 0
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.credit - vi.debit), 0)
                FROM voucher_items vi
                JOIN accounts a ON vi.account_code = a.code
                WHERE a.type = 'liability'
            ''')
            total_liabilities = cur.fetchone()[0] or 0
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.credit - vi.debit), 0)
                FROM voucher_items vi
                JOIN accounts a ON vi.account_code = a.code
                WHERE a.type = 'income'
            ''')
            income = cur.fetchone()[0] or 0
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.debit - vi.credit), 0)
                FROM voucher_items vi
                JOIN accounts a ON vi.account_code = a.code
                WHERE a.type = 'expense'
            ''')
            expense = cur.fetchone()[0] or 0
            
            net_profit = income - expense
        
        current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0
        debt_ratio = total_liabilities / total_assets if total_assets > 0 else 0
        profit_margin = net_profit / income if income > 0 else 0
        
        html = f"<div style='font-family: Tahoma; color: {c['text']};'>"
        html += f"<h2 style='text-align: center; color: {c['selected']};'>📊 نسبت‌های مالی</h2>"
        html += f"<p style='text-align: center; color: {c['text_secondary']};'>تاریخ: {display_date}</p><hr>"
        
        html += f"<h3>💰 نسبت‌های نقدینگی:</h3>"
        html += f"<p><b>نسبت جاری:</b> {current_ratio:.2f} (دارایی جاری / بدهی جاری)</p>"
        
        html += f"<h3>📊 نسبت‌های اهرمی:</h3>"
        html += f"<p><b>نسبت بدهی به دارایی:</b> {debt_ratio:.2%} (بدهی کل / دارایی کل)</p>"
        
        html += f"<h3>📈 نسبت‌های سودآوری:</h3>"
        html += f"<p><b>حاشیه سود خالص:</b> {profit_margin:.2%} (سود خالص / درآمد)</p>"
        
        if current_ratio >= 2:
            html += f"<p style='color: {c['success']};'>✅ نسبت جاری مناسب است (≥ 2)</p>"
        else:
            html += f"<p style='color: {c['danger']};'>⚠️ نسبت جاری پایین است (کمتر از 2)</p>"
        
        if debt_ratio <= 0.5:
            html += f"<p style='color: {c['success']};'>✅ نسبت بدهی مناسب است (≤ 50%)</p>"
        else:
            html += f"<p style='color: {c['danger']};'>⚠️ نسبت بدهی بالا است (بیش از 50%)</p>"
        
        html += "</div>"
        self.ratios_text.setHtml(html)
    
    # ============================================================
    # گزارش مشتریان
    # ============================================================
    
    def create_customers_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("نوع گزارش:"))
        self.customer_report_type = QComboBox()
        self.customer_report_type.addItems(
            ["📋 لیست مشتریان", "💰 مشتریان برتر", "📊 مانده حساب‌ها"]
        )
        control_layout.addWidget(self.customer_report_type)
        
        control_layout.addWidget(
            self._make_show_button(self.show_customers_report)
        )
        control_layout.addWidget(self._make_export_button(
            lambda: self.export_table_to_excel(self.customers_table, "گزارش_مشتریان")
        ))
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.customers_table = QTableWidget()
        self.customers_table.setAlternatingRowColors(True)
        layout.addWidget(self.customers_table)
        
        self.customers_total_label = QLabel()
        layout.addWidget(self.customers_total_label)
        
        return widget
    
    def show_customers_report(self):
        report_type = self.customer_report_type.currentIndex()
        c = self.get_theme_colors()
        
        with get_db() as conn:
            cur = conn.cursor()
            
            if report_type == 0:
                cur.execute('''
                    SELECT code, name, phone, email, address, 
                           COALESCE(balance, 0) as balance
                    FROM parties WHERE type = 'customer' ORDER BY name
                ''')
                data = cur.fetchall()
                self.customers_table.setColumnCount(6)
                self.customers_table.setHorizontalHeaderLabels(
                    ["کد", "نام", "تلفن", "ایمیل", "آدرس", "مانده حساب"]
                )
                
                self.customers_table.setRowCount(len(data))
                total_balance = 0
                for i, row in enumerate(data):
                    self.customers_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.customers_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.customers_table.setItem(i, 2, QTableWidgetItem(row['phone'] or '-'))
                    self.customers_table.setItem(i, 3, QTableWidgetItem(row['email'] or '-'))
                    self.customers_table.setItem(i, 4, QTableWidgetItem(row['address'] or '-'))
                    
                    balance_item = QTableWidgetItem(f"{row['balance']:,.0f}")
                    balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if row['balance'] > 0:
                        balance_item.setForeground(QColor(c['success']))
                    elif row['balance'] < 0:
                        balance_item.setForeground(QColor(c['danger']))
                    self.customers_table.setItem(i, 5, balance_item)
                    total_balance += row['balance'] or 0
                
                self.customers_total_label.setText(
                    f"👥 {len(data)} مشتری | مجموع مانده: {total_balance:,.0f} ریال"
                )
            
            elif report_type == 1:
                cur.execute('''
                    SELECT p.code, p.name, COUNT(d.id) as invoice_count, 
                           COALESCE(SUM(d.net_amount), 0) as total_purchase
                    FROM parties p
                    LEFT JOIN documents d ON p.id = d.party_id AND d.doc_type = 'sales'
                    WHERE p.type = 'customer'
                    GROUP BY p.id, p.code, p.name
                    ORDER BY total_purchase DESC
                    LIMIT 20
                ''')
                data = cur.fetchall()
                self.customers_table.setColumnCount(4)
                self.customers_table.setHorizontalHeaderLabels(
                    ["کد", "نام", "تعداد فاکتور", "مجموع خرید"]
                )
                
                self.customers_table.setRowCount(len(data))
                for i, row in enumerate(data):
                    self.customers_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.customers_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.customers_table.setItem(i, 2, QTableWidgetItem(str(row['invoice_count'])))
                    purchase_item = QTableWidgetItem(f"{row['total_purchase']:,.0f}")
                    purchase_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    purchase_item.setForeground(QColor(c['success']))
                    self.customers_table.setItem(i, 3, purchase_item)
                
                self.customers_total_label.setText(f"🏆 {len(data)} مشتری برتر")
            
            else:
                cur.execute('''
                    SELECT code, name, COALESCE(balance, 0) as balance
                    FROM parties WHERE type = 'customer' 
                    ORDER BY balance DESC
                ''')
                data = cur.fetchall()
                self.customers_table.setColumnCount(3)
                self.customers_table.setHorizontalHeaderLabels(
                    ["کد", "نام", "مانده حساب"]
                )
                
                self.customers_table.setRowCount(len(data))
                positive = 0
                negative = 0
                for i, row in enumerate(data):
                    self.customers_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.customers_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    
                    balance_item = QTableWidgetItem(f"{row['balance']:,.0f}")
                    balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if row['balance'] > 0:
                        balance_item.setForeground(QColor(c['success']))
                        positive += row['balance']
                    elif row['balance'] < 0:
                        balance_item.setForeground(QColor(c['danger']))
                        negative += abs(row['balance'])
                    self.customers_table.setItem(i, 2, balance_item)
                
                self.customers_total_label.setText(
                    f"💰 مانده مثبت: {positive:,.0f} | "
                    f"مانده منفی: {negative:,.0f} | "
                    f"خالص: {positive - negative:,.0f} ریال"
                )
    
    # ============================================================
    # گزارش انبار
    # ============================================================
    
    def create_inventory_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("نوع گزارش:"))
        self.inv_report_type = QComboBox()
        self.inv_report_type.addItems([
            "📋 لیست موجودی کالاها", "📊 ارزش موجودی انبار",
            "⚠️ کالاهای زیر حداقل", "📈 پرگردش‌ترین کالاها"
        ])
        control_layout.addWidget(self.inv_report_type)
        
        control_layout.addWidget(
            self._make_show_button(self.show_inventory_report)
        )
        control_layout.addWidget(self._make_export_button(
            lambda: self.export_table_to_excel(self.inv_table, "گزارش_انبار")
        ))
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.inv_table = QTableWidget()
        self.inv_table.setAlternatingRowColors(True)
        layout.addWidget(self.inv_table)
        
        self.inv_total_label = QLabel()
        layout.addWidget(self.inv_total_label)
        
        return widget
    
    def show_inventory_report(self):
        report_type = self.inv_report_type.currentIndex()
        c = self.get_theme_colors()
        
        with get_db() as conn:
            cur = conn.cursor()
            
            if report_type == 0:
                cur.execute(
                    "SELECT code, name, unit, stock, purchase_price, sale_price "
                    "FROM products ORDER BY code"
                )
                data = cur.fetchall()
                self.inv_table.setColumnCount(6)
                self.inv_table.setHorizontalHeaderLabels(
                    ["کد", "نام کالا", "واحد", "موجودی", "قیمت خرید", "قیمت فروش"]
                )
                
                self.inv_table.setRowCount(len(data))
                for i, row in enumerate(data):
                    self.inv_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.inv_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.inv_table.setItem(i, 2, QTableWidgetItem(row['unit'] or 'عدد'))
                    
                    stock_item = QTableWidgetItem(f"{row['stock']:,.2f}")
                    stock_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.inv_table.setItem(i, 3, stock_item)
                    
                    purchase_item = QTableWidgetItem(f"{row['purchase_price']:,.0f}")
                    purchase_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.inv_table.setItem(i, 4, purchase_item)
                    
                    sale_item = QTableWidgetItem(f"{row['sale_price']:,.0f}")
                    sale_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.inv_table.setItem(i, 5, sale_item)
                
                self.inv_total_label.setText(f"📊 {len(data)} کالا در انبار")
            
            elif report_type == 1:
                cur.execute(
                    "SELECT code, name, unit, stock, purchase_price, "
                    "(stock * purchase_price) as total_value "
                    "FROM products WHERE stock > 0 ORDER BY total_value DESC"
                )
                data = cur.fetchall()
                self.inv_table.setColumnCount(6)
                self.inv_table.setHorizontalHeaderLabels(
                    ["کد", "نام کالا", "واحد", "موجودی", "قیمت خرید", "ارزش کل"]
                )
                
                total_value = 0
                self.inv_table.setRowCount(len(data))
                for i, row in enumerate(data):
                    self.inv_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.inv_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.inv_table.setItem(i, 2, QTableWidgetItem(row['unit'] or 'عدد'))
                    
                    stock_item = QTableWidgetItem(f"{row['stock']:,.2f}")
                    stock_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.inv_table.setItem(i, 3, stock_item)
                    
                    price_item = QTableWidgetItem(f"{row['purchase_price']:,.0f}")
                    price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.inv_table.setItem(i, 4, price_item)
                    
                    value_item = QTableWidgetItem(f"{row['total_value']:,.0f}")
                    value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    value_item.setForeground(QColor(c['success']))
                    self.inv_table.setItem(i, 5, value_item)
                    
                    total_value += row['total_value'] or 0
                
                self.inv_total_label.setText(
                    f"💰 ارزش کل موجودی انبار: {total_value:,.0f} ریال"
                )
            
            elif report_type == 2:
                cur.execute('''
                    SELECT code, name, unit, stock, min_stock,
                           (min_stock - stock) as shortage
                    FROM products 
                    WHERE stock <= min_stock AND min_stock > 0 
                    ORDER BY shortage DESC
                ''')
                data = cur.fetchall()
                self.inv_table.setColumnCount(6)
                self.inv_table.setHorizontalHeaderLabels(
                    ["کد", "نام کالا", "واحد", "موجودی", "حداقل موجودی", "کسری"]
                )
                
                self.inv_table.setRowCount(len(data))
                for i, row in enumerate(data):
                    self.inv_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.inv_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.inv_table.setItem(i, 2, QTableWidgetItem(row['unit'] or 'عدد'))
                    
                    stock_item = QTableWidgetItem(f"{row['stock']:,.2f}")
                    stock_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    stock_item.setForeground(QColor(c['danger']))
                    self.inv_table.setItem(i, 3, stock_item)
                    
                    min_item = QTableWidgetItem(f"{row['min_stock']:,.2f}")
                    min_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.inv_table.setItem(i, 4, min_item)
                    
                    shortage_item = QTableWidgetItem(f"{row['shortage']:,.2f}")
                    shortage_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    shortage_item.setForeground(QColor(c['danger']))
                    self.inv_table.setItem(i, 5, shortage_item)
                
                self.inv_total_label.setText(f"⚠️ {len(data)} کالا زیر حداقل موجودی")
            
            else:
                cur.execute('''
                    SELECT p.code, p.name, p.unit, p.stock, 
                           COUNT(st.id) as trans_count,
                           COALESCE(SUM(CASE WHEN st.type='out' 
                                            THEN st.quantity ELSE 0 END), 0) as total_out
                    FROM products p
                    LEFT JOIN stock_transactions st ON p.id = st.product_id
                    GROUP BY p.id, p.code, p.name, p.unit, p.stock
                    ORDER BY trans_count DESC, total_out DESC
                    LIMIT 20
                ''')
                data = cur.fetchall()
                self.inv_table.setColumnCount(6)
                self.inv_table.setHorizontalHeaderLabels(
                    ["کد", "نام کالا", "واحد", "موجودی", "تعداد تراکنش", "مقدار خروجی"]
                )
                
                self.inv_table.setRowCount(len(data))
                for i, row in enumerate(data):
                    self.inv_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.inv_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.inv_table.setItem(i, 2, QTableWidgetItem(row['unit'] or 'عدد'))
                    
                    stock_item = QTableWidgetItem(f"{row['stock']:,.2f}")
                    stock_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.inv_table.setItem(i, 3, stock_item)
                    
                    trans_item = QTableWidgetItem(f"{row['trans_count']:,.0f}")
                    trans_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.inv_table.setItem(i, 4, trans_item)
                    
                    out_item = QTableWidgetItem(f"{row['total_out']:,.2f}")
                    out_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.inv_table.setItem(i, 5, out_item)
                
                self.inv_total_label.setText(f"📊 {len(data)} کالای پرگردش")
    
    # ============================================================
    # گزارش حقوق
    # ============================================================
    
    def create_payroll_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("سال:"))
        self.payroll_year = QSpinBox()
        self.payroll_year.setRange(1390, 1450)
        self.payroll_year.setValue(datetime.now().year if datetime.now().year > 1400 else 1403)
        control_layout.addWidget(self.payroll_year)
        
        control_layout.addWidget(QLabel("ماه:"))
        self.payroll_month = QComboBox()
        self.payroll_month.addItems([
            "همه", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ])
        control_layout.addWidget(self.payroll_month)
        
        control_layout.addWidget(QLabel("نوع گزارش:"))
        self.payroll_report_type = QComboBox()
        self.payroll_report_type.addItems([
            "📋 لیست حقوق ماهانه", "📊 خلاصه حقوق سالانه",
            "💰 گزارش پرداختی‌ها", "⏳ حقوق‌های پرداخت نشده"
        ])
        control_layout.addWidget(self.payroll_report_type)
        
        control_layout.addWidget(
            self._make_show_button(self.show_payroll_report)
        )
        control_layout.addWidget(self._make_export_button(
            lambda: self.export_table_to_excel(self.payroll_table, "گزارش_حقوق")
        ))
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.payroll_table = QTableWidget()
        self.payroll_table.setAlternatingRowColors(True)
        layout.addWidget(self.payroll_table)
        
        self.payroll_total_label = QLabel()
        layout.addWidget(self.payroll_total_label)
        
        return widget
    
    def show_payroll_report(self):
        year = self.payroll_year.value()
        month_idx = self.payroll_month.currentIndex()
        report_type = self.payroll_report_type.currentIndex()
        c = self.get_theme_colors()
        
        month_names = [
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ]
        
        with get_db() as conn:
            cur = conn.cursor()
            
            if report_type == 0:
                if month_idx == 0:
                    cur.execute('''
                        SELECT e.code, e.name, p.year, p.month, p.net_salary,
                               p.payment_status, p.payment_date
                        FROM payrolls p
                        JOIN employees e ON p.employee_id = e.id
                        WHERE p.year = ?
                        ORDER BY p.month, e.code
                    ''', [year])
                else:
                    cur.execute('''
                        SELECT e.code, e.name, p.year, p.month, p.net_salary,
                               p.payment_status, p.payment_date
                        FROM payrolls p
                        JOIN employees e ON p.employee_id = e.id
                        WHERE p.year = ? AND p.month = ?
                        ORDER BY e.code
                    ''', [year, month_idx])
                data = cur.fetchall()
                self.payroll_table.setColumnCount(7)
                self.payroll_table.setHorizontalHeaderLabels(
                    ["کد", "نام", "سال", "ماه", "خالص", "وضعیت", "تاریخ پرداخت"]
                )
                
                total_net = 0
                self.payroll_table.setRowCount(len(data))
                for i, row in enumerate(data):
                    self.payroll_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.payroll_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.payroll_table.setItem(i, 2, QTableWidgetItem(str(row['year'])))
                    self.payroll_table.setItem(
                        i, 3,
                        QTableWidgetItem(
                            month_names[row['month']-1] 
                            if 1 <= row['month'] <= 12 else str(row['month'])
                        )
                    )
                    
                    net_item = QTableWidgetItem(f"{row['net_salary']:,.0f}")
                    net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    net_item.setForeground(QColor(c['success']))
                    self.payroll_table.setItem(i, 4, net_item)
                    total_net += row['net_salary'] or 0
                    
                    status_text = {
                        'pending': '⏳ در انتظار',
                        'paid': '✅ پرداخت شده'
                    }.get(row['payment_status'], row['payment_status'])
                    status_item = QTableWidgetItem(status_text)
                    if row['payment_status'] == 'paid':
                        status_item.setForeground(QColor(c['success']))
                    else:
                        status_item.setForeground(QColor(c['warning']))
                    self.payroll_table.setItem(i, 5, status_item)
                    
                    payment_date_str = (
                        safe_display_date(row['payment_date']) 
                        if row['payment_date'] else "-"
                    )
                    self.payroll_table.setItem(i, 6, QTableWidgetItem(payment_date_str))
                
                self.payroll_total_label.setText(
                    f"💰 جمع خالص پرداختی: {total_net:,.0f} ریال"
                )
            
            elif report_type == 1:
                cur.execute('''
                    SELECT e.code, e.name, COUNT(p.id) as months_paid,
                           COALESCE(SUM(p.net_salary), 0) as total_paid,
                           COALESCE(AVG(p.net_salary), 0) as avg_salary
                    FROM employees e
                    LEFT JOIN payrolls p ON e.id = p.employee_id 
                        AND p.year = ? AND p.payment_status = 'paid'
                    WHERE e.is_active = 1
                    GROUP BY e.id, e.code, e.name
                    ORDER BY e.code
                ''', [year])
                data = cur.fetchall()
                self.payroll_table.setColumnCount(5)
                self.payroll_table.setHorizontalHeaderLabels(
                    ["کد", "نام", "ماه‌های پرداخت", "جمع پرداختی", "میانگین ماهانه"]
                )
                
                self.payroll_table.setRowCount(len(data))
                for i, row in enumerate(data):
                    self.payroll_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.payroll_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.payroll_table.setItem(i, 2, QTableWidgetItem(str(row['months_paid'])))
                    
                    total_item = QTableWidgetItem(f"{row['total_paid']:,.0f}")
                    total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    total_item.setForeground(QColor(c['success']))
                    self.payroll_table.setItem(i, 3, total_item)
                    
                    avg_item = QTableWidgetItem(f"{row['avg_salary']:,.0f}")
                    avg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.payroll_table.setItem(i, 4, avg_item)
                
                self.payroll_total_label.setText(f"📊 {len(data)} پرسنل")
            
            elif report_type == 2:
                cur.execute('''
                    SELECT e.code, e.name, p.year, p.month, p.net_salary, p.payment_date
                    FROM payrolls p
                    JOIN employees e ON p.employee_id = e.id
                    WHERE p.payment_status = 'paid'
                    ORDER BY p.payment_date DESC, e.code
                    LIMIT 50
                ''')
                data = cur.fetchall()
                self.payroll_table.setColumnCount(6)
                self.payroll_table.setHorizontalHeaderLabels(
                    ["کد", "نام", "سال", "ماه", "مبلغ", "تاریخ پرداخت"]
                )
                total_paid = 0
                
                self.payroll_table.setRowCount(len(data))
                for i, row in enumerate(data):
                    self.payroll_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.payroll_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.payroll_table.setItem(i, 2, QTableWidgetItem(str(row['year'])))
                    self.payroll_table.setItem(
                        i, 3,
                        QTableWidgetItem(
                            month_names[row['month']-1] 
                            if 1 <= row['month'] <= 12 else str(row['month'])
                        )
                    )
                    
                    net_item = QTableWidgetItem(f"{row['net_salary']:,.0f}")
                    net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    net_item.setForeground(QColor(c['success']))
                    self.payroll_table.setItem(i, 4, net_item)
                    total_paid += row['net_salary'] or 0
                    
                    payment_date_str = (
                        safe_display_date(row['payment_date']) 
                        if row['payment_date'] else "-"
                    )
                    self.payroll_table.setItem(i, 5, QTableWidgetItem(payment_date_str))
                
                self.payroll_total_label.setText(
                    f"💰 جمع پرداختی‌ها: {total_paid:,.0f} ریال"
                )
            
            else:
                cur.execute('''
                    SELECT e.code, e.name, p.year, p.month, p.net_salary
                    FROM payrolls p
                    JOIN employees e ON p.employee_id = e.id
                    WHERE p.payment_status = 'pending'
                    ORDER BY p.year, p.month, e.code
                ''')
                data = cur.fetchall()
                self.payroll_table.setColumnCount(5)
                self.payroll_table.setHorizontalHeaderLabels(
                    ["کد", "نام", "سال", "ماه", "مبلغ قابل پرداخت"]
                )
                total_pending = 0
                
                self.payroll_table.setRowCount(len(data))
                for i, row in enumerate(data):
                    self.payroll_table.setItem(i, 0, QTableWidgetItem(row['code']))
                    self.payroll_table.setItem(i, 1, QTableWidgetItem(row['name']))
                    self.payroll_table.setItem(i, 2, QTableWidgetItem(str(row['year'])))
                    self.payroll_table.setItem(
                        i, 3,
                        QTableWidgetItem(
                            month_names[row['month']-1] 
                            if 1 <= row['month'] <= 12 else str(row['month'])
                        )
                    )
                    
                    net_item = QTableWidgetItem(f"{row['net_salary']:,.0f}")
                    net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    net_item.setForeground(QColor(c['danger']))
                    self.payroll_table.setItem(i, 4, net_item)
                    total_pending += row['net_salary'] or 0
                
                self.payroll_total_label.setText(
                    f"💰 جمع بدهی حقوق: {total_pending:,.0f} ریال"
                )
    
    # ============================================================
    # توابع کمکی
    # ============================================================
    
    def _shamsi_to_gregorian(self, shamsi_date):
        """تبدیل تاریخ شمسی به میلادی"""
        if not shamsi_date or '/' not in shamsi_date:
            return datetime.now().strftime("%Y-%m-%d")
        try:
            from persiantools.jdatetime import JalaliDate
            parts = shamsi_date.split('/')
            if len(parts) == 3:
                jalali = JalaliDate(int(parts[0]), int(parts[1]), int(parts[2]))
                return jalali.to_gregorian().strftime("%Y-%m-%d")
        except:
            pass
        return datetime.now().strftime("%Y-%m-%d")
    
    def export_table_to_excel(self, table, filename):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره گزارش",
            f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        if not file_name:
            return
        
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                
                headers = []
                for col in range(table.columnCount()):
                    header = table.horizontalHeaderItem(col)
                    headers.append(header.text() if header else "")
                writer.writerow(headers)
                
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "موفق", f"✅ گزارش در {file_name} ذخیره شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")
    
    def export_profit_loss_to_excel(self):
        from_date_shamsi = self.pl_from_date.get_shamsi()
        to_date_shamsi = self.pl_to_date.get_shamsi()
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره گزارش",
            f"سود_زیان_{from_date_shamsi}_تا_{to_date_shamsi}.csv",
            "CSV Files (*.csv)"
        )
        if not file_name:
            return
        
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.credit - vi.debit), 0) as balance 
                FROM accounts a 
                LEFT JOIN voucher_items vi ON a.code = vi.account_code 
                WHERE a.type = "income" GROUP BY a.name
            ''')
            incomes = cur.fetchall()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.debit - vi.credit), 0) as balance 
                FROM accounts a 
                LEFT JOIN voucher_items vi ON a.code = vi.account_code 
                WHERE a.type = "expense" GROUP BY a.name
            ''')
            expenses = cur.fetchall()
        
        total_income = sum(i['balance'] or 0 for i in incomes)
        total_expense = sum(e['balance'] or 0 for e in expenses)
        net_profit = total_income - total_expense
        
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["صورت سود و زیان"])
                writer.writerow(["از تاریخ", from_date_shamsi])
                writer.writerow(["تا تاریخ", to_date_shamsi])
                writer.writerow([])
                writer.writerow(["درآمدها", "مبلغ (ریال)"])
                for inc in incomes:
                    writer.writerow([inc['name'], inc['balance']])
                writer.writerow(["جمع درآمدها", total_income])
                writer.writerow([])
                writer.writerow(["هزینه‌ها", "مبلغ (ریال)"])
                for exp in expenses:
                    writer.writerow([exp['name'], exp['balance']])
                writer.writerow(["جمع هزینه‌ها", total_expense])
                writer.writerow([])
                writer.writerow(["سود/زیان خالص", net_profit])
            
            QMessageBox.information(self, "موفق", f"✅ گزارش در {file_name} ذخیره شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")
    
    def export_capital_to_excel(self):
        shamsi_date = self.capital_date.get_shamsi()
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره گزارش",
            f"صورت_سرمایه_{shamsi_date}.csv", "CSV Files (*.csv)"
        )
        if not file_name:
            return
        
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.credit - vi.debit), 0) 
                FROM accounts a 
                LEFT JOIN voucher_items vi ON a.code = vi.account_code 
                WHERE a.code = "3101"
            ''')
            initial_capital = cur.fetchone()[0] or 0
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.credit - vi.debit), 0) 
                FROM accounts a 
                LEFT JOIN voucher_items vi ON a.code = vi.account_code 
                WHERE a.type = "income"
            ''')
            total_income = cur.fetchone()[0] or 0
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.debit - vi.credit), 0) 
                FROM accounts a 
                LEFT JOIN voucher_items vi ON a.code = vi.account_code 
                WHERE a.type = "expense"
            ''')
            total_expense = cur.fetchone()[0] or 0
            
            net_profit = total_income - total_expense
            
            cur.execute('''
                SELECT COALESCE(SUM(vi.debit - vi.credit), 0) 
                FROM accounts a 
                LEFT JOIN voucher_items vi ON a.code = vi.account_code 
                WHERE a.code = "3102"
            ''')
            withdrawal = cur.fetchone()[0] or 0
        
        ending_capital = initial_capital + net_profit - withdrawal
        
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["صورت تغییرات سرمایه"])
                writer.writerow(["تاریخ", shamsi_date])
                writer.writerow([])
                writer.writerow(["شرح", "مبلغ (ریال)"])
                writer.writerow(["سرمایه اولیه", initial_capital])
                writer.writerow(["اضافه شدن سود خالص", net_profit])
                if withdrawal > 0:
                    writer.writerow(["کسر برداشت‌ها", -withdrawal])
                writer.writerow(["سرمایه پایان دوره", ending_capital])
            
            QMessageBox.information(self, "موفق", f"✅ گزارش در {file_name} ذخیره شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")
    
    def export_balance_sheet_to_excel(self):
        shamsi_date = self.bs_date.get_shamsi()
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره گزارش",
            f"ترازنامه_{shamsi_date}.csv", "CSV Files (*.csv)"
        )
        if not file_name:
            return
        
        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.debit - vi.credit), 0) 
                FROM accounts a 
                LEFT JOIN voucher_items vi ON a.code = vi.account_code 
                WHERE a.type = "asset" GROUP BY a.name
            ''')
            assets = cur.fetchall()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.credit - vi.debit), 0) 
                FROM accounts a 
                LEFT JOIN voucher_items vi ON a.code = vi.account_code 
                WHERE a.type = "liability" GROUP BY a.name
            ''')
            liabilities = cur.fetchall()
            
            cur.execute('''
                SELECT a.name, COALESCE(SUM(vi.credit - vi.debit), 0) 
                FROM accounts a 
                LEFT JOIN voucher_items vi ON a.code = vi.account_code 
                WHERE a.type = "equity" GROUP BY a.name
            ''')
            equity = cur.fetchall()
        
        total_assets = sum(a[1] for a in assets)
        total_liabilities = sum(l[1] for l in liabilities)
        total_equity = sum(e[1] for e in equity)
        
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ترازنامه"])
                writer.writerow(["تاریخ", shamsi_date])
                writer.writerow([])
                writer.writerow(["دارایی‌ها", "مبلغ (ریال)"])
                for asset in assets:
                    writer.writerow([asset[0], asset[1]])
                writer.writerow(["جمع دارایی‌ها", total_assets])
                writer.writerow([])
                writer.writerow(["بدهی‌ها", "مبلغ (ریال)"])
                for liab in liabilities:
                    writer.writerow([liab[0], liab[1]])
                writer.writerow(["جمع بدهی‌ها", total_liabilities])
                writer.writerow([])
                writer.writerow(["سرمایه", "مبلغ (ریال)"])
                for eq in equity:
                    writer.writerow([eq[0], eq[1]])
                writer.writerow(["جمع سرمایه", total_equity])
                writer.writerow([])
                writer.writerow(["جمع بدهی‌ها و سرمایه", total_liabilities + total_equity])
                writer.writerow([
                    "موازنه",
                    "بله" if abs(total_assets - (total_liabilities + total_equity)) < 1 else "خیر"
                ])
            
            QMessageBox.information(self, "موفق", f"✅ گزارش در {file_name} ذخیره شد!")
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")
