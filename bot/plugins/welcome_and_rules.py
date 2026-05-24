"""
plugins/welcome_and_rules.py
=============================
- وضع / مسح / عرض رسالة الترحيب
- وضع / مسح / عرض القوانين
- رسالة ترحيب تلقائية عند دخول عضو جديد (مخصصة أو افتراضية)
"""

import random

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks
from helpers.utils import mention


# ====== مفاتيح Redis ======
def _welcome_key(chat_id):
    return f"welcome:{chat_id}"


def _rules_key(chat_id):
    return f"rules:{chat_id}"


# ====== رسائل ترحيب افتراضية ======
DEFAULT_WELCOME = [
    "🌹 أهلاً وسهلاً بك {user} في {chat}",
    "👋 يا هلا والله بـ {user} ، نوّرت {chat}",
    "✨ منوّرنا يا {user} في {chat}",
]


def render_welcome(template: str, user, chat) -> str:
    """تعويض المتغيرات في قالب الترحيب"""
    return (
        template
        .replace("{user}", mention(user))
        .replace("{name}", user.first_name or "صديقي")
        .replace("{id}", str(user.id))
        .replace("{username}", f"@{user.username}" if user.username else "—")
        .replace("{chat}", chat.title or "المجموعة")
        .replace("{count}", str(getattr(chat, "members_count", "?")))
    )


# =====================================================
# 1) وضع الترحيب
# =====================================================
@Client.on_message(filters.group & filters.regex(r"^وضع\s+الترحيب(?:\s+([\s\S]+))?$"))
async def set_welcome(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    text = (message.matches[0].group(1) or "").strip()

    # إن لم يكتب نصاً، خذ النص من الرد
    if not text and message.reply_to_message and message.reply_to_message.text:
        text = message.reply_to_message.text.strip()

    if not text:
        await message.reply_text(
            "⚠️ اكتب نص الترحيب بعد الأمر أو رد على رسالة.\n\n"
            "<b>المتغيرات المتاحة:</b>\n"
            "<code>{user}</code> - منشن العضو\n"
            "<code>{name}</code> - اسم العضو\n"
            "<code>{id}</code> - ايدي العضو\n"
            "<code>{username}</code> - يوزر العضو\n"
            "<code>{chat}</code> - اسم المجموعة\n"
            "<code>{count}</code> - عدد الأعضاء",
            parse_mode=ParseMode.HTML,
        )
        return

    rds.set(_welcome_key(chat_id), text)
    await message.reply_text("✅ تم حفظ رسالة الترحيب بنجاح.")


# =====================================================
# 2) مسح الترحيب
# =====================================================
@Client.on_message(filters.group & filters.regex(r"^مسح\s+الترحيب$"))
async def clear_welcome(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    if not rds.exists(_welcome_key(chat_id)):
        await message.reply_text("ℹ️ لا يوجد ترحيب مخصص لحذفه.")
        return

    rds.delete(_welcome_key(chat_id))
    await message.reply_text("🗑 تم مسح رسالة الترحيب المخصصة (سيُستخدم الترحيب الافتراضي).")


# =====================================================
# 3) عرض الترحيب
# =====================================================
@Client.on_message(filters.group & filters.regex(r"^الترحيب$"))
async def show_welcome(client: Client, message: Message):
    rds = client.redis
    chat_id = message.chat.id

    template = rds.get(_welcome_key(chat_id))
    if not template:
        await message.reply_text(
            "ℹ️ لا يوجد ترحيب مخصص — يُستخدم الترحيب الافتراضي.\n\n"
            "لإضافة ترحيب جديد :\n<code>وضع الترحيب نص الترحيب هنا</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    # اعرض نموذجاً مُحاكياً
    preview = render_welcome(template, message.from_user, message.chat)
    await message.reply_text(
        f"📋 <b>الترحيب الحالي:</b>\n\n{preview}",
        parse_mode=ParseMode.HTML,
    )


# =====================================================
# 4) وضع القوانين
# =====================================================
@Client.on_message(filters.group & filters.regex(r"^(?:وضع\s+قوانين|وضع\s+القوانين)(?:\s+([\s\S]+))?$"))
async def set_rules(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    text = (message.matches[0].group(1) or "").strip()
    if not text and message.reply_to_message and message.reply_to_message.text:
        text = message.reply_to_message.text.strip()

    if not text:
        await message.reply_text("⚠️ اكتب القوانين بعد الأمر أو رد على رسالة.")
        return

    rds.set(_rules_key(chat_id), text)
    await message.reply_text("✅ تم حفظ القوانين بنجاح.")


# =====================================================
# 5) مسح القوانين
# =====================================================
@Client.on_message(filters.group & filters.regex(r"^مسح\s+القوانين$"))
async def clear_rules(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    if not rds.exists(_rules_key(chat_id)):
        await message.reply_text("ℹ️ لا توجد قوانين لحذفها.")
        return

    rds.delete(_rules_key(chat_id))
    await message.reply_text("🗑 تم مسح القوانين.")


# =====================================================
# 6) عرض القوانين
# =====================================================
@Client.on_message(filters.group & filters.regex(r"^(القوانين|قوانين)$"))
async def show_rules(client: Client, message: Message):
    rds = client.redis
    chat_id = message.chat.id

    text = rds.get(_rules_key(chat_id))
    if not text:
        await message.reply_text("📭 لم يتم وضع قوانين لهذه المجموعة بعد.")
        return

    await message.reply_text(
        f"📜 <b>قوانين المجموعة:</b>\n\n{text}",
        parse_mode=ParseMode.HTML,
    )


# =====================================================
# 7) الترحيب التلقائي للأعضاء الجدد
# =====================================================
@Client.on_message(filters.new_chat_members)
async def on_new_members(client: Client, message: Message):
    # نتحقق من حالة البوت داخل المجموعة
    rds = client.redis
    enabled_key = f"bot:enabled:{message.chat.id}"
    val = rds.get(enabled_key)
    if val == "0":
        return  # البوت معطّل

    me = await client.get_me()
    template = rds.get(_welcome_key(message.chat.id))

    for member in message.new_chat_members:
        if member.id == me.id:
            await message.reply_text(
                "🎉 شكراً لإضافتي إلى المجموعة!\n"
                "اكتب <b>تفعيل البوت</b> للبدء.",
                parse_mode=ParseMode.HTML,
            )
            continue
        if member.is_bot:
            continue

        if template:
            text = render_welcome(template, member, message.chat)
        else:
            text = render_welcome(random.choice(DEFAULT_WELCOME), member, message.chat)

        await message.reply_text(text, parse_mode=ParseMode.HTML)
