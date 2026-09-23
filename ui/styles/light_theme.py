# ui/styles/light_theme.py
# تم روشن ImanAccount

from .base_theme import BaseTheme


class LightTheme(BaseTheme):
    """تم روشن - پیش‌فرض برنامه"""
    
    name = "light"
    display_name = "☀️ روشن"
    
    def get_stylesheet(self) -> str:
        """دریافت استایل کامل CSS برای تم روشن"""
        c = self.colors
        f = self.fonts
        r = self.radius
        
        return f"""
            /* ============================================
               تم روشن ImanAccount
               ============================================ */
            
            QMainWindow {{
                background-color: {c['bg_primary']};
            }}
            
            QWidget {{
                font-family: {f['family']};
                font-size: {f['size_normal']};
                color: {c['text_primary']};
            }}
            
            /* ========== منو ========== */
            QMenuBar {{
                background-color: {c['bg_header']};
                color: {c['text_secondary']};
                border: none;
                border-bottom: 2px solid {c['border_header']};
                padding: 4px 10px;
            }}
            
            QMenuBar::item {{
                background: transparent;
                padding: 6px 14px;
                border-radius: {r['small']};
            }}
            
            QMenuBar::item:selected {{
                background-color: {c['btn_primary']};
                color: {c['text_white']};
            }}
            
            QMenu {{
                background-color: {c['bg_secondary']};
                border: 1px solid {c['border_primary']};
                border-radius: {r['normal']};
                padding: 5px;
            }}
            
            QMenu::item {{
                padding: 8px 25px;
                color: {c['text_primary']};
            }}
            
            QMenu::item:selected {{
                background-color: {c['btn_primary']};
                color: {c['text_white']};
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {c['border_primary']};
                margin: 5px 10px;
            }}
            
            /* ========== نوار کناری ========== */
            QWidget#sidebar {{
                background-color: {c['bg_sidebar']};
                border-right: 2px solid {c['border_sidebar']};
                min-width: 200px;
                max-width: 220px;
            }}
            
            QPushButton#sidebarBtn {{
                background-color: transparent;
                color: {c['btn_sidebar']};
                border: none;
                text-align: left;
                padding: 10px 16px;
                margin: 2px 8px;
                border-radius: {r['normal']};
                font-size: {f['size_normal']};
                font-weight: 400;
            }}
            
            QPushButton#sidebarBtn:hover {{
                background-color: {c['border_primary']};
                color: {c['btn_sidebar_hover']};
            }}
            
            QPushButton#sidebarBtn:checked {{
                background-color: {c['btn_primary']};
                color: {c['btn_sidebar_active']};
                font-weight: 500;
            }}
            
            QPushButton#sidebarSubBtn {{
                background-color: transparent;
                color: {c['text_tertiary']};
                border: none;
                text-align: left;
                padding: 6px 16px 6px 32px;
                margin: 1px 8px;
                border-radius: {r['small']};
                font-size: 9pt;
                font-weight: 300;
            }}
            
            QPushButton#sidebarSubBtn:hover {{
                background-color: {c['border_primary']};
                color: {c['text_primary']};
            }}
            
            QPushButton#sidebarSubBtn:checked {{
                background-color: {c['btn_primary']};
                color: {c['text_white']};
                font-weight: 400;
            }}
            
            QLabel#sidebarTitle {{
                color: {c['text_tertiary']};
                font-size: 9pt;
                font-weight: bold;
                padding: 12px 16px 5px 16px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            QLabel#sidebarLogo {{
                font-size: 20pt;
                padding: 10px;
                color: {c['sidebar_logo']};
            }}
            
            QLabel#sidebarVersion {{
                color: {c['text_tertiary']};
                font-size: 9pt;
                padding: 10px;
                text-align: center;
            }}
            
            QFrame#sidebarSeparator {{
                background-color: {c['border_primary']};
                margin: 5px 15px;
                max-height: 1px;
            }}
            
            /* ========== هدر ========== */
            QWidget#header {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c['header_gradient_start']}, 
                    stop:1 {c['header_gradient_end']});
                border-bottom: 2px solid {c['border_header']};
            }}
            
            QLabel#headerTitle {{
                font-size: 18px;
                font-weight: bold;
                color: {c['text_white']};
                background: transparent;
            }}
            
            QLabel#headerSubtitle {{
                font-size: 10px;
                color: {c['text_secondary']};
                background: transparent;
            }}
            
            QLabel#headerDate {{
                font-size: 11pt;
                font-weight: bold;
                color: {c['text_primary']};
                background-color: {c['bg_card']};
                padding: 4px 12px;
                border-radius: 16px;
                border: 1px solid {c['border_primary']};
            }}
            
            QLabel#headerDays {{
                font-size: 10pt;
                padding: 4px 10px;
                border-radius: 16px;
                font-weight: bold;
                color: {c['text_white']};
            }}
            
            /* ========== جدول ========== */
            QTableWidget {{
                background-color: {c['bg_table']};
                color: {c['text_primary']};
                border: 1px solid {c['border_primary']};
                border-radius: {r['medium']};
                gridline-color: {c['border_secondary']};
                alternate-background-color: {c['bg_table_alternate']};
            }}
            
            QTableWidget::item:selected {{
                background-color: {c['btn_primary']};
                color: {c['text_white']};
            }}
            
            QHeaderView::section {{
                background-color: {c['bg_tertiary']};
                color: {c['text_primary']};
                padding: 8px;
                border: none;
                font-weight: 600;
                border-bottom: 2px solid {c['border_primary']};
            }}
            
            /* ========== دکمه‌ها ========== */
            QPushButton {{
                background-color: {c['btn_primary']};
                color: {c['text_white']};
                border: none;
                padding: 8px 16px;
                border-radius: {r['normal']};
                font-weight: 500;
            }}
            
            QPushButton:hover {{
                background-color: {c['btn_primary_hover']};
            }}
            
            QPushButton:pressed {{
                background-color: {c['btn_primary_pressed']};
            }}
            
            QPushButton:disabled {{
                background-color: {c['text_tertiary']};
                color: {c['text_tertiary']};
            }}
            
            QPushButton#successBtn {{
                background-color: {c['btn_success']};
            }}
            QPushButton#successBtn:hover {{
                background-color: {c['btn_success_hover']};
            }}
            
            QPushButton#dangerBtn {{
                background-color: {c['btn_danger']};
            }}
            QPushButton#dangerBtn:hover {{
                background-color: {c['btn_danger_hover']};
            }}
            
            QPushButton#warningBtn {{
                background-color: {c['btn_warning']};
            }}
            QPushButton#warningBtn:hover {{
                background-color: {c['btn_warning_hover']};
            }}
            
            QPushButton#infoBtn {{
                background-color: {c['btn_info']};
            }}
            QPushButton#infoBtn:hover {{
                background-color: {c['btn_info_hover']};
            }}
            
            /* ========== ورودی‌ها ========== */
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {{
                background-color: {c['bg_input']};
                color: {c['text_primary']};
                border: 1px solid {c['border_primary']};
                border-radius: {r['normal']};
                padding: 6px 10px;
            }}
            
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border: 1px solid {c['border_focus']};
                background-color: {c['bg_tertiary']};
            }}
            
            /* ========== گروه‌ها ========== */
            QGroupBox {{
                border: 2px solid {c['border_primary']};
                border-radius: {r['medium']};
                margin-top: 12px;
                padding-top: 10px;
                font-weight: 600;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px;
                background-color: {c['bg_secondary']};
            }}
            
            /* ========== تب‌ها ========== */
            QTabWidget::pane {{
                border: 1px solid {c['border_primary']};
                border-radius: {r['normal']};
                background: {c['bg_card']};
            }}
            
            QTabBar::tab {{
                background: {c['bg_tertiary']};
                padding: 6px 14px;
                margin: 2px;
                border-radius: {r['small']};
            }}
            
            QTabBar::tab:selected {{
                background: {c['btn_primary']};
                color: {c['text_white']};
            }}
            
            QTabBar::tab:hover {{
                background: {c['border_primary']};
            }}
            
            /* ========== نوار وضعیت ========== */
            QStatusBar {{
                background-color: {c['bg_header']};
                color: {c['text_white']};
                font-weight: 500;
            }}
            
            QStatusBar::item {{
                border: none;
            }}
            
            /* ========== اسکرول‌بار ========== */
            QScrollBar:vertical {{
                background: {c['bg_secondary']};
                width: 10px;
                border-radius: {r['small']};
            }}
            
            QScrollBar::handle:vertical {{
                background: {c['border_primary']};
                border-radius: {r['small']};
                min-height: 30px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: {c['text_secondary']};
            }}
            
            QScrollBar:horizontal {{
                background: {c['bg_secondary']};
                height: 10px;
                border-radius: {r['small']};
            }}
            
            QScrollBar::handle:horizontal {{
                background: {c['border_primary']};
                border-radius: {r['small']};
                min-width: 30px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background: {c['text_secondary']};
            }}
            
            /* ========== کارت ========== */
            QWidget#cardWidget {{
                background-color: {c['bg_card']};
                border-radius: {r['medium']};
                border: 1px solid {c['border_primary']};
            }}
            
            /* ========== لیبل‌ها ========== */
            QLabel#titleLabel {{
                font-size: {f['size_large']};
                font-weight: bold;
                padding: 10px;
                color: {c['text_primary']};
            }}
            
            QLabel#subtitleLabel {{
                font-size: {f['size_medium']};
                font-weight: bold;
                padding: 5px;
                color: {c['text_primary']};
            }}
            
            QLabel#netLabel {{
                font-weight: bold;
                font-size: {f['size_large']};
                color: {c['btn_success']};
            }}
            
            QLabel#taxLabel {{
                font-weight: bold;
                color: {c['btn_warning']};
            }}
            
            /* ========== پیام‌ها ========== */
            QMessageBox {{
                background-color: {c['bg_card']};
            }}
            
            /* ========== دیالوگ‌ها ========== */
            QDialog {{
                background-color: {c['bg_secondary']};
            }}
        """
