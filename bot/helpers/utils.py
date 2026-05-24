"""
helpers/utils.py
=================
أدوات مساعدة مشتركة.
"""

from pyrogram.types import Message


async def extract_user(client, message: Message):
    """
    استخراج المستخدم المستهدف من :
        - الرد على رسالة
        - منشن (@username)
        - ايدي رقمي
    """
    # 1) الرد
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user

    # 2) من نص الأمر
    if not message.text:
        return None

    parts = message.text.split()
    if len(parts) < 2:
        return None

    target = parts[-1].strip()

    # ايدي رقمي
    if target.lstrip("-").isdigit():
        try:
            return await client.get_users(int(target))
        except Exception:
            return None

    # يوزرنيم
    if target.startswith("@"):
        try:
            return await client.get_users(target)
        except Exception:
            return None

    return None


def mention(user) -> str:
    """منشن HTML للمستخدم"""
    name = user.first_name or "مستخدم"
    return f'<a href="tg://user?id={user.id}">{name}</a>'
