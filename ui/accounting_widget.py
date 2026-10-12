# ui/accounting_widget.py
# ============================================================
# ویجت حسابداری — نسخه 7.1 (با چاپ و PDF در همه تب‌ها)
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui.base_widgets import BaseWidget, BaseDialog
from ui.coding_manager import CodingStructure
from ui.accounting_pdf import AccountingPDFGenerator, get_pdf_generator
from database import get_db, ModuleLimitHelper
from dialog_utils import show_confirm_dialog
from shamsi_date import ShamsiDateEdit, safe_display_date, get_today_jalali
from screen_utils import ScreenManager
from ui.account_manager_widget import AccountManagerWidget
from datetime import datetime
import sys
import os
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# توابع کمکی
# ═══════════════════════════════════════════════════════════

def _get_company_info() -> dict:
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
                    'company_economic': '',
                    'company_phone': '',
                    'company_address': '',
                }
            return info
    except Exception as e:
        logger.warning(f"خطا: {e}")
        return {
            'company_name': 'شرکت حسابداری پارسه',
            'company_economic': '',
            'company_phone': '',
            'company_address': '',
        }


# ═══════════════════════════════════════════════════════════
# کلاس جستجوی حساب
# ═══════════════════════════════════════════════════════════

class AccountSearchBox(QWidget):
    """ویجت جستجوی حساب با Auto-complete"""
    
    account_selected = pyqtSignal(str)
    
    def __init__(self, accounts, parent=None):
        super().__init__(parent)
        self.accounts = accounts or []
        self.selected_code = None
        self._popup = None
        self.screen_manager = ScreenManager()
        self.setup_ui()
        self._apply_theme()
    
    def _scaled(self, value):
        return self.screen_manager.get_scaled(value)
    
    def _font_size(self, size):
        return self.screen_manager.get_font_size(size)
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("🔍 کد یا نام حساب را تایپ کنید...")
        self.line_edit.setMinimumHeight(self._scaled(38))
        font = self.line_edit.font()
        font.setPointSize(self._font_size(11))
        self.line_edit.setFont(font)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.returnPressed.connect(self._select_first)
        layout.addWidget(self.line_edit)
        
        self._popup = QListWidget()
        self._popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self._popup.setFocusPolicy(Qt.NoFocus)
        self._popup.itemClicked.connect(self._on_item_clicked)
        self._popup.hide()
        
        self.line_edit.installEventFilter(self)
    
    def set_accounts(self, accounts):
        self.accounts = accounts or []
    
    def _on_text_changed(self):
        if self._popup is None:
            return
        
        text = self.line_edit.text().lower().strip()
        
        if " - " in text:
            return
        
        if not text:
            self.selected_code = None
            self._popup.hide()
            return
        
        matches = []
        for acc in self.accounts:
            code = str(acc.get('code', '')).lower()
            name = str(acc.get('name', '')).lower()
            
            if text in code or text in name:
                matches.append(acc)
                if len(matches) >= 20:
                    break
        
        if not matches:
            self._popup.hide()
            return
        
        self._popup.clear()
        for acc in matches:
            icon_map = {
                'asset': '🏦', 'liability': '📋',
                'equity': '💰', 'income': '📈', 'expense': '💸',
            }
            icon = icon_map.get(acc.get('type', ''), '📄')
            
            item_text = f"{icon} {acc['code']} - {acc['name']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, acc['code'])
            
            font = item.font()
            font.setPointSize(self._font_size(11))
            item.setFont(font)
            
            self._popup.addItem(item)
        
        pos = self.line_edit.mapToGlobal(QPoint(0, self.line_edit.height()))
        self._popup.move(pos)
        
        popup_width = max(self.line_edit.width(), self._scaled(450))
        self._popup.setFixedWidth(popup_width)
        
        item_height = self._scaled(36)
        popup_height = min(self._scaled(350), len(matches) * item_height + self._scaled(10))
        self._popup.setFixedHeight(popup_height)
        
        self._popup.show()
        self._popup.setCurrentRow(0)
    
    def eventFilter(self, obj, event):
        if obj != self.line_edit:
            return super().eventFilter(obj, event)
        
        if self._popup is None:
            return super().eventFilter(obj, event)
        
        if not self._popup.isVisible():
            return super().eventFilter(obj, event)
        
        if event.type() == QEvent.KeyPress:
            key = event.key()
            
            if key == Qt.Key_Down:
                current = self._popup.currentRow()
                if current < self._popup.count() - 1:
                    self._popup.setCurrentRow(current + 1)
                return True
            
            elif key == Qt.Key_Up:
                current = self._popup.currentRow()
                if current > 0:
                    self._popup.setCurrentRow(current - 1)
                return True
            
            elif key in (Qt.Key_Return, Qt.Key_Enter):
                self._select_current()
                return True
            
            elif key == Qt.Key_Escape:
                self._popup.hide()
                return True
        
        return super().eventFilter(obj, event)
    
    def _select_first(self):
        if self._popup is None:
            return
        if self._popup.count() > 0:
            self._popup.setCurrentRow(0)
            self._select_current()
    
    def _select_current(self):
        if self._popup is None:
            return
        
        item = self._popup.currentItem()
        if item:
            code = item.data(Qt.UserRole)
            self.selected_code = code
            
            for acc in self.accounts:
                if acc['code'] == code:
                    self.line_edit.blockSignals(True)
                    self.line_edit.setText(f"{code} - {acc['name']}")
                    self.line_edit.blockSignals(False)
                    break
            
            self._popup.hide()
            self.account_selected.emit(code)
    
    def _on_item_clicked(self, item):
        if self._popup is None:
            return
        self._popup.setCurrentItem(item)
        self._select_current()
    
    def get_code(self):
        return self.selected_code
    
    def set_code(self, code):
        self.selected_code = code
        for acc in self.accounts:
            if acc['code'] == code:
                self.line_edit.blockSignals(True)
                self.line_edit.setText(f"{code} - {acc['name']}")
                self.line_edit.blockSignals(False)
                return
    
    def clear(self):
        self.line_edit.blockSignals(True)
        self.line_edit.clear()
        self.line_edit.blockSignals(False)
        self.selected_code = None
    
    def _apply_theme(self):
        try:
            from ui.styles.theme_manager import get_theme_manager
            tm = get_theme_manager()
            is_dark = tm.get_theme_name() == 'dark'
            
            if is_dark:
                bg = "#1a1a2e"
                text = "#e0e0e0"
                border = "#0f3460"
                selected_bg = "#533483"
                selected_text = "#ffffff"
                hover = "#2a2a4a"
            else:
                bg = "#ffffff"
                text = "#1a1a2e"
                border = "#dcdde1"
                selected_bg = "#1976D2"
                selected_text = "#ffffff"
                hover = "#f0f0f0"
            
            self.line_edit.setStyleSheet(f"""
                QLineEdit {{
                    background: {bg};
                    color: {text};
                    border: 2px solid {border};
                    border-radius: 8px;
                    padding: 6px 12px;
                    min-height: {self._scaled(30)}px;
                    font-size: {self._font_size(11)}pt;
                }}
                QLineEdit:focus {{
                    border: 2px solid {selected_bg};
                    background: {hover};
                }}
            """)
            
            if self._popup:
                self._popup.setStyleSheet(f"""
                    QListWidget {{
                        background: {bg};
                        color: {text};
                        border: 2px solid {selected_bg};
                        border-radius: 8px;
                        padding: 4px;
                        outline: none;
                        font-size: {self._font_size(11)}pt;
                    }}
                    QListWidget::item {{
                        padding: {self._scaled(8)}px {self._scaled(12)}px;
                        border-radius: 4px;
                        min-height: {self._scaled(24)}px;
                    }}
                    QListWidget::item:selected {{
                        background: {selected_bg};
                        color: {selected_text};
                    }}
                    QListWidget::item:hover {{
                        background: {hover};
                    }}
                """)
        except Exception as e:
            print(f"⚠️ خطا theme: {e}")


