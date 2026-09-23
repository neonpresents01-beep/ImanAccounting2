# ai/model_trainer.py

"""
آموزش مدل‌های ImanAILite با داده‌های واقعی
نسخه 4.0.0
"""

import os
import sys
import numpy as np
from pathlib import Path
from datetime import datetime
import json

# اضافه کردن مسیر
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import ImanAILite as imanai
from .data_collector import AccountingDataCollector
from .transaction_classifier import TransactionClassifier
from .models import MODELS_DIR, get_model_path


class ModelTrainer:
    """آموزش و مدیریت مدل‌های ImanAILite"""
    
    def __init__(self):
        self.collector = AccountingDataCollector()
        self.ai = imanai.create_imanai(verbose=False)
        self.models_dir = MODELS_DIR
        
        print(f"📂 مسیر مدل‌ها: {self.models_dir}")

    def train_account_suggester(self, epochs: int = 50, force_retrain: bool = False):
        """آموزش مدل پیشنهاد حساب"""
        print("\n" + "=" * 60)
        print("🧠 آموزش مدل پیشنهاد حساب")
        print("=" * 60)
        
        # جمع‌آوری داده
        data = self.collector.collect_transaction_data()
        
        if len(data) < 10:
            print("⚠️ داده کافی برای آموزش وجود ندارد. از داده‌های نمونه استفاده می‌شود.")
            data = self._get_sample_data()
        
        texts, labels = zip(*data)
        
        # ساخت توکنایزر
        tokenizer = imanai.TextTokenizer(vocab_size=5000, max_len=50)
        tokenizer.build_vocab(texts)
        
        # تبدیل به بردار
        X = np.array([tokenizer.encode(t) for t in texts], dtype=np.float32)
        y = np.array(labels, dtype=np.float32)
        
        # ساخت مدل
        model = imanai.NeuralNetwork("AccountSuggester")
        model.add(imanai.Dense(X.shape[1], 64, 'relu'))
        model.add(imanai.Dropout(0.3))
        model.add(imanai.Dense(64, 32, 'relu'))
        model.add(imanai.Dense(32, len(set(labels)), 'softmax'))
        model.compile('cross_entropy', 'adam', 0.001)
        
        # آموزش
        history = model.fit(X, y, epochs=epochs, batch_size=32,
                           validation_split=0.2, verbose=True)
        
        # ذخیره
        model_path = self.models_dir / "account_suggester.pkl"
        tokenizer_path = self.models_dir / "tokenizer.pkl"
        
        model.save(str(model_path))
        tokenizer.save(str(tokenizer_path))
        
        print(f"\n✅ مدل پیشنهاد حساب در {model_path} ذخیره شد")
        print(f"✅ توکنایزر در {tokenizer_path} ذخیره شد")
        
        return model

    def _get_sample_data(self):
        """داده‌های نمونه برای آموزش اولیه"""
        return [
            ("واریز به صندوق", 0), ("برداشت از صندوق", 0),
            ("واریز به حساب بانک", 1), ("برداشت از بانک", 1),
            ("فروش کالا", 2), ("درآمد فروش", 2),
            ("خرید کالا", 3), ("فاکتور خرید", 3),
            ("پرداخت حقوق", 4), ("حقوق پرسنل", 4),
            ("پرداخت اجاره", 5), ("اجاره دفتر", 5),
            ("پرداخت قبض برق", 6), ("قبض آب", 6),
            ("تعمیرات ساختمان", 7), ("تعمیر کولر", 7),
        ]

    def train_transaction_classifier(self, epochs: int = 50):
        """آموزش مدل دسته‌بندی تراکنش"""
        classifier = TransactionClassifier()
        data = self.collector.collect_transaction_data()
        
        if len(data) < 10:
            print("⚠️ داده کافی برای آموزش دسته‌بندی نیست")
            return None
        
        texts, labels = zip(*data)
        result = classifier.train(list(texts), list(labels), epochs=epochs)
        
        return result

    def train_cashflow_predictor(self, epochs: int = 100):
        """آموزش مدل پیش‌بینی جریان نقدی"""
        from .cashflow_predictor import IntelligentCashFlowPredictor
        
        predictor = IntelligentCashFlowPredictor()
        cashflow_data = self.collector.collect_cashflow_data()
        
        if len(cashflow_data) < 12:
            print("⚠️ داده کافی برای آموزش جریان نقدی نیست")
            return None
        
        history = predictor.train(cashflow_data, epochs=epochs)
        return history
