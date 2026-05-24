"""
plugins/help.py
================
أمر <الاوامر> — يعرض كل أوامر البوت بطريقة عصرية تفاعلية
عبر InlineKeyboard مقسّمة على فئات.
"""

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)


# ===== كل قائمة (مفتاح → (اسم بالعربي، إيموجي، نص الأوامر)) =====
CATEGORIES = {
    "ranks": ("الرتب والصلاحيات", "🎖", """
• <code>رفع/تنزيل مطور مساعد | مشغل</code>
• <code>رفع/تنزيل مالك اساسي | مالك | مدير | ادمن | مميز</code>
• <code>قائمة المطورين/المالكين/المدراء/الادمنية/المميزين</code>
• <code>تفعيل/تعطيل الرفع</code>
• <code>تنزيل الكل</code>
• <code>رتبتي / رتبة (بالرد)</code>
• <code>تغيير رتبة &lt;اسم&gt;</code>
• <code>مسح المالكين/المدراء/...</code>
• <code>حذف الرتب العامة / حذف جميع الرتب</code>
"""),
    "group": ("إدارة المجموعة", "💬", """
• <code>تفعيل البوت / تعطيل البوت</code>
• <code>اطلع / البوت اطلع</code>
• <code>المطور / مطور البوت</code>
• <code>القوانين / وضع القوانين / مسح القوانين</code>
• <code>الترحيب / وضع الترحيب / مسح الترحيب</code>
"""),
    "mute": ("الكتم والحظر", "🔇", """
• <code>كتم / الغاء الكتم</code>   (بالرد)
• <code>كتم عام / الغاء الكتم العام</code>
• <code>حظر عام / الغاء الحظر العام</code>
• <code>حظر عام من الالعاب / الغاء الحظر العام من الالعاب</code>
"""),
    "filters": ("الردود", "💬", """
<b>ردود المجموعة:</b>
• <code>اضف رد &lt;كلمة&gt;</code>  (بالرد)
• <code>مسح رد &lt;كلمة&gt; / الردود / مسح الردود</code>
• <code>تفعيل/تعطيل الردود</code>

<b>ردود الأعضاء:</b>
• <code>اضف ردي / مسح ردي / ردود الاعضاء</code>
• <code>تفعيل/تعطيل ردود الاعضاء</code>

<b>الردود المميزة:</b>
• <code>اضف رد مميز / مسح رد مميز / الردود المميزه</code>

<b>الردود العامة:</b>
• <code>اضف رد عام / مسح رد عام / الردود العامه / مسح الردود العامه</code>
• <code>اضف/مسح رد متعدد عام</code>
• <code>تفعيل/تعطيل ردود المطور</code>
"""),
    "commands": ("أوامر مخصصة", "⚙️", """
• <code>تغيير امر &lt;الأصلي&gt; الى &lt;الجديد&gt;</code>
• <code>اضف امر &lt;الجديد&gt; + &lt;الأصلي&gt;</code>
• <code>حذف امر &lt;الجديد&gt; / الاوامر المضافه</code>
• <code>قفل امر &lt;الأمر&gt; / فتح امر &lt;الأمر&gt;</code>
• <code>الاوامر المقفله / فتح كل الاوامر</code>
"""),
    "titles": ("ألقاب الأعضاء", "🏷", """
• <code>تغيير رتبه &lt;لقب&gt;</code>  (بالرد)
• <code>مسح رتبه</code>  (بالرد)
• <code>قائمة الرتب / مسح الرتب</code>
• <code>لقبي</code>
"""),
    "fun_lists": ("قوائم المتعة", "🎭", """
الفئات: كيك، عسل، نصاب، حمار، بقرة، كلب، قرد، تيس، ثور، هكر، دجاجة، ملكة، صياد، خروف
• <code>رفع/تنزيل &lt;فئة&gt;</code>  (بالرد)
• <code>قائمة &lt;فئة&gt;</code>
• <code>مسح &lt;فئة&gt;</code>
"""),
    "tools": ("أدوات سريعة", "🛠", """
• <code>بنق / ping</code>
• <code>الايدي / يوزر / معرف &lt;يوزر&gt;</code>
• <code>ايدي المجموعه / ايدي القناه</code>
• <code>معلوماتي / معلومات (بالرد)</code>
• <code>صورتي / المجموعه / عدد الاعضاء</code>
• <code>الوقت / التاريخ</code>
• <code>ام (بالرد) - مدير+</code>
• <code>معلومات البوت</code>
"""),
    "bank": ("البنك", "🏦", """
• <code>انشاء حساب بنكي / مسح حسابي / حسابي</code>
• <code>فلوسي / فلوس (بالرد)</code>
• <code>راتب (24س) / بخشيش (1س) / كنز (6س)</code>
• <code>استثمار فلوسي &lt;مبلغ&gt; (12س)</code>
• <code>حظ فلوسي &lt;مبلغ&gt;</code>
• <code>زرف &lt;مبلغ&gt; (بالرد)</code>
• <code>عجله &lt;مبلغ&gt; احمر/اسود/اخضر</code>
• <code>سرقة (بالرد)</code>
"""),
    "marriage": ("الزواج", "💍", """
• <code>زواج (بالرد)</code>
• <code>قبول الزواج / رفض الزواج</code>
• <code>طلاق / زواجي / زواجات</code>
"""),
    "tops": ("التوب", "🏆", """
• <code>توب / توب الفلوس / توب الحراميه</code>
• <code>توب الزرف / توب الزواجات</code>
• <code>تصفير التوب</code>  (مطور)
"""),
    "games": ("الألعاب النصية", "🎮", """
• <code>كلمات / عواصم / اكمل</code>
• <code>انقليزي / عربي / معاني / احسب</code>
• <code>ايموجي / جمل / تفكيك</code>
• <code>كت / تويت</code>  (نرد)
• <code>ترتيب</code>  (ليدربورد)
• <code>الغاء اللعبه</code>  (أدمن+)
"""),
    "fun": ("الترفيه", "✨", """
• <code>صارحني (بالرد) / تفعيل صارحني / تعطيل صارحني</code>
• <code>وسمسة &lt;نص&gt; (بالرد)</code>
• <code>استبدال &lt;قديم&gt; الى &lt;جديد&gt; / استبدالات / مسح استبدال</code>
"""),
    "download": ("التحميل والقرآن", "📥", """
• <code>تحميل / يوتيوب &lt;كلمة/رابط&gt;</code>
• <code>صوت &lt;كلمة/رابط&gt;</code>
• <code>قرآن &lt;سورة&gt; [قارئ]</code>
• <code>القرّاء / ميم / ميمز</code>
• <code>تفعيل/تعطيل التحميل</code>  (مدير+)
"""),
    "admin": ("لوحة المشغّل (Private)", "🛡", """
• <code>/start</code>  (خاص)
• <code>الاحصائيات / معلومات السيرفر</code>
• <code>المحظورين / المكتومين</code>
• <code>اذاعة بالقروبات (بالرد)</code>
• <code>اذاعة بالخاص (بالرد)</code>
• <code>تعيين اسم البوت / رمز البوت / قناة البوت / مجموعة المطور</code>  (مطور)
• <code>تغيير المطور &lt;id&gt; / تحديث</code>  (مطور)
• <code>جلب نسخة القروبات / جلب نسخة المستخدمين</code>  (مطور)
"""),
}


