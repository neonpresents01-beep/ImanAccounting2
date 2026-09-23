# plugins/official_plugins/moadian_plugin.py
# -*- coding: utf-8 -*-

"""
پلاگین کامل مودیان - ImanAccount v3.0 (Self-Migrating)
=========================================================
این پلاگین کاملاً خودکفاست:
- تمام تغییرات دیتابیس را خودش انجام می‌دهد
- کافی است فایل را در plugins/official_plugins/ قرار دهید
- با plugin_loader.py v4.0 کاملاً سازگار است

قابلیت‌ها:
- Migration خودکار دیتابیس
- مدیریت شناسه ۱۳ رقمی کالا/خدمت
- ساخت صورتحساب با ۴ بخش استاندارد
- اتصال به سامانه مودیان (JWS)
- استعلام، تاریخچه، تنظیمات
- Multi-tenant با رمزنگاری Fernet

نصب وابستگی‌ها:
    pip install python-jose[cryptography] cryptography requests
"""

import os
import json
import time
import base64
import hashlib
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, asdict, field

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from cryptography import x509
from cryptography.x509.oid import ObjectIdentifier
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QTabWidget, QDialog,
    QFileDialog, QMessageBox, QApplication, QDialogButtonBox,
    QDoubleSpinBox, QSpinBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

try:
    from jose import jws
    from jose.constants import ALGORITHMS
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False
    print("⚠️ python-jose نصب نیست — pip install python-jose[cryptography]")


# ════════════════════════════════════════════════════════════
# متغیرهای ماژول (برای plugin_loader.py v4.0)
# ════════════════════════════════════════════════════════════

PLUGIN_ID = "moadian"
PLUGIN_NAME = "پلاگین مودیان"
PLUGIN_VERSION = "3.0.0"
PLUGIN_AUTHOR = "ImanAccount"
PLUGIN_TYPE = "internal"
REQUIRED_MODULES = []  # بدون نیاز به ماژول لایسنس

SANDBOX_URL = "https://sandboxrc.tax.gov.ir/req/api/self-tsp"
PRODUCTION_URL = "https://tp.tax.gov.ir/req/api/self-tsp"

# متغیرهای سراسری
_widget_cache: Dict[str, QWidget] = {}
_customer_id = "default"
_migration_done = False


# ════════════════════════════════════════════════════════════
# ۱. Migration خودکار دیتابیس
# ════════════════════════════════════════════════════════════

