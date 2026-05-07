import asyncio
import os
import html
from groq import Groq
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from news_fetcher import get_latest_news
from database import already_posted, save_post

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CODM_SYSTEM_PROMPT = """
You are CODMIntelHQ, an expert Call of Duty Mobile assistant.
You ONLY answer questions about Call of Duty Mobile.
Topics: weapons, loadouts, ranked mode, operators, seasonal updates,
tournaments, maps, modes, leaks, patch notes, battle pass, CP, clans, esports.
If asked anything NOT CODM related, reply:
'⚠️ I only cover Call of Duty Mobile topics. Ask me about loadouts, ranked, operators, or anything CODM!'
Keep answers sharp, punchy, helpful. Max 3 paragraphs.
"""

groq_client = Groq(api_key=GROQ_API_KEY)


async def post_updates():
    bot = Bot(token=BOT_TOKEN)
    news = get_latest_news()
    posted_count = 0

    for item in news:
        if not already_posted(item["link"]):
            safe_title = html.escape(item["title"])

            caption = (
                f"{safe_title}\n\n"
                f"🔗 {item['link']}\n\n"
                f"📡 Source: {item['source']}\n"
                f"#CODM #CallOfDutyMobile\n\n"
                f"<i>⚠️ Automated update. Always verify before acting on any info.</i>"
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

                await asyncio.sleep(3)

            except Exception as e:
                print(f"Post error: {e}")

    print(f"Posted {posted_count} new updates.")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🎮 Usage: /ask [your question]\n"
            "Example: /ask best SMG for ranked?"
        )
        return

    question = " ".join(context.args)

    print(f"Question received: {question}")

    try:
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

        answer = chat.choices[0].message.content

        await update.message.reply_text(f"🎮 {answer}")

    except Exception as e:
        print(f"AI error: {e}")

        await update.message.reply_text(
            "⚠️ Couldn't process that right now. Try again in a moment."
        )


def run_bot_with_commands():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("ask", ask_command))

    print("✅ Bot listening for /ask commands...")

    app.run_polling()