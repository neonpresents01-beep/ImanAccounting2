# ai/__init__.py

"""
ماژول هوش مصنوعی ImanAI برای سیستم پارسه
نسخه 4.0.0 - با آموزش خودکار و جمع‌آوری داده
"""

import os
from pathlib import Path

# ========== مسیر مدل‌ها ==========
AI_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = AI_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

from .transaction_classifier import TransactionClassifier
from .cashflow_predictor import IntelligentCashFlowPredictor
from .data_collector import AccountingDataCollector
from .model_trainer import ModelTrainer
from .intelligent_voice_assistant import IntelligentVoiceAssistant
from .auto_collector import AutoCollector

__all__ = [
    "TransactionClassifier",
    "IntelligentCashFlowPredictor",
    "AccountingDataCollector",
    "ModelTrainer",
    "IntelligentVoiceAssistant",
    "AutoCollector",
    "MODELS_DIR",
]
