"""
plugins/fun.py
===============
قوائم المتعة (ألقاب فكاهية):
  كيك / عسل / نصاب / حمار / بقرة / كلب / قرد / تيس /
  ثور / هكر / دجاجة / ملكة / صياد / خروف

لكل فئة:
  • رفع <الفئة>      (بالرد / يوزر / ايدي)
  • تنزيل <الفئة>    (بالرد / يوزر / ايدي)
  • قائمة <الفئة>   (الجميع)
  • مسح <الفئة>      (مدير+)
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks
from helpers.utils import extract_user, mention


# ====== الفئات المدعومة ======
# الكلمة المفردة (للأوامر) → (اسم فئة Redis، الصيغة بصيغة الجمع للعرض، إيموجي)
CATEGORIES = {
    "كيك":   ("kek",      "الكيكات",    "🍰"),
    "عسل":   ("asal",     "العسولات",   "🍯"),
    "نصاب":  ("nassab",   "النصابين",   "🥷"),
    "حمار":  ("hmar",     "الحمير",     "🐴"),
    "بقرة":  ("baqra",    "الأبقار",    "🐄"),
    "كلب":   ("kalb",     "الكلاب",     "🐶"),
    "قرد":   ("qard",     "القرود",     "🐒"),
    "تيس":   ("tees",     "التيوس",     "🐐"),
    "ثور":   ("thor",     "الثيران",    "🐂"),
    "هكر":   ("hacker",   "الهكرز",     "💻"),
    "دجاجة": ("dajaja",   "الدجاج",     "🐔"),
    "ملكة":  ("malika",   "الملكات",    "👑"),
    "صياد":  ("sayyad",   "الصيادين",   "🎣"),
    "خروف":  ("kharoof",  "الخراف",     "🐑"),
}


def _key(cat_id, chat_id):
    return f"fun:{cat_id}:{chat_id}"


def _normalize(word: str) -> str:
    """تطبيع همزات شائعة"""
    return (word or "").strip().replace("أ", "ا").replace("إ", "ا").replace("ة", "ه")
    # ملاحظة: لا نطبّق هذا التطبيع على القاموس بل نستخدم البحث المرن أدناه


def _resolve_category(word: str):
    """يبحث في القاموس بالكلمة كما هي وبصيغ مطبّعة بسيطة"""
    if not word:
        return None
    w = word.strip()
    if w in CATEGORIES:
        return w
    # طبّع التاء المربوطة والهمزات
    w_norm = w.replace("أ", "ا").replace("إ", "ا").replace("ة", "ه")
    for k in CATEGORIES.keys():
        k_norm = k.replace("أ", "ا").replace("إ", "ا").replace("ة", "ه")
        if w_norm == k_norm:
            return k
    return None


# نبني فلتر regex من أسماء الفئات لمطابقة دقيقة
_CAT_PATTERN = "|".join(CATEGORIES.keys())


# ============================================================
# 1) رفع <فئة>
# ============================================================
@Client.on_message(filters.group & filters.regex(rf"^رفع\s+([\u0600-\u06FF]+)(?:\s|$)"))
async def fun_raise(client: Client, message: Message):
    word = message.matches[0].group(1)
    cat = _resolve_category(word)
    if not cat:
        return  # ليس فئة من قوائم المتعة، نمرر للبلجنز الأخرى

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

    cat_id, plural, emoji = CATEGORIES[cat]
    if rds.sismember(_key(cat_id, chat_id), str(target.id)):
        await message.reply_text(f"ℹ️ {mention(target)} مُسجَّل ضمن {plural} مسبقاً.", parse_mode=ParseMode.HTML)
        return

    rds.sadd(_key(cat_id, chat_id), str(target.id))
    await message.reply_text(
        f"{emoji} تم رفع {mention(target)} إلى رتبة <b>{cat}</b>.",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 2) تنزيل <فئة>
# ============================================================
@Client.on_message(filters.group & filters.regex(rf"^تنزيل\s+([\u0600-\u06FF]+)(?:\s|$)"))
async def fun_demote(client: Client, message: Message):
    word = message.matches[0].group(1)
    cat = _resolve_category(word)
    if not cat:
        return

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

    cat_id, plural, emoji = CATEGORIES[cat]
    if not rds.sismember(_key(cat_id, chat_id), str(target.id)):
        await message.reply_text(f"ℹ️ {mention(target)} ليس ضمن {plural}.", parse_mode=ParseMode.HTML)
        return

    rds.srem(_key(cat_id, chat_id), str(target.id))
    await message.reply_text(
        f"{emoji} تم تنزيل {mention(target)} من رتبة <b>{cat}</b>.",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 3) قائمة <فئة>  (تدعم المفرد والجمع)
# ============================================================
# نقبل أيضاً صيغ الجمع التي خزّناها
_PLURAL_TO_CAT = {plural: cat for cat, (_, plural, _) in CATEGORIES.items()}


@Client.on_message(filters.group & filters.regex(r"^قائمة\s+(.+)$"))
async def fun_list(client: Client, message: Message):
    raw = message.matches[0].group(1).strip()

    cat = _resolve_category(raw) or _PLURAL_TO_CAT.get(raw)
    if not cat:
        return  # لتمرير "قائمة الرتب" وغيرها لمعالجاتها

    rds = client.redis
    chat_id = message.chat.id
    cat_id, plural, emoji = CATEGORIES[cat]
    members = rds.smembers(_key(cat_id, chat_id)) or set()

    if not members:
        await message.reply_text(f"📭 لا يوجد أعضاء في {plural}.")
        return

    lines = [f"{emoji} <b>قائمة {plural} ({len(members)}):</b>\n"]
    for i, uid in enumerate(sorted(members), 1):
        try:
            u = await client.get_users(int(uid))
            lines.append(f"{i}. {mention(u)}")
        except Exception:
            lines.append(f"{i}. <code>{uid}</code>")
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ============================================================
# 4) مسح <فئة>
# ============================================================
@Client.on_message(filters.group & filters.regex(r"^مسح\s+(.+)$"))
async def fun_clear(client: Client, message: Message):
    raw = message.matches[0].group(1).strip()
    cat = _resolve_category(raw) or _PLURAL_TO_CAT.get(raw)
    if not cat:
        return

    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return

    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return

    cat_id, plural, emoji = CATEGORIES[cat]
    rds.delete(_key(cat_id, chat_id))
    await message.reply_text(f"🗑 تم مسح جميع {plural}.")
