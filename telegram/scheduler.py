import asyncio
import schedule
from . import loggers
from . import message_names as msg
from .bot import cancel_task, create_task, users
from asyncio.exceptions import CancelledError

# Users with launched scanner
active_users = {}


async def run_schedule():
    while True:
        schedule.run_pending()
        await asyncio.sleep(15)


async def stop_active_users():
    global active_users
    active_users = {user_id for user_id in users}
    for user in active_users:
        try:
            await cancel_task(user)
        # Does nothing but preventing error message
        except CancelledError:
            pass


async def run_active_users():
    for user in active_users:
        await create_task(user)


def schedule_rerun():
    global active_users
    system_user = 0
    loggers.log(system_user, msg.REBOOT, loggers.WARNING)
    asyncio.ensure_future(stop_active_users())
    asyncio.ensure_future(run_active_users())
    active_users.clear()


# Restarts all active users. Start date is set up for tomorrow every rerun to
# prevent appointing to previous dates.
schedule.every().day.at('08:00').do(schedule_rerun)
