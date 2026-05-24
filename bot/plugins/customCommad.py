"""
plugins/customCommad.py
========================
- إعادة تسمية أوامر البوت (Aliases)  :
    • تغيير امر <الأمر الأصلي> الى <الاسم الجديد>
    • اضف امر <الاسم الجديد> + <الأمر الأصلي>
- عرض القائمة                          :  الاوامر المضافه
- حذف بديل                              :  حذف امر <الاسم الجديد>
- نظام قفل الأوامر                      :
    • قفل امر <الأمر>
    • فتح امر <الأمر>
    • الاوامر المقفله
    • فتح كل الاوامر
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks


# ====== مفاتيح Redis ======
def _alias_key(chat_id):  return f"cmd_alias:{chat_id}"   # hash : alias -> original
def _lock_key(chat_id):   return f"cmd_lock:{chat_id}"    # set  : locked commands


# ============================================================
# 0) Middleware  (الأولوية الأعلى) : قفل + Alias
# ============================================================
@Client.on_message(filters.group & filters.text, group=-3)
async def commands_middleware(client: Client, message: Message):
    if not message.text:
        return

    rds = client.redis
    chat_id = message.chat.id
    text = message.text.strip()
    user_id = message.from_user.id if message.from_user else None

    # 1) القفل: إن كان النص أمراً مقفلاً وليس المرسل أدمن+ فأوقف المعالجة
    if rds.sismember(_lock_key(chat_id), text):
        if not user_id or not Ranks.admin_pls(rds, user_id, chat_id):
            await message.stop_propagation()
            return

    # 2) Alias: إن كان النص اسماً بديلاً، نستبدله بالأمر الأصلي
    original = rds.hget(_alias_key(chat_id), text)
    if original:
        try:
            message.text = original
        except Exception:
            pass


# ============================================================
# 1) تغيير امر <original> الى <new>
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^تغيير\s+امر\s+([\s\S]+?)\s+الى\s+([\s\S]+)$"))
async def rename_command(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    original = message.matches[0].group(1).strip()
    new_name = message.matches[0].group(2).strip()

    if original == new_name:
        await message.reply_text("⚠️ الاسم الجديد مطابق للأصلي.")
        return

    rds.hset(_alias_key(chat_id), new_name, original)
    await message.reply_text(
        f"✅ الآن <b>{new_name}</b> يعمل كأمر بديل لـ <b>{original}</b>.",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 2) اضف امر <new> + <original>
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^اضف\s+امر\s+([\s\S]+?)\s*[+=]\s*([\s\S]+)$"))
async def add_alias(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    new_name = message.matches[0].group(1).strip()
    original = message.matches[0].group(2).strip()

    if not new_name or not original or new_name == original:
        await message.reply_text("⚠️ صيغة خاطئة. الصحيح:\n<code>اضف امر اسم_جديد + اسم_الأمر_الأصلي</code>", parse_mode=ParseMode.HTML)
        return

    rds.hset(_alias_key(chat_id), new_name, original)
    await message.reply_text(
        f"✅ تم إضافة بديل: <b>{new_name}</b> → <b>{original}</b>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 3) حذف امر <new_name>
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^حذف\s+امر\s+([\s\S]+)$"))
async def del_alias(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    new_name = message.matches[0].group(1).strip()
    if not rds.hexists(_alias_key(chat_id), new_name):
        await message.reply_text("ℹ️ لا يوجد بديل بهذا الاسم.")
        return

    rds.hdel(_alias_key(chat_id), new_name)
    await message.reply_text(f"🗑 تم حذف البديل : <b>{new_name}</b>", parse_mode=ParseMode.HTML)


# ============================================================
# 4) الاوامر المضافه
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^الاوامر\s+المضافه$"))
async def list_aliases(client: Client, message: Message):
    rds = client.redis
    aliases = rds.hgetall(_alias_key(message.chat.id)) or {}

    if not aliases:
        await message.reply_text("📭 لا توجد أوامر مخصصة في هذه المجموعة.")
        return

    lines = ["📋 <b>الأوامر المخصصة:</b>\n"]
    for new_name, original in aliases.items():
        lines.append(f"• <b>{new_name}</b>  →  <code>{original}</code>")
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ============================================================
# 5) قفل امر <command>
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^قفل\s+امر\s+([\s\S]+)$"))
async def lock_command(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    cmd = message.matches[0].group(1).strip()
    rds.sadd(_lock_key(chat_id), cmd)
    await message.reply_text(f"🔒 تم قفل الأمر : <b>{cmd}</b>", parse_mode=ParseMode.HTML)


# ============================================================
# 6) فتح امر <command>
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^فتح\s+امر\s+([\s\S]+)$"))
async def unlock_command(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    cmd = message.matches[0].group(1).strip()
    if not rds.sismember(_lock_key(chat_id), cmd):
        await message.reply_text("ℹ️ هذا الأمر غير مقفل.")
        return

    rds.srem(_lock_key(chat_id), cmd)
    await message.reply_text(f"🔓 تم فتح الأمر : <b>{cmd}</b>", parse_mode=ParseMode.HTML)


# ============================================================
# 7) الاوامر المقفله
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^الاوامر\s+المقفله$"))
async def list_locked(client: Client, message: Message):
    rds = client.redis
    locked = rds.smembers(_lock_key(message.chat.id)) or set()
    if not locked:
        await message.reply_text("📭 لا توجد أوامر مقفلة.")
        return

    lines = ["🔒 <b>الأوامر المقفلة:</b>\n"]
    for c in sorted(locked):
        lines.append(f"• <code>{c}</code>")
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ============================================================
# 8) فتح كل الاوامر
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^فتح\s+كل\s+الاوامر$"))
async def unlock_all(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    rds.delete(_lock_key(chat_id))
    await message.reply_text("🔓 تم فتح جميع الأوامر.")
