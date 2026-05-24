"""
plugins/del_ranks.py
=====================
حذف الرتب : رتبة محددة / كل رتب المجموعة / كل الرتب العامة.
"""

from pyrogram import Client, filters
from pyrogram.types import Message

from helpers import Ranks


CLEAR_RANK_KEYWORDS = {
    "مسح المطورين المساعدين": Ranks.RANK_DEVP,
    "مسح المساعدين": Ranks.RANK_DEVP,
    "مسح المشغلين": Ranks.RANK_MY,
    "مسح المالكين الأساسيين": Ranks.RANK_PRIMARY_OWNER,
    "مسح المالكين الاساسيين": Ranks.RANK_PRIMARY_OWNER,
    "مسح المالكين": Ranks.RANK_OWNER,
    "مسح المدراء": Ranks.RANK_MANAGER,
    "مسح الادمنية": Ranks.RANK_ADMIN,
    "مسح الأدمنية": Ranks.RANK_ADMIN,
    "مسح المميزين": Ranks.RANK_VIP,
}

import re as _re
_CLEAR_RE = r"^(?:" + "|".join(sorted(map(_re.escape, CLEAR_RANK_KEYWORDS.keys()), key=len, reverse=True)) + r")$"


# ============ مسح رتبة معيّنة ============
@Client.on_message(filters.regex(_CLEAR_RE) & ~filters.bot)
async def clear_specific_rank(client: Client, message: Message):
    text = (message.text or "").strip()
    rank = None
    for kw in sorted(CLEAR_RANK_KEYWORDS.keys(), key=len, reverse=True):
        if text == kw:
            rank = CLEAR_RANK_KEYWORDS[kw]
            break
    if not rank:
        return

    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.can_promote(rds, user_id, rank, chat_id):
        await message.reply_text("⛔ ليس لديك صلاحية لمسح هذه الرتبة.")
        return

    chat_param = chat_id if rank in Ranks.CHAT_RANKS else None
    Ranks.clear_rank(rds, rank, chat_param)

    await message.reply_text(f"🗑 تم مسح جميع <b>{Ranks.RANK_NAMES_AR[rank]}</b>.", parse_mode="html")


# ============ مسح كل الرتب (المجموعة) ============
@Client.on_message(filters.regex(r"^مسح\s+الرتب$") & ~filters.bot)
async def clear_chat_ranks(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.primary_owner_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمالك الأساسي أو أعلى فقط.")
        return

    Ranks.clear_all_chat_ranks(rds, chat_id)
    await message.reply_text("🗑 تم حذف كل رتب هذه المجموعة.")


# ============ حذف الرتب العامة (مطور مساعد + مشغّل) ============
@Client.on_message(filters.regex(r"^حذف\s+الرتب\s+العامة$") & ~filters.bot)
async def clear_global_ranks(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.is_dev(user_id):
        await message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return

    Ranks.clear_all_global_ranks(rds)
    await message.reply_text("🗑 تم حذف جميع الرتب العامة (ما عدا المطور).")


# ============ حذف كل الرتب نهائياً (Dev only) ============
@Client.on_message(filters.regex(r"^حذف\s+جميع\s+الرتب$") & ~filters.bot)
async def clear_everything(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.is_dev(user_id):
        await message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return

    # احذف كل ما يبدأ بـ rank: و rank_lock:
    deleted = 0
    for key in rds.scan_iter("rank:*"):
        rds.delete(key)
        deleted += 1
    for key in rds.scan_iter("rank_lock:*"):
        rds.delete(key)
        deleted += 1

    await message.reply_text(f"🗑 تم حذف جميع الرتب نهائياً ({deleted} مفتاح).")
