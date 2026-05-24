"""
plugins/custom_plugin.py
=========================
بلاجن مخصص إضافي : أدوات سريعة ومفيدة .

الأوامر :
- بنق / ping            ← فحص استجابة البوت + زمن
- ايديي / الايدي         ← ايدي المرسل
- معلوماتي               ← معلوماتي
- معلومات   (مع الرد)    ← معلومات شخص آخر
- صورتي     (مع/بدون رد) ← إرسال صورة الملف الشخصي
- المجموعه               ← معلومات المجموعة الحالية
- الوقت / التاريخ         ← الوقت أو التاريخ الحالي
- عدد الاعضاء             ← إجمالي أعضاء المجموعة
- ام (مع الرد)            ← يكرر رسالة الرد كرسالة من البوت (مدير+)
- خروج                    ← يطرد البوت من جلسة المستخدم (للمطور فقط)
"""

import time
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

import config
from helpers import Ranks
from helpers.utils import mention


# ============================================================
# 1) بنق / ping
# ============================================================
@Client.on_message(filters.regex(r"^(بنق|ping|Ping|بنج)$"))
async def ping(client: Client, message: Message):
    t1 = time.monotonic()
    m = await message.reply_text("🏓 ...")
    t2 = time.monotonic()
    ms = int((t2 - t1) * 1000)
    await m.edit_text(f"🏓 <b>Pong!</b>\n⚡ {ms} ms", parse_mode=ParseMode.HTML)


# ============================================================
# 2) ايديي / الايدي
# ============================================================
@Client.on_message(filters.regex(r"^(ايديي|الايدي|ايدي|id|ID)$"))
async def my_id(client: Client, message: Message):
    user = message.from_user
    if not user:
        return
    await message.reply_text(
        f"🆔 ايديك : <code>{user.id}</code>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 3) معلوماتي
# ============================================================
@Client.on_message(filters.regex(r"^معلوماتي$"))
async def my_info(client: Client, message: Message):
    u = message.from_user
    if not u:
        return
    await _send_user_info(client, message, u)


# ============================================================
# 4) معلومات (مع الرد على عضو)
# ============================================================
@Client.on_message(filters.regex(r"^معلومات$") & filters.reply)
async def info_reply(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return
    await _send_user_info(client, message, message.reply_to_message.from_user)


async def _send_user_info(client, message, u):
    rds = client.redis
    name = u.first_name or "—"
    full = f"{name} {u.last_name}" if u.last_name else name
    uname = f"@{u.username}" if u.username else "—"
    is_bot = "نعم 🤖" if u.is_bot else "لا 👤"

    # الرتبة الإدارية (Ranks) إن وُجدت
    chat_id = message.chat.id if message.chat else None
    rank = Ranks.get_user_top_rank(rds, u.id, chat_id)
    rank_ar = Ranks.RANK_NAMES_AR.get(rank, "—") if rank else "—"

    # اللقب المخصص (من customRank)
    title = rds.hget(f"titles:{chat_id}", str(u.id)) if chat_id else None

    text = (
        f"👤 <b>معلومات العضو</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"• الاسم : {mention(u)}\n"
        f"• الاسم الكامل : <code>{full}</code>\n"
        f"• اليوزر : {uname}\n"
        f"• الايدي : <code>{u.id}</code>\n"
        f"• بوت ؟ : {is_bot}\n"
        f"• الرتبة : <b>{rank_ar}</b>\n"
        f"• اللقب : <b>{title or '—'}</b>\n"
        f"━━━━━━━━━━━━━━"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


# ============================================================
# 5) صورتي
# ============================================================
@Client.on_message(filters.regex(r"^صورتي$"))
async def my_photo(client: Client, message: Message):
    u = message.reply_to_message.from_user if (message.reply_to_message and message.reply_to_message.from_user) else message.from_user
    if not u:
        return

    photos = []
    async for p in client.get_chat_photos(u.id, limit=1):
        photos.append(p)

    if not photos:
        await message.reply_text("📭 لا توجد صورة شخصية.")
        return

    await client.send_photo(
        message.chat.id,
        photos[0].file_id,
        caption=f"📸 صورة {mention(u)}",
        parse_mode=ParseMode.HTML,
        reply_to_message_id=message.id,
    )


# ============================================================
# 6) المجموعه
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^(المجموعه|المجموعة)$"))
async def group_info(client: Client, message: Message):
    chat = message.chat
    try:
        full = await client.get_chat(chat.id)
        count = await client.get_chat_members_count(chat.id)
    except Exception:
        full = chat
        count = "?"

    uname = f"@{chat.username}" if chat.username else "—"
    title = chat.title or "—"
    desc = getattr(full, "description", None) or "—"

    text = (
        "💬 <b>معلومات المجموعة</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"• الاسم : <b>{title}</b>\n"
        f"• اليوزر : {uname}\n"
        f"• الايدي : <code>{chat.id}</code>\n"
        f"• الأعضاء : <code>{count}</code>\n"
        f"• الوصف : {desc}\n"
        "━━━━━━━━━━━━━━"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


# ============================================================
# 7) الوقت / التاريخ
# ============================================================
@Client.on_message(filters.regex(r"^(الوقت|الساعه|الساعة)$"))
async def now_time(client: Client, message: Message):
    now = datetime.now().strftime("%I:%M:%S %p")
    await message.reply_text(f"⏰ الوقت الآن : <b>{now}</b>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^التاريخ$"))
async def now_date(client: Client, message: Message):
    now = datetime.now().strftime("%Y-%m-%d  (%A)")
    await message.reply_text(f"📅 التاريخ : <b>{now}</b>", parse_mode=ParseMode.HTML)


# ============================================================
# 8) عدد الاعضاء
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^عدد\s+الاعضاء$"))
async def members_count(client: Client, message: Message):
    try:
        count = await client.get_chat_members_count(message.chat.id)
    except Exception:
        count = "?"
    await message.reply_text(f"👥 عدد الأعضاء : <code>{count}</code>", parse_mode=ParseMode.HTML)


# ============================================================
# 9) ام (يردد رسالة الرد كرسالة من البوت) - مدير+
# ============================================================
@Client.on_message(filters.regex(r"^ام$") & filters.reply)
async def echo_say(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    src = message.reply_to_message
    if not src:
        return

    try:
        await src.copy(chat_id)
        await message.delete()
    except Exception:
        pass


# ============================================================
# 10) خروج (مغادرة محادثات خاصة) - مطور
# ============================================================
@Client.on_message(filters.regex(r"^خروج\s+من\s+(.+)$"))
async def leave_specific(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not Ranks.is_dev(user_id):
        return

    target = message.matches[0].group(1).strip()
    try:
        if target.lstrip("-").isdigit():
            chat = await client.get_chat(int(target))
        else:
            chat = await client.get_chat(target)
        await client.leave_chat(chat.id)
        await message.reply_text(f"✅ تمت مغادرة : <b>{chat.title or chat.id}</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.reply_text(f"⚠️ فشل : {e}")


# ============================================================
# 11) معلومات البوت
# ============================================================
@Client.on_message(filters.regex(r"^معلومات\s+البوت$"))
async def bot_info(client: Client, message: Message):
    me = await client.get_me()
    text = (
        "🤖 <b>معلومات البوت</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"• الاسم : {me.first_name}\n"
        f"• اليوزر : @{me.username}\n"
        f"• الايدي : <code>{me.id}</code>\n"
        f"• المطور : <a href=\"tg://user?id={config.Dev_Zaid}\">Dev</a>\n"
        "━━━━━━━━━━━━━━"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
