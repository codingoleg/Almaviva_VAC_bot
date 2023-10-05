from typing import Callable, Coroutine

import db
import telegram.keyboards as kb
from aiogram.types import Message


GREETING = '''
Неофициальный бот v. 0.2 для сканирования свободных окон в визовые центры 
Италии Almaviva. Находится на стадии тестирования.
Перед использованием внимательно прочтите информацию с этих сайтов, подойдет ли вам этот бот:
https://ru.almaviva-visa.services
https://github.com/codingoleg/Almaviva_VAC_auto_appointment/blob/master/README.ru.md\n 
'''

# Admin
ADMIN_MODE_ON = 'ADMIN_MODE_ON'
ADMIN_MODE_OFF = 'ADMIN_MODE_OFF'
ADMIN_HELP = '/user\n' \
             '/show_active_users\n' \
             '/show_ready_users\n' \
             '/start_ready_users\n' \
             '/admin_stop\n'

# Account
ACC_DELETE = 'Удалить акканут?'
ACC_DELETED = 'Аккаунт удален'
ACC_NOT_FOUND = 'Аккаунт не найден'

# Auth
AUTH_200 = 'Авторизация на сайте прошла успешно'
AUTH_400_500 = 'Указаны неверные имя пользователя или пароль'
AUTH_503 = 'Сайт недоступен. Попробуйте позже'
AUTH_ANOTHER = 'UNEXPECTED STATUS CODE'

# Callback data
CALLBACK_TO_START = 'to_start'
CALLBACK_ACC_DELETE = 'Удалить акканут?'
CALLBACK_START = 'CALLBACK_START'
CALLBACK_STOP = 'CALLBACK_STOP'
CALLBACK_BAN = 'CALLBACK_BAN'
CALLBACK_UNBAN = 'CALLBACK_UNBAN'
CALLBACK_USER_DELETE = 'Удалить аккаунт'

# Choose buttons
CHOOSE_START = 'Старт'
CHOOSE_STOP = 'Стоп'
CHOOSE_YES = 'Да'
CHOOSE_NO = 'Нет'
CHOOSE_BAN = 'Бан'
CHOOSE_UNBAN = 'Разбан'
CHOOSE_DELETE = 'Удалить'

# Choice text
CHOOSE_CITY = 'Выберите город'
CHOOSE_START_DATE = "Выберите начальную дату для поиска:"
CHOOSE_FINAL_DATE = "Выберите конечную дату для поиска:"
CHOOSE_ADMIN_ACTION = 'Выберите действие'

# Enter data
ENTER_EMAIL_ALMA = 'Введите email учетной записи Almaviva'
ENTER_PASSWORD_ALMA = "Введите пароль учетной записи Almaviva"
ENTER_USER_ID = 'Введите USER_ID'

# Person
USER_NOT_FOUND = 'Пользователь не найден или не заполнены все поля'
NO_ACTIVE_USERS = 'Нет активных пользователей'
NO_READY_USERS = 'Нет готовых пользователей'

# Scan
SCAN_STOP = 'Остановить сканирование?'
SCAN_STOPPED = 'Сканирование остановлено'
SCAN_CANCELLED = 'Сканирование отменено'
SCAN_NOT_FOUND = 'Сканирование не найдено'
SCAN_UNIQUE = 'Только одно сканирование доступно для каждого аккаунта'
SCAN_STARTED = 'Сканирование началось. Если появится свободное окно, вы ' \
               'получите сообщение. Отменить или посмотреть статус ' \
               'сканирования можно через меню.'

# States
ADMIN = 'admin'
ACTION = 'action'

# Other
ANTIFLOOD = 'Слишком много запросов'
BANNED = 'Вы заблокированы'
NOT_UNIQUE_EMAIL = 'Email уже используется другим пользователем'
REBOOT = 'Перезагрузка всех активных пользователей'
WRONG_DATES = 'Неверный формат даты'


def successful_appointment(year: str, month: str, day: str, time: str) -> str:
    return f'Появилось свободное окно: {year}/{month}/{day}. {time}.'


def admin_start_user(user_id: int) -> str:
    return f'{user_id} запущен'


def admin_user_ban(user_id: int) -> str:
    return f'{user_id} забанен'


def admin_user_unban(user_id: int) -> str:
    return f'{user_id} разбанен'


def check_scan(scan_status: Callable) -> Callable[[Message], Coroutine]:
    """Decorator for stop scanning and check scanning"""
    async def wrapper(message: Message):
        user_id_exists = db.user_id_exists(message.from_user.id, db.ACCOUNT)
        if user_id_exists:
            is_active = db.select_data(message.from_user.id, db.ACCOUNT,
                                       db.IS_ACTIVE)[0]
            if is_active:
                await scan_status(message)
            else:
                await message.answer(SCAN_NOT_FOUND)
        else:
            await message.answer(SCAN_NOT_FOUND)

    return wrapper


@check_scan
async def show_last_request(message: Message):
    last_request = db.select_data(message.from_user.id, db.ACCOUNT,
                                  db.LAST_REQUEST)[0]
    msg = f'Сканирование в процессе. Последнее время опроса: {last_request}'
    await message.answer(msg)


@check_scan
async def stop_scanning(message: Message):
    await message.answer(SCAN_STOP, reply_markup=kb.stop_scanning())
