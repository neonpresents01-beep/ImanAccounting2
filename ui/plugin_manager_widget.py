# ui/plugin_manager_widget.py
# ============================================================
# ویجت مدیریت پلاگین‌ها با پشتیبانی از تم و سطح دسترسی
# ============================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui.base_widgets import BaseWidget
from ui.styles.theme_manager import get_theme_manager
import os
import json
import shutil
from pathlib import Path


class PluginManagerWidget(BaseWidget):
    """ویجت نمایش و مدیریت پلاگین‌ها با پشتیبانی از تم"""
    
    plugins_changed = pyqtSignal()
    
    def __init__(self, license_key: str = None, parent=None, user_level: str = 'viewer'):
        super().__init__(parent)
        self.license_key = license_key
        self._user_level = user_level
        self.plugin_manager = None
        self.plugins_dir = Path("plugins")
        
        # ThemeManager
        self.theme_manager = get_theme_manager()
        
        self._init_plugin_manager()
        self.init_ui()
        self.load_plugins_list()
        self.plugins_changed.connect(self.on_plugins_changed)
        self.update_ui_by_permission()
        
        # اتصال به تغییر تم
        self.theme_manager.add_observer(self.on_theme_changed)
        self.apply_theme()
    
    # ============================================================
    # مدیریت سطح دسترسی
    # ============================================================
    
    def set_user_level(self, level: str):
        """تنظیم سطح دسترسی"""
        self._user_level = level
        self.update_ui_by_permission()
    
    def update_ui_by_permission(self):
        """بروزرسانی UI بر اساس سطح دسترسی"""
        is_admin = self._user_level == 'admin'
        
        if hasattr(self, 'install_btn'):
            self.install_btn.setEnabled(is_admin)
        if hasattr(self, 'uninstall_btn'):
            self.uninstall_btn.setEnabled(is_admin)
        
        if not is_admin and hasattr(self, 'status_label'):
            self.status_label.setText("🔒 فقط مدیر سیستم می‌تواند پلاگین‌ها را مدیریت کند")
            self.status_label.setStyleSheet("color: #FF9800; padding: 5px; font-size: 9pt;")
    
    # ============================================================
    # مدیریت تم
    # ============================================================
    
    def on_theme_changed(self, theme_name: str):
        """هنگام تغییر تم"""
        self.apply_theme()
    
    def apply_theme(self):
        """اعمال تم روی ویجت"""
        theme_name = self.theme_manager.get_theme_name()
        is_dark = theme_name == 'dark'
        
        # رنگ‌های پویا
        bg_color = "#1a1a2e" if is_dark else "#f5f6fa"
        text_color = "#e0e0e0" if is_dark else "#1a1a2e"
        card_bg = "#1a1a3e" if is_dark else "#ffffff"
        card_bg_alt = "#0f0f23" if is_dark else "#f0f0f0"
        border_color = "#0f3460" if is_dark else "#dcdde1"
        header_bg = "#0f3460" if is_dark else "#e8e8e8"
        header_text = "#ffffff" if is_dark else "#1a1a2e"
        selected_bg = "#533483" if is_dark else "#4a90d9"
        selected_text = "#ffffff" if is_dark else "#ffffff"
        
        # استایل اصلی
        self.setStyleSheet(f"""
            QWidget {{
                background: {bg_color};
                color: {text_color};
            }}
            
            QLabel {{
                color: {text_color};
            }}
            
            QGroupBox {{
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                margin-top: 12px;
                font-weight: bold;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px;
                color: #e94560;
            }}
            
            QTableWidget {{
                background: {card_bg};
                color: {text_color};
                gridline-color: {border_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                alternate-background-color: {card_bg_alt};
            }}
            QTableWidget::item {{
                color: {text_color};
            }}
            QTableWidget::item:selected {{
                background: {selected_bg};
                color: {selected_text};
            }}
            QHeaderView::section {{
                background: {header_bg};
                color: {header_text};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
            
            QTextEdit {{
                background: {card_bg};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px;
            }}
            
            QPushButton {{
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:disabled {{
                background: #555;
                color: #888;
            }}
            
            QScrollBar:vertical {{
                background: {bg_color};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {border_color};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #e94560;
            }}
        """)
    
    # ============================================================
    # مقداردهی اولیه
    # ============================================================
    
    def _init_plugin_manager(self):
        """مقداردهی اولیه PluginManager"""
        try:
            from plugins.plugin_loader import PluginManager
            
            if self.license_key:
                self.plugin_manager = PluginManager(license_key=self.license_key)
            else:
                self.plugin_manager = PluginManager()
                
            print("✅ PluginManager مقداردهی شد")
        except ImportError as e:
            print(f"⚠️ خطا در بارگذاری PluginManager: {e}")
            self.plugin_manager = None
        except Exception as e:
            print(f"⚠️ خطا: {e}")
            self.plugin_manager = None
    
    # ============================================================
    # رابط کاربری
    # ============================================================
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # ========== هدر ==========
        header_layout = QHBoxLayout()
        
        title = QLabel("🧩 مدیریت پلاگین‌ها")
        title.setStyleSheet("""
            font-size: 16pt; 
            font-weight: bold; 
            padding: 10px; 
            color: #e94560;
        """)
        header_layout.addWidget(title)
        
        # وضعیت کلید عمومی
        self.public_key_status = QLabel()
        self.public_key_status.setStyleSheet("color: #aaa; font-size: 9pt; padding: 5px 10px; background: #2a2a3e; border-radius: 6px;")
        self.update_public_key_status()
        header_layout.addWidget(self.public_key_status)
        
        layout.addLayout(header_layout)
        
        # ========== نوار ابزار ==========
        toolbar = QHBoxLayout()
        
        self.install_btn = QPushButton("📦 نصب پلاگین جدید")
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        self.install_btn.clicked.connect(self.install_plugin)
        toolbar.addWidget(self.install_btn)
        
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        refresh_btn.clicked.connect(self.refresh_plugins)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # ========== جدول پلاگین‌ها ==========
        self.plugins_table = QTableWidget()
        self.plugins_table.setColumnCount(6)
        self.plugins_table.setHorizontalHeaderLabels([
            "نام", "نسخه", "شناسه", "توضیحات", "نویسنده", "وضعیت"
        ])
        self.plugins_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.plugins_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.plugins_table.horizontalHeader().setStretchLastSection(True)
        self.plugins_table.setAlternatingRowColors(True)
        layout.addWidget(self.plugins_table)
        
        # ========== دکمه‌های عملیات ==========
        btn_layout = QHBoxLayout()
        
        self.uninstall_btn = QPushButton("🗑️ حذف پلاگین")
        self.uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.uninstall_btn.clicked.connect(self.uninstall_plugin)
        btn_layout.addWidget(self.uninstall_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # ========== اطلاعات بیشتر ==========
        info_group = QGroupBox("📋 اطلاعات پلاگین")
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(120)
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # ========== وضعیت ==========
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; padding: 5px; font-size: 9pt;")
        layout.addWidget(self.status_label)
        
        self.plugins_table.clicked.connect(self.on_plugin_selected)
        
        # اعمال تم
        self.apply_theme()
    
    # ============================================================
    # توابع اصلی
    # ============================================================
    
    def update_public_key_status(self):
        """بروزرسانی وضعیت کلید عمومی"""
        if self.plugin_manager and hasattr(self.plugin_manager, 'loader'):
            public_key = getattr(self.plugin_manager.loader, 'public_key', None)
            if public_key:
                self.public_key_status.setText(f"🔑 کلید عمومی: {public_key[:25]}...")
                self.public_key_status.setStyleSheet("color: #4CAF50; font-size: 9pt; padding: 5px 10px; background: #1a3a1a; border-radius: 6px;")
            else:
                self.public_key_status.setText("⚠️ بدون کلید عمومی")
                self.public_key_status.setStyleSheet("color: #FF9800; font-size: 9pt; padding: 5px 10px; background: #3a2a1a; border-radius: 6px;")
        else:
            self.public_key_status.setText("⚠️ PluginManager در دسترس نیست")
            self.public_key_status.setStyleSheet("color: #e74c3c; font-size: 9pt; padding: 5px 10px; background: #3a1a1a; border-radius: 6px;")
    
    def load_plugins_list(self):
        """بارگذاری لیست پلاگین‌ها از پوشه"""
        plugins = self._scan_plugins_directory()
        
        self.plugins_table.setRowCount(len(plugins))
        
        for i, plugin in enumerate(plugins):
            self.plugins_table.setItem(i, 0, QTableWidgetItem(plugin.get('name', '-')))
            self.plugins_table.setItem(i, 1, QTableWidgetItem(plugin.get('version', '-')))
            self.plugins_table.setItem(i, 2, QTableWidgetItem(plugin.get('id', '-')))
            
            desc = plugin.get('description', '-')
            if len(desc) > 30:
                desc = desc[:30] + '...'
            self.plugins_table.setItem(i, 3, QTableWidgetItem(desc))
            
            self.plugins_table.setItem(i, 4, QTableWidgetItem(plugin.get('author', '-')))
            
            status_item = QTableWidgetItem("✅ نصب شده")
            status_item.setForeground(QColor('#4CAF50'))
            self.plugins_table.setItem(i, 5, status_item)
    
    def _scan_plugins_directory(self) -> list:
        """اسکن پوشه پلاگین‌ها"""
        plugins = []
        
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return plugins
        
        third_party_dir = self.plugins_dir / "third_party"
        if not third_party_dir.exists():
            third_party_dir.mkdir(parents=True, exist_ok=True)
            return plugins
        
        try:
            # اسکن فایل‌های .plugin
            for file_path in third_party_dir.glob("*.plugin"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        plugin_data = json.loads(content)
                        
                        plugins.append({
                            'id': plugin_data.get('id', file_path.stem),
                            'name': plugin_data.get('name', file_path.stem),
                            'version': plugin_data.get('version', '1.0.0'),
                            'description': plugin_data.get('description', ''),
                            'author': plugin_data.get('author', 'نامشخص'),
                            'path': str(file_path),
                            'manifest': plugin_data
                        })
                except Exception as e:
                    print(f"⚠️ خطا در خواندن {file_path}: {e}")
                    plugins.append({
                        'id': file_path.stem,
                        'name': file_path.stem,
                        'version': '?',
                        'description': f'⚠️ فایل خراب',
                        'author': 'نامشخص',
                        'path': str(file_path),
                        'manifest': {}
                    })
            
            # اسکن فایل‌های .py
            for file_path in third_party_dir.glob("*.py"):
                if file_path.name == "__init__.py":
                    continue
                try:
                    plugin_id = file_path.stem
                    if not any(p.get('id') == plugin_id for p in plugins):
                        plugins.append({
                            'id': plugin_id,
                            'name': file_path.stem,
                            'version': '1.0.0',
                            'description': 'پلاگین پایتون',
                            'author': 'نامشخص',
                            'path': str(file_path),
                            'manifest': {}
                        })
                except Exception as e:
                    print(f"⚠️ خطا در خواندن {file_path}: {e}")
                    
        except Exception as e:
            print(f"⚠️ خطا در اسکن پلاگین‌ها: {e}")
        
        return plugins
    
    def on_plugin_selected(self):
        """هنگام انتخاب پلاگین در جدول"""
        current_row = self.plugins_table.currentRow()
        if current_row >= 0:
            plugin_id = self.plugins_table.item(current_row, 2).text()
            self.show_plugin_info(plugin_id)
    
    def show_plugin_info(self, plugin_id: str):
        """نمایش اطلاعات پلاگین"""
        plugins = self._scan_plugins_directory()
        
        for plugin in plugins:
            if plugin.get('id') == plugin_id:
                manifest = plugin.get('manifest', {})
                
                info = f"""
<h3 style="color: #e94560;">{plugin.get('name', '-')}</h3>
<hr>
<table style="width: 100%; color: #ddd;">
<tr><td><b>شناسه:</b></td><td>{plugin.get('id', '-')}</td></tr>
<tr><td><b>نسخه:</b></td><td>{plugin.get('version', '-')}</td></tr>
<tr><td><b>توضیحات:</b></td><td>{plugin.get('description', '-')}</td></tr>
<tr><td><b>نویسنده:</b></td><td>{plugin.get('author', '-')}</td></tr>
<tr><td><b>مسیر:</b></td><td style="font-size: 9pt; color: #888;">{plugin.get('path', '-')}</td></tr>
<tr><td><b>مجوزها:</b></td><td>{', '.join(manifest.get('permissions', []))}</td></tr>
</table>
                """
                self.info_text.setHtml(info)
                break
    
    def install_plugin(self):
        """نصب پلاگین جدید"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل پلاگین", "", "Plugin Files (*.plugin);;Python Files (*.py);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            third_party_dir = self.plugins_dir / "third_party"
            third_party_dir.mkdir(parents=True, exist_ok=True)
            
            dest_path = third_party_dir / Path(file_path).name
            
            if dest_path.exists():
                base = dest_path.stem
                ext = dest_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = third_party_dir / f"{base}_{counter}{ext}"
                    counter += 1
            
            shutil.copy2(file_path, dest_path)
            
            self.refresh_plugins()
            self.plugins_changed.emit()
            
            QMessageBox.information(self, "موفق", f"✅ پلاگین با موفقیت نصب شد!\n📁 مسیر: {dest_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در نصب پلاگین:\n{str(e)}")
    
    def uninstall_plugin(self):
        """حذف پلاگین"""
        current_row = self.plugins_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "خطا", "یک پلاگین انتخاب کنید!")
            return
        
        plugin_name = self.plugins_table.item(current_row, 0).text()
        plugin_id = self.plugins_table.item(current_row, 2).text()
        
        plugins = self._scan_plugins_directory()
        plugin_path = None
        
        for plugin in plugins:
            if plugin.get('id') == plugin_id:
                plugin_path = plugin.get('path')
                break
        
        if not plugin_path:
            QMessageBox.warning(self, "خطا", "مسیر پلاگین پیدا نشد!")
            return
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف پلاگین '{plugin_name}' اطمینان دارید؟\n\n📁 {plugin_path}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = False
                
                if self.plugin_manager:
                    try:
                        success = self.plugin_manager.uninstall_plugin(plugin_id)
                    except Exception as e:
                        print(f"   ⚠️ خطا در plugin_manager: {e}")
                
                if not success and plugin_path and os.path.exists(plugin_path):
                    try:
                        os.remove(plugin_path)
                        success = True
                    except PermissionError:
                        QMessageBox.warning(self, "خطا", "❌ خطا: فایل در حال استفاده است!\nلطفاً برنامه را ببندید و دوباره تلاش کنید.")
                        return
                    except Exception as e:
                        print(f"   ❌ خطا در حذف مستقیم: {e}")
                
                if success:
                    third_party_dir = self.plugins_dir / "third_party"
                    for cache_file in third_party_dir.glob(f"__pycache__/{plugin_id}*.pyc"):
                        try:
                            os.remove(cache_file)
                        except:
                            pass
                    
                    self.refresh_plugins()
                    self.plugins_changed.emit()
                    self.info_text.clear()
                    QMessageBox.information(self, "موفق", f"✅ پلاگین '{plugin_name}' با موفقیت حذف شد!")
                else:
                    QMessageBox.warning(self, "خطا", "❌ خطا در حذف پلاگین!")
                    
            except Exception as e:
                QMessageBox.warning(self, "خطا", f"❌ خطا در حذف پلاگین:\n{str(e)}")
    
    def on_plugins_changed(self):
        """بروزرسانی منوهای اصلی"""
        try:
            main_window = self.window()
            if hasattr(main_window, 'rebuild_plugin_menus'):
                main_window.rebuild_plugin_menus()
            if hasattr(main_window, 'rebuild_plugin_tabs'):
                main_window.rebuild_plugin_tabs()
        except Exception as e:
            print(f"خطا در بروزرسانی منوهای پلاگین: {e}")
    
    def refresh_plugins(self):
        """بروزرسانی لیست پلاگین‌ها"""
        self.load_plugins_list()
        self.info_text.clear()
        self.update_public_key_status()
