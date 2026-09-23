# ui/accounting_widget.py
# ============================================================
# ویجت حسابداری — نسخه 3.0 (Theme-Integrated)
# با دفتر روزنامه و دفتر کل + تم یکپارچه
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui.base_widgets import BaseWidget, BaseDialog
from database import get_db, ModuleLimitHelper
from dialog_utils import show_confirm_dialog
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali
from screen_utils import ScreenManager
from ui.account_manager_widget import AccountManagerWidget
import sys
import os
import logging

logger = logging.getLogger(__name__)


class AccountingWidget(BaseWidget):
    """ویجت اصلی حسابداری با دفتر روزنامه و دفتر کل — تم یکپارچه"""
    
    def __init__(self, customer_name: str = "", user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        self.customer_name = customer_name
        self.user_level = user_level
        self.vouchers_data = []
        self.journal_data = []
        self.ledger_data = []
        self.ledger_summary_data = []
        self.accounts = []
        
        self.screen_manager = ScreenManager()
        self.scale = self.screen_manager.scale
        self.is_small_screen = self.screen_manager.is_small_screen()
        
        self._init_ai()
        self.setup_ui()
        self.load_vouchers()
        self.load_accounts()
        self.update_ui_by_permission()
        self._apply_widget_theme()
    
    # ============================================================
    # Theme — کامل و یکپارچه
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
            if hasattr(self, 'tabs'):
                self.tabs.setStyleSheet(f"""
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
            
            # 4. QTableWidgetها — استایل کامل
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
            
            # 5. QTextEditها
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
            
            # 6. QLineEditها
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
            
            # 7. QComboBoxها
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
            
            # 8. QSpinBox و QDoubleSpinBox
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
            
            # 9. QPushButtonها — بر اساس objectName
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
            
            # 10. QLabelها
            for lbl in self.findChildren(QLabel):
                obj_name = lbl.objectName()
                
                if obj_name == 'titleLabel':
                    lbl.setStyleSheet(f"""
                        color: {c['selected']};
                        font-size: 16pt;
                        font-weight: bold;
                        padding: 8px;
                        background: transparent;
                    """)
                elif obj_name == 'subtitleLabel':
                    lbl.setStyleSheet(f"""
                        color: {c['text']};
                        font-size: 12pt;
                        font-weight: bold;
                        padding: 6px;
                        background: transparent;
                    """)
                elif not lbl.styleSheet() or 'background' not in lbl.styleSheet():
                    text = lbl.text() or ""
                    # فقط لیبل‌های معمولی
                    if not any(text.startswith(p) for p in [
                        '🏢', '🖼️', '🌍', '📋', '📊', '💰', '🤖',
                        '💾', '🔧', '📅', '⚙️', '📝', '💡', '✏️',
                        '📈', '🏦', '📉', '🔒', '👥', '📦', '💵',
                        '⚠️', '✅', '❌', '🔍', '📄', '📖', '📚'
                    ]):
                        lbl.setStyleSheet(
                            f"color: {c['text']}; background: transparent; padding: 3px;"
                        )
            
            # 11. لیبل جمع‌بندی
            for attr in ['journal_total_label', 'ledger_total_label', 'total_label']:
                if hasattr(self, attr):
                    getattr(self, attr).setStyleSheet(f"""
                        background: {c['card']};
                        color: {c['text']};
                        padding: 10px;
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        font-weight: bold;
                    """)
            
            # 12. کارت‌های پنل
            for w in self.findChildren(QWidget):
                if w.objectName() == 'cardWidget':
                    w.setStyleSheet(f"""
                        QWidget#cardWidget {{
                            background: {c['card']};
                            border: 1px solid {c['border']};
                            border-radius: 8px;
                        }}
                    """)
            
            # 13. ScrollArea
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
                """)
            
            # 14. ShamsiDateEditها — اگه استایل داخلی دارن، دوباره اعمال نشه
            # (خودشون از theme manager استفاده می‌کنن)
            
            # 15. دکمه‌های دیالوگ (QDialogButtonBox)
            for dbb in self.findChildren(QDialogButtonBox):
                for btn in dbb.buttons():
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {c['bg_alt']};
                            color: {c['text']};
                            border: 1px solid {c['border']};
                            border-radius: 6px;
                            padding: 8px 20px;
                            font-weight: bold;
                            min-height: 32px;
                            min-width: 80px;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                            border: 1px solid {c['selected']};
                        }}
                        QPushButton:pressed {{
                            background: {c['selected']};
                            color: {c['selected_text']};
                        }}
                    """)
        
        except Exception as e:
            print(f"⚠️ خطا در _apply_widget_theme: {e}")
    
    # ============================================================
    # Permission
    # ============================================================
    
    def set_user_level(self, level: str):
        """تنظیم سطح دسترسی"""
        self.user_level = level
        self.update_ui_by_permission()
    
    def update_ui_by_permission(self):
        """بروزرسانی UI بر اساس سطح دسترسی"""
        can_edit = self.user_level in ['admin', 'accountant']
        
        if hasattr(self, 'new_btn'):
            self.new_btn.setVisible(can_edit)
        if hasattr(self, 'edit_btn'):
            self.edit_btn.setVisible(can_edit)
        if hasattr(self, 'delete_btn'):
            self.delete_btn.setVisible(can_edit)
    
    def _init_ai(self):
        self.ai_ready = False
        try:
            import ImanAILite as imanai
            self.ai_ready = True
        except Exception:
            pass
    
    # ============================================================
    # UI Setup
    # ============================================================
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        self.tabs.addTab(self.create_voucher_tab(), "📄 ثبت اسناد")
        self.tabs.addTab(self.create_journal_tab(), "📖 دفتر روزنامه")
        self.tabs.addTab(self.create_ledger_tab(), "📚 دفتر کل")
        
        try:
            self.account_manager = AccountManagerWidget()
            self.tabs.addTab(self.account_manager, "📊 مدیریت حساب‌ها")
        except Exception as e:
            error_label = QLabel(f"❌ خطا: {str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            self.tabs.addTab(error_label, "⚠️ مدیریت حساب‌ها")
        
        layout.addWidget(self.tabs)
    
    # ============================================================
    # تب ثبت اسناد
    # ============================================================
    
    def create_voucher_tab(self):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setSpacing(self.spacing(10))
        main_layout.setContentsMargins(
            self.margin(10), self.margin(10), self.margin(10), self.margin(10)
        )
        
        # پنل راست: اسناد
        right_panel = QWidget()
        right_panel.setObjectName("cardWidget")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(self.spacing(10))
        
        title = QLabel("📄 اسناد حسابداری")
        title.setObjectName("titleLabel")
        right_layout.addWidget(title)
        
        toolbar = self._create_toolbar()
        right_layout.addLayout(toolbar)
        
        self.vouchers_table = self.create_table(
            ["شماره", "تاریخ", "شرح", "نوع", "بدهکار", "بستانکار"],
            stretch_last=True
        )
        self.vouchers_table.clicked.connect(self.on_voucher_selected)
        right_layout.addWidget(self.vouchers_table)
        
        # پنل چپ: جزئیات
        left_panel = QWidget()
        left_panel.setObjectName("cardWidget")
        left_panel.setMaximumWidth(self.scaled(400))
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(self.spacing(10))
        
        detail_title = QLabel("📋 جزئیات سند")
        detail_title.setObjectName("subtitleLabel")
        left_layout.addWidget(detail_title)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("یک سند را انتخاب کنید...")
        left_layout.addWidget(self.details_text)
        
        if self.is_small_screen:
            left_panel.hide()
        
        main_layout.addWidget(right_panel, 2)
        main_layout.addWidget(left_panel, 1)
        
        return widget
    
    def _create_toolbar(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(self.spacing(8))
        
        self.new_btn = self.create_button("➕ سند جدید", "successBtn")
        self.new_btn.clicked.connect(self.new_voucher)
        toolbar.addWidget(self.new_btn)
        
        self.edit_btn = self.create_button("✏️ ویرایش", "warningBtn")
        self.edit_btn.clicked.connect(self.edit_voucher)
        toolbar.addWidget(self.edit_btn)
        
        self.delete_btn = self.create_button("🗑️ حذف", "dangerBtn")
        self.delete_btn.clicked.connect(self.delete_voucher)
        toolbar.addWidget(self.delete_btn)
        
        toolbar.addStretch()
        
        search_label = QLabel("🔍 جستجو:")
        toolbar.addWidget(search_label)
        
        self.search_input = self.create_input("شماره یا شرح...")
        self.search_input.setMaximumWidth(self.scaled(200))
        self.search_input.textChanged.connect(self.filter_vouchers)
        toolbar.addWidget(self.search_input)
        
        return toolbar
    
    # ============================================================
    # بارگذاری داده‌ها
    # ============================================================
    
    def load_accounts(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT code, name, type FROM accounts "
                    "WHERE is_active = 1 ORDER BY code"
                )
                self.accounts = c.fetchall()
        except Exception as e:
            logger.warning(f"خطا در بارگذاری حساب‌ها: {e}")
            self.accounts = []
    
    def load_vouchers(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT v.id, v.voucher_no, v.date, v.description, v.type,
                           COALESCE(SUM(vi.debit), 0) as total_debit,
                           COALESCE(SUM(vi.credit), 0) as total_credit
                    FROM vouchers v
                    LEFT JOIN voucher_items vi ON v.id = vi.voucher_id
                    GROUP BY v.id, v.voucher_no, v.date, v.description, v.type
                    ORDER BY v.id DESC
                ''')
                rows = c.fetchall()
                
                self.vouchers_data = []
                for row in rows:
                    self.vouchers_data.append({
                        'id': row[0],
                        'voucher_no': row[1],
                        'date': row[2],
                        'description': row[3],
                        'type': row[4],
                        'total_debit': row[5] or 0,
                        'total_credit': row[6] or 0
                    })
                
                self.display_vouchers(self.vouchers_data)
        except Exception as e:
            logger.warning(f"خطا در بارگذاری اسناد: {e}")
            self.vouchers_data = []
            self.display_vouchers([])
    
    def display_vouchers(self, vouchers):
        self.vouchers_table.setRowCount(len(vouchers))
        fs = self.font_size(10)
        c = self.get_theme_colors()
        
        for i, v in enumerate(vouchers):
            values = [
                str(v.get('voucher_no', '')),
                safe_display_date(v.get('date', '')),
                v.get('description', ''),
                v.get('type', 'عادی'),
                f"{v.get('total_debit', 0):,.0f}",
                f"{v.get('total_credit', 0):,.0f}"
            ]
            
            for j, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setFont(QFont("Tahoma", fs))
                if j >= 4:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if j == 4:
                        item.setForeground(QColor(c['success']))
                    else:
                        item.setForeground(QColor(c['danger']))
                self.vouchers_table.setItem(i, j, item)
    
    def filter_vouchers(self):
        text = self.search_input.text().strip()
        if not text:
            self.display_vouchers(self.vouchers_data)
            return
        filtered = [
            v for v in self.vouchers_data
            if text.lower() in str(v.get('voucher_no', '')).lower()
            or text.lower() in str(v.get('description', '')).lower()
        ]
        self.display_vouchers(filtered)
    
    def on_voucher_selected(self):
        row = self.vouchers_table.currentRow()
        if 0 <= row < len(self.vouchers_data):
            self.show_voucher_details(self.vouchers_data[row]['id'])
    
    def show_voucher_details(self, voucher_id):
        try:
            c = self.get_theme_colors()
            
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute('SELECT * FROM vouchers WHERE id = ?', [voucher_id])
                voucher = cur.fetchone()
                if not voucher:
                    return
                
                cur.execute('''
                    SELECT vi.*, a.name as account_name
                    FROM voucher_items vi
                    JOIN accounts a ON vi.account_code = a.code
                    WHERE vi.voucher_id = ?
                ''', [voucher_id])
                items = cur.fetchall()
                
                display_date = safe_display_date(voucher['date'])
                
                html = f"""
                <div style='font-family: Tahoma; direction: rtl; 
                            color: {c["text"]}; font-size: {self.font_size(10)}pt;'>
                    <h3 style='color: {c["selected"]};'>سند شماره: {voucher['voucher_no']}</h3>
                    <p><b>تاریخ:</b> {display_date}</p>
                    <p><b>شرح:</b> {voucher['description'] or ''}</p>
                    <p><b>نوع:</b> {voucher['type'] or 'عادی'}</p>
                    <hr>
                    <h4>اقلام سند:</h4>
                    <table width='100%' border='1' 
                           style='border-collapse: collapse; border-color: {c["border"]};'>
                        <tr style='background: {c["card"]}; color: {c["text"]};'>
                            <th>کد حساب</th><th>نام حساب</th><th>شرح</th>
                            <th>بدهکار</th><th>بستانکار</th>
                        </tr>
                """
                
                total_debit = 0
                total_credit = 0
                
                for item in items:
                    html += f"""
                        <tr>
                            <td>{item['account_code']}</td>
                            <td>{item['account_name']}</td>
                            <td>{item['description'] or ''}</td>
                            <td style='text-align: left;'>{item['debit']:,.0f}</td>
                            <td style='text-align: left;'>{item['credit']:,.0f}</td>
                        </tr>
                    """
                    total_debit += item['debit'] or 0
                    total_credit += item['credit'] or 0
                
                html += f"""
                        <tr style='font-weight: bold; background: {c["card"]};'>
                            <td colspan='3'>جمع</td>
                            <td style='text-align: left;'>{total_debit:,.0f}</td>
                            <td style='text-align: left;'>{total_credit:,.0f}</td>
                        </tr>
                    </table>
                """
                
                if abs(total_debit - total_credit) < 1:
                    html += f"<p style='color: {c['success']}; font-weight: bold;'>✅ سند موازنه است</p>"
                else:
                    html += f"<p style='color: {c['danger']}; font-weight: bold;'>⚠️ عدم موازنه: {abs(total_debit - total_credit):,.0f}</p>"
                
                html += "</div>"
                self.details_text.setHtml(html)
        except Exception as e:
            logger.warning(f"خطا در نمایش جزئیات سند: {e}")
    
    # ============================================================
    # عملیات CRUD سند
    # ============================================================
    
    def new_voucher(self):
        dialog = VoucherDialog(self.accounts, customer_name=self.customer_name)
        if dialog.exec_():
            self.load_vouchers()
            QMessageBox.information(self, "موفق", "✅ سند با موفقیت ثبت شد!")
    
    def edit_voucher(self):
        row = self.vouchers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک سند انتخاب کنید!")
            return
        voucher_id = self.vouchers_data[row]['id']
        dialog = VoucherDialog(
            self.accounts, voucher_id, customer_name=self.customer_name
        )
        if dialog.exec_():
            self.load_vouchers()
            self.show_voucher_details(voucher_id)
    
    def delete_voucher(self):
        row = self.vouchers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک سند انتخاب کنید!")
            return
        
        reply = show_confirm_dialog(
            self, "تأیید حذف", "آیا از حذف این سند اطمینان دارید؟"
        )
        if reply:
            voucher_id = self.vouchers_data[row]['id']
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute('DELETE FROM voucher_items WHERE voucher_id = ?', [voucher_id])
                cur.execute('DELETE FROM vouchers WHERE id = ?', [voucher_id])
                conn.commit()
            self.load_vouchers()
            self.details_text.clear()
            QMessageBox.information(self, "موفق", "سند با موفقیت حذف شد!")
    
    # ============================================================
    # دفتر روزنامه
    # ============================================================
    
    def create_journal_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(
            self.margin(10), self.margin(10), self.margin(10), self.margin(10)
        )
        
        title = QLabel("📖 دفتر روزنامه")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("از تاریخ:"))
        self.journal_from_date = ShamsiDateEdit()
        toolbar.addWidget(self.journal_from_date)
        toolbar.addWidget(QLabel("تا تاریخ:"))
        self.journal_to_date = ShamsiDateEdit()
        toolbar.addWidget(self.journal_to_date)
        
        refresh_btn = self.create_button("🔄 نمایش", "infoBtn")
        refresh_btn.clicked.connect(self.load_journal)
        toolbar.addWidget(refresh_btn)
        
        export_btn = self.create_button("📎 خروجی", "successBtn")
        export_btn.clicked.connect(self.export_journal)
        toolbar.addWidget(export_btn)
        
        toolbar.addStretch()
        
        self.journal_search = self.create_input("جستجو در شرح...")
        self.journal_search.setMaximumWidth(self.scaled(200))
        self.journal_search.textChanged.connect(self.filter_journal)
        toolbar.addWidget(self.journal_search)
        layout.addLayout(toolbar)
        
        self.journal_table = self.create_table(
            ["ردیف", "تاریخ", "شماره سند", "شرح سند",
             "کد حساب", "نام حساب", "بدهکار", "بستانکار"],
            stretch_last=True
        )
        layout.addWidget(self.journal_table)
        
        self.journal_total_label = QLabel("جمع بدهکار: ۰ | جمع بستانکار: ۰")
        layout.addWidget(self.journal_total_label)
        
        self.journal_from_date.set_date(get_today_jalali())
        self.journal_to_date.set_date(get_today_jalali())
        self.load_journal()
        
        return widget
    
    def load_journal(self):
        try:
            from_date = self.journal_from_date.get_shamsi()
            to_date = self.journal_to_date.get_shamsi()
            
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute('''
                    SELECT v.id, v.voucher_no, v.date, v.description, v.type,
                           vi.account_code, a.name as account_name,
                           vi.debit, vi.credit
                    FROM vouchers v
                    JOIN voucher_items vi ON v.id = vi.voucher_id
                    JOIN accounts a ON vi.account_code = a.code
                    WHERE v.date >= ? AND v.date <= ?
                    ORDER BY v.date ASC, v.id ASC
                ''', [from_date, to_date])
                self.journal_data = cur.fetchall()
            
            self.display_journal(self.journal_data)
        except Exception as e:
            logger.warning(f"خطا در بارگذاری دفتر روزنامه: {e}")
            self.journal_data = []
            self.display_journal([])
    
    def display_journal(self, data):
        self.journal_table.setRowCount(len(data))
        total_debit = 0
        total_credit = 0
        fs = self.font_size(10)
        c = self.get_theme_colors()
        
        for i, row in enumerate(data):
            self.journal_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.journal_table.setItem(
                i, 1, QTableWidgetItem(safe_display_date(row['date']))
            )
            self.journal_table.setItem(i, 2, QTableWidgetItem(str(row['voucher_no'])))
            self.journal_table.setItem(
                i, 3, QTableWidgetItem(row['description'] or '')
            )
            self.journal_table.setItem(i, 4, QTableWidgetItem(row['account_code']))
            self.journal_table.setItem(
                i, 5, QTableWidgetItem(row['account_name'] or '')
            )
            
            debit_item = QTableWidgetItem(f"{row['debit']:,.0f}")
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            debit_item.setForeground(QColor(c['success']))
            self.journal_table.setItem(i, 6, debit_item)
            
            credit_item = QTableWidgetItem(f"{row['credit']:,.0f}")
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            credit_item.setForeground(QColor(c['danger']))
            self.journal_table.setItem(i, 7, credit_item)
            
            total_debit += row['debit'] or 0
            total_credit += row['credit'] or 0
        
        self.journal_total_label.setText(
            f"جمع بدهکار: {total_debit:,.0f} | جمع بستانکار: {total_credit:,.0f} | "
            f"تعداد اسناد: {len(set(row['voucher_no'] for row in data))}"
        )
    
    def filter_journal(self):
        text = self.journal_search.text().strip()
        if not text:
            self.display_journal(self.journal_data)
            return
        
        filtered = []
        for row in self.journal_data:
            if (
                text in str(row.get('description', '')).lower()
                or text in str(row.get('account_name', '')).lower()
                or text in str(row.get('account_code', '')).lower()
            ):
                filtered.append(row)
        
        self.display_journal(filtered)
    
    def export_journal(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره دفتر روزنامه",
            f"دفتر_روزنامه_{self.journal_from_date.get_shamsi()}_تا_"
            f"{self.journal_to_date.get_shamsi()}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_name:
            try:
                import csv
                with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "ردیف", "تاریخ", "شماره سند", "شرح",
                        "کد حساب", "نام حساب", "بدهکار", "بستانکار"
                    ])
                    for i, row in enumerate(self.journal_data):
                        writer.writerow([
                            i + 1,
                            safe_display_date(row['date']),
                            row['voucher_no'],
                            row['description'] or '',
                            row['account_code'],
                            row['account_name'] or '',
                            row['debit'] or 0,
                            row['credit'] or 0
                        ])
                QMessageBox.information(
                    self, "موفق",
                    f"✅ دفتر روزنامه در {file_name} ذخیره شد!"
                )
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")
    
    # ============================================================
    # دفتر کل
    # ============================================================
    
    def create_ledger_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(
            self.margin(10), self.margin(10), self.margin(10), self.margin(10)
        )
        
        title = QLabel("📚 دفتر کل")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("حساب:"))
        self.ledger_account_combo = QComboBox()
        self.ledger_account_combo.setMinimumWidth(self.scaled(200))
        self.ledger_account_combo.addItem("-- همه حساب‌ها --", "")
        for acc in self.accounts:
            self.ledger_account_combo.addItem(
                f"{acc['code']} - {acc['name']}", acc['code']
            )
        toolbar.addWidget(self.ledger_account_combo)
        
        toolbar.addWidget(QLabel("از تاریخ:"))
        self.ledger_from_date = ShamsiDateEdit()
        toolbar.addWidget(self.ledger_from_date)
        
        toolbar.addWidget(QLabel("تا تاریخ:"))
        self.ledger_to_date = ShamsiDateEdit()
        toolbar.addWidget(self.ledger_to_date)
        
        refresh_btn = self.create_button("🔄 نمایش", "infoBtn")
        refresh_btn.clicked.connect(self.load_ledger)
        toolbar.addWidget(refresh_btn)
        
        export_btn = self.create_button("📎 خروجی", "successBtn")
        export_btn.clicked.connect(self.export_ledger)
        toolbar.addWidget(export_btn)
        
        toolbar.addStretch()
        
        self.ledger_search = self.create_input("جستجو در شرح...")
        self.ledger_search.setMaximumWidth(self.scaled(200))
        self.ledger_search.textChanged.connect(self.filter_ledger)
        toolbar.addWidget(self.ledger_search)
        layout.addLayout(toolbar)
        
        self.ledger_table = self.create_table(
            ["ردیف", "تاریخ", "شماره سند", "شرح", "بدهکار", "بستانکار", "مانده"],
            stretch_last=True
        )
        layout.addWidget(self.ledger_table)
        
        self.ledger_total_label = QLabel("جمع بدهکار: ۰ | جمع بستانکار: ۰ | مانده: ۰")
        layout.addWidget(self.ledger_total_label)
        
        self.ledger_from_date.set_date(get_today_jalali())
        self.ledger_to_date.set_date(get_today_jalali())
        self.load_ledger()
        
        return widget
    
    def load_ledger(self):
        try:
            account_code = self.ledger_account_combo.currentData()
            from_date = self.ledger_from_date.get_shamsi()
            to_date = self.ledger_to_date.get_shamsi()
            
            with get_db() as conn:
                cur = conn.cursor()
                
                if account_code:
                    cur.execute('''
                        SELECT v.id, v.voucher_no, v.date, v.description,
                               vi.account_code, a.name as account_name,
                               vi.debit, vi.credit
                        FROM vouchers v
                        JOIN voucher_items vi ON v.id = vi.voucher_id
                        JOIN accounts a ON vi.account_code = a.code
                        WHERE vi.account_code = ? AND v.date >= ? AND v.date <= ?
                        ORDER BY v.date ASC, v.id ASC
                    ''', [account_code, from_date, to_date])
                    self.ledger_data = cur.fetchall()
                    self.display_ledger(self.ledger_data)
                else:
                    cur.execute('''
                        SELECT a.code, a.name, a.type,
                               COALESCE(SUM(vi.debit), 0) as total_debit,
                               COALESCE(SUM(vi.credit), 0) as total_credit
                        FROM accounts a
                        LEFT JOIN voucher_items vi ON a.code = vi.account_code
                        LEFT JOIN vouchers v ON vi.voucher_id = v.id
                        WHERE v.date >= ? AND v.date <= ?
                        GROUP BY a.code, a.name, a.type
                        ORDER BY a.code
                    ''', [from_date, to_date])
                    self.ledger_summary_data = cur.fetchall()
                    self.display_ledger_summary(self.ledger_summary_data)
        except Exception as e:
            logger.warning(f"خطا در بارگذاری دفتر کل: {e}")
            self.ledger_data = []
            self.display_ledger([])
    
    def display_ledger(self, data):
        self.ledger_table.setRowCount(len(data))
        total_debit = 0
        total_credit = 0
        balance = 0
        c = self.get_theme_colors()
        
        for i, row in enumerate(data):
            self.ledger_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.ledger_table.setItem(
                i, 1, QTableWidgetItem(safe_display_date(row['date']))
            )
            self.ledger_table.setItem(i, 2, QTableWidgetItem(str(row['voucher_no'])))
            self.ledger_table.setItem(
                i, 3, QTableWidgetItem(row['description'] or '')
            )
            
            debit_item = QTableWidgetItem(f"{row['debit']:,.0f}")
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            debit_item.setForeground(QColor(c['success']))
            self.ledger_table.setItem(i, 4, debit_item)
            
            credit_item = QTableWidgetItem(f"{row['credit']:,.0f}")
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            credit_item.setForeground(QColor(c['danger']))
            self.ledger_table.setItem(i, 5, credit_item)
            
            total_debit += row['debit'] or 0
            total_credit += row['credit'] or 0
            balance = total_debit - total_credit
            
            balance_item = QTableWidgetItem(f"{balance:,.0f}")
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            balance_item.setForeground(
                QColor(c['success'] if balance >= 0 else c['danger'])
            )
            self.ledger_table.setItem(i, 6, balance_item)
        
        self.ledger_total_label.setText(
            f"جمع بدهکار: {total_debit:,.0f} | جمع بستانکار: {total_credit:,.0f} | "
            f"مانده: {balance:,.0f}"
        )
    
    def display_ledger_summary(self, data):
        self.ledger_table.setRowCount(len(data))
        total_debit = 0
        total_credit = 0
        c = self.get_theme_colors()
        
        type_names = {
            'asset': '🏦 دارایی',
            'liability': '📋 بدهی',
            'equity': '💰 سرمایه',
            'income': '📈 درآمد',
            'expense': '💸 هزینه'
        }
        
        for i, row in enumerate(data):
            self.ledger_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.ledger_table.setItem(i, 1, QTableWidgetItem(row['code']))
            self.ledger_table.setItem(i, 2, QTableWidgetItem(row['name']))
            self.ledger_table.setItem(
                i, 3, QTableWidgetItem(type_names.get(row['type'], row['type']))
            )
            
            debit_item = QTableWidgetItem(f"{row['total_debit']:,.0f}")
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            debit_item.setForeground(QColor(c['success']))
            self.ledger_table.setItem(i, 4, debit_item)
            
            credit_item = QTableWidgetItem(f"{row['total_credit']:,.0f}")
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            credit_item.setForeground(QColor(c['danger']))
            self.ledger_table.setItem(i, 5, credit_item)
            
            total_debit += row['total_debit'] or 0
            total_credit += row['total_credit'] or 0
        
        self.ledger_total_label.setText(
            f"جمع بدهکار: {total_debit:,.0f} | جمع بستانکار: {total_credit:,.0f}"
        )
    
    def filter_ledger(self):
        text = self.ledger_search.text().strip()
        if not text:
            self.load_ledger()
            return
        
        if self.ledger_data:
            filtered = []
            for row in self.ledger_data:
                if (
                    text in str(row.get('description', '')).lower()
                    or text in str(row.get('account_name', '')).lower()
                    or text in str(row.get('account_code', '')).lower()
                ):
                    filtered.append(row)
            self.display_ledger(filtered)
    
    def export_ledger(self):
        account_name = self.ledger_account_combo.currentText()
        if not account_name or account_name == "-- همه حساب‌ها --":
            account_name = "همه_حساب‌ها"
        
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره دفتر کل",
            f"دفتر_کل_{account_name}_"
            f"{self.ledger_from_date.get_shamsi()}_تا_"
            f"{self.ledger_to_date.get_shamsi()}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_name:
            try:
                import csv
                with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    
                    if self.ledger_data:
                        writer.writerow([
                            "ردیف", "تاریخ", "شماره سند", "شرح",
                            "بدهکار", "بستانکار", "مانده"
                        ])
                        balance = 0
                        for i, row in enumerate(self.ledger_data):
                            balance += (row['debit'] or 0) - (row['credit'] or 0)
                            writer.writerow([
                                i + 1,
                                safe_display_date(row['date']),
                                row['voucher_no'],
                                row['description'] or '',
                                row['debit'] or 0,
                                row['credit'] or 0,
                                balance
                            ])
                    else:
                        writer.writerow([
                            "کد حساب", "نام حساب", "نوع", "بدهکار", "بستانکار"
                        ])
                        for row in self.ledger_summary_data:
                            writer.writerow([
                                row['code'],
                                row['name'],
                                row['type'],
                                row['total_debit'] or 0,
                                row['total_credit'] or 0
                            ])
                
                QMessageBox.information(
                    self, "موفق", f"✅ دفتر کل در {file_name} ذخیره شد!"
                )
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره: {str(e)}")


# ============================================================
# دیالوگ سند حسابداری — Theme-Integrated
# ============================================================

class VoucherDialog(BaseDialog):
    """دیالوگ ایجاد/ویرایش سند حسابداری با قابلیت ویرایش مستقیم"""
    
    def __init__(self, accounts, voucher_id=None, customer_name="", suggested_account=None):
        super().__init__(base_width=850, base_height=600)
        self.accounts = accounts
        self.voucher_id = voucher_id
        self.customer_name = customer_name
        self.suggested_account = suggested_account
        self.screen_manager = ScreenManager()
        self.is_small_screen = self.screen_manager.is_small_screen()
        
        self.setWindowTitle("سند حسابداری")
        self.setModal(True)
        
        self.setup_ui()
        if voucher_id:
            self.load_voucher_data()
        if suggested_account:
            self._apply_suggestion()
        
        self.apply_theme()
        self._apply_dialog_theme()
    
    # ========== متدهای کمکی ==========
    
    def scaled(self, value: int) -> int:
        return self.screen_manager.get_scaled(value)
    
    def spacing(self, value: int = 10) -> int:
        return self.screen_manager.get_spacing(value)
    
    def margin(self, value: int = 10) -> int:
        return self.screen_manager.get_margin(value)
    
    def font_size(self, size: int) -> int:
        return self.screen_manager.get_font_size(size)
    
    def create_button(self, text: str, object_name: str = "") -> QPushButton:
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        btn.setMinimumHeight(self.scaled(32))
        return btn
    
    def create_table(self, columns: list, stretch_last: bool = True) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setSelectionBehavior(QTableWidget.SelectItems)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setAlternatingRowColors(True)
        
        table.setEditTriggers(
            QTableWidget.DoubleClicked |
            QTableWidget.EditKeyPressed |
            QTableWidget.AnyKeyPressed
        )
        
        if stretch_last:
            table.horizontalHeader().setStretchLastSection(True)
        
        table.verticalHeader().setDefaultSectionSize(self.scaled(30))
        return table
    
    # ========== تم دیالوگ ==========
    
    def _apply_dialog_theme(self):
        """اعمال تم روی دیالوگ سند"""
        try:
            c = self.get_theme_colors()
            
            # 1. خود دیالوگ
            self.setStyleSheet(f"""
                QDialog {{
                    background: {c['bg']};
                    color: {c['text']};
                }}
                QWidget {{
                    background: {c['bg']};
                    color: {c['text']};
                }}
            """)
            
            # 2. QGroupBoxها
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
            
            # 3. QTableWidget
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
                """)
            
            # 4. QTextEditها
            for te in self.findChildren(QTextEdit):
                te.setStyleSheet(f"""
                    QTextEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: 6px;
                    }}
                    QTextEdit:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
            # 5. QComboBoxها
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
            
            # 6. QSpinBoxها
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
            
            # 7. دکمه‌ها
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
                    """)
                else:
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
                    """)
            
            # 8. QLabelها
            for lbl in self.findChildren(QLabel):
                if not lbl.styleSheet() or 'background' not in lbl.styleSheet():
                    lbl.setStyleSheet(
                        f"color: {c['text']}; background: transparent; padding: 3px;"
                    )
            
            # 9. لیبل جمع‌بندی
            if hasattr(self, 'total_label'):
                self.total_label.setStyleSheet(f"""
                    background: {c['card']};
                    color: {c['text']};
                    padding: 10px;
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    font-weight: bold;
                """)
        
        except Exception as e:
            print(f"⚠️ خطا در _apply_dialog_theme: {e}")
    
    # ========== رابط کاربری ==========
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(8))
        layout.setContentsMargins(
            self.margin(10), self.margin(10), self.margin(10), self.margin(10)
        )
        
        # ====== گروه اطلاعات سند ======
        info_group = QGroupBox("اطلاعات سند")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(self.spacing(6))
        info_layout.setLabelAlignment(Qt.AlignRight)
        
        no_layout = QHBoxLayout()
        self.voucher_no = QSpinBox()
        self.voucher_no.setRange(1, 999999)
        self.voucher_no.setMinimumHeight(self.scaled(32))
        if not self.voucher_id:
            self.voucher_no.setValue(self.get_next_voucher_no())
        no_layout.addWidget(self.voucher_no)
        
        auto_no_btn = self.create_button("🔢 خودکار")
        auto_no_btn.clicked.connect(
            lambda: self.voucher_no.setValue(self.get_next_voucher_no())
        )
        auto_no_btn.setMinimumHeight(self.scaled(32))
        no_layout.addWidget(auto_no_btn)
        no_layout.addStretch()
        info_layout.addRow("شماره سند:", no_layout)
        
        self.date = ShamsiDateEdit()
        self.date.setMinimumHeight(self.scaled(32))
        info_layout.addRow("تاریخ:", self.date)
        
        self.description = QTextEdit()
        self.description.setMaximumHeight(self.scaled(80))
        self.description.setPlaceholderText("شرح سند را وارد کنید...")
        info_layout.addRow("شرح:", self.description)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["عادی", "افتتاحیه", "اختتامیه", "اصلاحی"])
        self.type_combo.setMinimumHeight(self.scaled(32))
        info_layout.addRow("نوع سند:", self.type_combo)
        
        layout.addWidget(info_group)
        
        # ====== گروه اقلام سند ======
        items_group = QGroupBox("اقلام سند")
        items_layout = QVBoxLayout(items_group)
        items_layout.setSpacing(self.spacing(6))
        
        self.items_table = self.create_table(
            ["کد حساب", "نام حساب", "شرح", "بدهکار", "بستانکار"],
            stretch_last=True
        )
        self.items_table.cellChanged.connect(self.update_totals)
        items_layout.addWidget(self.items_table)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(self.spacing(6))
        
        add_btn = self.create_button("➕ افزودن ردیف", "infoBtn")
        add_btn.clicked.connect(self.add_item_row)
        btn_layout.addWidget(add_btn)
        
        remove_btn = self.create_button("➖ حذف ردیف", "dangerBtn")
        remove_btn.clicked.connect(self.remove_item_row)
        btn_layout.addWidget(remove_btn)
        
        duplicate_btn = self.create_button("📋 کپی ردیف")
        duplicate_btn.clicked.connect(self.duplicate_item_row)
        btn_layout.addWidget(duplicate_btn)
        
        btn_layout.addStretch()
        
        self.total_label = QLabel("جمع بدهکار: ۰ | جمع بستانکار: ۰")
        btn_layout.addWidget(self.total_label)
        
        items_layout.addLayout(btn_layout)
        layout.addWidget(items_group)
        
        # ====== دکمه‌های دیالوگ ======
        dialog_btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        dialog_btns.accepted.connect(self.accept)
        dialog_btns.rejected.connect(self.reject)
        layout.addWidget(dialog_btns)
        
        self.add_item_row()
    
    # ========== توابع کمکی ==========
    
    def get_next_voucher_no(self):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute('SELECT MAX(voucher_no) FROM vouchers')
            max_no = cur.fetchone()[0]
            return 1 if max_no is None else max_no + 1
    
    # ========== مدیریت ردیف‌ها ==========
    
    def add_item_row(self):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        self.items_table.setRowHeight(row, self.scaled(32))
        
        account_combo = QComboBox()
        account_combo.setMinimumHeight(self.scaled(30))
        account_combo.addItem("-- انتخاب حساب --", "")
        for acc in self.accounts:
            account_combo.addItem(f"{acc['code']} - {acc['name']}", acc['code'])
        
        account_combo.currentIndexChanged.connect(
            lambda checked, r=row: self.on_account_changed(r)
        )
        self.items_table.setCellWidget(row, 0, account_combo)
        
        name_item = QTableWidgetItem("")
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 1, name_item)
        
        desc_item = QTableWidgetItem("")
        desc_item.setFlags(desc_item.flags() | Qt.ItemIsEditable)
        self.items_table.setItem(row, 2, desc_item)
        
        debit_item = QTableWidgetItem("0")
        debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        debit_item.setFlags(debit_item.flags() | Qt.ItemIsEditable)
        self.items_table.setItem(row, 3, debit_item)
        
        credit_item = QTableWidgetItem("0")
        credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        credit_item.setFlags(credit_item.flags() | Qt.ItemIsEditable)
        self.items_table.setItem(row, 4, credit_item)
        
        if account_combo.count() > 1:
            self.on_account_changed(row)
    
    def duplicate_item_row(self):
        row = self.items_table.currentRow()
        if row >= 0:
            self.add_item_row()
            new_row = self.items_table.rowCount() - 1
            
            combo = self.items_table.cellWidget(row, 0)
            if combo:
                new_combo = self.items_table.cellWidget(new_row, 0)
                new_combo.setCurrentIndex(combo.currentIndex())
            
            for col in [2, 3, 4]:
                item = self.items_table.item(row, col)
                if item:
                    self.items_table.item(new_row, col).setText(item.text())
            
            self.update_totals()
    
    def on_account_changed(self, row):
        combo = self.items_table.cellWidget(row, 0)
        if combo and combo.currentIndex() > 0:
            text = combo.currentText()
            if " - " in text:
                self.items_table.item(row, 1).setText(text.split(" - ")[1])
        elif combo and combo.currentIndex() == 0:
            self.items_table.item(row, 1).setText("")
    
    def remove_item_row(self):
        row = self.items_table.currentRow()
        if row >= 0 and self.items_table.rowCount() > 1:
            self.items_table.removeRow(row)
            self.update_totals()
    
    # ========== محاسبات ==========
    
    def update_totals(self):
        total_debit = 0
        total_credit = 0
        c = self.get_theme_colors()
        
        for row in range(self.items_table.rowCount()):
            debit_item = self.items_table.item(row, 3)
            credit_item = self.items_table.item(row, 4)
            
            if debit_item:
                try:
                    text = debit_item.text().replace(',', '').strip()
                    if text and text != "0":
                        total_debit += float(text)
                except Exception:
                    pass
            
            if credit_item:
                try:
                    text = credit_item.text().replace(',', '').strip()
                    if text and text != "0":
                        total_credit += float(text)
                except Exception:
                    pass
        
        self.total_label.setText(
            f"جمع بدهکار: {total_debit:,.0f} | جمع بستانکار: {total_credit:,.0f}"
        )
        
        if abs(total_debit - total_credit) < 1:
            self.total_label.setStyleSheet(f"""
                background: {c['success']};
                color: #ffffff;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            """)
        else:
            self.total_label.setStyleSheet(f"""
                background: {c['danger']};
                color: #ffffff;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            """)
        
        return total_debit, total_credit
    
    # ========== بارگذاری داده‌های ویرایش ==========
    
    def load_voucher_data(self):
        try:
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute('SELECT * FROM vouchers WHERE id = ?', [self.voucher_id])
                voucher = cur.fetchone()
                if not voucher:
                    return
                
                self.voucher_no.setValue(voucher['voucher_no'])
                if voucher['date']:
                    self.date.set_date(voucher['date'])
                self.description.setPlainText(voucher['description'] or '')
                
                index = self.type_combo.findText(voucher['type'] or "عادی")
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)
                
                cur.execute(
                    'SELECT * FROM voucher_items WHERE voucher_id = ? ORDER BY id',
                    [self.voucher_id]
                )
                items = cur.fetchall()
                
                while self.items_table.rowCount() > 0:
                    self.items_table.removeRow(0)
                
                for item in items:
                    row = self.items_table.rowCount()
                    self.add_item_row()
                    
                    combo = self.items_table.cellWidget(row, 0)
                    if combo:
                        for i in range(combo.count()):
                            if combo.itemData(i) == item['account_code']:
                                combo.setCurrentIndex(i)
                                break
                    
                    self.items_table.item(row, 2).setText(item['description'] or "")
                    self.items_table.item(row, 3).setText(
                        f"{item['debit']:,.0f}" if item['debit'] else "0"
                    )
                    self.items_table.item(row, 4).setText(
                        f"{item['credit']:,.0f}" if item['credit'] else "0"
                    )
                
                self.update_totals()
        except Exception as e:
            logger.warning(f"خطا در بارگذاری داده‌های سند: {e}")
    
    def _apply_suggestion(self):
        if self.suggested_account and self.suggested_account.get("success"):
            self.add_item_row()
            row = self.items_table.rowCount() - 1
            combo = self.items_table.cellWidget(row, 0)
            account_code = self.suggested_account.get("account_code")
            if combo and account_code:
                for i in range(combo.count()):
                    if combo.itemData(i) == account_code:
                        combo.setCurrentIndex(i)
                        break
    
    # ========== ذخیره ==========
    
    def accept(self):
        if not self.description.toPlainText().strip():
            QMessageBox.warning(self, "خطا", "شرح سند را وارد کنید!")
            return
        
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "حداقل یک ردیف به سند اضافه کنید!")
            return
        
        total_debit, total_credit = self.update_totals()
        items_data = []
        
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 0)
            if not combo or combo.currentIndex() <= 0:
                continue
            
            account_code = combo.currentData()
            description = self.items_table.item(row, 2).text() or ""
            
            try:
                debit_text = (
                    self.items_table.item(row, 3).text().replace(',', '').strip() or "0"
                )
                credit_text = (
                    self.items_table.item(row, 4).text().replace(',', '').strip() or "0"
                )
                debit = float(debit_text) if debit_text else 0
                credit = float(credit_text) if credit_text else 0
            except ValueError:
                QMessageBox.warning(
                    self, "خطا", f"مقادیر عددی ردیف {row+1} نامعتبر است!"
                )
                return
            
            if debit == 0 and credit == 0:
                QMessageBox.warning(self, "خطا", f"ردیف {row+1} مبلغ ندارد!")
                return
            
            items_data.append({
                'account_code': account_code,
                'description': description,
                'debit': debit,
                'credit': credit
            })
        
        if len(items_data) == 0:
            QMessageBox.warning(self, "خطا", "حداقل یک ردیف معتبر اضافه کنید!")
            return
        
        if abs(total_debit - total_credit) > 1:
            QMessageBox.warning(
                self, "خطا",
                f"سند موازنه نیست!\nاختلاف: {abs(total_debit - total_credit):,.0f}"
            )
            return
        
        try:
            with get_db() as conn:
                cur = conn.cursor()
                shamsi_date = self.date.get_shamsi()
                
                if self.voucher_id:
                    cur.execute('''
                        UPDATE vouchers 
                        SET voucher_no=?, date=?, description=?, type=?
                        WHERE id=?
                    ''', [
                        self.voucher_no.value(), shamsi_date,
                        self.description.toPlainText().strip(),
                        self.type_combo.currentText(), self.voucher_id
                    ])
                    cur.execute(
                        'DELETE FROM voucher_items WHERE voucher_id = ?',
                        [self.voucher_id]
                    )
                    voucher_id = self.voucher_id
                else:
                    cur.execute('''
                        INSERT INTO vouchers (voucher_no, date, description, type)
                        VALUES (?, ?, ?, ?)
                    ''', [
                        self.voucher_no.value(), shamsi_date,
                        self.description.toPlainText().strip(),
                        self.type_combo.currentText()
                    ])
                    voucher_id = cur.lastrowid
                
                for item in items_data:
                    cur.execute('''
                        INSERT INTO voucher_items 
                        (voucher_id, account_code, description, debit, credit)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [
                        voucher_id, item['account_code'], item['description'],
                        item['debit'], item['credit']
                    ])
                
                conn.commit()
            
            QMessageBox.information(self, "موفق", "✅ سند با موفقیت ذخیره شد!")
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا در ذخیره سند: {str(e)}")
