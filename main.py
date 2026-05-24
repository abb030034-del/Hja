#witewolf :: @j49_c 
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException
import requests
import time
import sys
import os
import psutil
import signal
import json
import threading
from datetime import datetime
from typing import Dict, Set, List, Optional, Tuple, Any
#witewolf :: @j49_c 
_CREDIT = "الذئب الأبيض @j49_c"
_MASTER_TOKEN = os.environ.get("MASTER_TOKEN", "")
_MASTER_ID = int(os.environ.get("MASTER_ID", "0"))
_DATA_FILE = "bots_data.json"
_LOCK_FILE = "bot.lock"
_SESSION_STORE: Dict[int, Dict[str, Any]] = {}
_FACTORY_USERNAME = "tdcddcbot"
_FACTORY_CHANNELS: List[str] = []

_AVAILABLE_EFFECTS = {
    "👍": "5107584321108051014",
    "👎": "5104858069142078462",
    "❤️": "5159385139981059251",
    "🔥": "5104841245755180586",
    "🎉": "5046509860389126442",
    "💩": "5046589136895476101"
}
#witewolf :: @j49_c 
_MEDIA_TYPES_MAP = {
    'photo': 'الصور',
    'audio': 'الملفات الصوتية',
    'document': 'المستندات',
    'sticker': 'الملصقات',
    'video': 'مقاطع الفيديو',
    'voice': 'الرسائل الصوتية',
    'contact': 'جهات الاتصال',
    'forward': 'الرسائل المُعاد توجيهها',
    'all_link': 'جميع الروابط',
    'telegram_link': 'روابط تيليجرام'
}

_BANNED_MEDIA_KEYS = [
    'photo', 'audio', 'document', 'sticker', 'video', 'voice',
    'contact', 'forward', 'all_link', 'telegram_link'
]

def _build_button(text: str, callback_data: Optional[str] = None,
                  url: Optional[str] = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data, url=url)

def _format_timestamp(ts: Optional[float] = None) -> str:
    dt = datetime.fromtimestamp(ts) if ts else datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def _extract_message_info(m) -> Dict[str, Any]:
    user = m.from_user
    uid = user.id
    first_name = user.first_name or "غير متوفر"
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    username = f"@{user.username}" if user.username else "لا يوجد"
#witewolf :: @j49_c 
    if m.text:
        msg_type = "نص"
    elif m.photo:
        msg_type = "صورة"
    elif m.video:
        msg_type = "فيديو"
    elif m.document:
        msg_type = "ملف"
    elif m.audio:
        msg_type = "ملف صوتي"
    elif m.voice:
        msg_type = "رسالة صوتية"
    elif m.sticker:
        msg_type = "ملصق"
    else:
        msg_type = "نوع آخر"

    timestamp = _format_timestamp(m.date)
    language = user.language_code or "غير محدد"
    is_premium = "نعم" if getattr(user, 'is_premium', False) else "لا"

    return {
        'uid': uid,
        'full_name': full_name,
        'username': username,
        'message_type': msg_type,
        'timestamp': timestamp,
        'language': language,
        'is_premium': is_premium,
        'first_name': first_name,
        'last_name': last_name
    }
#witewolf :: @j49_c 

class BotData:
    __slots__ = (
        'owner_id', 'token', 'admin_id', 'channel_username',
        'developer_username', 'bot_name', 'bot_username',
        'banned_users', 'muted_users', 'mandatory_channels',
        'registered_users', 'users_counter', 'active_effect_id',
        'welcome_photo_id', 'is_running', 'sub_admins',
        'auto_forward', 'typing_indicator', 'reply_mode',
        'receipt_message', 'welcome_caption', 'banned_media_types'
    )

    def __init__(self, owner_id: int, token: str, admin_id: int,
                 channel: str = "", developer: str = "",
                 bot_name: str = "", bot_username: str = ""):
        self.owner_id = owner_id
        self.token = token
        self.admin_id = admin_id or owner_id
        self.channel_username = channel
        self.developer_username = developer
        self.bot_name = bot_name
        self.bot_username = bot_username
        self.banned_users: Set[int] = set()
        self.muted_users: Set[int] = set()
        self.mandatory_channels: List[str] = []
        self.registered_users: Set[int] = set()
        self.users_counter = 0
        self.active_effect_id = "5104841245755180586"
        self.welcome_photo_id = "https://i.top4top.io/p_3792b7wla1.jpg"
        self.is_running = False
        self.sub_admins: Set[int] = set()
        self.auto_forward = True
        self.typing_indicator = True
        self.reply_mode = True
        self.receipt_message = "تم استلام رسالتك بنجاح، سيتم الرد عليك في أقرب وقت."
        self.welcome_caption = ""
        self.banned_media_types: List[str] = []

