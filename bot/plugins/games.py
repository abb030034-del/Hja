"""
plugins/games.py  (الجزء المالي)
==================================
نظام البنك والألعاب المالية :

• انشاء حساب بنكي / مسح حسابي / حسابي
• فلوسي / فلوس (بالرد)
• راتب          (كل 24 ساعة)
• بخشيش        (كل ساعة)
• كنز           (كل 6 ساعات - مبلغ عشوائي)
• استثمار فلوسي <مبلغ>   (كل 12 ساعة - ربح/خسارة عشوائية)
• حظ فلوسي <مبلغ>        (50/50 ضعف أو خسارة)
• زرف <مبلغ>    (بالرد) - تحويل بين أعضاء
• عجله <مبلغ> <لون>       - روليت (احمر/اسود/اخضر)
• تصفير البنك            (مطور)
"""

import time
import random
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks
from helpers.utils import extract_user, mention


# ====== إعدادات مالية ======
START_BALANCE   = 5000      # رصيد ابتدائي
SALARY_AMOUNT   = 10000     # الراتب اليومي
SALARY_CD       = 24 * 3600
TIP_MIN, TIP_MAX = 500, 3000
TIP_CD          = 3600
KANZ_MIN, KANZ_MAX = 1000, 20000
KANZ_CD         = 6 * 3600
INVEST_CD       = 12 * 3600

CURRENCY = "💰"


# ====== مفاتيح Redis ======
def _acc_key(uid):       return f"bank:acc:{uid}"            # hash
def _cd_key(uid, kind):  return f"bank:cd:{uid}:{kind}"      # str (ts)


# ====== أدوات حساب ======
def has_account(rds, uid) -> bool:
    return bool(rds.exists(_acc_key(uid)))


def create_account(rds, uid):
    rds.hset(_acc_key(uid), mapping={
        "balance": START_BALANCE,
        "created_at": int(time.time()),
    })


def get_balance(rds, uid) -> int:
    v = rds.hget(_acc_key(uid), "balance")
    return int(v) if v else 0


def add_balance(rds, uid, amount: int) -> int:
    return int(rds.hincrby(_acc_key(uid), "balance", amount))


def set_balance(rds, uid, amount: int):
    rds.hset(_acc_key(uid), "balance", int(amount))


def can_do(rds, uid, kind, cooldown) -> tuple:
    """يرجّع (ok, remaining_seconds)"""
    last = rds.get(_cd_key(uid, kind))
    if not last:
        return True, 0
    elapsed = int(time.time()) - int(last)
    if elapsed >= cooldown:
        return True, 0
    return False, cooldown - elapsed


def mark_done(rds, uid, kind):
    rds.set(_cd_key(uid, kind), int(time.time()))


def fmt_remaining(secs: int) -> str:
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    parts = []
    if h: parts.append(f"{h} ساعة")
    if m: parts.append(f"{m} دقيقة")
    if s and not h: parts.append(f"{s} ثانية")
    return " و ".join(parts) if parts else "ثانية"


def fmt_money(n: int) -> str:
    return f"{int(n):,}".replace(",", "٬")


# ====== Decorator-like guard ======
async def ensure_account(rds, message: Message) -> bool:
    uid = message.from_user.id
    if not has_account(rds, uid):
        await message.reply_text(
            "⚠️ ليس لديك حساب بنكي.\n\n"
            "اكتب : <code>انشاء حساب بنكي</code>",
            parse_mode=ParseMode.HTML,
        )
        return False
    return True


