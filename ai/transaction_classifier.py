# ai/transaction_classifier.py

"""
دسته‌بندی هوشمند تراکنش‌های حسابداری با ImanAILite v4.0.0
"""

import os
import sys
import re
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter

# اضافه کردن مسیر
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import ImanAILite as imanai
from .models import MODELS_DIR, get_model_path, get_tokenizer_path, get_vocab_path


class TransactionClassifier:
    """دسته‌بندی هوشمند تراکنش‌های حسابداری"""
    
    CLASS_TO_ACCOUNT = {
        0: {"code": "1101", "name": "صندوق", "type": "asset"},
        1: {"code": "1102", "name": "بانک", "type": "asset"},
        2: {"code": "4101", "name": "فروش کالا", "type": "income"},
        3: {"code": "5101", "name": "خرید کالا", "type": "expense"},
        4: {"code": "5102", "name": "هزینه حقوق", "type": "expense"},
        5: {"code": "5103", "name": "هزینه اجاره", "type": "expense"},
        6: {"code": "5104", "name": "هزینه آب و برق", "type": "expense"},
        7: {"code": "5105", "name": "هزینه تعمیرات", "type": "expense"},
    }
    
    KEYWORDS = {
        "1101": ["صندوق", "نقد", "دریافت نقدی", "پرداخت نقدی"],
        "1102": ["بانک", "واریز", "برداشت", "کارت", "شبا", "ساتنا"],
        "4101": ["فروش", "درآمد", "فاکتور فروش", "مشتری", "رسید فروش"],
        "5101": ["خرید", "کالا", "جنس", "محصول", "دیجیکالا", "فاکتور خرید"],
        "5102": ["حقوق", "دستمزد", "پرسنل", "کارمند", "عیدی", "پاداش"],
        "5103": ["اجاره", "رهن", "ساختمان", "دفتر", "مغازه"],
        "5104": ["آب", "برق", "گاز", "تلفن", "اینترنت", "قبض"],
        "5105": ["تعمیر", "سرویس", "نگهداری", "تعمیرات", "بازسازی"],
    }
    
    def __init__(self):
        self.model_name = "TransactionClassifier"
        self.vocab = []
        self.num_classes = len(self.CLASS_TO_ACCOUNT)
        self.is_trained = False
        self.model = None
        
        # ========== مسیر مدل‌ها ==========
        self.model_dir = MODELS_DIR
        self.model_path = get_model_path("transaction_classifier")
        self.vocab_path = get_vocab_path()
        
        print(f"📂 مسیر مدل دسته‌بندی: {self.model_dir}")
        
        # بارگذاری مدل
        self._load_model()
    
    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\d+', ' ', text)
        text = re.sub(r'[،,\.\/\\\-_:;()\[\]{}«»""\'\'؟!]', ' ', text)
        text = text.replace('ي', 'ی').replace('ك', 'ک')
        return text.lower().strip()
    
    def _vectorize(self, text: str) -> np.ndarray:
        vec = np.zeros(len(self.vocab), dtype=np.float32)
        words = self._clean_text(text).split()
        
        for i, word in enumerate(self.vocab):
            if word in words:
                vec[i] = 1.0
            elif any(word in w or w in word for w in words):
                vec[i] = 0.5
        return vec
    
    def _build_model(self):
        """ساخت مدل با ImanAILite"""
        input_dim = len(self.vocab) if self.vocab else 100
        
        self.model = imanai.NeuralNetwork(self.model_name)
        self.model.add(imanai.Dense(input_dim, 64, 'relu'))
        self.model.add(imanai.Dropout(0.3))
        self.model.add(imanai.Dense(64, 32, 'relu'))
        self.model.add(imanai.Dense(32, self.num_classes, 'softmax'))
        self.model.compile('cross_entropy', 'adam', 0.001)
        self.is_trained = True
        
        print(f"✅ مدل دسته‌بندی ساخته شد (input_dim={input_dim})")
    
    def predict(self, description: str) -> Dict:
        """پیش‌بینی حساب"""
        if not description or not description.strip():
            return {
                "account_code": "5101",
                "account_name": "خرید کالا",
                "account_type": "expense",
                "confidence": 0.0,
                "method": "empty_input"
            }
        
        if self.model and self.is_trained and len(self.vocab) > 0:
            try:
                vec = self._vectorize(description).reshape(1, -1)
                probs = self.model.predict(vec)[0]
                if len(probs.shape) > 1:
                    probs = probs.flatten()
                pred_class = int(np.argmax(probs))
                confidence = float(probs[pred_class])
                account = self.CLASS_TO_ACCOUNT[pred_class]
                
                return {
                    "account_code": account["code"],
                    "account_name": account["name"],
                    "account_type": account["type"],
                    "confidence": round(confidence, 3),
                    "method": "neural_network",
                    "class_id": pred_class
                }
            except Exception as e:
                print(f"⚠️ خطا در پیش‌بینی: {e}")
        
        return self._keyword_predict(description)
    
    def _keyword_predict(self, text: str) -> Dict:
        """پیش‌بینی با کلمات کلیدی"""
        text = self._clean_text(text)
        scores = {code: 0.0 for code in self.KEYWORDS.keys()}
        
        for code, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[code] += 1.0
                kw_words = kw.split()
                if len(kw_words) > 1:
                    matches = sum(1 for w in kw_words if w in text)
                    scores[code] += matches * 0.5
        
        max_score = max(scores.values()) if scores else 0
        
        if max_score > 0:
            best_code = max(scores, key=scores.get)
            confidence = min(max_score / 3, 0.8)
            account = next(v for v in self.CLASS_TO_ACCOUNT.values() if v["code"] == best_code)
            return {
                "account_code": best_code,
                "account_name": account["name"],
                "account_type": account["type"],
                "confidence": round(confidence, 3),
                "method": "keyword_matching"
            }
        
        return {
            "account_code": "5101",
            "account_name": "خرید کالا",
            "account_type": "expense",
            "confidence": 0.3,
            "method": "default"
        }
    
    def train(self, texts: List[str], labels: List[int], epochs: int = 50,
              validation_split: float = 0.2, save: bool = True) -> Dict:
        """آموزش مدل"""
        print("\n" + "=" * 60)
        print("🧠 آموزش مدل دسته‌بندی تراکنش (ImanAILite v4.0.0)")
        print("=" * 60)
        
        if len(texts) == 0:
            raise ValueError("داده‌ای برای آموزش وجود ندارد")
        
        self._build_vocabulary(texts)
        print(f"📚 دایره لغات: {len(self.vocab)} کلمه")
        
        self._build_model()
        
        X = np.array([self._vectorize(t) for t in texts], dtype=np.float32)
        y = np.zeros((len(labels), self.num_classes))
        y[np.arange(len(labels)), labels] = 1
        
        print(f"📊 شکل داده: X={X.shape}, y={y.shape}")
        
        history = self.model.fit(X, y, epochs=epochs, batch_size=32,
                                 validation_split=validation_split, verbose=True)
        
        self.is_trained = True
        
        if save:
            self.save()
        
        print(f"\n✅ آموزش با موفقیت به پایان رسید!")
        
        return {
            "history": history,
            "samples": len(texts),
            "vocab_size": len(self.vocab)
        }
    
    def _build_vocabulary(self, texts: List[str], min_freq: int = 2):
        all_words = []
        for text in texts:
            cleaned = self._clean_text(text)
            all_words.extend(cleaned.split())
        
        word_counts = Counter(all_words)
        vocab = [word for word, count in word_counts.items() if count >= min_freq]
        
        for keywords in self.KEYWORDS.values():
            for kw in keywords:
                for word in kw.split():
                    if word not in vocab:
                        vocab.append(word)
        
        self.vocab = sorted(set(vocab))
        print(f"✅ دایره لغات با {len(self.vocab)} کلمه ساخته شد")
    
    def _init_default_vocab(self):
        default_words = set()
        for keywords in self.KEYWORDS.values():
            for kw in keywords:
                default_words.update(kw.split())
        self.vocab = sorted(list(default_words))
        self.is_trained = False
    
    def save(self):
        """ذخیره مدل در ai/models/"""
        if self.model:
            self.model.save(str(self.model_path))
        
        with open(self.vocab_path, "w", encoding="utf-8") as f:
            json.dump({
                "vocab": self.vocab,
                "vocab_size": len(self.vocab),
                "class_mapping": self.CLASS_TO_ACCOUNT
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 مدل دسته‌بندی در {self.model_path} ذخیره شد")
    
    def _load_model(self):
        """بارگذاری مدل از ai/models/"""
        try:
            if self.model_path.exists():
                with open(self.vocab_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.vocab = data["vocab"]
                
                self._build_model()
                if self.model_path.exists():
                    self.model.load(str(self.model_path))
                    self.is_trained = True
                    print(f"✅ مدل دسته‌بندی بارگذاری شد: {self.model_path}")
            else:
                print("ℹ️ مدل دسته‌بندی یافت نشد")
                self._init_default_vocab()
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری مدل دسته‌بندی: {e}")
            self._init_default_vocab()
    
    def get_model_info(self) -> Dict:
        return {
            "is_trained": self.is_trained,
            "vocab_size": len(self.vocab),
            "num_classes": self.num_classes,
            "classes": self.CLASS_TO_ACCOUNT
        }