#witewolf :: @j49_c 
class BotInstance:
    def __init__(self, data: BotData, factory=None):
        self.data = data
        self.bot = telebot.TeleBot(data.token)
        self._stop_event = threading.Event()
        self._factory = factory

    def _back_button(self, callback_data: str) -> List[InlineKeyboardButton]:
        return [_build_button("رجوع", callback_data=callback_data)]

    def _persist(self) -> None:
        if self._factory:
            self._factory._save_all_data()

    def _check_subscription(self, user_id: int) -> bool:
        for channel in self.data.mandatory_channels:
            try:
                member = self.bot.get_chat_member(f"@{channel}", user_id)
                if not member or member.status not in ('member', 'administrator', 'creator'):
                    return False
            except Exception:
                return False
        return True

    def _send_subscription_prompt(self, message) -> None:
        keyboard = InlineKeyboardMarkup()
        for channel in self.data.mandatory_channels:
            keyboard.add(_build_button(
                f"اشترك في @{channel}",
                url=f"https://t.me/{channel}"
            ))#witewolf :: @j49_c 
        keyboard.add(_build_button(
            "تأكيد الاشتراك",
            callback_data="check_sub"
        ))
        self.bot.send_message(
            message.chat.id,
            "<b>يرجى الاشتراك في القنوات التالية للمتابعة:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    def _clear_inline_keyboard(self, msg, user_id: int, action: str) -> None:
        try:
            self.bot.edit_message_reply_markup(
                chat_id=msg.chat.id,
                message_id=msg.message_id,
                reply_markup=InlineKeyboardMarkup()
            )
            self.bot.send_message(
                msg.chat.id,
                f"<b>تم تنفيذ الإجراء: {action} للمستخدم {user_id}</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"markup update error: {e}")

    def _is_admin(self, user_id: int) -> bool:
        return (user_id == self.data.admin_id or
                user_id == self.data.owner_id or
                user_id in self.data.sub_admins)
#witewolf :: @j49_c 
    def _is_message_banned(self, message) -> bool:
        if not self.data.banned_media_types:
            return False
        if 'forward' in self.data.banned_media_types and message.forward_from:
            return True
        if message.photo and 'photo' in self.data.banned_media_types:
            return True
        if message.video and 'video' in self.data.banned_media_types:
            return True
        if message.audio and 'audio' in self.data.banned_media_types:
            return True
        if message.voice and 'voice' in self.data.banned_media_types:
            return True
        if message.document and 'document' in self.data.banned_media_types:
            return True
        if message.sticker and 'sticker' in self.data.banned_media_types:
            return True
        if message.contact and 'contact' in self.data.banned_media_types:
            return True
        if 'all_link' in self.data.banned_media_types and message.text:
            if 'http://' in message.text or 'https://' in message.text:
                return True
        if 'telegram_link' in self.data.banned_media_types and message.text:
            if 't.me/' in message.text or 'telegram.me/' in message.text:
                return True
        return False
#witewolf :: @j49_c 
    def _send_typing(self, chat_id: int) -> None:
        if self.data.typing_indicator:
            try:
                self.bot.send_chat_action(chat_id, 'typing')
            except Exception:
                pass

    def _register_handlers(self) -> None:
        bot = self.bot
        data = self.data
        instance = self

        @bot.message_handler(commands=['start'])
        def handle_start(message):
            data.users_counter += 1
            user_id = message.from_user.id

            if not instance._check_subscription(user_id):
                instance._send_subscription_prompt(message)
                return

            is_new_user = user_id not in data.registered_users
            if is_new_user:
                data.registered_users.add(user_id)
                instance._persist()
#witewolf :: @j49_c 
            channel_url = f"https://t.me/{data.channel_username}" if data.channel_username else "https://t.me/telegram"
            developer_url = f"https://t.me/{data.developer_username}" if data.developer_username else "https://t.me/telegram"
            factory_url = f"https://t.me/{_FACTORY_USERNAME}"

            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.row(
                _build_button("القناة الرسمية", url=channel_url),
                _build_button("المطور", url=developer_url)
            )
            keyboard.row(
                _build_button("إنشاء بوت تواصل خاص", url=factory_url)
            )

            first_name = message.from_user.first_name or "المستخدم"
            caption = data.welcome_caption if data.welcome_caption else (
                f"<b>مرحباً بك {first_name} في نظام التواصل الآلي.</b>\n"
                f"يمكنك إرسال رسالتك الآن وسيتم توجيهها إلى الإدارة."
            )

            bot.send_photo(
                chat_id=message.chat.id,
                photo=data.welcome_photo_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
                message_effect_id=data.active_effect_id
            )

            if is_new_user:
                info = _extract_message_info(message)
                notification = (
                    "<b>مستخدم جديد</b>\n\n"
                    f"الاسم: {info['first_name']}\n"
                    f"اليوزر: {info['username']}\n"
                    f"المعرف: <code>{info['uid']}</code>\n"
                    f"بريميوم: {info['is_premium']}\n"
                    f"الوقت: {_format_timestamp()}\n"
                    f"إجمالي المستخدمين: {len(data.registered_users)}"
                )
                try:
                    bot.send_message(data.admin_id, notification, parse_mode="HTML")
                except Exception:
                    pass

        @bot.callback_query_handler(func=lambda c: c.data == "check_sub")
        def handle_check_subscription(callback):
            user_id = callback.from_user.id
            if instance._check_subscription(user_id):
                bot.answer_callback_query(callback.id, "تم التحقق بنجاح.")
                bot.delete_message(callback.message.chat.id, callback.message.message_id)
                handle_start(callback.message)
            else:
                bot.answer_callback_query(callback.id, "لم تكتمل الاشتراكات بعد.", show_alert=True)

        @bot.message_handler(commands=['admin'])
        def handle_admin_command(message):
            user_id = message.chat.id
            if not instance._is_admin(user_id):
                bot.reply_to(message, "<b>عذراً، هذا الأمر مخصص للإدارة فقط.</b>", parse_mode="HTML")
                return
            instance._send_admin_main(message.chat.id)

        @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_main_") or c.data.startswith("adm_subs_") or
              c.data.startswith("adm_fwd_") or c.data.startswith("adm_bc_") or c.data.startswith("adm_settings_") or
              c.data.startswith("adm_banned_") or c.data.startswith("adm_banmute_") or c.data.startswith("adm_effects_") or
              c.data.startswith("adm_photo_") or c.data.startswith("adm_admins_"))
        def handle_admin_menus(callback):
            if not instance._is_admin(callback.message.chat.id):
                bot.answer_callback_query(callback.id, "غير مصرح.")
                return
#witewolf :: @j49_c 
            action = callback.data
            chat_id = callback.message.chat.id
            msg_id = callback.message.message_id

            if action == "adm_main_stats":
                bot.answer_callback_query(callback.id)
                stats_text = (
                    "<b>إحصائيات النظام</b>\n\n"
                    f"عدد المستخدمين: {len(data.registered_users)}\n"
                    f"المحظورون: {len(data.banned_users)}\n"
                    f"المكتومون: {len(data.muted_users)}\n"
                    f"القنوات الإجبارية: {len(data.mandatory_channels)}\n"
                    f"الوقت: {_format_timestamp()}"
                )
                kb = InlineKeyboardMarkup(row_width=1)
                kb.add(*instance._back_button("adm_main_back"))
                bot.send_message(chat_id, stats_text, parse_mode="HTML", reply_markup=kb)

            elif action == "adm_main_subs":
                instance._send_subs_menu(chat_id, msg_id)

            elif action == "adm_main_fwd":
                instance._send_fwd_menu(chat_id, msg_id)

            elif action == "adm_main_bc":
                instance._send_bc_menu(chat_id, msg_id)

            elif action == "adm_main_settings":
                instance._send_settings_menu(chat_id, msg_id)

            elif action == "adm_main_effects":
                bot.answer_callback_query(callback.id)
                instance._send_effects_panel(chat_id, msg_id)

            elif action == "adm_main_photo":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل الصورة الجديدة للواجهة:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._change_photo_step)

            elif action == "adm_main_admins":
                instance._send_admins_menu(chat_id, msg_id)

            elif action == "adm_main_banmute":
                instance._send_banmute_menu(chat_id, msg_id)

            elif action == "adm_main_back":
                instance._send_admin_main(chat_id, msg_id)

            elif action == "adm_subs_add":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل معرف القناة (@username):</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._add_channel_step)

            elif action == "adm_subs_list":
                bot.answer_callback_query(callback.id)
                instance._send_subs_list(chat_id)

            elif action.startswith("adm_subs_del_"):
                channel = action.replace("adm_subs_del_", "")
                if channel in data.mandatory_channels:
                    data.mandatory_channels.remove(channel)
                    instance._persist()
                    bot.answer_callback_query(callback.id, f"تم حذف @{channel}")
                    instance._send_subs_list(chat_id, msg_id)
                else:
                    bot.answer_callback_query(callback.id, "القناة غير موجودة")

            elif action == "adm_subs_back":
                instance._send_admin_main(chat_id, msg_id)

            elif action == "adm_fwd_toggle":
                data.auto_forward = not data.auto_forward
                instance._persist()
                bot.answer_callback_query(callback.id, f"التوجيه {'مفعل' if data.auto_forward else 'معطل'}")
                instance._send_fwd_menu(chat_id, msg_id)

            elif action == "adm_fwd_back":
                instance._send_admin_main(chat_id, msg_id)

            elif action == "adm_bc_text":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل الرسالة النصية للإذاعة:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._broadcast_message)

            elif action == "adm_bc_forward":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل أي رسالة لإعادة توجيهها.</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._broadcast_forward)

            elif action == "adm_bc_back":
                instance._send_admin_main(chat_id, msg_id)

            elif action == "adm_settings_typing":
                data.typing_indicator = not data.typing_indicator
                instance._persist()
                bot.answer_callback_query(callback.id, f"حالة مؤشر الكتابة: {'مفعل' if data.typing_indicator else 'معطل'}")
                instance._send_settings_menu(chat_id, msg_id)

            elif action == "adm_settings_reply":
                data.reply_mode = not data.reply_mode
                instance._persist()
                bot.answer_callback_query(callback.id, f"الرد التلقائي: {'مفعل' if data.reply_mode else 'معطل'}")
                instance._send_settings_menu(chat_id, msg_id)

            elif action == "adm_settings_receipt":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل رسالة الاستلام الجديدة:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._set_receipt_message)

            elif action == "adm_settings_welcome":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل رسالة الترحيب الجديدة:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._set_welcome_message)

            elif action == "adm_settings_banned":
                bot.answer_callback_query(callback.id)
                instance._send_banned_media_menu(chat_id, msg_id)

            elif action == "adm_settings_back":
                instance._send_admin_main(chat_id, msg_id)

            elif action.startswith("adm_banned_toggle_"):
                media_key = action.replace("adm_banned_toggle_", "")
                if media_key in data.banned_media_types:
                    data.banned_media_types.remove(media_key)
                else:
                    data.banned_media_types.append(media_key)
                instance._persist()
                bot.answer_callback_query(callback.id, "تم التحديث")
                instance._send_banned_media_menu(chat_id, msg_id)

            elif action == "adm_banned_back":
                instance._send_settings_menu(chat_id, msg_id)

            elif action == "adm_banmute_ban":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل معرف المستخدم لحظره:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._ban_user_step)

            elif action == "adm_banmute_unban":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل معرف المستخدم لرفع الحظر:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._unban_user_step)

            elif action == "adm_banmute_mute":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل معرف المستخدم لكتمه:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._mute_user_step)

            elif action == "adm_banmute_unmute":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل معرف المستخدم لرفع الكتم:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._unmute_user_step)

            elif action == "adm_banmute_banned":
                bot.answer_callback_query(callback.id)
                if data.banned_users:
                    ban_list = "\n".join([f"• <code>{uid}</code>" for uid in data.banned_users])
                    bot.send_message(chat_id, f"<b>المحظورون:</b>\n\n{ban_list}", parse_mode="HTML")
                else:
                    bot.send_message(chat_id, "<b>لا يوجد محظورون.</b>", parse_mode="HTML")

            elif action == "adm_banmute_muted":
                bot.answer_callback_query(callback.id)
                if data.muted_users:
                    mute_list = "\n".join([f"• <code>{uid}</code>" for uid in data.muted_users])
                    bot.send_message(chat_id, f"<b>المكتومون:</b>\n\n{mute_list}", parse_mode="HTML")
                else:
                    bot.send_message(chat_id, "<b>لا يوجد مكتومون.</b>", parse_mode="HTML")

            elif action == "adm_banmute_back":
                instance._send_admin_main(chat_id, msg_id)

            elif action == "adm_admins_add":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل معرف المشرف الجديد:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, instance._add_admin_step)

            elif action == "adm_admins_list":
                bot.answer_callback_query(callback.id)
                all_admins = [data.admin_id] + list(data.sub_admins)
                admin_lines = "\n".join([
                    f"• <code>{uid}</code>" + (" (رئيسي)" if uid == data.admin_id else "")
                    for uid in all_admins
                ])
                bot.send_message(chat_id, f"<b>قائمة المشرفين:</b>\n\n{admin_lines}", parse_mode="HTML")

            elif action == "adm_admins_back":
                instance._send_admin_main(chat_id, msg_id)

            elif action.startswith("eff_"):
                if not instance._is_admin(callback.message.chat.id):
                    bot.answer_callback_query(callback.id, "غير مصرح.")
                    return
                effect_id = action.replace("eff_", "")
                data.active_effect_id = effect_id
                instance._persist()
                selected_emoji = next((k for k, v in _AVAILABLE_EFFECTS.items() if v == effect_id), "")
                bot.answer_callback_query(callback.id, f"تم تغيير التأثير إلى {selected_emoji}")
                instance._send_effects_panel(chat_id, msg_id)

        @bot.callback_query_handler(func=lambda c: c.data.startswith(('ban_', 'reply_')))
        def handle_quick_actions(callback):
            if not instance._is_admin(callback.message.chat.id):
                bot.answer_callback_query(callback.id, "غير مصرح.")
                return
            try:
                action_type, user_id_str = callback.data.split('_', 1)
                target_user_id = int(user_id_str)

                if action_type == 'ban':
                    data.banned_users.add(target_user_id)
                    instance._persist()
                    bot.answer_callback_query(callback.id, f"تم حظر المستخدم {target_user_id}")
                    instance._clear_inline_keyboard(callback.message, target_user_id, "حظر")
                elif action_type == 'reply':
                    bot.answer_callback_query(callback.id, "أرسل ردك الآن")
                    prompt = bot.send_message(
                        data.admin_id,
                        f"<b>أرسل الرد إلى المستخدم {target_user_id}:</b>",
                        parse_mode="HTML"
                    )
                    bot.register_next_step_handler(
                        prompt,
                        lambda msg: instance._send_reply_to_user(msg, target_user_id)
                    )
            except Exception as e:
                bot.answer_callback_query(callback.id, "حدث خطأ")
                print(f"quick action error: {e}")

        @bot.message_handler(content_types=[
            'text', 'photo', 'video', 'document',
            'audio', 'voice', 'sticker', 'contact'
        ])
        def handle_incoming_message(message):
            user_id = message.chat.id

            if user_id in data.banned_users:
                bot.reply_to(message, "<b>عذراً، أنت محظور من استخدام النظام.</b>", parse_mode="HTML")
                return
            if user_id in data.muted_users:
                return
            if instance._is_admin(user_id):
                return
            if not instance._check_subscription(user_id):
                instance._send_subscription_prompt(message)
                return
            if instance._is_message_banned(message):
                bot.reply_to(message, "<b>هذا النوع من المحتوى غير مسموح به.</b>", parse_mode="HTML")
                return

            if data.auto_forward:
                info = _extract_message_info(message)
                instance._forward_message_to_admin(message, info)

            if data.reply_mode:
                instance._send_typing(user_id)
                bot.reply_to(message, data.receipt_message, parse_mode="HTML")

    def _send_admin_main(self, chat_id: int, msg_id: Optional[int] = None) -> None:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.row(
            _build_button("الاشتراك الإجباري", callback_data="adm_main_subs"),
            _build_button("إعدادات التوجيه", callback_data="adm_main_fwd")
        )
        kb.row(
            _build_button("الإذاعة", callback_data="adm_main_bc"),
            _build_button("الإحصائيات", callback_data="adm_main_stats")
        )
        kb.row(
            _build_button("الإعدادات العامة", callback_data="adm_main_settings"),
            _build_button("التأثيرات", callback_data="adm_main_effects")
        )
        kb.row(
            _build_button("تغيير صورة الواجهة", callback_data="adm_main_photo"),
            _build_button("إدارة المشرفين", callback_data="adm_main_admins")
        )
        kb.row(
            _build_button("الحظر والكتم", callback_data="adm_main_banmute")
        )
        text = "<b>لوحة التحكم الإدارية</b>\n\nاختر القسم المطلوب:"
        if msg_id:
            try:
                self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=kb)
                return
            except Exception:
                pass
        self.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)

    def _send_subs_menu(self, chat_id: int, msg_id: int) -> None:
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(_build_button("إضافة قناة", callback_data="adm_subs_add"))
        kb.add(_build_button("عرض القنوات", callback_data="adm_subs_list"))
        kb.add(*self._back_button("adm_main_back"))
        text = "<b>إدارة الاشتراك الإجباري</b>"
        self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=kb)

    def _send_subs_list(self, chat_id: int, msg_id: Optional[int] = None) -> None:
        kb = InlineKeyboardMarkup(row_width=1)
        if self.data.mandatory_channels:
            for channel in self.data.mandatory_channels:
                kb.add(_build_button(f"حذف @{channel}", callback_data=f"adm_subs_del_{channel}"))
        else:
            kb.add(_build_button("لا توجد قنوات مضافة", callback_data="none"))
        kb.add(*self._back_button("adm_subs_back"))
        channels_display = "\n".join([f"• @{c}" for c in self.data.mandatory_channels]) if self.data.mandatory_channels else "لا توجد قنوات"
        text = f"<b>القنوات الإجبارية الحالية:</b>\n{channels_display}"
        if msg_id:
            self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=kb)
        else:
            self.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)

    def _send_fwd_menu(self, chat_id: int, msg_id: int) -> None:
        status = "مفعل" if self.data.auto_forward else "معطل"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(_build_button(f"التوجيه التلقائي: {status}", callback_data="adm_fwd_toggle"))
        kb.add(*self._back_button("adm_main_back"))
        text = "<b>إعدادات إعادة التوجيه</b>"
        self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=kb)

    def _send_bc_menu(self, chat_id: int, msg_id: int) -> None:
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(_build_button("إذاعة رسالة", callback_data="adm_bc_text"))
        kb.add(_build_button("إذاعة توجيه", callback_data="adm_bc_forward"))
        kb.add(*self._back_button("adm_main_back"))
        text = "<b>قسم الإذاعة</b>"
        self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=kb)

    def _send_settings_menu(self, chat_id: int, msg_id: int) -> None:
        typing_status = "مفعل" if self.data.typing_indicator else "معطل"
        reply_status = "مفعل" if self.data.reply_mode else "معطل"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(_build_button(f"مؤشر الكتابة: {typing_status}", callback_data="adm_settings_typing"))
        kb.add(_build_button(f"الرد التلقائي: {reply_status}", callback_data="adm_settings_reply"))
        kb.add(_build_button("رسالة الاستلام", callback_data="adm_settings_receipt"))
        kb.add(_build_button("رسالة الترحيب", callback_data="adm_settings_welcome"))
        kb.add(_build_button("المحتويات الممنوعة", callback_data="adm_settings_banned"))
        kb.add(*self._back_button("adm_main_back"))
        text = "<b>الإعدادات العامة</b>"
        self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=kb)

    def _send_banned_media_menu(self, chat_id: int, msg_id: int) -> None:
        kb = InlineKeyboardMarkup(row_width=1)
        for key in _BANNED_MEDIA_KEYS:
            status = "مسموح" if key not in self.data.banned_media_types else "ممنوع"
            label = f"{_MEDIA_TYPES_MAP.get(key, key)}: {status}"
            kb.add(_build_button(label, callback_data=f"adm_banned_toggle_{key}"))
        kb.add(*self._back_button("adm_settings_back"))
        text = "<b>إدارة المحتويات الممنوعة</b>"
        self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=kb)

    def _send_banmute_menu(self, chat_id: int, msg_id: int) -> None:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.row(
            _build_button("حظر", callback_data="adm_banmute_ban"),
            _build_button("رفع الحظر", callback_data="adm_banmute_unban")
        )
        kb.row(
            _build_button("كتم", callback_data="adm_banmute_mute"),
            _build_button("رفع الكتم", callback_data="adm_banmute_unmute")
        )
        kb.row(
            _build_button("قائمة المحظورين", callback_data="adm_banmute_banned"),
            _build_button("قائمة المكتومين", callback_data="adm_banmute_muted")
        )
        kb.add(*self._back_button("adm_main_back"))
        text = "<b>إدارة الحظر والكتم</b>"
        self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=kb)

    def _send_admins_menu(self, chat_id: int, msg_id: int) -> None:
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(_build_button("إضافة مشرف", callback_data="adm_admins_add"))
        kb.add(_build_button("قائمة المشرفين", callback_data="adm_admins_list"))
        kb.add(*self._back_button("adm_main_back"))
        text = "<b>إدارة المشرفين</b>"
        self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=kb)

    def _build_effects_keyboard(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardMarkup(row_width=3)
        buttons = []
        for emoji_name, effect_id in _AVAILABLE_EFFECTS.items():
            label = f"{emoji_name} ✔️" if effect_id == self.data.active_effect_id else emoji_name
            buttons.append(_build_button(label, callback_data=f"eff_{effect_id}"))
        for i in range(0, len(buttons), 3):
            kb.row(*buttons[i:i+3])
        return kb

    def _send_effects_panel(self, chat_id: int, msg_id: Optional[int] = None) -> None:
        keyboard = self._build_effects_keyboard()
        keyboard.add(*self._back_button("adm_main_back"))
        text = "<b>اختر التأثير المناسب للواجهة:</b>"
        if msg_id:
            try:
                self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML", reply_markup=keyboard)
                return
            except Exception:
                pass
        self.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)

    def _set_receipt_message(self, message) -> None:
        if not self._is_admin(message.chat.id):
            return
        self.data.receipt_message = message.text or ""
        self._persist()
        self.bot.reply_to(message, "<b>تم تحديث رسالة الاستلام.</b>", parse_mode="HTML")

    def _set_welcome_message(self, message) -> None:
        if not self._is_admin(message.chat.id):
            return
        self.data.welcome_caption = message.text or ""
        self._persist()
        self.bot.reply_to(message, "<b>تم تحديث رسالة الترحيب.</b>", parse_mode="HTML")

    def _forward_message_to_admin(self, message, info: Dict[str, Any]) -> None:
        admin_id = self.data.admin_id
        header = (
            "<b>رسالة جديدة</b>\n\n"
            f"المرسل: {info['full_name']}\n"
            f"اليوزر: {info['username']}\n"
            f"المعرف: <code>{info['uid']}</code>\n"
            f"بريميوم: {info['is_premium']}\n"
            f"اللغة: {info['language']}\n"
            f"نوع المحتوى: {info['message_type']}\n"
            f"الوقت: {info['timestamp']}\n\n"
            "<b>المحتوى:</b>\n"
        )
        action_keyboard = InlineKeyboardMarkup(row_width=2)
        action_keyboard.row(
            _build_button("حظر", callback_data=f"ban_{info['uid']}"),
            _build_button("رد", callback_data=f"reply_{info['uid']}")
        )

        try:
            if message.text:
                self.bot.send_message(admin_id, header + message.text, parse_mode="HTML", reply_markup=action_keyboard)
            elif message.photo:
                caption = header + (message.caption or "")
                self.bot.send_photo(admin_id, message.photo[-1].file_id, caption=caption, parse_mode="HTML", reply_markup=action_keyboard)
            elif message.video:
                caption = header + (message.caption or "")
                self.bot.send_video(admin_id, message.video.file_id, caption=caption, parse_mode="HTML", reply_markup=action_keyboard)
            elif message.document:
                caption = header + (message.caption or "")
                self.bot.send_document(admin_id, message.document.file_id, caption=caption, parse_mode="HTML", reply_markup=action_keyboard)
            elif message.audio:
                caption = header + (message.caption or "")
                self.bot.send_audio(admin_id, message.audio.file_id, caption=caption, parse_mode="HTML", reply_markup=action_keyboard)
            elif message.voice:
                self.bot.send_voice(admin_id, message.voice.file_id, caption=header, parse_mode="HTML", reply_markup=action_keyboard)
            elif message.sticker:
                self.bot.send_sticker(admin_id, message.sticker.file_id, reply_markup=action_keyboard)
                self.bot.send_message(admin_id, header, parse_mode="HTML")
            elif message.contact:
                contact_text = f"جهة اتصال:\n{message.contact.phone_number}\n{message.contact.first_name} {message.contact.last_name or ''}"
                self.bot.send_message(admin_id, header + contact_text, parse_mode="HTML", reply_markup=action_keyboard)
            else:
                self.bot.forward_message(admin_id, message.chat.id, message.message_id)
                self.bot.send_message(admin_id, header, parse_mode="HTML")
        except Exception as e:
            print(f"msg forward error: {e}")

    def _broadcast_message(self, original_message) -> None:
        if not self._is_admin(original_message.chat.id):
            return
        admin_id = self.data.admin_id
        success_count = 0
        fail_count = 0
        progress_msg = self.bot.send_message(admin_id, "<b>جاري الإذاعة...</b>", parse_mode="HTML")
        for user_id in list(self.data.registered_users):
            try:
                if original_message.text:
                    self.bot.send_message(user_id, original_message.text, parse_mode="HTML")
                elif original_message.photo:
                    self.bot.send_photo(user_id, original_message.photo[-1].file_id, caption=original_message.caption or "", parse_mode="HTML")
                elif original_message.video:
                    self.bot.send_video(user_id, original_message.video.file_id, caption=original_message.caption or "", parse_mode="HTML")
                elif original_message.document:
                    self.bot.send_document(user_id, original_message.document.file_id, caption=original_message.caption or "", parse_mode="HTML")
                elif original_message.audio:
                    self.bot.send_audio(user_id, original_message.audio.file_id, caption=original_message.caption or "", parse_mode="HTML")
                elif original_message.voice:
                    self.bot.send_voice(user_id, original_message.voice.file_id)
                elif original_message.sticker:
                    self.bot.send_sticker(user_id, original_message.sticker.file_id)
                else:
                    self.bot.forward_message(user_id, original_message.chat.id, original_message.message_id)
                success_count += 1
                if success_count % 30 == 0:
                    try:
                        self.bot.edit_message_text(
                            chat_id=admin_id, message_id=progress_msg.message_id,
                            text=f"<b>جاري الإذاعة...\nناجح: {success_count}\nفشل: {fail_count}</b>",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
            except Exception:
                fail_count += 1
        result_text = f"<b>اكتملت الإذاعة.\n\nنجاح: {success_count}\nفشل: {fail_count}</b>"
        try:
            self.bot.edit_message_text(chat_id=admin_id, message_id=progress_msg.message_id, text=result_text, parse_mode="HTML")
        except Exception:
            self.bot.send_message(admin_id, result_text, parse_mode="HTML")
#witewolf :: @j49_c 
    def _broadcast_forward(self, original_message) -> None:
        if not self._is_admin(original_message.chat.id):
            return
        admin_id = self.data.admin_id
        success_count = 0
        fail_count = 0
        progress_msg = self.bot.send_message(admin_id, "<b>جاري إذاعة التوجيه...</b>", parse_mode="HTML")
        for user_id in list(self.data.registered_users):
            try:
                self.bot.forward_message(user_id, original_message.chat.id, original_message.message_id)
                success_count += 1
                if success_count % 30 == 0:
                    self.bot.edit_message_text(
                        chat_id=admin_id, message_id=progress_msg.message_id,
                        text=f"<b>جاري الإذاعة...\nناجح: {success_count}\nفشل: {fail_count}</b>",
                        parse_mode="HTML"
                    )
            except Exception:
                fail_count += 1
        result_text = f"<b>اكتملت إذاعة التوجيه.\n\nنجاح: {success_count}\nفشل: {fail_count}</b>"
        try:
            self.bot.edit_message_text(chat_id=admin_id, message_id=progress_msg.message_id, text=result_text, parse_mode="HTML")
        except Exception:
            self.bot.send_message(admin_id, result_text, parse_mode="HTML")

    def _send_reply_to_user(self, admin_message, target_user_id: int) -> None:
        try:
            if admin_message.text:
                self.bot.send_message(target_user_id, admin_message.text, parse_mode="HTML")
            elif admin_message.photo:
                self.bot.send_photo(target_user_id, admin_message.photo[-1].file_id, caption=admin_message.caption or "", parse_mode="HTML")
            elif admin_message.video:
                self.bot.send_video(target_user_id, admin_message.video.file_id, caption=admin_message.caption or "", parse_mode="HTML")
            elif admin_message.document:
                self.bot.send_document(target_user_id, admin_message.document.file_id, caption=admin_message.caption or "", parse_mode="HTML")
            elif admin_message.audio:
                self.bot.send_audio(target_user_id, admin_message.audio.file_id, caption=admin_message.caption or "", parse_mode="HTML")
            elif admin_message.voice:
                self.bot.send_voice(target_user_id, admin_message.voice.file_id)
            elif admin_message.sticker:
                self.bot.send_sticker(target_user_id, admin_message.sticker.file_id)
            else:
                self.bot.forward_message(target_user_id, admin_message.chat.id, admin_message.message_id)
            self.bot.send_message(self.data.admin_id, "<b>تم إرسال الرد بنجاح.</b>", parse_mode="HTML")
        except Exception as e:
            self.bot.send_message(self.data.admin_id, f"<b>فشل الإرسال: {e}</b>", parse_mode="HTML")

    def _add_channel_step(self, message) -> None:
        if not self._is_admin(message.chat.id):
            return
        channel_username = message.text.strip().lstrip('@')
        self.data.mandatory_channels.append(channel_username)
        self._persist()
        self.bot.reply_to(message, f"<b>تمت إضافة القناة @{channel_username}</b>", parse_mode="HTML")

    def _ban_user_step(self, message) -> None:
        if not self._is_admin(message.chat.id):
            return
        try:
            target_id = int(message.text.strip())
            self.data.banned_users.add(target_id)
            self._persist()
            self.bot.reply_to(message, f"<b>تم حظر المستخدم {target_id}</b>", parse_mode="HTML")
        except ValueError:
            self.bot.reply_to(message, "<b>معرف غير صحيح.</b>", parse_mode="HTML")

    def _unban_user_step(self, message) -> None:
        if not self._is_admin(message.chat.id):
            return
        try:
            target_id = int(message.text.strip())
            self.data.banned_users.discard(target_id)
            self._persist()
            self.bot.reply_to(message, f"<b>تم رفع الحظر عن المستخدم {target_id}</b>", parse_mode="HTML")
        except ValueError:
            self.bot.reply_to(message, "<b>معرف غير صحيح.</b>", parse_mode="HTML")

    def _mute_user_step(self, message) -> None:
        if not self._is_admin(message.chat.id):
            return
        try:
            target_id = int(message.text.strip())
            self.data.muted_users.add(target_id)
            self._persist()
            self.bot.reply_to(message, f"<b>تم كتم المستخدم {target_id}</b>", parse_mode="HTML")
        except ValueError:
            self.bot.reply_to(message, "<b>معرف غير صحيح.</b>", parse_mode="HTML")

    def _unmute_user_step(self, message) -> None:
        if not self._is_admin(message.chat.id):
            return
        try:
            target_id = int(message.text.strip())
            self.data.muted_users.discard(target_id)
            self._persist()
            self.bot.reply_to(message, f"<b>تم رفع الكتم عن المستخدم {target_id}</b>", parse_mode="HTML")
        except ValueError:
            self.bot.reply_to(message, "<b>معرف غير صحيح.</b>", parse_mode="HTML")

    def _change_photo_step(self, message) -> None:
        if not self._is_admin(message.chat.id):
            return
        if message.photo:
            self.data.welcome_photo_id = message.photo[-1].file_id
            self._persist()
            self.bot.reply_to(message, "<b>تم تحديث صورة الواجهة بنجاح.</b>", parse_mode="HTML")
        else:
            self.bot.reply_to(message, "<b>يرجى إرسال صورة فقط.</b>", parse_mode="HTML")

    def _add_admin_step(self, message) -> None:
        if message.chat.id != self.data.admin_id and message.chat.id != self.data.owner_id:
            return
        try:
            target_id = int(message.text.strip())
            self.data.sub_admins.add(target_id)
            self._persist()
            self.bot.reply_to(message, f"<b>تمت إضافة المشرف {target_id}</b>", parse_mode="HTML")
        except ValueError:
            self.bot.reply_to(message, "<b>معرف غير صحيح.</b>", parse_mode="HTML")

    def stop(self) -> None:
        try:
            self.data.is_running = False
            self._stop_event.set()
            self.bot.stop_polling()
        except Exception as e:
            print(f"stop error: {e}")

    def run(self) -> None:
        try:
            self._register_handlers()
            print(f"✅ Bot started: {self.data.bot_username}")
            while self.data.is_running and not self._stop_event.is_set():
                try:
                    self.bot.polling(none_stop=False, timeout=60, long_polling_timeout=60)
                except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as net_err:
                    print(f"Network error for {self.data.bot_username}: {net_err}. Retrying in 10s...")
                    time.sleep(10)
                    continue
                except ApiTelegramException as api_error:
                    if api_error.error_code == 401:
                        print(f"❌ Bot {self.data.bot_username} token unauthorized – stopping")
                        self.stop()
                        if self._factory:
                            self._factory._handle_token_failure(self.data.bot_username)
                        break
                    else:
                        if self.data.is_running and not self._stop_event.is_set():
                            print(f"polling API error: {api_error}")
                            time.sleep(3)
                except Exception as ex:
                    if self.data.is_running and not self._stop_event.is_set():
                        print(f"polling error: {ex}")
                        time.sleep(3)
                    else:
                        break
        except Exception as e:
            print(f"run error: {e}")
        finally:
            self.data.is_running = False


class FactoryBot:
    def __init__(self):
        self.bot = telebot.TeleBot(_MASTER_TOKEN)
        self.instances: Dict[str, BotInstance] = {}
        self.banned_users: Set[int] = set()
        self.all_users: Set[int] = set()
        self.maintenance_mode = False
        self.factory_channels: List[str] = list(_FACTORY_CHANNELS)
        self._load_data()

    def _load_data(self) -> None:
        try:
            if os.path.exists(_DATA_FILE):
                with open(_DATA_FILE, 'r', encoding='utf-8') as file:
                    raw_data = json.load(file)
                bots_data = raw_data.get('bots', {})
                factory_meta = raw_data.get('factory_data', {})
                self.banned_users = set(factory_meta.get('banned_users', []))
                self.all_users = set(factory_meta.get('users', []))
                self.maintenance_mode = factory_meta.get('maintenance_mode', False)
                self.factory_channels = factory_meta.get('factory_channels', list(_FACTORY_CHANNELS))
                for bot_id, bot_info in bots_data.items():
                    bot_data = BotData(
                        bot_info['owner_id'],
                        bot_info['bot_token'],
                        bot_info['admin_id'],
                        bot_info.get('channel_username', ""),
                        bot_info.get('developer_username', ""),
                        bot_info.get('bot_name', ""),
                        bot_info.get('bot_username', bot_id)
                    )
                    bot_data.banned_users = set(bot_info.get('banned_users', []))
                    bot_data.muted_users = set(bot_info.get('muted_users', []))
                    bot_data.mandatory_channels = bot_info.get('mandatory_channels', [])
                    bot_data.registered_users = set(bot_info.get('registered_users', []))
                    bot_data.users_counter = bot_info.get('users_counter', 0)
                    bot_data.active_effect_id = bot_info.get('message_effect_id', "5104841245755180586")
                    bot_data.welcome_photo_id = bot_info.get('welcome_photo', "https://i.top4top.io/p_3792b7wla1.jpg")
                    bot_data.sub_admins = set(bot_info.get('sub_admins', []))
                    bot_data.auto_forward = bot_info.get('auto_forward', True)
                    bot_data.typing_indicator = bot_info.get('typing_indicator', True)
                    bot_data.reply_mode = bot_info.get('reply_mode', True)
                    bot_data.receipt_message = bot_info.get('receipt_message', "تم استلام رسالتك بنجاح، سيتم الرد عليك في أقرب وقت.")
                    bot_data.welcome_caption = bot_info.get('welcome_caption', "")
                    bot_data.banned_media_types = bot_info.get('banned_media_types', [])
                    self.instances[bot_id] = BotInstance(bot_data, self)
                print(f"✅ Loaded {len(self.instances)} bots")
        except Exception as e:
            print(f"load error: {e}")

    def _save_all_data(self) -> None:
        try:
            serialized_bots = {}
            for bot_id, instance in self.instances.items():
                data = instance.data
                serialized_bots[bot_id] = {
                    'owner_id': data.owner_id,
                    'bot_token': data.token,
                    'admin_id': data.admin_id,
                    'channel_username': data.channel_username,
                    'developer_username': data.developer_username,
                    'bot_name': data.bot_name,
                    'bot_username': data.bot_username,
                    'banned_users': list(data.banned_users),
                    'muted_users': list(data.muted_users),
                    'mandatory_channels': data.mandatory_channels,
                    'registered_users': list(data.registered_users),
                    'users_counter': data.users_counter,
                    'message_effect_id': data.active_effect_id,
                    'welcome_photo': data.welcome_photo_id,
                    'sub_admins': list(data.sub_admins),
                    'auto_forward': data.auto_forward,
                    'typing_indicator': data.typing_indicator,
                    'reply_mode': data.reply_mode,
                    'receipt_message': data.receipt_message,
                    'welcome_caption': data.welcome_caption,
                    'banned_media_types': data.banned_media_types
                }
            factory_meta = {
                'banned_users': list(self.banned_users),
                'users': list(self.all_users),
                'maintenance_mode': self.maintenance_mode,
                'factory_channels': self.factory_channels
            }
            with open(_DATA_FILE, 'w', encoding='utf-8') as file:
                json.dump(
                    {'bots': serialized_bots, 'factory_data': factory_meta},
                    file,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            print(f"save error: {e}")

    def _validate_bot_token(self, token: str) -> Tuple[bool, Any]:
        try:
            test_bot = telebot.TeleBot(token)
            bot_info = test_bot.get_me()
            return True, (bot_info.first_name or "Bot", bot_info.username or "unknown")
        except Exception as e:
            return False, str(e)

    def _create_new_bot(self, owner_id: int, token: str, admin_id: int,
                        channel: str = "", developer: str = "") -> Tuple[bool, Any]:
        if not admin_id:
            admin_id = owner_id
        is_valid, result = self._validate_bot_token(token)
        if not is_valid:
            return False, f"توكن غير صحيح: {result}"
        bot_name, bot_username = result
        bot_data = BotData(owner_id, token, admin_id, channel, developer, bot_name, bot_username)
        instance = BotInstance(bot_data, self)
        self.instances[bot_username] = instance
        self._save_all_data()
        self._start_bot_instance(bot_username)
        return True, (bot_name, bot_username)

    def _start_bot_instance(self, bot_id: str) -> bool:
        if bot_id in self.instances:
            instance = self.instances[bot_id]
            if not instance.data.is_running:
                instance.data.is_running = True
                thread = threading.Thread(target=instance.run, daemon=True)
                thread.start()
                return True
        return False

    def _stop_bot_instance(self, bot_id: str) -> bool:
        if bot_id in self.instances:
            instance = self.instances[bot_id]
            if instance.data.is_running:
                instance.stop()
                return True
        return False

    def _delete_bot_instance(self, bot_id: str) -> bool:
        if bot_id in self.instances:
            self._stop_bot_instance(bot_id)
            time.sleep(1)
            del self.instances[bot_id]
            self._save_all_data()
            return True
        return False

    def _handle_token_failure(self, bot_id: str) -> None:
        if bot_id in self.instances:
            instance = self.instances[bot_id]
            try:
                self.bot.send_message(
                    instance.data.admin_id,
                    f"<b>⚠️ تم إيقاف بوتك @{bot_id} بسبب مشكلة في التوكن (401 Unauthorized). "
                    "يرجى التحقق من التوكن أو إعادة إنشاء البوت.</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            self._stop_bot_instance(bot_id)

    def _get_user_bots(self, user_id: int) -> List[Dict[str, Any]]:
        result = []
        for bot_id, instance in self.instances.items():
            if instance.data.owner_id == user_id:
                result.append({
                    'id': bot_id,
                    'running': instance.data.is_running,
                    'users': len(instance.data.registered_users),
                    'name': instance.data.bot_name,
                    'admin_id': instance.data.admin_id,
                    'channel': instance.data.channel_username,
                    'developer': instance.data.developer_username
                })
        return result

    def _check_factory_subscription(self, user_id: int) -> bool:
        if not self.factory_channels:
            return True
        for channel in self.factory_channels:
            try:
                member = self.bot.get_chat_member(f"@{channel}", user_id)
                if not member or member.status not in ('member', 'administrator', 'creator'):
                    return False
            except Exception:
                return False
        return True

    def _send_factory_subscription_prompt(self, chat_id: int) -> None:
        keyboard = InlineKeyboardMarkup()
        for channel in self.factory_channels:
            keyboard.add(_build_button(
                f"اشترك في @{channel}",
                url=f"https://t.me/{channel}"
            ))
        keyboard.add(_build_button(
            "تأكيد الاشتراك",
            callback_data="fac_check_sub"
        ))
        self.bot.send_message(
            chat_id,
            "<b>يرجى الاشتراك في القنوات التالية للمتابعة:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    def _build_factory_admin_keyboard(self) -> InlineKeyboardMarkup:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.row(
            _build_button("الإحصائيات", callback_data="fac_adm_stats"),
            _build_button("إذاعة", callback_data="fac_adm_broadcast")
        )
        kb.row(
            _build_button("حظر مستخدم", callback_data="fac_adm_ban"),
            _build_button("رفع الحظر", callback_data="fac_adm_unban")
        )
        kb.row(
            _build_button("حذف بوت", callback_data="fac_adm_del_bot"),
            _build_button("جميع البوتات", callback_data="fac_adm_all_bots")
        )
        kb.row(
            _build_button("القنوات الإجبارية", callback_data="fac_adm_channels"),
            _build_button("إضافة قناة", callback_data="fac_adm_add_ch")
        )
        maintenance_label = "فتح المصنع" if self.maintenance_mode else "وضع الصيانة"
        kb.row(_build_button(maintenance_label, callback_data="fac_adm_maintenance"))
        return kb

    def _send_factory_admin_panel(self, chat_id: int, message_id: Optional[int] = None) -> None:
        keyboard = self._build_factory_admin_keyboard()
        text = "<b>لوحة تحكم المصنع</b>\n\nاختر الإجراء:"
        if message_id:
            try:
                self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML", reply_markup=keyboard)
                return
            except Exception:
                pass
        self.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)

    def _build_owner_panel_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.row(
            _build_button("إنشاء بوت", callback_data="fac_create"),
            _build_button("بوتاتي", callback_data="fac_my_bots")
        )
        kb.row(
            _build_button("المطور", url="https://t.me/j49_c")
        )
        if user_id == _MASTER_ID:
            kb.row(_build_button("لوحة التحكم", callback_data="fac_admin_panel"))
        return kb

    def _register_factory_handlers(self) -> None:
        bot = self.bot
        factory = self

        @bot.message_handler(commands=['start'])
        def handle_start(message):
            user_id = message.from_user.id
            factory.all_users.add(user_id)
            factory._save_all_data()

            if user_id in factory.banned_users:
                bot.send_message(message.chat.id, "<b>عذراً، أنت محظور من استخدام هذا النظام.</b>", parse_mode="HTML")
                return
            if factory.maintenance_mode and user_id != _MASTER_ID:
                bot.send_message(message.chat.id, "<b>النظام في وضع الصيانة حالياً، يُرجى المحاولة لاحقاً.</b>", parse_mode="HTML")
                return
            if factory.factory_channels and not factory._check_factory_subscription(user_id):
                factory._send_factory_subscription_prompt(message.chat.id)
                return

            keyboard = factory._build_owner_panel_keyboard(user_id)
            first_name = message.from_user.first_name or "المستخدم"
            caption = (
                f"<b>مرحباً بك {first_name} في مصنع بوتات التواصل.</b>\n"
                f"هذا النظام مُقدم من {_CREDIT}.\n"
                "يمكنك إدارة بوتاتك الخاصة من خلال القائمة أدناه."
            )
            bot.send_photo(
                chat_id=message.chat.id,
                photo="https://l.top4top.io/p_3756rj4kc1.jpg",
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard
            )

        @bot.callback_query_handler(func=lambda c: c.data == "fac_check_sub")
        def handle_factory_check_sub(callback):
            user_id = callback.from_user.id
            if factory._check_factory_subscription(user_id):
                bot.answer_callback_query(callback.id, "تم التحقق.")
                bot.delete_message(callback.message.chat.id, callback.message.message_id)
                handle_start(callback.message)
            else:
                bot.answer_callback_query(callback.id, "لم تكتمل الاشتراكات.", show_alert=True)

        @bot.callback_query_handler(func=lambda c: c.data == "fac_admin_panel")
        def handle_admin_panel(callback):
            if callback.from_user.id != _MASTER_ID:
                bot.answer_callback_query(callback.id, "غير مصرح.")
                return
            bot.answer_callback_query(callback.id)
            factory._send_factory_admin_panel(callback.message.chat.id)

        @bot.callback_query_handler(func=lambda c: c.data.startswith("fac_adm_"))
        def handle_factory_admin_actions(callback):
            if callback.from_user.id != _MASTER_ID:
                bot.answer_callback_query(callback.id, "غير مصرح.")
                return
            action = callback.data
            chat_id = callback.message.chat.id

            if action == "fac_adm_stats":
                bot.answer_callback_query(callback.id)
                running_count = sum(1 for i in factory.instances.values() if i.data.is_running)
                stats_text = (
                    "<b>إحصائيات المصنع</b>\n\n"
                    f"المستخدمون: {len(factory.all_users)}\n"
                    f"البوتات: {len(factory.instances)}\n"
                    f"النشطة: {running_count}\n"
                    f"المحظورون: {len(factory.banned_users)}\n"
                    f"قنوات الاشتراك الإجباري: {len(factory.factory_channels)}\n"
                    f"حالة الصيانة: {'مفعلة' if factory.maintenance_mode else 'معطلة'}\n"
                    f"الوقت: {_format_timestamp()}"
                )
                bot.send_message(chat_id, stats_text, parse_mode="HTML")

            elif action == "fac_adm_broadcast":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل الرسالة للإذاعة:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, factory._factory_broadcast)

            elif action == "fac_adm_ban":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل معرف المستخدم لحظره:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, factory._factory_ban_user)

            elif action == "fac_adm_unban":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل معرف المستخدم لرفع الحظر:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, factory._factory_unban_user)

            elif action == "fac_adm_del_bot":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل @معرف البوت أو التوكن لحذفه:</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, factory._factory_delete_bot)

            elif action == "fac_adm_all_bots":
                bot.answer_callback_query(callback.id)
                if not factory.instances:
                    bot.send_message(chat_id, "<b>لا توجد بوتات.</b>", parse_mode="HTML")
                else:
                    lines = []
                    for bid, inst in factory.instances.items():
                        status_icon = "🟢" if inst.data.is_running else "🔴"
                        lines.append(f"{status_icon} @{bid} | المستخدمون: {len(inst.data.registered_users)} | المالك: <code>{inst.data.owner_id}</code>")
                    bot.send_message(chat_id, "<b>قائمة البوتات:</b>\n\n" + "\n".join(lines), parse_mode="HTML")

            elif action == "fac_adm_channels":
                bot.answer_callback_query(callback.id)
                if factory.factory_channels:
                    kb = InlineKeyboardMarkup()
                    for ch in factory.factory_channels:
                        kb.add(_build_button(f"حذف @{ch}", callback_data=f"fac_rmch_{ch}"))
                    channels_list = "\n".join([f"• @{c}" for c in factory.factory_channels])
                    bot.send_message(chat_id, f"<b>القنوات الإجبارية للمصنع:</b>\n{channels_list}", parse_mode="HTML", reply_markup=kb)
                else:
                    bot.send_message(chat_id, "<b>لا توجد قنوات إجبارية.</b>", parse_mode="HTML")

            elif action == "fac_adm_add_ch":
                bot.answer_callback_query(callback.id)
                prompt = bot.send_message(chat_id, "<b>أرسل معرف القناة (@username):</b>", parse_mode="HTML")
                bot.register_next_step_handler(prompt, factory._factory_add_channel)

            elif action == "fac_adm_maintenance":
                factory.maintenance_mode = not factory.maintenance_mode
                factory._save_all_data()
                status_text = "تم تفعيل وضع الصيانة" if factory.maintenance_mode else "تم إلغاء وضع الصيانة"
                bot.answer_callback_query(callback.id, status_text)
                bot.send_message(chat_id, f"<b>{status_text}</b>", parse_mode="HTML")

        @bot.callback_query_handler(func=lambda c: c.data.startswith("fac_rmch_"))
        def handle_factory_remove_channel(callback):
            if callback.from_user.id != _MASTER_ID:
                bot.answer_callback_query(callback.id, "غير مصرح.")
                return
            ch = callback.data.replace("fac_rmch_", "")
            if ch in factory.factory_channels:
                factory.factory_channels.remove(ch)
                factory._save_all_data()
                bot.answer_callback_query(callback.id, f"تم حذف @{ch}")
                bot.edit_message_reply_markup(callback.message.chat.id, callback.message.message_id, reply_markup=InlineKeyboardMarkup())
            else:
                bot.answer_callback_query(callback.id, "غير موجودة")
