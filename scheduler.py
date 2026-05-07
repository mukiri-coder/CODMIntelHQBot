import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot import post_updates

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(post_updates, 'interval', minutes=60)
    scheduler.start()
    print("CODM bot running... ⚙️")
    # Keep running forever
    while True:
        await asyncio.sleep(3600)

asyncio.run(main())