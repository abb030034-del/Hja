"""
plugins/sarhni.py
==================
صارحني — رسائل مجهولة عبر الخاص.

طريقة الاستخدام :
  • تفعيل صارحني  / تعطيل صارحني        (يفعّل العضو الميزة لشخصه)
  • صارحني (بالرد على عضو في مجموعة)    -> ينشئ رابطاً للعضو
  • اضغط الرابط -> راسل البوت في الخاص   -> البوت يحوّل الرسالة مجهولة لذلك العضو
"""

import secrets

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import config
from helpers.utils import mention


# Redis keys
def _enabled_key(uid):  return f"sarhni:enabled:{uid}"   # "1"/"0"
def _token_key(token):  return f"sarhni:token:{token}"   # -> uid
def _pending_key(sender_id): return f"sarhni:pending:{sender_id}"  # -> uid


def is_enabled(rds, uid):
    return rds.get(_enabled_key(uid)) == "1"


# تفعيل / تعطيل
@Client.on_message(filters.regex(r"^تفعيل\s+صارحني$"))
async def enable_sarhni(client, message):
    rds = client.redis
    if not message.from_user: return
    rds.set(_enabled_key(message.from_user.id), "1")
    await message.reply_text("✅ تم تفعيل صارحني لك. يمكن للآخرين الآن إرسال رسائل مجهولة إليك.")


@Client.on_message(filters.regex(r"^تعطيل\s+صارحني$"))
async def disable_sarhni(client, message):
    rds = client.redis
    if not message.from_user: return
    rds.set(_enabled_key(message.from_user.id), "0")
    await message.reply_text("🔕 تم تعطيل صارحني لك.")


# صارحني (بالرد) في مجموعة
@Client.on_message(filters.group & filters.regex(r"^صارحني$") & filters.reply)
async def make_sarhni_link(client, message: Message):
    rds = client.redis
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target:
        return
    if target.is_bot:
        await message.reply_text("⚠️ لا يمكن مصارحة بوت.")
        return
    if not is_enabled(rds, target.id):
        await message.reply_text(f"⚠️ {mention(target)} لم يفعّل صارحني.\nليفعّلها يكتب: <code>تفعيل صارحني</code>", parse_mode=ParseMode.HTML)
        return

    # token قصير لاستخدام start parameter
    token = secrets.token_urlsafe(8)
    rds.set(_token_key(token), str(target.id), ex=86400)  # 24h

    bot_uname = config.botUsername or "this_bot"
    link = f"https://t.me/{bot_uname}?start=sarhni_{token}"

    await message.reply_text(
        f"💌 لمصارحة {mention(target)} اضغط الزر:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✉️ صارحه/ها", url=link)
        ]]),
    )


# /start sarhni_<token>
@Client.on_message(filters.private & filters.command("start"))
async def sarhni_start(client, message: Message):
    rds = client.redis
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].startswith("sarhni_"):
        return  # خلي /start الافتراضي يشتغل في مكان آخر

    token = parts[1][len("sarhni_"):]
    target_id = rds.get(_token_key(token))
    if not target_id:
        await message.reply_text("⚠️ هذا الرابط غير صالح أو منتهي.")
        return

    rds.set(_pending_key(message.from_user.id), target_id, ex=600)  # 10 دقائق لإرسال الرسالة
    await message.reply_text(
        "💬 أرسل الآن رسالتك (نص أو صورة...) وسيتم تحويلها مجهولة الهوية للشخص.",
    )


# استلام الرسالة المجهولة في الخاص
@Client.on_message(filters.private & ~filters.command("start"))
async def receive_sarhni(client, message: Message):
    rds = client.redis
    uid = message.from_user.id
    target = rds.get(_pending_key(uid))
    if not target:
        return  # ليست رسالة صارحني

    rds.delete(_pending_key(uid))
    try:
        # ابعث الرسالة بدون الكشف عن المرسل
        await message.copy(int(target), caption=None)
        # رسالة عنوان
        await client.send_message(
            int(target),
            "💌 لقد وصلتك رسالة مجهولة عبر <b>صارحني</b>",
            parse_mode=ParseMode.HTML,
        )
        await message.reply_text("✅ تم إرسال رسالتك مجهولة الهوية.")
    except Exception as e:
        await message.reply_text(f"⚠️ فشل الإرسال : {e}")
