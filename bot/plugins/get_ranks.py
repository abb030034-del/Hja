"""
plugins/get_ranks.py
=====================
عرض قوائم الرتب + مسح رتبة معيّنة + تغيير رتبة.
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

import config
from helpers import Ranks
from helpers.utils import extract_user, mention


# اسم الرتبة بالعربي -> رمز الرتبة
LIST_KEYWORDS = {
    "قائمة المطورين": Ranks.RANK_DEV,
    "قائمة المطورين المساعدين": Ranks.RANK_DEVP,
    "قائمة المساعدين": Ranks.RANK_DEVP,
    "قائمة المشغلين": Ranks.RANK_MY,
    "قائمة المالكين الأساسيين": Ranks.RANK_PRIMARY_OWNER,
    "قائمة المالكين الاساسيين": Ranks.RANK_PRIMARY_OWNER,
    "قائمة المالكين": Ranks.RANK_OWNER,
    "قائمة المدراء": Ranks.RANK_MANAGER,
    "قائمة الادمنية": Ranks.RANK_ADMIN,
    "قائمة الأدمنية": Ranks.RANK_ADMIN,
    "قائمة المميزين": Ranks.RANK_VIP,
}


# ============ قائمة رتبة معيّنة ============
@Client.on_message(filters.text & ~filters.bot)
async def list_rank(client: Client, message: Message):
    text = (message.text or "").strip()

    rank = None
    for kw in sorted(LIST_KEYWORDS.keys(), key=len, reverse=True):
        if text == kw:
            rank = LIST_KEYWORDS[kw]
            break
    if not rank:
        return

    rds = client.redis
    chat_id = message.chat.id

    # رتب عامة لا تأخذ chat_id
    if rank == Ranks.RANK_DEV:
        members = {str(config.Dev_Zaid)} if config.Dev_Zaid else set()
    elif rank in Ranks.GLOBAL_RANKS:
        members = Ranks.get_rank_members(rds, rank)
    else:
        members = Ranks.get_rank_members(rds, rank, chat_id)

    title = Ranks.RANK_NAMES_AR[rank]
    if not members:
        await message.reply_text(f"📭 لا يوجد أي مستخدم برتبة <b>{title}</b>.", parse_mode=ParseMode.HTML)
        return

    lines = [f"📋 قائمة <b>{title}</b> ({len(members)}):\n"]
    for i, uid in enumerate(sorted(members), 1):
        try:
            u = await client.get_users(int(uid))
            lines.append(f"{i}. {mention(u)}  <code>{uid}</code>")
        except Exception:
            lines.append(f"{i}. <code>{uid}</code>")

    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ============ قائمة الرتب (اجمالي) ============
@Client.on_message(filters.regex(r"^قائمة\s+الرتب$") & ~filters.bot)
async def list_all_ranks(client: Client, message: Message):
    rds = client.redis
    chat_id = message.chat.id

    lines = ["📊 <b>إحصائيات الرتب في هذه المجموعة:</b>\n"]

    # رتب عامة
    for r in (Ranks.RANK_DEV, Ranks.RANK_DEVP, Ranks.RANK_MY):
        if r == Ranks.RANK_DEV:
            count = 1
        else:
            count = len(Ranks.get_rank_members(rds, r))
        lines.append(f"• {Ranks.RANK_NAMES_AR[r]} : <code>{count}</code>")

    lines.append("")

    # رتب المجموعة
    for r in (Ranks.RANK_PRIMARY_OWNER, Ranks.RANK_OWNER,
              Ranks.RANK_MANAGER, Ranks.RANK_ADMIN, Ranks.RANK_VIP):
        count = len(Ranks.get_rank_members(rds, r, chat_id))
        lines.append(f"• {Ranks.RANK_NAMES_AR[r]} : <code>{count}</code>")

    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ============ رتبتي / رتبة (الرد على شخص) ============
@Client.on_message(filters.regex(r"^(رتبتي|رتبة)$") & ~filters.bot)
async def my_rank(client: Client, message: Message):
    rds = client.redis
    chat_id = message.chat.id

    if message.matches[0].group(1) == "رتبة" and message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        target = message.from_user

    if not target:
        return

    rank = Ranks.get_user_top_rank(rds, target.id, chat_id)
    if not rank:
        await message.reply_text(
            f"ℹ️ {mention(target)} ليس لديه أي رتبة.",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.reply_text(
        f"🎖 رتبة {mention(target)} : <b>{Ranks.RANK_NAMES_AR[rank]}</b>",
        parse_mode=ParseMode.HTML,
    )


# ============ تغيير رتبة (تنزيل القديمة + رفع جديدة) ============
@Client.on_message(filters.regex(r"^تغيير\s+رتبة\s+(.+)$") & ~filters.bot)
async def change_rank(client: Client, message: Message):
    rds = client.redis
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    new_rank_text = message.matches[0].group(1).strip()
    # احذف أي ايدي/يوزرنيم في نهاية النص حتى نطابق اسم الرتبة فقط
    parts = new_rank_text.split()
    # نحاول مطابقة من البداية مع أطول اسم
    name_map = {
        "مطور مساعد": Ranks.RANK_DEVP,
        "مساعد": Ranks.RANK_DEVP,
        "مشغل": Ranks.RANK_MY,
        "مالك اساسي": Ranks.RANK_PRIMARY_OWNER,
        "مالك أساسي": Ranks.RANK_PRIMARY_OWNER,
        "مالك": Ranks.RANK_OWNER,
        "مدير": Ranks.RANK_MANAGER,
        "ادمن": Ranks.RANK_ADMIN,
        "أدمن": Ranks.RANK_ADMIN,
        "مميز": Ranks.RANK_VIP,
    }

    rank = None
    for kw in sorted(name_map.keys(), key=len, reverse=True):
        if new_rank_text == kw or new_rank_text.startswith(kw + " "):
            rank = name_map[kw]
            break

    if not rank:
        await message.reply_text("⚠️ اسم الرتبة غير معروف.")
        return

    if not Ranks.can_promote(rds, user_id, rank, chat_id):
        await message.reply_text("⛔ ليس لديك صلاحية لتغيير هذه الرتبة.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه أو ايديه.")
        return

    if Ranks.is_dev(target.id):
        await message.reply_text("⛔ لا يمكن تغيير رتبة المطور.")
        return

    chat_param = chat_id if rank in Ranks.CHAT_RANKS else None

    # احذف كل رتبه السابقة في هذه المجموعة
    for r in Ranks.CHAT_RANKS:
        Ranks.remove_rank(rds, r, target.id, chat_id)
    # وأيضاً العامة (إن كانت الرتبة الجديدة عامة سنُضيفها أدناه)
    if rank in Ranks.GLOBAL_RANKS:
        for r in (Ranks.RANK_DEVP, Ranks.RANK_MY):
            Ranks.remove_rank(rds, r, target.id)

    Ranks.add_rank(rds, rank, target.id, chat_param)

    await message.reply_text(
        f"🔄 تم تغيير رتبة {mention(target)} إلى <b>{Ranks.RANK_NAMES_AR[rank]}</b>.",
        parse_mode=ParseMode.HTML,
    )
