# ui/coding_manager.py
# ============================================================
# مدیریت ساختار کدینگ حسابداری (۵ سطحی استاندارد)
# نسخه 3.0 — کامل با API درختواره
# ============================================================
# تغییرات v3.0:
# ✅ ساختار 5 سطحی: گروه/کل/معین/تفصیلی/جزئی
# ✅ جداکننده '.' (نقطه)
# ✅ Migration خودکار از v1/v2 به v3
# ✅ API کامل برای درختواره
# ✅ ساختار پیش‌فرض حسابداری ایرانی
# ✅ متدهای کمکی (parent, children, siblings, ...)
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import json
import os
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================
# ثابت‌ها
# ============================================================

CODING_VERSION = 3
DEFAULT_SEPARATOR = '.'

# ✅ ساختار 5 سطحی پیش‌فرض
DEFAULT_LEVELS = [
    {
        'length': 1,
        'name': 'گروه اصلی',
        'color': '#e74c3c',       # قرمز
        'icon': '🔴',
        'description': 'دسته اصلی (دارایی، بدهی، سرمایه، درآمد، هزینه)',
    },
    {
        'length': 2,
        'name': 'کل',
        'color': '#3498db',       # آبی
        'icon': '🔵',
        'description': 'کل حساب (دارایی جاری، دارایی غیرجاری، ...)',
    },
    {
        'length': 2,
        'name': 'معین',
        'color': '#2ecc71',       # سبز
        'icon': '🟢',
        'description': 'معین حساب (موجودی نقد، حساب‌های دریافتنی، ...)',
    },
    {
        'length': 3,
        'name': 'تفصیلی',
        'color': '#f39c12',       # نارنجی
        'icon': '🟠',
        'description': 'تفصیلی حساب (صندوق، بانک ملت، ...)',
    },
    {
        'length': 3,
        'name': 'جزئی',
        'color': '#9b59b6',       # بنفش
        'icon': '🟣',
        'description': 'جزئیات بیشتر (شعبه، پروژه، ...) — اختیاری',
    },
]


# ============================================================
# کلاس اصلی: CodingStructure
# ============================================================