#witewolf :: @j49_c 
        @bot.callback_query_handler(func=lambda c: c.data == "fac_create")
        def handle_create_bot(callback):
            user_id = callback.from_user.id
            if user_id in factory.banned_users:
                bot.answer_callback_query(callback.id, "محظور من استخدام النظام.")
                return
            if factory.maintenance_mode and user_id != _MASTER_ID:
                bot.answer_callback_query(callback.id, "النظام في وضع الصيانة.")
                return
            bot.answer_callback_query(callback.id)
            prompt = bot.send_message(callback.message.chat.id, "<b>أرسل توكن البوت الجديد من @BotFather:</b>", parse_mode="HTML")
            _SESSION_STORE[callback.message.chat.id] = {'step': 'token', 'owner_id': user_id}
            bot.register_next_step_handler(prompt, factory._creation_step_token)

        @bot.callback_query_handler(func=lambda c: c.data == "fac_my_bots")
        def handle_my_bots(callback):
            bot.answer_callback_query(callback.id)
            user_id = callback.message.chat.id
            user_bots = factory._get_user_bots(user_id)
            if not user_bots:
                bot.send_message(user_id, "<b>لا تملك أي بوتات حالياً.</b>", parse_mode="HTML")
                return
            for b in user_bots:
                kb = InlineKeyboardMarkup(row_width=2)
                kb.row(
                    _build_button("إعدادات البوت", callback_data=f"fac_bot_settings_{b['id']}"),
                    _build_button("حذف البوت", callback_data=f"fac_del_{b['id']}")
                )
                status_text = "نشط" if b['running'] else "متوقف"
                info_text = f"<b>@{b['id']}</b>\nالمستخدمون: {b['users']}\nالحالة: {status_text}"
                bot.send_message(user_id, info_text, parse_mode="HTML", reply_markup=kb)

        @bot.callback_query_handler(func=lambda c: c.data.startswith("fac_bot_settings_"))
        def handle_bot_settings(callback):
            bot.answer_callback_query(callback.id)
            user_id = callback.message.chat.id
            target_bot_id = callback.data.replace("fac_bot_settings_", "")
            if target_bot_id in factory.instances:
                inst = factory.instances[target_bot_id]
                if inst.data.owner_id == user_id:
                    d = inst.data
                    settings_text = (
                        f"<b>إعدادات @{target_bot_id}</b>\n\n"
                        f"المشرف: <code>{d.admin_id}</code>\n"
                        f"القناة: @{d.channel_username}\n"
                        f"المطور: @{d.developer_username}\n"
                        f"المستخدمون: {len(d.registered_users)}\n"
                        f"المحظورون: {len(d.banned_users)}\n"
                        f"المكتومون: {len(d.muted_users)}\n"
                        f"القنوات الإجبارية: {len(d.mandatory_channels)}\n"
                        f"الحالة: {'نشط' if d.is_running else 'متوقف'}"
                    )
                    bot.send_message(user_id, settings_text, parse_mode="HTML")
                else:
                    bot.send_message(user_id, "<b>لا تملك صلاحية الوصول لهذا البوت.</b>", parse_mode="HTML")

        @bot.callback_query_handler(func=lambda c: c.data.startswith("fac_del_"))
        def handle_delete_bot(callback):
            bot.answer_callback_query(callback.id)
            user_id = callback.message.chat.id
            target_bot_id = callback.data.replace("fac_del_", "")
            if target_bot_id in factory.instances:
                inst = factory.instances[target_bot_id]
                if inst.data.owner_id == user_id:
                    kb = InlineKeyboardMarkup(row_width=2)
                    kb.row(
                        _build_button("نعم، احذف", callback_data=f"fac_confirm_del_{target_bot_id}"),
                        _build_button("إلغاء", callback_data="fac_cancel_del")
                    )
                    bot.send_message(user_id, f"<b>تأكيد حذف @{target_bot_id}؟</b>\nلا يمكن التراجع عن هذا الإجراء.", parse_mode="HTML", reply_markup=kb)
                else:
                    bot.send_message(user_id, "<b>لا تملك صلاحية حذف هذا البوت.</b>", parse_mode="HTML")
            else:
                bot.send_message(user_id, "<b>البوت غير موجود.</b>", parse_mode="HTML")

        @bot.callback_query_handler(func=lambda c: c.data.startswith("fac_confirm_del_"))
        def handle_confirm_delete(callback):
            bot.answer_callback_query(callback.id)
            user_id = callback.message.chat.id
            target_bot_id = callback.data.replace("fac_confirm_del_", "")
            if target_bot_id in factory.instances:
                inst = factory.instances[target_bot_id]
                if inst.data.owner_id == user_id:
                    if factory._delete_bot_instance(target_bot_id):
                        bot.edit_message_text(chat_id=user_id, message_id=callback.message.message_id, text=f"<b>تم حذف @{target_bot_id} بنجاح.</b>", parse_mode="HTML")
                    else:
                        bot.send_message(user_id, "<b>فشل الحذف.</b>", parse_mode="HTML")
                else:
                    bot.send_message(user_id, "<b>لا تملك الصلاحية.</b>", parse_mode="HTML")
            else:
                bot.send_message(user_id, "<b>البوت غير موجود.</b>", parse_mode="HTML")

        @bot.callback_query_handler(func=lambda c: c.data == "fac_cancel_del")
        def handle_cancel_delete(callback):
            bot.answer_callback_query(callback.id, "تم الإلغاء.")
            bot.edit_message_text(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text="<b>تم إلغاء الحذف.</b>", parse_mode="HTML")

    def _creation_step_token(self, message) -> None:
        user_id = message.chat.id
        token = message.text.strip()
        is_valid, result = self._validate_bot_token(token)
        if not is_valid:
            self.bot.send_message(user_id, f"<b>التوكن غير صحيح:\n{result}</b>", parse_mode="HTML")
            prompt = self.bot.send_message(user_id, "<b>أرسل التوكن الصحيح:</b>", parse_mode="HTML")
            self.bot.register_next_step_handler(prompt, self._creation_step_token)
            return
        bot_name, bot_username = result
        session = _SESSION_STORE.get(user_id, {})
        session['token'] = token
        session['bot_name'] = bot_name
        session['bot_username'] = bot_username
        session['admin_id'] = user_id
        session['step'] = 'channel'
        prompt = self.bot.send_message(
            user_id,
            f"<b>تم التحقق من التوكن.</b>\nالاسم: {bot_name}\nاليوزر: @{bot_username}\n\n"
            f"تم تعيينك كمشرف افتراضي (المعرف: <code>{user_id}</code>).\n\n"
            "أرسل الآن معرف قناتك الرئيسية (@username):",
            parse_mode="HTML"
        )
        self.bot.register_next_step_handler(prompt, self._creation_step_complete)

    def _creation_step_complete(self, message) -> None:
        user_id = message.chat.id
        channel_username = message.text.strip().lstrip('@')
        session = _SESSION_STORE.get(user_id, {})
        developer_username = message.from_user.username or f"user_{user_id}"
        token = session.get('token', '')
        admin_id = session.get('admin_id', user_id)
        owner_id = session.get('owner_id', user_id)
        success, result = self._create_new_bot(owner_id, token, admin_id, channel_username, developer_username)
        if success:
            bot_name, bot_username = result
            success_msg = (
                f"<b>تم إنشاء البوت بنجاح!</b>\n\n"
                f"الاسم: {bot_name}\n"
                f"اليوزر: @{bot_username}\n"
                f"المشرف: {admin_id}\n"
                f"القناة: @{channel_username}\n"
                f"المطور: @{developer_username}"
            )
            self.bot.send_message(user_id, success_msg, parse_mode="HTML")
            if user_id != _MASTER_ID:
                try:
                    ui = message.from_user
                    notif = (
                        "<b>بوت جديد</b>\n\n"
                        f"المالك: {ui.first_name or 'غير معروف'}\n"
                        f"معرفه: <code>{user_id}</code>\n"
                        f"البوت: {bot_name} (@{bot_username})\n"
                        f"القناة: @{channel_username}\n"
                        f"المطور: @{developer_username}"
                    )
                    self.bot.send_message(_MASTER_ID, notif, parse_mode="HTML")
                except Exception:
                    pass
        else:
            self.bot.send_message(user_id, f"<b>فشل إنشاء البوت:\n{result}</b>", parse_mode="HTML")
        if user_id in _SESSION_STORE:
            del _SESSION_STORE[user_id]

    def _factory_broadcast(self, message) -> None:
        if message.chat.id != _MASTER_ID:
            return
        sc = 0
        fc = 0
        pm = self.bot.send_message(_MASTER_ID, "<b>جاري الإذاعة...</b>", parse_mode="HTML")
        for uid in list(self.all_users):
            if uid == _MASTER_ID:
                continue
            try:
                if message.text:
                    self.bot.send_message(uid, message.text, parse_mode="HTML")
                elif message.photo:
                    self.bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption or "", parse_mode="HTML")
                elif message.video:
                    self.bot.send_video(uid, message.video.file_id, caption=message.caption or "", parse_mode="HTML")
                elif message.document:
                    self.bot.send_document(uid, message.document.file_id, caption=message.caption or "", parse_mode="HTML")
                elif message.audio:
                    self.bot.send_audio(uid, message.audio.file_id, caption=message.caption or "", parse_mode="HTML")
                elif message.voice:
                    self.bot.send_voice(uid, message.voice.file_id)
                elif message.sticker:
                    self.bot.send_sticker(uid, message.sticker.file_id)
                else:
                    self.bot.forward_message(uid, message.chat.id, message.message_id)
                sc += 1
            except Exception:
                fc += 1
        result = f"<b>اكتملت الإذاعة.\n\nنجاح: {sc}\nفشل: {fc}</b>"
        try:
            self.bot.edit_message_text(chat_id=_MASTER_ID, message_id=pm.message_id, text=result, parse_mode="HTML")
        except Exception:
            self.bot.send_message(_MASTER_ID, result, parse_mode="HTML")

    def _factory_ban_user(self, message) -> None:
        if message.chat.id != _MASTER_ID:
            return
        try:
            target_id = int(message.text.strip())
            self.banned_users.add(target_id)
            self._save_all_data()
            self.bot.reply_to(message, f"<b>تم حظر المستخدم {target_id}</b>", parse_mode="HTML")
        except ValueError:
            self.bot.reply_to(message, "<b>معرف غير صحيح.</b>", parse_mode="HTML")

    def _factory_unban_user(self, message) -> None:
        if message.chat.id != _MASTER_ID:
            return
        try:
            target_id = int(message.text.strip())
            self.banned_users.discard(target_id)
            self._save_all_data()
            self.bot.reply_to(message, f"<b>تم رفع الحظر عن المستخدم {target_id}</b>", parse_mode="HTML")
        except ValueError:
            self.bot.reply_to(message, "<b>معرف غير صحيح.</b>", parse_mode="HTML")

    def _factory_delete_bot(self, message) -> None:
        if message.chat.id != _MASTER_ID:
            return
        input_text = message.text.strip()
        target = None
        if input_text.startswith('@'):
            bu = input_text[1:]
            if bu in self.instances:
                target = bu
        else:
            for bid, inst in self.instances.items():
                if inst.data.token == input_text:
                    target = bid
                    break
            if not target and input_text in self.instances:
                target = input_text
        if target:
            inst = self.instances[target]
            bn = inst.data.bot_name
            oid = inst.data.owner_id
            if self._delete_bot_instance(target):
                self.bot.reply_to(message, f"<b>تم حذف البوت {bn} (@{target})</b>", parse_mode="HTML")
            else:
                self.bot.reply_to(message, "<b>فشل الحذف.</b>", parse_mode="HTML")
        else:
            self.bot.reply_to(message, "<b>لم يتم العثور على البوت.</b>", parse_mode="HTML")

    def _factory_add_channel(self, message) -> None:
        if message.chat.id != _MASTER_ID:
            return
        ch = message.text.strip().lstrip('@')
        self.factory_channels.append(ch)
        self._save_all_data()
        self.bot.reply_to(message, f"<b>تمت إضافة القناة @{ch}</b>", parse_mode="HTML")

    def _start_all_bots(self) -> None:
        for bid in list(self.instances.keys()):
            self._start_bot_instance(bid)
        print(f"✅ Started {len(self.instances)} bots")

    def run(self) -> None:
        self._register_factory_handlers()
        self._start_all_bots()
        print("🚀 Factory is running...")
        while True:
            try:
                self.bot.infinity_polling(timeout=60, long_polling_timeout=60)
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as net_err:
                print(f"Factory network error: {net_err}. Retrying in 10s...")
                time.sleep(10)
            except Exception as ex:
                print(f"Factory polling exception: {ex}. Retrying in 5s...")
                time.sleep(5)


