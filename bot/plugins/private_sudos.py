"""
plugins/private_sudos.py
=========================
لوحة التحكم الخاصة (Private) — للمطور / المساعدين / المشغّل .

الميزات :
- /start              — قائمة رئيسية بالخاص
- /stats              — إحصائيات
- اسم البوت / رمز البوت / قناة البوت / قروب المطور  (مطور)
- اذاعة بالخاص        — لكل المستخدمين
- اذاعة بالقروبات     — لكل المجموعات
- معلومات السيرفر
- المحظورين           — قائمة المحظورين عاماً
- المكتومين           — قائمة المكتومين عاماً
- تغيير المطور         — للمطور الحالي فقط
- تحديث               — إعادة تحميل
- جلب نسخة القروبات / المستخدمين
"""

import os
import time
import asyncio
import platform

from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatType
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
)

import config
from helpers import Ranks
from helpers.utils import mention


# =================== Redis Keys ===================
GROUPS_KEY = "bot:groups"           # set of chat_ids
USERS_KEY = "bot:users"             # set of user_ids
BOT_NAME_KEY = "bot:name"
BOT_SYMBOL_KEY = "bot:symbol"
BOT_CHANNEL_KEY = "bot:channel"
DEV_GROUP_KEY = "bot:dev_group"
BROADCAST_STATE = "bc:state:{uid}"  # mode in (private/groups)


# =================== تتبع المستخدمين والمجموعات ===================
@Client.on_message(group=-5)
async def track_users_chats(client, message: Message):
    rds = client.redis
    if message.from_user and not message.from_user.is_bot:
        rds.sadd(USERS_KEY, str(message.from_user.id))
    if message.chat and message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        rds.sadd(GROUPS_KEY, str(message.chat.id))


# =================== /start (في الخاص) ===================
@Client.on_message(filters.private & filters.command("start"))
async def private_start(client, message: Message):
    # لا تتداخل مع رابط صارحني
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("sarhni_"):
        return

    rds = client.redis
    uid = message.from_user.id if message.from_user else 0
    is_dev = Ranks.is_dev(uid)
    is_my = Ranks.my_pls(rds, uid)

    name = rds.get(BOT_NAME_KEY) or "بوت ادارة"
    text = (
        f"👋 مرحباً {mention(message.from_user)} في <b>{name}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"يمكنك إضافتي إلى مجموعتك وتفعيلي بأمر : <code>تفعيل البوت</code>\n"
        f"━━━━━━━━━━━━"
    )

    rows = []
    rows.append([InlineKeyboardButton("➕ أضفني لمجموعة", url=f"https://t.me/{config.botUsername}?startgroup=true")])
    rows.append([InlineKeyboardButton("👨‍💻 المطور", url=f"tg://user?id={config.Dev_Zaid}")])

    if is_my:
        rows.append([
            InlineKeyboardButton("📊 الإحصائيات", callback_data="adm:stats"),
            InlineKeyboardButton("🌐 السيرفر", callback_data="adm:server"),
        ])
        rows.append([
            InlineKeyboardButton("📢 إذاعة بالقروبات", callback_data="adm:bc:groups"),
            InlineKeyboardButton("📨 إذاعة بالخاص", callback_data="adm:bc:private"),
        ])
        rows.append([
            InlineKeyboardButton("⛔ المحظورين", callback_data="adm:gban"),
            InlineKeyboardButton("🔇 المكتومين", callback_data="adm:gmute"),
        ])

    if is_dev:
        rows.append([
            InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="adm:settings"),
            InlineKeyboardButton("🔄 تحديث", callback_data="adm:reload"),
        ])

    await message.reply_text(
        text, parse_mode=ParseMode.HTML, disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(rows),
    )


