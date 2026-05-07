import asyncio
import os
import html
import random
import time
import logging

from datetime import datetime
from collections import defaultdict

from dotenv import load_dotenv
from groq import Groq

from telegram import (
    Bot,
    Update,
    Poll,
    BotCommand
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

from news_fetcher import get_latest_news

from database import (
    already_posted,
    save_post,
    save_scrim_result,
    get_last_scrim,
    is_banned,
    ban_user
)

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# ENV
# ─────────────────────────────────────────────

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ADMIN_IDS = [
    int(x)
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x
]

groq_client = Groq(api_key=GROQ_API_KEY)

user_last_request = defaultdict(float)

RATE_LIMIT_SECONDS = 10
MAX_QUESTION_LENGTH = 300

# ─────────────────────────────────────────────
# YOUTUBE CACHE
# ─────────────────────────────────────────────

_yt_cache = []
_yt_cache_time = 0

YT_CACHE_SECONDS = 7200  # 2 hours


def get_youtube_videos():
    """
    Cached YouTube fetcher.
    Prevents hammering APIs repeatedly.
    """

    global _yt_cache
    global _yt_cache_time

    if time.time() - _yt_cache_time < YT_CACHE_SECONDS:
        logger.info("Using cached YouTube results")
        return _yt_cache

    logger.info("Fetching fresh YouTube videos")

    updates = [
        # your fetch logic here
    ]

    _yt_cache = updates
    _yt_cache_time = time.time()

    return _yt_cache


# ─────────────────────────────────────────────
# AI SYSTEM PROMPT
# ─────────────────────────────────────────────

CODM_SYSTEM_PROMPT = """
You are CODMIntelHQ, an expert Call of Duty Mobile assistant.

You ONLY answer questions about Call of Duty Mobile.

Topics:
weapons, loadouts, ranked mode, operators,
seasonal updates, tournaments, maps, modes,
leaks, patch notes, battle pass, CP, clans, esports.

If asked anything NOT CODM related reply:
'⚠️ I only cover Call of Duty Mobile topics!'

Keep answers sharp, punchy, helpful.
Max 3 paragraphs.
"""

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def is_admin(user_id):
    return user_id in ADMIN_IDS


def is_rate_limited(user_id):
    now = time.time()

    if now - user_last_request[user_id] < RATE_LIMIT_SECONDS:
        return True

    user_last_request[user_id] = now
    return False


def ai_answer(question):
    chat = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": CODM_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": question
            }
        ],
        max_tokens=300
    )

    return chat.choices[0].message.content


# ─────────────────────────────────────────────
# AUTO POSTER
# ─────────────────────────────────────────────

async def post_updates(context: ContextTypes.DEFAULT_TYPE = None):
    bot = Bot(token=BOT_TOKEN)

    logger.info("Fetching latest news")

    news = get_latest_news()

    posted_count = 0

    for item in news:
        if posted_count >= 4:
            break

        if not already_posted(item["link"]):

            safe_title = html.escape(item["title"])

            caption = (
                f"{safe_title}\n\n"
                f"🔗 {item['link']}\n\n"
                f"📡 Source: {item['source']}\n"
                f"#CODM #CallOfDutyMobile\n\n"
                f"<i>⚠️ Automated update. Verify info.</i>"
            )

            try:
                if item.get("image"):

                    await bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=item["image"],
                        caption=caption,
                        parse_mode="HTML"
                    )

                else:
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=caption,
                        parse_mode="HTML"
                    )

                save_post(item["link"])

                posted_count += 1

                logger.info(f"Posted: {item['title']}")

                await asyncio.sleep(4)

            except Exception as e:
                logger.error(f"Post error: {e}")

    logger.info(f"Auto-posted {posted_count} updates")


# ─────────────────────────────────────────────
# PUBLIC COMMANDS
# ─────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if is_banned(update.effective_user.id):
        return

    name = update.effective_user.first_name

    msg = (
        f"👋 Yo {name}! Welcome to *CODMIntelHQ* 🎮\n\n"
        f"Your #1 source for CODM news, scrims and meta.\n\n"
        f"Use /ask to ask anything CODM 🔥"
    )

    await update.message.reply_text(
        msg,
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────
# ASK COMMAND
# ─────────────────────────────────────────────

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if is_banned(update.effective_user.id):
        return

    if is_rate_limited(update.effective_user.id):

        await update.message.reply_text(
            "⏳ Wait a few seconds before asking again."
        )

        return

    if not context.args:

        await update.message.reply_text(
            "🎮 Usage: /ask [question]"
        )

        return

    question = " ".join(context.args).strip()

    # HARD CHARACTER LIMIT
    question = question[:MAX_QUESTION_LENGTH]

    logger.info(
        f"/ask from {update.effective_user.id}: {question}"
    )

    try:
        answer = ai_answer(question)

        await update.message.reply_text(
            f"🎮 {answer}"
        )

    except Exception as e:

        logger.error(f"AI error: {e}")

        await update.message.reply_text(
            "⚠️ AI temporarily unavailable."
        )


# ─────────────────────────────────────────────
# LOADOUT COMMAND
# ─────────────────────────────────────────────

async def loadout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if is_banned(update.effective_user.id):
        return

    if is_rate_limited(update.effective_user.id):

        await update.message.reply_text(
            "⏳ Wait a few seconds before asking again."
        )

        return

    weapon = (
        " ".join(context.args).strip()
        if context.args else
        "any weapon"
    )

    # HARD CHARACTER LIMIT
    weapon = weapon[:100]

    try:

        answer = ai_answer(
            f"Give me the best competitive loadout "
            f"with attachments for {weapon} "
            f"in CODM ranked mode."
        )

        await update.message.reply_text(
            f"🔧 *Loadout: {weapon.upper()}*\n\n{answer}",
            parse_mode="Markdown"
        )

    except Exception as e:

        logger.error(f"Loadout error: {e}")

        await update.message.reply_text(
            "⚠️ Try again later."
        )


# ─────────────────────────────────────────────
# BAN COMMAND
# ─────────────────────────────────────────────

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):

        await update.message.reply_text(
            "⛔ Admin only."
        )

        return

    if not context.args:

        await update.message.reply_text(
            "Usage: /ban [user_id]"
        )

        return

    try:

        user_id = int(context.args[0])

        ban_user(user_id)

        logger.warning(f"User banned: {user_id}")

        await update.message.reply_text(
            f"✅ User {user_id} banned permanently."
        )

    except ValueError:

        await update.message.reply_text(
            "⚠️ Invalid user ID."
        )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():

    app = Application.builder().token(BOT_TOKEN).build()

    # Public Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("loadout", loadout_command))

    # Admin Commands
    app.add_handler(CommandHandler("ban", ban_command))

    # Auto poster
    app.job_queue.run_repeating(
        post_updates,
        interval=14400,
        first=10
    )

    async def set_commands(app):

        await app.bot.set_my_commands([
            BotCommand("start", "Start bot"),
            BotCommand("ask", "Ask CODM question"),
            BotCommand("loadout", "Best weapon build"),
        ])

    app.post_init = set_commands

    logger.info("✅ CODMIntelHQ running")
    logger.info("📡 Auto-posting enabled")
    logger.info("🎮 Commands loaded")

    app.run_polling()


if __name__ == "__main__":
    main()