# ai/models/__init__.py

"""
مدل‌های ذخیره شده ImanAI
مسیر: ai/models/
"""

import os
from pathlib import Path

MODELS_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

def get_model_path(model_name: str) -> str:
    """دریافت مسیر کامل یک مدل"""
    return str(MODELS_DIR / f"{model_name}.pkl")

def get_tokenizer_path() -> str:
    """دریافت مسیر توکنایزر"""
    return str(MODELS_DIR / "tokenizer.pkl")

def get_training_data_path() -> str:
    """دریافت مسیر داده‌های آموزشی"""
    return str(MODELS_DIR / "training_data.json")

def get_vocab_path() -> str:
    """دریافت مسیر دیکشنری"""
    return str(MODELS_DIR / "vocabulary.json")

__all__ = [
    "MODELS_DIR",
    "get_model_path",
    "get_tokenizer_path",
    "get_training_data_path",
    "get_vocab_path",
]
