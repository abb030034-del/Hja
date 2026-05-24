"""
plugins/globalFilters.py
=========================
- اضف / مسح رد عام            (مطور / مساعد)
- الردود العامه / مسح الردود العامه
- اضف / مسح رد متعدد عام     (نفس الكلمة = عدة ردود يُختار عشوائياً)
- تفعيل / تعطيل ردود المطور  (سويتش على كل الردود العامة)
"""

import random

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks
from helpers import payload as P


# ====== مفاتيح Redis ======
GLOBAL_KEY = "filter:global"                 # hash : kw -> payload
GLOBAL_MULTI_KEY = "filter:global_multi"     # key prefix : filter:global_multi:{kw} -> list[payload]
DEV_ENABLED_KEY = "filter:dev_enabled"       # "1" / "0"  (default "1")


def is_dev_filters_enabled(rds) -> bool:
    return rds.get(DEV_ENABLED_KEY) != "0"


def _multi_key(keyword):
    return f"{GLOBAL_MULTI_KEY}:{keyword}"


# ============================================================
# 1) اضف رد عام
# ============================================================
@Client.on_message(filters.regex(r"^اضف\s+رد\s+عام\s+([\s\S]+)$"))
async def add_global(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not Ranks.devp_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر للمطور أو المطور المساعد فقط.")
        return

    keyword = message.matches[0].group(1).strip()
    pl = P.extract_payload(message)
    if not pl:
        await message.reply_text("⚠️ يجب الرد على رسالة لحفظها كرد عام.")
        return

    rds.hset(GLOBAL_KEY, keyword, P.dumps(pl))
    await message.reply_text(f"🌐 تم إضافة رد عام على : <b>{keyword}</b>", parse_mode=ParseMode.HTML)


# ============================================================
# 2) مسح رد عام
# ============================================================
@Client.on_message(filters.regex(r"^مسح\s+رد\s+عام\s+([\s\S]+)$"))
async def del_global(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not Ranks.devp_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر للمطور أو المطور المساعد فقط.")
        return

    keyword = message.matches[0].group(1).strip()
    if not rds.hexists(GLOBAL_KEY, keyword):
        await message.reply_text("ℹ️ هذا الرد غير موجود.")
        return

    rds.hdel(GLOBAL_KEY, keyword)
    await message.reply_text(f"🗑 تم حذف الرد العام : <b>{keyword}</b>", parse_mode=ParseMode.HTML)


# ============================================================
# 3) الردود العامه
# ============================================================
@Client.on_message(filters.regex(r"^الردود\s+العامه$"))
async def list_global(client: Client, message: Message):
    rds = client.redis
    kws = list(rds.hkeys(GLOBAL_KEY) or [])

    # أضف كلمات الردود المتعددة أيضاً
    multi_kws = []
    for key in rds.scan_iter(f"{GLOBAL_MULTI_KEY}:*"):
        multi_kws.append(key.split(":", 2)[-1])

    if not kws and not multi_kws:
        await message.reply_text("📭 لا توجد ردود عامة.")
        return

    lines = ["🌐 <b>الردود العامة:</b>"]
    if kws:
        lines.append("\n<u>عادية:</u>")
        lines += [f"• <code>{k}</code>" for k in kws]
    if multi_kws:
        lines.append("\n<u>متعددة:</u>")
        lines += [f"• <code>{k}</code>  ({rds.llen(_multi_key(k))})" for k in multi_kws]

    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ============================================================
# 4) مسح الردود العامه
# ============================================================
@Client.on_message(filters.regex(r"^مسح\s+الردود\s+العامه$"))
async def clear_global(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not Ranks.is_dev(user_id):
        await message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return

    rds.delete(GLOBAL_KEY)
    deleted = 0
    for key in rds.scan_iter(f"{GLOBAL_MULTI_KEY}:*"):
        rds.delete(key)
        deleted += 1
    await message.reply_text(f"🗑 تم حذف جميع الردود العامة ({deleted + 1} مجموعة).")


# ============================================================
# 5) اضف رد متعدد عام
# ============================================================
@Client.on_message(filters.regex(r"^اضف\s+رد\s+متعدد\s+عام\s+([\s\S]+)$"))
async def add_global_multi(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not Ranks.devp_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر للمطور أو المطور المساعد فقط.")
        return

    keyword = message.matches[0].group(1).strip()
    pl = P.extract_payload(message)
    if not pl:
        await message.reply_text("⚠️ يجب الرد على رسالة لحفظها كرد متعدد.")
        return

    rds.rpush(_multi_key(keyword), P.dumps(pl))
    count = rds.llen(_multi_key(keyword))
    await message.reply_text(
        f"🌐➕ تم إضافة رد متعدد على : <b>{keyword}</b>  (عدد الردود: {count})",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 6) مسح رد متعدد عام  (يحذف كل الردود لتلك الكلمة)
# ============================================================
@Client.on_message(filters.regex(r"^مسح\s+رد\s+متعدد\s+عام\s+([\s\S]+)$"))
async def del_global_multi(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not Ranks.devp_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر للمطور أو المطور المساعد فقط.")
        return

    keyword = message.matches[0].group(1).strip()
    key = _multi_key(keyword)
    if not rds.exists(key):
        await message.reply_text("ℹ️ لا يوجد رد متعدد بهذه الكلمة.")
        return

    rds.delete(key)
    await message.reply_text(f"🗑 تم حذف الرد المتعدد : <b>{keyword}</b>", parse_mode=ParseMode.HTML)


# ============================================================
# 7) تفعيل / تعطيل ردود المطور
# ============================================================
@Client.on_message(filters.regex(r"^(تفعيل|تعطيل)\s+ردود\s+المطور$"))
async def toggle_dev_filters(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not Ranks.is_dev(user_id):
        await message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return

    if message.matches[0].group(1) == "تفعيل":
        rds.set(DEV_ENABLED_KEY, "1")
        await message.reply_text("✅ تم تفعيل ردود المطور (عامّاً).")
    else:
        rds.set(DEV_ENABLED_KEY, "0")
        await message.reply_text("🔕 تم تعطيل ردود المطور (عامّاً).")


# ============================================================
# 8) محرّك الردود العامة
# ============================================================
@Client.on_message(filters.text & ~filters.via_bot)
async def global_filter_engine(client: Client, message: Message):
    if not message.text or not message.from_user:
        return

    rds = client.redis
    if not is_dev_filters_enabled(rds):
        return

    text = message.text.strip()

    # 1) رد عام مفرد
    raw = rds.hget(GLOBAL_KEY, text)
    if raw:
        pl = P.loads(raw)
        if pl:
            await P.send_payload(client, message.chat.id, pl, reply_to_message_id=message.id)
            return

    # 2) رد عام متعدد (اختيار عشوائي)
    key = _multi_key(text)
    if rds.exists(key):
        items = rds.lrange(key, 0, -1)
        if items:
            pl = P.loads(random.choice(items))
            if pl:
                await P.send_payload(client, message.chat.id, pl, reply_to_message_id=message.id)
                return
