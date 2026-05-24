"""
plugins/all.py
================
نقطة جامعة لاستيراد كل المتغيرات والثوابت والـHelpers المشتركة
لاستخدامها بسرعة في أي بلجن مستقبلي.

يكفي :
    from plugins.all import *
"""

# المتغيرات العامة
import config  # noqa: F401

# الـHelpers
from helpers import Ranks                          # noqa: F401
from helpers.utils import extract_user, mention    # noqa: F401
from helpers import payload as P                   # noqa: F401
from helpers import quran as Q                     # noqa: F401
from helpers.memes import random_meme              # noqa: F401
from helpers import games_data as GD               # noqa: F401

# أدوات Pyrogram الأكثر استخداماً
from pyrogram import Client, filters               # noqa: F401
from pyrogram.enums import ParseMode, ChatType     # noqa: F401
from pyrogram.types import (                       # noqa: F401
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ChatPermissions,
)

# Redis helper (تُحقن في app.redis من main.py)

# ====== ثوابت مشتركة ======
EMOJI = {
    "ok":    "✅",
    "no":    "⛔",
    "warn":  "⚠️",
    "info":  "ℹ️",
    "trash": "🗑",
    "lock":  "🔒",
    "unlock":"🔓",
    "money": "💰",
    "star":  "⭐",
    "fire":  "🔥",
    "love":  "❤️",
}

SEPARATOR = "━━━━━━━━━━━━"


def html_card(title: str, lines: list[str]) -> str:
    """يولّد بطاقة HTML موحّدة الشكل"""
    body = "\n".join(lines)
    return f"<b>{title}</b>\n{SEPARATOR}\n{body}\n{SEPARATOR}"


# ====== فلاتر مشتركة جاهزة ======
def text_eq(*words):
    """فلتر يطابق نصاً يساوي تماماً إحدى الكلمات (Pyrogram regex)"""
    pattern = r"^(" + "|".join(words) + r")$"
    return filters.regex(pattern)


def reply_text_eq(*words):
    """نفس السابق مع الرد"""
    return text_eq(*words) & filters.reply