def _acquire_process_lock() -> bool:
    try:
        if os.path.exists(_LOCK_FILE):
            with open(_LOCK_FILE, 'r') as lock_file:
                existing_pid = int(lock_file.read().strip())
            if psutil.pid_exists(existing_pid):
                print(f"⚠️ Already running (PID {existing_pid})")
                return False
            os.remove(_LOCK_FILE)
        with open(_LOCK_FILE, 'w') as lock_file:
            lock_file.write(str(os.getpid()))
        return True
    except Exception as e:
        print(f"lock error: {e}")
        return False


def _release_process_lock() -> None:
    try:
        if os.path.exists(_LOCK_FILE):
            os.remove(_LOCK_FILE)
    except Exception as e:
        print(f"unlock error: {e}")


def _handle_shutdown_signal(signum, frame) -> None:
    print("\n📢 Shutting down...")
    _release_process_lock()
    sys.exit(0)


signal.signal(signal.SIGINT, _handle_shutdown_signal)
signal.signal(signal.SIGTERM, _handle_shutdown_signal)

if __name__ == "__main__":
    if not _acquire_process_lock():
        print("❌ Cannot run another instance")
        sys.exit(1)

    factory_instance = None
    try:
        factory_instance = FactoryBot()
        factory_instance.run()
    except Exception as e:
        print(f"fatal error: {e}")
    finally:
        if factory_instance:
            factory_instance._save_all_data()
        _release_process_lock()
        #witewolf :: @j49_c 