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

    # تتبّع للتوب
    rds.hincrby(f"bank:xfer:{uid}", "total", amount)
    rds.hincrby(f"bank:xfer:{uid}", "count", 1)

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



# =============================================================
# ====================  قسم التوب  =============================
# =============================================================

# ============ سرقة <بالرد>  (لتغذية توب الحراميه) ============
STEAL_CD = 3600

@Client.on_message(filters.regex(r"^سرقة$"))
async def steal(client: Client, message: Message):
    rds = client.redis
    if not await ensure_account(rds, message):
        return
    uid = message.from_user.id

    target = await extract_user(client, message)
    if not target:
        await message.reply_text("⚠️ يجب الرد على الضحية.")
        return
    if target.id == uid:
        await message.reply_text("⚠️ لا تسرق نفسك 😅")
        return
    if not has_account(rds, target.id):
        await message.reply_text("⚠️ الضحية ليس لديها حساب.")
        return

    ok, remain = can_do(rds, uid, "steal", STEAL_CD)
    if not ok:
        await message.reply_text(f"⏳ السرقة التالية بعد : <b>{fmt_remaining(remain)}</b>", parse_mode=ParseMode.HTML)
        return

    mark_done(rds, uid, "steal")

    victim_bal = get_balance(rds, target.id)
    if victim_bal < 1000:
        await message.reply_text("🪙 الضحية فقيرة جداً ، لا فائدة من سرقتها.")
        return

    success = random.random() < 0.45  # 45% نجاح
    if success:
        loot = random.randint(min(500, victim_bal), min(int(victim_bal * 0.30), 50000))
        add_balance(rds, uid, loot)
        add_balance(rds, target.id, -loot)
        rds.hincrby(f"bank:thefts:{uid}", "count", 1)
        rds.hincrby(f"bank:thefts:{uid}", "total", loot)
        await message.reply_text(
            f"🦹 نجحت السرقة! خطفت <b>+{fmt_money(loot)} {CURRENCY}</b> من {mention(target)}",
            parse_mode=ParseMode.HTML,
        )
    else:
        fine = random.randint(500, 3000)
        new_bal = add_balance(rds, uid, -fine)
        await message.reply_text(
            f"👮 تم القبض عليك! غرامة <b>-{fmt_money(fine)} {CURRENCY}</b>\n"
            f"💵 رصيدك : <b>{fmt_money(new_bal)} {CURRENCY}</b>",
            parse_mode=ParseMode.HTML,
        )


# ============ نظام الزواج البسيط ============
# marriage:{uid} = hash {spouse, since}
# marriage:proposal:{target_uid} = proposer_uid

def _marriage_key(uid): return f"marriage:{uid}"


