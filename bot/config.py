import os
import json

# ====== ملف حفظ الإعدادات ======
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")


def load_settings():
    """تحميل الإعدادات من ملف JSON إن وُجد"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_settings(data: dict):
    """حفظ الإعدادات إلى ملف JSON"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ====== تحميل الإعدادات ======
_settings = load_settings()

# ====== المتغيرات العامة ======
API_ID = int(_settings.get("api_id", 0))
API_HASH = _settings.get("api_hash", "")
TOKEN = _settings.get("token", "")
Dev_Zaid = int(_settings.get("dev_zaid", 0))   # ID المالك / المطور
sudo_id = [Dev_Zaid] if Dev_Zaid else []        # قائمة المشرفين
botUsername = _settings.get("bot_username", "")

# ====== إعدادات Redis ======
REDIS_HOST = _settings.get("redis_host", "localhost")
REDIS_PORT = int(_settings.get("redis_port", 6379))
REDIS_DB = int(_settings.get("redis_db", 0))
REDIS_PASSWORD = _settings.get("redis_password", None) or None
