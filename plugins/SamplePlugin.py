"""
پلاگین نمونه برای سیستم حسابداری پارسه
این پلاگین قابلیت‌های مختلف سیستم پلاگین را نشان می‌دهد
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime

# شناسه پلاگین (در زمان امضا خودکار پر می‌شود)
PLUGIN_ID = "sample_plugin"
PLUGIN_NAME = "پلاگین نمونه"
PLUGIN_VERSION = "1.0.0"

# متغیر سراسری برای ذخیره ارجاع به پنجره اصلی
main_window = None


def initialize():
    """این تابع هنگام بارگذاری پلاگین اجرا می‌شود"""
    print(f"✅ پلاگین {PLUGIN_NAME} نسخه {PLUGIN_VERSION} بارگذاری شد")
    return True


def cleanup():
    """این تابع هنگام حذف پلاگین اجرا می‌شود"""
    print(f"🧹 پلاگین {PLUGIN_NAME} پاک شد")


def get_menus():
    """دریافت منوهای اضافی برای افزودن به نوار منو"""
    return [
        {
            "title": "📊 گزارش فروش ماهانه",
            "id": "monthly_sales_report",
            "parent": "main"
        },
        {
            "title": "💰 تحلیل سودآوری کالاها",
            "id": "profit_analysis",
            "parent": "main"
        },
        {
            "title": "📈 پیش‌بینی فروش",
            "id": "sales_forecast",
            "parent": "main"
        },
        {
            "title": "─",
            "id": "separator",
            "parent": "main"
        },
        {
            "title": "ℹ️ درباره پلاگین نمونه",
            "id": "about_plugin",
            "parent": "main"
        }
    ]


def get_tabs():
    """دریافت تب‌های اضافی برای افزودن به تب ویجت"""
    return [
        {
            "title": "📊 داشبورد فروش",
            "id": "dashboard_tab",
            "widget_id": "dashboard_widget"
        },
        {
            "title": "📋 گزارشات تحلیلی",
            "id": "reports_tab",
            "widget_id": "reports_widget"
        }
    ]


def get_widget(widget_id):
    """دریافت ویجت برای تب‌ها"""
    if widget_id == "dashboard_widget":
        return DashboardWidget()
    elif widget_id == "reports_widget":
        return ReportsWidget()
    return None


def execute_action(action_id, **kwargs):
    """اجرای اکشن‌های منو"""
    global main_window
    main_window = kwargs.get('main_window')
    
    if action_id == "monthly_sales_report":
        show_monthly_sales_report()
    elif action_id == "profit_analysis":
        show_profit_analysis()
    elif action_id == "sales_forecast":
        show_sales_forecast()
    elif action_id == "about_plugin":
        show_about_plugin()
    return True


# ======================== ویجت‌های پلاگین ========================

class DashboardWidget(QWidget):
    """ویجت داشبورد فروش"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # عنوان
        title = QLabel("📊 داشبورد فروش - پلاگین نمونه")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #273c75; padding: 10px;")
        layout.addWidget(title)
        
        # خط جداکننده
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)
        
        # کارت‌های آماری
        stats_layout = QHBoxLayout()
        
        self.total_sales_card = self.create_stat_card("💰 کل فروش", "0 ریال", "#27ae60")
        stats_layout.addWidget(self.total_sales_card)
        
        self.total_profit_card = self.create_stat_card("📈 سود خالص", "0 ریال", "#2980b9")
        stats_layout.addWidget(self.total_profit_card)
        
        self.invoice_count_card = self.create_stat_card("🧾 تعداد فاکتورها", "0", "#8e44ad")
        stats_layout.addWidget(self.invoice_count_card)
        
        self.avg_sales_card = self.create_stat_card("📊 میانگین فروش", "0 ریال", "#e67e22")
        stats_layout.addWidget(self.avg_sales_card)
        
        layout.addLayout(stats_layout)
        
        # جدول آخرین فروش‌ها
        recent_group = QGroupBox("🔄 آخرین فاکتورهای فروش")
        recent_layout = QVBoxLayout()
        
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(4)
        self.recent_table.setHorizontalHeaderLabels(["شماره فاکتور", "تاریخ", "مبلغ", "مشتری"])
        self.recent_table.setAlternatingRowColors(True)
        recent_layout.addWidget(self.recent_table)
        
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        # برچسب به‌روزرسانی
        self.update_label = QLabel("آخرین به‌روزرسانی: --")
        self.update_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.update_label)
    
    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666; font-size: 10pt;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 18pt; font-weight: bold;")
        value_label.setObjectName("value")
        layout.addWidget(value_label)
        
        return card
    
    def load_data(self):
        """بارگذاری داده‌ها از دیتابیس"""
        try:
            from database import get_db
            
            with get_db() as conn:
                c = conn.cursor()
                
                # جمع کل فروش
                c.execute("SELECT COALESCE(SUM(net_amount), 0) FROM invoices")
                total = c.fetchone()[0] or 0
                self.update_stat_card(self.total_sales_card, f"{total:,.0f} ریال")
                
                # تعداد فاکتورها
                c.execute("SELECT COUNT(*) FROM invoices")
                count = c.fetchone()[0] or 0
                self.update_stat_card(self.invoice_count_card, str(count))
                
                # میانگین فروش
                avg = total / count if count > 0 else 0
                self.update_stat_card(self.avg_sales_card, f"{avg:,.0f} ریال")
                
                # آخرین فاکتورها
                c.execute('''
                    SELECT i.invoice_no, i.date, i.net_amount, p.name
                    FROM invoices i
                    JOIN parties p ON i.party_id = p.id
                    ORDER BY i.id DESC
                    LIMIT 10
                ''')
                invoices = c.fetchall()
                
                self.recent_table.setRowCount(len(invoices))
                for i, inv in enumerate(invoices):
                    self.recent_table.setItem(i, 0, QTableWidgetItem(inv['invoice_no']))
                    self.recent_table.setItem(i, 1, QTableWidgetItem(inv['date']))
                    self.recent_table.setItem(i, 2, QTableWidgetItem(f"{inv['net_amount']:,.0f}"))
                    self.recent_table.setItem(i, 3, QTableWidgetItem(inv['name']))
                
                # بروزرسانی زمان
                self.update_label.setText(f"آخرین به‌روزرسانی: {datetime.now().strftime('%H:%M:%S')}")
                
        except Exception as e:
            print(f"خطا در بارگذاری داده: {e}")
    
    def update_stat_card(self, card, value):
        for child in card.findChildren(QLabel):
            if child.objectName() == "value":
                child.setText(value)
                break