@Client.on_message(filters.regex(r"^زواج$") & filters.reply)
async def propose(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    target_msg = message.reply_to_message
    if not u or not target_msg or not target_msg.from_user:
        return

    target = target_msg.from_user
    if target.id == u.id:
        await message.reply_text("⚠️ لا يمكنك الزواج من نفسك.")
        return
    if target.is_bot:
        await message.reply_text("⚠️ لا يمكن الزواج من بوت.")
        return
    if rds.exists(_marriage_key(u.id)):
        await message.reply_text("⚠️ أنت متزوج بالفعل.")
        return
    if rds.exists(_marriage_key(target.id)):
        await message.reply_text(f"⚠️ {mention(target)} متزوج/ـة بالفعل.", parse_mode=ParseMode.HTML)
        return

    rds.set(f"marriage:proposal:{target.id}", str(u.id), ex=300)  # 5 دقائق
    await message.reply_text(
        f"💍 {mention(u)} يعرض الزواج على {mention(target)}\n"
        f"للقبول اكتب : <code>قبول الزواج</code>\n"
        f"للرفض اكتب : <code>رفض الزواج</code>",
        parse_mode=ParseMode.HTML,
    )


@Client.on_message(filters.regex(r"^قبول\s+الزواج$"))
async def accept_marriage(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    if not u:
        return
    proposer_id = rds.get(f"marriage:proposal:{u.id}")
    if not proposer_id:
        await message.reply_text("ℹ️ لا يوجد عرض زواج لك.")
        return

    if rds.exists(_marriage_key(u.id)):
        await message.reply_text("⚠️ أنت متزوج بالفعل.")
        return

    now = int(time.time())
    rds.hset(_marriage_key(u.id), mapping={"spouse": proposer_id, "since": now})
    rds.hset(_marriage_key(int(proposer_id)), mapping={"spouse": str(u.id), "since": now})
    rds.delete(f"marriage:proposal:{u.id}")

    try:
        sp = await client.get_users(int(proposer_id))
        await message.reply_text(
            f"💒 مبروك ! تم زواج {mention(u)} من {mention(sp)} 🎉",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await message.reply_text("💒 تم الزواج بنجاح !")


@Client.on_message(filters.regex(r"^رفض\s+الزواج$"))
async def reject_marriage(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    if not u:
        return
    if not rds.exists(f"marriage:proposal:{u.id}"):
        await message.reply_text("ℹ️ لا يوجد عرض زواج لك.")
        return
    rds.delete(f"marriage:proposal:{u.id}")
    await message.reply_text("💔 تم رفض الزواج.")


@Client.on_message(filters.regex(r"^طلاق$"))
async def divorce(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    if not u:
        return
    if not rds.exists(_marriage_key(u.id)):
        await message.reply_text("ℹ️ أنت لست متزوجاً أصلاً.")
        return
    sp_id = rds.hget(_marriage_key(u.id), "spouse")
    rds.delete(_marriage_key(u.id))
    if sp_id:
        rds.delete(_marriage_key(int(sp_id)))
    await message.reply_text("💔 تم الطلاق.")


@Client.on_message(filters.regex(r"^زواجي$"))
async def my_marriage(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    if not u:
        return
    if not rds.exists(_marriage_key(u.id)):
        await message.reply_text("ℹ️ أنت لست متزوجاً.")
        return

    sp_id = int(rds.hget(_marriage_key(u.id), "spouse") or 0)
    since = int(rds.hget(_marriage_key(u.id), "since") or 0)
    since_str = datetime.fromtimestamp(since).strftime("%Y-%m-%d") if since else "—"

    try:
        sp = await client.get_users(sp_id)
        sp_str = mention(sp)
    except Exception:
        sp_str = f"<code>{sp_id}</code>"

    await message.reply_text(
        f"💑 <b>زواجك</b>\n"
        f"━━━━━━━━━━━━\n"
        f"• الشريك : {sp_str}\n"
        f"• منذ : <code>{since_str}</code>",
        parse_mode=ParseMode.HTML,
    )


# ============ توب الفلوس ============
async def _build_top(client, rds, score_for_key: str, limit=10):
    """يبني قائمة Top بناءً على hash field=value لكل user."""
    pairs = []
    if score_for_key == "balance":
        for key in rds.scan_iter("bank:acc:*"):
            uid = key.split(":")[-1]
            bal = int(rds.hget(key, "balance") or 0)
            pairs.append((int(uid), bal))
    elif score_for_key == "thefts":
        for key in rds.scan_iter("bank:thefts:*"):
            uid = key.split(":")[-1]
            cnt = int(rds.hget(key, "count") or 0)
            pairs.append((int(uid), cnt))
    elif score_for_key == "xfer":
        for key in rds.scan_iter("bank:xfer:*"):
            uid = key.split(":")[-1]
            total = int(rds.hget(key, "total") or 0)
            pairs.append((int(uid), total))

    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:limit]


async def _format_top(client, pairs, title, unit, emoji="🏆"):
    if not pairs:
        return f"📭 لا توجد بيانات لـ {title}."
    lines = [f"{emoji} <b>{title}</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, score) in enumerate(pairs):
        rank = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        try:
            u = await client.get_users(uid)
            name = mention(u)
        except Exception:
            name = f"<code>{uid}</code>"
        lines.append(f"{rank}  {name} — <b>{fmt_money(score)}</b> {unit}")
    return "\n".join(lines)


@Client.on_message(filters.regex(r"^توب\s+الفلوس$"))
async def top_money(client: Client, message: Message):
    rds = client.redis
    pairs = await _build_top(client, rds, "balance")
    text = await _format_top(client, pairs, "توب الفلوس", CURRENCY, "💰")
    await message.reply_text(text, parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^توب\s+الحراميه$"))
async def top_thieves(client: Client, message: Message):
    rds = client.redis
    pairs = await _build_top(client, rds, "thefts")
    text = await _format_top(client, pairs, "توب الحراميه", "سرقة", "🦹")
    await message.reply_text(text, parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^توب\s+الزرف$"))
async def top_transfers(client: Client, message: Message):
    rds = client.redis
    pairs = await _build_top(client, rds, "xfer")
    text = await _format_top(client, pairs, "توب الزرف", CURRENCY, "💸")
    await message.reply_text(text, parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^توب\s+الزواجات$"))
async def top_marriages(client: Client, message: Message):
    rds = client.redis
    pairs = []
    seen = set()
    for key in rds.scan_iter("marriage:[0-9-]*"):
        uid = key.split(":")[-1]
        if not uid.lstrip("-").isdigit():
            continue
        uid = int(uid)
        if uid in seen:
            continue
        sp = rds.hget(key, "spouse")
        since = int(rds.hget(key, "since") or 0)
        if not sp:
            continue
        sp = int(sp)
        seen.add(uid)
        seen.add(sp)
        pairs.append((uid, sp, since))

    pairs.sort(key=lambda x: x[2])  # الأقدم أولاً

    if not pairs:
        await message.reply_text("📭 لا توجد زواجات بعد.")
        return

    lines = ["💑 <b>توب الزواجات (الأقدم أولاً)</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, (a, b, since) in enumerate(pairs[:10]):
        rank = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        date = datetime.fromtimestamp(since).strftime("%Y-%m-%d") if since else "—"
        try:
            ua = await client.get_users(a); ub = await client.get_users(b)
            line = f"{rank}  {mention(ua)}  ❤️  {mention(ub)}  — <code>{date}</code>"
        except Exception:
            line = f"{rank}  <code>{a}</code> ❤️ <code>{b}</code> — <code>{date}</code>"
        lines.append(line)

    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


@Client.on_message(filters.regex(r"^زواجات$"))
async def list_marriages(client: Client, message: Message):
    """نفس فكرة توب الزواجات لكن بدون ترتيب الأقدم"""
    rds = client.redis
    pairs = []
    seen = set()
    for key in rds.scan_iter("marriage:[0-9-]*"):
        uid = key.split(":")[-1]
        if not uid.lstrip("-").isdigit():
            continue
        uid = int(uid)
        if uid in seen:
            continue
        sp = rds.hget(key, "spouse")
        if not sp:
            continue
        sp = int(sp)
        seen.add(uid); seen.add(sp)
        pairs.append((uid, sp))

    if not pairs:
        await message.reply_text("📭 لا توجد زواجات حالياً.")
        return

    lines = [f"💍 <b>قائمة الزواجات ({len(pairs)}):</b>\n"]
    for i, (a, b) in enumerate(pairs, 1):
        try:
            ua = await client.get_users(a); ub = await client.get_users(b)
            line = f"{i}. {mention(ua)} ❤️ {mention(ub)}"
        except Exception:
            line = f"{i}. <code>{a}</code> ❤️ <code>{b}</code>"
        lines.append(line)
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ============ توب (نظرة عامة) ============
@Client.on_message(filters.regex(r"^توب$"))
async def top_overview(client: Client, message: Message):
    rds = client.redis
    sections = []

    # توب الفلوس - أعلى 3
    money = await _build_top(client, rds, "balance", limit=3)
    if money:
        sections.append("💰 <b>توب الفلوس:</b>")
        for i, (uid, sc) in enumerate(money):
            try:
                u = await client.get_users(uid); name = mention(u)
            except Exception:
                name = f"<code>{uid}</code>"
            sections.append(f"{['🥇','🥈','🥉'][i]} {name} — {fmt_money(sc)} {CURRENCY}")

    # توب الحراميه
    thefts = await _build_top(client, rds, "thefts", limit=3)
    if thefts:
        sections.append("\n🦹 <b>توب الحراميه:</b>")
        for i, (uid, sc) in enumerate(thefts):
            try:
                u = await client.get_users(uid); name = mention(u)
            except Exception:
                name = f"<code>{uid}</code>"
            sections.append(f"{['🥇','🥈','🥉'][i]} {name} — {fmt_money(sc)} سرقة")

    if not sections:
        await message.reply_text("📭 لا توجد بيانات بعد.")
        return

    await message.reply_text("🏆 <b>التوب العام</b>\n━━━━━━━━━━━━\n" + "\n".join(sections), parse_mode=ParseMode.HTML)


# ============ تصفير التوب (مطور) ============
@Client.on_message(filters.regex(r"^تصفير\s+التوب$"))
async def reset_top(client: Client, message: Message):
    rds = client.redis
    u = message.from_user
    if not u or not Ranks.is_dev(u.id):
        await message.reply_text("⛔ هذا الأمر للمطور فقط.")
        return

    deleted = 0
    for pat in ("bank:thefts:*", "bank:xfer:*"):
        for key in rds.scan_iter(pat):
            rds.delete(key); deleted += 1
    await message.reply_text(f"🗑 تم تصفير التوب ({deleted} مفتاح).")



# =============================================================
# ==================  الألعاب النصية (المرحلة 11)  ============
# =============================================================
from helpers import games_data as GD


def _active_key(chat_id): return f"game:active:{chat_id}"
def _score_key(chat_id):  return f"game:score:{chat_id}"

GAME_POINTS = {
    "capitals": 3, "scramble": 2, "complete": 2, "english": 2,
    "arabic": 2, "meaning": 4, "math": 2, "emoji": 2, "sentence": 4,
    "dismantle": 3,
}
GAME_TIMEOUT = 60  # ثانية


def _start_game(rds, chat_id, gtype, answer, hint=""):
    rds.hset(_active_key(chat_id), mapping={
        "type": gtype, "answer": str(answer),
        "hint": str(hint), "start_at": int(time.time()),
    })
    rds.expire(_active_key(chat_id), GAME_TIMEOUT * 2)


def _get_active(rds, chat_id):
    d = rds.hgetall(_active_key(chat_id))
    if not d: return None
    if int(time.time()) - int(d.get("start_at", 0)) > GAME_TIMEOUT:
        rds.delete(_active_key(chat_id))
        return None
    return d


def _add_score(rds, chat_id, uid, pts):
    rds.hincrby(_score_key(chat_id), str(uid), pts)


# كلمات
@Client.on_message(filters.group & filters.regex(r"^كلمات$"))
async def game_scramble(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة.")
        return
    word = random.choice(GD.SCRAMBLE_WORDS)
    letters = list(word); random.shuffle(letters)
    _start_game(rds, message.chat.id, "scramble", word)
    await message.reply_text(
        f"🔤 <b>كلمات</b> — أعد ترتيب الحروف:\n\n<code>{' '.join(letters)}</code>\n\nلديك {GAME_TIMEOUT}ث.",
        parse_mode=ParseMode.HTML,
    )


# عواصم
@Client.on_message(filters.group & filters.regex(r"^عواصم$"))
async def game_capitals(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة."); return
    country, capital = random.choice(list(GD.CAPITALS.items()))
    _start_game(rds, message.chat.id, "capitals", capital)
    await message.reply_text(f"🏛 <b>عواصم</b> — ما عاصمة <b>{country}</b> ؟", parse_mode=ParseMode.HTML)


# اكمل
@Client.on_message(filters.group & filters.regex(r"^اكمل$"))
async def game_complete(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة."); return
    word = random.choice(GD.SCRAMBLE_WORDS)
    idx = random.randint(1, len(word)-1)
    hidden = word[:idx] + "_" + word[idx+1:]
    _start_game(rds, message.chat.id, "complete", word)
    await message.reply_text(f"✏️ <b>اكمل</b> — أكمل الكلمة:\n\n<code>{hidden}</code>", parse_mode=ParseMode.HTML)


# انقليزي
@Client.on_message(filters.group & filters.regex(r"^انقليزي$"))
async def game_english(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة."); return
    en, ar = random.choice(list(GD.EN_TO_AR.items()))
    _start_game(rds, message.chat.id, "english", ar)
    await message.reply_text(f"🌍 <b>انقليزي</b> — ما معنى <b>{en}</b> بالعربي ؟", parse_mode=ParseMode.HTML)


# عربي
@Client.on_message(filters.group & filters.regex(r"^عربي$"))
async def game_arabic(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة."); return
    en, ar = random.choice(list(GD.EN_TO_AR.items()))
    _start_game(rds, message.chat.id, "arabic", en)
    await message.reply_text(f"🌍 <b>عربي</b> — ما ترجمة <b>{ar}</b> للإنجليزية ؟", parse_mode=ParseMode.HTML)


# معاني
@Client.on_message(filters.group & filters.regex(r"^معاني$"))
async def game_meaning(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة."); return
    word = random.choice(list(GD.MEANINGS.keys()))
    meaning = GD.MEANINGS[word]
    _start_game(rds, message.chat.id, "meaning", word, hint=meaning)
    await message.reply_text(f"📖 <b>معاني</b> — ما الكلمة التي معناها:\n\n<i>{meaning}</i>", parse_mode=ParseMode.HTML)


# احسب
@Client.on_message(filters.group & filters.regex(r"^احسب$"))
async def game_math(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة."); return
    a, b = random.randint(2, 50), random.randint(2, 50)
    op = random.choice(["+", "-", "×"])
    answer = {"+": a+b, "-": a-b, "×": a*b}[op]
    _start_game(rds, message.chat.id, "math", answer)
    await message.reply_text(f"🧮 <b>احسب</b> — كم يساوي <b>{a} {op} {b}</b> ؟", parse_mode=ParseMode.HTML)


# ايموجي
@Client.on_message(filters.group & filters.regex(r"^ايموجي$"))
async def game_emoji(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة."); return
    emoji, ans = random.choice(list(GD.EMOJI_QUIZ.items()))
    _start_game(rds, message.chat.id, "emoji", ans)
    await message.reply_text(f"🎯 <b>ايموجي</b> — ماذا يعني هذا : {emoji}", parse_mode=ParseMode.HTML)


# جمل
@Client.on_message(filters.group & filters.regex(r"^جمل$"))
async def game_sentence(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة."); return
    s = random.choice(GD.SENTENCES)
    words = s.split(); random.shuffle(words)
    _start_game(rds, message.chat.id, "sentence", s)
    await message.reply_text(
        f"📝 <b>جمل</b> — أعد ترتيب الجملة:\n\n<code>{' | '.join(words)}</code>",
        parse_mode=ParseMode.HTML,
    )


# تفكيك
@Client.on_message(filters.group & filters.regex(r"^تفكيك$"))
async def game_dismantle(client, message):
    rds = client.redis
    if _get_active(rds, message.chat.id):
        await message.reply_text("⚠️ توجد لعبة نشطة."); return
    word = random.choice(GD.SCRAMBLE_WORDS)
    hidden = word[0] + "_" * (len(word) - 1)
    _start_game(rds, message.chat.id, "dismantle", word, hint=hidden)
    await message.reply_text(
        f"🧩 <b>تفكيك</b> — خمّن الكلمة:\n\n<code>{hidden}</code>\n(عدد الحروف: {len(word)})",
        parse_mode=ParseMode.HTML,
    )


# كت / تويت (نرد)
@Client.on_message(filters.group & filters.regex(r"^(كت|تويت)$"))
async def game_dice(client, message):
    name = message.matches[0].group(1)
    msg = await client.send_dice(message.chat.id, emoji="🎲")
    val = msg.dice.value if msg.dice else "?"
    await message.reply_text(f"🎲 <b>{name}</b> — النتيجة : <b>{val}</b>", parse_mode=ParseMode.HTML)


# الغاء اللعبه
@Client.on_message(filters.group & filters.regex(r"^الغاء\s+اللعبه$"))
async def cancel_game(client, message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    if not user_id: return
    if not _get_active(rds, message.chat.id):
        await message.reply_text("ℹ️ لا توجد لعبة نشطة."); return
    if not Ranks.admin_pls(rds, user_id, message.chat.id):
        await message.reply_text("⛔ هذا الأمر للأدمن أو أعلى."); return
    rds.delete(_active_key(message.chat.id))
    await message.reply_text("🛑 تم إلغاء اللعبة.")


# ترتيب (لوحة الصدارة)
@Client.on_message(filters.group & filters.regex(r"^ترتيب$"))
async def game_leaderboard(client, message):
    rds = client.redis
    scores = rds.hgetall(_score_key(message.chat.id)) or {}
    if not scores:
        await message.reply_text("📭 لا توجد نقاط بعد."); return
    pairs = sorted(((int(u), int(p)) for u, p in scores.items()), key=lambda x: x[1], reverse=True)[:10]
    lines = ["🏆 <b>ترتيب اللاعبين:</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, p) in enumerate(pairs):
        rank = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        try:
            u = await client.get_users(uid); name = mention(u)
        except Exception:
            name = f"<code>{uid}</code>"
        lines.append(f"{rank} {name} — <b>{p}</b> نقطة")
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# محرّك التحقق من الإجابات
@Client.on_message(filters.group & filters.text & ~filters.via_bot, group=2)
async def game_answer_engine(client, message):
    if not message.from_user or not message.text: return
    rds = client.redis
    chat_id = message.chat.id

    active = _get_active(rds, chat_id)
    if not active: return

    answer = (active.get("answer", "") or "").strip().lower()
    user_text = message.text.strip().lower()
    if user_text == answer:
        gtype = active.get("type", "")
        pts = GAME_POINTS.get(gtype, 1)
        _add_score(rds, chat_id, message.from_user.id, pts)
        rds.delete(_active_key(chat_id))
        await message.reply_text(
            f"✅ إجابة صحيحة! +{pts} نقاط لـ {mention(message.from_user)}",
            parse_mode=ParseMode.HTML,
        )


# سورس / استخراج الاكواد
@Client.on_message(filters.regex(r"^(سورس|استخراج\s+الاكواد)$"))
async def source_info(client, message):
    text = (
        "📦 <b>السورس</b>\n"
        "━━━━━━━━━━━━\n"
        "• اللغة : Python\n"
        "• المكتبة : Pyrogram + Redis\n"
        f"• المطور : <a href=\"tg://user?id={config.Dev_Zaid}\">Dev</a>\n"
        "━━━━━━━━━━━━"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
