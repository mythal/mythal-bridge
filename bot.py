import logging
import os
import asyncio
from telegram import Bot, ForceReply, Update, Message
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import tempfile
import random
import json
from httpx import AsyncClient, RemoteProtocolError

client = AsyncClient()

BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN")
BRIDGE_URL = os.environ.get("BRIDGE_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
QQ_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID"))
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID"))
ADMIN_NICKNAME = os.environ.get("ADMIN_NICKNAME")
TELEGRAM_CHAT_ID = None
BRIDGE_THREAD_ID = None

qq_to_telegram_msg_map = {}
telegram_to_qq_msg_map = {}

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global TELEGRAM_CHAT_ID, BRIDGE_THREAD_ID
    if not TELEGRAM_CHAT_ID:
        TELEGRAM_CHAT_ID = update.effective_chat.id
        BRIDGE_THREAD_ID = update.effective_message.message_thread_id
        await update.message.reply_text(
            "Start forwarding messages between Telegram and QQ group."
        )
    else:
        await update.message.reply_text(
            "Bot is already started. If you want to change the chat ID, please restart the bot."
        )
        return


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


anonymous_prefix = [
    "无名",
    "匿名",
    "不愿意透露姓名的",
    "未知",
    "神秘的",
    "不能提的",
    "隐姓埋名的",
    "X的",
]
anonymous_suffix = [
    "驼鹿",
    "大象",
    "狮子",
    "老虎",
    "熊猫",
    "长颈鹿",
    "斑马",
    "袋鼠",
    "考拉",
    "企鹅",
    "海豹",
    "海狮",
    "鳄鱼",
    "鳄鱼",
    "蛇",
    "蜥蜴",
    "青蛙",
    "猕猴桃",
    "苹果",
    "香蕉",
    "橘子",
    "葡萄",
    "西瓜",
    "草莓",
    "蓝莓",
    "樱桃",
    "柠檬",
    "菠萝",
    "芒果",
    "桃子",
    "梨子",
    "杏子",
    "李子",
    "柚子",
    "椰子",
    "荔枝",
    "水母",
    "龙虾",
    "螃蟹",
    "章鱼",
    "海星",
    "海胆",
    "海参",
    "海葵",
    "海马",
    "海豚",
    "鲸鱼",
    "鲨鱼",
    "金枪鱼",
    "鳗鱼",
    "鲑鱼",
    "鳕鱼",
    "鲈鱼",
    "鲷鱼",
    "鲭鱼",
    "鲳鱼",
]

async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not BRIDGE_THREAD_ID:
        await update.message.reply_text(
            f"Please start the bot first by sending /start@{context.bot.username} command."
        )
        return
    message = update.message
    if not isinstance(message, Message):
        return
    name = "匿名"
    if message.from_user.id == ADMIN_USER_ID:
        name = ADMIN_NICKNAME
    else:
        # Use user id as seed for random name generation
        rng = random.Random()
        rng.seed(update.effective_user.id)
        prefix = rng.choice(anonymous_prefix)
        suffix = rng.choice(anonymous_suffix)
        name = f"{prefix}{suffix}"
    if message.message_thread_id != BRIDGE_THREAD_ID:
        return
    send_message = []
    if message.text:
        send_message.append({"type": "text", "data": {"text": f"[{name}]: {message.text}"}})
    if message.caption:
        send_message.append({"type": "text", "data": {"text": f"[{name}]: {message.caption}"}})
    if message.photo:
        photo = message.photo[-1]  # Get the highest resolution photo
        photo_file = await photo.get_file()
        if photo_file and photo_file.file_path:
            send_message.append(
                {"type": "image", "data": {"file": photo.file_id, "url": photo_file.file_path}}
            )
        if not message.text and not message.caption:
            send_message.append({"type": "text", "data": {"text": f"[{name}] 发了一张图片"}})
    if message.sticker:
        sticker_file = await message.sticker.get_file()
        if sticker_file and sticker_file.file_path:
            type = "video" if message.sticker.is_video else "image"
            send_message.append(
                {"type": type, "data": {"file": message.sticker.file_id, "url": sticker_file.file_path}}
            )
        sticker_emoji = message.sticker.emoji or "🎭"
        send_message.append({"type": "text", "data": {"text": f"[{name}] 发了一个贴纸 {sticker_emoji}"}})
    if len(send_message) == 0:
        return
    
    sent = await client.post(
        f"{BRIDGE_URL}/send_group_msg",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {BRIDGE_TOKEN}",
        },
        json={
            "group_id": int(QQ_GROUP_ID),
            "message": send_message,
        },
    )
    sent = sent.json()
    logger.info(f"Sent message to QQ group: {sent}")
    sent_message_id = sent.get("data", {}).get("message_id")
    qq_to_telegram_msg_map[sent_message_id] = message.message_id
    telegram_to_qq_msg_map[message.message_id] = sent_message_id