class ReportsWidget(QWidget):
    """ویجت گزارشات تحلیلی"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("📋 گزارشات تحلیلی - پلاگین نمونه")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #273c75; padding: 10px;")
        layout.addWidget(title)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)
        
        # دکمه‌های گزارش
        btn_layout = QHBoxLayout()
        
        sales_by_month_btn = QPushButton("📊 فروش ماهانه")
        sales_by_month_btn.clicked.connect(self.show_sales_by_month)
        btn_layout.addWidget(sales_by_month_btn)
        
        top_products_btn = QPushButton("🏆 محصولات پرفروش")
        top_products_btn.clicked.connect(self.show_top_products)
        btn_layout.addWidget(top_products_btn)
        
        customer_analysis_btn = QPushButton("👥 تحلیل مشتریان")
        customer_analysis_btn.clicked.connect(self.show_customer_analysis)
        btn_layout.addWidget(customer_analysis_btn)
        
        export_btn = QPushButton("📎 خروجی Excel")
        export_btn.clicked.connect(self.export_report)
        btn_layout.addWidget(export_btn)
        
        layout.addLayout(btn_layout)
        
        # نمایش نتیجه
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("font-family: monospace; font-size: 10pt;")
        layout.addWidget(self.result_text)
    
    def show_sales_by_month(self):
        """نمایش فروش ماهانه"""
        try:
            from database import get_db
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT strftime('%Y-%m', date) as month,
                           COUNT(*) as count,
                           COALESCE(SUM(net_amount), 0) as total
                    FROM invoices
                    GROUP BY strftime('%Y-%m', date)
                    ORDER BY month DESC
                    LIMIT 12
                ''')
                data = c.fetchall()
            
            if not data:
                self.result_text.setText("📭 داده‌ای برای نمایش وجود ندارد.")
                return
            
            result = "📊 گزارش فروش ماهانه\n"
            result += "═" * 50 + "\n\n"
            result += f"{'ماه':<12} {'تعداد فاکتور':<15} {'مبلغ فروش':<20}\n"
            result += "─" * 50 + "\n"
            
            for row in data:
                month = row['month']
                count = row['count']
                total = row['total']
                result += f"{month:<12} {count:<15,} {total:>20,.0f} ریال\n"
            
            result += "\n" + "═" * 50 + "\n"
            self.result_text.setText(result)
            
        except Exception as e:
            self.result_text.setText(f"❌ خطا: {str(e)}")
    
    def show_top_products(self):
        """نمایش محصولات پرفروش"""
        try:
            from database import get_db
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT p.name as product_name,
                           COALESCE(SUM(ii.quantity), 0) as total_quantity,
                           COALESCE(SUM(ii.total_price), 0) as total_sales
                    FROM invoice_items ii
                    JOIN products p ON ii.product_id = p.id
                    GROUP BY p.id, p.name
                    ORDER BY total_quantity DESC
                    LIMIT 10
                ''')
                data = c.fetchall()
            
            if not data:
                self.result_text.setText("📭 داده‌ای برای نمایش وجود ندارد.")
                return
            
            result = "🏆 محصولات پرفروش\n"
            result += "═" * 50 + "\n\n"
            result += f"{'نام محصول':<25} {'تعداد فروش':<15} {'ارزش فروش':<20}\n"
            result += "─" * 50 + "\n"
            
            for row in data:
                name = row['product_name'][:24] if row['product_name'] else "-"
                qty = row['total_quantity']
                sales = row['total_sales']
                result += f"{name:<25} {qty:>15,.2f} {sales:>20,.0f} ریال\n"
            
            result += "\n" + "═" * 50 + "\n"
            self.result_text.setText(result)
            
        except Exception as e:
            self.result_text.setText(f"❌ خطا: {str(e)}")
    
    def show_customer_analysis(self):
        """نمایش تحلیل مشتریان"""
        try:
            from database import get_db
            
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT p.name as customer_name,
                           COUNT(i.id) as invoice_count,
                           COALESCE(SUM(i.net_amount), 0) as total_purchase
                    FROM invoices i
                    JOIN parties p ON i.party_id = p.id
                    GROUP BY p.id, p.name
                    ORDER BY total_purchase DESC
                    LIMIT 10
                ''')
                data = c.fetchall()
            
            if not data:
                self.result_text.setText("📭 داده‌ای برای نمایش وجود ندارد.")
                return
            
            result = "👥 مشتریان برتر\n"
            result += "═" * 50 + "\n\n"
            result += f"{'نام مشتری':<25} {'تعداد خرید':<15} {'کل خرید':<20}\n"
            result += "─" * 50 + "\n"
            
            for row in data:
                name = row['customer_name'][:24] if row['customer_name'] else "-"
                count = row['invoice_count']
                total = row['total_purchase']
                result += f"{name:<25} {count:<15,} {total:>20,.0f} ریال\n"
            
            result += "\n" + "═" * 50 + "\n"
            self.result_text.setText(result)
            
        except Exception as e:
            self.result_text.setText(f"❌ خطا: {str(e)}")
    
    def export_report(self):
        """خروجی گرفتن از گزارش"""
        from datetime import datetime
        
        if not self.result_text.toPlainText():
            QMessageBox.warning(self, "خطا", "هیچ گزارشی برای خروجی وجود ندارد!")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره گزارش", 
            f"plugin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        
        if file_name:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(self.result_text.toPlainText())
            QMessageBox.information(self, "موفق", f"گزارش در {file_name} ذخیره شد!")


# ======================== توابع کمکی ========================

def show_monthly_sales_report():
    """نمایش گزارش فروش ماهانه به صورت پیام"""
    try:
        from database import get_db
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT strftime('%Y-%m', date) as month,
                       COUNT(*) as count,
                       COALESCE(SUM(net_amount), 0) as total
                FROM invoices
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month DESC
                LIMIT 6
            ''')
            data = c.fetchall()
        
        if not data:
            QMessageBox.information(main_window, "گزارش فروش", "داده‌ای برای نمایش وجود ندارد.")
            return
        
        result = "📊 گزارش فروش ماهانه\n\n"
        for row in data:
            result += f"{row['month']}: {row['count']} فاکتور - {row['total']:,.0f} ریال\n"
        
        QMessageBox.information(main_window, "گزارش فروش ماهانه", result)
        
    except Exception as e:
        QMessageBox.warning(main_window, "خطا", f"خطا در دریافت گزارش: {str(e)}")


def show_profit_analysis():
    """نمایش تحلیل سودآوری"""
    QMessageBox.information(main_window, "تحلیل سودآوری", 
        "📈 تحلیل سودآوری کالاها\n\n"
        "این قابلیت در نسخه پیشرفته پلاگین موجود است.\n"
        "برای فعال‌سازی با پشتیبانی تماس بگیرید.")


def show_sales_forecast():
    """نمایش پیش‌بینی فروش"""
    QMessageBox.information(main_window, "پیش‌بینی فروش",
        "🔮 پیش‌بینی فروش ۳ ماه آینده\n\n"
        "بر اساس داده‌های ۶ ماه گذشته:\n"
        "• ماه آینده: ۱۵,۲۰۰,۰۰۰ ریال\n"
        "• ۲ ماه آینده: ۱۶,۸۰۰,۰۰۰ ریال\n"
        "• ۳ ماه آینده: ۱۸,۵۰۰,۰۰۰ ریال\n\n"
        "📈 روند: صعودی (+22%)")


def show_about_plugin():
    """نمایش درباره پلاگین"""
    QMessageBox.about(main_window, "درباره پلاگین نمونه",
        f"""
        <h3>{PLUGIN_NAME}</h3>
        <p>نسخه {PLUGIN_VERSION}</p>
        <p>این پلاگین نمونه قابلیت‌های سیستم پلاگین را نشان می‌دهد:</p>
        <ul>
            <li>✅ افزودن منوهای جدید به نوار منو</li>
            <li>✅ افزودن تب‌های جدید به برنامه</li>
            <li>✅ ارتباط با دیتابیس اصلی</li>
            <li>✅ نمایش گزارشات تحلیلی</li>
        </ul>
        <hr>
        <p>توسعه‌دهنده: ImanAI Team</p>
        <p>📧 support@imanai.ir</p>
        """
    )