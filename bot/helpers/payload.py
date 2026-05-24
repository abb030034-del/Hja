"""
helpers/payload.py
===================
استخراج/إرسال محتوى الردود (نص، ميديا، ملصق، صوت...).
"""

import json


def extract_payload(message):
    """
    استخراج payload من الرسالة المُردّ عليها.
    يرجّع dict فيه type + file_id (أو نص) + caption.
    """
    src = message.reply_to_message
    if not src:
        return None

    if src.sticker:
        return {"type": "sticker", "file_id": src.sticker.file_id}
    if src.animation:  # GIF
        return {"type": "animation", "file_id": src.animation.file_id, "caption": src.caption or ""}
    if src.photo:
        return {"type": "photo", "file_id": src.photo.file_id, "caption": src.caption or ""}
    if src.video:
        return {"type": "video", "file_id": src.video.file_id, "caption": src.caption or ""}
    if src.voice:
        return {"type": "voice", "file_id": src.voice.file_id}
    if src.audio:
        return {"type": "audio", "file_id": src.audio.file_id, "caption": src.caption or ""}
    if src.video_note:
        return {"type": "video_note", "file_id": src.video_note.file_id}
    if src.document:
        return {"type": "document", "file_id": src.document.file_id, "caption": src.caption or ""}
    if src.text:
        return {"type": "text", "text": src.text}
    return None


async def send_payload(client, chat_id, payload, reply_to_message_id=None):
    """إرسال payload للمحادثة"""
    t = payload.get("type")
    cap = payload.get("caption") or None

    if t == "text":
        await client.send_message(chat_id, payload["text"], reply_to_message_id=reply_to_message_id)
    elif t == "sticker":
        await client.send_sticker(chat_id, payload["file_id"], reply_to_message_id=reply_to_message_id)
    elif t == "animation":
        await client.send_animation(chat_id, payload["file_id"], caption=cap, reply_to_message_id=reply_to_message_id)
    elif t == "photo":
        await client.send_photo(chat_id, payload["file_id"], caption=cap, reply_to_message_id=reply_to_message_id)
    elif t == "video":
        await client.send_video(chat_id, payload["file_id"], caption=cap, reply_to_message_id=reply_to_message_id)
    elif t == "voice":
        await client.send_voice(chat_id, payload["file_id"], reply_to_message_id=reply_to_message_id)
    elif t == "audio":
        await client.send_audio(chat_id, payload["file_id"], caption=cap, reply_to_message_id=reply_to_message_id)
    elif t == "video_note":
        await client.send_video_note(chat_id, payload["file_id"], reply_to_message_id=reply_to_message_id)
    elif t == "document":
        await client.send_document(chat_id, payload["file_id"], caption=cap, reply_to_message_id=reply_to_message_id)


def dumps(payload) -> str:
    return json.dumps(payload, ensure_ascii=False)


def loads(s: str):
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None
