import asyncio
import db
import telegram
from aiogram.utils import executor


if __name__ == '__main__':
    # Create database and tables if they don't exist
    db.create_all_tables()

    # Reset all users' scanning statuses to False
    db.reset_values(db.ACCOUNT, db.IS_ACTIVE)

    # Create schedule loop to restart all users' scanning
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(telegram.run_schedule())

    # Start bot with schedule loop
    telegram.dp.middleware.setup(telegram.ThrottlingMiddleware())
    executor.start_polling(telegram.dp, loop=loop, skip_updates=True)