# ============ الواجهة ============
def build_main():
    btns = []
    keys = list(CATEGORIES.keys())
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i:i+2]:
            name, emoji, _ = CATEGORIES[k]
            row.append(InlineKeyboardButton(f"{emoji} {name}", callback_data=f"help:{k}"))
        btns.append(row)
    btns.append([InlineKeyboardButton("❌ إغلاق", callback_data="help:close")])
    return InlineKeyboardMarkup(btns)


HEADER = (
    "🤖 <b>أوامر البوت</b>\n"
    "━━━━━━━━━━━━\n"
    "اختر فئة لعرض أوامرها:\n"
    "━━━━━━━━━━━━"
)


@Client.on_message(filters.regex(r"^(الاوامر|الأوامر|أوامر|اوامر|الاوامر؟)$"))
async def show_help(client, message: Message):
    await message.reply_text(
        HEADER,
        parse_mode=ParseMode.HTML,
        reply_markup=build_main(),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^help:(.+)$"))
async def help_callback(client, query: CallbackQuery):
    key = query.matches[0].group(1)

    if key == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.answer()
        return

    if key == "main":
        await query.message.edit_text(
            HEADER,
            parse_mode=ParseMode.HTML,
            reply_markup=build_main(),
            disable_web_page_preview=True,
        )
        await query.answer()
        return

    cat = CATEGORIES.get(key)
    if not cat:
        await query.answer("⚠️ غير موجود.", show_alert=True)
        return

    name, emoji, body = cat
    text = f"{emoji} <b>{name}</b>\n━━━━━━━━━━━━{body}━━━━━━━━━━━━"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع", callback_data="help:main"),
         InlineKeyboardButton("❌ إغلاق", callback_data="help:close")],
    ])
    try:
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        pass
    await query.answer()