# ============================================================
# 1) انشاء حساب بنكي
# ============================================================
@Client.on_message(filters.regex(r"^انشاء\s+حساب\s+بنكي$"))
async def create_bank(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    if not u:
        return
    if has_account(rds, u.id):
        await message.reply_text("ℹ️ لديك حساب بنكي مسبقاً.")
        return

    create_account(rds, u.id)
    await message.reply_text(
        f"🎉 تم إنشاء حسابك البنكي بنجاح!\n"
        f"💵 رصيدك الابتدائي : <b>{fmt_money(START_BALANCE)} {CURRENCY}</b>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 2) مسح حسابي
# ============================================================
@Client.on_message(filters.regex(r"^مسح\s+حسابي$"))
async def delete_my_bank(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    if not u:
        return
    if not has_account(rds, u.id):
        await message.reply_text("ℹ️ لا تملك حساباً.")
        return

    rds.delete(_acc_key(u.id))
    for k in ("salary", "tip", "kanz", "invest"):
        rds.delete(_cd_key(u.id, k))
    await message.reply_text("🗑 تم مسح حسابك البنكي.")


# ============================================================
# 3) حسابي / فلوسي
# ============================================================
@Client.on_message(filters.regex(r"^(حسابي|فلوسي)$"))
async def my_account(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    if not u:
        return
    if not has_account(rds, u.id):
        await message.reply_text("⚠️ ليس لديك حساب. اكتب: <code>انشاء حساب بنكي</code>", parse_mode=ParseMode.HTML)
        return

    bal = get_balance(rds, u.id)
    created = int(rds.hget(_acc_key(u.id), "created_at") or 0)
    created_str = datetime.fromtimestamp(created).strftime("%Y-%m-%d") if created else "—"

    await message.reply_text(
        f"🏦 <b>حساب {mention(u)}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"💵 الرصيد : <b>{fmt_money(bal)} {CURRENCY}</b>\n"
        f"📅 تاريخ الإنشاء : <code>{created_str}</code>\n"
        f"━━━━━━━━━━━━",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 4) فلوس (بالرد)
# ============================================================
@Client.on_message(filters.regex(r"^فلوس$"))
async def show_others_money(client: Client, message: Message):
    rds = client.redis
    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم.")
        return
    if not has_account(rds, target.id):
        await message.reply_text(f"ℹ️ {mention(target)} ليس لديه حساب.", parse_mode=ParseMode.HTML)
        return

    bal = get_balance(rds, target.id)
    await message.reply_text(
        f"💵 رصيد {mention(target)} : <b>{fmt_money(bal)} {CURRENCY}</b>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 5) راتب  (24 ساعة)
# ============================================================
@Client.on_message(filters.regex(r"^راتب$"))
async def salary(client: Client, message: Message):
    rds = client.redis
    if not await ensure_account(rds, message):
        return
    uid = message.from_user.id

    ok, remain = can_do(rds, uid, "salary", SALARY_CD)
    if not ok:
        await message.reply_text(f"⏳ ستستلم الراتب التالي بعد : <b>{fmt_remaining(remain)}</b>", parse_mode=ParseMode.HTML)
        return

    new_bal = add_balance(rds, uid, SALARY_AMOUNT)
    mark_done(rds, uid, "salary")
    await message.reply_text(
        f"💼 تم استلام راتبك : <b>+{fmt_money(SALARY_AMOUNT)} {CURRENCY}</b>\n"
        f"💵 رصيدك الآن : <b>{fmt_money(new_bal)} {CURRENCY}</b>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 6) بخشيش  (ساعة)
# ============================================================
@Client.on_message(filters.regex(r"^بخشيش$"))
async def tip(client: Client, message: Message):
    rds = client.redis
    if not await ensure_account(rds, message):
        return
    uid = message.from_user.id

    ok, remain = can_do(rds, uid, "tip", TIP_CD)
    if not ok:
        await message.reply_text(f"⏳ البخشيش التالي بعد : <b>{fmt_remaining(remain)}</b>", parse_mode=ParseMode.HTML)
        return

    amount = random.randint(TIP_MIN, TIP_MAX)
    new_bal = add_balance(rds, uid, amount)
    mark_done(rds, uid, "tip")
    await message.reply_text(
        f"🎁 بخشيش : <b>+{fmt_money(amount)} {CURRENCY}</b>\n"
        f"💵 رصيدك : <b>{fmt_money(new_bal)} {CURRENCY}</b>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 7) كنز  (6 ساعات)
# ============================================================
@Client.on_message(filters.regex(r"^كنز$"))
async def treasure(client: Client, message: Message):
    rds = client.redis
    if not await ensure_account(rds, message):
        return
    uid = message.from_user.id

    ok, remain = can_do(rds, uid, "kanz", KANZ_CD)
    if not ok:
        await message.reply_text(f"⏳ الكنز التالي بعد : <b>{fmt_remaining(remain)}</b>", parse_mode=ParseMode.HTML)
        return

    amount = random.randint(KANZ_MIN, KANZ_MAX)
    new_bal = add_balance(rds, uid, amount)
    mark_done(rds, uid, "kanz")
    await message.reply_text(
        f"🪙 وجدت كنزاً : <b>+{fmt_money(amount)} {CURRENCY}</b>\n"
        f"💵 رصيدك : <b>{fmt_money(new_bal)} {CURRENCY}</b>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 8) استثمار فلوسي <مبلغ>  (12 ساعة)
# ============================================================
@Client.on_message(filters.regex(r"^استثمار\s+فلوسي\s+(\d+)$"))
async def invest(client: Client, message: Message):
    rds = client.redis
    if not await ensure_account(rds, message):
        return
    uid = message.from_user.id

    ok, remain = can_do(rds, uid, "invest", INVEST_CD)
    if not ok:
        await message.reply_text(f"⏳ استثمار جديد بعد : <b>{fmt_remaining(remain)}</b>", parse_mode=ParseMode.HTML)
        return

    amount = int(message.matches[0].group(1))
    bal = get_balance(rds, uid)
    if amount <= 0 or amount > bal:
        await message.reply_text("⚠️ مبلغ غير صالح.")
        return

    # عائد عشوائي : -30% إلى +60%
    pct = random.randint(-30, 60)
    profit = int(amount * pct / 100)
    new_bal = add_balance(rds, uid, profit)
    mark_done(rds, uid, "invest")

    sign = "+" if profit >= 0 else ""
    emoji = "📈" if profit > 0 else ("📉" if profit < 0 else "➖")
    await message.reply_text(
        f"{emoji} نتيجة الاستثمار : <b>{sign}{fmt_money(profit)} {CURRENCY}</b>  ({pct:+d}%)\n"
        f"💵 رصيدك الآن : <b>{fmt_money(new_bal)} {CURRENCY}</b>",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 9) حظ فلوسي <مبلغ>  (بدون cooldown)
# ============================================================
@Client.on_message(filters.regex(r"^حظ\s+فلوسي\s+(\d+)$"))
async def luck(client: Client, message: Message):
    rds = client.redis
    if not await ensure_account(rds, message):
        return
    uid = message.from_user.id
    amount = int(message.matches[0].group(1))
    bal = get_balance(rds, uid)
    if amount <= 0 or amount > bal:
        await message.reply_text("⚠️ مبلغ غير صالح.")
        return

    if random.random() < 0.5:
        new_bal = add_balance(rds, uid, amount)
        await message.reply_text(
            f"🍀 حظ جيد! ربحت <b>+{fmt_money(amount)} {CURRENCY}</b>\n"
            f"💵 رصيدك : <b>{fmt_money(new_bal)} {CURRENCY}</b>",
            parse_mode=ParseMode.HTML,
        )
    else:
        new_bal = add_balance(rds, uid, -amount)
        await message.reply_text(
            f"💔 حظ سيئ! خسرت <b>-{fmt_money(amount)} {CURRENCY}</b>\n"
            f"💵 رصيدك : <b>{fmt_money(new_bal)} {CURRENCY}</b>",
            parse_mode=ParseMode.HTML,
        )


# ============================================================
# 10) زرف <مبلغ>  (بالرد) — تحويل
# ============================================================
@Client.on_message(filters.regex(r"^زرف\s+(\d+)$"))
async def transfer(client: Client, message: Message):
    rds = client.redis
    if not await ensure_account(rds, message):
        return
    uid = message.from_user.id

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على المستخدم لتحويل المبلغ له.")
        return
    if target.id == uid:
        await message.reply_text("⚠️ لا يمكنك التحويل لنفسك.")
        return
    if target.is_bot:
        await message.reply_text("⚠️ لا يمكن التحويل للبوتات.")
        return
    if not has_account(rds, target.id):
        await message.reply_text(f"⚠️ {mention(target)} ليس لديه حساب.", parse_mode=ParseMode.HTML)
        return

    amount = int(message.matches[0].group(1))
    bal = get_balance(rds, uid)
    if amount <= 0 or amount > bal:
        await message.reply_text("⚠️ مبلغ غير صالح.")
        return

    add_balance(rds, uid, -amount)
    add_balance(rds, target.id, amount)
    await message.reply_text(
        f"💸 تم زرف <b>{fmt_money(amount)} {CURRENCY}</b> إلى {mention(target)}",
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# 11) عجله <مبلغ> <لون>  — روليت
# ============================================================
ROULETTE_COLORS = {
    "احمر": ("احمر 🔴", 1, 18),   # ربح ×2
    "أحمر": ("احمر 🔴", 1, 18),
    "اسود": ("اسود ⚫", 1, 18),
    "أسود": ("اسود ⚫", 1, 18),
    "اخضر": ("اخضر 🟢", 14, 1),    # ربح ×14
    "أخضر": ("اخضر 🟢", 14, 1),
}


@Client.on_message(filters.regex(r"^عجله\s+(\d+)\s+(\S+)$"))
async def roulette(client: Client, message: Message):
    rds = client.redis
    if not await ensure_account(rds, message):
        return
    uid = message.from_user.id

    amount = int(message.matches[0].group(1))
    color_input = message.matches[0].group(2).strip()

    if color_input not in ROULETTE_COLORS:
        await message.reply_text("⚠️ اختر : <b>احمر</b> أو <b>اسود</b> أو <b>اخضر</b>", parse_mode=ParseMode.HTML)
        return

    bal = get_balance(rds, uid)
    if amount <= 0 or amount > bal:
        await message.reply_text("⚠️ مبلغ غير صالح.")
        return

    # تطبيع اللون المختار
    if color_input in ("احمر", "أحمر"):
        chosen = "احمر"
    elif color_input in ("اسود", "أسود"):
        chosen = "اسود"
    else:
        chosen = "اخضر"

    # روليت : 18 احمر + 18 اسود + 1 اخضر = 37
    spin = random.randint(1, 37)
    if spin == 37:
        spin_color = "اخضر"
    elif spin <= 18:
        spin_color = "احمر"
    else:
        spin_color = "اسود"

    _, payout_mult, _ = ROULETTE_COLORS[chosen]
    spin_label, _, _ = ROULETTE_COLORS[spin_color]

    if spin_color == chosen:
        win = amount * payout_mult
        new_bal = add_balance(rds, uid, win)
        await message.reply_text(
            f"🎰 العجلة وقفت على : <b>{spin_label}</b>\n"
            f"🏆 ربحت <b>+{fmt_money(win)} {CURRENCY}</b>\n"
            f"💵 رصيدك : <b>{fmt_money(new_bal)} {CURRENCY}</b>",
            parse_mode=ParseMode.HTML,
        )
    else:
        new_bal = add_balance(rds, uid, -amount)
        await message.reply_text(
            f"🎰 العجلة وقفت على : <b>{spin_label}</b>\n"
            f"💔 خسرت <b>-{fmt_money(amount)} {CURRENCY}</b>\n"
            f"💵 رصيدك : <b>{fmt_money(new_bal)} {CURRENCY}</b>",
            parse_mode=ParseMode.HTML,
        )


# ============================================================
# 12) تصفير البنك  (مطور)
# ============================================================
@Client.on_message(filters.regex(r"^تصفير\s+البنك$"))
async def reset_bank(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    if not u or not Ranks.is_dev(u.id):
        await message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return

    deleted = 0
    for key in rds.scan_iter("bank:*"):
        rds.delete(key)
        deleted += 1

    await message.reply_text(f"🗑 تم تصفير البنك كلياً ({deleted} مفتاح).")
