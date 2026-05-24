"""
plugins/replace.py
====================
استبدال كلمات في المجموعة.

  • استبدال <قديم> الى <جديد>     (مدير+)
  • استبدالات                       — قائمة
  • مسح استبدال <قديم>            (مدير+)
  • مسح الاستبدالات              (مدير+)

عندما يكتب أي عضو نصاً يحوي كلمة "قديم"، يستجيب البوت بنفس النص بعد استبدالها بـ "جديد".
"""

import re

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks


def _key(chat_id): return f"replace:{chat_id}"  # hash : old -> new


@Client.on_message(filters.group & filters.regex(r"^استبدال\s+([\s\S]+?)\s+الى\s+([\s\S]+)$"))
async def add_replace(client, message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id: return
    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return
    old = message.matches[0].group(1).strip()
    new = message.matches[0].group(2).strip()
    if not old or not new:
        return
    rds.hset(_key(chat_id), old, new)
    await message.reply_text(f"✅ تم تسجيل استبدال : <b>{old}</b> → <b>{new}</b>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.group & filters.regex(r"^استبدالات$"))
async def list_replaces(client, message):
    rds = client.redis
    data = rds.hgetall(_key(message.chat.id)) or {}
    if not data:
        await message.reply_text("📭 لا توجد استبدالات.")
        return
    lines = ["🔁 <b>الاستبدالات:</b>\n"]
    for old, new in data.items():
        lines.append(f"• <b>{old}</b> → <b>{new}</b>")
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


@Client.on_message(filters.group & filters.regex(r"^مسح\s+استبدال\s+([\s\S]+)$"))
async def del_replace(client, message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id: return
    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return
    old = message.matches[0].group(1).strip()
    if not rds.hexists(_key(chat_id), old):
        await message.reply_text("ℹ️ لا يوجد استبدال بهذا الاسم.")
        return
    rds.hdel(_key(chat_id), old)
    await message.reply_text(f"🗑 تم حذف الاستبدال : <b>{old}</b>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.group & filters.regex(r"^مسح\s+الاستبدالات$"))
async def clear_replaces(client, message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id: return
    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return
    rds.delete(_key(chat_id))
    await message.reply_text("🗑 تم حذف كل الاستبدالات.")


# محرّك الاستبدال
@Client.on_message(filters.group & filters.text & ~filters.via_bot, group=3)
async def replace_engine(client, message: Message):
    if not message.text or not message.from_user: return
    rds = client.redis
    data = rds.hgetall(_key(message.chat.id)) or {}
    if not data: return

    text = message.text
    new_text = text
    changed = False
    for old, new in data.items():
        if old in new_text:
            new_text = new_text.replace(old, new)
            changed = True

    if changed and new_text != text:
        await message.reply_text(f"🔁 {new_text}")
