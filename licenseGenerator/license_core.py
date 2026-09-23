# license_core.py - نسخه نهایی با پشتیبانی از محدودیت ماژول و HWID

import hashlib
import base64
import json
import os
import uuid
import platform
import socket
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# ============================================================
# تنظیمات امنیتی
# ============================================================

# خواندن کلید از متغیر محیطی (امن‌تر برای توزیع)
MASTER_KEY = os.environ.get('IMANAI_MASTER_KEY', 'ImanAI_Super_Secret_Key_2024_ChangeMe!').encode()
SALT = b"ImanAccounting_Salt_2024"


# ============================================================
# کلاس اصلی تولید و دیکد لایسنس
# ============================================================

class LicenseGenerator:
    """تولید و بررسی لایسنس با پشتیبانی از محدودیت ماژول"""
    
    def __init__(self):
        self.fernet = self._get_fernet()
    
    def _get_fernet(self):
        """دریافت رمزنگار Fernet"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=SALT,
            iterations=480000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(MASTER_KEY))
        return Fernet(key)
    
    @staticmethod
    def get_system_hwid() -> str:
        """دریافت HWID منحصربه‌فرد سیستم"""
        try:
            # ترکیبی از اطلاعات سخت‌افزاری و نرم‌افزاری
            hostname = socket.gethostname()
            processor = platform.processor()
            machine = platform.machine()
            system = platform.system()
            
            # تلاش برای دریافت Mac Address
            import uuid as uuid_lib
            mac = uuid_lib.getnode()
            
            hw_string = f"{hostname}-{processor}-{machine}-{system}-{mac}"
            return hashlib.sha256(hw_string.encode()).hexdigest()[:32]
        except:
            return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]
    
    def generate_license(self, customer_name: str, hwid: str, expire_days: int = 30, 
                         modules: list = None, limits: dict = None, 
                         public_key: str = None, is_admin: bool = False,
                         is_school: bool = False) -> dict:
        """
        ساخت لایسنس جدید با پشتیبانی از محدودیت ماژول
        
        Args:
            customer_name: نام مشتری
            hwid: HWID سیستم
            expire_days: تعداد روز اعتبار (0 = نامحدود)
            modules: لیست ماژول‌های فعال
            limits: دیکشنری محدودیت‌ها {'accounting': 100, 'inventory': 50}
            public_key: کلید عمومی RSA برای امضای پلاگین
            is_admin: آیا لایسنس ادمین است
            is_school: آیا لایسنس مدرسه است
        
        Returns:
            dict: شامل raw, formatted, data
        """
        if modules is None:
            modules = ['accounting', 'inventory', 'payroll', 'parties', 'invoice', 'purchase']
        
        if limits is None:
            limits = {
                'accounting': 0,   # 0 = نامحدود
                'inventory': 0,
                'payroll': 0,
                'parties': 0,
                'invoice': 0,
                'purchase': 0
            }
        
        # تاریخ انقضا
        if expire_days == 0:
            expire_date = "نامحدود"
        else:
            expire_date = (datetime.now() + timedelta(days=expire_days)).strftime("%Y-%m-%d")
        
        created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        license_id = str(uuid.uuid4())[:8]
        
        # ساخت payload
        payload = {
            "license_id": license_id,
            "customer": customer_name,
            "hwid": hwid,
            "expire": expire_date,
            "modules": modules,
            "limits": limits,
            "public_key": public_key,
            "is_admin": is_admin,
            "is_school": is_school,
            "created": created_date,
            "version": "2.0.0"
        }
        
        # رمزنگاری
        encrypted = self.fernet.encrypt(json.dumps(payload).encode())
        license_key = base64.b64encode(encrypted).decode()
        
        # فرمت کردن با خط تیره
        formatted = "-".join([license_key[i:i+4] for i in range(0, len(license_key), 4)])
        
        return {
            "raw": license_key, 
            "formatted": formatted, 
            "data": payload
        }
    
    def decode_license(self, license_key: str) -> dict:
        """
        دیکد کردن لایسنس و بررسی اعتبار
        
        Args:
            license_key: کلید لایسنس (با یا بدون خط تیره)
        
        Returns:
            dict: اطلاعات لایسنس یا خطا
        """
        try:
            # حذف خط تیره‌ها
            license_key = license_key.replace("-", "").strip()
            
            # دیکد base64
            encrypted = base64.b64decode(license_key)
            
            # رمزگشایی
            decrypted = self.fernet.decrypt(encrypted)
            data = json.loads(decrypted.decode())
            
            # سازگاری با نسخه‌های قدیمی (اضافه کردن فیلدهای缺失)
            if 'limits' not in data:
                data['limits'] = {}
            
            if 'is_admin' not in data:
                data['is_admin'] = False
            
            if 'is_school' not in data:
                data['is_school'] = False
            
            # محاسبه روزهای باقیمانده
            if data.get('expire') and data['expire'] != "نامحدود":
                try:
                    expire = datetime.strptime(data['expire'], "%Y-%m-%d")
                    days_left = (expire - datetime.now()).days
                    data['days_left'] = max(0, days_left)
                    data['is_expired'] = days_left <= 0
                except:
                    data['days_left'] = 365
                    data['is_expired'] = False
            else:
                data['days_left'] = 3650
                data['is_expired'] = False
            
            return data
            
        except Exception as e:
            return {"error": str(e), "is_expired": True}
    
    def verify_license(self, license_key: str, hwid: str = None) -> dict:
        """
        بررسی کامل لایسنس (اعتبار + HWID + انقضا)
        
        Args:
            license_key: کلید لایسنس
            hwid: HWID سیستم (اگر None باشد، HWID فعلی استفاده می‌شود)
        
        Returns:
            dict: نتیجه بررسی
        """
        if hwid is None:
            hwid = self.get_system_hwid()
        
        data = self.decode_license(license_key)
        
        if "error" in data:
            return {
                "valid": False,
                "error": data["error"],
                "message": f"❌ لایسنس نامعتبر: {data['error']}"
            }
        
        # بررسی HWID
        if data.get('hwid') and data['hwid'] != hwid and not data.get('is_admin'):
            return {
                "valid": False,
                "error": "hwid_mismatch",
                "message": "❌ این لایسنس برای این کامپیوتر نیست!"
            }
        
        # بررسی انقضا
        if data.get('is_expired', False):
            return {
                "valid": False,
                "error": "expired",
                "message": f"❌ لایسنس منقضی شده است! (انقضا: {data.get('expire', 'نامشخص')})"
            }
        
        return {
            "valid": True,
            "data": data,
            "message": f"✅ لایسنس معتبر است | مشتری: {data.get('customer')} | انقضا: {data.get('expire')}"
        }
    
    def get_module_limit(self, license_key: str, module_name: str, hwid: str = None) -> int:
        """
        دریافت محدودیت یک ماژول خاص از لایسنس
        
        Args:
            license_key: کلید لایسنس
            module_name: نام ماژول (accounting, inventory, ...)
            hwid: HWID سیستم
        
        Returns:
            int: محدودیت (0 = نامحدود)
        """
        result = self.verify_license(license_key, hwid)
        if not result.get("valid"):
            return 0
        
        data = result.get("data", {})
        limits = data.get("limits", {})
        return limits.get(module_name, 0)
    
    def has_module(self, license_key: str, module_name: str, hwid: str = None) -> bool:
        """
        بررسی وجود ماژول در لایسنس
        
        Args:
            license_key: کلید لایسنس
            module_name: نام ماژول
            hwid: HWID سیستم
        
        Returns:
            bool: آیا ماژول فعال است
        """
        result = self.verify_license(license_key, hwid)
        if not result.get("valid"):
            return False
        
        data = result.get("data", {})
        modules = data.get("modules", [])
        return module_name in modules


# ============================================================
# کلاس مدیریت لایسنس (برای استفاده در برنامه اصلی)
# ============================================================

class LicenseManager:
    """مدیریت لایسنس در برنامه اصلی"""
    
    def __init__(self, license_file: str = "license.key"):
        self.license_file = license_file
        self.generator = LicenseGenerator()
        self._license_data = None
        self._hwid = self.generator.get_system_hwid()
        self.load_license()
    
    def load_license(self) -> tuple:
        """
        بارگذاری لایسنس از فایل
        
        Returns:
            (data, error): داده‌های لایسنس یا خطا
        """
        if not os.path.exists(self.license_file):
            return None, "not_found"
        
        try:
            with open(self.license_file, 'r', encoding='utf-8') as f:
                license_key = f.read().strip()
            
            if not license_key:
                return None, "empty"
            
            result = self.generator.verify_license(license_key, self._hwid)
            
            if result.get("valid"):
                self._license_data = result.get("data")
                return self._license_data, None
            else:
                return None, result.get("error", "invalid")
                
        except Exception as e:
            return None, f"error: {str(e)}"
    
    def save_license(self, license_key: str) -> bool:
        """ذخیره لایسنس در فایل"""
        try:
            with open(self.license_file, 'w', encoding='utf-8') as f:
                f.write(license_key)
            self.load_license()
            return True
        except:
            return False
    
    def create_demo_license(self, days: int = 30) -> bool:
        """ایجاد لایسنس آزمایشی"""
        result = self.generator.generate_license(
            customer_name="نسخه آزمایشی",
            hwid=self._hwid,
            expire_days=days,
            modules=['accounting', 'inventory', 'payroll', 'parties', 'invoice', 'purchase', 'ai', 'reports'],
            limits={}
        )
        return self.save_license(result['formatted'])
    
    def get_module_limit(self, module_name: str) -> int:
        """دریافت محدودیت ماژول"""
        if not self._license_data:
            return 0
        limits = self._license_data.get('limits', {})
        return limits.get(module_name, 0)
    
    def has_module(self, module_name: str) -> bool:
        """بررسی وجود ماژول"""
        if not self._license_data:
            return False
        modules = self._license_data.get('modules', [])
        return module_name in modules
    
    def get_modules(self) -> list:
        """دریافت لیست ماژول‌های فعال"""
        if not self._license_data:
            return []
        return self._license_data.get('modules', [])
    
    def get_days_left(self) -> int:
        """دریافت روزهای باقیمانده"""
        if not self._license_data:
            return 0
        return self._license_data.get('days_left', 0)
    
    def is_admin(self) -> bool:
        """آیا لایسنس ادمین است"""
        if not self._license_data:
            return False
        return self._license_data.get('is_admin', False)
    
    def is_school(self) -> bool:
        """آیا لایسنس مدرسه است"""
        if not self._license_data:
            return False
        return self._license_data.get('is_school', False)
    
    def get_info(self) -> dict:
        """دریافت اطلاعات لایسنس"""
        if not self._license_data:
            return {
                'valid': False,
                'error': 'no_license'
            }
        
        return {
            'valid': True,
            'customer': self._license_data.get('customer', 'نامشخص'),
            'modules': self._license_data.get('modules', []),
            'limits': self._license_data.get('limits', {}),
            'expire_date': self._license_data.get('expire', 'نامحدود'),
            'days_left': self._license_data.get('days_left', 0),
            'is_admin': self._license_data.get('is_admin', False),
            'is_school': self._license_data.get('is_school', False),
            'license_id': self._license_data.get('license_id', '')
        }


# ============================================================
# تست
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 تست سیستم لایسنس ImanAI")
    print("=" * 60)
    
    # ایجاد نمونه
    gen = LicenseGenerator()
    hwid = gen.get_system_hwid()
    print(f"🖥️ HWID سیستم: {hwid}")
    
    # ساخت لایسنس آزمایشی
    print("\n📝 ساخت لایسنس آزمایشی...")
    limits = {
        'accounting': 100,
        'inventory': 50,
        'payroll': 10
    }
    
    lic = gen.generate_license(
        customer_name="شرکت تست",
        hwid=hwid,
        expire_days=30,
        modules=['accounting', 'inventory', 'payroll'],
        limits=limits
    )
    
    print(f"📋 لایسنس: {lic['formatted']}")
    print(f"📦 ماژول‌ها: {lic['data']['modules']}")
    print(f"⚙️ محدودیت‌ها: {lic['data']['limits']}")
    
    # بررسی لایسنس
    print("\n🔍 بررسی لایسنس...")
    result = gen.verify_license(lic['formatted'], hwid)
    print(result['message'])
    
    if result['valid']:
        data = result['data']
        print(f"   👤 مشتری: {data.get('customer')}")
        print(f"   📅 انقضا: {data.get('expire')}")
        print(f"   📊 محدودیت حسابداری: {data.get('limits', {}).get('accounting', 0)}")
        print(f"   📦 محدودیت انبار: {data.get('limits', {}).get('inventory', 0)}")
    
    print("\n" + "=" * 60)
    print("✅ تست با موفقیت انجام شد!")