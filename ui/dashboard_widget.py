# ui/dashboard_widget.py
# ============================================================
# داشبورد مدیریتی با نمودارها و تحلیل‌های پیشرفته
# تمام تاریخ‌ها به صورت شمسی نمایش داده می‌شوند
# پشتیبانی کامل از تم (روشن/تاریک)
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtChart import (
    QChart, QChartView, QPieSeries, QPieSlice,
    QBarSeries, QBarSet, QBarCategoryAxis,
    QLineSeries, QValueAxis, QCategoryAxis,
    QLegend
)
from ui.base_widgets import BaseWidget
from database import get_db
from datetime import datetime, timedelta
from shamsi_date import (
    safe_display_date, 
    get_today_jalali, 
    ShamsiDateEdit, 
    shamsi_to_gregorian, 
    gregorian_to_shamsi
)
import random


class DashboardWidget(BaseWidget):
    """داشبورد مدیریتی با نمودارها و تحلیل‌های پیشرفته و پشتیبانی از سطح دسترسی"""
    
    def __init__(self, user_level: str = 'viewer', parent=None):
        super().__init__(parent)
        self.user_level = user_level
        self._colors = {}
        self._is_dark = False
        
        self.setup_ui()
        self.load_data()
        self.update_ui_by_permission()
        self.apply_theme()
        
        # تایمر بروزرسانی (هر ۲ دقیقه)
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_data)
        self.timer.start(120000)
        
        # اتصال به تغییر تم
        self.theme_manager.add_observer(self.on_theme_changed)
    
    # ============================================================
    # مدیریت تم
    # ============================================================
    
    def on_theme_changed(self, theme_name: str):
        """هنگام تغییر تم - به‌روزرسانی کامل داشبورد"""
        self.apply_theme()
        self.load_data()
    
    def get_theme_colors(self):
        """دریافت رنگ‌های بر اساس تم فعلی"""
        theme_name = self.theme_manager.get_theme_name() if hasattr(self, 'theme_manager') else 'light'
        self._is_dark = theme_name == 'dark'
        
        if self._is_dark:
            self._colors = {
                'bg': "#1a1a2e",
                'bg_secondary': "#16213e",
                'bg_tertiary': "#0f0f23",
                'text': "#e8e8e8",
                'text_secondary': "#a0a0a0",
                'text_tertiary': "#666666",
                'card': "#1a1a2e",
                'card_alt': "#16213e",
                'border': "#2a2a4a",
                'hover': "#2a2a4a",
                'selected': "#e94560",
                'selected_text': "#ffffff",
                'header_bg': "#0f3460",
                'header_text': "#ffffff",
                'shadow': "rgba(0,0,0,0.3)",
                'success': "#27ae60",
                'danger': "#e74c3c",
                'warning': "#f39c12",
                'info': "#3498db",
                'purple': "#8e44ad",
            }
        else:
            self._colors = {
                'bg': "#f5f6fa",
                'bg_secondary': "#f0f0f0",
                'bg_tertiary': "#e8e8e8",
                'text': "#1a1a2e",
                'text_secondary': "#2c3e50",
                'text_tertiary': "#7f8c8d",
                'card': "#ffffff",
                'card_alt': "#f8f9fa",
                'border': "#dcdde1",
                'hover': "#e8e8e8",
                'selected': "#e94560",
                'selected_text': "#ffffff",
                'header_bg': "#e8e8e8",
                'header_text': "#1a1a2e",
                'shadow': "rgba(0,0,0,0.1)",
                'success': "#27ae60",
                'danger': "#e74c3c",
                'warning': "#f39c12",
                'info': "#3498db",
                'purple': "#8e44ad",
            }
        
        return self._colors
    
    def apply_theme(self):
        """اعمال تم روی داشبورد - کارت‌های KPI رنگ ثابت دارند"""
        colors = self.get_theme_colors()
        
        # ۱. اعمال روی خود ویجت
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['bg']};
                color: {colors['text']};
            }}
            QWidget#cardWidget {{
                background: {colors['card']};
                border-radius: 10px;
                border: 1px solid {colors['border']};
            }}
        """)
        
        # ۲. به‌روزرسانی گروه‌ها
        for widget in self.findChildren(QGroupBox):
            widget.setStyleSheet(f"""
                QGroupBox {{
                    color: {colors['text']};
                    border: 2px solid {colors['border']};
                    border-radius: {self.scaled(8)}px;
                    margin-top: {self.scaled(12)}px;
                    font-weight: bold;
                    padding-top: {self.scaled(10)}px;
                    background-color: {colors['card']};
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: {self.scaled(10)}px;
                    padding: 0 {self.scaled(10)}px;
                    color: {colors['selected']};
                    background-color: {colors['card']};
                }}
            """)
        
        # ۳. به‌روزرسانی info_text
        if hasattr(self, 'info_text'):
            self.info_text.setStyleSheet(f"""
                QTextEdit {{
                    background: {colors['card']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    border-radius: {self.scaled(6)}px;
                    padding: {self.scaled(8)}px;
                    font-size: {self.font_size(9)}pt;
                }}
            """)
        
        # ۴. به‌روزرسانی دکمه‌ها
        for btn in self.findChildren(QPushButton):
            if btn.objectName() == "infoBtn":
                btn.setStyleSheet(f"""
                    QPushButton#infoBtn {{
                        background: {colors['info']};
                        color: white;
                        padding: {self.scaled(8)}px {self.scaled(16)}px;
                        border: none;
                        border-radius: {self.scaled(6)}px;
                        font-weight: bold;
                    }}
                    QPushButton#infoBtn:hover {{
                        background: {colors['info']}CC;
                    }}
                """)
        
        # ۵. به‌روزرسانی لیبل‌ها
        for label in self.findChildren(QLabel):
            if label.objectName() == "titleLabel":
                label.setStyleSheet(f"""
                    color: {colors['text']};
                    font-size: {self.font_size(16)}pt;
                    font-weight: bold;
                    padding: {self.scaled(10)}px;
                """)
            elif label.objectName() == "valueLabel":
                # کارت‌های KPI استایل خودشون رو دارن (رنگ ثابت)
                pass
            else:
                label.setStyleSheet(f"""
                    color: {colors['text']};
                    font-size: {self.font_size(10)}pt;
                    padding: {self.scaled(4)}px;
                """)
        
        # ۶. به‌روزرسانی نمودارها
        for chart_view in self.findChildren(QChartView):
            chart_view.setStyleSheet("background: transparent; border: none;")
            if chart_view.chart():
                chart_view.chart().setBackgroundBrush(QColor(colors['card']))
                chart_view.chart().setTheme(self._get_chart_theme())
        
        # ۷. کارت‌های KPI - رنگ‌های ثابت (دست نمی‌زنیم)
        # این کارت‌ها در _create_kpi_card با رنگ‌های ثابت ساخته شده‌اند
        # و نیازی به به‌روزرسانی ندارند
    
    def _get_chart_theme(self):
        """دریافت تم مناسب برای نمودارها"""
        if self._is_dark:
            return QChart.ChartThemeDark
        return QChart.ChartThemeLight
    
    # ============================================================
    # رابط کاربری
    # ============================================================
    
    def set_user_level(self, level: str):
        """تنظیم سطح دسترسی"""
        self.user_level = level
        self.update_ui_by_permission()
        self.load_data()
    
    def update_ui_by_permission(self):
        """بروزرسانی UI بر اساس سطح دسترسی"""
        is_admin = self.user_level == 'admin'
        is_accountant = self.user_level in ['admin', 'accountant']
        
        if hasattr(self, 'sales_card'):
            self.sales_card.setVisible(is_accountant)
        if hasattr(self, 'profit_card'):
            self.profit_card.setVisible(is_accountant)
        if hasattr(self, 'invoice_card'):
            self.invoice_card.setVisible(is_accountant)
        if hasattr(self, 'cash_card'):
            self.cash_card.setVisible(is_admin or is_accountant)
        if hasattr(self, 'bank_card'):
            self.bank_card.setVisible(is_admin or is_accountant)
        
        if hasattr(self, 'info_text'):
            if not is_admin:
                self.info_text.setHtml(self.info_text.toHtml().replace("📊 **آمار سیستم:**", "📊 **آمار عمومی:**"))
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.spacing(15))
        layout.setContentsMargins(self.margin(20), self.margin(15), 
                                  self.margin(20), self.margin(15))
        
        # ====== عنوان ======
        title_layout = QHBoxLayout()
        title = QLabel("📊 داشبورد مدیریت")
        title.setObjectName("titleLabel")
        title_layout.addWidget(title)
        
        refresh_btn = self.create_button("🔄 بروزرسانی", "infoBtn")
        refresh_btn.clicked.connect(self.load_data)
        title_layout.addStretch()
        title_layout.addWidget(refresh_btn)
        
        today_label = QLabel(f"📅 {get_today_jalali()}")
        today_label.setStyleSheet(f"color: #666; font-size: {self.font_size(10)}pt;")
        title_layout.addWidget(today_label)
        
        layout.addLayout(title_layout)
        
        # ====== کارت‌های KPI (رنگ‌های ثابت) ======
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(self.spacing(15))
        
        self.cash_card = self._create_kpi_card("💰 موجودی نقد", "0 ریال", "#27ae60")
        self.bank_card = self._create_kpi_card("🏦 موجودی بانک", "0 ریال", "#2980b9")
        self.sales_card = self._create_kpi_card("📈 فروش امروز", "0 ریال", "#f39c12")
        self.profit_card = self._create_kpi_card("📊 سود ماه", "0 ریال", "#e74c3c")
        self.invoice_card = self._create_kpi_card("🧾 فاکتورها", "0", "#8e44ad")
        
        cards_layout.addWidget(self.cash_card)
        cards_layout.addWidget(self.bank_card)
        cards_layout.addWidget(self.sales_card)
        cards_layout.addWidget(self.profit_card)
        cards_layout.addWidget(self.invoice_card)
        layout.addLayout(cards_layout)
        
        # ====== ردیف نمودارها ======
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(self.spacing(15))
        
        self.pie_chart_view = QChartView()
        self.pie_chart_view.setMinimumHeight(self.scaled(250))
        self.pie_chart_view.setRenderHint(QPainter.Antialiasing)
        charts_layout.addWidget(self.pie_chart_view, 1)
        
        self.bar_chart_view = QChartView()
        self.bar_chart_view.setMinimumHeight(self.scaled(250))
        self.bar_chart_view.setRenderHint(QPainter.Antialiasing)
        charts_layout.addWidget(self.bar_chart_view, 2)
        
        layout.addLayout(charts_layout)
        
        # ====== ردیف دوم نمودارها ======
        charts_layout2 = QHBoxLayout()
        charts_layout2.setSpacing(self.spacing(15))
        
        self.line_chart_view = QChartView()
        self.line_chart_view.setMinimumHeight(self.scaled(200))
        self.line_chart_view.setRenderHint(QPainter.Antialiasing)
        charts_layout2.addWidget(self.line_chart_view, 2)
        
        info_group = QGroupBox("📋 اطلاعات سیستم")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(self.scaled(120))
        self.info_text.setStyleSheet("font-size: 9pt;")
        info_layout.addWidget(self.info_text)
        charts_layout2.addWidget(info_group, 1)
        
        layout.addLayout(charts_layout2)
        
        self.apply_theme()
    
    def _create_kpi_card(self, title, value, color):
        """ایجاد کارت KPI با رنگ ثابت (برای خوانایی در هر دو تم)"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: {self.scaled(10)}px;
                padding: {self.scaled(12)}px;
                color: white;
                min-height: {self.scaled(70)}px;
            }}
        """)
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: {self.font_size(10)}pt; font-weight: bold; color: white;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName("valueLabel")
        value_label.setStyleSheet(f"font-size: {self.font_size(14)}pt; font-weight: bold; color: white;")
        value_label.setWordWrap(True)
        layout.addWidget(value_label)
        
        card.value_label = value_label
        return card
    
    # ============================================================
    # بارگذاری داده‌ها - با تاریخ شمسی
    # ============================================================
    
    def load_data(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                # ====== موجودی صندوق ======
                c.execute("""
                    SELECT COALESCE(SUM(debit - credit), 0) 
                    FROM voucher_items vi 
                    JOIN accounts a ON vi.account_code = a.code 
                    WHERE a.code = '1101'
                """)
                cash = c.fetchone()[0] or 0
                self.cash_card.value_label.setText(f"{cash:,.0f} ریال")
                
                # ====== موجودی بانک ======
                c.execute("""
                    SELECT COALESCE(SUM(debit - credit), 0) 
                    FROM voucher_items vi 
                    JOIN accounts a ON vi.account_code = a.code 
                    WHERE a.code = '1102'
                """)
                bank = c.fetchone()[0] or 0
                self.bank_card.value_label.setText(f"{bank:,.0f} ریال")
                
                # ====== فروش امروز (شمسی) ======
                today_jalali = get_today_jalali()
                today_gregorian = shamsi_to_gregorian(today_jalali)
                
                c.execute("""
                    SELECT COALESCE(SUM(net_amount), 0) 
                    FROM documents 
                    WHERE doc_type = 'sales' AND date = ?
                """, [today_gregorian])
                sales = c.fetchone()[0] or 0
                self.sales_card.value_label.setText(f"{sales:,.0f} ریال")
                
                # ====== تعداد فاکتورها ======
                c.execute("SELECT COUNT(*) FROM documents WHERE doc_type = 'sales'")
                invoice_count = c.fetchone()[0] or 0
                self.invoice_card.value_label.setText(f"{invoice_count:,} عدد")
                
                # ====== سود ماه (شمسی) ======
                parts = today_jalali.split('/')
                month_start_jalali = f"{parts[0]}/{parts[1]}/01"
                month_start_gregorian = shamsi_to_gregorian(month_start_jalali)
                
                c.execute("""
                    SELECT COALESCE(SUM(credit - debit), 0) 
                    FROM voucher_items vi 
                    JOIN vouchers v ON vi.voucher_id = v.id 
                    JOIN accounts a ON vi.account_code = a.code 
                    WHERE a.type = 'income' AND v.date >= ?
                """, [month_start_gregorian])
                income = c.fetchone()[0] or 0
                
                c.execute("""
                    SELECT COALESCE(SUM(debit - credit), 0) 
                    FROM voucher_items vi 
                    JOIN vouchers v ON vi.voucher_id = v.id 
                    JOIN accounts a ON vi.account_code = a.code 
                    WHERE a.type = 'expense' AND v.date >= ?
                """, [month_start_gregorian])
                expense = c.fetchone()[0] or 0
                
                profit = income - expense
                self.profit_card.value_label.setText(f"{profit:,.0f} ریال")
                
                # تغییر رنگ کارت سود بر اساس مقدار
                if profit >= 0:
                    self.profit_card.setStyleSheet("""
                        QFrame {
                            background-color: #27ae60;
                            border-radius: 10px;
                            padding: 12px;
                            color: white;
                            min-height: 70px;
                        }
                    """)
                else:
                    self.profit_card.setStyleSheet("""
                        QFrame {
                            background-color: #e74c3c;
                            border-radius: 10px;
                            padding: 12px;
                            color: white;
                            min-height: 70px;
                        }
                    """)
                
                # ====== اطلاعات سیستم ======
                c.execute("SELECT COUNT(*) FROM vouchers")
                vouchers_count = c.fetchone()[0] or 0
                
                c.execute("SELECT COUNT(*) FROM products")
                products_count = c.fetchone()[0] or 0
                
                c.execute("SELECT COUNT(*) FROM employees")
                employees_count = c.fetchone()[0] or 0
                
                c.execute("SELECT COUNT(*) FROM parties")
                parties_count = c.fetchone()[0] or 0
                
                c.execute("SELECT COUNT(*) FROM documents")
                docs_count = c.fetchone()[0] or 0
                
                now_gregorian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                now_shamsi = gregorian_to_shamsi(now_gregorian.split(' ')[0]) + " " + now_gregorian.split(' ')[1]
                
                self.info_text.setText(f"""
