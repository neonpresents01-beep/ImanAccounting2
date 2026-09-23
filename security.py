# security.py
# ============================================================
# ماژول امنیت — مدیریت رمز عبور با bcrypt مستقیم
# نسخه 2.0 (بدون passlib — فقط bcrypt)
# ============================================================

import hashlib
import hmac
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


# ============================================================
# Import bcrypt
# ============================================================

try:
    import bcrypt as _bcrypt
    BCRYPT_AVAILABLE = True
    logger.info(f"✅ bcrypt بارگذاری شد")
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("⚠️ bcrypt نصب نیست!")


# ============================================================
# ثابت‌ها
# ============================================================

BCRYPT_ROUNDS = 12
MAX_PASSWORD_BYTES = 72
SHA256_SALT = "ImanAI_Salt_v1"


# ============================================================
# PasswordHasher
# ============================================================

class PasswordHasher:
    """مدیریت امن رمز عبور"""
    
    @classmethod
    def hash(cls, password: str) -> str:
        """Hash کردن رمز عبور"""
        if not password:
            raise ValueError("رمز عبور نمی‌تواند خالی باشد")
        
        password_bytes = password.encode('utf-8')[:MAX_PASSWORD_BYTES]
        
        if BCRYPT_AVAILABLE:
            try:
                salt = _bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
                hashed = _bcrypt.hashpw(password_bytes, salt)
                return hashed.decode('utf-8')
            except Exception as e:
                logger.error(f"❌ خطا در bcrypt.hash: {e}")
        
        logger.warning("⚠️ استفاده از SHA-256 fallback")
        return hashlib.sha256(
            f"{SHA256_SALT}{password}".encode('utf-8')
        ).hexdigest()
    
    @classmethod
    def verify(cls, password: str, stored_hash: str) -> Tuple[bool, bool]:
        """بررسی رمز عبور"""
        if not password or not stored_hash:
            return False, False
        
        password_bytes = password.encode('utf-8')[:MAX_PASSWORD_BYTES]
        
        is_bcrypt = stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$")
        
        if is_bcrypt and BCRYPT_AVAILABLE:
            try:
                is_valid = _bcrypt.checkpw(
                    password_bytes,
                    stored_hash.encode('utf-8')
                )
                return bool(is_valid), False
            except Exception as e:
                logger.error(f"❌ خطا در bcrypt.checkpw: {e}")
                return False, False
        
        elif len(stored_hash) == 64 and ':' not in stored_hash:
            new_hash = hashlib.sha256(
                f"{SHA256_SALT}{password}".encode('utf-8')
            ).hexdigest()
            
            if hmac.compare_digest(new_hash, stored_hash):
                return True, True
            
            old_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            
            if hmac.compare_digest(old_hash, stored_hash):
                return True, True
            
            return False, False
        
        return False, False
    
    @classmethod
    def needs_rehash(cls, stored_hash: str) -> bool:
        """آیا نیاز به hash مجدد داره؟"""
        if not stored_hash:
            return True
        if not BCRYPT_AVAILABLE:
            return False
        if not (stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$")):
            return True
        try:
            parts = stored_hash.split('$')
            if len(parts) >= 3:
                rounds = int(parts[2])
                return rounds < BCRYPT_ROUNDS
        except Exception:
            pass
        return False
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """اعتبارسنجی قدرت رمز"""
        if not password:
            return False, "رمز عبور نمی‌تواند خالی باشد"
        
        if len(password) < 6:
            return False, "رمز عبور باید حداقل ۶ کاراکتر باشد"
        
        if len(password.encode('utf-8')) > MAX_PASSWORD_BYTES:
            return False, f"رمز عبور بیش از {MAX_PASSWORD_BYTES} بایت است"
        
        warnings = []
        if not any(c.isdigit() for c in password):
            warnings.append("بدون عدد")
        if not any(c.isalpha() for c in password):
            warnings.append("بدون حرف")
        
        if warnings:
            return True, f"⚠️ نکته: رمز {' و '.join(warnings)} است"
        
        return True, ""
    
    @staticmethod
    def get_password_strength_score(password: str) -> int:
        """امتیاز قدرت رمز"""
        if not password:
            return 0
        
        score = 0
        score += min(len(password) * 4, 40)
        
        if any(c.islower() for c in password):
            score += 10
        if any(c.isupper() for c in password):
            score += 15
        if any(c.isdigit() for c in password):
            score += 15
        if any(not c.isalnum() for c in password):
            score += 20
        
        return min(score, 100)


# ============================================================
# Migration
# ============================================================

def migrate_old_passwords() -> dict:
    """علامت‌گذاری hashهای قدیمی برای تغییر"""
    if not BCRYPT_AVAILABLE:
        logger.warning("⚠️ bcrypt نصب نیست — migration انجام نشد")
        return {'migrated': 0, 'failed': 0, 'total': 0, 'error': 'bcrypt not installed'}
    
    result = {'migrated': 0, 'failed': 0, 'total': 0}
    
    try:
        from database import get_db
        
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute("SELECT id, username, password_hash FROM users")
            users = c.fetchall()
            
            result['total'] = len(users)
            
            for user in users:
                user_id = user['id']
                username = user['username']
                old_hash = user['password_hash']
                
                if old_hash.startswith("$2"):
                    continue
                
                if len(old_hash) == 64:
                    try:
                        c.execute(
                            "UPDATE users SET password_hash = ?, "
                            "must_change_password = 1 WHERE id = ?",
                            [f"SHA256_MIGRATED:{old_hash}", user_id]
                        )
                        result['migrated'] += 1
                        logger.info(f"✅ {username}: علامت‌گذاری شد")
                    except Exception as e:
                        result['failed'] += 1
                        logger.error(f"❌ {username}: {e}")
            
            conn.commit()
    
    except Exception as e:
        logger.error(f"❌ خطا در migration: {e}")
        result['error'] = str(e)
    
    return result


# ============================================================
# تست
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("🔐 تست PasswordHasher")
    print("=" * 60)
    
    print(f"\n✅ bcrypt available: {BCRYPT_AVAILABLE}")
    
    password = "admin123"
    h = PasswordHasher.hash(password)
    print(f"\n📝 Hash: {h[:60]}...")
    
    valid, rehash = PasswordHasher.verify(password, h)
    print(f"✅ Verify صحیح: {valid} (needs_rehash: {rehash})")
    
    valid, _ = PasswordHasher.verify("wrong", h)
    print(f"❌ Verify غلط: {valid}")
    
    old_hash = hashlib.sha256(f"{SHA256_SALT}admin123".encode()).hexdigest()
    valid, rehash = PasswordHasher.verify("admin123", old_hash)
    print(f"🔄 SHA-256 → bcrypt: valid={valid}, needs_rehash={rehash}")
    
    for pwd in ["123", "admin123", "Admin@123", "MyStr0ng!Pass#2025"]:
        score = PasswordHasher.get_password_strength_score(pwd)
        print(f"📊 Strength '{pwd}': {score}%")
    
    long_pwd = "a" * 100
    try:
        h = PasswordHasher.hash(long_pwd)
        print(f"✅ رمز ۱۰۰ کاراکتری: {h[:30]}...")
        valid, _ = PasswordHasher.verify(long_pwd, h)
        print(f"✅ Verify رمز بلند: {valid}")
    except Exception as e:
        print(f"❌ خطا در رمز بلند: {e}")
    
    print("\n" + "=" * 60)
    print("✅ تست کامل شد")
    print("=" * 60)