class MoadianMigration:
    """
    مدیریت خودکار تغییرات دیتابیس برای پلاگین مودیان.
    جداول و ستون‌های لازم را ایجاد می‌کند.
    """

    @classmethod
    def run(cls) -> bool:
        global _migration_done

        if _migration_done:
            return True

        try:
            from database import get_db

            with get_db() as conn:
                c = conn.cursor()

                # جداول اصلی
                cls._create_moadian_settings(c)
                cls._create_moadian_invoices(c)
                cls._create_moadian_logs(c)
                cls._create_moadian_serial(c)
                cls._create_moadian_products(c)

                # ستون‌های products
                cls._add_product_columns(c)

                # ایندکس‌ها
                cls._create_indexes(c)

                conn.commit()

                _migration_done = True
                print("✅ Migration پلاگین مودیان انجام شد")
                return True

        except Exception as e:
            print(f"❌ خطا در migration: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def _column_exists(c, table: str, column: str) -> bool:
        try:
            c.execute(f"PRAGMA table_info({table})")
            return column in [row[1] for row in c.fetchall()]
        except Exception:
            return False

    @classmethod
    def _create_moadian_settings(cls, c):
        c.execute('''
            CREATE TABLE IF NOT EXISTS moadian_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT UNIQUE NOT NULL,
                fiscal_id TEXT,
                economic_code TEXT,
                private_key_path TEXT,
                certificate_path TEXT,
                is_sandbox BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    @classmethod
    def _create_moadian_invoices(cls, c):
        c.execute('''
            CREATE TABLE IF NOT EXISTS moadian_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                taxid TEXT UNIQUE NOT NULL,
                reference_number TEXT,
                uid TEXT,
                invoice_type TEXT DEFAULT 'normal',
                invoice_data TEXT,
                status TEXT DEFAULT 'pending',
                response_data TEXT,
                retry_count INTEGER DEFAULT 0,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    @classmethod
    def _create_moadian_logs(cls, c):
        c.execute('''
            CREATE TABLE IF NOT EXISTS moadian_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT,
                endpoint TEXT,
                request_data TEXT,
                response_data TEXT,
                status_code INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    @classmethod
    def _create_moadian_serial(cls, c):
        c.execute('''
            CREATE TABLE IF NOT EXISTS moadian_serial (
                customer_id TEXT PRIMARY KEY,
                last_serial INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    @classmethod
    def _create_moadian_products(cls, c):
        c.execute('''
            CREATE TABLE IF NOT EXISTS moadian_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER UNIQUE NOT NULL,
                sstid TEXT,
                sstt TEXT,
                unit_moadian TEXT DEFAULT '1627',
                vat_rate INTEGER DEFAULT 9,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')

    @classmethod
    def _add_product_columns(cls, c):
        new_columns = [
            ('moadian_sstid', 'TEXT'),
            ('moadian_unit', 'TEXT DEFAULT "1627"'),
            ('moadian_vat', 'INTEGER DEFAULT 9'),
        ]
        for col_name, col_type in new_columns:
            if not cls._column_exists(c, 'products', col_name):
                try:
                    c.execute(f'ALTER TABLE products ADD COLUMN {col_name} {col_type}')
                    print(f"   ✅ ستون {col_name} به products اضافه شد")
                except Exception as e:
                    print(f"   ⚠️ خطا در {col_name}: {e}")

    @classmethod
    def _create_indexes(cls, c):
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_moadian_inv_customer ON moadian_invoices(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_moadian_inv_status ON moadian_invoices(status)",
            "CREATE INDEX IF NOT EXISTS idx_moadian_inv_taxid ON moadian_invoices(taxid)",
            "CREATE INDEX IF NOT EXISTS idx_moadian_logs_customer ON moadian_logs(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_moadian_products_pid ON moadian_products(product_id)",
            "CREATE INDEX IF NOT EXISTS idx_moadian_products_sstid ON moadian_products(sstid)",
            "CREATE INDEX IF NOT EXISTS idx_products_moadian_sstid ON products(moadian_sstid)",
        ]
        for idx in indexes:
            try:
                c.execute(idx)
            except Exception:
                pass


# ════════════════════════════════════════════════════════════
# ۲. مدیریت دیتابیس
# ════════════════════════════════════════════════════════════

class MoadianDatabase:

    @classmethod
    def next_serial(cls, customer_id: str) -> int:
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO moadian_serial (customer_id, last_serial)
                    VALUES (?, 1)
                    ON CONFLICT(customer_id) DO UPDATE SET
                        last_serial = last_serial + 1,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING last_serial
                ''', [customer_id])
                row = c.fetchone()
                return row['last_serial'] if row else 1
        except Exception as e:
            print(f"⚠️ خطا در سریال: {e}")
            return int(time.time()) % 0xFFFFFFFFFF

    @classmethod
    def log_request(cls, customer_id: str, endpoint: str,
                    request_data: dict, response_data: dict,
                    status_code: int):
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO moadian_logs
                    (customer_id, endpoint, request_data, response_data, status_code)
                    VALUES (?, ?, ?, ?, ?)
                ''', [
                    customer_id, endpoint,
                    json.dumps(request_data, ensure_ascii=False)[:5000],
                    json.dumps(response_data, ensure_ascii=False)[:5000],
                    status_code
                ])
        except Exception as e:
            print(f"⚠️ خطا در لاگ: {e}")

    @classmethod
    def save_invoice(cls, customer_id: str, taxid: str,
                     invoice_data: dict, response_data: dict,
                     invoice_type: str = 'normal',
                     status: str = 'pending') -> bool:
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                uid = None
                ref = None
                if response_data and 'result' in response_data:
                    r = response_data['result']
                    if isinstance(r, dict):
                        uid = r.get('uid')
                        ref = r.get('referenceNumber')

                c.execute('''
                    INSERT INTO moadian_invoices
                    (customer_id, taxid, reference_number, uid, invoice_type,
                     invoice_data, status, response_data, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(taxid) DO UPDATE SET
                        reference_number = excluded.reference_number,
                        uid = excluded.uid,
                        status = excluded.status,
                        response_data = excluded.response_data,
                        updated_at = excluded.updated_at
                ''', [
                    customer_id, taxid, ref, uid, invoice_type,
                    json.dumps(invoice_data, ensure_ascii=False),
                    status,
                    json.dumps(response_data, ensure_ascii=False),
                    datetime.now().isoformat()
                ])
                return True
        except Exception as e:
            print(f"⚠️ خطا در ذخیره: {e}")
            return False

    @classmethod
    def get_invoices(cls, customer_id: str, limit: int = 100) -> list:
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT * FROM moadian_invoices
                    WHERE customer_id = ?
                    ORDER BY sent_at DESC LIMIT ?
                ''', [customer_id, limit])
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"⚠️ خطا: {e}")
            return []

    @classmethod
    def get_products_for_moadian(cls) -> list:
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT p.id, p.code, p.name, p.unit, p.stock,
                           p.sale_price, p.moadian_sstid,
                           mp.sstid as mp_sstid, mp.unit_moadian, mp.vat_rate
                    FROM products p
                    LEFT JOIN moadian_products mp ON p.id = mp.product_id
                    WHERE p.is_active = 1
                    ORDER BY p.code
                ''')
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"⚠️ خطا: {e}")
            return []

    @classmethod
    def get_product_moadian_info(cls, product_id: int) -> dict:
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT p.id, p.code, p.name, p.moadian_sstid,
                           mp.sstid as mp_sstid, mp.unit_moadian, mp.vat_rate
                    FROM products p
                    LEFT JOIN moadian_products mp ON p.id = mp.product_id
                    WHERE p.id = ?
                ''', [product_id])
                row = c.fetchone()
                if row:
                    d = dict(row)
                    d['sstid'] = d.get('mp_sstid') or d.get('moadian_sstid') or ''
                    d['unit_moadian'] = d.get('unit_moadian') or '1627'
                    d['vat_rate'] = d.get('vat_rate') or 9
                    return d
        except Exception as e:
            print(f"⚠️ خطا: {e}")
        return {}

    @classmethod
    def save_product_moadian_info(cls, product_id: int, sstid: str,
                                   unit_moadian: str = '1627',
                                   vat_rate: int = 9) -> bool:
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()

                c.execute('''
                    INSERT INTO moadian_products
                    (product_id, sstid, unit_moadian, vat_rate, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(product_id) DO UPDATE SET
                        sstid = excluded.sstid,
                        unit_moadian = excluded.unit_moadian,
                        vat_rate = excluded.vat_rate,
                        updated_at = excluded.updated_at
                ''', [product_id, sstid, unit_moadian, vat_rate,
                      datetime.now().isoformat()])

                c.execute('''
                    UPDATE products
                    SET moadian_sstid = ?, moadian_unit = ?, moadian_vat = ?
                    WHERE id = ?
                ''', [sstid, unit_moadian, vat_rate, product_id])

                return True
        except Exception as e:
            print(f"⚠️ خطا در ذخیره: {e}")
            return False


# ════════════════════════════════════════════════════════════
# ۳. تنظیمات رمزنگاری‌شده
# ════════════════════════════════════════════════════════════

class MoadianConfig:

    def __init__(self, customer_id: str = "default"):
        self.customer_id = customer_id
        self.fiscal_id = None
        self.economic_code = None
        self.private_key_path = None
        self.certificate_path = None
        self.is_sandbox = True
        self.is_configured = False
        self._load()

    def _key(self) -> bytes:
        m = f"ImanAccount_{self.customer_id}_MoadianKey".encode()
        return base64.urlsafe_b64encode(hashlib.sha256(m).digest())

    def _enc(self, data: str) -> str:
        if not data:
            return ""
        return Fernet(self._key()).encrypt(data.encode()).decode()

    def _dec(self, enc: str) -> str:
        if not enc:
            return ""
        try:
            return Fernet(self._key()).decrypt(enc.encode()).decode()
        except Exception:
            return ""

    def _load(self):
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT fiscal_id, economic_code, private_key_path,
                           certificate_path, is_sandbox
                    FROM moadian_settings WHERE customer_id = ?
                ''', [self.customer_id])
                row = c.fetchone()
                if row:
                    self.fiscal_id = self._dec(row['fiscal_id']) or None
                    self.economic_code = self._dec(row['economic_code']) or None
                    self.private_key_path = self._dec(row['private_key_path']) or None
                    self.certificate_path = self._dec(row['certificate_path']) or None
                    self.is_sandbox = bool(row['is_sandbox'])
                    self.is_configured = bool(
                        self.fiscal_id and self.private_key_path
                        and os.path.exists(self.private_key_path)
                    )
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری: {e}")

    def save(self) -> bool:
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO moadian_settings
                    (customer_id, fiscal_id, economic_code, private_key_path,
                     certificate_path, is_sandbox, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(customer_id) DO UPDATE SET
                        fiscal_id = excluded.fiscal_id,
                        economic_code = excluded.economic_code,
                        private_key_path = excluded.private_key_path,
                        certificate_path = excluded.certificate_path,
                        is_sandbox = excluded.is_sandbox,
                        updated_at = excluded.updated_at
                ''', [
                    self.customer_id,
                    self._enc(self.fiscal_id or ""),
                    self._enc(self.economic_code or ""),
                    self._enc(self.private_key_path or ""),
                    self._enc(self.certificate_path or ""),
                    1 if self.is_sandbox else 0,
                    datetime.now().isoformat()
                ])
                return True
        except Exception as e:
            print(f"⚠️ خطا در ذخیره: {e}")
            return False

    def validate(self) -> Tuple[bool, list]:
        errors = []
        if not self.fiscal_id:
            errors.append("شناسه حافظه مالیاتی وارد نشده")
        elif len(self.fiscal_id) != 36:
            errors.append("شناسه باید ۳۶ کاراکتر UUID باشد")
        if not self.economic_code:
            errors.append("کد اقتصادی وارد نشده")
        elif not self.economic_code.isdigit() or len(self.economic_code) != 14:
            errors.append("کد اقتصادی باید ۱۴ رقم عددی باشد")
        if not self.private_key_path:
            errors.append("مسیر کلید خصوصی وارد نشده")
        elif not os.path.exists(self.private_key_path):
            errors.append("فایل کلید خصوصی یافت نشد")
        return len(errors) == 0, errors


# ════════════════════════════════════════════════════════════
# ۴. رمزنگاری و امضا
# ════════════════════════════════════════════════════════════

class MoadianCrypto:

    @staticmethod
    def load_private_key(path: str):
        with open(path, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

    @staticmethod
    def private_key_to_pem(key) -> bytes:
        return key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

    @staticmethod
    def generate_jws_signature(key, payload: dict) -> str:
        if JOSE_AVAILABLE:
            pem = MoadianCrypto.private_key_to_pem(key)
            return jws.sign(
                payload, pem,
                algorithm=ALGORITHMS.RS256,
                headers={"typ": "JWT", "alg": "RS256"}
            )
        data = json.dumps(payload, ensure_ascii=False,
                          separators=(',', ':')).encode('utf-8')
        sig = key.sign(data, padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(sig).decode('ascii')

    @staticmethod
    def generate_tax_id(fiscal_id: str, serial: int,
                        date: datetime = None) -> str:
        if date is None:
            date = datetime.now()
        fiscal_part = fiscal_id[:6].ljust(6, '0')
        serial_part = format(serial % 0xFFFFFFFFFF, '010x')[:10].upper()
        date_part = f"{date.year % 100:02d}{date.month:02d}{date.day:02d}"
        tax_id = f"{fiscal_part}{serial_part}{date_part}"
        return f"{tax_id}{MoadianCrypto._verhoeff(tax_id)}"[:22]

    @staticmethod
    def _verhoeff(number: str) -> str:
        d = [
            [0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],
            [2,3,4,0,1,7,8,9,5,6],[3,4,0,1,2,8,9,5,6,7],
            [4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
            [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],
            [8,7,6,5,9,3,2,1,0,4],[9,8,7,6,5,4,3,2,1,0]
        ]
        p = [
            [0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],
            [5,8,0,3,7,9,6,1,4,2],[8,9,1,6,0,4,3,5,2,7],
            [9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],
            [2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]
        ]
        c = 0
        for i, ch in enumerate(reversed(number)):
            c = d[c][p[i % 8][int(ch)]]
        return str((10 - c) % 10)


class CSRGenerator:

    @staticmethod
    def generate_private_key(size: int = 2048):
        return rsa.generate_private_key(
            public_exponent=65537, key_size=size,
            backend=default_backend()
        )

    @staticmethod
    def generate_csr(key, common_name: str,
                     organization: str, country: str = "IR") -> bytes:
        csr = x509.CertificateSigningRequestBuilder().subject_name(
            x509.Name([
                x509.NameAttribute(ObjectIdentifier("2.5.4.3"), common_name),
                x509.NameAttribute(ObjectIdentifier("2.5.4.10"), organization),
                x509.NameAttribute(ObjectIdentifier("2.5.4.6"), country),
            ])
        ).sign(key, hashes.SHA256(), default_backend())
        return csr.public_bytes(serialization.Encoding.PEM)

    @staticmethod
    def save_key_and_csr(key, csr_pem: bytes,
                         output_dir: str, prefix: str = "moadian"):
        os.makedirs(output_dir, exist_ok=True)
        key_path = os.path.join(output_dir, f"{prefix}_private.pem")
        csr_path = os.path.join(output_dir, f"{prefix}.csr")
        with open(key_path, 'wb') as f:
            f.write(MoadianCrypto.private_key_to_pem(key))
        with open(csr_path, 'wb') as f:
            f.write(csr_pem)
        return key_path, csr_path


# ════════════════════════════════════════════════════════════
# ۵. سازنده صورتحساب
# ════════════════════════════════════════════════════════════

@dataclass
class InvoiceHeader:
    taxid: str = ""
    indatim: int = 0
    inty: int = 1
    inp: int = 1
    tins: str = ""
    tbill: float = 0.0
    setm: Optional[int] = None
    cap: Optional[float] = None
    tvop: float = 0.0
    tax17: float = 0.0


@dataclass
class InvoiceBuyer:
    tinb: str = ""
    tinb_type: int = 2
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None


@dataclass
class InvoiceItem:
    sstid: str = ""
    sstt: str = ""
    am: float = 1.0
    fee: float = 0.0
    vra: int = 9
    dis: float = 0.0
    prdis: float = 0.0
    adis: float = 0.0
    vam: float = 0.0
    tsstam: float = 0.0
    unit: str = "1627"


@dataclass
class InvoicePayment:
    pdt: int = 1
    pv: float = 0.0


class StandardInvoiceBuilder:

    INVOICE_NORMAL = "normal"
    INVOICE_CORRECTIVE = "corrective"
    INVOICE_CANCELLATION = "cancellation"
    INVOICE_RETURN = "return"

    def __init__(self, fiscal_id: str, economic_code: str,
                 customer_id: str = "default",
                 invoice_type: str = "normal"):
        self.fiscal_id = fiscal_id
        self.economic_code = economic_code
        self.customer_id = customer_id
        self.invoice_type = invoice_type
        self.header = InvoiceHeader()
        self.buyer = InvoiceBuyer()
        self.items: List[InvoiceItem] = []
        self.payments: List[InvoicePayment] = []
        self.extension: Dict = {}
        self.description: str = ""
        self._reference_taxid: Optional[str] = None

    def set_header(self, inty: int = 1, inp: int = 1,
                   setm: Optional[int] = None,
                   tins: str = None) -> 'StandardInvoiceBuilder':
        serial = MoadianDatabase.next_serial(self.customer_id)
        self.header.inty = inty
        self.header.inp = inp
        self.header.setm = setm
        self.header.tins = tins or self.economic_code
        self.header.indatim = int(time.time() * 1000)
        self.header.taxid = MoadianCrypto.generate_tax_id(
            self.fiscal_id, serial
        )
        return self

    def set_buyer(self, tinb: str, tinb_type: int = 2,
                  name: str = None, phone: str = None,
                  address: str = None,
                  postal_code: str = None) -> 'StandardInvoiceBuilder':
        self.buyer = InvoiceBuyer(
            tinb=tinb, tinb_type=tinb_type, name=name,
            phone=phone, address=address, postal_code=postal_code
        )
        return self

    def add_item(self, sstid: str, sstt: str, am: float, fee: float,
                 vra: int = 9, dis: float = 0.0,
                 unit: str = "1627") -> 'StandardInvoiceBuilder':
        prdis = fee * am
        adis = prdis - dis
        vam = adis * vra / 100
        tsstam = adis + vam
        self.items.append(InvoiceItem(
            sstid=sstid, sstt=sstt, am=am, fee=fee,
            vra=vra, dis=dis, prdis=prdis, adis=adis,
            vam=vam, tsstam=tsstam, unit=unit
        ))
        return self

    def add_payment(self, pdt: int = 1,
                    pv: float = 0.0) -> 'StandardInvoiceBuilder':
        self.payments.append(InvoicePayment(pdt=pdt, pv=pv))
        return self

    def set_reference_taxid(self, taxid: str) -> 'StandardInvoiceBuilder':
        self._reference_taxid = taxid
        return self

    def set_extension(self, **kwargs) -> 'StandardInvoiceBuilder':
        self.extension.update(kwargs)
        return self

    def _calc_totals(self):
        self.header.tbill = sum(item.tsstam for item in self.items)
        self.header.tvop = sum(item.vam for item in self.items)

    def build(self) -> dict:
        self._calc_totals()
        invoice = {
            "header": asdict(self.header),
            "body": [asdict(item) for item in self.items],
            "buyer": asdict(self.buyer),
        }
        if self.payments:
            invoice["payments"] = [asdict(p) for p in self.payments]
        if self.extension:
            invoice["extension"] = self.extension
        if self.description:
            invoice["description"] = self.description
        if self._reference_taxid:
            invoice["referenceTaxid"] = self._reference_taxid
        return invoice

    def validate(self) -> Tuple[bool, List[str]]:
        errors = []
        if not self.header.taxid or len(self.header.taxid) < 20:
            errors.append("TaxID نامعتبر است")
        if not self.header.tins:
            errors.append("شماره اقتصادی فروشنده وارد نشده")
        if not self.buyer.tinb:
            errors.append("شماره اقتصادی خریدار وارد نشده")
        if self.buyer.tinb_type not in [1, 2]:
            errors.append("نوع خریدار باید ۱ یا ۲ باشد")
        if not self.items:
            errors.append("حداقل یک قلم باید اضافه شود")
        else:
            for i, item in enumerate(self.items):
                if not item.sstid:
                    errors.append(f"قلم {i+1}: شناسه ۱۳ رقمی کالا وارد نشده")
                elif not item.sstid.isdigit() or len(item.sstid) != 13:
                    errors.append(f"قلم {i+1}: شناسه کالا باید ۱۳ رقم باشد")
                if item.am <= 0:
                    errors.append(f"قلم {i+1}: مقدار باید > صفر")
                if not (0 <= item.vra <= 100):
                    errors.append(f"قلم {i+1}: نرخ مالیات ۰-۱۰۰")
        if self.invoice_type in [self.INVOICE_CORRECTIVE,
                                  self.INVOICE_CANCELLATION]:
            if not self._reference_taxid:
                errors.append("برای اصلاحی/ابطالی، TaxID مرجع الزامی است")
        return len(errors) == 0, errors


# ════════════════════════════════════════════════════════════
# ۶. کلاینت مودیان
# ════════════════════════════════════════════════════════════

class MoadianClient:

    PACKET_GET_SERVER_INFO = "GET_SERVER_INFORMATION"
    PACKET_GET_TOKEN = "GET_TOKEN"
    PACKET_INVOICE = "INVOICE.V01"
    PACKET_INQUIRY_UID = "INQUIRY_BY_UID"
    PACKET_INQUIRY_REF = "INQUIRY_BY_REFERENCE_NUMBER"
    PACKET_INQUIRY_TAXID = "INQUIRY_BY_TAXID"

    def __init__(self, config: MoadianConfig):
        self.config = config
        self.base_url = SANDBOX_URL if config.is_sandbox else PRODUCTION_URL
        self.token = None
        self.server_public_key = None
        self.private_key = None

        if config.private_key_path and os.path.exists(config.private_key_path):
            try:
                self.private_key = MoadianCrypto.load_private_key(
                    config.private_key_path
                )
            except Exception as e:
                print(f"⚠️ خطا در بارگذاری کلید: {e}")

        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1,
                      status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _build_packet(self, packet_type: str, data: dict = None) -> dict:
        mil_time = int(time.time() * 1000)
        packet = {
            "uid": None,
            "packetType": packet_type,
            "retry": False,
            "data": data,
            "encryptionKeyId": "",
            "symmetricKey": "",
            "iv": "",
            "fiscalId": self.config.fiscal_id,
            "dataSignature": ""
        }
        payload = {
            "requestTraceId": str(mil_time),
            "timestamp": str(mil_time),
            "packet": packet
        }
        if self.private_key:
            try:
                signature = MoadianCrypto.generate_jws_signature(
                    self.private_key, payload
                )
                return {
                    "requestTraceId": str(mil_time),
                    "timestamp": str(mil_time),
                    "packet": packet,
                    "signature": signature
                }
            except Exception as e:
                print(f"⚠️ خطا در امضا: {e}")
        return payload

    def _post(self, endpoint: str, payload: dict) -> Tuple[bool, Dict]:
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                json=payload, timeout=30
            )
            try:
                resp_json = response.json()
            except Exception:
                resp_json = {'text': response.text[:500]}

            MoadianDatabase.log_request(
                self.config.customer_id, endpoint,
                payload, resp_json, response.status_code
            )

            if response.status_code == 200:
                return True, resp_json
            return False, {
                'error': f"HTTP {response.status_code}",
                'message': resp_json
            }
        except requests.exceptions.Timeout:
            return False, {'error': 'timeout', 'message': 'اتصال طول کشید'}
        except requests.exceptions.ConnectionError:
            return False, {'error': 'connection_error',
                           'message': 'اتصال برقرار نشد'}
        except Exception as e:
            return False, {'error': str(e)}

    def get_server_information(self) -> Tuple[bool, Dict]:
        if not self.private_key:
            return False, {'error': 'کلید خصوصی بارگذاری نشده'}
        packet = self._build_packet(self.PACKET_GET_SERVER_INFO)
        ok, result = self._post("/sync/GET_SERVER_INFORMATION", packet)
        if ok:
            try:
                data = result.get('result', {}).get('data', {})
                keys = data.get('publicKeys', [])
                if keys:
                    self.server_public_key = keys[0].get('key')
            except Exception:
                pass
        return ok, result

    def get_token(self) -> Tuple[bool, str]:
        if not self.private_key:
            return False, "کلید خصوصی بارگذاری نشده"
        ok, _ = self.get_server_information()
        if not ok:
            return False, "خطا در اطلاعات سرور"
        packet = self._build_packet(
            self.PACKET_GET_TOKEN,
            data={"username": self.config.fiscal_id}
        )
        ok, result = self._post("/sync/GET_TOKEN", packet)
        if ok:
            token = None
            if isinstance(result.get('result'), dict):
                token = result['result'].get('token')
            token = token or result.get('token')
            if token:
                self.token = token
                return True, token
        return False, str(result)

    def send_invoice(self, invoice_data: dict,
                     invoice_type: str = 'normal') -> Tuple[bool, Dict]:
        if not self.token:
            ok, _ = self.get_token()
            if not ok:
                return False, {'error': 'خطا در دریافت توکن'}
        packet = self._build_packet(self.PACKET_INVOICE, data=invoice_data)
        ok, result = self._post("/sync/INVOICE.V01", packet)
        if ok:
            taxid = invoice_data.get('header', {}).get('taxid', '')
            MoadianDatabase.save_invoice(
                self.config.customer_id, taxid, invoice_data,
                result, invoice_type, 'sent'
            )
        return ok, result

    def inquiry_by_uid(self, uid: str) -> Tuple[bool, Dict]:
        if not self.token:
            self.get_token()
        packet = self._build_packet(
            self.PACKET_INQUIRY_UID, data={"uid": uid}
        )
        return self._post("/sync/INQUIRY_BY_UID", packet)

    def inquiry_by_ref(self, ref: str) -> Tuple[bool, Dict]:
        if not self.token:
            self.get_token()
        packet = self._build_packet(
            self.PACKET_INQUIRY_REF, data={"referenceNumber": ref}
        )
        return self._post("/sync/INQUIRY_BY_REFERENCE_NUMBER", packet)

    def inquiry_by_taxid(self, taxid: str) -> Tuple[bool, Dict]:
        if not self.token:
            self.get_token()
        packet = self._build_packet(
            self.PACKET_INQUIRY_TAXID, data={"taxid": taxid}
        )
        return self._post("/sync/INQUIRY_BY_TAXID", packet)

    def test_connection(self) -> Tuple[bool, str]:
        mode = "Sandbox" if self.config.is_sandbox else "Production"
        ok, result = self.get_server_information()
        if not ok:
            return False, f"خطا در اطلاعات سرور: {result}"
        ok, token = self.get_token()
        if not ok:
            return False, f"خطا در توکن: {token}"
        return True, f"اتصال موفق به {mode}"


# ════════════════════════════════════════════════════════════
# ۷. استایل‌های مشترک
# ════════════════════════════════════════════════════════════

GROUP_STYLE = """
    QGroupBox {
        font-weight: bold; border: 2px solid #273c75;
        border-radius: 8px; margin-top: 10px;
        padding-top: 15px; background: white;
    }
    QGroupBox::title {
        subcontrol-origin: margin; left: 10px;
        padding: 0 10px; color: #273c75;
    }
"""

INPUT_STYLE = "padding: 8px; border: 1px solid #ddd; border-radius: 4px;"

BTN_PRIMARY = """
    QPushButton { background: #273c75; color: white; padding: 10px 25px;
        border: none; border-radius: 6px; font-weight: bold; }
    QPushButton:hover { background: #192a56; }
"""
BTN_SUCCESS = """
    QPushButton { background: #4CAF50; color: white; padding: 10px 25px;
        border: none; border-radius: 6px; font-weight: bold; }
    QPushButton:hover { background: #388E3C; }
"""
BTN_DANGER = """
    QPushButton { background: #e74c3c; color: white; padding: 10px 25px;
        border: none; border-radius: 6px; font-weight: bold; }
    QPushButton:hover { background: #c0392b; }
"""
BTN_INFO = """
    QPushButton { background: #3498db; color: white; padding: 10px 25px;
        border: none; border-radius: 6px; font-weight: bold; }
    QPushButton:hover { background: #2980b9; }
"""


def make_title(text: str, size: int = 16) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(f"""
        font-size: {size}pt; font-weight: bold; color: #273c75;
        padding: 10px; background: #e8f0fe; border-radius: 8px;
    """)
    label.setAlignment(Qt.AlignCenter)
    return label


def make_status(text: str = "ℹ️ آماده") -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(
        "padding: 10px; background: #f8f9fa; "
        "border-radius: 6px; color: #666;"
    )
    return label


def set_status(label: QLabel, text: str, kind: str = "info"):
    colors = {
        "info": ("#f8f9fa", "#666"),
        "success": ("#e8f5e9", "#2e7d32"),
        "error": ("#ffebee", "#c62828"),
        "warning": ("#fff3e0", "#e65100"),
    }
    bg, fg = colors.get(kind, colors["info"])
    label.setText(text)
    label.setStyleSheet(
        f"padding: 10px; background: {bg}; "
        f"border-radius: 6px; color: {fg};"
    )


# ════════════════════════════════════════════════════════════
# ۸. ویجت مدیریت کالاهای مودیانی
# ════════════════════════════════════════════════════════════

class MoadianProductsWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.products_data = []
        self._init_ui()
        self.load_products()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        layout.addWidget(make_title("📦 مدیریت شناسه کالا/خدمت مودیان", 14))

        info = QLabel(
            "برای هر کالا، شناسه ۱۳ رقمی مودیان را از سامانه "
            "stuffid.tax.gov.ir دریافت و اینجا وارد کنید.\n"
            "بدون این شناسه، صورتحساب در سامانه مودیان رد می‌شود."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "padding: 10px; background: #fff3e0; "
            "border-radius: 6px; color: #e65100;"
        )
        layout.addWidget(info)

        toolbar = QHBoxLayout()

        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet(BTN_INFO)
        refresh_btn.clicked.connect(self.load_products)
        toolbar.addWidget(refresh_btn)

        sync_btn = QPushButton("🔗 همگام‌سازی با انبار")
        sync_btn.setStyleSheet(BTN_PRIMARY)
        sync_btn.clicked.connect(self.sync_from_inventory)
        toolbar.addWidget(sync_btn)

        toolbar.addStretch()

        toolbar.addWidget(QLabel("🔍 جستجو:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("کد یا نام کالا...")
        self.search_input.setStyleSheet(INPUT_STYLE)
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self.filter_products)
        toolbar.addWidget(self.search_input)

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "کد", "نام کالا", "واحد", "شناسه مودیان (۱۳ رقمی)",
            "کد واحد مودیان", "نرخ VAT %"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #ddd; border-radius: 6px;
                background: white; font-size: 10pt; }
            QHeaderView::section { background: #273c75; color: white;
                padding: 8px; font-weight: bold; }
        """)
        self.table.doubleClicked.connect(self.edit_product_moadian)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()

        edit_btn = QPushButton("✏️ ویرایش شناسه مودیان")
        edit_btn.setStyleSheet(BTN_SUCCESS)
        edit_btn.clicked.connect(self.edit_product_moadian)
        btn_row.addWidget(edit_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.status = make_status("ℹ️ آماده")
        layout.addWidget(self.status)

    def load_products(self):
        try:
            products = MoadianDatabase.get_products_for_moadian()
            self.products_data = products
            self.display_products(products)

            total = len(products)
            with_sstid = sum(
                1 for p in products
                if p.get('mp_sstid') or p.get('moadian_sstid')
            )

            set_status(
                self.status,
                f"📊 {total} کالا | {with_sstid} دارای شناسه | "
                f"{total - with_sstid} بدون شناسه",
                "success" if with_sstid == total else "warning"
            )
        except Exception as e:
            set_status(self.status, f"❌ خطا: {e}", "error")

    def display_products(self, products):
        self.table.setRowCount(len(products))
        for i, p in enumerate(products):
            self.table.setItem(i, 0, QTableWidgetItem(str(p.get('code', ''))))
            self.table.setItem(i, 1, QTableWidgetItem(str(p.get('name', ''))))
            self.table.setItem(i, 2, QTableWidgetItem(str(p.get('unit', ''))))

            sstid = p.get('mp_sstid') or p.get('moadian_sstid') or ''
            sstid_item = QTableWidgetItem(sstid or "— ثبت نشده —")
            if sstid and len(sstid) == 13:
                sstid_item.setForeground(QColor('#27ae60'))
            else:
                sstid_item.setForeground(QColor('#e74c3c'))
            self.table.setItem(i, 3, sstid_item)

            self.table.setItem(i, 4, QTableWidgetItem(
                str(p.get('unit_moadian') or '1627')
            ))

            vat = p.get('vat_rate') or 9
            vat_item = QTableWidgetItem(f"{vat}%")
            vat_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 5, vat_item)

    def filter_products(self):
        text = self.search_input.text().strip().lower()
        if not text:
            self.display_products(self.products_data)
            return
        filtered = [
            p for p in self.products_data
            if text in str(p.get('code', '')).lower()
            or text in str(p.get('name', '')).lower()
        ]
        self.display_products(filtered)

    def edit_product_moadian(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "یک کالا انتخاب کنید!")
            return
        product = self.products_data[row]
        dlg = ProductMoadianDialog(product, self)
        if dlg.exec_():
            self.load_products()

    def sync_from_inventory(self):
        try:
            from database import get_db
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT p.id, p.moadian_sstid, p.moadian_unit, p.moadian_vat
                    FROM products p
                    LEFT JOIN moadian_products mp ON p.id = mp.product_id
                    WHERE mp.id IS NULL AND p.moadian_sstid IS NOT NULL
                ''')
                rows = c.fetchall()
                count = 0
                for row in rows:
                    c.execute('''
                        INSERT INTO moadian_products
                        (product_id, sstid, unit_moadian, vat_rate)
                        VALUES (?, ?, ?, ?)
                    ''', [
                        row['id'],
                        row['moadian_sstid'],
                        row['moadian_unit'] or '1627',
                        row['moadian_vat'] or 9
                    ])
                    count += 1
                conn.commit()

            set_status(self.status, f"✅ {count} کالا همگام شد", "success")
            self.load_products()
        except Exception as e:
            set_status(self.status, f"❌ خطا: {e}", "error")


class ProductMoadianDialog(QDialog):

    def __init__(self, product: dict, parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle(f"ویرایش شناسه مودیان — {product.get('name', '')}")
        self.setModal(True)
        self.resize(500, 400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        info_group = QGroupBox("اطلاعات کالا")
        info_group.setStyleSheet(GROUP_STYLE)
        info_form = QFormLayout(info_group)
        info_form.addRow("کد:", QLabel(str(self.product.get('code', ''))))
        info_form.addRow("نام:", QLabel(str(self.product.get('name', ''))))
        info_form.addRow("واحد:", QLabel(str(self.product.get('unit', ''))))
        layout.addWidget(info_group)

        moadian_group = QGroupBox("شناسه کالا/خدمت مودیان")
        moadian_group.setStyleSheet(GROUP_STYLE)
        moadian_form = QFormLayout(moadian_group)

        self.sstid_input = QLineEdit()
        self.sstid_input.setPlaceholderText("۱۳ رقم — مثال: 2330001234567")
        self.sstid_input.setMaxLength(13)
        self.sstid_input.setText(
            self.product.get('mp_sstid')
            or self.product.get('moadian_sstid')
            or ''
        )
        self.sstid_input.setStyleSheet(INPUT_STYLE)
        moadian_form.addRow("شناسه ۱۳ رقمی:", self.sstid_input)

        self.unit_combo = QComboBox()
        self.unit_combo.setEditable(True)
        units = [
            ("1627", "عدد"), ("1628", "کیلوگرم"), ("1629", "متر"),
            ("1630", "لیتر"), ("1631", "بسته"), ("1632", "کارتن"),
            ("1633", "جفت"), ("1634", "شاخه"),
        ]
        for code, name in units:
            self.unit_combo.addItem(f"{code} — {name}", code)
        current_unit = self.product.get('unit_moadian') or '1627'
        idx = self.unit_combo.findData(current_unit)
        if idx >= 0:
            self.unit_combo.setCurrentIndex(idx)
        moadian_form.addRow("کد واحد مودیان:", self.unit_combo)

        self.vat_input = QSpinBox()
        self.vat_input.setRange(0, 100)
        self.vat_input.setValue(self.product.get('vat_rate') or 9)
        self.vat_input.setSuffix(" %")
        moadian_form.addRow("نرخ VAT:", self.vat_input)

        layout.addWidget(moadian_group)

        help_label = QLabel(
            "💡 شناسه کالا/خدمت را از سامانه stuffid.tax.gov.ir دریافت کنید."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet(
            "padding: 8px; background: #e3f2fd; "
            "border-radius: 5px; color: #1565c0; font-size: 9pt;"
        )
        layout.addWidget(help_label)

        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _save(self):
        sstid = self.sstid_input.text().strip()

        if not sstid:
            reply = QMessageBox.question(
                self, "تأیید",
                "شناسه وارد نشده. آیا می‌خواهید بدون شناسه ذخیره کنید؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        elif not sstid.isdigit() or len(sstid) != 13:
            QMessageBox.warning(
                self, "خطا",
                "شناسه کالا باید دقیقاً ۱۳ رقم عددی باشد!"
            )
            return

        success = MoadianDatabase.save_product_moadian_info(
            product_id=self.product['id'],
            sstid=sstid,
            unit_moadian=self.unit_combo.currentData(),
            vat_rate=self.vat_input.value()
        )

        if success:
            QMessageBox.information(self, "موفق", "✅ اطلاعات ذخیره شد")
            self.accept()
        else:
            QMessageBox.warning(self, "خطا", "❌ خطا در ذخیره")


# ════════════════════════════════════════════════════════════
# ۹. ویجت تنظیمات
# ════════════════════════════════════════════════════════════

class MoadianSettingsWidget(QWidget):

    def __init__(self, customer_id: str = "default", parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.config = MoadianConfig(customer_id)
        self._init_ui()
        self._load()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(make_title("⚙️ تنظیمات اتصال به سامانه مودیان"))

        desc = QLabel(
            "اطلاعات زیر رمزنگاری‌شده ذخیره می‌شود.\n"
            "برای دریافت گواهی، از سامانه mycert.ir اقدام کنید."
        )
        desc.setStyleSheet("color: #666; padding: 5px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        grp = QGroupBox("📋 اطلاعات اتصال")
        grp.setStyleSheet(GROUP_STYLE)
        form = QFormLayout(grp)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.fiscal_input = QLineEdit()
        self.fiscal_input.setPlaceholderText(
            "9d94612e-1e99-46ab-9efc-2cf85bb23797"
        )
        self.fiscal_input.setStyleSheet(INPUT_STYLE)
        form.addRow("🆔 شناسه حافظه مالیاتی:", self.fiscal_input)

        self.economic_input = QLineEdit()
        self.economic_input.setPlaceholderText("29403041730001")
        self.economic_input.setMaxLength(14)
        self.economic_input.setStyleSheet(INPUT_STYLE)
        form.addRow("💰 کد اقتصادی (۱۴ رقم):", self.economic_input)

        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("مسیر private_key.pem")
        self.key_input.setStyleSheet(INPUT_STYLE)
        key_layout.addWidget(self.key_input)

        key_btn = QPushButton("📁 انتخاب")
        key_btn.setStyleSheet(BTN_INFO)
        key_btn.clicked.connect(self._select_key)
        key_layout.addWidget(key_btn)
        form.addRow("🔑 کلید خصوصی:", key_layout)

        cert_layout = QHBoxLayout()
        self.cert_input = QLineEdit()
        self.cert_input.setPlaceholderText("مسیر certificate.pem (اختیاری)")
        self.cert_input.setStyleSheet(INPUT_STYLE)
        cert_layout.addWidget(self.cert_input)

        cert_btn = QPushButton("📁 انتخاب")
        cert_btn.setStyleSheet(BTN_INFO)
        cert_btn.clicked.connect(self._select_cert)
        cert_layout.addWidget(cert_btn)
        form.addRow("📜 گواهی‌نامه:", cert_layout)

        self.sandbox_check = QCheckBox("محیط تست (Sandbox)")
        self.sandbox_check.setChecked(True)
        self.sandbox_check.setStyleSheet("padding: 8px;")
        form.addRow("🌐 محیط:", self.sandbox_check)

        layout.addWidget(grp)

        gen_grp = QGroupBox("🔧 ابزار تولید کلید و CSR")
        gen_grp.setStyleSheet(GROUP_STYLE)
        gen_layout = QVBoxLayout(gen_grp)

        gen_desc = QLabel(
            "اگر کلید خصوصی و CSR ندارید، اینجا تولید کنید و "
            "فایل CSR را به mycert.ir بفرستید."
        )
        gen_desc.setWordWrap(True)
        gen_desc.setStyleSheet("color: #666; padding: 5px;")
        gen_layout.addWidget(gen_desc)

        gen_btn = QPushButton("⚡ تولید کلید خصوصی + CSR جدید")
        gen_btn.setStyleSheet(BTN_PRIMARY)
        gen_btn.clicked.connect(self._generate_csr)
        gen_layout.addWidget(gen_btn)

        layout.addWidget(gen_grp)

        self.status = make_status("ℹ️ لطفاً اطلاعات را وارد کنید")
        layout.addWidget(self.status)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        test_btn = QPushButton("🔌 تست اتصال")
        test_btn.setStyleSheet(BTN_INFO)
        test_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(test_btn)

        save_btn = QPushButton("💾 ذخیره تنظیمات")
        save_btn.setStyleSheet(BTN_SUCCESS)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _select_key(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "کلید خصوصی", "",
            "Key Files (*.pem *.key);;All Files (*)"
        )
        if path:
            self.key_input.setText(path)

    def _select_cert(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "گواهی‌نامه", "",
            "Cert Files (*.pem *.crt *.cer);;All Files (*)"
        )
        if path:
            self.cert_input.setText(path)

    def _load(self):
        if self.config.fiscal_id:
            self.fiscal_input.setText(self.config.fiscal_id)
        if self.config.economic_code:
            self.economic_input.setText(self.config.economic_code)
        if self.config.private_key_path:
            self.key_input.setText(self.config.private_key_path)
        if self.config.certificate_path:
            self.cert_input.setText(self.config.certificate_path)
        self.sandbox_check.setChecked(self.config.is_sandbox)

    def _collect(self):
        self.config.fiscal_id = self.fiscal_input.text().strip()
        self.config.economic_code = self.economic_input.text().strip()
        self.config.private_key_path = self.key_input.text().strip()
        self.config.certificate_path = self.cert_input.text().strip() or None
        self.config.is_sandbox = self.sandbox_check.isChecked()

    def _save(self):
        self._collect()
        valid, errors = self.config.validate()
        if not valid:
            set_status(self.status, "❌ " + "\n".join(errors), "error")
            return
        if self.config.save():
            self.config.is_configured = True
            set_status(self.status, "✅ تنظیمات ذخیره شد", "success")
        else:
            set_status(self.status, "❌ خطا در ذخیره", "error")

    def _test_connection(self):
        set_status(self.status, "⏳ در حال تست...", "warning")
        QApplication.processEvents()

        self._collect()
        valid, errors = self.config.validate()
        if not valid:
            set_status(self.status, "❌ " + "\n".join(errors), "error")
            return

        client = MoadianClient(self.config)
        ok, msg = client.test_connection()
        set_status(self.status,
                   f"✅ {msg}" if ok else f"❌ {msg}",
                   "success" if ok else "error")

    def _generate_csr(self):
        org = self.fiscal_input.text().strip() or "ImanAccount"
        output_dir = os.path.join(
            os.path.expanduser("~"), ".imanaccount", "moadian"
        )
        try:
            key = CSRGenerator.generate_private_key(2048)
            csr_pem = CSRGenerator.generate_csr(key, org, org)
            key_path, csr_path = CSRGenerator.save_key_and_csr(
                key, csr_pem, output_dir, prefix=self.customer_id
            )
            self.key_input.setText(key_path)
            set_status(
                self.status,
                f"✅ کلید و CSR تولید شد:\n"
                f"🔑 {key_path}\n📄 {csr_path}\n"
                f"فایل CSR را به mycert.ir بفرستید.",
                "success"
            )
        except Exception as e:
            set_status(self.status, f"❌ خطا: {e}", "error")


# ════════════════════════════════════════════════════════════
# ۱۰. ویجت ارسال صورتحساب
# ════════════════════════════════════════════════════════════

class MoadianSendWidget(QWidget):

    invoice_sent = pyqtSignal(dict)

    def __init__(self, customer_id: str = "default", parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.config = MoadianConfig(customer_id)
        self.client = None
        self.products_cache = []
        self._init_ui()
        self.load_products()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        layout.addWidget(make_title("📤 ارسال صورتحساب به سامانه مودیان", 14))

        header_grp = QGroupBox("📋 سرآیند صورتحساب")
        header_grp.setStyleSheet(GROUP_STYLE)
        header_form = QFormLayout(header_grp)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "عادی", "اصلاحی", "ابطالی", "برگشت از فروش"
        ])
        self.type_combo.setStyleSheet("padding: 6px;")
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        header_form.addRow("نوع صورتحساب:", self.type_combo)

        self.ref_taxid = QLineEdit()
        self.ref_taxid.setPlaceholderText("TaxID صورتحساب مرجع")
        self.ref_taxid.setStyleSheet(INPUT_STYLE)
        self.ref_taxid.setEnabled(False)
        header_form.addRow("TaxID مرجع:", self.ref_taxid)

        self.inty_combo = QComboBox()
        self.inty_combo.addItems([
            "1 - نوع اول (B2B)", "2 - نوع دوم (B2C)", "3 - نوع سوم"
        ])
        self.inty_combo.setStyleSheet("padding: 6px;")
        header_form.addRow("الگوی صورتحساب:", self.inty_combo)

        self.setm_combo = QComboBox()
        self.setm_combo.addItems([
            "1 - نقدی", "2 - نسیه", "3 - نقدی/نسیه"
        ])
        self.setm_combo.setStyleSheet("padding: 6px;")
        header_form.addRow("روش تسویه:", self.setm_combo)

        layout.addWidget(header_grp)

        buyer_grp = QGroupBox("👤 خریدار")
        buyer_grp.setStyleSheet(GROUP_STYLE)
        buyer_form = QFormLayout(buyer_grp)

        self.buyer_tinb = QLineEdit()
        self.buyer_tinb.setPlaceholderText("شماره اقتصادی خریدار")
        self.buyer_tinb.setStyleSheet(INPUT_STYLE)
        buyer_form.addRow("شماره اقتصادی:", self.buyer_tinb)

        self.buyer_name = QLineEdit()
        self.buyer_name.setPlaceholderText("نام خریدار")
        self.buyer_name.setStyleSheet(INPUT_STYLE)
        buyer_form.addRow("نام:", self.buyer_name)

        self.buyer_type = QComboBox()
        self.buyer_type.addItems(["1 - حقوقی", "2 - حقیقی"])
        self.buyer_type.setStyleSheet("padding: 6px;")
        buyer_form.addRow("نوع:", self.buyer_type)

        layout.addWidget(buyer_grp)

        items_grp = QGroupBox("📦 اقلام (از انبار)")
        items_grp.setStyleSheet(GROUP_STYLE)
        items_layout = QVBoxLayout(items_grp)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels([
            "کالا (از انبار)", "شرح", "تعداد",
            "قیمت واحد", "مالیات %", "جمع"
        ])
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setMinimumHeight(200)
        self.items_table.setStyleSheet("""
            QTableWidget { border: 1px solid #ddd; border-radius: 6px;
                background: white; font-size: 10pt; }
            QHeaderView::section { background: #273c75; color: white;
                padding: 8px; font-weight: bold; }
        """)
        items_layout.addWidget(self.items_table)

        btn_row = QHBoxLayout()

        add_btn = QPushButton("➕ افزودن از انبار")
        add_btn.setStyleSheet(BTN_SUCCESS)
        add_btn.clicked.connect(self._add_row)
        btn_row.addWidget(add_btn)

        del_btn = QPushButton("➖ حذف قلم")
        del_btn.setStyleSheet(BTN_DANGER)
        del_btn.clicked.connect(self._remove_row)
        btn_row.addWidget(del_btn)

        btn_row.addStretch()

        self.total_label = QLabel("جمع کل: 0 ریال")
        self.total_label.setStyleSheet(
            "font-weight: bold; color: #273c75; padding: 8px;"
        )
        btn_row.addWidget(self.total_label)

        items_layout.addLayout(btn_row)
        layout.addWidget(items_grp)

        action_row = QHBoxLayout()
        action_row.addStretch()

        preview_btn = QPushButton("👁️ پیش‌نمایش")
        preview_btn.setStyleSheet("""
            QPushButton { background: #9b59b6; color: white;
                padding: 12px 30px; border: none;
                border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #8e44ad; }
        """)
        preview_btn.clicked.connect(self._preview)
        action_row.addWidget(preview_btn)

        send_btn = QPushButton("📤 ارسال به مودیان")
        send_btn.setStyleSheet(BTN_PRIMARY)
        send_btn.clicked.connect(self._send)
        action_row.addWidget(send_btn)

        layout.addLayout(action_row)

        self.status = make_status("ℹ️ آماده ارسال")
        layout.addWidget(self.status)

    def load_products(self):
        try:
            self.products_cache = MoadianDatabase.get_products_for_moadian()
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری کالاها: {e}")

    def _on_type_changed(self, idx):
        self.ref_taxid.setEnabled(idx in [1, 2])

    def _add_row(self):
        if not self.products_cache:
            QMessageBox.warning(
                self, "خطا",
                "هیچ کالایی در انبار نیست!\n"
                "ابتدا از بخش انبار کالا تعریف کنید."
            )
            return

        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        combo = QComboBox()
        combo.setMinimumHeight(32)
        combo.addItem("-- انتخاب کالا --", "")
        for p in self.products_cache:
            stock = p.get('stock', 0) or 0
            combo.addItem(
                f"{p['code']} - {p['name']} (موجودی: {stock})",
                p['id']
            )
        combo.currentIndexChanged.connect(
            lambda idx, r=row: self._on_product_changed(r)
        )
        self.items_table.setCellWidget(row, 0, combo)

        self.items_table.setItem(row, 1, QTableWidgetItem(""))

        qty = QDoubleSpinBox()
        qty.setRange(0.01, 999999)
        qty.setValue(1)
        qty.setDecimals(2)
        qty.valueChanged.connect(lambda v, r=row: self._calc_row(r))
        self.items_table.setCellWidget(row, 2, qty)

        price = QLineEdit()
        price.setPlaceholderText("0")
        price.setAlignment(Qt.AlignRight)
        price.textChanged.connect(lambda t, r=row: self._calc_row(r))
        self.items_table.setCellWidget(row, 3, price)

        vat = QSpinBox()
        vat.setRange(0, 100)
        vat.setValue(9)
        vat.setSuffix(" %")
        vat.valueChanged.connect(lambda v, r=row: self._calc_row(r))
        self.items_table.setCellWidget(row, 4, vat)

        total_item = QTableWidgetItem("0")
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
        total_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 5, total_item)

    def _on_product_changed(self, row):
        combo = self.items_table.cellWidget(row, 0)
        if not combo or combo.currentIndex() <= 0:
            return

        product_id = combo.currentData()
        product = next(
            (p for p in self.products_cache if p['id'] == product_id),
            None
        )
        if not product:
            return

        sstid = product.get('mp_sstid') or product.get('moadian_sstid') or ''
        if not sstid:
            QMessageBox.warning(
                self, "شناسه مودیان ثبت نشده",
                f"کالای '{product['name']}' شناسه ۱۳ رقمی مودیان ندارد!\n\n"
                f"لطفاً از تب «کالاهای مودیان» آن را ثبت کنید."
            )
            combo.setCurrentIndex(0)
            return

        desc_item = self.items_table.item(row, 1)
        if desc_item and not desc_item.text():
            desc_item.setText(product['name'])

        price_widget = self.items_table.cellWidget(row, 3)
        if price_widget and not price_widget.text():
            price_widget.setText(str(int(product.get('sale_price') or 0)))

        vat_widget = self.items_table.cellWidget(row, 4)
        if vat_widget:
            vat_widget.setValue(product.get('vat_rate') or 9)

        self._calc_row(row)

    def _calc_row(self, row):
        qty = self.items_table.cellWidget(row, 2)
        price = self.items_table.cellWidget(row, 3)
        vat = self.items_table.cellWidget(row, 4)
        total_item = self.items_table.item(row, 5)

        if not (qty and price and vat and total_item):
            return

        try:
            am = qty.value()
            fee = float(price.text().replace(',', '') or 0)
            vra = vat.value()
            total = am * fee * (1 + vra / 100)
            total_item.setText(f"{total:,.0f}")
        except (ValueError, AttributeError):
            total_item.setText("0")

        self._recalc_total()

    def _recalc_total(self):
        total = 0.0
        for row in range(self.items_table.rowCount()):
            item = self.items_table.item(row, 5)
            if item:
                try:
                    total += float(item.text().replace(',', ''))
                except ValueError:
                    pass
        self.total_label.setText(f"جمع کل: {total:,.0f} ریال")

    def _remove_row(self):
        row = self.items_table.currentRow()
        if row >= 0:
            self.items_table.removeRow(row)
            self._recalc_total()

    def _build_invoice(self) -> Optional[dict]:
        if not self.config.is_configured:
            QMessageBox.warning(
                self, "خطا", "ابتدا تنظیمات مودیان را کامل کنید"
            )
            return None

        type_map = {
            0: StandardInvoiceBuilder.INVOICE_NORMAL,
            1: StandardInvoiceBuilder.INVOICE_CORRECTIVE,
            2: StandardInvoiceBuilder.INVOICE_CANCELLATION,
            3: StandardInvoiceBuilder.INVOICE_RETURN,
        }
        invoice_type = type_map.get(
            self.type_combo.currentIndex(),
            StandardInvoiceBuilder.INVOICE_NORMAL
        )

        builder = StandardInvoiceBuilder(
            self.config.fiscal_id,
            self.config.economic_code,
            self.customer_id,
            invoice_type
        )

        inty = int(self.inty_combo.currentText().split(" - ")[0])
        setm = int(self.setm_combo.currentText().split(" - ")[0])
        builder.set_header(inty=inty, setm=setm)

        if invoice_type in [
            StandardInvoiceBuilder.INVOICE_CORRECTIVE,
            StandardInvoiceBuilder.INVOICE_CANCELLATION
        ]:
            ref = self.ref_taxid.text().strip()
            if ref:
                builder.set_reference_taxid(ref)

        buyer_type = int(self.buyer_type.currentText().split(" - ")[0])
        builder.set_buyer(
            tinb=self.buyer_tinb.text().strip(),
            tinb_type=buyer_type,
            name=self.buyer_name.text().strip() or None
        )

        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 0)
            if not combo or combo.currentIndex() <= 0:
                continue

            product_id = combo.currentData()
            product = next(
                (p for p in self.products_cache if p['id'] == product_id),
                None
            )
            if not product:
                continue

            sstid = (
                product.get('mp_sstid')
                or product.get('moadian_sstid')
                or ''
            )

            qty_w = self.items_table.cellWidget(row, 2)
            price_w = self.items_table.cellWidget(row, 3)
            vat_w = self.items_table.cellWidget(row, 4)

            am = qty_w.value() if qty_w else 1
            try:
                fee = float(price_w.text().replace(',', '') or 0)
            except (ValueError, AttributeError):
                fee = 0
            vra = vat_w.value() if vat_w else 9

            desc_item = self.items_table.item(row, 1)
            sstt = desc_item.text() if desc_item else product['name']

            unit = product.get('unit_moadian') or '1627'

            builder.add_item(
                sstid=sstid, sstt=sstt, am=am, fee=fee,
                vra=vra, unit=unit
            )

        valid, errors = builder.validate()
        if not valid:
            QMessageBox.warning(
                self, "خطای اعتبارسنجی", "\n".join(errors)
            )
            return None

        return builder.build()

    def _preview(self):
        invoice = self._build_invoice()
        if not invoice:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("پیش‌نمایش صورتحساب")
        dlg.resize(700, 500)
        v = QVBoxLayout(dlg)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            json.dumps(invoice, ensure_ascii=False, indent=2)
        )
        text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 10pt;"
        )
        v.addWidget(text)

        close_btn = QPushButton("بستن")
        close_btn.setStyleSheet(BTN_PRIMARY)
        close_btn.clicked.connect(dlg.accept)
        v.addWidget(close_btn)

        dlg.exec_()

    def _send(self):
        invoice = self._build_invoice()
        if not invoice:
            return

        reply = QMessageBox.question(
            self, "تأیید",
            "ارسال این صورتحساب به سامانه مودیان؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        set_status(self.status, "⏳ در حال ارسال...", "warning")
        QApplication.processEvents()

        if not self.client:
            self.client = MoadianClient(self.config)

        type_map = {
            0: 'normal', 1: 'corrective',
            2: 'cancellation', 3: 'return'
        }
        itype = type_map.get(self.type_combo.currentIndex(), 'normal')

        ok, result = self.client.send_invoice(invoice, itype)

        if ok:
            set_status(self.status, "✅ ارسال موفق", "success")
            self.invoice_sent.emit(result)
            QMessageBox.information(
                self, "موفق",
                f"صورتحساب ارسال شد.\n\n"
                f"{json.dumps(result, ensure_ascii=False)[:500]}"
            )
        else:
            err = result.get('error', 'ناشناخته')
            set_status(self.status, f"❌ خطا: {err}", "error")
            QMessageBox.critical(
                self, "خطا",
                f"ارسال ناموفق:\n\n"
                f"{json.dumps(result, ensure_ascii=False)[:500]}"
            )


# ════════════════════════════════════════════════════════════
# ۱۱. ویجت استعلام
# ════════════════════════════════════════════════════════════

class MoadianInquiryWidget(QWidget):

    def __init__(self, customer_id: str = "default", parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.config = MoadianConfig(customer_id)
        self.client = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(make_title("🔍 استعلام وضعیت صورتحساب"))

        grp = QGroupBox("جستجو")
        grp.setStyleSheet(GROUP_STYLE)
        form = QFormLayout(grp)

        self.type = QComboBox()
        self.type.addItems(["UID", "شماره مرجع", "TaxID"])
        self.type.setStyleSheet("padding: 6px;")
        form.addRow("نوع:", self.type)

        self.value = QLineEdit()
        self.value.setPlaceholderText("مقدار را وارد کنید")
        self.value.setStyleSheet(INPUT_STYLE)
        form.addRow("مقدار:", self.value)

        layout.addWidget(grp)

        btn = QPushButton("🔍 استعلام")
        btn.setStyleSheet(BTN_PRIMARY)
        btn.clicked.connect(self._do)
        layout.addWidget(btn)

        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setStyleSheet("""
            font-family: Consolas, monospace; font-size: 10pt;
            border: 1px solid #ddd; border-radius: 6px;
            padding: 10px; background: #f8f9fa;
        """)
        layout.addWidget(self.result)

    def _do(self):
        if not self.config.is_configured:
            QMessageBox.warning(self, "خطا", "تنظیمات را کامل کنید")
            return

        val = self.value.text().strip()
        if not val:
            QMessageBox.warning(self, "خطا", "مقدار را وارد کنید")
            return

        self.result.setPlainText("⏳ در حال استعلام...")
        QApplication.processEvents()

        if not self.client:
            self.client = MoadianClient(self.config)

        t = self.type.currentText()
        if t == "UID":
            ok, res = self.client.inquiry_by_uid(val)
        elif t == "شماره مرجع":
            ok, res = self.client.inquiry_by_ref(val)
        else:
            ok, res = self.client.inquiry_by_taxid(val)

        prefix = "" if ok else "❌ "
        self.result.setPlainText(
            prefix + json.dumps(res, ensure_ascii=False, indent=2)
        )


# ════════════════════════════════════════════════════════════
# ۱۲. ویجت تاریخچه
# ════════════════════════════════════════════════════════════

class MoadianHistoryWidget(QWidget):

    def __init__(self, customer_id: str = "default", parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        layout.addWidget(make_title("📚 تاریخچه صورتحساب‌ها", 14))

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "TaxID", "نوع", "شماره مرجع", "UID", "وضعیت", "تاریخ"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #ddd; border-radius: 6px;
                background: white; }
            QHeaderView::section { background: #273c75; color: white;
                padding: 8px; font-weight: bold; }
        """)
        layout.addWidget(self.table)

        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet(BTN_INFO)
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

    def refresh(self):
        invoices = MoadianDatabase.get_invoices(self.customer_id, 100)
        self.table.setRowCount(len(invoices))

        type_map = {
            'normal': 'عادی', 'corrective': 'اصلاحی',
            'cancellation': 'ابطالی', 'return': 'برگشت'
        }

        for i, inv in enumerate(invoices):
            values = [
                inv.get('taxid', ''),
                type_map.get(inv.get('invoice_type', 'normal'), 'عادی'),
                inv.get('reference_number', '') or '-',
                inv.get('uid', '') or '-',
                inv.get('status', ''),
                inv.get('sent_at', '') or '',
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if col == 4:
                    f = QFont()
                    f.setBold(True)
                    item.setFont(f)
                self.table.setItem(i, col, item)


# ════════════════════════════════════════════════════════════
# ۱۳. رویدادهای پلاگین — هماهنگ با plugin_loader.py v4.0
# ════════════════════════════════════════════════════════════

def on_init():
    """
    راه‌اندازی اولیه — اجرای migration خودکار.
    توسط Plugin._create_plugin() فراخوانی می‌شود.
    """
    print(f"🚀 {PLUGIN_NAME} v{PLUGIN_VERSION} راه‌اندازی می‌شود...")

    if not MoadianMigration.run():
        print("❌ Migration ناموفق!")
        return False

    print(f"✅ {PLUGIN_NAME} آماده است")
    return True


def on_cleanup():
    """پاکسازی هنگام حذف پلاگین"""
    global _widget_cache
    _widget_cache.clear()
    print(f"🧹 {PLUGIN_NAME} پاکسازی شد")


def on_tab() -> List[Dict]:
    """
    لیست تب‌ها — طبق استاندارد plugin_loader v4.0.

    Returns:
        list of dict: [{'title': str, 'widget_id': str}, ...]
    """
    return [
        {'title': '📤 ارسال', 'widget_id': 'moadian_send'},
        {'title': '📦 کالاها', 'widget_id': 'moadian_products'},
        {'title': '🔍 استعلام', 'widget_id': 'moadian_inquiry'},
        {'title': '📚 تاریخچه', 'widget_id': 'moadian_history'},
        {'title': '⚙️ تنظیمات', 'widget_id': 'moadian_settings'},
    ]


def on_menu() -> List[Dict]:
    """
    منوهای پلاگین — طبق استاندارد plugin_loader v4.0.

    Returns:
        list of dict: [{'title': str, 'actions': [...]}, ...]
    """
    return [
        {
            'title': 'مودیان',
            'icon': '📤',
            'actions': [
                {
                    'id': 'open_moadian_send',
                    'title': 'ارسال صورتحساب',
                    'icon': '📤',
                },
                {
                    'id': 'open_moadian_products',
                    'title': 'مدیریت کالاها',
                    'icon': '📦',
                },
                {
                    'id': 'open_moadian_inquiry',
                    'title': 'استعلام وضعیت',
                    'icon': '🔍',
                },
                {
                    'id': 'open_moadian_settings',
                    'title': 'تنظیمات اتصال',
                    'icon': '⚙️',
                },
            ],
        },
    ]


def on_widget(widget_id: str) -> Optional[QWidget]:
    """
    ساخت ویجت بر اساس شناسه — طبق استاندارد plugin_loader v4.0.

    Args:
        widget_id: یکی از 'moadian_send', 'moadian_products',
                   'moadian_inquiry', 'moadian_history', 'moadian_settings'

    Returns:
        QWidget یا None
    """
    global _widget_cache

    if not _migration_done:
        MoadianMigration.run()

    if widget_id in _widget_cache:
        return _widget_cache[widget_id]

    try:
        if widget_id == 'moadian_send':
            widget = MoadianSendWidget(_customer_id)
        elif widget_id == 'moadian_products':
            widget = MoadianProductsWidget()
        elif widget_id == 'moadian_inquiry':
            widget = MoadianInquiryWidget(_customer_id)
        elif widget_id == 'moadian_history':
            widget = MoadianHistoryWidget(_customer_id)
        elif widget_id == 'moadian_settings':
            widget = MoadianSettingsWidget(_customer_id)
        else:
            print(f"⚠️ widget_id نامعتبر: {widget_id}")
            return None

        _widget_cache[widget_id] = widget
        return widget

    except Exception as e:
        print(f"❌ خطا در ساخت ویجت {widget_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def on_action(action_id: str, **kwargs):
    """
    اجرای اکشن‌های منو — طبق استاندارد plugin_loader v4.0.

    Args:
        action_id: شناسه اکشن
        **kwargs: شامل 'parent' از MainWindow
    """
    try:
        parent = kwargs.get('parent')

        if action_id == 'open_moadian_send':
            dlg = QDialog(parent)
            dlg.setWindowTitle("ارسال صورتحساب به مودیان")
            dlg.resize(950, 780)
            v = QVBoxLayout(dlg)
            v.addWidget(MoadianSendWidget(_customer_id))
            dlg.exec_()
            return True

        elif action_id == 'open_moadian_products':
            dlg = QDialog(parent)
            dlg.setWindowTitle("مدیریت کالاهای مودیان")
            dlg.resize(950, 750)
            v = QVBoxLayout(dlg)
            v.addWidget(MoadianProductsWidget())
            dlg.exec_()
            return True

        elif action_id == 'open_moadian_inquiry':
            dlg = QDialog(parent)
            dlg.setWindowTitle("استعلام وضعیت")
            dlg.resize(750, 600)
            v = QVBoxLayout(dlg)
            v.addWidget(MoadianInquiryWidget(_customer_id))
            dlg.exec_()
            return True

        elif action_id == 'open_moadian_settings':
            dlg = QDialog(parent)
            dlg.setWindowTitle("تنظیمات مودیان")
            dlg.resize(800, 750)
            v = QVBoxLayout(dlg)
            v.addWidget(MoadianSettingsWidget(_customer_id))
            dlg.exec_()
            return True

    except Exception as e:
        print(f"❌ خطا در اکشن {action_id}: {e}")
        import traceback
        traceback.print_exc()

    return False


def set_customer(customer_id: str):
    """
    تعیین مشتری فعال — برای Multi-tenant.
    این تابع از بیرون (MainWindow) فراخوانی می‌شود.
    """
    global _customer_id, _widget_cache
    _customer_id = customer_id
    _widget_cache.clear()
    print(f"👤 مشتری مودیان تغییر کرد به: {customer_id}")


# ════════════════════════════════════════════════════════════
# ۱۴. کلاس سازگاری با کدهای قدیمی
# ════════════════════════════════════════════════════════════

class MoadianPlugin:
    """Wrapper سازگاری با کدهای قدیمی"""

    def __init__(self, app=None):
        self.app = app
        self.customer_id = "default"
        on_init()

    def get_main_widget(self, customer_id: str = "default"):
        global _customer_id
        _customer_id = customer_id

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ddd;
                border-radius: 6px; background: white; }
            QTabBar::tab { padding: 10px 20px; font-weight: bold;
                background: #f0f0f0; border: 1px solid #ddd;
                margin-right: 2px; }
            QTabBar::tab:selected { background: #273c75; color: white; }
        """)

        for tab_info in on_tab():
            widget = on_widget(tab_info['widget_id'])
            if widget:
                tabs.addTab(widget, tab_info['title'])

        return tabs


# ════════════════════════════════════════════════════════════
# ۱۵. تست مستقل
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    try:
        from database import DatabaseManager
        DatabaseManager.init_db()
    except ImportError:
        print("⚠️ database.py یافت نشد")
        sys.exit(1)

    if not on_init():
        print("❌ پلاگین راه‌اندازی نشد")
        sys.exit(1)

    window = QTabWidget()
    window.setWindowTitle(f"{PLUGIN_NAME} v{PLUGIN_VERSION} — تست")
    window.resize(1000, 750)
    window.setStyleSheet("""
        QTabWidget::pane { border: 1px solid #ddd;
            border-radius: 6px; background: white; }
        QTabBar::tab { padding: 10px 20px; font-weight: bold;
            background: #f0f0f0; border: 1px solid #ddd;
            margin-right: 2px; }
        QTabBar::tab:selected { background: #273c75; color: white; }
    """)

    for tab_info in on_tab():
        widget = on_widget(tab_info['widget_id'])
        if widget:
            window.addTab(widget, tab_info['title'])

    window.show()
    sys.exit(app.exec_())
