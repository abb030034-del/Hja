"""
plugins/set_ranks.py
=====================
رفع وتنزيل الرتب + تفعيل/تعطيل الرفع + تنزيل الكل.
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks
from helpers.utils import extract_user, mention


# ====== ربط الكلمات العربية بأسماء الرتب ======
RAISE_KEYWORDS = {
    "رفع مطور": Ranks.RANK_DEV,
    "رفع مطور مساعد": Ranks.RANK_DEVP,
    "رفع مساعد": Ranks.RANK_DEVP,
    "رفع مشغل": Ranks.RANK_MY,
    "رفع مالك اساسي": Ranks.RANK_PRIMARY_OWNER,
    "رفع مالك أساسي": Ranks.RANK_PRIMARY_OWNER,
    "رفع مالك": Ranks.RANK_OWNER,
    "رفع مدير": Ranks.RANK_MANAGER,
    "رفع ادمن": Ranks.RANK_ADMIN,
    "رفع أدمن": Ranks.RANK_ADMIN,
    "رفع مميز": Ranks.RANK_VIP,
}

DEMOTE_KEYWORDS = {
    "تنزيل مطور": Ranks.RANK_DEV,
    "تنزيل مطور مساعد": Ranks.RANK_DEVP,
    "تنزيل مساعد": Ranks.RANK_DEVP,
    "تنزيل مشغل": Ranks.RANK_MY,
    "تنزيل مالك اساسي": Ranks.RANK_PRIMARY_OWNER,
    "تنزيل مالك أساسي": Ranks.RANK_PRIMARY_OWNER,
    "تنزيل مالك": Ranks.RANK_OWNER,
    "تنزيل مدير": Ranks.RANK_MANAGER,
    "تنزيل ادمن": Ranks.RANK_ADMIN,
    "تنزيل أدمن": Ranks.RANK_ADMIN,
    "تنزيل مميز": Ranks.RANK_VIP,
}


def _match_keyword(text: str, mapping: dict):
    """مطابقة بداية النص مع أطول مفتاح ممكن"""
    if not text:
        return None
    text = text.strip()
    # رتّب من الأطول للأقصر حتى لا يطغى "رفع مالك" على "رفع مالك اساسي"
    for kw in sorted(mapping.keys(), key=len, reverse=True):
        if text == kw or text.startswith(kw + " ") or text.startswith(kw + "\n"):
            return mapping[kw]
    return None


# ============ رفع رتبة ============
@Client.on_message(filters.text & ~filters.bot)
async def handle_raise(client: Client, message: Message):
    rank = _match_keyword(message.text, RAISE_KEYWORDS)
    if not rank:
        return

    rds = client.redis
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    # 1) تحقق صلاحية الرفع
    if not Ranks.can_promote(rds, user_id, rank, chat_id):
        await message.reply_text("⛔ ليس لديك صلاحية لرفع هذه الرتبة.")
        return

    # 2) تحقق من قفل الرفع (يطبّق فقط على رتب المجموعة، تخطّى المطور)
    if not Ranks.is_dev(user_id) and Ranks.is_promotion_locked(rds, rank, chat_id if rank in Ranks.CHAT_RANKS else None):
        await message.reply_text("🔒 الرفع لهذه الرتبة معطّل حالياً.")
        return

    # 3) استخراج المستهدف
    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه أو ايديه.")
        return

    if target.is_bot:
        await message.reply_text("⚠️ لا يمكن رفع رتبة بوت.")
        return

    # 4) منع رفع المطور أو الذات
    if Ranks.is_dev(target.id) and rank != Ranks.RANK_DEV:
        await message.reply_text("⚠️ هذا المستخدم هو المطور أصلاً.")
        return

    chat_param = chat_id if rank in Ranks.CHAT_RANKS else None
    if Ranks.has_rank(rds, rank, target.id, chat_param):
        await message.reply_text(
            f"ℹ️ {mention(target)} يملك رتبة <b>{Ranks.RANK_NAMES_AR[rank]}</b> مسبقاً.",
            parse_mode=ParseMode.HTML,
        )
        return

    Ranks.add_rank(rds, rank, target.id, chat_param)
    await message.reply_text(
        f"✅ تم رفع {mention(target)} إلى رتبة <b>{Ranks.RANK_NAMES_AR[rank]}</b>.",
        parse_mode=ParseMode.HTML,
    )


# ============ تنزيل رتبة ============
@Client.on_message(filters.text & ~filters.bot)
async def handle_demote(client: Client, message: Message):
    rank = _match_keyword(message.text, DEMOTE_KEYWORDS)
    if not rank:
        return

    rds = client.redis
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.can_promote(rds, user_id, rank, chat_id):
        await message.reply_text("⛔ ليس لديك صلاحية لتنزيل هذه الرتبة.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه أو ايديه.")
        return

    # لا يمكن تنزيل المطور
    if Ranks.is_dev(target.id):
        await message.reply_text("⛔ لا يمكن تنزيل المطور.")
        return

    chat_param = chat_id if rank in Ranks.CHAT_RANKS else None
    if not Ranks.has_rank(rds, rank, target.id, chat_param):
        await message.reply_text(
            f"ℹ️ {mention(target)} لا يملك رتبة <b>{Ranks.RANK_NAMES_AR[rank]}</b>.",
            parse_mode=ParseMode.HTML,
        )
        return

    Ranks.remove_rank(rds, rank, target.id, chat_param)
    await message.reply_text(
        f"✅ تم تنزيل {mention(target)} من رتبة <b>{Ranks.RANK_NAMES_AR[rank]}</b>.",
        parse_mode=ParseMode.HTML,
    )


# ============ تفعيل / تعطيل الرفع ============
@Client.on_message(filters.regex(r"^(تفعيل|تعطيل)\s+الرفع(?:\s+(.+))?$") & ~filters.bot)
async def handle_toggle_promotion(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    # فقط مالك أساسي أو أعلى يستطيع التحكم
    if not Ranks.primary_owner_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمالك الأساسي أو أعلى فقط.")
        return

    action = message.matches[0].group(1)
    rank_text = (message.matches[0].group(2) or "").strip()

    # ابحث عن اسم رتبة محدد، وإلا طبّق على كل رتب المجموعة
    target_ranks = []
    if rank_text:
        mapping_search = {
            "مالك اساسي": Ranks.RANK_PRIMARY_OWNER,
            "مالك أساسي": Ranks.RANK_PRIMARY_OWNER,
            "مالك": Ranks.RANK_OWNER,
            "مدير": Ranks.RANK_MANAGER,
            "ادمن": Ranks.RANK_ADMIN,
            "أدمن": Ranks.RANK_ADMIN,
            "مميز": Ranks.RANK_VIP,
        }
        rank = None
        for kw in sorted(mapping_search.keys(), key=len, reverse=True):
            if rank_text == kw:
                rank = mapping_search[kw]
                break
        if not rank:
            await message.reply_text("⚠️ اسم الرتبة غير صحيح.")
            return
        target_ranks = [rank]
    else:
        target_ranks = list(Ranks.CHAT_RANKS)

    if action == "تفعيل":
        for r in target_ranks:
            Ranks.unlock_promotion(rds, r, chat_id)
        await message.reply_text("✅ تم تفعيل الرفع.")
    else:
        for r in target_ranks:
            Ranks.lock_promotion(rds, r, chat_id)
        await message.reply_text("🔒 تم تعطيل الرفع.")


# ============ تنزيل الكل ============
@Client.on_message(filters.regex(r"^تنزيل\s+الكل$") & ~filters.bot)
async def handle_demote_all(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.primary_owner_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمالك الأساسي أو أعلى فقط.")
        return

    # تنزيل كل الرتب الخاصة بالمجموعة (ما عدا المالك الأساسي يبقى لمن أصدر الأمر)
    for r in Ranks.CHAT_RANKS:
        Ranks.clear_rank(rds, r, chat_id)

    await message.reply_text("✅ تم تنزيل كل الرتب في هذه المجموعة.")