# =================== الإحصائيات ===================
async def _stats_text(client, rds):
    users = rds.scard(USERS_KEY) or 0
    groups = rds.scard(GROUPS_KEY) or 0
    gbanned = rds.scard("gban:users") or 0
    gmuted = rds.scard("gmute:users") or 0
    accounts = sum(1 for _ in rds.scan_iter("bank:acc:*"))
    return (
        "📊 <b>إحصائيات البوت</b>\n"
        "━━━━━━━━━━━━\n"
        f"• المستخدمون : <code>{users}</code>\n"
        f"• المجموعات : <code>{groups}</code>\n"
        f"• الحسابات البنكية : <code>{accounts}</code>\n"
        f"• محظور عام : <code>{gbanned}</code>\n"
        f"• مكتوم عام : <code>{gmuted}</code>\n"
        "━━━━━━━━━━━━"
    )


@Client.on_message(filters.regex(r"^(/stats|الاحصائيات|الإحصائيات)$"))
async def cmd_stats(client, message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not Ranks.my_pls(rds, user_id):
        return
    await message.reply_text(await _stats_text(client, rds), parse_mode=ParseMode.HTML)


# =================== معلومات السيرفر ===================
@Client.on_message(filters.regex(r"^معلومات\s+السيرفر$"))
async def server_info(client, message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not Ranks.my_pls(rds, user_id):
        return

    try:
        import psutil  # type: ignore
        cpu = f"{psutil.cpu_percent(interval=0.3)}%"
        ram = f"{psutil.virtual_memory().percent}%"
        disk = f"{psutil.disk_usage('/').percent}%"
    except Exception:
        cpu = ram = disk = "?"

    text = (
        "🖥 <b>معلومات السيرفر</b>\n"
        "━━━━━━━━━━━━\n"
        f"• النظام : <code>{platform.system()} {platform.release()}</code>\n"
        f"• Python : <code>{platform.python_version()}</code>\n"
        f"• CPU : <code>{cpu}</code>\n"
        f"• RAM : <code>{ram}</code>\n"
        f"• Disk : <code>{disk}</code>\n"
        "━━━━━━━━━━━━"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML)


# =================== تعيين : اسم البوت / رمزه / قناته / مجموعة المطور ===================
@Client.on_message(filters.regex(r"^تعيين\s+اسم\s+البوت\s+([\s\S]+)$"))
async def set_bot_name(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.is_dev(message.from_user.id):
        return
    name = message.matches[0].group(1).strip()
    rds.set(BOT_NAME_KEY, name)
    await message.reply_text(f"✅ اسم البوت : <b>{name}</b>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^تعيين\s+رمز\s+البوت\s+([\s\S]+)$"))
async def set_bot_symbol(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.is_dev(message.from_user.id):
        return
    sym = message.matches[0].group(1).strip()
    rds.set(BOT_SYMBOL_KEY, sym)
    await message.reply_text(f"✅ رمز البوت : <b>{sym}</b>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^تعيين\s+قناة\s+البوت\s+([\s\S]+)$"))
async def set_bot_channel(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.is_dev(message.from_user.id):
        return
    ch = message.matches[0].group(1).strip()
    rds.set(BOT_CHANNEL_KEY, ch)
    await message.reply_text(f"✅ قناة البوت : <b>{ch}</b>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^تعيين\s+مجموعة\s+المطور\s+([\s\S]+)$"))
async def set_dev_group(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.is_dev(message.from_user.id):
        return
    g = message.matches[0].group(1).strip()
    rds.set(DEV_GROUP_KEY, g)
    await message.reply_text(f"✅ مجموعة المطور : <b>{g}</b>", parse_mode=ParseMode.HTML)


# =================== المحظورين / المكتومين ===================
async def _format_user_set(client, rds, key, title, emoji):
    members = rds.smembers(key) or set()
    if not members:
        return f"📭 لا يوجد {title}."
    lines = [f"{emoji} <b>{title} ({len(members)})</b>\n"]
    for i, uid in enumerate(sorted(members), 1):
        try:
            u = await client.get_users(int(uid))
            lines.append(f"{i}. {mention(u)} — <code>{uid}</code>")
        except Exception:
            lines.append(f"{i}. <code>{uid}</code>")
        if i >= 50:
            lines.append(f"... و {len(members)-i} أكثر")
            break
    return "\n".join(lines)


@Client.on_message(filters.regex(r"^المحظورين$"))
async def show_gbanned(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.devp_pls(rds, message.from_user.id):
        return
    text = await _format_user_set(client, rds, "gban:users", "المحظورون عامّاً", "⛔")
    await message.reply_text(text, parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^المكتومين$"))
async def show_gmuted(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.devp_pls(rds, message.from_user.id):
        return
    text = await _format_user_set(client, rds, "gmute:users", "المكتومون عامّاً", "🔇")
    await message.reply_text(text, parse_mode=ParseMode.HTML)


# =================== الإذاعة ===================
@Client.on_message(filters.regex(r"^اذاعة\s+بالقروبات$") & filters.reply)
async def broadcast_groups(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.devp_pls(rds, message.from_user.id):
        return
    src = message.reply_to_message
    if not src:
        await message.reply_text("⚠️ ردّ على رسالة لإذاعتها.")
        return

    groups = list(rds.smembers(GROUPS_KEY) or [])
    status = await message.reply_text(f"📢 جاري الإذاعة إلى {len(groups)} مجموعة ...")
    sent, failed = 0, 0
    for cid in groups:
        try:
            await src.copy(int(cid))
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ تم الإرسال إلى <b>{sent}</b> | ❌ فشل: <b>{failed}</b>", parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^اذاعة\s+بالخاص$") & filters.reply)
async def broadcast_private(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.devp_pls(rds, message.from_user.id):
        return
    src = message.reply_to_message
    if not src:
        await message.reply_text("⚠️ ردّ على رسالة لإذاعتها.")
        return

    users = list(rds.smembers(USERS_KEY) or [])
    status = await message.reply_text(f"📨 جاري الإرسال لـ {len(users)} مستخدم ...")
    sent, failed = 0, 0
    for uid in users:
        try:
            await src.copy(int(uid))
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ تم الإرسال إلى <b>{sent}</b> | ❌ فشل: <b>{failed}</b>", parse_mode=ParseMode.HTML)


# =================== تغيير المطور الأساسي ===================
@Client.on_message(filters.regex(r"^تغيير\s+المطور\s+(\d+)$"))
async def change_dev(client, message):
    if not message.from_user or not Ranks.is_dev(message.from_user.id):
        return
    new_id = int(message.matches[0].group(1))

    data = config.load_settings()
    data["dev_zaid"] = new_id
    config.save_settings(data)
    config.Dev_Zaid = new_id
    config.sudo_id = [new_id]

    await message.reply_text(f"✅ تم نقل ملكية المطور إلى : <code>{new_id}</code>", parse_mode=ParseMode.HTML)


# =================== تحديث ===================
@Client.on_message(filters.regex(r"^تحديث$"))
async def reload_bot(client, message):
    if not message.from_user or not Ranks.is_dev(message.from_user.id):
        return
    await message.reply_text("🔄 جاري إعادة التشغيل ...")
    # نخرج بكود 0 - سيقوم supervisor/systemd بإعادة التشغيل.
    # أو ببساطة نوقف العملية.
    os._exit(0)


# =================== جلب نسخة من القروبات / المستخدمين ===================
@Client.on_message(filters.regex(r"^جلب\s+نسخة\s+القروبات$"))
async def export_groups(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.is_dev(message.from_user.id):
        return
    groups = list(rds.smembers(GROUPS_KEY) or [])
    if not groups:
        await message.reply_text("📭 لا توجد مجموعات مسجّلة.")
        return
    path = "/tmp/bot_groups.txt"
    with open(path, "w", encoding="utf-8") as f:
        for gid in groups:
            try:
                ch = await client.get_chat(int(gid))
                f.write(f"{gid}\t{ch.title}\t@{ch.username or '-'}\n")
            except Exception:
                f.write(f"{gid}\t?\n")
    await client.send_document(message.chat.id, path, caption=f"📦 {len(groups)} مجموعة")


@Client.on_message(filters.regex(r"^جلب\s+نسخة\s+المستخدمين$"))
async def export_users(client, message):
    rds = client.redis
    if not message.from_user or not Ranks.is_dev(message.from_user.id):
        return
    users = list(rds.smembers(USERS_KEY) or [])
    if not users:
        await message.reply_text("📭 لا يوجد مستخدمون مسجّلون.")
        return
    path = "/tmp/bot_users.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(users))
    await client.send_document(message.chat.id, path, caption=f"📦 {len(users)} مستخدم")


# =================== Callback Queries للوحة التحكم ===================
@Client.on_callback_query(filters.regex(r"^adm:"))
async def admin_callbacks(client, query: CallbackQuery):
    rds = client.redis
    uid = query.from_user.id
    if not Ranks.my_pls(rds, uid):
        await query.answer("⛔ ليس لديك صلاحية.", show_alert=True)
        return

    data = query.data

    if data == "adm:stats":
        await query.message.edit_text(await _stats_text(client, rds), parse_mode=ParseMode.HTML)
    elif data == "adm:server":
        try:
            import psutil  # type: ignore
            cpu, ram, disk = f"{psutil.cpu_percent(interval=0.3)}%", f"{psutil.virtual_memory().percent}%", f"{psutil.disk_usage('/').percent}%"
        except Exception:
            cpu = ram = disk = "?"
        await query.message.edit_text(
            f"🖥 <b>السيرفر</b>\n━━━━━━━━━━━━\n"
            f"• OS: {platform.system()} {platform.release()}\n"
            f"• Python: {platform.python_version()}\n"
            f"• CPU: {cpu} | RAM: {ram} | Disk: {disk}",
            parse_mode=ParseMode.HTML,
        )
    elif data == "adm:gban":
        await query.message.edit_text(await _format_user_set(client, rds, "gban:users", "المحظورون عامّاً", "⛔"), parse_mode=ParseMode.HTML)
    elif data == "adm:gmute":
        await query.message.edit_text(await _format_user_set(client, rds, "gmute:users", "المكتومون عامّاً", "🔇"), parse_mode=ParseMode.HTML)
    elif data == "adm:bc:groups":
        await query.answer("ردّ على الرسالة المراد إذاعتها بالأمر :\nاذاعة بالقروبات", show_alert=True)
    elif data == "adm:bc:private":
        await query.answer("ردّ على الرسالة المراد إذاعتها بالأمر :\nاذاعة بالخاص", show_alert=True)
    elif data == "adm:settings":
        name = rds.get(BOT_NAME_KEY) or "—"
        sym = rds.get(BOT_SYMBOL_KEY) or "—"
        ch = rds.get(BOT_CHANNEL_KEY) or "—"
        dg = rds.get(DEV_GROUP_KEY) or "—"
        await query.message.edit_text(
            "⚙️ <b>إعدادات البوت</b>\n━━━━━━━━━━━━\n"
            f"• الاسم : <b>{name}</b>\n"
            f"• الرمز : <b>{sym}</b>\n"
            f"• القناة : <b>{ch}</b>\n"
            f"• قروب المطور : <b>{dg}</b>\n\n"
            "للتعيين :\n"
            "<code>تعيين اسم البوت ...</code>\n"
            "<code>تعيين رمز البوت ...</code>\n"
            "<code>تعيين قناة البوت ...</code>\n"
            "<code>تعيين مجموعة المطور ...</code>",
            parse_mode=ParseMode.HTML,
        )
    elif data == "adm:reload":
        if not Ranks.is_dev(uid):
            await query.answer("⛔ للمطور فقط.", show_alert=True)
            return
        await query.message.edit_text("🔄 جاري إعادة التشغيل ...")
        await asyncio.sleep(0.5)
        os._exit(0)

    await query.answer()
