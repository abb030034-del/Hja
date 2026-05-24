"""
plugins/whisper.py
====================
وسمسة — رسائل سرية بين الأعضاء في المجموعات .

الاستخدام (داخل مجموعة):
  • وسمسة <نص> (بالرد على عضو)
  -> ينشر البوت رسالة تحتوي زر "اقرأ" — فقط ذلك العضو (والمرسل) يستطيع القراءة عبر CallbackQuery.
"""

import secrets

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from helpers.utils import mention


def _whisper_key(token): return f"whisper:{token}"


@Client.on_message(filters.group & filters.regex(r"^وسمسة\s+([\s\S]+)$") & filters.reply)
async def make_whisper(client, message: Message):
    rds = client.redis
    sender = message.from_user
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not sender or not target:
        return
    if target.is_bot:
        await message.reply_text("⚠️ لا يمكن إرسال وسمسة لبوت.")
        return

    text = message.matches[0].group(1).strip()
    if not text:
        await message.reply_text("⚠️ اكتب نص الوسمسة.")
        return

    token = secrets.token_urlsafe(10)
    rds.hset(_whisper_key(token), mapping={
        "sender": sender.id,
        "target": target.id,
        "text": text,
    })
    rds.expire(_whisper_key(token), 86400)  # 24h

    await message.reply_text(
        f"🤫 وسمسة من {mention(sender)} إلى {mention(target)}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔓 اقرأ الوسمسة", callback_data=f"whisper:{token}")
        ]]),
    )
    try:
        await message.delete()
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^whisper:(.+)$"))
async def read_whisper(client, query: CallbackQuery):
    rds = client.redis
    token = query.matches[0].group(1)
    data = rds.hgetall(_whisper_key(token))
    if not data:
        await query.answer("⚠️ هذه الوسمسة انتهت أو غير موجودة.", show_alert=True)
        return

    sender_id = int(data.get("sender", 0))
    target_id = int(data.get("target", 0))
    text = data.get("text", "")

    if query.from_user.id not in (sender_id, target_id):
        await query.answer("🤫 هذه الوسمسة ليست لك.", show_alert=True)
        return

    await query.answer(text, show_alert=True)
