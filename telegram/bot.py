from datetime import datetime
from typing import Dict

import asyncio
import db
from . import loggers
from . import message_names as msg
from . import middleware as md
from . import keyboards as kb
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage import redis
from aiogram.types import Message, CallbackQuery
from asyncio.exceptions import CancelledError
from config import token, admin_id, bot_storage_host
from encrypting.encrypting import fernet
from scanner import Appointment, YEAR, MOSCOW_TZ, run_auth

bot = Bot(token=token)
dp = Dispatcher(bot, storage=redis.RedisStorage2(host=bot_storage_host))
ADMIN_ID = int(admin_id)

modify_user = 0  # Single user telegram ID to act with. Only for admin.
users = {}  # User's telegram IDs
tasks = set()  # Initial tasks
gather_task = asyncio.gather(*tasks)


async def create_task(user_id: int):
    """Creates scanning task for user"""
    global tasks, gather_task, users
    task = asyncio.create_task(dp_run_scanning(user_id))
    users[user_id] = task
    tasks.add(task)
    gather_task = asyncio.gather(*tasks)
    start_time = datetime.now(MOSCOW_TZ).strftime('%m/%d %H:%M')
    db.update_values(user_id, db.ACCOUNT,
                     (db.START_TIME, db.IS_ACTIVE), (start_time, True))
    loggers.log(user_id, msg.SCAN_STARTED, loggers.INFO)


async def cancel_task(user_id: int):
    """Cancels scanning task for user"""
    global tasks, gather_task, users
    task = users[user_id]
    task.cancel()
    loggers.log(user_id, msg.SCAN_CANCELLED)
    tasks.remove(task)
    gather_task = asyncio.gather(*tasks)
    del users[user_id]
    db.update_value(user_id, db.ACCOUNT, db.IS_ACTIVE, False)
    loggers.log(user_id, msg.SCAN_STOPPED, loggers.INFO)


# User handlers

@dp.message_handler(commands=['start'], state='*')
@md.rate_limit()
async def dp_start(message: Message):
    """Sends greeting message. If user has already launched scanning or is
    banned, sends corresponding messages"""
    user_id_exists = db.user_id_exists(message.from_user.id, db.ACCOUNT)
    if user_id_exists:
        is_active = db.select_data(message.from_user.id, db.ACCOUNT,
                                   db.IS_ACTIVE)[0]
    else:
        # Create 4 tables if user does not exist
        for table in (db.ACCOUNT, db.BANNED):
            db.insert_row(table, (db.USER_ID,), (message.from_user.id,))
        is_active = False

    if is_active:
        await message.answer(msg.SCAN_UNIQUE)
    else:
        banned = db.select_data(message.from_user.id, db.BANNED, db.BAN)[0]
        if banned:
            await message.answer(msg.BANNED)
        else:
            loggers.log(message.from_user.id, msg.GREETING)
            await message.answer(msg.GREETING, reply_markup=kb.start())
    await dp.current_state().reset_state()


@dp.callback_query_handler(text=msg.CALLBACK_TO_START)
async def dp_username(callback: CallbackQuery):
    """Requests email from Almaviva account"""
    await callback.answer()
    await callback.message.answer(msg.ENTER_EMAIL_ALMA)
    await dp.current_state().set_state("0")


@dp.message_handler(state='0')
async def dp_password(message: Message):
    """Requests password from Almaviva account"""
    db.update_value(message.from_user.id, db.ACCOUNT, db.USERNAME_ALMA,
                    fernet.encrypt(message.text.encode()))
    await message.answer(msg.ENTER_PASSWORD_ALMA)
    await dp.current_state().set_state('1')


