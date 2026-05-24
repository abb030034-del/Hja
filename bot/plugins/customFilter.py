"""
plugins/customFilter.py
========================
ردود خاصة بالمجموعات :
- ردود المجموعة (للجميع داخل المجموعة) : اضف رد / مسح رد / الردود / مسح الردود / تفعيل-تعطيل الردود
- ردود الأعضاء (شخصية)               : اضف ردي / مسح ردي / ردود الاعضاء / تفعيل-تعطيل ردود الاعضاء
- الردود المميزة                       : اضف رد مميز / مسح رد مميز / الردود المميزه
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks
from helpers import payload as P


# ============== مفاتيح Redis ==============
def _group_key(chat_id):           return f"filter:group:{chat_id}"          # hash kw->payload
def _member_key(chat_id, user_id): return f"filter:member:{chat_id}:{user_id}"
def _special_key(chat_id):         return f"filter:special:{chat_id}"
def _group_enabled(chat_id):       return f"filter:enabled:group:{chat_id}"
def _member_enabled(chat_id):      return f"filter:enabled:member:{chat_id}"


def is_group_enabled(rds, chat_id) -> bool:
    return rds.get(_group_enabled(chat_id)) != "0"  # افتراضياً مفعّل


def is_member_enabled(rds, chat_id) -> bool:
    return rds.get(_member_enabled(chat_id)) != "0"


# ============================================================
# 1) ردود المجموعة
# ============================================================

# اضف رد <كلمة>  (مع الرد على رسالة المحتوى)
@Client.on_message(filters.group & filters.regex(r"^اضف\s+رد\s+([\s\S]+)$"))
async def add_group_filter(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    keyword = message.matches[0].group(1).strip()
    if not keyword:
        await message.reply_text("⚠️ اكتب الكلمة بعد الأمر.")
        return

    pl = P.extract_payload(message)
    if not pl:
        await message.reply_text("⚠️ يجب الرد على رسالة (نص/صورة/فيديو/ملصق...) ليتم حفظها كرد.")
        return

    rds.hset(_group_key(chat_id), keyword, P.dumps(pl))
    await message.reply_text(f"✅ تم إضافة رد المجموعة على : <b>{keyword}</b>", parse_mode=ParseMode.HTML)


# مسح رد <كلمة>
@Client.on_message(filters.group & filters.regex(r"^مسح\s+رد\s+([\s\S]+)$"))
async def del_group_filter(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    keyword = message.matches[0].group(1).strip()
    if not rds.hexists(_group_key(chat_id), keyword):
        await message.reply_text("ℹ️ هذا الرد غير موجود.")
        return

    rds.hdel(_group_key(chat_id), keyword)
    await message.reply_text(f"🗑 تم حذف رد المجموعة على : <b>{keyword}</b>", parse_mode=ParseMode.HTML)


# الردود
@Client.on_message(filters.group & filters.regex(r"^الردود$"))
async def list_group_filters(client: Client, message: Message):
    rds = client.redis
    kws = list(rds.hkeys(_group_key(message.chat.id)) or [])
    if not kws:
        await message.reply_text("📭 لا توجد ردود محفوظة في هذه المجموعة.")
        return
    text = "📋 <b>ردود المجموعة:</b>\n\n" + "\n".join(f"• <code>{k}</code>" for k in kws)
    await message.reply_text(text, parse_mode=ParseMode.HTML)


# مسح الردود
@Client.on_message(filters.group & filters.regex(r"^مسح\s+الردود$"))
async def clear_group_filters(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return
    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return
    rds.delete(_group_key(chat_id))
    await message.reply_text("🗑 تم حذف جميع ردود المجموعة.")


# تفعيل / تعطيل الردود
@Client.on_message(filters.group & filters.regex(r"^(تفعيل|تعطيل)\s+الردود$"))
async def toggle_group_filters(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return
    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    if message.matches[0].group(1) == "تفعيل":
        rds.set(_group_enabled(chat_id), "1")
        await message.reply_text("✅ تم تفعيل ردود المجموعة.")
    else:
        rds.set(_group_enabled(chat_id), "0")
        await message.reply_text("🔕 تم تعطيل ردود المجموعة.")


# ============================================================
# 2) ردود الأعضاء (شخصية)
# ============================================================

# اضف ردي <كلمة>
@Client.on_message(filters.group & filters.regex(r"^اضف\s+ردي\s+([\s\S]+)$"))
async def add_member_filter(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    keyword = message.matches[0].group(1).strip()
    pl = P.extract_payload(message)
    if not pl:
        await message.reply_text("⚠️ يجب الرد على رسالة ليتم حفظها كرد شخصي.")
        return

    rds.hset(_member_key(chat_id, user_id), keyword, P.dumps(pl))
    await message.reply_text(f"✅ تم حفظ ردك الشخصي على : <b>{keyword}</b>", parse_mode=ParseMode.HTML)


# مسح ردي <كلمة>
@Client.on_message(filters.group & filters.regex(r"^مسح\s+ردي\s+([\s\S]+)$"))
async def del_member_filter(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    keyword = message.matches[0].group(1).strip()
    if not rds.hexists(_member_key(chat_id, user_id), keyword):
        await message.reply_text("ℹ️ ليس لديك رد بهذه الكلمة.")
        return

    rds.hdel(_member_key(chat_id, user_id), keyword)
    await message.reply_text(f"🗑 تم حذف ردك على : <b>{keyword}</b>", parse_mode=ParseMode.HTML)


# ردود الاعضاء  (للجميع: قائمة ردودي)
@Client.on_message(filters.group & filters.regex(r"^ردود\s+الاعضاء$"))
async def list_member_filters(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    kws = list(rds.hkeys(_member_key(chat_id, user_id)) or [])
    if not kws:
        await message.reply_text("📭 ليس لديك أي ردود شخصية في هذه المجموعة.")
        return
    text = "📋 <b>ردودك الشخصية:</b>\n\n" + "\n".join(f"• <code>{k}</code>" for k in kws)
    await message.reply_text(text, parse_mode=ParseMode.HTML)


# تفعيل / تعطيل ردود الاعضاء
@Client.on_message(filters.group & filters.regex(r"^(تفعيل|تعطيل)\s+ردود\s+الاعضاء$"))
async def toggle_member_filters(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return
    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    if message.matches[0].group(1) == "تفعيل":
        rds.set(_member_enabled(chat_id), "1")
        await message.reply_text("✅ تم تفعيل ردود الأعضاء.")
    else:
        rds.set(_member_enabled(chat_id), "0")
        await message.reply_text("🔕 تم تعطيل ردود الأعضاء.")


# ============================================================
# 3) الردود المميزة
# ============================================================

# اضف رد مميز <كلمة>
@Client.on_message(filters.group & filters.regex(r"^اضف\s+رد\s+مميز\s+([\s\S]+)$"))
async def add_special_filter(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return
    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    keyword = message.matches[0].group(1).strip()
    pl = P.extract_payload(message)
    if not pl:
        await message.reply_text("⚠️ يجب الرد على رسالة لحفظها كرد مميز.")
        return

    rds.hset(_special_key(chat_id), keyword, P.dumps(pl))
    await message.reply_text(f"⭐ تم إضافة رد مميز على : <b>{keyword}</b>", parse_mode=ParseMode.HTML)


# مسح رد مميز <كلمة>
@Client.on_message(filters.group & filters.regex(r"^مسح\s+رد\s+مميز\s+([\s\S]+)$"))
async def del_special_filter(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return
    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    keyword = message.matches[0].group(1).strip()
    if not rds.hexists(_special_key(chat_id), keyword):
        await message.reply_text("ℹ️ هذا الرد غير موجود.")
        return

    rds.hdel(_special_key(chat_id), keyword)
    await message.reply_text(f"🗑 تم حذف الرد المميز : <b>{keyword}</b>", parse_mode=ParseMode.HTML)


# الردود المميزه
@Client.on_message(filters.group & filters.regex(r"^الردود\s+المميزه$"))
async def list_special_filters(client: Client, message: Message):
    rds = client.redis
    kws = list(rds.hkeys(_special_key(message.chat.id)) or [])
    if not kws:
        await message.reply_text("📭 لا توجد ردود مميزة.")
        return
    text = "⭐ <b>الردود المميزة:</b>\n\n" + "\n".join(f"• <code>{k}</code>" for k in kws)
    await message.reply_text(text, parse_mode=ParseMode.HTML)


# ============================================================
# 4) محرّك الردود : يتحقق من أي رسالة ويردّ إن كانت مطابقة
# ============================================================
@Client.on_message(filters.group & filters.text & ~filters.via_bot)
async def filter_engine(client: Client, message: Message):
    if not message.from_user or not message.text:
        return

    rds = client.redis
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip()

    # 1) رد شخصي للعضو
    if is_member_enabled(rds, chat_id):
        raw = rds.hget(_member_key(chat_id, user_id), text)
        if raw:
            pl = P.loads(raw)
            if pl:
                await P.send_payload(client, chat_id, pl, reply_to_message_id=message.id)
                return

    # 2) رد مميز
    raw = rds.hget(_special_key(chat_id), text)
    if raw:
        pl = P.loads(raw)
        if pl:
            await P.send_payload(client, chat_id, pl, reply_to_message_id=message.id)
            return

    # 3) رد مجموعة
    if is_group_enabled(rds, chat_id):
        raw = rds.hget(_group_key(chat_id), text)
        if raw:
            pl = P.loads(raw)
            if pl:
                await P.send_payload(client, chat_id, pl, reply_to_message_id=message.id)
                return