# ═══════════════════════════════════════════════════════════
# ویجت اصلی حسابداری
# ═══════════════════════════════════════════════════════════

class AccountingWidget(BaseWidget):
    """ویجت اصلی حسابداری با قابلیت چاپ و PDF"""
    
    def __init__(self, customer_name: str = "", user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        self.customer_name = customer_name
        self.user_level = user_level
        self.vouchers_data = []
        self.journal_data = []
        self.ledger_data = []
        self.ledger_summary_data = []
        self.accounts = []
        
        # PDF Generator
        self.company_info = _get_company_info()
        self.pdf_generator = get_pdf_generator(self.company_info)
        
        # ScreenManager
        self.screen_manager = ScreenManager()
        self.scale = self.screen_manager.scale
        self.is_small_screen = self.screen_manager.is_small_screen()
        
        # کدینگ
        self.coding = CodingStructure()
        if not self.coding.levels:
            self.coding.get_default_structure()
        
        self._init_ai()
        self.setup_ui()
        self.load_vouchers()
        self.load_accounts()
        self.update_ui_by_permission()
        self._apply_widget_theme()
    
    # ═══════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def scaled(self, value: int) -> int:
        return self.screen_manager.get_scaled(value)
    
    def font_size(self, size: int) -> int:
        return self.screen_manager.get_font_size(size)
    
    def spacing(self, value: int = 10) -> int:
        return self.screen_manager.get_spacing(value)
    
    def margin(self, value: int = 10) -> int:
        return self.screen_manager.get_margin(value)
    
    def padding(self, value: int = 10) -> int:
        return self.screen_manager.get_padding(value)
    
    # ═══════════════════════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════════════════════
    
    def _apply_widget_theme(self):
        try:
            c = self.get_theme_colors()
            font_sz = self.font_size(10)
            
            self.setStyleSheet(f"""
                QWidget {{
                    background: {c['bg']};
                    color: {c['text']};
                    font-size: {font_sz}pt;
                }}
            """)
            
            if hasattr(self, 'tabs'):
                self.tabs.setStyleSheet(f"""
                    QTabWidget::pane {{
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: {self.padding(8)}px;
                        background: {c['bg']};
                    }}
                    QTabBar::tab {{
                        padding: {self.padding(10)}px {self.padding(18)}px;
                        margin: 2px;
                        border-radius: 6px;
                        background: {c['bg_alt']};
                        color: {c['text']};
                        font-weight: bold;
                        font-size: {self.font_size(10)}pt;
                    }}
                    QTabBar::tab:selected {{
                        background: {c['selected']};
                        color: {c['selected_text']};
                    }}
                    QTabBar::tab:hover {{
                        background: {c['hover']};
                    }}
                """)
            
            for gb in self.findChildren(QGroupBox):
                gb.setStyleSheet(f"""
                    QGroupBox {{
                        background: {c['card']};
                        color: {c['text']};
                        border: 2px solid {c['border']};
                        border-radius: 8px;
                        margin-top: {self.margin(15)}px;
                        padding: {self.padding(15)}px {self.padding(10)}px {self.padding(10)}px {self.padding(10)}px;
                        font-weight: bold;
                        font-size: {self.font_size(11)}pt;
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        subcontrol-position: top right;
                        right: {self.margin(15)}px;
                        padding: 0 {self.padding(8)}px;
                        color: {c['selected']};
                        background: {c['bg']};
                    }}
                """)
            
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
                        font-size: {self.font_size(10)}pt;
                    }}
                    QTableWidget::item {{
                        padding: {self.padding(6)}px;
                        border: none;
                    }}
                    QTableWidget::item:selected {{
                        background: {c['selected']};
                        color: {c['selected_text']};
                    }}
                    QHeaderView::section {{
                        background: {c['card']};
                        color: {c['text']};
                        padding: {self.padding(8)}px;
                        border: none;
                        border-right: 1px solid {c['border']};
                        border-bottom: 1px solid {c['border']};
                        font-weight: bold;
                        font-size: {self.font_size(10)}pt;
                    }}
                """)
            
            for te in self.findChildren(QTextEdit):
                te.setStyleSheet(f"""
                    QTextEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: {self.padding(8)}px;
                        font-size: {self.font_size(10)}pt;
                    }}
                """)
            
            for le in self.findChildren(QLineEdit):
                if isinstance(le.parent(), AccountSearchBox):
                    continue
                le.setStyleSheet(f"""
                    QLineEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: {self.padding(6)}px {self.padding(10)}px;
                        min-height: {self.scaled(26)}px;
                        font-size: {self.font_size(10)}pt;
                    }}
                    QLineEdit:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
            for cb in self.findChildren(QComboBox):
                cb.setStyleSheet(f"""
                    QComboBox {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: {self.padding(6)}px {self.padding(10)}px;
                        min-height: {self.scaled(26)}px;
                        font-size: {self.font_size(10)}pt;
                    }}
                    QComboBox:focus {{
                        border: 2px solid {c['selected']};
                    }}
                    QComboBox::drop-down {{
                        border: none;
                        width: {self.scaled(24)}px;
                    }}
                    QComboBox QAbstractItemView {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        selection-background-color: {c['selected']};
                        selection-color: {c['selected_text']};
                        font-size: {self.font_size(10)}pt;
                    }}
                """)
            
            for sb in self.findChildren((QSpinBox, QDoubleSpinBox)):
                sb.setStyleSheet(f"""
                    QSpinBox, QDoubleSpinBox {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: {self.padding(6)}px;
                        min-height: {self.scaled(26)}px;
                        font-size: {self.font_size(10)}pt;
                    }}
                    QSpinBox:focus, QDoubleSpinBox:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
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
                            padding: {self.padding(8)}px {self.padding(16)}px;
                            font-weight: bold;
                            min-height: {self.scaled(30)}px;
                            font-size: {self.font_size(10)}pt;
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
                            padding: {self.padding(8)}px {self.padding(16)}px;
                            font-weight: bold;
                            min-height: {self.scaled(30)}px;
                            font-size: {self.font_size(10)}pt;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                            border: 1px solid {c['selected']};
                        }}
                    """)
            
            for lbl in self.findChildren(QLabel):
                obj_name = lbl.objectName()
                
                if obj_name == 'titleLabel':
                    lbl.setStyleSheet(f"""
                        color: {c['selected']};
                        font-size: {self.font_size(16)}pt;
                        font-weight: bold;
                        padding: {self.padding(8)}px;
                        background: transparent;
                    """)
                elif obj_name == 'subtitleLabel':
                    lbl.setStyleSheet(f"""
                        color: {c['text']};
                        font-size: {self.font_size(12)}pt;
                        font-weight: bold;
                        padding: {self.padding(6)}px;
                        background: transparent;
                    """)
                elif not lbl.styleSheet() or 'background' not in lbl.styleSheet():
                    text = lbl.text() or ""
                    if not any(text.startswith(p) for p in [
                        '🏢', '🖼️', '🌍', '📋', '📊', '💰', '🤖',
                        '💾', '🔧', '📅', '⚙️', '📝', '💡', '✏️',
                        '📈', '🏦', '📉', '🔒', '👥', '📦', '💵',
                        '⚠️', '✅', '❌', '🔍', '📄', '📖', '📚'
                    ]):
                        lbl.setStyleSheet(
                            f"color: {c['text']}; background: transparent; "
                            f"padding: {self.padding(3)}px; font-size: {self.font_size(10)}pt;"
                        )
            
            for attr in ['journal_total_label', 'ledger_total_label', 'total_label']:
                if hasattr(self, attr):
                    getattr(self, attr).setStyleSheet(f"""
                        background: {c['card']};
                        color: {c['text']};
                        padding: {self.padding(10)}px;
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: {self.font_size(10)}pt;
                    """)
            
            for w in self.findChildren(QWidget):
                if w.objectName() == 'cardWidget':
                    w.setStyleSheet(f"""
                        QWidget#cardWidget {{
                            background: {c['card']};
                            border: 1px solid {c['border']};
                            border-radius: 8px;
                        }}
                    """)
        
        except Exception as e:
            print(f"⚠️ خطا theme: {e}")
    
    # ═══════════════════════════════════════════════════════════
    # Permission
    # ═══════════════════════════════════════════════════════════
    
    def set_user_level(self, level: str):
        self.user_level = level
        self.update_ui_by_permission()
    
    def update_ui_by_permission(self):
        can_edit = self.user_level in ['admin', 'accountant']
        
        for attr in ['new_btn', 'edit_btn', 'delete_btn']:
            if hasattr(self, attr):
                getattr(self, attr).setVisible(can_edit)
    
    def _init_ai(self):
        self.ai_ready = False
        try:
            import ImanAILite
            self.ai_ready = True
        except Exception:
            pass
    
    # ═══════════════════════════════════════════════════════════
    # UI Setup
    # ═══════════════════════════════════════════════════════════
    
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
    
    # ═══════════════════════════════════════════════════════════
    # Helper Methods for UI
    # ═══════════════════════════════════════════════════════════
    
    def create_table(self, columns: list, stretch_last: bool = True) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        
        if stretch_last:
            table.horizontalHeader().setStretchLastSection(True)
        
        table.verticalHeader().setDefaultSectionSize(self.scaled(30))
        return table
    
    def create_button(self, text: str, object_name: str = "") -> QPushButton:
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        btn.setMinimumHeight(self.scaled(32))
        return btn
    
    def create_input(self, placeholder: str = "") -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setMinimumHeight(self.scaled(32))
        return inp
    
    # ═══════════════════════════════════════════════════════════
    # تب ثبت اسناد
    # ═══════════════════════════════════════════════════════════
    
    def create_voucher_tab(self):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setSpacing(self.spacing(10))
        main_layout.setContentsMargins(
            self.margin(10), self.margin(10), self.margin(10), self.margin(10)
        )
        
        # پنل راست
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
        
        # پنل چپ
        left_panel = QWidget()
        left_panel.setObjectName("cardWidget")
        left_panel.setMaximumWidth(self.scaled(450))
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(self.spacing(10))
        
        detail_title = QLabel("📋 جزئیات سند")
        detail_title.setObjectName("subtitleLabel")
        left_layout.addWidget(detail_title)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("یک سند را انتخاب کنید...")
        left_layout.addWidget(self.details_text)
        
        # ───── دکمه‌های چاپ و PDF ─────
        print_layout = QHBoxLayout()
        print_layout.setSpacing(self.spacing(8))
        
        self.print_voucher_btn = self.create_button("🖨️ چاپ سند", "infoBtn")
        self.print_voucher_btn.setMinimumHeight(self.scaled(38))
        self.print_voucher_btn.clicked.connect(self.print_current_voucher)
        print_layout.addWidget(self.print_voucher_btn)
        
        self.pdf_voucher_btn = self.create_button("📄 PDF سند", "successBtn")
        self.pdf_voucher_btn.setMinimumHeight(self.scaled(38))
        self.pdf_voucher_btn.clicked.connect(self.save_current_voucher_pdf)
        print_layout.addWidget(self.pdf_voucher_btn)
        
        left_layout.addLayout(print_layout)
        
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
    
    # ═══════════════════════════════════════════════════════════
    # بارگذاری داده‌ها
    # ═══════════════════════════════════════════════════════════
    
    def load_accounts(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT code, name, type FROM accounts "
                    "WHERE is_active = 1 ORDER BY code"
                )
                self.accounts = [dict(row) for row in c.fetchall()]
        except Exception as e:
            logger.warning(f"خطا: {e}")
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
            logger.warning(f"خطا: {e}")
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
                    html += f"<p style='color: {c['danger']}; font-weight: bold;'>⚠️ عدم موازنه</p>"
                
                html += "</div>"
                self.details_text.setHtml(html)
        except Exception as e:
            logger.warning(f"خطا: {e}")
    
    # ═══════════════════════════════════════════════════════════
    # چاپ و PDF سند
    # ═══════════════════════════════════════════════════════════
    
    def _get_current_voucher_data(self):
        """دریافت داده سند انتخاب‌شده فعلی"""
        row = self.vouchers_table.currentRow()
        if row < 0 or row >= len(self.vouchers_data):
            return None, None
        
        voucher_id = self.vouchers_data[row]['id']
        
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM vouchers WHERE id = ?', [voucher_id])
            v = cur.fetchone()
            if not v:
                return None, None
            
            cur.execute('''
                SELECT vi.*, a.name as account_name
                FROM voucher_items vi
                JOIN accounts a ON vi.account_code = a.code
                WHERE vi.voucher_id = ?
                ORDER BY vi.id
            ''', [voucher_id])
            items = cur.fetchall()
        
        voucher = {
            'voucher_no': v['voucher_no'],
            'date': safe_display_date(v['date']),
            'description': v['description'] or '',
            'type': v['type'] or 'عادی',
        }
        
        items_list = [{
            'account_code': it['account_code'],
            'account_name': it['account_name'],
            'description': it['description'] or '',
            'debit': it['debit'] or 0,
            'credit': it['credit'] or 0,
        } for it in items]
        
        return voucher, items_list
    
    def print_current_voucher(self):
        """چاپ سند جاری"""
        voucher, items = self._get_current_voucher_data()
        
        if not voucher:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        try:
            html = self.pdf_generator.generate_voucher_html(voucher, items)
            AccountingPDFGenerator.print_html(html, self)
        except Exception as e:
            logger.error(f"خطا در چاپ: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ خطا در چاپ: {str(e)}")
    
    def save_current_voucher_pdf(self):
        """ذخیره PDF سند جاری"""
        voucher, items = self._get_current_voucher_data()
        
        if not voucher:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        
        default_name = f"سند_{voucher['voucher_no']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        file_path = AccountingPDFGenerator.ask_save_path(self, default_name)
        if not file_path:
            return
        
        try:
            success = self.pdf_generator.generate_voucher_pdf(
                voucher, items, file_path
            )
            
            if success:
                QMessageBox.information(
                    self, "موفق",
                    f"✅ PDF سند ذخیره شد:\n{file_path}"
                )
            else:
                QMessageBox.warning(
                    self, "خطا",
                    "❌ خطا در تولید PDF!\n"
                    "لطفاً مطمئن شوید ReportLab نصب است:\n"
                    "pip install reportlab arabic-reshaper python-bidi"
                )
        except Exception as e:
            logger.error(f"خطا در PDF: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    # ═══════════════════════════════════════════════════════════
    # CRUD
    # ═══════════════════════════════════════════════════════════
    
    def new_voucher(self):
        dialog = VoucherDialog(
            self.accounts,
            customer_name=self.customer_name,
            coding=self.coding
        )
        if dialog.exec_():
            self.load_vouchers()
            QMessageBox.information(self, "موفق", "✅ سند ثبت شد!")
    
    def edit_voucher(self):
        row = self.vouchers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
            return
        voucher_id = self.vouchers_data[row]['id']
        dialog = VoucherDialog(
            self.accounts,
            voucher_id,
            customer_name=self.customer_name,
            coding=self.coding
        )
        if dialog.exec_():
            self.load_vouchers()
            self.show_voucher_details(voucher_id)
    
    def delete_voucher(self):
        row = self.vouchers_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک سند انتخاب کنید!")
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
            QMessageBox.information(self, "موفق", "سند حذف شد!")
    
    # ═══════════════════════════════════════════════════════════
    # دفتر روزنامه
    # ═══════════════════════════════════════════════════════════
    
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
        
        # ═════ ردیف اول: فیلترها و تاریخ‌ها ═════
        toolbar1 = QHBoxLayout()
        toolbar1.setSpacing(self.spacing(8))
        
        toolbar1.addWidget(QLabel("از تاریخ:"))
        self.journal_from_date = ShamsiDateEdit()
        self.journal_from_date.setMinimumHeight(self.scaled(32))
        toolbar1.addWidget(self.journal_from_date)
        
        toolbar1.addWidget(QLabel("تا تاریخ:"))
        self.journal_to_date = ShamsiDateEdit()
        self.journal_to_date.setMinimumHeight(self.scaled(32))
        toolbar1.addWidget(self.journal_to_date)
        
        refresh_btn = self.create_button("🔄 نمایش", "infoBtn")
        refresh_btn.clicked.connect(self.load_journal)
        toolbar1.addWidget(refresh_btn)
        
        toolbar1.addStretch()
        
        self.journal_search = self.create_input("جستجو در شرح...")
        self.journal_search.setMaximumWidth(self.scaled(250))
        self.journal_search.textChanged.connect(self.filter_journal)
        toolbar1.addWidget(self.journal_search)
        
        layout.addLayout(toolbar1)
        
        # ═════ ردیف دوم: دکمه‌های چاپ و خروجی ═════
        toolbar2 = QHBoxLayout()
        toolbar2.setSpacing(self.spacing(8))
        
        info_label = QLabel("📌 خروجی گزارش:")
        info_label.setStyleSheet(
            f"color: {self.get_theme_colors()['text_secondary']}; "
            f"font-size: {self.font_size(10)}pt; font-weight: bold;"
        )
        toolbar2.addWidget(info_label)
        
        print_btn = self.create_button("🖨️ چاپ", "infoBtn")
        print_btn.setMinimumHeight(self.scaled(36))
        print_btn.setToolTip("چاپ دفتر روزنامه")
        print_btn.clicked.connect(self.print_journal)
        toolbar2.addWidget(print_btn)
        
        pdf_btn = self.create_button("📄 خروجی PDF", "successBtn")
        pdf_btn.setMinimumHeight(self.scaled(36))
        pdf_btn.setToolTip("ذخیره PDF دفتر روزنامه")
        pdf_btn.clicked.connect(self.save_journal_pdf)
        toolbar2.addWidget(pdf_btn)
        
        csv_btn = self.create_button("📎 خروجی Excel", "warningBtn")
        csv_btn.setMinimumHeight(self.scaled(36))
        csv_btn.setToolTip("ذخیره CSV")
        csv_btn.clicked.connect(self.export_journal)
        toolbar2.addWidget(csv_btn)
        
        toolbar2.addStretch()
        layout.addLayout(toolbar2)
        
        # ═════ جدول ═════
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
            logger.warning(f"خطا: {e}")
            self.journal_data = []
            self.display_journal([])
    
    def display_journal(self, data):
        self.journal_table.setRowCount(len(data))
        total_debit = 0
        total_credit = 0
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
            f"جمع بدهکار: {total_debit:,.0f} | جمع بستانکار: {total_credit:,.0f}"
        )
    
    def filter_journal(self):
        text = self.journal_search.text().strip()
        if not text:
            self.display_journal(self.journal_data)
            return
        
        filtered = [
            row for row in self.journal_data
            if (text in str(row.get('description', '')).lower()
                or text in str(row.get('account_name', '')).lower()
                or text in str(row.get('account_code', '')).lower())
        ]
        self.display_journal(filtered)
    
    def print_journal(self):
        """چاپ دفتر روزنامه"""
        if not self.journal_data:
            QMessageBox.warning(self, "خطا", "داده‌ای برای چاپ وجود ندارد!")
            return
        
        try:
            from_date = self.journal_from_date.get_shamsi()
            to_date = self.journal_to_date.get_shamsi()
            
            headers = ["ردیف", "تاریخ", "شماره سند", "شرح",
                       "کد حساب", "نام حساب", "بدهکار", "بستانکار"]
            
            rows = []
            total_debit = 0
            total_credit = 0
            
            for i, row in enumerate(self.journal_data, 1):
                debit = row['debit'] or 0
                credit = row['credit'] or 0
                total_debit += debit
                total_credit += credit
                
                rows.append([
                    i,
                    safe_display_date(row['date']),
                    row['voucher_no'],
                    row['description'] or '',
                    row['account_code'],
                    row['account_name'] or '',
                    f"{debit:,.0f}" if debit else "-",
                    f"{credit:,.0f}" if credit else "-",
                ])
            
            totals = [
                "", "", "", "جمع کل", "", "",
                f"{total_debit:,.0f}",
                f"{total_credit:,.0f}",
            ]
            
            html = self.pdf_generator.generate_table_html(
                "دفتر روزنامه",
                f"از {from_date} تا {to_date}",
                headers, rows, totals
            )
            
            AccountingPDFGenerator.print_html(html, self)
        except Exception as e:
            logger.error(f"خطا در چاپ: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ خطا در چاپ: {str(e)}")
    
    def save_journal_pdf(self):
        """ذخیره PDF دفتر روزنامه"""
        if not self.journal_data:
            QMessageBox.warning(self, "خطا", "داده‌ای برای ذخیره وجود ندارد!")
            return
        
        from_date = self.journal_from_date.get_shamsi()
        to_date = self.journal_to_date.get_shamsi()
        
        default_name = f"دفتر_روزنامه_{from_date}_تا_{to_date}.pdf"
        default_name = default_name.replace('/', '_')
        
        file_path = AccountingPDFGenerator.ask_save_path(self, default_name)
        if not file_path:
            return
        
        try:
            data = [dict(row) for row in self.journal_data]
            
            success = self.pdf_generator.generate_journal_pdf(
                data, from_date, to_date, file_path
            )
            
            if success:
                QMessageBox.information(
                    self, "موفق",
                    f"✅ PDF دفتر روزنامه ذخیره شد:\n{file_path}"
                )
            else:
                QMessageBox.warning(self, "خطا", "❌ خطا در تولید PDF!")
        except Exception as e:
            logger.error(f"خطا در PDF: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def export_journal(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره دفتر روزنامه",
            f"دفتر_روزنامه_{self.journal_from_date.get_shamsi()}.csv",
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
                QMessageBox.information(self, "موفق", "✅ ذخیره شد!")
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    # ═══════════════════════════════════════════════════════════
    # دفتر کل
    # ═══════════════════════════════════════════════════════════
    
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
        
        # ═════ ردیف اول: فیلترها ═════
        toolbar1 = QHBoxLayout()
        toolbar1.setSpacing(self.spacing(8))
        
        toolbar1.addWidget(QLabel("حساب:"))
        self.ledger_account_combo = QComboBox()
        self.ledger_account_combo.setMinimumWidth(self.scaled(250))
        self.ledger_account_combo.setMinimumHeight(self.scaled(32))
        self.ledger_account_combo.addItem("-- همه حساب‌ها --", "")
        for acc in self.accounts:
            self.ledger_account_combo.addItem(
                f"{acc['code']} - {acc['name']}", acc['code']
            )
        toolbar1.addWidget(self.ledger_account_combo)
        
        toolbar1.addWidget(QLabel("از تاریخ:"))
        self.ledger_from_date = ShamsiDateEdit()
        self.ledger_from_date.setMinimumHeight(self.scaled(32))
        toolbar1.addWidget(self.ledger_from_date)
        
        toolbar1.addWidget(QLabel("تا تاریخ:"))
        self.ledger_to_date = ShamsiDateEdit()
        self.ledger_to_date.setMinimumHeight(self.scaled(32))
        toolbar1.addWidget(self.ledger_to_date)
        
        refresh_btn = self.create_button("🔄 نمایش", "infoBtn")
        refresh_btn.clicked.connect(self.load_ledger)
        toolbar1.addWidget(refresh_btn)
        
        toolbar1.addStretch()
        
        self.ledger_search = self.create_input("جستجو در شرح...")
        self.ledger_search.setMaximumWidth(self.scaled(250))
        self.ledger_search.textChanged.connect(self.filter_ledger)
        toolbar1.addWidget(self.ledger_search)
        
        layout.addLayout(toolbar1)
        
        # ═════ ردیف دوم: دکمه‌های چاپ و خروجی ═════
        toolbar2 = QHBoxLayout()
        toolbar2.setSpacing(self.spacing(8))
        
        info_label = QLabel("📌 خروجی گزارش:")
        info_label.setStyleSheet(
            f"color: {self.get_theme_colors()['text_secondary']}; "
            f"font-size: {self.font_size(10)}pt; font-weight: bold;"
        )
        toolbar2.addWidget(info_label)
        
        print_btn = self.create_button("🖨️ چاپ", "infoBtn")
        print_btn.setMinimumHeight(self.scaled(36))
        print_btn.setToolTip("چاپ دفتر کل")
        print_btn.clicked.connect(self.print_ledger)
        toolbar2.addWidget(print_btn)
        
        pdf_btn = self.create_button("📄 خروجی PDF", "successBtn")
        pdf_btn.setMinimumHeight(self.scaled(36))
        pdf_btn.setToolTip("ذخیره PDF دفتر کل")
        pdf_btn.clicked.connect(self.save_ledger_pdf)
        toolbar2.addWidget(pdf_btn)
        
        csv_btn = self.create_button("📎 خروجی Excel", "warningBtn")
        csv_btn.setMinimumHeight(self.scaled(36))
        csv_btn.setToolTip("ذخیره CSV")
        csv_btn.clicked.connect(self.export_ledger)
        toolbar2.addWidget(csv_btn)
        
        toolbar2.addStretch()
        layout.addLayout(toolbar2)
        
        # ═════ جدول ═════
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
            logger.warning(f"خطا: {e}")
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
            'asset': '🏦 دارایی', 'liability': '📋 بدهی',
            'equity': '💰 سرمایه', 'income': '📈 درآمد', 'expense': '💸 هزینه'
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
            filtered = [
                row for row in self.ledger_data
                if (text in str(row.get('description', '')).lower()
                    or text in str(row.get('account_name', '')).lower()
                    or text in str(row.get('account_code', '')).lower())
            ]
            self.display_ledger(filtered)
    
    def print_ledger(self):
        """چاپ دفتر کل"""
        account_code = self.ledger_account_combo.currentData()
        account_name = self.ledger_account_combo.currentText()
        
        if account_code:
            if not self.ledger_data:
                QMessageBox.warning(self, "خطا", "داده‌ای برای چاپ وجود ندارد!")
                return
            
            headers = ["ردیف", "تاریخ", "شماره سند", "شرح", "بدهکار", "بستانکار", "مانده"]
            
            rows = []
            total_debit = 0
            total_credit = 0
            balance = 0
            
            for i, row in enumerate(self.ledger_data, 1):
                debit = row['debit'] or 0
                credit = row['credit'] or 0
                total_debit += debit
                total_credit += credit
                balance = total_debit - total_credit
                
                rows.append([
                    i,
                    safe_display_date(row['date']),
                    row['voucher_no'],
                    row['description'] or '',
                    f"{debit:,.0f}" if debit else "-",
                    f"{credit:,.0f}" if credit else "-",
                    f"{balance:,.0f}",
                ])
            
            totals = ["", "", "", "جمع کل", f"{total_debit:,.0f}",
                     f"{total_credit:,.0f}", f"{balance:,.0f}"]
        else:
            if not self.ledger_summary_data:
                QMessageBox.warning(self, "خطا", "داده‌ای برای چاپ وجود ندارد!")
                return
            
            headers = ["ردیف", "کد حساب", "نام حساب", "نوع", "بدهکار", "بستانکار"]
            
            type_map = {
                'asset': 'دارایی', 'liability': 'بدهی',
                'equity': 'سرمایه', 'income': 'درآمد', 'expense': 'هزینه'
            }
            
            rows = []
            total_debit = 0
            total_credit = 0
            
            for i, row in enumerate(self.ledger_summary_data, 1):
                debit = row['total_debit'] or 0
                credit = row['total_credit'] or 0
                total_debit += debit
                total_credit += credit
                
                rows.append([
                    i,
                    row['code'],
                    row['name'],
                    type_map.get(row['type'], row['type']),
                    f"{debit:,.0f}" if debit else "-",
                    f"{credit:,.0f}" if credit else "-",
                ])
            
            totals = ["", "", "جمع کل", "", f"{total_debit:,.0f}", f"{total_credit:,.0f}"]
        
        try:
            from_date = self.ledger_from_date.get_shamsi()
            to_date = self.ledger_to_date.get_shamsi()
            
            html = self.pdf_generator.generate_table_html(
                "دفتر کل",
                f"حساب: {account_name} | از {from_date} تا {to_date}",
                headers, rows, totals
            )
            
            AccountingPDFGenerator.print_html(html, self)
        except Exception as e:
            logger.error(f"خطا در چاپ: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ خطا در چاپ: {str(e)}")
    
    def save_ledger_pdf(self):
        """ذخیره PDF دفتر کل"""
        account_code = self.ledger_account_combo.currentData()
        account_name = self.ledger_account_combo.currentText()
        
        if account_code and not self.ledger_data:
            QMessageBox.warning(self, "خطا", "داده‌ای برای ذخیره وجود ندارد!")
            return
        
        if not account_code and not self.ledger_summary_data:
            QMessageBox.warning(self, "خطا", "داده‌ای برای ذخیره وجود ندارد!")
            return
        
        from_date = self.ledger_from_date.get_shamsi()
        to_date = self.ledger_to_date.get_shamsi()
        
        # نام امن برای فایل
        safe_account_name = account_name.replace('/', '_').replace(' ', '_').replace('-', '_')
        default_name = f"دفتر_کل_{safe_account_name}_{from_date}_تا_{to_date}.pdf"
        default_name = default_name.replace('/', '_')
        
        file_path = AccountingPDFGenerator.ask_save_path(self, default_name)
        if not file_path:
            return
        
        try:
            if account_code:
                data = [dict(row) for row in self.ledger_data]
                is_summary = False
            else:
                data = [dict(row) for row in self.ledger_summary_data]
                is_summary = True
            
            success = self.pdf_generator.generate_ledger_pdf(
                data, account_name, from_date, to_date,
                file_path, is_summary=is_summary
            )
            
            if success:
                QMessageBox.information(
                    self, "موفق",
                    f"✅ PDF دفتر کل ذخیره شد:\n{file_path}"
                )
            else:
                QMessageBox.warning(self, "خطا", "❌ خطا در تولید PDF!")
        except Exception as e:
            logger.error(f"خطا در PDF: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    def export_ledger(self):
        account_name = self.ledger_account_combo.currentText()
        if not account_name or account_name == "-- همه حساب‌ها --":
            account_name = "همه_حساب‌ها"
        
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره دفتر کل",
            f"دفتر_کل_{account_name}.csv",
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
                
                QMessageBox.information(self, "موفق", "✅ ذخیره شد!")
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ {str(e)}")


# ═══════════════════════════════════════════════════════════
# دیالوگ سند حسابداری
# ═══════════════════════════════════════════════════════════

class VoucherDialog(BaseDialog):
    """دیالوگ سند با جستجوی حساب بالای جدول + چاپ و PDF"""
    
    def __init__(self, accounts, voucher_id=None, customer_name="",
                 suggested_account=None, coding=None):
        self.screen_manager = ScreenManager()
        self.scale = self.screen_manager.scale
        self.is_small_screen = self.screen_manager.is_small_screen()
        
        super().__init__(base_width=1000, base_height=750)
        
        self.accounts = accounts
        self.voucher_id = voucher_id
        self.customer_name = customer_name
        self.suggested_account = suggested_account
        self.coding = coding or CodingStructure()
        
        # PDF Generator
        self.company_info = _get_company_info()
        self.pdf_generator = get_pdf_generator(self.company_info)
        
        self.setWindowTitle("📄 سند حسابداری")
        self.setModal(True)
        
        self.setup_ui()
        
        if voucher_id:
            self.load_voucher_data()
        if suggested_account:
            self._apply_suggestion()
        
        self.apply_theme()
        self._apply_dialog_theme()
    
    # ═══════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def scaled(self, value: int) -> int:
        return self.screen_manager.get_scaled(value)
    
    def font_size(self, size: int) -> int:
        return self.screen_manager.get_font_size(size)
    
    def spacing(self, value: int = 10) -> int:
        return self.screen_manager.get_spacing(value)
    
    def margin(self, value: int = 10) -> int:
        return self.screen_manager.get_margin(value)
    
    def padding(self, value: int = 10) -> int:
        return self.screen_manager.get_padding(value)
    
    def create_button(self, text: str, object_name: str = "") -> QPushButton:
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        btn.setMinimumHeight(self.scaled(36))
        return btn
    
    # ═══════════════════════════════════════════════════════════
    # UI Setup
    # ═══════════════════════════════════════════════════════════
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(10))
        layout.setContentsMargins(
            self.margin(15), self.margin(15), self.margin(15), self.margin(15)
        )
        
        # اطلاعات سند
        info_group = QGroupBox("📋 اطلاعات سند")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(self.spacing(10))
        info_layout.setLabelAlignment(Qt.AlignRight)
        info_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        no_layout = QHBoxLayout()
        no_layout.setSpacing(self.spacing(8))
        
        self.voucher_no = QSpinBox()
        self.voucher_no.setRange(1, 999999)
        self.voucher_no.setMinimumHeight(self.scaled(38))
        self.voucher_no.setMinimumWidth(self.scaled(120))
        font = self.voucher_no.font()
        font.setPointSize(self.font_size(11))
        self.voucher_no.setFont(font)
        if not self.voucher_id:
            self.voucher_no.setValue(self.get_next_voucher_no())
        no_layout.addWidget(self.voucher_no)
        
        auto_no_btn = self.create_button("🔢 خودکار")
        auto_no_btn.setMinimumHeight(self.scaled(38))
        auto_no_btn.clicked.connect(
            lambda: self.voucher_no.setValue(self.get_next_voucher_no())
        )
        no_layout.addWidget(auto_no_btn)
        no_layout.addStretch()
        info_layout.addRow("شماره سند:", no_layout)
        
        self.date = ShamsiDateEdit()
        self.date.setMinimumHeight(self.scaled(38))
        info_layout.addRow("تاریخ:", self.date)
        
        self.description = QTextEdit()
        self.description.setMaximumHeight(self.scaled(70))
        self.description.setMinimumHeight(self.scaled(60))
        self.description.setPlaceholderText("شرح سند را وارد کنید...")
        info_layout.addRow("شرح:", self.description)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["عادی", "افتتاحیه", "اختتامیه", "اصلاحی"])
        self.type_combo.setMinimumHeight(self.scaled(38))
        info_layout.addRow("نوع سند:", self.type_combo)
        
        layout.addWidget(info_group)
        
        # اقلام سند
        items_group = QGroupBox("📦 اقلام سند")
        items_layout = QVBoxLayout(items_group)
        items_layout.setSpacing(self.spacing(10))
        
        # بخش جستجو
        search_group = QGroupBox("🔍 جستجو و افزودن حساب")
        search_group.setStyleSheet(f"""
            QGroupBox {{
                background: rgba(25,118,210,0.08);
                border: 2px solid rgba(25,118,210,0.3);
                border-radius: 10px;
                margin-top: {self.margin(12)}px;
                padding: {self.padding(12)}px;
                font-weight: bold;
                font-size: {self.font_size(11)}pt;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top right;
                right: {self.margin(12)}px;
                padding: 0 {self.padding(8)}px;
                color: #1976D2;
                background: {self.get_theme_colors()['bg']};
            }}
        """)
        
        search_layout = QVBoxLayout(search_group)
        search_layout.setSpacing(self.spacing(6))
        
        hint_label = QLabel(
            "💡 کد یا نام حساب را تایپ کنید | ↑↓ جابجایی | Enter انتخاب | دکمه افزودن"
        )
        hint_label.setStyleSheet(
            f"color: #666; font-size: {self.font_size(9)}pt; "
            f"padding: {self.padding(4)}px; background: transparent;"
        )
        search_layout.addWidget(hint_label)
        
        search_row = QHBoxLayout()
        search_row.setSpacing(self.spacing(8))
        
        self.account_search = AccountSearchBox(self.accounts, self)
        self.account_search.account_selected.connect(self.on_account_selected)
        search_row.addWidget(self.account_search, 1)
        
        add_btn = self.create_button("➕ افزودن به سند", "successBtn")
        add_btn.setMinimumHeight(self.scaled(40))
        add_btn.setMinimumWidth(self.scaled(170))
        add_btn.clicked.connect(self.add_selected_account)
        search_row.addWidget(add_btn)
        
        clear_search_btn = self.create_button("🧹 پاک", "warningBtn")
        clear_search_btn.setMinimumHeight(self.scaled(40))
        clear_search_btn.setFixedWidth(self.scaled(80))
        clear_search_btn.clicked.connect(self.clear_search)
        search_row.addWidget(clear_search_btn)
        
        search_layout.addLayout(search_row)
        items_layout.addWidget(search_group)
        
        # جدول اقلام
        table_label = QLabel("📋 اقلام اضافه شده:")
        table_label.setStyleSheet(
            f"font-weight: bold; font-size: {self.font_size(10)}pt; "
            f"color: {self.get_theme_colors()['text']}; padding: 4px;"
        )
        items_layout.addWidget(table_label)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(
            ["کد حساب", "نام حساب", "شرح", "بدهکار", "بستانکار"]
        )
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.items_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.items_table.verticalHeader().setDefaultSectionSize(self.scaled(38))
        self.items_table.horizontalHeader().setStretchLastSection(True)
        
        self.items_table.setColumnWidth(0, self.scaled(150))
        self.items_table.setColumnWidth(1, self.scaled(220))
        self.items_table.setColumnWidth(2, self.scaled(250))
        self.items_table.setColumnWidth(3, self.scaled(120))
        self.items_table.setColumnWidth(4, self.scaled(120))
        
        self.items_table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )
        self.items_table.cellChanged.connect(self.update_totals)
        self.items_table.setMinimumHeight(self.scaled(200))
        
        items_layout.addWidget(self.items_table)
        
        # دکمه‌های عملیات
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(self.spacing(8))
        
        remove_btn = self.create_button("➖ حذف ردیف", "dangerBtn")
        remove_btn.clicked.connect(self.remove_item_row)
        btn_layout.addWidget(remove_btn)
        
        duplicate_btn = self.create_button("📋 کپی ردیف", "infoBtn")
        duplicate_btn.clicked.connect(self.duplicate_item_row)
        btn_layout.addWidget(duplicate_btn)
        
        print_btn = self.create_button("🖨️ چاپ سند", "infoBtn")
        print_btn.clicked.connect(self.print_voucher)
        btn_layout.addWidget(print_btn)
        
        pdf_btn = self.create_button("📄 PDF", "successBtn")
        pdf_btn.clicked.connect(self.save_pdf)
        btn_layout.addWidget(pdf_btn)
        
        btn_layout.addStretch()
        
        self.total_label = QLabel("جمع بدهکار: ۰ | جمع بستانکار: ۰")
        btn_layout.addWidget(self.total_label)
        
        items_layout.addLayout(btn_layout)
        layout.addWidget(items_group)
        
        # دکمه‌های دیالوگ
        dialog_btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        dialog_btns.accepted.connect(self.accept)
        dialog_btns.rejected.connect(self.reject)
        
        for btn in dialog_btns.buttons():
            btn.setMinimumHeight(self.scaled(40))
            btn.setMinimumWidth(self.scaled(110))
            font = btn.font()
            font.setPointSize(self.font_size(11))
            font.setBold(True)
            btn.setFont(font)
        
        layout.addWidget(dialog_btns)
    
    # ═══════════════════════════════════════════════════════════
    # توابع کمکی
    # ═══════════════════════════════════════════════════════════
    
    def get_next_voucher_no(self):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute('SELECT MAX(voucher_no) FROM vouchers')
            max_no = cur.fetchone()[0]
            return 1 if max_no is None else max_no + 1
    
    def on_account_selected(self, code):
        pass
    
    def add_selected_account(self):
        code = self.account_search.get_code()
        
        if not code:
            QMessageBox.warning(self, "خطا", "ابتدا یک حساب انتخاب کنید!")
            return
        
        account = next(
            (a for a in self.accounts if a['code'] == code),
            None
        )
        
        if not account:
            QMessageBox.warning(self, "خطا", "حساب پیدا نشد!")
            return
        
        for row in range(self.items_table.rowCount()):
            code_item = self.items_table.item(row, 0)
            if code_item and code_item.text() == code:
                reply = QMessageBox.question(
                    self, "تکراری",
                    f"حساب '{code}' قبلاً در سند هست!\n"
                    f"آیا می‌خواهید دوباره اضافه کنید؟",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
                break
        
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        self.items_table.setRowHeight(row, self.scaled(38))
        
        font = QFont("Tahoma", self.font_size(10))
        
        code_item = QTableWidgetItem(code)
        code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)
        code_item.setFont(font)
        self.items_table.setItem(row, 0, code_item)
        
        name_item = QTableWidgetItem(account['name'])
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        name_item.setFont(font)
        self.items_table.setItem(row, 1, name_item)
        
        desc_item = QTableWidgetItem("")
        desc_item.setFlags(desc_item.flags() | Qt.ItemIsEditable)
        desc_item.setFont(font)
        self.items_table.setItem(row, 2, desc_item)
        
        debit_item = QTableWidgetItem("0")
        debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        debit_item.setFlags(debit_item.flags() | Qt.ItemIsEditable)
        debit_item.setFont(font)
        self.items_table.setItem(row, 3, debit_item)
        
        credit_item = QTableWidgetItem("0")
        credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        credit_item.setFlags(credit_item.flags() | Qt.ItemIsEditable)
        credit_item.setFont(font)
        self.items_table.setItem(row, 4, credit_item)
        
        self.clear_search()
        self.items_table.setCurrentCell(row, 3)
        QTimer.singleShot(100, lambda: self._focus_debit(row))
    
    def clear_search(self):
        self.account_search.clear()
        self.account_search.line_edit.setFocus()
    
    def _focus_debit(self, row):
        try:
            self.items_table.setCurrentCell(row, 3)
            self.items_table.editItem(self.items_table.item(row, 3))
        except Exception:
            pass
    
    def duplicate_item_row(self):
        row = self.items_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک ردیف انتخاب کنید!")
            return
        
        code_item = self.items_table.item(row, 0)
        if not code_item:
            return
        code = code_item.text()
        
        account = next((a for a in self.accounts if a['code'] == code), None)
        if not account:
            return
        
        old_desc = self.items_table.item(row, 2)
        old_debit = self.items_table.item(row, 3)
        old_credit = self.items_table.item(row, 4)
        
        new_row = self.items_table.rowCount()
        self.items_table.insertRow(new_row)
        self.items_table.setRowHeight(new_row, self.scaled(38))
        
        font = QFont("Tahoma", self.font_size(10))
        
        new_code = QTableWidgetItem(code)
        new_code.setFlags(new_code.flags() & ~Qt.ItemIsEditable)
        new_code.setFont(font)
        self.items_table.setItem(new_row, 0, new_code)
        
        new_name = QTableWidgetItem(account['name'])
        new_name.setFlags(new_name.flags() & ~Qt.ItemIsEditable)
        new_name.setFont(font)
        self.items_table.setItem(new_row, 1, new_name)
        
        for col, old_item in [(2, old_desc), (3, old_debit), (4, old_credit)]:
            text = old_item.text() if old_item else ("0" if col >= 3 else "")
            new_item = QTableWidgetItem(text)
            if col >= 3:
                new_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)
            new_item.setFont(font)
            self.items_table.setItem(new_row, col, new_item)
        
        self.update_totals()
    
    def remove_item_row(self):
        rows = set()
        for index in self.items_table.selectedIndexes():
            rows.add(index.row())
        
        if not rows:
            QMessageBox.warning(self, "خطا", "یک ردیف انتخاب کنید!")
            return
        
        for row in sorted(rows, reverse=True):
            self.items_table.removeRow(row)
        
        self.update_totals()
    
    # ═══════════════════════════════════════════════════════════
    # محاسبات
    # ═══════════════════════════════════════════════════════════
    
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
        
        if abs(total_debit - total_credit) < 1 and total_debit > 0:
            self.total_label.setStyleSheet(f"""
                background: {c['success']};
                color: #ffffff;
                padding: {self.padding(10)}px {self.padding(16)}px;
                border-radius: 6px;
                font-weight: bold;
                font-size: {self.font_size(11)}pt;
            """)
        else:
            self.total_label.setStyleSheet(f"""
                background: {c['danger']};
                color: #ffffff;
                padding: {self.padding(10)}px {self.padding(16)}px;
                border-radius: 6px;
                font-weight: bold;
                font-size: {self.font_size(11)}pt;
            """)
        
        return total_debit, total_credit
    
    # ═══════════════════════════════════════════════════════════
    # بارگذاری
    # ═══════════════════════════════════════════════════════════
    
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
                
                font = QFont("Tahoma", self.font_size(10))
                
                for item in items:
                    row = self.items_table.rowCount()
                    self.items_table.insertRow(row)
                    self.items_table.setRowHeight(row, self.scaled(38))
                    
                    code_item = QTableWidgetItem(item['account_code'])
                    code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)
                    code_item.setFont(font)
                    self.items_table.setItem(row, 0, code_item)
                    
                    account = next(
                        (a for a in self.accounts if a['code'] == item['account_code']),
                        None
                    )
                    name_text = account['name'] if account else "-"
                    name_item = QTableWidgetItem(name_text)
                    name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                    name_item.setFont(font)
                    self.items_table.setItem(row, 1, name_item)
                    
                    desc_item = QTableWidgetItem(item['description'] or "")
                    desc_item.setFlags(desc_item.flags() | Qt.ItemIsEditable)
                    desc_item.setFont(font)
                    self.items_table.setItem(row, 2, desc_item)
                    
                    debit_item = QTableWidgetItem(
                        f"{item['debit']:,.0f}" if item['debit'] else "0"
                    )
                    debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    debit_item.setFlags(debit_item.flags() | Qt.ItemIsEditable)
                    debit_item.setFont(font)
                    self.items_table.setItem(row, 3, debit_item)
                    
                    credit_item = QTableWidgetItem(
                        f"{item['credit']:,.0f}" if item['credit'] else "0"
                    )
                    credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    credit_item.setFlags(credit_item.flags() | Qt.ItemIsEditable)
                    credit_item.setFont(font)
                    self.items_table.setItem(row, 4, credit_item)
                
                self.update_totals()
        except Exception as e:
            logger.warning(f"خطا: {e}")
    
    def _apply_suggestion(self):
        if self.suggested_account and self.suggested_account.get("success"):
            account_code = self.suggested_account.get("account_code")
            if account_code:
                self.account_search.set_code(account_code)
                self.add_selected_account()
    
    # ═══════════════════════════════════════════════════════════
    # چاپ و PDF
    # ═══════════════════════════════════════════════════════════
    
    def _get_current_data(self):
        voucher = {
            'voucher_no': self.voucher_no.value(),
            'date': self.date.get_shamsi(),
            'description': self.description.toPlainText().strip(),
            'type': self.type_combo.currentText(),
        }
        
        items = []
        for row in range(self.items_table.rowCount()):
            code_item = self.items_table.item(row, 0)
            if not code_item:
                continue
            
            try:
                debit = float(
                    (self.items_table.item(row, 3).text().replace(',', '').strip() or "0")
                )
                credit = float(
                    (self.items_table.item(row, 4).text().replace(',', '').strip() or "0")
                )
            except Exception:
                debit = 0
                credit = 0
            
            items.append({
                'account_code': code_item.text(),
                'account_name': self.items_table.item(row, 1).text() if self.items_table.item(row, 1) else '',
                'description': self.items_table.item(row, 2).text() if self.items_table.item(row, 2) else '',
                'debit': debit,
                'credit': credit,
            })
        
        return voucher, items
    
    def print_voucher(self):
        voucher, items = self._get_current_data()
        
        if not items:
            QMessageBox.warning(self, "خطا", "هیچ ردیفی برای چاپ وجود ندارد!")
            return
        
        try:
            html = self.pdf_generator.generate_voucher_html(voucher, items)
            AccountingPDFGenerator.print_html(html, self)
        except Exception as e:
            logger.error(f"خطا در چاپ: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ خطا در چاپ: {str(e)}")
    
    def save_pdf(self):
        voucher, items = self._get_current_data()
        
        if not items:
            QMessageBox.warning(self, "خطا", "هیچ ردیفی برای ذخیره وجود ندارد!")
            return
        
        default_name = f"سند_{voucher['voucher_no']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        file_path = AccountingPDFGenerator.ask_save_path(self, default_name)
        if not file_path:
            return
        
        try:
            success = self.pdf_generator.generate_voucher_pdf(
                voucher, items, file_path
            )
            
            if success:
                QMessageBox.information(
                    self, "موفق",
                    f"✅ PDF سند ذخیره شد:\n{file_path}"
                )
            else:
                QMessageBox.warning(self, "خطا", "❌ خطا در تولید PDF!")
        except Exception as e:
            logger.error(f"خطا در PDF: {e}", exc_info=True)
            QMessageBox.warning(self, "خطا", f"❌ {str(e)}")
    
    # ═══════════════════════════════════════════════════════════
    # ذخیره
    # ═══════════════════════════════════════════════════════════
    
    def accept(self):
        if not self.description.toPlainText().strip():
            QMessageBox.warning(self, "خطا", "شرح سند را وارد کنید!")
            return
        
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "حداقل یک ردیف!")
            return
        
        total_debit, total_credit = self.update_totals()
        items_data = []
        
        for row in range(self.items_table.rowCount()):
            code_item = self.items_table.item(row, 0)
            if not code_item:
                continue
            
            account_code = code_item.text().strip()
            if not account_code:
                continue
            
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
                    self, "خطا", f"مقادیر عددی ردیف {row+1} نامعتبر!"
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
            QMessageBox.warning(self, "خطا", "حداقل یک ردیف معتبر!")
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
            
            QMessageBox.information(self, "موفق", "✅ سند ذخیره شد!")
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"خطا: {str(e)}")
    
    # ═══════════════════════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════════════════════
    
    def _apply_dialog_theme(self):
        try:
            c = self.get_theme_colors()
            font_sz = self.font_size(10)
            
            self.setStyleSheet(f"""
                QDialog {{
                    background: {c['bg']};
                    color: {c['text']};
                    font-size: {font_sz}pt;
                }}
            """)
            
            for gb in self.findChildren(QGroupBox):
                if gb.title() == "🔍 جستجو و افزودن حساب":
                    continue
                gb.setStyleSheet(f"""
                    QGroupBox {{
                        background: {c['card']};
                        color: {c['text']};
                        border: 2px solid {c['border']};
                        border-radius: 8px;
                        margin-top: {self.margin(15)}px;
                        padding: {self.padding(15)}px {self.padding(10)}px {self.padding(10)}px {self.padding(10)}px;
                        font-weight: bold;
                        font-size: {self.font_size(11)}pt;
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        subcontrol-position: top right;
                        right: {self.margin(15)}px;
                        padding: 0 {self.padding(8)}px;
                        color: {c['selected']};
                        background: {c['bg']};
                    }}
                """)
            
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
                        font-size: {font_sz}pt;
                    }}
                    QTableWidget::item {{
                        padding: {self.padding(6)}px;
                    }}
                    QTableWidget::item:selected {{
                        background: {c['selected']};
                        color: {c['selected_text']};
                    }}
                    QHeaderView::section {{
                        background: {c['card']};
                        color: {c['text']};
                        padding: {self.padding(8)}px;
                        border: none;
                        border-right: 1px solid {c['border']};
                        border-bottom: 1px solid {c['border']};
                        font-weight: bold;
                        font-size: {font_sz}pt;
                    }}
                """)
            
            for te in self.findChildren(QTextEdit):
                te.setStyleSheet(f"""
                    QTextEdit {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: {self.padding(6)}px;
                        font-size: {font_sz}pt;
                    }}
                    QTextEdit:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
            for cb in self.findChildren(QComboBox):
                cb.setStyleSheet(f"""
                    QComboBox {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: {self.padding(6)}px {self.padding(10)}px;
                        min-height: {self.scaled(28)}px;
                        font-size: {font_sz}pt;
                    }}
                    QComboBox:focus {{
                        border: 2px solid {c['selected']};
                    }}
                    QComboBox QAbstractItemView {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        selection-background-color: {c['selected']};
                        selection-color: {c['selected_text']};
                        font-size: {font_sz}pt;
                    }}
                """)
            
            for sb in self.findChildren((QSpinBox, QDoubleSpinBox)):
                sb.setStyleSheet(f"""
                    QSpinBox, QDoubleSpinBox {{
                        background: {c['bg_alt']};
                        color: {c['text']};
                        border: 1px solid {c['border']};
                        border-radius: 6px;
                        padding: {self.padding(6)}px;
                        min-height: {self.scaled(28)}px;
                        font-size: {font_sz}pt;
                    }}
                    QSpinBox:focus, QDoubleSpinBox:focus {{
                        border: 2px solid {c['selected']};
                    }}
                """)
            
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
                            padding: {self.padding(8)}px {self.padding(16)}px;
                            font-weight: bold;
                            min-height: {self.scaled(32)}px;
                            font-size: {font_sz}pt;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                            color: {c['text']};
                        }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {c['bg_alt']};
                            color: {c['text']};
                            border: 1px solid {c['border']};
                            border-radius: 6px;
                            padding: {self.padding(8)}px {self.padding(16)}px;
                            font-weight: bold;
                            min-height: {self.scaled(32)}px;
                            font-size: {font_sz}pt;
                        }}
                        QPushButton:hover {{
                            background: {c['hover']};
                            border: 1px solid {c['selected']};
                        }}
                    """)
            
            for lbl in self.findChildren(QLabel):
                if not lbl.styleSheet() or 'background' not in lbl.styleSheet():
                    lbl.setStyleSheet(
                        f"color: {c['text']}; background: transparent; "
                        f"padding: {self.padding(3)}px; font-size: {font_sz}pt;"
                    )
            
            if hasattr(self, 'total_label'):
                self.total_label.setStyleSheet(f"""
                    background: {c['card']};
                    color: {c['text']};
                    padding: {self.padding(10)}px {self.padding(16)}px;
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: {self.font_size(11)}pt;
                """)
        
        except Exception as e:
            print(f"⚠️ خطا theme: {e}")
            import traceback
            traceback.print_exc()
