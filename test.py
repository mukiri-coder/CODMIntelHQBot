import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    await bot.send_message(chat_id=os.getenv("CHANNEL_ID"), text="Test message ✅")
    print("Sent!")

asyncio.run(main())