📊 **آمار سیستم:**
• تعداد اسناد حسابداری: {vouchers_count:,}
• تعداد کالاها: {products_count:,}
• تعداد پرسنل: {employees_count:,}
• تعداد اشخاص: {parties_count:,}
• تعداد اسناد خرید/فروش: {docs_count:,}
• تاریخ بروزرسانی: {now_shamsi}
                """)
                
                # ====== نمودارها ======
                self._update_pie_chart(income, expense)
                self._update_bar_chart()
                self._update_line_chart()
                
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری داشبورد: {e}")
            self.info_text.setText(f"⚠️ خطا در بارگذاری داده‌ها: {str(e)}")
    
    # ============================================================
    # نمودار دایره‌ای
    # ============================================================
    
    def _update_pie_chart(self, income, expense):
        colors = self._colors
        
        series = QPieSeries()
        series.setHoleSize(0.35)
        
        if income > 0:
            slice_income = series.append("درآمد", income)
            slice_income.setColor(QColor("#2ecc71"))
            slice_income.setLabelVisible(True)
            slice_income.setLabel(f"{income:,.0f}")
            slice_income.setLabelColor(QColor(colors['text']))
        
        if expense > 0:
            slice_expense = series.append("هزینه", expense)
            slice_expense.setColor(QColor("#e74c3c"))
            slice_expense.setLabelVisible(True)
            slice_expense.setLabel(f"{expense:,.0f}")
            slice_expense.setLabelColor(QColor(colors['text']))
        
        if income == 0 and expense == 0:
            slice_empty = series.append("بدون داده", 1)
            slice_empty.setColor(QColor(colors['text_tertiary']))
            slice_empty.setLabelVisible(True)
            slice_empty.setLabel("بدون داده")
            slice_empty.setLabelColor(QColor(colors['text']))
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("💰 سهم درآمد/هزینه")
        chart.setTitleFont(QFont("Tahoma", 10))
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignRight)
        chart.legend().setLabelColor(QColor(colors['text']))
        chart.setBackgroundBrush(QColor(colors['card']))
        chart.setTheme(self._get_chart_theme())
        
        self.pie_chart_view.setChart(chart)
        self.pie_chart_view.setStyleSheet("background: transparent; border: none;")
    
    # ============================================================
    # نمودار میل‌ای (فروش ۶ ماه اخیر) - با تاریخ شمسی
    # ============================================================
    
    def _update_bar_chart(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                from persiantools.jdatetime import JalaliDate
                
                months = []
                sales_data = []
                
                today = JalaliDate.today()
                
                for i in range(5, -1, -1):
                    month = today.month - i
                    year = today.year
                    if month <= 0:
                        month += 12
                        year -= 1
                    
                    month_start_jalali = f"{year:04d}/{month:02d}/01"
                    if month == 12:
                        month_end_jalali = f"{year:04d}/12/{29 if JalaliDate.is_leap(year) else 30}"
                    else:
                        month_end_jalali = f"{year:04d}/{month+1:02d}/01"
                    
                    month_start_gregorian = shamsi_to_gregorian(month_start_jalali)
                    month_end_gregorian = shamsi_to_gregorian(month_end_jalali)
                    
                    c.execute("""
                        SELECT COALESCE(SUM(net_amount), 0) 
                        FROM documents 
                        WHERE doc_type = 'sales' 
                        AND date >= ? AND date < ?
                    """, [month_start_gregorian, month_end_gregorian])
                    sales = c.fetchone()[0] or 0
                    
                    month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                                  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
                    months.append(month_names[month - 1])
                    sales_data.append(sales / 1000000)
                
                colors = self._colors
                
                series = QBarSeries()
                bar_set = QBarSet("فروش")
                bar_set.append(sales_data)
                bar_set.setColor(QColor("#3498db"))
                series.append(bar_set)
                series.setLabelsVisible(True)
                
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle("📈 فروش ۶ ماه اخیر (میلیون ریال)")
                chart.setTitleFont(QFont("Tahoma", 10))
                chart.setAnimationOptions(QChart.SeriesAnimations)
                chart.setBackgroundBrush(QColor(colors['card']))
                chart.setTheme(self._get_chart_theme())
                
                axis_x = QBarCategoryAxis()
                axis_x.append(months)
                axis_x.setLabelsColor(QColor(colors['text']))
                chart.addAxis(axis_x, Qt.AlignBottom)
                series.attachAxis(axis_x)
                
                axis_y = QValueAxis()
                axis_y.setTitleText("میلیون ریال")
                axis_y.setTitleBrush(QColor(colors['text']))
                axis_y.setLabelsColor(QColor(colors['text']))
                chart.addAxis(axis_y, Qt.AlignLeft)
                series.attachAxis(axis_y)
                
                self.bar_chart_view.setChart(chart)
                self.bar_chart_view.setStyleSheet("background: transparent; border: none;")
                
        except Exception as e:
            print(f"⚠️ خطا در نمودار میل‌ای: {e}")
    
    # ============================================================
    # نمودار خطی (روند سود ۳ ماه اخیر) - با تاریخ شمسی
    # ============================================================
    
    def _update_line_chart(self):
        try:
            with get_db() as conn:
                c = conn.cursor()
                
                from persiantools.jdatetime import JalaliDate
                
                months = []
                profit_data = []
                
                today = JalaliDate.today()
                
                for i in range(2, -1, -1):
                    month = today.month - i
                    year = today.year
                    if month <= 0:
                        month += 12
                        year -= 1
                    
                    month_start_jalali = f"{year:04d}/{month:02d}/01"
                    if month == 12:
                        month_end_jalali = f"{year:04d}/12/{29 if JalaliDate.is_leap(year) else 30}"
                    else:
                        month_end_jalali = f"{year:04d}/{month+1:02d}/01"
                    
                    month_start_gregorian = shamsi_to_gregorian(month_start_jalali)
                    month_end_gregorian = shamsi_to_gregorian(month_end_jalali)
                    
                    c.execute("""
                        SELECT COALESCE(SUM(credit - debit), 0) 
                        FROM voucher_items vi 
                        JOIN vouchers v ON vi.voucher_id = v.id 
                        JOIN accounts a ON vi.account_code = a.code 
                        WHERE a.type = 'income' AND v.date >= ? AND v.date < ?
                    """, [month_start_gregorian, month_end_gregorian])
                    income = c.fetchone()[0] or 0
                    
                    c.execute("""
                        SELECT COALESCE(SUM(debit - credit), 0) 
                        FROM voucher_items vi 
                        JOIN vouchers v ON vi.voucher_id = v.id 
                        JOIN accounts a ON vi.account_code = a.code 
                        WHERE a.type = 'expense' AND v.date >= ? AND v.date < ?
                    """, [month_start_gregorian, month_end_gregorian])
                    expense = c.fetchone()[0] or 0
                    
                    profit = income - expense
                    
                    month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                                  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
                    months.append(month_names[month - 1])
                    profit_data.append(profit / 1000000)
                
                colors = self._colors
                
                series = QLineSeries()
                series.setColor(QColor("#27ae60"))
                
                for i, val in enumerate(profit_data):
                    series.append(i, val)
                
                series.setPointsVisible(True)
                series.setPointLabelsVisible(True)
                series.setPointLabelsFormat("@yPoint")
                series.setPointLabelsFont(QFont("Tahoma", 8))
                
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle("📊 روند سود ۳ ماه اخیر (میلیون ریال)")
                chart.setTitleFont(QFont("Tahoma", 10))
                chart.setAnimationOptions(QChart.SeriesAnimations)
                chart.setBackgroundBrush(QColor(colors['card']))
                chart.setTheme(self._get_chart_theme())
                
                axis_x = QBarCategoryAxis()
                axis_x.append(months)
                axis_x.setLabelsColor(QColor(colors['text']))
                chart.addAxis(axis_x, Qt.AlignBottom)
                series.attachAxis(axis_x)
                
                axis_y = QValueAxis()
                axis_y.setTitleText("میلیون ریال")
                axis_y.setTitleBrush(QColor(colors['text']))
                axis_y.setLabelsColor(QColor(colors['text']))
                chart.addAxis(axis_y, Qt.AlignLeft)
                series.attachAxis(axis_y)
                
                if profit_data:
                    min_val = min(profit_data)
                    max_val = max(profit_data)
                    if min_val == max_val:
                        min_val = min_val - 1 if min_val > 0 else min_val - 1
                        max_val = max_val + 1
                    axis_y.setRange(min_val - abs(min_val)*0.2, max_val + abs(max_val)*0.2)
                
                self.line_chart_view.setChart(chart)
                self.line_chart_view.setStyleSheet("background: transparent; border: none;")
                
        except Exception as e:
            print(f"⚠️ خطا در نمودار خطی: {e}")
