import logging
import os
from telegram import ForceReply, Update, Message
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import random
import threading
import qq_to_telegram

from httpx import AsyncClient

client = AsyncClient()

BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN")
BRIDGE_URL = os.environ.get("BRIDGE_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TARGET_GROUP_ID = int(os.environ.get("TARGET_GROUP_ID"))
BRIDGE_THREAD_ID = int(os.environ.get("BRIDGE_THREAD_ID"))
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID"))
ADMIN_NICKNAME = os.environ.get("ADMIN_NICKNAME")

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
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


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
    await client.post(
        f"{BRIDGE_URL}/send_group_msg",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {BRIDGE_TOKEN}",
        },
        json={
            "group_id": int(TARGET_GROUP_ID),
            "message": f"[{name}]: {message.text}",
        },
    )


def main() -> None:
    """Start the bot."""
    threading.Thread(target=qq_to_telegram.run).start()

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
