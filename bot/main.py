import os
import sys
import asyncio
import redis
from pyrogram import Client, idle

import config


def ask_and_save_settings():
    """يطلب من المستخدم البيانات الأساسية ويحفظها إن لم تكن موجودة"""
    data = config.load_settings()
    changed = False

    if not data.get("api_id"):
        data["api_id"] = input("ادخل API_ID : ").strip()
        changed = True

    if not data.get("api_hash"):
        data["api_hash"] = input("ادخل API_HASH : ").strip()
        changed = True

    if not data.get("token"):
        data["token"] = input("ادخل توكن البوت (BOT TOKEN) : ").strip()
        changed = True

    if not data.get("dev_zaid"):
        data["dev_zaid"] = input("ادخل ايدي المالك (Dev_Zaid) : ").strip()
        changed = True

    if changed:
        config.save_settings(data)
        print("✅ تم حفظ الإعدادات في settings.json")

    # تحديث القيم في وحدة config
    config.API_ID = int(data["api_id"])
    config.API_HASH = data["api_hash"]
    config.TOKEN = data["token"]
    config.Dev_Zaid = int(data["dev_zaid"])
    config.sudo_id = [config.Dev_Zaid]


def connect_redis():
    """الاتصال بـ Redis والتأكد من نجاح الاتصال"""
    try:
        r = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
            decode_responses=True,
        )
        r.ping()
        print(f"✅ تم الاتصال بـ Redis على {config.REDIS_HOST}:{config.REDIS_PORT}")
        return r
    except Exception as e:
        print(f"❌ فشل الاتصال بـ Redis : {e}")
        sys.exit(1)


async def main():
    # 1) جلب وحفظ الإعدادات
    ask_and_save_settings()

    # 2) الاتصال بـ Redis
    rds = connect_redis()

    # 3) تهيئة Pyrogram Client مع نظام Plugins
    plugins_path = os.path.join(os.path.dirname(__file__), "plugins")
    app = Client(
        name="MyBot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.TOKEN,
        plugins=dict(root="plugins"),
        workdir=os.path.dirname(__file__),
    )

    # حقن Redis كخاصية داخل البوت ليستفيد منها أي Plugin لاحقًا
    app.redis = rds

    # 4) تشغيل البوت
    await app.start()
    me = await app.get_me()
    config.botUsername = me.username

    # حفظ اليوزرنيم
    data = config.load_settings()
    data["bot_username"] = me.username
    config.save_settings(data)

    print("──────────────────────────────────────")
    print(f"🤖 البوت يعمل الآن : @{me.username}")
    print(f"👤 المالك (Dev_Zaid) : {config.Dev_Zaid}")
    print(f"📦 مجلد البلجنز : {plugins_path}")
    print("──────────────────────────────────────")

    # 5) إبقاء البوت قيد التشغيل
    await idle()

    await app.stop()
    print("🛑 تم إيقاف البوت.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 تم الإيقاف يدويًا.")