class CodingStructure:
    """
    ساختار کدینگ حسابداری
    
    Attributes:
        levels: لیست سطوح (هر سطح: length, name, color, icon, description)
        separator: جداکننده بین سطوح (پیش‌فرض '.')
        version: نسخه ساختار (برای migration)
    """
    
    # ═══════════════════════════════════════════════════════
    # Constructor
    # ═══════════════════════════════════════════════════════
    
    def __init__(self):
        self.levels = []
        self.separator = DEFAULT_SEPARATOR
        self.version = CODING_VERSION
        self.load()
    
    # ═══════════════════════════════════════════════════════
    # مسیر فایل
    # ═══════════════════════════════════════════════════════
    
    def get_settings_path(self):
        """مسیر فایل تنظیمات"""
        return os.path.join(
            os.path.dirname(__file__), "..", "coding_structure.json"
        )
    
    # ═══════════════════════════════════════════════════════
    # Save / Load / Migration
    # ═══════════════════════════════════════════════════════
    
    def save(self):
        """ذخیره ساختار در فایل"""
        data = {
            'levels': self.levels,
            'separator': self.separator,
            'version': self.version,
        }
        try:
            with open(self.get_settings_path(), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ ساختار کدینگ ذخیره شد: {len(self.levels)} سطح")
            return True
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره کدینگ: {e}")
            return False
    
    def load(self):
        """بارگذاری ساختار (با Migration خودکار)"""
        path = self.get_settings_path()
        
        # اگه فایل نیست → ساختار پیش‌فرض
        if not os.path.exists(path):
            logger.info("📋 فایل کدینگ نیست — ساختار پیش‌فرض ۵ سطحی")
            self._apply_default()
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.levels = data.get('levels', [])
            self.separator = data.get('separator', DEFAULT_SEPARATOR)
            self.version = data.get('version', 1)
            
            # ✅ Migration
            if self.version < CODING_VERSION:
                logger.info(
                    f"🔄 Migration کدینگ از v{self.version} به v{CODING_VERSION}"
                )
                self._migrate()
            
            # ✅ اعتبارسنجی
            self._validate_and_fix()
        
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری کدینگ: {e}")
            self._apply_default()
    
    def _validate_and_fix(self):
        """اعتبارسنجی و اصلاح ساختار"""
        if not self.levels:
            logger.warning("⚠️ levels خالی — استفاده از پیش‌فرض")
            self._apply_default()
            return
        
        # چک فیلدهای هر سطح
        for i, level in enumerate(self.levels):
            if 'length' not in level:
                level['length'] = 2
            if 'name' not in level:
                level['name'] = f'سطح {i+1}'
            if 'color' not in level:
                level['color'] = '#3498db'
            if 'icon' not in level:
                level['icon'] = '⚪'
            if 'description' not in level:
                level['description'] = ''
    
    def _migrate(self):
        """Migration از نسخه‌های قدیم به 3.0"""
        path = self.get_settings_path()
        
        # ✅ پشتیبان‌گیری
        if os.path.exists(path):
            backup_path = (
                path + f".v{self.version}.backup_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            try:
                shutil.copy2(path, backup_path)
                logger.info(f"📦 پشتیبان: {backup_path}")
            except Exception as e:
                logger.warning(f"⚠️ خطا در پشتیبان: {e}")
        
        # ✅ اعمال ساختار جدید
        self._apply_default()
        
        logger.info(
            f"✅ Migration انجام شد: {len(self.levels)} سطح، "
            f"جداکننده '{self.separator}'"
        )
    
    def _apply_default(self):
        """اعمال ساختار پیش‌فرض"""
        self.levels = [lvl.copy() for lvl in DEFAULT_LEVELS]
        self.separator = DEFAULT_SEPARATOR
        self.version = CODING_VERSION
        self.save()
    
    def get_default_structure(self):
        """اگر خالیه، پیش‌فرض رو اعمال کن"""
        if not self.levels:
            self._apply_default()
    
    def reset_to_default(self):
        """بازنشانی به پیش‌فرض 5 سطحی"""
        self._apply_default()
    
    # ═══════════════════════════════════════════════════════
    # Helper: اطلاعات سطوح
    # ═══════════════════════════════════════════════════════
    
    def get_level_count(self):
        """تعداد سطوح"""
        return len(self.levels)
    
    def get_max_level(self):
        """حداکثر سطح مجاز"""
        return len(self.levels)
    
    def get_code_length(self):
        """طول کل کد (بدون جداکننده)"""
        return sum(level['length'] for level in self.levels)
    
    def get_level_info(self, level_num):
        """
        اطلاعات یک سطح
        
        Args:
            level_num: شماره سطح (1-based)
        
        Returns:
            dict یا None
        """
        if 1 <= level_num <= len(self.levels):
            return self.levels[level_num - 1]
        return None
    
    def get_level_color(self, level_num):
        """رنگ یک سطح"""
        info = self.get_level_info(level_num)
        return info.get('color', '#666666') if info else '#666666'
    
    def get_level_name(self, level_num):
        """نام یک سطح"""
        info = self.get_level_info(level_num)
        return info.get('name', f'سطح {level_num}') if info else f'سطح {level_num}'
    
    def get_level_icon(self, level_num):
        """آیکون یک سطح"""
        info = self.get_level_info(level_num)
        return info.get('icon', '⚪') if info else '⚪'
    
    # ═══════════════════════════════════════════════════════
    # Helper: Parse / Format Code
    # ═══════════════════════════════════════════════════════
    
    def format_code(self, parts):
        """
        تبدیل لیست بخش‌ها به کد فرمت شده
        
        Args:
            parts: لیست str (مثل ['1', '11', '01', '001'])
        
        Returns:
            str (مثل '1.11.01.001')
        """
        if not parts:
            return ''
        return self.separator.join(str(p) for p in parts)
    
    def parse_code(self, code):
        """
        تبدیل کد به لیست بخش‌ها
        
        Args:
            code: str (مثل '1.11.01.001')
        
        Returns:
            list[str] (مثل ['1', '11', '01', '001'])
        """
        if not code:
            return []
        return str(code).split(self.separator)
    
    def get_level_of_code(self, code):
        """
        تشخیص سطح یک کد
        
        Returns:
            int (1-based) یا 0 اگه نامعتبر
        """
        parts = self.parse_code(code)
        return len(parts)
    
    def validate_code(self, code):
        """
        اعتبارسنجی کد
        
        Returns:
            tuple (is_valid: bool, error_message: str)
        """
        if not code:
            return False, "کد خالی است"
        
        parts = self.parse_code(code)
        
        if len(parts) > len(self.levels):
            return False, f"کد بیشتر از {len(self.levels)} سطح دارد"
        
        for i, part in enumerate(parts):
            level_info = self.levels[i]
            expected_length = level_info['length']
            
            if not part.isdigit():
                return False, f"سطح {i+1} ({level_info['name']}) فقط عدد"
            
            if len(part) != expected_length:
                return False, (
                    f"سطح {i+1} ({level_info['name']}) باید "
                    f"{expected_length} رقم باشد، ولی {len(part)} رقم است"
                )
        
        return True, ""
    
    def validate_parts(self, parts):
        """اعتبارسنجی لیست بخش‌ها"""
        if not parts:
            return False
        return self.validate_code(self.format_code(parts))[0]
    
    # ═══════════════════════════════════════════════════════
    # Helper: ساختار درختی
    # ═══════════════════════════════════════════════════════
    
    def get_parent_code(self, code):
        """
        دریافت کد والد
        
        Args:
            code: '1.11.01.001'
        
        Returns:
            '1.11.01' یا None
        """
        parts = self.parse_code(code)
        if len(parts) <= 1:
            return None
        return self.format_code(parts[:-1])
    
    def get_ancestors(self, code):
        """
        دریافت همه والدها (از بالا به پایین)
        
        Args:
            code: '1.11.01.001'
        
        Returns:
            ['1', '1.11', '1.11.01']
        """
        parts = self.parse_code(code)
        ancestors = []
        for i in range(1, len(parts)):
            ancestors.append(self.format_code(parts[:i]))
        return ancestors
    
    def get_code_at_level(self, code, target_level):
        """
        دریافت کد در سطح مشخص
        
        Args:
            code: '1.11.01.001'
            target_level: 2
        
        Returns:
            '1.11' یا None
        """
        parts = self.parse_code(code)
        if target_level < 1 or target_level > len(parts):
            return None
        return self.format_code(parts[:target_level])
    
    def is_ancestor(self, ancestor_code, descendant_code):
        """آیا ancestor_code والد descendant_code است؟"""
        if ancestor_code == descendant_code:
            return False
        ancestor_parts = self.parse_code(ancestor_code)
        descendant_parts = self.parse_code(descendant_code)
        
        if len(ancestor_parts) >= len(descendant_parts):
            return False
        
        return descendant_parts[:len(ancestor_parts)] == ancestor_parts
    
    def get_next_code(self, parent_code=None, existing_siblings=None):
        """
        تولید کد بعدی در یک سطح
        
        Args:
            parent_code: کد والد (None برای سطح 1)
            existing_siblings: لیست کدهای موجود در همون سطح (برای پیدا کردن عدد بعدی)
        
        Returns:
            کد جدید یا None
        """
        # تعیین سطح
        if parent_code is None:
            next_level = 1
            parent_parts = []
        else:
            parent_parts = self.parse_code(parent_code)
            next_level = len(parent_parts) + 1
        
        # چک عمق
        if next_level > len(self.levels):
            return None
        
        level_info = self.levels[next_level - 1]
        length = level_info['length']
        
        # اگه siblings نداریم، از 1 شروع کن
        if not existing_siblings:
            new_num = 1
        else:
            # پیدا کردن بزرگترین عدد
            max_num = 0
            for sibling_code in existing_siblings:
                sibling_parts = self.parse_code(sibling_code)
                if len(sibling_parts) == next_level:
                    try:
                        num = int(sibling_parts[-1])
                        max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        pass
            new_num = max_num + 1
        
        # چک ظرفیت
        max_value = 10 ** length - 1
        if new_num > max_value:
            logger.warning(f"⚠️ سطح {next_level} پر شده (max={max_value})")
            return None
        
        new_part = str(new_num).zfill(length)
        return self.format_code(parent_parts + [new_part])
    
    def get_next_sibling_code(self, current_code, existing_codes):
        """
        کد بعدی در همون سطح (برای insert after)
        
        Args:
            current_code: کد فعلی
            existing_codes: لیست همه کدهای موجود
        
        Returns:
            کد جدید یا None
        """
        parts = self.parse_code(current_code)
        if not parts:
            return None
        
        # کد والد
        parent_code = self.get_parent_code(current_code) if len(parts) > 1 else None
        
        # سطوح
        siblings = []
        for code in existing_codes:
            code_parts = self.parse_code(code)
            if len(code_parts) != len(parts):
                continue
            code_parent = (
                self.get_parent_code(code) if len(code_parts) > 1 else None
            )
            if code_parent == parent_code:
                siblings.append(code)
        
        return self.get_next_code(parent_code, siblings)
    
    # ═══════════════════════════════════════════════════════
    # Helper: اطلاعات نمایشی
    # ═══════════════════════════════════════════════════════
    
    def get_level_display(self, level_num):
        """نمایش سطح به صورت 'نام (طول)'"""
        info = self.get_level_info(level_num)
        if not info:
            return f'سطح {level_num}'
        return f"{info['name']} ({info['length']} رقم)"
    
    def get_structure_display(self):
        """نمایش کل ساختار"""
        parts = []
        for i, level in enumerate(self.levels):
            parts.append(f"{i+1}:{level['length']}")
        return self.separator.join(parts)
    
    def get_structure_summary(self):
        """خلاصه ساختار برای نمایش"""
        lines = []
        for i, level in enumerate(self.levels):
            lines.append(
                f"سطح {i+1}: {level['name']} "
                f"({level['length']} رقم) — {level['color']}"
            )
        return '\n'.join(lines)
    
    # ═══════════════════════════════════════════════════════
    # Helper: اعتبارسنجی rename / delete
    # ═══════════════════════════════════════════════════════
    
    def can_delete_code(self, code, has_children, has_transactions):
        """
        آیا کد قابل حذف است؟
        
        Returns:
            tuple (can_delete: bool, reason: str)
        """
        if has_children:
            return False, "این حساب دارای زیرحساب است"
        if has_transactions:
            return False, "این حساب در اسناد استفاده شده"
        return True, ""
    
    def can_edit_code(self, code, new_code, existing_codes):
        """
        آیا کد جدید قابل قبول است؟
        """
        # اعتبارسنجی فرمت
        is_valid, error = self.validate_code(new_code)
        if not is_valid:
            return False, error
        
        # چک تکراری
        if new_code in existing_codes and new_code != code:
            return False, "این کد قبلاً استفاده شده"
        
        return True, ""


# ============================================================
# دیالوگ تنظیم ساختار کدینگ
# ============================================================

class CodingStructureDialog(QDialog):
    """دیالوگ تنظیم ساختار کدینگ"""
    
    def __init__(self, coding_structure, parent=None):
        super().__init__(parent)
        self.coding = coding_structure
        self.setWindowTitle("⚙️ تنظیمات ساختار کدینگ")
        self.setModal(True)
        self.setMinimumSize(850, 650)
        self.setup_ui()
        self.load_data()
        self.apply_theme()
    
    # ═══════════════════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════════════════
    
    def get_theme_colors(self):
        """دریافت رنگ‌های تم"""
        try:
            from ui.styles.theme_manager import get_theme_manager
            tm = get_theme_manager()
            is_dark = tm.get_theme_name() == 'dark'
        except Exception:
            is_dark = False
        
        if is_dark:
            return {
                'bg': "#1a1a2e", 'bg_alt': "#16213e", 'card': "#1a1a3e",
                'text': "#e8e8e8", 'text_secondary': "#a0a0a0",
                'border': "#0f3460", 'hover': "#2a2a4a",
                'selected': "#e94560", 'selected_text': "#ffffff",
                'success': "#27ae60", 'danger': "#e74c3c",
                'warning': "#f39c12", 'info': "#3498db",
            }
        else:
            return {
                'bg': "#f5f6fa", 'bg_alt': "#ffffff", 'card': "#ffffff",
                'text': "#1a1a2e", 'text_secondary': "#5d6d7e",
                'border': "#dcdde1", 'hover': "#e8e8e8",
                'selected': "#1976D2", 'selected_text': "#ffffff",
                'success': "#27ae60", 'danger': "#e74c3c",
                'warning': "#f39c12", 'info': "#3498db",
            }
    
    def apply_theme(self):
        """اعمال تم"""
        c = self.get_theme_colors()
        
        self.setStyleSheet(f"""
            QDialog {{
                background: {c['bg']};
                color: {c['text']};
            }}
            QLabel {{
                color: {c['text']};
                background: transparent;
            }}
            QGroupBox {{
                background: {c['card']};
                color: {c['text']};
                border: 2px solid {c['border']};
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px 10px 10px 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top right;
                right: 15px;
                padding: 0 8px;
                color: {c['selected']};
                background: {c['bg']};
            }}
            QLineEdit, QComboBox, QSpinBox {{
                background: {c['bg_alt']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 26px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border: 2px solid {c['selected']};
            }}
            QPushButton {{
                background: {c['bg_alt']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 32px;
            }}
            QPushButton:hover {{
                background: {c['hover']};
                border: 1px solid {c['selected']};
            }}
            QPushButton#successBtn {{
                background: {c['success']};
                color: white;
                border: none;
            }}
            QPushButton#successBtn:hover {{
                background: #1e8449;
            }}
            QPushButton#dangerBtn {{
                background: {c['danger']};
                color: white;
                border: none;
            }}
            QPushButton#dangerBtn:hover {{
                background: #c0392b;
            }}
            QPushButton#warningBtn {{
                background: {c['warning']};
                color: white;
                border: none;
            }}
            QPushButton#warningBtn:hover {{
                background: #d68910;
            }}
            QPushButton#infoBtn {{
                background: {c['info']};
                color: white;
                border: none;
            }}
            QPushButton#infoBtn:hover {{
                background: #2980b9;
            }}
            QTableWidget {{
                background: {c['bg_alt']};
                alternate-background-color: {c['bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                gridline-color: {c['border']};
            }}
            QTableWidget::item {{
                padding: 5px;
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
                font-weight: bold;
            }}
        """)
    
    # ═══════════════════════════════════════════════════════
    # UI
    # ═══════════════════════════════════════════════════════
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # ─── Header ───
        header = QLabel(
            "📋 تنظیمات ساختار کدینگ حسابداری\n"
            "💡 پیشنهاد: ۵ سطح استاندارد (گروه اصلی / کل / معین / تفصیلی / جزئی)"
        )
        header.setStyleSheet(
            "font-size: 12pt; font-weight: bold; padding: 12px; "
            "background: #e8f4fd; border-radius: 6px; color: #1976D2;"
        )
        header.setWordWrap(True)
        layout.addWidget(header)
        
        # ─── ردیف جداکننده ───
        sep_layout = QHBoxLayout()
        sep_layout.setSpacing(10)
        
        sep_layout.addWidget(QLabel("🔗 جداکننده:"))
        self.separator_combo = QComboBox()
        self.separator_combo.addItems([".", "-", "/", "_", " "])
        self.separator_combo.setMinimumWidth(80)
        self.separator_combo.currentTextChanged.connect(self.update_preview)
        sep_layout.addWidget(self.separator_combo)
        
        sep_layout.addSpacing(20)
        sep_layout.addWidget(QLabel("پیش‌نمایش:"))
        
        self.separator_preview = QLabel("1.11.01.001")
        self.separator_preview.setStyleSheet(
            "font-family: 'Courier New', monospace; font-size: 12pt; "
            "background: #f0f0f0; padding: 6px 12px; border-radius: 4px; "
            "color: #1976D2; font-weight: bold;"
        )
        sep_layout.addWidget(self.separator_preview)
        
        sep_layout.addStretch()
        layout.addLayout(sep_layout)
        
        # ─── جدول سطوح ───
        self.levels_table = QTableWidget()
        self.levels_table.setColumnCount(7)
        self.levels_table.setHorizontalHeaderLabels([
            "سطح", "آیکون", "نام سطح", "طول", "رنگ", "نمونه کد", "توضیحات"
        ])
        self.levels_table.horizontalHeader().setStretchLastSection(True)
        self.levels_table.setColumnWidth(0, 50)
        self.levels_table.setColumnWidth(1, 50)
        self.levels_table.setColumnWidth(2, 130)
        self.levels_table.setColumnWidth(3, 70)
        self.levels_table.setColumnWidth(4, 60)
        self.levels_table.setColumnWidth(5, 150)
        self.levels_table.verticalHeader().setDefaultSectionSize(42)
        self.levels_table.setAlternatingRowColors(True)
        layout.addWidget(self.levels_table, 1)
        
        # ─── دکمه‌های عملیات ───
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        add_btn = QPushButton("➕ افزودن سطح")
        add_btn.setObjectName("successBtn")
        add_btn.clicked.connect(self.add_level)
        action_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("➖ حذف سطح")
        remove_btn.setObjectName("dangerBtn")
        remove_btn.clicked.connect(self.remove_level)
        action_layout.addWidget(remove_btn)
        
        action_layout.addSpacing(20)
        
        reset_btn = QPushButton("🔄 بازنشانی به پیش‌فرض (۵ سطحی)")
        reset_btn.setObjectName("warningBtn")
        reset_btn.clicked.connect(self.reset_to_default)
        action_layout.addWidget(reset_btn)
        
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        # ─── هشدار ───
        warning = QLabel(
            "⚠️ توجه: تغییر ساختار کدینگ بر روی حساب‌های موجود تأثیر می‌گذارد!\n"
            "💾 قبل از هر تغییر، به‌صورت خودکار پشتیبان گرفته می‌شود."
        )
        warning.setStyleSheet(
            "color: #856404; background: #fff3cd; padding: 10px; "
            "border-radius: 6px; border: 1px solid #ffc107; "
            "font-size: 9pt;"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        # ─── دکمه‌های نهایی ───
        final_layout = QHBoxLayout()
        final_layout.addStretch()
        
        save_btn = QPushButton("💾 ذخیره ساختار")
        save_btn.setObjectName("successBtn")
        save_btn.setMinimumWidth(150)
        save_btn.setMinimumHeight(42)
        save_btn.clicked.connect(self.save_structure)
        final_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ انصراف")
        cancel_btn.setObjectName("dangerBtn")
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setMinimumHeight(42)
        cancel_btn.clicked.connect(self.reject)
        final_layout.addWidget(cancel_btn)
        
        layout.addLayout(final_layout)
    
    # ═══════════════════════════════════════════════════════
    # Load Data
    # ═══════════════════════════════════════════════════════
    
    def load_data(self):
        """بارگذاری ساختار فعلی در UI"""
        self.separator_combo.setCurrentText(self.coding.separator)
        
        self.levels_table.setRowCount(len(self.coding.levels))
        
        for i, level in enumerate(self.coding.levels):
            self._add_row(i, level)
        
        self.update_sample_codes()
        self.update_preview()
    
    def _add_row(self, row, level):
        """افزودن یک ردیف به جدول"""
        # شماره سطح
        num_item = QTableWidgetItem(str(row + 1))
        num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
        num_item.setTextAlignment(Qt.AlignCenter)
        self.levels_table.setItem(row, 0, num_item)
        
        # آیکون
        icon_edit = QLineEdit(level.get('icon', '⚪'))
        icon_edit.setMaxLength(3)
        icon_edit.setAlignment(Qt.AlignCenter)
        icon_edit.setStyleSheet("font-size: 14pt; padding: 2px;")
        self.levels_table.setCellWidget(row, 1, icon_edit)
        
        # نام سطح
        name_edit = QLineEdit(level.get('name', f'سطح {row+1}'))
        name_edit.textChanged.connect(self.update_preview)
        self.levels_table.setCellWidget(row, 2, name_edit)
        
        # طول
        length_spin = QSpinBox()
        length_spin.setRange(1, 6)
        length_spin.setValue(level.get('length', 2))
        length_spin.valueChanged.connect(self.update_sample_codes)
        self.levels_table.setCellWidget(row, 3, length_spin)
        
        # رنگ
        color_btn = QPushButton("🎨")
        color = level.get('color', '#3498db')
        color_btn.setStyleSheet(
            f"background-color: {color}; color: white; "
            f"font-weight: bold; border-radius: 4px; "
            f"font-size: 14pt;"
        )
        color_btn.setProperty('color_value', color)
        color_btn.clicked.connect(
            lambda checked, r=row: self.select_color(r)
        )
        self.levels_table.setCellWidget(row, 4, color_btn)
        
        # نمونه کد
        sample_item = QTableWidgetItem("")
        sample_item.setFlags(sample_item.flags() & ~Qt.ItemIsEditable)
        sample_item.setTextAlignment(Qt.AlignCenter)

        # ✅ استفاده از QFont به جای setStyleSheet
        sample_font = QFont("Courier New", 10)
        sample_item.setFont(sample_font)
        sample_item.setForeground(QColor("#1976D2"))

        self.levels_table.setItem(row, 5, sample_item)
        
        # توضیحات
        desc_edit = QLineEdit(level.get('description', ''))
        desc_edit.setPlaceholderText("اختیاری")
        self.levels_table.setCellWidget(row, 6, desc_edit)
    
    def update_sample_codes(self):
        """بروزرسانی نمونه کدها"""
        separator = self.separator_combo.currentText()
        
        for i in range(self.levels_table.rowCount()):
            # ساخت نمونه بر اساس طول همه سطوح تا این سطح
            parts = []
            for j in range(i + 1):
                length_spin = self.levels_table.cellWidget(j, 3)
                if length_spin:
                    parts.append(str(1).zfill(length_spin.value()))
            
            sample = separator.join(parts)
            
            item = self.levels_table.item(i, 5)
            if item:
                item.setText(sample)
    
    def update_preview(self):
        """بروزرسانی پیش‌نمایش"""
        separator = self.separator_combo.currentText()
        
        # ساخت پیش‌نمایش کامل
        parts = []
        for i in range(self.levels_table.rowCount()):
            length_spin = self.levels_table.cellWidget(i, 3)
            if length_spin:
                parts.append(str(1).zfill(length_spin.value()))
        
        preview = separator.join(parts) if parts else "---"
        self.separator_preview.setText(preview)
        
        # بروزرسانی نمونه‌های جدول
        self.update_sample_codes()
    
    # ═══════════════════════════════════════════════════════
    # Actions
    # ═══════════════════════════════════════════════════════
    
    def select_color(self, row):
        """انتخاب رنگ برای سطح"""
        color_btn = self.levels_table.cellWidget(row, 4)
        if not color_btn:
            return
        
        current_color = color_btn.property('color_value') or '#3498db'
        color = QColorDialog.getColor(
            QColor(current_color), self, "انتخاب رنگ سطح"
        )
        
        if color.isValid():
            color_hex = color.name()
            color_btn.setStyleSheet(
                f"background-color: {color_hex}; color: white; "
                f"font-weight: bold; border-radius: 4px; "
                f"font-size: 14pt;"
            )
            color_btn.setProperty('color_value', color_hex)
    
    def add_level(self):
        """افزودن سطح جدید"""
        if self.levels_table.rowCount() >= 7:
            QMessageBox.warning(
                self, "خطا", "حداکثر ۷ سطح مجاز است!"
            )
            return
        
        row = self.levels_table.rowCount()
        self.levels_table.insertRow(row)
        
        # آیکون پیش‌فرض
        default_icon = '🟣' if row >= 5 else '⚪'
        default_color = '#9b59b6'
        default_length = 3
        
        level = {
            'length': default_length,
            'name': f'سطح {row + 1}',
            'color': default_color,
            'icon': default_icon,
            'description': '',
        }
        
        self._add_row(row, level)
        
        # بروزرسانی شماره سطوح
        self._update_row_numbers()
        self.update_sample_codes()
        self.update_preview()
    
    def remove_level(self):
        """حذف سطح انتخابی"""
        row = self.levels_table.currentRow()
        
        if row < 0:
            QMessageBox.warning(
                self, "خطا", "لطفاً یک سطح را انتخاب کنید!"
            )
            return
        
        if self.levels_table.rowCount() <= 1:
            QMessageBox.warning(
                self, "خطا", "حداقل یک سطح باید وجود داشته باشد!"
            )
            return
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف سطح {row + 1} اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.levels_table.removeRow(row)
            self._update_row_numbers()
            self.update_sample_codes()
            self.update_preview()
    
    def _update_row_numbers(self):
        """بروزرسانی شماره سطوح"""
        for row in range(self.levels_table.rowCount()):
            item = self.levels_table.item(row, 0)
            if item:
                item.setText(str(row + 1))
            else:
                new_item = QTableWidgetItem(str(row + 1))
                new_item.setFlags(new_item.flags() & ~Qt.ItemIsEditable)
                new_item.setTextAlignment(Qt.AlignCenter)
                self.levels_table.setItem(row, 0, new_item)
    
    def reset_to_default(self):
        """بازنشانی به پیش‌فرض ۵ سطحی"""
        reply = QMessageBox.question(
            self, "تأیید بازنشانی",
            "آیا ساختار به ۵ سطح استاندارد بازنشانی شود؟\n\n"
            f"ساختار فعلی: {self.levels_table.rowCount()} سطح\n"
            "ساختار جدید: ۵ سطح (گروه/کل/معین/تفصیلی/جزئی)",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # پاک کردن جدول
        self.levels_table.setRowCount(0)
        
        # جداکننده
        self.separator_combo.setCurrentText(DEFAULT_SEPARATOR)
        
        # ساختار پیش‌فرض
        self.levels_table.setRowCount(len(DEFAULT_LEVELS))
        for i, level in enumerate(DEFAULT_LEVELS):
            self._add_row(i, level)
        
        self.update_sample_codes()
        self.update_preview()
        
        QMessageBox.information(
            self, "موفق", "✅ ساختار به ۵ سطح استاندارد بازنشانی شد!"
        )
    
    # ═══════════════════════════════════════════════════════
    # Save
    # ═══════════════════════════════════════════════════════
    
    def save_structure(self):
        """ذخیره ساختار"""
        levels = []
        
        for row in range(self.levels_table.rowCount()):
            icon_edit = self.levels_table.cellWidget(row, 1)
            name_edit = self.levels_table.cellWidget(row, 2)
            length_spin = self.levels_table.cellWidget(row, 3)
            color_btn = self.levels_table.cellWidget(row, 4)
            desc_edit = self.levels_table.cellWidget(row, 6)
            
            if not all([icon_edit, name_edit, length_spin, color_btn]):
                continue
            
            color = color_btn.property('color_value') or '#3498db'
            
            levels.append({
                'length': length_spin.value(),
                'color': color,
                'name': name_edit.text().strip() or f'سطح {row + 1}',
                'icon': icon_edit.text().strip() or '⚪',
                'description': desc_edit.text().strip() if desc_edit else '',
            })
        
        # اعتبارسنجی
        if not levels:
            QMessageBox.warning(
                self, "خطا", "حداقل یک سطح باید وجود داشته باشد!"
            )
            return
        
        # نام تکراری
        names = [lvl['name'] for lvl in levels]
        if len(names) != len(set(names)):
            QMessageBox.warning(
                self, "خطا", "نام سطوح نمی‌توانند تکراری باشند!"
            )
            return
        
        # پشتیبان
        path = self.coding.get_settings_path()
        if os.path.exists(path):
            backup_path = (
                path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            try:
                shutil.copy2(path, backup_path)
                logger.info(f"📦 پشتیبان: {backup_path}")
            except Exception as e:
                logger.warning(f"⚠️ خطا در پشتیبان: {e}")
        
        # ذخیره
        self.coding.levels = levels
        self.coding.separator = self.separator_combo.currentText()
        self.coding.version = CODING_VERSION
        
        if self.coding.save():
            QMessageBox.information(
                self, "موفق",
                f"✅ ساختار کدینگ ذخیره شد!\n\n"
                f"📊 {len(levels)} سطح\n"
                f"🔗 جداکننده: '{self.coding.separator}'\n\n"
                f"💾 پشتیبان در: coding_structure.json.backup_*"
            )
            self.accept()
        else:
            QMessageBox.warning(
                self, "خطا", "❌ خطا در ذخیره ساختار!"
            )


# ============================================================
# Singleton Accessor
# ============================================================

_coding_instance = None


def get_coding_structure():
    """دریافت نمونه Singleton از CodingStructure"""
    global _coding_instance
    if _coding_instance is None:
        _coding_instance = CodingStructure()
    return _coding_instance


# ============================================================
# تست
# ============================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    
    coding = CodingStructure()
    print(f"\n📋 ساختار کدینگ:")
    print(f"   تعداد سطوح: {coding.get_level_count()}")
    print(f"   جداکننده: '{coding.separator}'")
    print(f"   طول کل: {coding.get_code_length()}")
    print(f"\n{coding.get_structure_summary()}\n")
    
    # تست کدها
    test_codes = [
        "1",
        "1.11",
        "1.11.01",
        "1.11.01.001",
        "1.11.01.001.001",
    ]
    
    for code in test_codes:
        is_valid, error = coding.validate_code(code)
        level = coding.get_level_of_code(code)
        parent = coding.get_parent_code(code)
        print(
            f"   {code:25} | سطح {level} | "
            f"والد: {parent or '—':20} | "
            f"{'✅' if is_valid else '❌ ' + error}"
        )
    
    # تست next_code
    print(f"\n📝 تست next_code:")
    print(f"   بعد از '1': {coding.get_next_code(None, ['1'])}")
    print(f"   بعد از '1.11': {coding.get_next_code('1', ['1.11', '1.12'])}")
    print(f"   زیر '1.11': {coding.get_next_code('1.11', [])}")
    
    # نمایش دیالوگ
    dialog = CodingStructureDialog(coding)
    dialog.exec_()
