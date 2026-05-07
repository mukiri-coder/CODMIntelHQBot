import asyncio
import os
import html
import random
import time

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
    get_last_scrim
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ADMIN_IDS = [
    int(x)
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x
]

BANNED_IDS = [
    int(x)
    for x in os.getenv("BANNED_IDS", "").split(",")
    if x
]

groq_client = Groq(api_key=GROQ_API_KEY)

user_last_request = defaultdict(float)

RATE_LIMIT_SECONDS = 10

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


def is_banned(user_id):
    return user_id in BANNED_IDS


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
                f"<i>⚠️ Automated update. Always verify info.</i>"
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

                await asyncio.sleep(4)

            except Exception as e:
                print(f"Post error: {e}")

    print(f"[{datetime.now()}] Auto-posted {posted_count} updates.")


# ─────────────────────────────────────────────
# PUBLIC COMMANDS
# ─────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    name = update.effective_user.first_name

    msg = (
        f"👋 Yo {name}! Welcome to *CODMIntelHQ* 🎮\n\n"
        f"Your #1 source for CODM news, loadouts, scrims and more.\n\n"
        f"*Here's what I can do:*\n\n"
        f"🔫 /loadout [weapon] — best attachments\n"
        f"📊 /meta — current ranked meta\n"
        f"❓ /ask [question] — ask me anything CODM\n"
        f"⚔️ /1v1 [@user] — issue a challenge\n"
        f"🏆 /scrim — upcoming scrims\n"
        f"🎖️ /lastscrim — last scrim result\n"
        f"🎯 /trivia — test your CODM knowledge\n\n"
        f"Let's get it! 🔥"
    )

    await update.message.reply_text(
        msg,
        parse_mode="Markdown"
    )


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    if is_rate_limited(update.effective_user.id):
        await update.message.reply_text(
            "⏳ Slow down! Wait a few seconds before asking again."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "🎮 Usage: /ask [question]\n"
            "Example: /ask best SMG for ranked?"
        )
        return

    question = " ".join(context.args)

    print(f"/ask: {question}")

    try:
        answer = ai_answer(question)

        await update.message.reply_text(
            f"🎮 {answer}"
        )

    except Exception as e:
        print(f"AI error: {e}")

        await update.message.reply_text(
            "⚠️ Try again in a moment."
        )


async def loadout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    if is_rate_limited(update.effective_user.id):
        await update.message.reply_text(
            "⏳ Slow down! Wait a few seconds before asking again."
        )
        return

    weapon = (
        " ".join(context.args)
        if context.args else
        "any weapon"
    )

    try:
        answer = ai_answer(
            f"Give me the best competitive loadout "
            f"with attachments for {weapon} "
            f"in CODM ranked mode. Format clearly."
        )

        await update.message.reply_text(
            f"🔧 *Loadout: {weapon.upper()}*\n\n{answer}",
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text(
            "⚠️ Try again in a moment."
        )


async def meta_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    if is_rate_limited(update.effective_user.id):
        await update.message.reply_text(
            "⏳ Slow down! Wait a few seconds before asking again."
        )
        return

    try:
        answer = ai_answer(
            "What is the current CODM ranked meta? "
            "List top 3 weapons per category: "
            "AR, SMG, Sniper. "
            "Be brief and punchy."
        )

        await update.message.reply_text(
            f"📊 *Current Meta*\n\n{answer}",
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text(
            "⚠️ Try again in a moment."
        )


async def challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    challenger = update.effective_user.first_name

    target = (
        " ".join(context.args)
        if context.args else
        "anyone brave enough"
    )

    msg = (
        f"⚔️ *1v1 CHALLENGE ISSUED!*\n\n"
        f"🔥 {challenger} is calling out {target}!\n\n"
        f"📍 Mode: Search & Destroy\n"
        f"🗺️ Map: Standoff\n"
        f"💀 First to 5 kills wins\n\n"
        f"Do you accept? Reply below 👇\n"
        f"#CODM1v1 #CODMIntelHQ"
    )

    await update.message.reply_text(
        msg,
        parse_mode="Markdown"
    )


async def scrim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    msg = (
        f"🏆 *Upcoming Scrims Schedule*\n\n"
        f"📅 Saturday 8PM EAT — 5v5 Hardpoint\n"
        f"📅 Sunday 6PM EAT — Search & Destroy\n"
        f"📅 Monday 9PM EAT — TDM Blitz\n\n"
        f"📝 To register: DM @CODMIntelHQ\n"
        f"💰 Entry: Free\n"
        f"🏅 Prize: Bragging rights + shoutout\n\n"
        f"#CODMScrims #CODMKenya"
    )

    await update.message.reply_text(
        msg,
        parse_mode="Markdown"
    )


async def lastscrim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    result = get_last_scrim()

    if result:
        msg = (
            f"🏆 *Last Scrim Result*\n\n"
            f"🗓️ {result['date']}\n"
            f"🎮 Mode: {result['mode']}\n"
            f"🥇 Winner: *{result['winner']}*\n"
            f"💀 Score: {result['score']}\n"
            f"⭐ MVP: {result['mvp']}\n\n"
            f"#CODMScrims #CODMIntelHQ"
        )

    else:
        msg = (
            "No scrim results recorded yet. "
            "Check back after the next scrim! 🎮"
        )

    await update.message.reply_text(
        msg,
        parse_mode="Markdown"
    )


async def trivia_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    questions = [
        (
            "Which map is most popular for ranked Hardpoint?",
            ["Standoff", "Rust", "Hackney Yard", "Monastery"],
            0
        ),
        (
            "What does SMG stand for?",
            [
                "Sub Machine Gun",
                "Super Mega Gun",
                "Sniper Master Grade",
                "Speed Mobility Gun"
            ],
            0
        ),
        (
            "Which mode has bomb defusal?",
            [
                "Search & Destroy",
                "Hardpoint",
                "Domination",
                "TDM"
            ],
            0
        ),
        (
            "What rank comes after Legendary?",
            [
                "There is none",
                "Champion",
                "Master",
                "Elite"
            ],
            0
        ),
    ]

    q, options, correct = random.choice(questions)

    await update.message.reply_poll(
        question=f"🎮 CODM Trivia: {q}",
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct,
        is_anonymous=False
    )


# ─────────────────────────────────────────────
# ADMIN COMMANDS
# ─────────────────────────────────────────────

async def postnow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Admin only."
        )
        return

    await update.message.reply_text(
        "📡 Fetching and posting now..."
    )

    await post_updates()

    await update.message.reply_text(
        "✅ Done!"
    )


async def setposts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Admin only."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /setposts [number]"
        )
        return

    context.bot_data["posts_per_batch"] = int(context.args[0])

    await update.message.reply_text(
        f"✅ Posts per batch set to {context.args[0]}"
    )


