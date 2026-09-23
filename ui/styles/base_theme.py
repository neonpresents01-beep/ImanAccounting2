# ui/styles/base_theme.py
# کلاس پایه برای تمام تم‌ها

from typing import Dict, Any


class BaseTheme:
    """کلاس پایه تم - همه تم‌ها باید از این ارث‌بری کنند"""
    
    # ===== نام تم =====
    name = "base"
    display_name = "پایه"
    
    # ===== رنگ‌های اصلی =====
    colors = {
        'bg_primary': '#ffffff',
        'bg_secondary': '#f5f7fa',
        'bg_tertiary': '#eef2f5',
        'bg_card': '#ffffff',
        'bg_header': '#1a2332',
        'bg_sidebar': '#1a2332',
        'bg_input': '#ffffff',
        'bg_table': '#ffffff',
        'bg_table_alternate': '#f8f9fa',
        'bg_group': '#ffffff',
        'text_primary': '#2c3e50',
        'text_secondary': '#5d6d7e',
        'text_tertiary': '#a0a0a0',
        'text_white': '#ffffff',
        'text_black': '#000000',
        'btn_primary': '#1976D2',
        'btn_primary_hover': '#1565C0',
        'btn_primary_pressed': '#0d47a1',
        'btn_success': '#27ae60',
        'btn_success_hover': '#1e8449',
        'btn_danger': '#e74c3c',
        'btn_danger_hover': '#c0392b',
        'btn_warning': '#f39c12',
        'btn_warning_hover': '#d68910',
        'btn_info': '#3498db',
        'btn_info_hover': '#2980b9',
        'btn_sidebar': '#b0bec5',
        'btn_sidebar_hover': '#ffffff',
        'btn_sidebar_active': '#ffffff',
        'border_primary': '#d5d8dc',
        'border_secondary': '#e5e8ec',
        'border_focus': '#1976D2',
        'border_sidebar': '#1976D2',
        'border_header': '#1976D2',
        'success': '#27ae60',
        'danger': '#e74c3c',
        'warning': '#f39c12',
        'info': '#3498db',
        'header_gradient_start': '#1a2332',
        'header_gradient_end': '#2c3e50',
        'sidebar_logo': '#e94560',
        'card_shadow': 'rgba(0,0,0,0.05)',
    }
    
    # ===== فونت‌ها =====
    fonts = {
        'family': '"Segoe UI", "Tahoma", "Vazirmatn", sans-serif',
        'size_small': '9pt',
        'size_normal': '10pt',
        'size_medium': '12pt',
        'size_large': '16pt',
        'size_xlarge': '20pt',
    }
    
    # ===== فاصله‌ها =====
    spacing = {
        'small': '4px',
        'normal': '8px',
        'medium': '12px',
        'large': '16px',
        'xlarge': '24px',
    }
    
    # ===== گوشه‌ها =====
    radius = {
        'small': '4px',
        'normal': '6px',
        'medium': '8px',
        'large': '12px',
        'xlarge': '16px',
    }
    
    def get_stylesheet(self) -> str:
        """دریافت استایل کامل CSS"""
        raise NotImplementedError("هر تم باید متد get_stylesheet را پیاده‌سازی کند")
    
    def get_colors(self) -> Dict[str, str]:
        return self.colors.copy()
    
    def get_fonts(self) -> Dict[str, str]:
        return self.fonts.copy()
