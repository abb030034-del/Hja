"""
plugins/group_update.py
========================
- تفعيل / تعطيل البوت داخل المجموعة
- اطلع (طرد البوت)
- ترحيب وتوديع الأعضاء
- ردود تلقائية بسيطة
- معلومات المطور
"""

import random
import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.types import Message, ChatMemberUpdated

import config
from helpers import Ranks
from helpers.utils import mention


# ====== مفاتيح Redis ======
def _bot_enabled_key(chat_id):
    return f"bot:enabled:{chat_id}"


def is_bot_enabled(rds, chat_id) -> bool:
    """البوت مفعّل افتراضياً ما لم يُعطَّل صراحة"""
    val = rds.get(_bot_enabled_key(chat_id))
    if val is None:
        return True
    return val == "1"


def set_bot_enabled(rds, chat_id, enabled: bool):
    rds.set(_bot_enabled_key(chat_id), "1" if enabled else "0")


# =============================================================
# 1) فلتر عام : إن كان البوت معطلاً يوقف معالجة باقي الأوامر
# =============================================================
@Client.on_message(filters.group & filters.text, group=-1)
async def gate_disabled_bot(client: Client, message: Message):
    rds = client.redis
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None

    if is_bot_enabled(rds, chat_id):
        return  # شغّال، خلّي باقي البلجنز تعمل

    # البوت معطّل ـــ اسمح فقط للمشغّل أو أعلى بأمر "تفعيل البوت"
    text = (message.text or "").strip()
    if text == "تفعيل البوت" and user_id and Ranks.my_pls(rds, user_id):
        return  # خلّ معالج التفعيل أدناه يعمل

    # وقّف باقي الهاندلرز
    await message.stop_propagation()


# =============================================================
# 2) تفعيل / تعطيل البوت
# =============================================================
@Client.on_message(filters.group & filters.regex(r"^تفعيل\s+البوت$"))
async def enable_bot(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.my_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر لمشغّل البوت أو أعلى فقط.")
        return

    if is_bot_enabled(rds, message.chat.id):
        await message.reply_text("ℹ️ البوت مفعّل بالفعل.")
        return

    set_bot_enabled(rds, message.chat.id, True)
    await message.reply_text("✅ تم تفعيل البوت في هذه المجموعة.")


@Client.on_message(filters.group & filters.regex(r"^تعطيل\s+البوت$"))
async def disable_bot(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    if not Ranks.my_pls(rds, user_id):
        await message.reply_text("⛔ هذا الأمر لمشغّل البوت أو أعلى فقط.")
        return

    if not is_bot_enabled(rds, message.chat.id):
        await message.reply_text("ℹ️ البوت معطّل بالفعل.")
        return

    set_bot_enabled(rds, message.chat.id, False)
    await message.reply_text("🔕 تم تعطيل البوت في هذه المجموعة.")


# =============================================================
# 3) اطلع / {اسم البوت} اطلع  -> البوت يغادر المجموعة
# =============================================================
@Client.on_message(filters.group & filters.text)
async def leave_command(client: Client, message: Message):
    text = (message.text or "").strip()
    if not text.endswith("اطلع"):
        return

    # صيغ مقبولة: "اطلع" / "البوت اطلع" / "{username} اطلع"
    valid = False
    if text == "اطلع":
        valid = True
    elif text == "البوت اطلع":
        valid = True
    elif config.botUsername and text == f"{config.botUsername} اطلع":
        valid = True
    elif config.botUsername and text == f"@{config.botUsername} اطلع":
        valid = True

    if not valid:
        return

    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    # فقط المالك الأساسي أو أعلى يطرد البوت
    if not Ranks.primary_owner_pls(rds, user_id, message.chat.id):
        await message.reply_text("⛔ هذا الأمر للمالك الأساسي أو أعلى فقط.")
        return

    await message.reply_text("👋 إلى اللقاء..")
    try:
        await asyncio.sleep(0.5)
        await client.leave_chat(message.chat.id)
    except Exception as e:
        await message.reply_text(f"⚠️ فشل المغادرة: {e}")


# =============================================================
# 4) ترحيب وتوديع الأعضاء
# =============================================================
WELCOME_MESSAGES = [
    "🌹 أهلاً وسهلاً بك {user} في {chat}",
    "👋 يا هلا والله بـ {user} ، نوّرت {chat}",
    "✨ منوّرنا يا {user} في {chat}",
]

GOODBYE_MESSAGES = [
    "💔 وداعاً {user} ..",
    "👋 {user} غادر المجموعة.",
    "🚪 {user} ترك {chat}.",
]


@Client.on_message(filters.new_chat_members)
async def on_new_members(client: Client, message: Message):
    rds = client.redis
    if not is_bot_enabled(rds, message.chat.id):
        return

    me = await client.get_me()
    chat_title = message.chat.title or "المجموعة"

    for member in message.new_chat_members:
        if member.id == me.id:
            await message.reply_text(
                "🎉 شكراً لإضافتي إلى المجموعة!\n"
                "اكتب <b>تفعيل البوت</b> للبدء.",
                parse_mode=ParseMode.HTML,
            )
            continue
        if member.is_bot:
            continue

        text = random.choice(WELCOME_MESSAGES).format(
            user=mention(member),
            chat=chat_title,
        )
        await message.reply_text(text, parse_mode=ParseMode.HTML)


@Client.on_message(filters.left_chat_member)
async def on_left_member(client: Client, message: Message):
    rds = client.redis
    if not is_bot_enabled(rds, message.chat.id):
        return

    me = await client.get_me()
    member = message.left_chat_member
    if not member or member.id == me.id or member.is_bot:
        return

    chat_title = message.chat.title or "المجموعة"
    text = random.choice(GOODBYE_MESSAGES).format(
        user=mention(member),
        chat=chat_title,
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML)


# =============================================================
# 5) ردود تلقائية بسيطة
# =============================================================
AUTO_REPLIES = {
    "بوت": [
        "نعم 👀",
        "تامر أمر 🤖",
        "أنا هنا 🌹",
    ],
    "احبك": [
        "وأنا أحبك أكثر ❤️",
        "حبيبي 🌹",
        "بادلك الحب 💖",
    ],
    "اكرهك": [
        "💔 ليش هيك ؟",
        "ما يهمني 😎",
        "اكرهك أكثر 😤",
    ],
    "كليزق": [
        "ابعد عني 🤢",
        "روح اشطف ثوبك 😂",
        "ولك بليز ..",
    ],
    "ميمز": [
        "😂😂😂",
        "🤣🤣🤣",
        "ميمز ولا أروع",
    ],
}


@Client.on_message(filters.text & filters.group)
async def auto_replies(client: Client, message: Message):
    text = (message.text or "").strip()
    if text in AUTO_REPLIES:
        reply = random.choice(AUTO_REPLIES[text])
        await message.reply_text(reply)


# =============================================================
# 6) معلومات المطور
# =============================================================
@Client.on_message(filters.regex(r"^(المطور|مطور البوت)$"))
async def dev_info(client: Client, message: Message):
    dev_id = config.Dev_Zaid
    try:
        u = await client.get_users(dev_id)
        name = u.first_name or "Dev"
        username = f"@{u.username}" if u.username else "—"
    except Exception:
        name = "المطور"
        username = "—"

    text = (
        "👨‍💻 <b>مطور البوت</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"• الاسم : <a href=\"tg://user?id={dev_id}\">{name}</a>\n"
        f"• اليوزر : {username}\n"
        f"• الايدي : <code>{dev_id}</code>\n"
        "━━━━━━━━━━━━━━"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