async def announce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Admin only."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /announce [message]"
        )
        return

    msg = " ".join(context.args)

    bot = Bot(token=BOT_TOKEN)

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=(
            f"📢 *ANNOUNCEMENT*\n\n"
            f"{msg}\n\n"
            f"#CODMIntelHQ"
        ),
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ Announced!"
    )


async def scrimresult_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Admin only."
        )
        return

    if len(context.args) < 5:
        await update.message.reply_text(
            "Usage: /scrimresult [winner] [score] "
            "[loser] [mvp] [mode]"
        )
        return

    winner, score, loser, mvp, mode = context.args[:5]

    date = datetime.now().strftime("%d %b %Y")

    save_scrim_result(
        date,
        mode,
        winner,
        score,
        mvp
    )

    bot = Bot(token=BOT_TOKEN)

    msg = (
        f"🏆 *SCRIM RESULTS*\n\n"
        f"🗓️ {date}\n"
        f"🎮 Mode: {mode}\n"
        f"🥇 Winner: *{winner}*\n"
        f"💀 Score: {score} vs {loser}\n"
        f"⭐ MVP: {mvp}\n\n"
        f"GGs to both teams! 🔥\n"
        f"#CODMScrims #CODMIntelHQ"
    )

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=msg,
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ Result posted to channel!"
    )


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return

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

    user_id = int(context.args[0])

    BANNED_IDS.append(user_id)

    await update.message.reply_text(
        f"✅ User {user_id} banned."
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
    app.add_handler(CommandHandler("meta", meta_command))
    app.add_handler(CommandHandler("1v1", challenge_command))
    app.add_handler(CommandHandler("scrim", scrim_command))
    app.add_handler(CommandHandler("lastscrim", lastscrim_command))
    app.add_handler(CommandHandler("trivia", trivia_command))

    # Admin Commands
    app.add_handler(CommandHandler("postnow", postnow_command))
    app.add_handler(CommandHandler("setposts", setposts_command))
    app.add_handler(CommandHandler("announce", announce_command))
    app.add_handler(CommandHandler("scrimresult", scrimresult_command))
    app.add_handler(CommandHandler("ban", ban_command))

    # Auto-post every 4 hours
    app.job_queue.run_repeating(
        post_updates,
        interval=14400,
        first=10
    )

    # Telegram command menu
    async def set_commands(app):
        await app.bot.set_my_commands([
            BotCommand("start", "Start the bot"),
            BotCommand("ask", "Ask any CODM question"),
            BotCommand("loadout", "Best loadout"),
            BotCommand("meta", "Current ranked meta"),
            BotCommand("1v1", "Challenge someone"),
            BotCommand("scrim", "Upcoming scrims"),
            BotCommand("lastscrim", "Last scrim result"),
            BotCommand("trivia", "Play CODM trivia"),
        ])

    app.post_init = set_commands

    print("✅ CODMIntelHQ Bot fully running...")
    print("📡 Auto-posting every 4 hours")
    print("🎮 Commands active")

    app.run_polling()


if __name__ == "__main__":
    main()