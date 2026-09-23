# ai/data_collector.py

"""
جمع‌آوری داده‌های آموزشی از اسناد حسابداری موجود
"""

import os
import sys
import sqlite3
import numpy as np
import re
import json
from typing import List, Tuple, Dict
from pathlib import Path
from datetime import datetime

# اضافه کردن مسیر
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from .models import MODELS_DIR


APPDATA = os.environ.get('APPDATA', os.getcwd())
DB_DIR = Path(APPDATA) / "ParsehAccounting"
REAL_DB_PATH = str(DB_DIR / "accounting.db")


class AccountingDataCollector:
    """جمع‌آوری داده‌های آموزشی از دیتابیس"""
    
    ACCOUNT_TO_CLASS = {
        "1101": 0, "1102": 1, "4101": 2, "5101": 3,
        "5102": 4, "5103": 5, "5104": 6, "5105": 7,
    }
    
    def __init__(self, db_path: str = None):
        self.db_path = REAL_DB_PATH if db_path is None else db_path
        self.training_data = []
        self.models_dir = MODELS_DIR
        print(f"📂 دیتابیس: {self.db_path}")
        print(f"📂 مدل‌ها: {self.models_dir}")

    def collect_transaction_data(self) -> List[Tuple[str, int]]:
        """جمع‌آوری داده از دیتابیس"""
        if not Path(self.db_path).exists():
            print(f"⚠️ دیتابیس وجود ندارد: {self.db_path}")
            return []
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''
                SELECT vi.description, vi.account_code, v.description as voucher_desc
                FROM voucher_items vi
                JOIN vouchers v ON vi.voucher_id = v.id
                WHERE vi.account_code IN ('1101', '1102', '4101', '5101', '5102', '5103', '5104', '5105')
                AND (vi.description IS NOT NULL OR v.description IS NOT NULL)
                ORDER BY v.date DESC
                LIMIT 10000
            ''')
            
            data = []
            for row in c.fetchall():
                item_desc = row[0] or ""
                account_code = row[1]
                voucher_desc = row[2] or ""
                full_desc = f"{voucher_desc} {item_desc}".strip()
                
                if full_desc and account_code in self.ACCOUNT_TO_CLASS:
                    data.append((self._clean_text(full_desc), self.ACCOUNT_TO_CLASS[account_code]))
        except sqlite3.OperationalError as e:
            print(f"⚠️ خطا در خواندن دیتابیس: {e}")
            return []
        finally:
            conn.close()
        
        print(f"✅ {len(data)} تراکنش از دیتابیس جمع‌آوری شد")
        self.training_data = data
        return data

    def collect_cashflow_data(self) -> List[float]:
        """جمع‌آوری داده جریان نقدی"""
        if not Path(self.db_path).exists():
            return []
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''
                SELECT
                    strftime('%Y-%m', v.date) as month,
                    SUM(CASE WHEN vi.account_code = '1102' THEN vi.debit - vi.credit ELSE 0 END) as balance_change
                FROM voucher_items vi
                JOIN vouchers v ON vi.voucher_id = v.id
                GROUP BY strftime('%Y-%m', v.date)
                ORDER BY month
            ''')
            
            balances = []
            running_balance = 0
            for row in c.fetchall():
                running_balance += row[1] or 0
                balances.append(running_balance)
        except:
            balances = []
        finally:
            conn.close()
        
        print(f"✅ داده‌های جریان نقدی برای {len(balances)} ماه جمع‌آوری شد")
        return balances

    def collect_anomaly_data(self) -> List[Dict]:
        """جمع‌آوری داده ناهنجاری‌ها"""
        if not Path(self.db_path).exists():
            return []
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''
                SELECT
                    v.id,
                    v.description,
                    SUM(vi.debit) as total_debit,
                    SUM(vi.credit) as total_credit,
                    ABS(SUM(vi.debit) - SUM(vi.credit)) as diff
                FROM vouchers v
                JOIN voucher_items vi ON v.id = vi.voucher_id
                GROUP BY v.id
                HAVING diff > 0
            ''')
            
            anomalies = []
            for row in c.fetchall():
                anomalies.append({
                    "voucher_id": row[0],
                    "description": row[1],
                    "total_debit": row[2],
                    "total_credit": row[3],
                    "difference": row[4],
                    "is_anomaly": True
                })
        except:
            anomalies = []
        finally:
            conn.close()
        
        print(f"✅ {len(anomalies)} ناهنجاری شناسایی شد")
        return anomalies

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'[،,\.\/\\\-_:;()\[\]{}«»""\'\']', ' ', text)
        text = ' '.join(text.split())
        return text.lower()

    def save_training_data(self):
        """ذخیره داده‌های آموزشی در ai/models/"""
        output_dir = self.models_dir
        
        if self.training_data:
            with open(output_dir / "transactions.json", "w", encoding="utf-8") as f:
                json.dump([
                    {"text": text, "label": label}
                    for text, label in self.training_data
                ], f, ensure_ascii=False, indent=2)

        cashflow = self.collect_cashflow_data()
        if cashflow:
            with open(output_dir / "cashflow.json", "w", encoding="utf-8") as f:
                json.dump(cashflow, f, indent=2)
        
        print(f"💾 داده‌های آموزشی در {output_dir} ذخیره شدند")

    def load_training_data(self):
        """بارگذاری داده‌های آموزشی از ai/models/"""
        input_dir = self.models_dir
        
        trans_file = input_dir / "transactions.json"
        if trans_file.exists():
            with open(trans_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.training_data = [(d["text"], d["label"]) for d in data]
                print(f"📂 {len(self.training_data)} تراکنش بارگذاری شد")
        
        cashflow_file = input_dir / "cashflow.json"
        if cashflow_file.exists():
            with open(cashflow_file, "r", encoding="utf-8") as f:
                self.cashflow_data = json.load(f)
                print(f"📂 {len(self.cashflow_data)} ماه داده جریان نقدی بارگذاری شد")
        
        return self.training_data
