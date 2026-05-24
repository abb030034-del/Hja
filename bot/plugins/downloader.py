"""
plugins/downloader.py
======================
- تفعيل / تعطيل التحميل  (مدير+)
- تحميل <رابط_يوتيوب> أو يوتيوب <كلمة بحث>
- صوت <رابط/كلمة>        (تحميل صوت mp3)
- قرآن <سورة> [قارئ]
- ميمز                    (ميم عشوائي)

ملاحظة : يتطلب تثبيت yt-dlp :
    pip install yt-dlp
"""

import os
import asyncio
import tempfile

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from helpers import Ranks
from helpers import quran as Q
from helpers.memes import random_meme


def _enabled_key(chat_id): return f"download:enabled:{chat_id}"  # افتراضياً مفعّل


def is_download_enabled(rds, chat_id) -> bool:
    return rds.get(_enabled_key(chat_id)) != "0"


# ============ تفعيل / تعطيل التحميل ============
@Client.on_message(filters.group & filters.regex(r"^(تفعيل|تعطيل)\s+التحميل$"))
async def toggle_download(client, message):
    rds = client.redis
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id: return
    if not Ranks.manager_pls(rds, user_id, chat_id):
        await message.reply_text("⛔ هذا الأمر للمدير أو أعلى فقط.")
        return
    if message.matches[0].group(1) == "تفعيل":
        rds.set(_enabled_key(chat_id), "1")
        await message.reply_text("✅ تم تفعيل التحميل.")
    else:
        rds.set(_enabled_key(chat_id), "0")
        await message.reply_text("🔕 تم تعطيل التحميل.")


# ============ تحميل (يوتيوب / بحث) ============
async def _yt_download(query: str, audio_only: bool, out_dir: str):
    """يستخدم yt-dlp في عملية فرعية"""
    out_template = os.path.join(out_dir, "%(title).80s.%(ext)s")
    cmd = ["yt-dlp", "--no-warnings", "-q", "-o", out_template]
    if audio_only:
        cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "5"]
    else:
        cmd += ["-f", "best[height<=480][ext=mp4]/best[ext=mp4]/best"]

    # إن كان رابطاً مباشراً نستخدمه، وإلا بحث يوتيوب
    if query.startswith("http"):
        cmd.append(query)
    else:
        cmd.append(f"ytsearch1:{query}")

    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        return None, (err.decode(errors="ignore")[:500] or "Unknown error")

    files = sorted(os.listdir(out_dir), key=lambda f: os.path.getmtime(os.path.join(out_dir, f)))
    if not files:
        return None, "لم يُنزَّل أي ملف"
    return os.path.join(out_dir, files[-1]), None


@Client.on_message(filters.regex(r"^(تحميل|يوتيوب)\s+([\s\S]+)$"))
async def download_video(client, message):
    rds = client.redis
    if message.chat.type.name != "PRIVATE" and not is_download_enabled(rds, message.chat.id):
        await message.reply_text("🔕 التحميل معطّل في هذه المجموعة.")
        return

    query = message.matches[0].group(2).strip()
    status = await message.reply_text("⏳ جاري التحميل ...")

    with tempfile.TemporaryDirectory() as tmp:
        path, err = await _yt_download(query, audio_only=False, out_dir=tmp)
        if err or not path:
            await status.edit_text(f"⚠️ فشل التحميل : {err or 'خطأ غير معروف'}")
            return
        try:
            await client.send_video(message.chat.id, path, caption=f"📥 {os.path.basename(path)}", reply_to_message_id=message.id)
            await status.delete()
        except Exception as e:
            await status.edit_text(f"⚠️ فشل الإرسال : {e}")


@Client.on_message(filters.regex(r"^صوت\s+([\s\S]+)$"))
async def download_audio(client, message):
    rds = client.redis
    if message.chat.type.name != "PRIVATE" and not is_download_enabled(rds, message.chat.id):
        await message.reply_text("🔕 التحميل معطّل في هذه المجموعة.")
        return

    query = message.matches[0].group(1).strip()
    status = await message.reply_text("⏳ جاري تحميل الصوت ...")

    with tempfile.TemporaryDirectory() as tmp:
        path, err = await _yt_download(query, audio_only=True, out_dir=tmp)
        if err or not path:
            await status.edit_text(f"⚠️ فشل التحميل : {err or 'خطأ غير معروف'}")
            return
        try:
            await client.send_audio(message.chat.id, path, caption=f"🎵 {os.path.basename(path)}", reply_to_message_id=message.id)
            await status.delete()
        except Exception as e:
            await status.edit_text(f"⚠️ فشل الإرسال : {e}")


# ============ قرآن ============
@Client.on_message(filters.regex(r"^قرآن\s+(.+)$"))
async def quran_cmd(client, message):
    raw = message.matches[0].group(1).strip()
    parts = raw.split()
    # القارئ اختياري في النهاية
    reciter = "العفاسي"
    if parts[-1] in Q.RECITERS:
        reciter = parts[-1]
        surah_name = " ".join(parts[:-1])
    else:
        surah_name = raw

    found = Q.find_surah(surah_name)
    if not found:
        avail = ", ".join(Q.RECITERS.keys())
        await message.reply_text(
            f"⚠️ سورة غير معروفة.\n\n<b>القرّاء المتاحون:</b>\n{avail}",
            parse_mode=ParseMode.HTML,
        )
        return

    num, name = found
    url = Q.get_surah_url(reciter, num)
    if not url:
        await message.reply_text("⚠️ القارئ غير متاح.")
        return

    status = await message.reply_text(f"⏳ جاري جلب سورة <b>{name}</b> ...", parse_mode=ParseMode.HTML)

    try:
        await client.send_audio(
            message.chat.id,
            url,
            caption=f"📖 سورة <b>{name}</b> — <b>{Q.RECITERS[reciter]['name']}</b>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=message.id,
        )
        await status.delete()
    except Exception as e:
        await status.edit_text(f"⚠️ فشل الإرسال : {e}")


@Client.on_message(filters.regex(r"^القرّاء$|^القراء$"))
async def list_reciters(client, message):
    lines = ["📖 <b>القرّاء المتاحون:</b>\n"]
    for key, r in Q.RECITERS.items():
        lines.append(f"• <code>{key}</code> — {r['name']}")
    lines.append("\nالاستخدام: <code>قرآن الفاتحة العفاسي</code>")
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ============ ميمز ============
@Client.on_message(filters.regex(r"^ميم$|^ميمز$"))
async def random_meme_cmd(client, message):
    # هذا يتعارض مع AUTO_REPLIES["ميمز"] - معالجنا هنا في group افتراضي
    # سيتم تنفيذ كلاهما إذا لم نوقف الانتشار.
    await message.reply_text(f"😂 {random_meme()}")
