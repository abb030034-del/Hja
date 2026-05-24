"""
plugins/id.py
==============
أوامر استعلام الـ ID والمعلومات السريعة.

- ID / id / ايدي     — ايديك أو ايدي من ردّيت عليه
- ايدي المجموعه       — ايدي المجموعة الحالية
- ايدي القناه (بالرد على رسالة موجّهة من قناة) — ايدي القناة
- يوزر               — يوزرنيمك (أو من ردّيت عليه)
- ايدي بالرد           — مثل ID لكن صريح بالرد
- معرف <يوزر>          — حلّ يوزر إلى ايدي
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers.utils import mention


# ============ ID / id / ايدي ============
@Client.on_message(filters.regex(r"^(ID|id|الايدي|ايدي|ايديي)$"))
async def get_id(client, message: Message):
    target = (
        message.reply_to_message.from_user
        if (message.reply_to_message and message.reply_to_message.from_user)
        else message.from_user
    )
    if not target:
        return
    text = (
        f"👤 <b>المعرّف</b>\n"
        f"━━━━━━━━━━━━\n"
        f"• الاسم : {mention(target)}\n"
        f"• الايدي : <code>{target.id}</code>\n"
        f"• اليوزر : {'@' + target.username if target.username else '—'}\n"
        f"━━━━━━━━━━━━"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML)


# ============ ايدي المجموعه ============
@Client.on_message(filters.group & filters.regex(r"^ايدي\s+المجموعه|^ايدي\s+المجموعة$"))
async def group_id(client, message: Message):
    await message.reply_text(
        f"💬 ايدي المجموعة : <code>{message.chat.id}</code>",
        parse_mode=ParseMode.HTML,
    )


# ============ ايدي القناه (بالرد على رسالة موجّهة من قناة) ============
@Client.on_message(filters.regex(r"^ايدي\s+القناه|^ايدي\s+القناة$") & filters.reply)
async def channel_id(client, message: Message):
    src = message.reply_to_message
    if src.forward_from_chat:
        ch = src.forward_from_chat
        await message.reply_text(
            f"📺 <b>القناة:</b>\n"
            f"• الاسم : {ch.title}\n"
            f"• الايدي : <code>{ch.id}</code>\n"
            f"• اليوزر : {'@' + ch.username if ch.username else '—'}",
            parse_mode=ParseMode.HTML,
        )
    elif src.sender_chat:
        await message.reply_text(
            f"📺 ايدي القناة : <code>{src.sender_chat.id}</code>\n"
            f"الاسم : {src.sender_chat.title or '—'}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.reply_text("⚠️ لا يبدو أن الرسالة من قناة.")


# ============ يوزر ============
@Client.on_message(filters.regex(r"^يوزر$"))
async def get_username(client, message: Message):
    target = (
        message.reply_to_message.from_user
        if (message.reply_to_message and message.reply_to_message.from_user)
        else message.from_user
    )
    if not target:
        return
    if target.username:
        await message.reply_text(f"🔗 @{target.username}")
    else:
        await message.reply_text(f"ℹ️ {mention(target)} ليس لديه يوزرنيم.", parse_mode=ParseMode.HTML)


# ============ معرف <يوزر> ============
@Client.on_message(filters.regex(r"^معرف\s+(@?\w+)$"))
async def resolve_username(client, message: Message):
    uname = message.matches[0].group(1)
    if not uname.startswith("@"):
        uname = "@" + uname
    try:
        u = await client.get_users(uname)
        await message.reply_text(
            f"👤 {mention(u)}\n"
            f"• الايدي : <code>{u.id}</code>\n"
            f"• اليوزر : @{u.username or '—'}",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply_text(f"⚠️ تعذّر العثور على المستخدم : {e}")
