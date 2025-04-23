import asyncio
import json
import os
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction
from pytz import timezone
from datetime import datetime

api_id = 23148567
api_hash = "af20a7311061aa46ab9e01de54444fdf"
phone = "+989214574165"

client = TelegramClient('session_name', api_id, api_hash)

active_chats_file = "active_chats.json"
blocked_users_file = "blocked_users.json"
terminal_config_file = "terminal_config.json"

# چک کردن فایل‌های JSON و بارگذاری داده‌ها با مدیریت خطا
def load_json(file_name, default_value):
    if os.path.exists(file_name):
        try:
            with open(file_name, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, ValueError):
            return default_value
    else:
        return default_value

active_chats = load_json(active_chats_file, set())
blocked_users = load_json(blocked_users_file, set())

# بارگذاری تنظیمات ترمینال
def load_terminal_config():
    if os.path.exists(terminal_config_file):
        try:
            with open(terminal_config_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

terminal_config = load_terminal_config()

def save_active_chats():
    with open(active_chats_file, "w") as f:
        json.dump(list(active_chats), f)

def save_blocked_users():
    with open(blocked_users_file, "w") as f:
        json.dump(list(blocked_users), f)

def save_terminal_config():
    with open(terminal_config_file, "w") as f:
        json.dump(terminal_config, f)

async def show_typing(chat_id, duration=4):
    try:
        await client(SetTypingRequest(peer=chat_id, action=SendMessageTypingAction()))
        await asyncio.sleep(duration)
    except:
        pass

async def send_terminal_loop(chat_id):
    while True:
        config = terminal_config.get(str(chat_id), {})
        if not config.get("enabled"):
            break
        message = config.get("message")
        interval = config.get("interval", 60)
        if message:
            try:
                await client.send_message(chat_id, message)
            except:
                pass
        await asyncio.sleep(interval)

@client.on(events.NewMessage())
async def auto_responder(event):
    sender = await event.get_sender()
    me = await client.get_me()
    msg = event.raw_text.strip().lower()
    is_private = event.is_private
    is_group = event.is_group
    is_owner = sender.id == me.id

    if is_private:
        if msg == "بلاک":
            blocked_users.add(sender.id)
            save_blocked_users()
            await event.respond("شما بلاک شدید.")
            await event.delete()
        elif msg == "آن بلاک":
            blocked_users.discard(sender.id)
            save_blocked_users()
            await event.respond("شما آن‌بلاک شدید.")
            await event.delete()
        elif sender.id in blocked_users:
            await event.delete()
        return

    if not is_group or sender.bot:
        return

    # تنظیم ترمینال
    if msg == "تنظیم ترمینال" and is_owner and event.is_reply:
        replied = await event.get_reply_message()
        terminal_config[str(event.chat_id)] = {"message": replied.message, "enabled": False, "interval": 60}
        save_terminal_config()
        await event.reply("پیام ترمینال تنظیم شد.")

    # ترمینال روشن X
    elif msg.startswith("ترمینال روشن") and is_owner:
        try:
            interval = int(msg.split("ترمینال روشن")[1].strip())
        except:
            interval = 60
        if str(event.chat_id) in terminal_config:
            terminal_config[str(event.chat_id)]["enabled"] = True
            terminal_config[str(event.chat_id)]["interval"] = interval
            save_terminal_config()
            await event.reply(f"ترمینال با فاصله {interval} ثانیه روشن شد.")
            asyncio.create_task(send_terminal_loop(event.chat_id))
        else:
            await event.reply("اول با ریپلای روی پیام، دستور 'تنظیم ترمینال' رو بفرست.")

    elif msg == "ترمینال خاموش" and is_owner:
        if str(event.chat_id) in terminal_config:
            terminal_config[str(event.chat_id)]["enabled"] = False
            save_terminal_config()
            await event.reply("ترمینال خاموش شد.")

    # بقیه دستورات
    elif msg == "سلف روشن" and is_owner:
        active_chats.add(event.chat_id)
        save_active_chats()
        await event.reply("پاسخ خودکار در این گروه فعال شد.")
    elif msg == "سلف خاموش" and is_owner:
        active_chats.discard(event.chat_id)
        save_active_chats()
        await event.reply("پاسخ خودکار در این گروه غیرفعال شد.")
    elif msg == "لیست" and is_owner:
        groups = "\n".join(str(cid) for cid in active_chats)
        await event.reply(f"گروه‌های فعال:\n{groups or 'هیچ‌کدام'}")
    elif msg == "دستورها" and is_owner:
        await event.reply("""دستورهای ربات:

- سلف روشن / سلف خاموش
- لیست
- حذف (در ریپلای)
- حذف پیام‌ها
- بی‌پاسخ / باپاسخ (در ریپلای)
- بلاک / آن بلاک (در ریپلای)
- تنظیم ترمینال (در ریپلای)
- ترمینال روشن [زمان]
- ترمینال خاموش
""")
    elif msg == "حذف" and is_owner and event.is_reply:
        replied = await event.get_reply_message()
        if replied.sender_id == me.id:
            try:
                await replied.delete()
                await event.delete()
            except:
                await event.reply("نتونستم حذف کنم.")
    elif msg == "حذف پیام‌ها" and is_owner:
        count = 0
        async for m in client.iter_messages(event.chat_id, from_user=me.id):
            try:
                await m.delete()
                count += 1
                await asyncio.sleep(0.1)
            except:
                continue
        await event.reply(f"{count} پیام حذف شد.")
    elif msg == "بی‌پاسخ" and is_owner and event.is_reply:
        replied = await event.get_reply_message()
        blocked_users.add(replied.sender_id)
        save_blocked_users()
        await event.reply("دیگه به این کاربر پاسخ داده نمی‌شه.")
    elif msg == "باپاسخ" and is_owner and event.is_reply:
        replied = await event.get_reply_message()
        blocked_users.discard(replied.sender_id)
        save_blocked_users()
        await event.reply("پاسخ‌گویی به این کاربر فعال شد.")
    elif msg == "بلاک" and is_owner and event.is_reply:
        replied = await event.get_reply_message()
        blocked_users.add(replied.sender_id)
        save_blocked_users()
        await event.reply("کاربر بلاک شد.")
    elif msg == "آن بلاک" and is_owner and event.is_reply:
        replied = await event.get_reply_message()
        blocked_users.discard(replied.sender_id)
        save_blocked_users()
        await event.reply("کاربر آن‌بلاک شد.")

    elif event.chat_id in active_chats:
        sender_id = sender.id
        is_reply = event.is_reply
        reply_ok = False
        if is_reply:
            replied = await event.get_reply_message()
            if replied and replied.sender_id == me.id:
                reply_ok = True
        if (not is_reply or reply_ok) and sender_id not in blocked_users:
            await show_typing(event.chat_id)
            await asyncio.sleep(1.5)
            if msg == "سلام":
                await event.reply("درود")
            elif msg == ".":
                await event.reply(".")
            elif msg == "😐":
                await event.reply("😐")
            elif msg in ["خوبی", "چطوری"]:
                await event.reply("تنکس")
            elif "اصل" in msg or "ربات" in msg:
                if is_reply and replied.sender_id == me.id:
                    if "اصل" in msg:
                        await event.reply("پپوله 18 گنبد کاووس")
                    elif "ربات" in msg:
                        await event.reply("داری به توهینم شعور می‌کنی؟")

def convert_to_fancy_number(text):
    fancy = {"0": "𝟘", "1": "𝟙", "2": "𝟚", "3": "𝟛", "4": "𝟜", "5": "𝟝", "6": "𝟞", "7": "𝟟", "8": "𝟠", "9": "𝟡", ":": ":"}
    return ''.join(fancy.get(c, c) for c in text)

async def update_profile():
    tehran = timezone('Asia/Tehran')
    base_name = "باتِر؋ـلای‌بوے𐦍"
    while True:
        now = datetime.now(tehran).strftime("%H:%M")
        fancy_time = convert_to_fancy_number(now)
        full_name = f"{base_name} | {fancy_time}"
        try:
            await client(UpdateProfileRequest(first_name=full_name))
        except:
            pass
        await asyncio.sleep(60 - datetime.now().second)

async def main():
    await client.start(phone)
    client.loop.create_task(update_profile())
    await client.run_until_disconnected()

client.loop.run_until_complete(main())
