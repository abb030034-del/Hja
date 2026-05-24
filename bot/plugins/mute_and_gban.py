"""
plugins/mute_and_gban.py
=========================
- كتم / إلغاء الكتم (محلي داخل المجموعة)
- كتم عام / إلغاء الكتم العام  (يطبّق على كل المجموعات)
- حظر عام / إلغاء الحظر العام  (يطرد من كل مجموعة فيها البوت)
- حظر عام من الألعاب / إلغاء الحظر العام من الألعاب
"""

from datetime import datetime, timedelta, timezone

from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.types import Message, ChatPermissions

from helpers import Ranks
from helpers.utils import extract_user, mention


# ====== مفاتيح Redis ======
GMUTE_KEY = "gmute:users"
GBAN_KEY = "gban:users"
GBAN_GAMES_KEY = "gban_games:users"


# ====== فحوصات سريعة ======
def is_gmuted(rds, user_id) -> bool:
    return bool(rds.sismember(GMUTE_KEY, str(user_id)))


def is_gbanned(rds, user_id) -> bool:
    return bool(rds.sismember(GBAN_KEY, str(user_id)))


def is_gbanned_games(rds, user_id) -> bool:
    return bool(rds.sismember(GBAN_GAMES_KEY, str(user_id)))


# ====== صلاحيات Telegram (للكتم/إلغاؤه) ======
NO_PERMS = ChatPermissions(
    can_send_messages=False,
    can_send_media_messages=False,
    can_send_other_messages=False,
    can_send_polls=False,
    can_add_web_page_previews=False,
)

FULL_PERMS = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_other_messages=True,
    can_send_polls=True,
    can_add_web_page_previews=True,
    can_invite_users=True,
    can_change_info=False,
    can_pin_messages=False,
)