@dp.message_handler(state='1')
async def dp_choose_city(message: Message):
    """Tries to authorize with entered email and password. If succeeded,
    requests city to appoint. Otherwise, sends warning message"""
    db.update_value(message.from_user.id, db.ACCOUNT, db.PASSWORD_ALMA,
                    fernet.encrypt(message.text.encode()))
    response = await run_auth(message.from_user.id)
    if response.status == 200:
        loggers.log(message.from_user.id, msg.AUTH_200, loggers.INFO)
        await bot.send_message(message.from_user.id, msg.AUTH_200)
        await bot.send_message(message.from_user.id, msg.CHOOSE_CITY,
                               reply_markup=kb.cities())
        await dp.current_state().set_state('3')
    elif response.status in (400, 500):
        loggers.log(message.from_user.id, msg.AUTH_400_500, loggers.WARNING)
        await bot.send_message(message.from_user.id, msg.AUTH_400_500)
        await dp.current_state().reset_state()
    elif response.status == 503:
        loggers.log(message.from_user.id, msg.AUTH_503, loggers.WARNING)
        await bot.send_message(message.from_user.id, msg.AUTH_503)
        await dp.current_state().reset_state()
    else:
        loggers.log(
            message.from_user.id,
            f'{msg.AUTH_ANOTHER}{response.status}',
            loggers.WARNING
        )
        await bot.send_message(message.from_user.id, msg.AUTH_ANOTHER)
        # If unexpected status code occurs send message to Admin also
        await bot.send_message(
            ADMIN_ID,
            f'{msg.AUTH_ANOTHER} {response.status}: {message.from_user.id}'
        )
        await dp.current_state().reset_state()


@dp.callback_query_handler(state='3')
async def dp_start_date(callback: CallbackQuery):
    """Shows inline calendar. Requests start date to appoint"""
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, callback.data)
    db.update_value(callback.from_user.id, db.ACCOUNT, db.CITY,
                    fernet.encrypt(callback.data.encode()))
    await callback.message.answer(
        msg.CHOOSE_START_DATE,
        reply_markup=await kb.Calendar().start_calendar()
    )
    await dp.current_state().set_state("4")


@dp.callback_query_handler(kb.CALENDAR_CALLBACK.filter(), state='4')
async def dp_final_date(callback: CallbackQuery, callback_data: Dict):
    """Shows inline calendar. Requests final date to appoint"""
    selected, single_date = await kb.Calendar().process_selection(
        callback, callback_data)
    if selected:
        db.update_values(
            callback.from_user.id,
            db.ACCOUNT,
            (db.ST_MONTH, db.ST_DAY),
            (single_date.month, single_date.day)
        )
        await callback.message.answer(single_date.strftime("%d/%m/%Y"))
        # For the second calendar start date is not today as in the first
        # calendar, but date that user entered into the first calendar.
        # This prevents previous date choice as final date.
        start_date = datetime(int(YEAR), single_date.month, single_date.day)
        await bot.send_message(
            callback.from_user.id,
            msg.CHOOSE_FINAL_DATE,
            reply_markup=await kb.Calendar(start_date).start_calendar(
                month=single_date.month)
        )
        await dp.current_state().set_state("5")


@dp.callback_query_handler(kb.CALENDAR_CALLBACK.filter(), state='5')
async def dp_check_acc(callback: CallbackQuery, callback_data: Dict):
    """Request user for input data correctness:
     1. If data is not correct return to input number of persons.
     2. If data is correct, proceed to input (Person 1)"""
    month = db.select_data(callback.from_user.id, db.ACCOUNT, db.ST_MONTH)[0]
    day = db.select_data(callback.from_user.id, db.ACCOUNT, db.ST_DAY)[0]
    start_date = datetime(int(YEAR), month, day)

    selected, single_date = await kb.Calendar(start_date).process_selection(
        callback, callback_data)
    if selected:
        await bot.send_message(callback.from_user.id,
                               single_date.strftime("%d/%m/%Y"))
        db.update_values(
            callback.from_user.id,
            db.ACCOUNT,
            (db.FIN_MONTH, db.FIN_DAY),
            (single_date.month, single_date.day)
        )
        """Creates task to launch scanning"""
        await create_task(callback.from_user.id)
        await bot.send_message(callback.from_user.id, msg.SCAN_STARTED)
        await dp.current_state().reset_state()


