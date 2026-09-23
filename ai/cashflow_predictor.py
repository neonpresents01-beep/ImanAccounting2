# ai/cashflow_predictor.py

"""
پیش‌بینی جریان نقدی با LSTM - ImanAILite v4.0.0
"""

import os
import sys
import numpy as np
from typing import List, Dict
from datetime import datetime
from pathlib import Path

# اضافه کردن مسیر
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import ImanAILite as imanai
from .models import MODELS_DIR, get_model_path


class IntelligentCashFlowPredictor:
    """پیش‌بینی هوشمند جریان نقدی با LSTM"""

    def __init__(self, sequence_length: int = 6):
        self.sequence_length = sequence_length
        self.ai = imanai.create_imanai(verbose=False)
        self.model_name = "CashFlowLSTM"
        self.models_dir = MODELS_DIR
        self.model_path = get_model_path("cashflow_lstm")
        self._build_or_load_model()

    def _build_or_load_model(self):
        """ساخت یا بارگذاری مدل LSTM"""
        if self.model_path.exists():
            try:
                self.ai.load(self.model_name, str(self.model_path))
                print(f"✅ مدل LSTM بارگذاری شد: {self.model_path}")
                return
            except:
                pass
        
        self.ai.create_lstm(
            self.model_name,
            input_dim=1,
            seq_len=self.sequence_length,
            hidden_dim=32,
            num_layers=1
        )
        print(f"✅ مدل LSTM جدید ساخته شد")

    def prepare_sequences(self, data: List[float]) -> tuple:
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            seq = data[i:i + self.sequence_length]
            target = data[i + self.sequence_length]
            X.append(seq)
            y.append(target)
        if not X:
            return None, None
        X = np.array(X, dtype=np.float32).reshape(-1, self.sequence_length, 1)
        y = np.array(y, dtype=np.float32).reshape(-1, 1)
        return X, y

    def train(self, historical_data: List[float], epochs: int = 100):
        X, y = self.prepare_sequences(historical_data)
        if X is None:
            print("❌ داده کافی برای آموزش نیست")
            return
        
        print(f"🚀 آموزش LSTM با {len(X)} نمونه...")
        history = self.ai.train(self.model_name, X, y,
                               epochs=epochs, batch_size=8,
                               lr=0.001,
                               validation_split=0.1,
                               verbose=True)
        
        # ذخیره مدل
        self.ai.save(self.model_name, str(self.model_path))
        print(f"💾 مدل LSTM ذخیره شد: {self.model_path}")
        
        return history

    def predict_next(self, recent_data: List[float], steps: int = 3) -> List[Dict]:
        if len(recent_data) < self.sequence_length:
            return self._simple_predict(recent_data, steps)
        
        predictions = []
        current_seq = recent_data[-self.sequence_length:].copy()
        
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        current_month = datetime.now().month - 1
        
        for i in range(steps):
            X = np.array(current_seq, dtype=np.float32).reshape(1, self.sequence_length, 1)
            try:
                pred = self.ai.predict(self.model_name, X)[0][0]
            except:
                pred = np.mean(current_seq[-3:])
            
            predictions.append({
                "month": month_names[(current_month + i + 1) % 12],
                "predicted_balance": round(float(pred), -3),
                "confidence": max(0.5, 0.9 - (i * 0.1))
            })
            current_seq = current_seq[1:] + [pred]
        
        return predictions

    def _simple_predict(self, data: List[float], steps: int) -> List[Dict]:
        if not data:
            return []
        avg_change = (data[-1] - data[0]) / max(len(data) - 1, 1) if len(data) > 1 else 0
        predictions = []
        last = data[-1]
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        current_month = datetime.now().month - 1
        for i in range(steps):
            pred = last + (avg_change * (i + 1))
            predictions.append({
                "month": month_names[(current_month + i + 1) % 12],
                "predicted_balance": round(pred, -3),
                "confidence": 0.6
            })
        return predictions
