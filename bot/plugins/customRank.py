"""
plugins/customRank.py
======================
ألقاب الأعضاء (رتب مخصصة - مجرد ألقاب نصية بجانب اسم العضو):
- تغيير رتبه <اللقب>   (بالرد / يوزر / ايدي)   ← أدمن+
- مسح رتبه             (بالرد / يوزر / ايدي)   ← أدمن+
- قائمة الرتب          ← عرض قائمة الألقاب  (الجميع)
- مسح الرتب            ← حذف كل ألقاب المجموعة  (مدير+)
- رتبتي                ← عرض لقبي  (الجميع)  [نُكمل وظيفة سابقة]
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks
from helpers.utils import extract_user, mention


# ====== Redis ======
def _titles_key(chat_id): return f"titles:{chat_id}"   # hash : user_id -> title


def get_title(rds, chat_id, user_id):
    return rds.hget(_titles_key(chat_id), str(user_id))


def set_title(rds, chat_id, user_id, title):
    rds.hset(_titles_key(chat_id), str(user_id), title)


def del_title(rds, chat_id, user_id):
    rds.hdel(_titles_key(chat_id), str(user_id))


# ============================================================
# 1) تغيير رتبه <لقب>
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^تغيير\s+رتبه\s+([\s\S]+)$"))
async def change_title(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.admin_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى فقط.")
        return

    raw = message.matches[0].group(1).strip()

    # افصل اللقب عن (الرد/المنشن/الايدي)
    target = await extract_user(client, message)
    if target:
        # حذف آخر كلمة إن كانت يوزر/ايدي
        parts = raw.split()
        if len(parts) > 1 and (parts[-1].startswith("@") or parts[-1].lstrip("-").isdigit()):
            raw = " ".join(parts[:-1]).strip()

    if not raw:
        await message.reply_text("⚠️ اكتب اللقب بعد الأمر.")
        return

    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم أو كتابة يوزرنيمه/ايديه.")
        return

    if len(raw) > 40:
        await message.reply_text("⚠️ اللقب طويل جداً (40 حرفاً كحدّ أقصى).")
        return

    set_title(rds, chat_id, target.id, raw)
    await message.reply_text(
        f"🏷 تم تعيين لقب {mention(target)} : <b>{raw}</b>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 2) مسح رتبه
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^مسح\s+رتبه$"))
async def clear_title(client: Client, message: Message):
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

    if not get_title(rds, chat_id, target.id):
        await message.reply_text("ℹ️ هذا العضو ليس لديه لقب.")
        return

    del_title(rds, chat_id, target.id)
    await message.reply_text(
        f"🗑 تم مسح لقب {mention(target)}.",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 3) قائمة الرتب  (تستحوذ على الأمر بأولوية عالية)
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^قائمة\s+الرتب$"), group=-1)
async def list_titles(client: Client, message: Message):
    rds = client.redis
    titles = rds.hgetall(_titles_key(message.chat.id)) or {}

    if not titles:
        await message.reply_text("📭 لا توجد ألقاب مخصصة في هذه المجموعة.")
        await message.stop_propagation()
        return

    lines = [f"🏷 <b>قائمة الألقاب ({len(titles)}):</b>\n"]
    for i, (uid, title) in enumerate(titles.items(), 1):
        try:
            u = await client.get_users(int(uid))
            user_str = mention(u)
        except Exception:
            user_str = f"<code>{uid}</code>"
        lines.append(f"{i}. {user_str}  →  <b>{title}</b>")

    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    await message.stop_propagation()


# ============================================================
# 4) مسح الرتب  (تستحوذ على الأمر بأولوية عالية)
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^مسح\s+الرتب$"), group=-1)
async def clear_all_titles(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        await message.stop_propagation()
        return

    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        await message.stop_propagation()
        return

    rds.delete(_titles_key(chat_id))
    await message.reply_text("🗑 تم مسح جميع الألقاب في هذه المجموعة.")
    await message.stop_propagation()


# ============================================================
# 5) رتبتي  -> أظهر اللقب إن وُجد إضافة للرتبة الإدارية
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^لقبي$"))
async def my_title(client: Client, message: Message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    title = get_title(rds, chat_id, user_id)
    if not title:
        await message.reply_text("ℹ️ ليس لديك لقب مخصص.")
        return

    await message.reply_text(
        f"🏷 لقبك في هذه المجموعة : <b>{title}</b>",
        parse_mode=ParseMode.HTML,
    )