# =====================================================
# 1) كتم محلي
# =====================================================
@Client.on_message(filters.group & filters.regex(r"^كتم$"))
async def local_mute(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه/ايديه.")
        return

    if Ranks.is_dev(target.id):
        await message.reply_text("⛔ لا يمكن كتم المطور.")
        return

    if Ranks.admin_pls(rds, target.id, chat_id):
        await message.reply_text("⛔ لا يمكن كتم شخص يملك صلاحية مماثلة أو أعلى.")
        return

    try:
        await client.restrict_chat_member(chat_id, target.id, NO_PERMS)
    except Exception as e:
        await message.reply_text(f"⚠️ تعذّر الكتم : {e}")
        return

    await message.reply_text(
        f"🔇 تم كتم {mention(target)}.",
        parse_mode=ParseMode.HTML,
    )


# =====================================================
# 2) إلغاء الكتم المحلي
# =====================================================
@Client.on_message(filters.group & filters.regex(r"^(الغاء|إلغاء)\s+الكتم$"))
async def local_unmute(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه/ايديه.")
        return

    try:
        await client.restrict_chat_member(chat_id, target.id, FULL_PERMS)
    except Exception as e:
        await message.reply_text(f"⚠️ تعذّر إلغاء الكتم : {e}")
        return

    await message.reply_text(
        f"🔊 تم إلغاء كتم {mention(target)}.",
        parse_mode=ParseMode.HTML,
    )


# =====================================================
# 3) كتم عام
# =====================================================
@Client.on_message(filters.regex(r"^كتم\s+عام$"))
async def global_mute(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    # كتم عام للمطور والمساعد فقط
    if not Ranks.devp_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر للمطور أو المطور المساعد فقط.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه/ايديه.")
        return

    if Ranks.is_dev(target.id):
        await message.reply_text("⛔ لا يمكن كتم المطور.")
        return

    if is_gmuted(rds, target.id):
        await message.reply_text("ℹ️ هذا المستخدم مكتوم عاماً مسبقاً.")
        return

    rds.sadd(GMUTE_KEY, str(target.id))
    await message.reply_text(
        f"🌐🔇 تم تطبيق <b>كتم عام</b> على {mention(target)}.",
        parse_mode=ParseMode.HTML,
    )


@Client.on_message(filters.regex(r"^(الغاء|إلغاء)\s+الكتم\s+العام$"))
async def global_unmute(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.devp_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر للمطور أو المطور المساعد فقط.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه/ايديه.")
        return

    if not is_gmuted(rds, target.id):
        await message.reply_text("ℹ️ هذا المستخدم ليس مكتوماً عاماً.")
        return

    rds.srem(GMUTE_KEY, str(target.id))
    await message.reply_text(
        f"🌐🔊 تم إلغاء الكتم العام عن {mention(target)}.",
        parse_mode=ParseMode.HTML,
    )


# =====================================================
# 4) حظر عام
# =====================================================
@Client.on_message(filters.regex(r"^حظر\s+عام$"))
async def global_ban(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.devp_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر للمطور أو المطور المساعد فقط.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه/ايديه.")
        return

    if Ranks.is_dev(target.id):
        await message.reply_text("⛔ لا يمكن حظر المطور.")
        return

    if is_gbanned(rds, target.id):
        await message.reply_text("ℹ️ هذا المستخدم محظور عاماً مسبقاً.")
        return

    rds.sadd(GBAN_KEY, str(target.id))

    # محاولة طرده من المجموعة الحالية فوراً (إن كانت من مجموعة)
    if message.chat.type.name != "PRIVATE":
        try:
            await client.ban_chat_member(message.chat.id, target.id)
        except Exception:
            pass

    await message.reply_text(
        f"🌐⛔ تم تطبيق <b>حظر عام</b> على {mention(target)}.",
        parse_mode=ParseMode.HTML,
    )


@Client.on_message(filters.regex(r"^(الغاء|إلغاء)\s+الحظر\s+العام$"))
async def global_unban(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.devp_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر للمطور أو المطور المساعد فقط.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه/ايديه.")
        return

    if not is_gbanned(rds, target.id):
        await message.reply_text("ℹ️ هذا المستخدم ليس محظوراً عاماً.")
        return

    rds.srem(GBAN_KEY, str(target.id))
    await message.reply_text(
        f"🌐✅ تم إلغاء الحظر العام عن {mention(target)}.",
        parse_mode=ParseMode.HTML,
    )


# =====================================================
# 5) حظر عام من الألعاب
# =====================================================
@Client.on_message(filters.regex(r"^حظر\s+عام\s+من\s+الالعاب$"))
async def global_ban_games(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.my_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر لمشغّل البوت أو أعلى فقط.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه/ايديه.")
        return

    if Ranks.is_dev(target.id):
        await message.reply_text("⛔ لا يمكن حظر المطور.")
        return

    if is_gbanned_games(rds, target.id):
        await message.reply_text("ℹ️ هذا المستخدم محظور من الألعاب مسبقاً.")
        return

    rds.sadd(GBAN_GAMES_KEY, str(target.id))
    await message.reply_text(
        f"🎮⛔ تم حظر {mention(target)} من الألعاب عامّاً.",
        parse_mode=ParseMode.HTML,
    )


@Client.on_message(filters.regex(r"^(الغاء|إلغاء)\s+الحظر\s+العام\s+من\s+الالعاب$"))
async def global_unban_games(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.my_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر لمشغّل البوت أو أعلى فقط.")
        return

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه/ايديه.")
        return

    if not is_gbanned_games(rds, target.id):
        await message.reply_text("ℹ️ هذا المستخدم ليس محظوراً من الألعاب.")
        return

    rds.srem(GBAN_GAMES_KEY, str(target.id))
    await message.reply_text(
        f"🎮✅ تم إلغاء الحظر العام من الألعاب عن {mention(target)}.",
        parse_mode=ParseMode.HTML,
    )


# =====================================================
# 6) تطبيق الكتم العام : حذف رسائل المكتومين عامّاً
# =====================================================
@Client.on_message(filters.group & ~filters.service, group=-2)
async def enforce_global_mute(client: Client, message: Message):
    if not message.from_user:
        return
    rds = client.redis
    if is_gmuted(rds, message.from_user.id):
        try:
            await message.delete()
        except Exception:
            pass
        await message.stop_propagation()


# =====================================================
# 7) تطبيق الحظر العام : طرد المحظور عند انضمامه
# =====================================================
@Client.on_message(filters.new_chat_members, group=-2)
async def enforce_global_ban_on_join(client: Client, message: Message):
    rds = client.redis
    for member in message.new_chat_members:
        if is_gbanned(rds, member.id):
            try:
                await client.ban_chat_member(message.chat.id, member.id)
                await message.reply_text(
                    f"⛔ تم طرد {mention(member)} (محظور عامّاً).",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
