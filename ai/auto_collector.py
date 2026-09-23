# ai/auto_collector.py

"""
AutoCollector - جمع‌آوری خودکار داده از دیتابیس ImanAccount
و به‌روزرسانی مدل ImanAILite
"""

import os
import sys
import time
import json
import threading
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

# اضافه کردن مسیر
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import ImanAILite as imanai
from database import get_db
from .models import MODELS_DIR


class AutoCollector(QObject):
    """جمع‌آوری خودکار داده از دیتابیس و به‌روزرسانی مدل"""
    
    # سیگنال‌ها
    collection_started = pyqtSignal()
    collection_progress = pyqtSignal(int, str)
    collection_completed = pyqtSignal(dict)
    model_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, interval_minutes: int = 30):
        super().__init__()
        self.interval_minutes = interval_minutes
        self.is_running = False
        self.is_collecting = False
        self.last_collection = None
        
        # ========== مسیر مدل‌ها ==========
        self.model_dir = MODELS_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📂 مسیر مدل‌ها (AutoCollector): {self.model_dir}")
        
        # مدل و توکنایزر
        self.model = None
        self.tokenizer = None
        self.is_ai_ready = False
        
        # داده‌های جمع‌آوری شده
        self.collected_data = []
        self.training_history = deque(maxlen=100)
        
        # نقشه حساب‌ها به کلاس‌ها
        self.account_to_class = {
            "1101": 0, "1102": 1, "1201": 2, "1301": 3,
            "2101": 4, "2102": 5, "3101": 6,
            "4101": 7, "4102": 8,
            "5101": 9, "5102": 10, "5103": 11, "5104": 12, "5105": 13, "5106": 14,
        }
        
        # بارگذاری مدل
        self._load_model()
        
        # شروع تایمر
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_and_collect)
        self.timer.start(60000)  # هر ۱ دقیقه چک کن
        
        print(f"✅ AutoCollector راه‌اندازی شد (هر {interval_minutes} دقیقه)")
    
    def _load_model(self):
        """بارگذاری مدل از ai/models/"""
        try:
            model_path = self.model_dir / "account_suggester.pkl"
            tokenizer_path = self.model_dir / "tokenizer.pkl"
            
            if model_path.exists() and tokenizer_path.exists():
                self.model = imanai.NeuralNetwork()
                self.model.load(str(model_path))
                self.tokenizer = imanai.TextTokenizer()
                self.tokenizer.load(str(tokenizer_path))
                self.is_ai_ready = True
                print(f"✅ مدل بارگذاری شد: {model_path}")
            else:
                print("⚠️ مدل موجود نیست، مدل جدید ساخته می‌شود")
                self._create_new_model()
                
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری مدل: {e}")
            self._create_new_model()
    
    def _create_new_model(self):
        """ایجاد مدل جدید در ai/models/"""
        try:
            self.tokenizer = imanai.TextTokenizer(vocab_size=5000, max_len=50)
            
            self.model = imanai.NeuralNetwork("AccountSuggester")
            self.model.add(imanai.Dense(50, 64, 'relu'))
            self.model.add(imanai.Dropout(0.3))
            self.model.add(imanai.Dense(64, 32, 'relu'))
            self.model.add(imanai.Dense(32, len(self.account_to_class), 'softmax'))
            self.model.compile('cross_entropy', 'adam', 0.001)
            self.is_ai_ready = True
            
            self._save_model()
            print(f"✅ مدل جدید ایجاد شد: {self.model_dir}")
            
        except Exception as e:
            print(f"❌ خطا در ایجاد مدل: {e}")
    
    def _save_model(self):
        """ذخیره مدل در ai/models/"""
        if self.model:
            self.model.save(str(self.model_dir / "account_suggester.pkl"))
        
        if self.tokenizer:
            self.tokenizer.save(str(self.model_dir / "tokenizer.pkl"))
        
        print(f"💾 مدل ذخیره شد: {self.model_dir}")
    
    def check_and_collect(self):
        if self.is_collecting:
            return
        
        if self.last_collection is None:
            self.start_collection()
            return
        
        elapsed = (datetime.now() - self.last_collection).total_seconds() / 60
        if elapsed >= self.interval_minutes:
            self.start_collection()
    
    def start_collection(self):
        if self.is_collecting:
            return
        
        self.is_collecting = True
        self.collection_started.emit()
        
        thread = threading.Thread(target=self._collect_thread)
        thread.daemon = True
        thread.start()
    
    def _collect_thread(self):
        try:
            self.collection_progress.emit(10, "📊 جمع‌آوری داده از دیتابیس...")
            
            new_data = self._collect_from_database()
            
            if not new_data:
                self.collection_progress.emit(100, "⚠️ داده جدیدی یافت نشد")
                self.is_collecting = False
                self.last_collection = datetime.now()
                return
            
            self.collection_progress.emit(30, f"🧠 {len(new_data)} داده جدید پیدا شد")
            
            all_data = self._combine_data(new_data)
            
            self.collection_progress.emit(50, "📚 آماده‌سازی داده برای آموزش...")
            
            result = self._train_model(all_data)
            
            self.collection_progress.emit(80, "💾 ذخیره مدل...")
            
            self._save_model()
            
            self.collection_progress.emit(100, f"✅ مدل به‌روز شد! ({len(new_data)} داده جدید)")
            
            self.collection_completed.emit({
                "new_samples": len(new_data),
                "total_samples": len(all_data),
                "vocab_size": len(self.tokenizer.vocab) if self.tokenizer else 0,
                "timestamp": datetime.now().isoformat()
            })
            
            self.model_updated.emit({
                "samples": len(all_data),
                "vocab": len(self.tokenizer.vocab) if self.tokenizer else 0,
                "time": datetime.now().strftime("%H:%M")
            })
            
            self.last_collection = datetime.now()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            print(f"❌ خطا در جمع‌آوری: {e}")
        
        finally:
            self.is_collecting = False
    
    def _collect_from_database(self) -> list:
        data = []
        try:
            with get_db() as conn:
                c = conn.cursor()
                account_codes = list(self.account_to_class.keys())
                placeholders = ','.join(['?'] * len(account_codes))
                
                if self.last_collection:
                    last_time = self.last_collection.strftime("%Y-%m-%d %H:%M:%S")
                    c.execute(f'''
                        SELECT vi.description, vi.account_code, v.description as voucher_desc
                        FROM voucher_items vi
                        JOIN vouchers v ON vi.voucher_id = v.id
                        WHERE vi.account_code IN ({placeholders})
                        AND (vi.description IS NOT NULL OR v.description IS NOT NULL)
                        AND v.created_at > ?
                        ORDER BY v.id DESC
                        LIMIT 500
                    ''', account_codes + [last_time])
                else:
                    c.execute(f'''
                        SELECT vi.description, vi.account_code, v.description as voucher_desc
                        FROM voucher_items vi
                        JOIN vouchers v ON vi.voucher_id = v.id
                        WHERE vi.account_code IN ({placeholders})
                        AND (vi.description IS NOT NULL OR v.description IS NOT NULL)
                        ORDER BY v.id DESC
                        LIMIT 1000
                    ''', account_codes)
                
                for row in c.fetchall():
                    item_desc = row[0] or ""
                    account_code = row[1]
                    voucher_desc = row[2] or ""
                    full_desc = f"{voucher_desc} {item_desc}".strip()
                    
                    if full_desc and account_code in self.account_to_class:
                        data.append({
                            "description": full_desc,
                            "account_code": account_code,
                            "class": self.account_to_class[account_code]
                        })
        except Exception as e:
            print(f"⚠️ خطا در جمع‌آوری از دیتابیس: {e}")
        
        return data
    
    def _combine_data(self, new_data: list) -> list:
        existing_data = []
        data_path = self.model_dir / "training_data.json"
        if data_path.exists():
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                pass
        
        all_data = existing_data + new_data
        
        seen = set()
        unique_data = []
        for item in all_data:
            key = item["description"]
            if key not in seen:
                seen.add(key)
                unique_data.append(item)
        
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, ensure_ascii=False, indent=2)
        
        return unique_data
    
    def _train_model(self, data: list):
        if len(data) < 10:
            return {"status": "skipped", "reason": "not enough data"}
        
        texts = [item["description"] for item in data]
        labels = [item["class"] for item in data]
        
        if self.tokenizer:
            self.tokenizer.build_vocab(texts)
        else:
            self.tokenizer = imanai.TextTokenizer(vocab_size=5000, max_len=50)
            self.tokenizer.build_vocab(texts)
        
        X = np.array([self.tokenizer.encode(t) for t in texts], dtype=np.float32)
        y = np.array(labels, dtype=np.float32)
        
        if self.model:
            history = self.model.fit(
                X, y,
                epochs=20,
                batch_size=32,
                validation_split=0.2,
                verbose=True
            )
            
            return {
                "status": "success",
                "samples": len(data),
                "epochs": len(history),
                "final_loss": history[-1] if history else 0
            }
        
        return {"status": "failed", "reason": "model not available"}
    
    def get_stats(self) -> dict:
        data_path = self.model_dir / "training_data.json"
        sample_count = 0
        if data_path.exists():
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    sample_count = len(json.load(f))
            except:
                pass
        
        return {
            "is_running": self.is_running,
            "is_collecting": self.is_collecting,
            "last_collection": self.last_collection.strftime("%Y-%m-%d %H:%M") if self.last_collection else "هرگز",
            "interval_minutes": self.interval_minutes,
            "samples_collected": sample_count,
            "model_ready": self.is_ai_ready,
            "vocab_size": len(self.tokenizer.vocab) if self.tokenizer else 0
        }
    
    def force_collect(self):
        self.start_collection()
    
    def stop(self):
        self.is_running = False
        if self.timer:
            self.timer.stop()
