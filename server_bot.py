#!/usr/bin/env python3
"""
🤖 Telegram Server Manager Bot
يتحكم في السيرفر عبر Telegram
"""

import subprocess
import psutil
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# ============================================================
# ⚙️  الإعدادات — غيّر هذه القيم فقط
# ============================================================
BOT_TOKEN   = "l8836414433:AAG4ZvSVE7AL0DetYAC8_DAFUuoQyYJ0EII"   # توكن البوت من @BotFather
ALLOWED_IDS = [8588392906]             # Telegram user IDs المسموح لهم
# ============================================================


# ── حماية: تحقق من هوية المستخدم ──────────────────────────
def is_allowed(update: Update) -> bool:
    uid = (update.effective_user or update.callback_query.from_user).id
    return uid in ALLOWED_IDS


# ── مساعد: تنفيذ أمر shell ────────────────────────────────
def run(cmd: str, timeout: int = 15) -> str:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = (result.stdout + result.stderr).strip()
        return out[:3500] if out else "✅ تم التنفيذ (لا يوجد مخرجات)"
    except subprocess.TimeoutExpired:
        return "⏰ انتهت مهلة الأمر"
    except Exception as e:
        return f"❌ خطأ: {e}"


# ══════════════════════════════════════════════════════════════
#  /start  — القائمة الرئيسية
# ══════════════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("⛔ غير مصرح لك.")
        return

    kb = [
        [InlineKeyboardButton("📋 عرض السيرفيسات",   callback_data="list_services"),
         InlineKeyboardButton("📊 موارد السيرفر",    callback_data="resources")],
        [InlineKeyboardButton("🔍 حالة سيرفيس",      callback_data="status_menu"),
         InlineKeyboardButton("▶️ تشغيل سيرفيس",    callback_data="start_menu")],
        [InlineKeyboardButton("⏹️ إيقاف سيرفيس",    callback_data="stop_menu"),
         InlineKeyboardButton("🔄 إعادة تشغيل",     callback_data="restart_menu")],
        [InlineKeyboardButton("🐳 Docker Containers", callback_data="docker_list"),
         InlineKeyboardButton("📁 مساحة القرص",      callback_data="disk")],
        [InlineKeyboardButton("🔌 البورتات المفتوحة", callback_data="ports"),
         InlineKeyboardButton("📝 آخر السجلات",      callback_data="logs_menu")],
    ]
    await update.message.reply_text(
        "🖥️ *مرحباً بك في مدير السيرفر*\n\nاختر ما تريد:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════
#  معالج الأزرار
# ══════════════════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(update):
        await query.edit_message_text("⛔ غير مصرح لك.")
        return

    data = query.data
    back_btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]

    # ── موارد السيرفر ─────────────────────────────────────
    if data == "resources":
        cpu  = psutil.cpu_percent(interval=1)
        ram  = psutil.virtual_memory()
        swap = psutil.swap_memory()
        load = os.getloadavg()

        bar = lambda p: "█" * int(p/10) + "░" * (10 - int(p/10))

        msg = (
            f"📊 *موارد السيرفر*\n\n"
            f"🔹 CPU:  `{cpu:.1f}%`  {bar(cpu)}\n"
            f"🔹 RAM:  `{ram.percent:.1f}%`  {bar(ram.percent)}\n"
            f"   المستخدم: `{ram.used/1e9:.2f} GB` / `{ram.total/1e9:.2f} GB`\n"
            f"🔹 Swap: `{swap.percent:.1f}%`\n"
            f"🔹 Load: `{load[0]:.2f}` `{load[1]:.2f}` `{load[2]:.2f}`\n"
        )
        await query.edit_message_text(msg, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(back_btn))

    # ── قائمة السيرفيسات النشطة ───────────────────────────
    elif data == "list_services":
        out = run("systemctl list-units --type=service --state=running --no-pager --no-legend | awk '{print $1}' | head -30")
        await query.edit_message_text(
            f"📋 *السيرفيسات النشطة:*\n```\n{out}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_btn)
        )

    # ── مساحة القرص ───────────────────────────────────────
    elif data == "disk":
        out = run("df -h --output=target,size,used,avail,pcent | head -15")
        await query.edit_message_text(
            f"📁 *مساحة القرص:*\n```\n{out}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_btn)
        )

    # ── البورتات المفتوحة ──────────────────────────────────
    elif data == "ports":
        out = run("ss -tlnp | grep LISTEN")
        await query.edit_message_text(
            f"🔌 *البورتات المفتوحة:*\n```\n{out}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_btn)
        )

    # ── Docker ─────────────────────────────────────────────
    elif data == "docker_list":
        out = run("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo 'Docker غير مثبت أو لا يوجد containers'")
        await query.edit_message_text(
            f"🐳 *Docker Containers:*\n```\n{out}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_btn)
        )

    # ── قوائم الأوامر (حالة / تشغيل / إيقاف / restart) ───
    elif data in ("status_menu", "start_menu", "stop_menu", "restart_menu", "logs_menu"):
        prompts = {
            "status_menu":  ("🔍 حالة سيرفيس", "status",  "service_status"),
            "start_menu":   ("▶️ تشغيل",        "start",   "service_start"),
            "stop_menu":    ("⏹️ إيقاف",         "stop",    "service_stop"),
            "restart_menu": ("🔄 إعادة تشغيل",  "restart", "service_restart"),
            "logs_menu":    ("📝 سجلات",         "logs",    "service_logs"),
        }
        label, _, prefix = prompts[data]
        # اعرض أشهر السيرفيسات كأزرار سريعة
        common = ["nginx", "apache2", "mysql", "postgresql", "redis", "ssh",
                  "docker", "mongodb", "nodejs", "pm2"]
        kb = []
        row = []
        for s in common:
            row.append(InlineKeyboardButton(s, callback_data=f"{prefix}:{s}"))
            if len(row) == 3:
                kb.append(row); row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("✏️ اكتب اسماً آخر", callback_data=f"custom:{prefix}")])
        kb.append(back_btn[0])
        await query.edit_message_text(
            f"{label}\nاختر السيرفيس أو اكتب اسمه:",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── تنفيذ عمليات السيرفيس ─────────────────────────────
    elif ":" in data and data.split(":")[0] in (
            "service_status", "service_start", "service_stop",
            "service_restart", "service_logs"):
        action, svc = data.split(":", 1)
        cmds = {
            "service_status":  f"systemctl status {svc} --no-pager -l",
            "service_start":   f"sudo systemctl start {svc}  && echo 'تم التشغيل ✅'",
            "service_stop":    f"sudo systemctl stop {svc}   && echo 'تم الإيقاف ✅'",
            "service_restart": f"sudo systemctl restart {svc}&& echo 'تمت إعادة التشغيل ✅'",
            "service_logs":    f"journalctl -u {svc} -n 30 --no-pager",
        }
        out = run(cmds[action])
        await query.edit_message_text(
            f"```\n{out}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_btn)
        )

    # ── طلب إدخال يدوي ────────────────────────────────────
    elif data.startswith("custom:"):
        prefix = data.split(":", 1)[1]
        ctx.user_data["awaiting"] = prefix
        labels = {
            "service_status":  "حالة",
            "service_start":   "تشغيل",
            "service_stop":    "إيقاف",
            "service_restart": "إعادة تشغيل",
            "service_logs":    "سجلات",
        }
        await query.edit_message_text(
            f"✏️ أرسل اسم السيرفيس الذي تريد {labels.get(prefix,'تنفيذ الأمر عليه')}:"
        )

    # ── رجوع للقائمة الرئيسية ─────────────────────────────
    elif data == "back_main":
        kb = [
            [InlineKeyboardButton("📋 عرض السيرفيسات",   callback_data="list_services"),
             InlineKeyboardButton("📊 موارد السيرفر",    callback_data="resources")],
            [InlineKeyboardButton("🔍 حالة سيرفيس",      callback_data="status_menu"),
             InlineKeyboardButton("▶️ تشغيل سيرفيس",    callback_data="start_menu")],
            [InlineKeyboardButton("⏹️ إيقاف سيرفيس",    callback_data="stop_menu"),
             InlineKeyboardButton("🔄 إعادة تشغيل",     callback_data="restart_menu")],
            [InlineKeyboardButton("🐳 Docker Containers", callback_data="docker_list"),
             InlineKeyboardButton("📁 مساحة القرص",      callback_data="disk")],
            [InlineKeyboardButton("🔌 البورتات المفتوحة", callback_data="ports"),
             InlineKeyboardButton("📝 آخر السجلات",      callback_data="logs_menu")],
        ]
        await query.edit_message_text(
            "🖥️ *القائمة الرئيسية* — اختر ما تريد:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )


# ── استقبال النص عند طلب اسم سيرفيس يدوي ─────────────────
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    prefix = ctx.user_data.pop("awaiting", None)
    if not prefix:
        await update.message.reply_text("استخدم /start للقائمة الرئيسية.")
        return

    svc = update.message.text.strip()
    cmds = {
        "service_status":  f"systemctl status {svc} --no-pager -l",
        "service_start":   f"sudo systemctl start {svc}  && echo '✅ تم التشغيل'",
        "service_stop":    f"sudo systemctl stop {svc}   && echo '✅ تم الإيقاف'",
        "service_restart": f"sudo systemctl restart {svc}&& echo '✅ تمت إعادة التشغيل'",
        "service_logs":    f"journalctl -u {svc} -n 30 --no-pager",
    }
    out = run(cmds[prefix])
    back = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
    await update.message.reply_text(
        f"```\n{out}\n```",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(back)
    )


# ══════════════════════════════════════════════════════════════
#  تشغيل البوت
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    from telegram.ext import MessageHandler, filters

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🤖 البوت يعمل الآن...")
    app.run_polling()
