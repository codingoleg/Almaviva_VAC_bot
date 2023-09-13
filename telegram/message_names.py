from typing import Callable, Coroutine

import db
import telegram.keyboards as kb
from aiogram.types import Message
from encrypting.encrypting import fernet


GREETING = '''
Неофициальный бот v. 0.1 для записи в визовые центры Италии 
Almaviva. Находится на стадии тестирования.
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
             '/admin_stop'

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
CALLBACK_1 = '1'
CALLBACK_2 = '2'
CALLBACK_YES = 'Да'
CALLBACK_NO = 'Нет'
CALLBACK_ACC = 'callback_acc'
CALLBACK_TO_START = 'to_start'
CALLBACK_TO_END = 'to_end'
CALLBACK_TO_PERSON_1 = 'to_person_1'
CALLBACK_TO_PERSON_2 = 'to_person_2'
CALLBACK_ACC_DELETE = 'Удалить акканут?'
CALLBACK_START = 'CALLBACK_START'
CALLBACK_STOP = 'CALLBACK_STOP'
CALLBACK_BAN = 'CALLBACK_BAN'
CALLBACK_UNBAN = 'CALLBACK_UNBAN'

# Choose buttons
CHOOSE_START = 'Старт'
CHOOSE_STOP = 'Стоп'
CHOOSE_YES = 'Да'
CHOOSE_NO = 'Нет'
CHOOSE_1 = '1'
CHOOSE_2 = '2'
CHOOSE_BAN = 'Бан'
CHOOSE_UNBAN = 'Разбан'

# Choice text
CHOOSE_NUM_OF_PERSONS = "Выберите количество человек"
CHOOSE_CITY = 'Выберите город'
CHOOSE_START_DATE = "Выберите начальную дату для поиска:"
CHOOSE_FINAL_DATE = "Выберите конечную дату для поиска:"
CHOOSE_ADMIN_ACTION = 'Выберите действие'

# Enter data
ENTER_EMAIL_ALMA = 'Введите email учетной записи Almaviva'
ENTER_PASSWORD_ALMA = "Введите пароль учетной записи Almaviva"
ENTER_USER_ID = 'Введите USER_ID'

# Person
FIRST_NAME = 'имя'
LAST_NAME = 'фамилию'
PERSON_1 = 'первого'
PERSON_2 = 'второго'
USER_NOT_FOUND = 'Пользователь не найден или не заполнены все поля'
NO_ACTIVE_USERS = 'Нет активных пользователей'
NO_READY_USERS = 'Нет готовых пользователей'

# Scan
SCAN_STOP = 'Остановить сканирование?'
SCAN_STOPPED = 'Сканирование остановлено'
SCAN_CANCELLED = 'Сканирование отменено'
SCAN_NOT_FOUND = 'Сканирование не найдено'
SCAN_UNIQUE = 'Только одно сканирование доступно для каждого аккаунта'
SCAN_STARTED = 'Сканирование началось. Если запись произойдет успешно, вы ' \
               'получите сообщение. Отменить или посмотреть статус ' \
               'сканирования можно через меню.'

# States
ADMIN = 'admin'
ACTION = 'action'

# Other
ANTIFLOOD = 'Слишком много запросов'
BANNED = 'Вы заблокированы'
IS_CORRECT = 'Данные верны?'
NOT_UNIQUE_EMAIL = 'Email уже используется другим пользователем'
REBOOT = 'Перезагрузка всех активных пользователей'
WRONG_DATES = 'Неверный формат даты'


def print_out_acc(num_of_persons: str, city: str) -> str:
    return f"Количество человек: {num_of_persons}\n" \
           f"Город: {fernet.decrypt(city).decode()}\n"


def enter_name(name_type: str, person_num: str) -> str:
    return f"Введите {name_type} {person_num} " \
           f"человека латинскими буквами по загранпаспорту"


def enter_phone(person_num: str) -> str:
    return f"Введите номер телефона {person_num} " \
           f"человека без пробелов.\nПример: 79261234567"


def enter_passport(person_num: str) -> str:
    return f"Введите номер паспорта {person_num} человека без пробелов"


def enter_email(person_num: str) -> str:
    return f"Введите email {person_num} человека"


def print_out_person(
        person_num: str,
        name: str,
        surname: str,
        passport: str,
        phone: str,
        email: str
) -> str:
    return f'Данные {person_num} человека:\n' \
           f"Имя: {fernet.decrypt(name).decode()}\n" \
           f"Фамилия: {fernet.decrypt(surname).decode()}\n" \
           f"Паспорт: {fernet.decrypt(passport).decode()}\n" \
           f"Телефон: {fernet.decrypt(phone).decode()}\n" \
           f"Email: {fernet.decrypt(email).decode()}\n"


def successful_appointment(year: str, month: str, day: str, time: str) -> str:
    return f'Запись успешно создана! {year}/{month}/{day}. {time}.\n' \
           f'Проверьте статус записи на сайте'


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