@dp.message_handler(commands=['stop_scanning'], state='*')
@md.rate_limit()
async def dp_stop_scanning(message: Message):
    """Requests to stop scanning"""
    await msg.stop_scanning(message)
    await dp.current_state().reset_state()


@dp.callback_query_handler(text=msg.SCAN_STOPPED)
async def dp_stop_scanning_callback(callback: CallbackQuery):
    """Stops scanning"""
    await cancel_task(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(msg.SCAN_STOPPED)


@dp.message_handler(commands=['check_scanning'], state='*')
@md.rate_limit()
async def dp_check_scanning(message: Message):
    """Shows scanning status and it's last request time"""
    await msg.show_last_request(message)
    await dp.current_state().reset_state()


@dp.message_handler(commands=['delete_acc'], state='*')
@md.rate_limit()
async def dp_delete_acc(message: Message):
    """If user ID exists, requests to delete account"""
    user_id_exists = db.user_id_exists(message.from_user.id, db.ACCOUNT)
    if user_id_exists:
        await message.answer(msg.ACC_DELETE, reply_markup=kb.acc_delete())
    else:
        await message.answer(msg.ACC_NOT_FOUND)
    await dp.current_state().reset_state()


@dp.callback_query_handler(text=msg.CALLBACK_ACC_DELETE)
async def dp_delete_acc_callback(callback: CallbackQuery):
    """Stops scanning and deletes all tables, except 'banned'"""
    is_active = db.select_data(callback.from_user.id, db.ACCOUNT,
                               db.IS_ACTIVE)[0]
    if is_active:
        await cancel_task(callback.from_user.id)
    db.delete_user(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(msg.ACC_DELETED)


async def dp_run_scanning(user_id: int):
    """Launches scanner. Sends message if it gets result or cancelled"""
    try:
        app_result = await Appointment(user_id).run_scanning()
    except CancelledError:
        app_result = False

    # Successful appointment
    if app_result:
        month, day, free_time = [data for data in app_result]
        await bot.send_message(
            user_id, msg.successful_appointment(YEAR, month, day, free_time)
        )
        loggers.log(
            user_id,
            msg.successful_appointment(YEAR, month, day, free_time),
            loggers.INFO
        )
        await cancel_task(user_id)
    elif app_result is None:
        loggers.log(user_id, msg.WRONG_DATES, loggers.WARNING)
        await cancel_task(user_id)


# Admin handlers

@dp.message_handler(commands=['admin'], state='*')
async def dp_admin_start(message: Message):
    """Enters admin mode"""
    if message.from_user.id == ADMIN_ID:
        await message.answer(msg.ADMIN_MODE_ON)
        await bot.send_message(message.from_user.id, msg.ADMIN_HELP)
        loggers.log(message.from_user.id, msg.ADMIN_MODE_ON,
                    loggers.WARNING)
        await dp.current_state().set_state(msg.ADMIN)


@dp.message_handler(commands=['admin_stop'], state=msg.ADMIN)
async def dp_admin_stop(message: Message):
    """Exits admin mode"""
    await message.answer(msg.ADMIN_MODE_OFF)
    loggers.log(message.from_user.id, msg.ADMIN_MODE_OFF,
                loggers.WARNING)
    await dp.current_state().reset_state()


@dp.message_handler(commands=['start_ready_users'], state=msg.ADMIN)
async def dp_start_users(message: Message):
    """Starts scanning for all users with filled data"""
    for user_id in db.get_ready_users():
        await run_auth(user_id)
        await create_task(user_id)
        await message.answer(msg.admin_start_user(user_id))


@dp.message_handler(commands=['user'], state=msg.ADMIN)
async def dp_choose_user(message: Message):
    """Requests for user ID to interact with"""
    await message.answer(msg.ENTER_USER_ID)
    await dp.current_state().set_state(msg.ACTION)


@dp.message_handler(lambda message: message.text.isdigit(), state=msg.ACTION)
async def dp_choose_action(message: Message):
    """Shows admin panel to interact with user id"""
    global modify_user
    modify_user = int(message.text)
    await message.answer(msg.CHOOSE_ADMIN_ACTION,
                         reply_markup=kb.admin_panel())


@dp.callback_query_handler(text=msg.CALLBACK_START, state=msg.ACTION)
async def dp_create_task(callback: CallbackQuery):
    """Launches scanner for single user only with filled data"""
    global modify_user
    if modify_user in db.get_ready_users():
        await run_auth(modify_user)
        await create_task(modify_user)
        await callback.answer()
        await callback.message.answer(msg.admin_start_user(modify_user))
    else:
        await callback.message.answer(msg.USER_NOT_FOUND)
    modify_user = 0
    await dp.current_state().set_state(msg.ADMIN)


@dp.callback_query_handler(text=msg.CALLBACK_STOP, state=msg.ACTION)
async def dp_cancel_task(callback: CallbackQuery):
    """Stops scanner for single user"""
    global modify_user
    await cancel_task(modify_user)
    await callback.answer()
    await callback.message.answer(msg.SCAN_STOPPED)
    modify_user = 0
    await dp.current_state().set_state(msg.ADMIN)


@dp.callback_query_handler(text=msg.CALLBACK_BAN, state=msg.ACTION)
async def dp_ban(callback: CallbackQuery):
    """Bans user"""
    global modify_user
    db.update_value(modify_user, db.BANNED, db.BAN, True)
    await callback.answer()
    await callback.message.answer(msg.admin_user_ban(modify_user))
    modify_user = 0
    await dp.current_state().set_state(msg.ADMIN)


@dp.callback_query_handler(text=msg.CALLBACK_UNBAN, state=msg.ACTION)
async def dp_unban(callback: CallbackQuery):
    """Unbans user"""
    global modify_user
    db.update_value(modify_user, db.BANNED, db.BAN, False)
    await callback.answer()
    await callback.message.answer(msg.admin_user_unban(modify_user))
    modify_user = 0
    await dp.current_state().set_state(msg.ADMIN)


@dp.callback_query_handler(text=msg.CALLBACK_USER_DELETE, state=msg.ACTION)
async def dp_delete_user(callback: CallbackQuery):
    """Deletes user"""
    global modify_user
    user_id_exists = db.user_id_exists(modify_user, db.ACCOUNT)
    if user_id_exists:
        is_active = db.select_data(modify_user, db.ACCOUNT, db.IS_ACTIVE)[0]
        if is_active:
            await cancel_task(modify_user)
        db.delete_user(modify_user)
        await callback.message.answer(msg.ACC_DELETE,
                                      reply_markup=kb.acc_delete())
    else:
        await callback.message.answer(msg.ACC_NOT_FOUND)
    modify_user = 0
    await dp.current_state().set_state(msg.ADMIN)


@dp.message_handler(commands=['show_active_users'], state=msg.ADMIN)
async def show_active_users(message: Message):
    """Shows all users with launched scanner"""
    if users:
        for user_id in users:
            start_time = db.select_data(user_id, db.ACCOUNT, db.START_TIME)[0]
            last_request = db.select_data(user_id, db.ACCOUNT,
                                          db.LAST_REQUEST)[0]
            await message.answer(f'{user_id} [{start_time}] [{last_request}]')
    else:
        await message.answer(msg.NO_ACTIVE_USERS)


@dp.message_handler(commands=['show_ready_users'], state=msg.ADMIN)
async def show_ready_users(message: Message):
    """Shows all users with filled data"""
    ready_users = db.get_ready_users()
    if ready_users:
        await message.answer(' '.join(str(user) for user in ready_users))
    else:
        await message.answer(msg.NO_READY_USERS)
