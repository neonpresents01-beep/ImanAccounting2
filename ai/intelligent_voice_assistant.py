#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
دستیار صوتی هوشمند - با قابلیت درک زبان طبیعی
"""

import re
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from collections import Counter

from ImanAILite import ImanAILite
from database import get_db, AccountingHelper
from date_utils import DateUtils


class IntentRecognizer:
    """تشخیص قصد کاربر با کلمات کلیدی هوشمند"""

    INTENTS = {
        "get_balance": ["موجودی", "مانده", "چقدر داره", "چقدر است"],
        "get_profit": ["سود", "زیان", "سودآوری", "بازده"],
        "get_sales": ["فروش", "درآمد", "فروش داشتیم"],
        "get_expenses": ["هزینه", "خرج", "هزینه‌ها"],
        "create_voucher": ["ثبت سند", "سند جدید", "ثبت کن", "اضافه کن"],
        "create_invoice": ["فاکتور", "خرید", "فروش", "ثبت فاکتور"],
        "search_voucher": ["پیدا کن", "جستجو", "بگرد", "سند شماره"],
        "search_customer": ["مشتری", "خریدار", "اطلاعات مشتری"],
        "search_product": ["کالا", "محصول", "موجودی"],
        "predict": ["پیش‌بینی", "پیش بینی", "چه میشود", "آینده"],
        "help": ["راهنما", "کمک", "چطور کار کنم"],
        "greeting": ["سلام", "درود", "صبح بخیر", "عصر بخیر", "هی"],
        "goodbye": ["خداحافظ", "بای", "فعلا"],
        "date": ["تاریخ", "امروز چه روزیه", "چندمه"],
        "time": ["ساعت", "چند وقته", "زمان"],
    }

    def __init__(self):
        self.vocab = []
        self._build_vocab()

    def _build_vocab(self):
        all_words = set()
        for intent, keywords in self.INTENTS.items():
            for kw in keywords:
                for word in kw.split():
                    all_words.add(word)
        self.vocab = list(all_words)

    def recognize(self, text: str) -> Tuple[str, float]:
        text = text.lower()
        scores = {}

        for intent, keywords in self.INTENTS.items():
            score = 0
            for kw in keywords:
                if kw in text:
                    score += 1
                kw_parts = kw.split()
                if len(kw_parts) > 1:
                    matches = sum(1 for p in kw_parts if p in text)
                    if matches == len(kw_parts):
                        score += 2
            if score > 0:
                scores[intent] = score

        if scores:
            best_intent = max(scores, key=scores.get)
            max_score = scores[best_intent]
            confidence = min(max_score / 5, 0.95)
            return best_intent, confidence

        return "unknown", 0.0


class EntityExtractor:
    """استخراج موجودیت‌ها از متن"""

    def __init__(self):
        self.patterns = {
            "amount": r'(\d+)(?:[\s,]?(\d+))?\s*(میلیون|هزار|تومان|ریال)?',
            "number": r'شماره\s*(\d+)',
            "customer": r'مشتری\s*["\']?([^"\']+)["\']?',
            "supplier": r'تأمین[\s]*کننده\s*["\']?([^"\']+)["\']?',
            "product": r'کالا\s*["\']?([^"\']+)["\']?',
            "month": r'(فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند)',
        }

    def extract(self, text: str, intent: str) -> Dict:
        entities = {}

        amount_match = re.search(self.patterns["amount"], text)
        if amount_match:
            try:
                num1 = int(amount_match.group(1))
                num2 = int(amount_match.group(2)) if amount_match.group(2) else 0
                amount = num1 * 1000000 + num2 * 1000 if num2 else num1

                unit = amount_match.group(3) or "ریال"
                if unit == "میلیون":
                    amount *= 1000000
                elif unit == "هزار":
                    amount *= 1000
                elif unit == "تومان":
                    amount *= 10

                entities["amount"] = amount
            except:
                pass

        number_match = re.search(self.patterns["number"], text)
        if number_match:
            entities["voucher_no"] = int(number_match.group(1))

        customer_match = re.search(self.patterns["customer"], text)
        if customer_match:
            entities["customer_name"] = customer_match.group(1).strip()

        supplier_match = re.search(self.patterns["supplier"], text)
        if supplier_match:
            entities["supplier_name"] = supplier_match.group(1).strip()

        product_match = re.search(self.patterns["product"], text)
        if product_match:
            entities["product_name"] = product_match.group(1).strip()

        month_match = re.search(self.patterns["month"], text)
        if month_match:
            month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
            entities["month"] = month_names.index(month_match.group(1)) + 1

        return entities


class ConversationContext:
    """مدیریت بافت مکالمه"""

    def __init__(self, max_history: int = 10):
        self.history = []
        self.max_history = max_history
        self.last_intent = None
        self.last_entities = {}

    def add(self, user_text: str, intent: str, entities: Dict, response: str):
        self.history.append({
            "user": user_text,
            "intent": intent,
            "entities": entities,
            "response": response,
            "timestamp": datetime.now()
        })

        self.last_intent = intent
        self.last_entities = entities

        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_context(self) -> Dict:
        if self.history:
            last = self.history[-1]
            return {
                "last_intent": last["intent"],
                "last_entities": last["entities"],
                "conversation_length": len(self.history)
            }
        return {}

    def clear(self):
        self.history = []
        self.last_intent = None
        self.last_entities = {}


class IntelligentVoiceAssistant:
    """دستیار صوتی هوشمند"""

    def __init__(self):
        self.intent_recognizer = IntentRecognizer()
        self.entity_extractor = EntityExtractor()
        self.context = ConversationContext()
        self.ai = ImanAILite()
        self.models_dir = Path("ai/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def process(self, text: str) -> Dict:
        intent, confidence = self.intent_recognizer.recognize(text)
        entities = self.entity_extractor.extract(text, intent)

        if not entities and self.context.last_entities:
            entities = self.context.last_entities.copy()

        result = self._execute_intent(intent, entities, text)

        self.context.add(text, intent, entities, result["response"])

        return {
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
            "response": result["response"],
            "action": result.get("action"),
            "data": result.get("data")
        }

    def _execute_intent(self, intent: str, entities: Dict, original_text: str) -> Dict:
        if intent == "get_balance":
            return self._get_balance(entities)
        elif intent == "get_profit":
            return self._get_profit(entities)
        elif intent == "get_sales":
            return self._get_sales(entities)
        elif intent == "get_expenses":
            return self._get_expenses(entities)
        elif intent == "create_voucher":
            return self._create_voucher(entities, original_text)
        elif intent == "search_voucher":
            return self._search_voucher(entities)
        elif intent == "search_customer":
            return self._search_customer(entities)
        elif intent == "search_product":
            return self._search_product(entities)
        elif intent == "greeting":
            return self._greeting()
        elif intent == "goodbye":
            return self._goodbye()
        elif intent == "date":
            return self._get_date()
        elif intent == "time":
            return self._get_time()
        elif intent == "help":
            return self._get_help()
        else:
            return {
                "response": "متوجه نشدم. بگویید 'راهنما' تا دستورات را ببینم.",
                "action": None
            }

    def _get_balance(self, entities: Dict) -> Dict:
        balance = AccountingHelper.get_account_balance("1101")
        return {
            "response": f"موجودی صندوق {balance:,.0f} ریال است",
            "action": "show_balance",
            "data": {"balance": balance}
        }

    def _get_profit(self, entities: Dict) -> Dict:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COALESCE(SUM(credit - debit), 0) FROM voucher_items vi JOIN accounts a ON vi.account_code = a.code WHERE a.type = 'income'")
            income = c.fetchone()[0] or 0
            c.execute("SELECT COALESCE(SUM(debit - credit), 0) FROM voucher_items vi JOIN accounts a ON vi.account_code = a.code WHERE a.type = 'expense'")
            expense = c.fetchone()[0] or 0

        profit = income - expense

        if profit >= 0:
            response = f"سود خالص {profit:,.0f} ریال است. درآمدها {income:,.0f} و هزینه‌ها {expense:,.0f} ریال"
        else:
            response = f"زیان خالص {abs(profit):,.0f} ریال است"

        return {"response": response, "action": "show_profit", "data": {"profit": profit}}

    def _get_sales(self, entities: Dict) -> Dict:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COALESCE(SUM(credit - debit), 0) FROM voucher_items vi JOIN accounts a ON vi.account_code = a.code WHERE a.code = '4101'")
            sales = c.fetchone()[0] or 0

        return {"response": f"فروش کل {sales:,.0f} ریال است", "action": "show_sales", "data": {"sales": sales}}

    def _get_expenses(self, entities: Dict) -> Dict:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COALESCE(SUM(debit - credit), 0) FROM voucher_items vi JOIN accounts a ON vi.account_code = a.code WHERE a.type = 'expense'")
            expenses = c.fetchone()[0] or 0

        return {"response": f"هزینه‌های کل {expenses:,.0f} ریال است", "action": "show_expenses", "data": {"expenses": expenses}}

    def _create_voucher(self, entities: Dict, original_text: str) -> Dict:
        description = original_text.replace("سند جدید", "").replace("ثبت سند", "").strip()
        if not description:
            description = "سند بدون شرح"

        return {
            "response": f"سند با شرح '{description}' آماده ثبت است",
            "action": "open_voucher_dialog",
            "data": {"description": description}
        }

    def _search_voucher(self, entities: Dict) -> Dict:
        voucher_no = entities.get("voucher_no")
        if not voucher_no:
            return {"response": "لطفاً شماره سند را بگویید", "action": None}

        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, description, date FROM vouchers WHERE voucher_no = ?", [voucher_no])
            row = c.fetchone()

        if row:
            date_display = DateUtils.to_jalali_str(row[2], "%Y/%m/%d") if row[2] else ""
            response = f"سند شماره {voucher_no} با شرح '{row[1]}' در تاریخ {date_display} ثبت شده است"
            return {"response": response, "action": "show_voucher", "data": {"voucher_id": row[0]}}
        else:
            return {"response": f"سند شماره {voucher_no} یافت نشد", "action": None}

    def _search_customer(self, entities: Dict) -> Dict:
        customer_name = entities.get("customer_name")
        if not customer_name:
            return {"response": "لطفاً نام مشتری را بگویید", "action": None}

        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code, phone, balance FROM parties WHERE name LIKE ? AND type = 'customer'", [f"%{customer_name}%"])
            row = c.fetchone()

        if row:
            response = f"مشتری با کد {row[0]}، تلفن {row[1] or 'نامشخص'} و مانده {row[2]:,.0f} ریال"
            return {"response": response, "action": "show_customer", "data": {"customer": customer_name}}
        else:
            return {"response": f"مشتری با نام {customer_name} یافت نشد", "action": None}

    def _search_product(self, entities: Dict) -> Dict:
        product_name = entities.get("product_name")
        if not product_name:
            return {"response": "لطفاً نام کالا را بگویید", "action": None}

        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code, stock, unit FROM products WHERE name LIKE ?", [f"%{product_name}%"])
            row = c.fetchone()

        if row:
            response = f"کالا با کد {row[0]}، موجودی {row[1]:,.2f} {row[2] or 'عدد'}"
            return {"response": response, "action": "show_product", "data": {"product": product_name}}
        else:
            return {"response": f"کالا با نام {product_name} یافت نشد", "action": None}

    def _greeting(self) -> Dict:
        hour = datetime.now().hour
        if hour < 12:
            greeting = "صبح بخیر"
        elif hour < 18:
            greeting = "ظهر بخیر"
        else:
            greeting = "عصر بخیر"

        return {"response": f"{greeting}! من دستیار هوشمند پارسه هستم. چطور می‌توانم کمک کنم؟", "action": None}

    def _goodbye(self) -> Dict:
        return {"response": "خداحافظ! خوشحال بودم که کمک کردم.", "action": None}

    def _get_date(self) -> Dict:
        today = DateUtils.today_jalali_str("%Y/%m/%d")
        return {"response": f"امروز {today} است", "action": None}

    def _get_time(self) -> Dict:
        now = datetime.now().strftime("%H:%M")
        return {"response": f"ساعت {now} است", "action": None}

    def _get_help(self) -> Dict:
        help_text = """
📋 دستورات قابل استفاده:

💰 گزارش‌گیری:
• موجودی صندوق
• سود این ماه
• فروش این ماه
• هزینه‌های این ماه

📝 ثبت:
• سند جدید با شرح [متن]

🔍 جستجو:
• پیدا کن سند شماره [شماره]
• اطلاعات مشتری [نام]
• اطلاعات کالا [نام]

📅 عمومی:
• تاریخ امروز
• ساعت
• راهنما
• خداحافظ
"""
        return {"response": help_text, "action": "show_help"}