async def handle_qq_event(bot: Bot, event: dict):
    # Example
    # {'self_id': 3474477577, 'user_id': 2962702023, 'time': 1754805255, 'message_id': 556040977, 'message_seq': 16929, 'message_type': 'group', 'sender': {'user_id': 2962702023, 'nickname': '小灯', 'card': '小灯', 'role': 'owner', 'title': ''}, 'raw_message': 'test', 'font': 14, 'sub_type': 'normal', 'message': [{'type': 'text', 'data': {'text': 'test'}}], 'message_format': 'array', 'post_type': 'message', 'group_id': 1107382038}
    if not isinstance(event, dict):
        return
    if not TELEGRAM_CHAT_ID:
        logger.warning("Telegram chat ID is not set. Please start the bot first.")
        return
    message = event.get("message", [])
    text = ""
    images = []
    stickers = []
    for item in message:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            text += item.get("data", {}).get("text", "")
        elif item.get("type") == "image":
            url = item.get("data", {}).get("url", "")
            filename = item.get("data", {}).get("file", "")
            if url and filename:
                logger.info(f"Downloading image from {url}")
                image_resp = await client.get(url)
                if image_resp.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        temp_file.write(image_resp.content)
                        images.append(temp_file.name)
                else:
                    logger.error(f"Failed to download image: {image_resp.status_code}")
        else:
            type = item.get("type", "")
            if type == "":
                continue
            if type == "face":
                text += "[表情]"
            else:
                text += f"[{type}]"
    nickname = event.get("sender", {}).get("nickname", None)
    if not nickname:
        return
    sent = None
    if len(images) == 1:
        image = images[0]
        caption = text or "sent an image"
        sent = await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=image, caption=f"[{nickname}] {caption}", reply_to_message_id=BRIDGE_THREAD_ID)
        try:
            os.remove(image)
        except OSError as e:
            logger.error(f"Error deleting image file {image}: {e}")
        return
    if text:
        sent = await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"[{nickname}]: {text}", reply_to_message_id=BRIDGE_THREAD_ID)
    qq_message_id = event.get("message_id", None)
    if not qq_message_id:
        return
    telegram_to_qq_msg_map[sent.message_id] = qq_message_id
    qq_to_telegram_msg_map[qq_message_id] = sent.message_id


async def listen_qq_events(bot: Bot):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BRIDGE_TOKEN}",
    }
    while True:
        try:
            async with AsyncClient(timeout=None) as client:
                async with client.stream('GET', f'{BRIDGE_URL}/_events', headers=headers) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data:"):
                            data = line.split("data:", 1)[1]
                            data = json.loads(data)
                            await handle_qq_event(bot, data)
        except Exception as e:
            if isinstance(e, RemoteProtocolError):
                logger.debug("Connection closed by the server, retrying...")
            else:
                logger.exception("Error while listening to QQ events: %s", e)

def main() -> None:
    """Start the bot."""

    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.Sticker.ALL) & ~filters.COMMAND, forward))
    loop = asyncio.get_event_loop()
    loop.create_task(listen_qq_events(application.bot))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
